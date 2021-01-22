import copy
import csv
import glob
import itertools
import json
import os
from collections import OrderedDict, defaultdict
from datetime import timedelta
# from scripts.dataentry.tutorials import Session
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

import jsons
import pytz
import yaml

from miniconf.site_data import (
    CommitteeMember,
    Paper,
    PaperContent,
    PlenarySession,
    PlenaryVideo,
    QaSession,
    QaSubSession,
    SessionInfo,
    SocialEvent,
    SocialEventOrganizers,
    Tutorial,
    TutorialSessionInfo,
    TutorialAuthorInfo,
    Workshop,
    WorkshopPaper,
    DoctoralConsortium,
    Award,
    Awardee,
    Demonstrations
)


def load_site_data(
    site_data_path: str, site_data: Dict[str, Any], by_uid: Dict[str, Any],
) -> List[str]:
    """Loads all site data at once.

    Populates the `committee` and `by_uid` using files under `site_data_path`.

    NOTE: site_data[filename][field]
    """
    registered_sitedata = {
        "config",
        # index.html
        "committee",
        # schedule.html
        "overall_calendar",
        "plenary_sessions",
        "opening_remarks",
        # tutorials.html
        "tutorials",
        # papers.html
        "AI for Social Impact Track_papers",
        "Demos_papers",
        "Doctoral Consortium_papers",
        "doctoral_consortium",
        "EAAI_papers",
        "IAAI_papers",
        "Main Track_papers",
        "Senior Member Track_papers",
        "Sister Conference_papers",
        "Student Abstracts_papers",
        "Undergraduate Consortium_papers",
        "award_papers",
        "paper_recs",
        "papers_projection",
        "paper_sessions",
        # socials.html
        "socials",
        # workshops.html
        "workshops",
        "workshop_papers",
        # sponsors.html
        "sponsors",
        # about.html
        "awards",
        "code_of_conduct",
        "faq",
        "demonstrations",
    }
    extra_files = []
    # Load all for your sitedata one time.
    for f in glob.glob(site_data_path + "/*"):
        filename = os.path.basename(f)
        if filename == "inbox":
            continue
        name, typ = filename.split(".")
        if name not in registered_sitedata:
            continue

        extra_files.append(f)
        if typ == "json":
            site_data[name] = json.load(open(f, encoding="utf-8"))
        elif typ in {"csv", "tsv"}:
            site_data[name] = list(csv.DictReader(open(f, encoding="utf-8")))
        elif typ == "yml":
            site_data[name] = yaml.load(open(f, encoding="utf-8").read(), Loader=yaml.SafeLoader)
    assert set(site_data.keys()) == registered_sitedata, registered_sitedata - set(
        site_data.keys()
    )

    display_time_format = "%H:%M"

    # index.html
    site_data["committee"] = build_committee(site_data["committee"]["committee"])

    # schedule.html
    generate_plenary_events(site_data)
    generate_tutorial_events(site_data)
    generate_workshop_events(site_data)
    generate_dc_events(site_data)
    generate_paper_events(site_data)
    generate_social_events(site_data)

    site_data["calendar"] = build_schedule(site_data["overall_calendar"])
    site_data["event_types"] = list(
        {event["type"] for event in site_data["overall_calendar"]}
    )

    # plenary_sessions.html
    plenary_sessions = build_plenary_sessions(
        raw_plenary_sessions=site_data["plenary_sessions"],
        raw_plenary_videos={"opening_remarks": site_data["opening_remarks"]},
    )

    site_data["plenary_sessions"] = plenary_sessions
    by_uid["plenary_sessions"] = {
        plenary_session.id: plenary_session
        for _, plenary_sessions_on_date in plenary_sessions.items()
        for plenary_session in plenary_sessions_on_date
    }
    site_data["plenary_session_days"] = [
        [day.replace(" ", "").lower(), day, ""] for day in plenary_sessions
    ]
    site_data["plenary_session_days"][0][-1] = "active"

    # Papers' progam to their data
    for p in site_data["AI for Social Impact Track_papers"]:
        p["program"] = "AISI"
    for p in site_data["Demos_papers"]:
        p["program"] = "Demo"
    for p in site_data["Doctoral Consortium_papers"]:
        p["program"] = "DC"
    for p in site_data["EAAI_papers"]:
        p["program"] = "EAAI"
    for p in site_data["IAAI_papers"]:
        p["program"] = "IAAI"
    for p in site_data["Main Track_papers"]:
        p["program"] = "Main"
    for p in site_data["Senior Member Track_papers"]:
        p["program"] = "SMT"
    for p in site_data["Sister Conference_papers"]:
        p["program"] = "SC"
    for p in site_data["Student Abstracts_papers"]:
        p["program"] = "SA"
    for p in site_data["Undergraduate Consortium_papers"]:
        p["program"] = "UC"
    for p in site_data["award_papers"]:
        p["program"] = "Award"

    site_data["programs"] = ["AISI", "Demo", "DC",
                             "EAAI", "IAAI","Main","SMT","SC",
                             "SA","UC","Award"]

    # tutorials.html
    tutorial_MQ = []
    tutorial_MH = []
    tutorial_AQ = []
    tutorial_AH = []

    # IAAI poster presentation
    iaai_poster_schedule = {}
    iaai_poster_schedule['February 4, Thursday'] = {}
    iaai_poster_schedule['February 5, Friday'] = {}
    iaai_poster_schedule['February 6, Saturday'] = {}
    iaai_poster_schedule['February 4, Thursday']['Aerospace'] = [74,132,171]
    iaai_poster_schedule['February 4, Thursday']['Commerce'] = [23,84,87,92,93,101,140,179,190]
    iaai_poster_schedule['February 4, Thursday']['Security'] = [98,113,142]
    iaai_poster_schedule['February 5, Friday']['General'] = [104]
    iaai_poster_schedule['February 5, Friday']['Engineering'] = [100,105,165,176]
    iaai_poster_schedule['February 5, Friday']['Knowledge'] = [21,37,59,65,119,151,157,174]
    iaai_poster_schedule['February 5, Friday']['Natural Language Processing'] = [89]
    iaai_poster_schedule['February 5, Friday']['Prediction'] = [43,55]
    iaai_poster_schedule['February 6, Saturday']['Artificial Intelligence'] = [17,31,60,73,167]
    iaai_poster_schedule['February 6, Saturday']['Bioscience'] = [76,77,124,145,146,149]
    iaai_poster_schedule['February 6, Saturday']['COVID'] = [152,154]
    iaai_poster_schedule['February 6, Saturday']['Driving'] = [34]
    iaai_poster_schedule['February 6, Saturday']['Intelligent Technology'] = [99]

    site_data["iaai_poster_schedule"] = iaai_poster_schedule


    # undergraduate_consortium.html
    tutorial_UC = []
    tutorial_OTHER = []

    for item in site_data["tutorials"]:
        if "MQ" in item["UID"]:
            tutorial_MQ.append(item)
        if "MH" in item["UID"]:
            tutorial_MH.append(item)
        if "AQ" in item["UID"]:
            tutorial_AQ.append(item)
        if "AH" in item["UID"]:
            tutorial_AH.append(item)
        if item["UID"] == "UC":
            tutorial_OTHER.append(item)
        if "UC" in item["UID"]:
            tutorial_UC.append(item)

    tutorials = build_tutorials(site_data["tutorials"])

    site_data["tutorials"] = tutorials
    site_data["tutorial_calendar"] = build_tutorial_schedule(
        site_data["overall_calendar"]
    )
    site_data["tutorials_MQ"] = build_tutorials(tutorial_MQ)
    site_data["tutorials_MH"] = build_tutorials(tutorial_MH)
    site_data["tutorials_AQ"] = build_tutorials(tutorial_AQ)
    site_data["tutorials_AH"] = build_tutorials(tutorial_AH)
    site_data["tutorials_UC"] = build_tutorials(tutorial_UC)
    site_data["tutorials_OTHER"] = build_tutorials(tutorial_OTHER)
    # tutorial_<uid>.html
    by_uid["tutorials"] = {tutorial.id: tutorial for tutorial in tutorials}

    # workshops.html
    workshops = build_workshops(
        raw_workshops=site_data["workshops"],
        raw_workshop_papers=site_data["workshop_papers"],
    )
    site_data["workshops"] = workshops
    # workshop_<uid>.html
    by_uid["workshops"] = {workshop.id: workshop for workshop in workshops}

    # Doctoral Consortium
    doctoral_consortium=build_doctoral_consortium(site_data["doctoral_consortium"])
    site_data["doctoral_consortium"] = doctoral_consortium

    # Demonstrations
    demonstrations=build_tutorials(site_data["demonstrations"])
    site_data["demonstrations"] = demonstrations

    # socials.html/diversity_programs.html
    social_events = build_socials(site_data["socials"])
    site_data["socials"] = social_events

    # organization awards
    awards = build_awards(site_data['awards'])
    site_data['awards'] = awards

    # papers.{html,json}
    papers = build_papers(
        raw_papers=site_data["AI for Social Impact Track_papers"]+
            site_data["Demos_papers"]+
            site_data["Doctoral Consortium_papers"]+
            site_data["EAAI_papers"]+
            site_data["IAAI_papers"]+
            site_data["Main Track_papers"]+
            site_data["Senior Member Track_papers"]+
            site_data["Sister Conference_papers"]+
            site_data["Student Abstracts_papers"]+
            site_data["award_papers"]+
            site_data["Undergraduate Consortium_papers"],
        paper_sessions=site_data["paper_sessions"],
        paper_recs=site_data["paper_recs"],
        paper_images_path=site_data["config"]["paper_images_path"],
        default_image_path=site_data["config"]["logo"]["image"]
    )
    # remove workshop paper in papers.html
    # for wsh in site_data["workshops"]:
    #     papers.extend(wsh.papers)
    site_data["papers"] = papers

    site_data["tracks"] = list(
        sorted(track for track in {paper.content.track for paper in papers})
    )

    site_data["main_program_tracks"] = list(
        sorted(
            track
            for track in {
                paper.content.track
                for paper in papers
                if paper.content.program == "main"
            }
        )
    )
    # paper_<uid>.html
    papers_by_uid: Dict[str, Any] = {}
    for paper in papers:
        assert paper.id not in papers_by_uid, paper.id
        papers_by_uid[paper.id] = paper
    by_uid["papers"] = papers_by_uid
    # serve_papers_projection.json
    all_paper_ids_with_projection = {
        item["id"] for item in site_data["papers_projection"]
    }
    for paper_id in set(by_uid["papers"].keys()) - all_paper_ids_with_projection:
        paper = by_uid["papers"][paper_id]
        if paper.content.program == "main":
            print(f"WARNING: {paper_id} does not have a projection")

    # about.html
    site_data["faq"] = site_data["faq"]["FAQ"]
    site_data["code_of_conduct"] = site_data["code_of_conduct"]["CodeOfConduct"]

    # sponsors.html
    build_sponsors(site_data, by_uid, display_time_format)

    # qa_sessions.html
    site_data["qa_sessions"], site_data["qa_session_days"] = build_qa_sessions(
        site_data["paper_sessions"]
    )
    site_data["qa_sessions_by_day"] = {
        day: list(sessions)
        for day, sessions in itertools.groupby(
            site_data["qa_sessions"], lambda qa: qa.day
        )
    }

    print("Data Successfully Loaded")
    return extra_files


def extract_list_field(v, key):
    value = v.get(key, "")
    if isinstance(value, list):
        return value
    else:
        return value.split("|")


def build_committee(
    raw_committee: List[Dict[str, Any]]
) -> Dict[str, List[CommitteeMember]]:
    # We want to show the committee grouped by role. Grouping has to be done in python since jinja's groupby sorts
    # groups by name, i.e. the general chair would not be on top anymore because it doesn't start with A.
    # See https://github.com/pallets/jinja/issues/250

    committee = [jsons.load(item, cls=CommitteeMember) for item in raw_committee]
    committee_by_role = OrderedDict()
    for role, members in itertools.groupby(committee, lambda member: member.role):
        member_list = list(members)
        # add plural 's' to "chair" roles with multiple members
        if role.lower().endswith("chair") and len(member_list) > 1:
            role += "s"
        committee_by_role[role] = member_list

    return committee_by_role

def build_awards(raw_awards: List[Dict[str, Any]]) -> List[Award]:
    # print(raw_awards)
    return [
        Award(
            id=award["id"],
            name=award["name"],
            description=award["description"],
            awardees=[Awardee(
                name=awardee['name'],
                id=awardee['id'],
                link=awardee['link'] if 'link' in awardee.keys() else None,
                description=awardee['description'] if 'description' in awardee.keys() else None,
                paperlink=awardee['paperlink'] if 'paperlink' in awardee.keys() else None,
                image=awardee['image'] if 'image' in awardee.keys() else None,
                organization=awardee['organization'],
                talk=SessionInfo(session_name = awardee['talk'][0]['session_name'], 
                                start_time=awardee['talk'][0]['start_time'],
                                end_time=awardee['talk'][0]['end_time'],
                                link=awardee['talk'][0]['link']) 
                                if 'talk' in awardee.keys() else None
            ) for awardee in award['awardees']]
        )
        for award in raw_awards
    ]

def build_plenary_sessions(
    raw_plenary_sessions: List[Dict[str, Any]],
    raw_plenary_videos: Dict[str, List[Dict[str, Any]]],
) -> DefaultDict[str, List[PlenarySession]]:

    plenary_videos: DefaultDict[str, List[PlenaryVideo]] = defaultdict(list)
    for plenary_id, videos in raw_plenary_videos.items():
        for item in videos:
            plenary_videos[plenary_id].append(
                PlenaryVideo(
                    id=item["UID"],
                    title=item["title"],
                    speakers=item["speakers"],
                    presentation_id=item["presentation_id"],
                )
            )

    plenary_sessions: DefaultDict[str, List[PlenarySession]] = defaultdict(list)
    for item in raw_plenary_sessions:
        plenary_sessions[item["day"]].append(
            PlenarySession(
                id=item["UID"],
                title=item["title"],
                image=item["image"],
                day=item["day"],
                sessions=[
                    SessionInfo(
                        session_name=session.get("name"),
                        start_time=session.get("start_time"),
                        end_time=session.get("end_time"),
                        link=session.get("zoom_link"),
                    )
                    for session in item.get("sessions")
                ],
                presenter=item.get("presenter"),
                institution=item.get("institution"),
                abstract=item.get("abstract"),
                bio=item.get("bio"),
                presentation_id=item.get("presentation_id"),
                rocketchat_channel=item.get("rocketchat_channel"),
                videos=plenary_videos.get(item["UID"]),
            )
        )

    return plenary_sessions


def generate_plenary_events(site_data: Dict[str, Any]):
    """ We add sessions from the plenary for the weekly and daily view. """
    # Add plenary sessions to calendar
    all_sessions = []
    for plenary in site_data["plenary_sessions"]:
        uid = plenary["UID"]

        for session in plenary["sessions"]:
            start = session["start_time"]
            end = session["end_time"]
            event = {
                "title": "<b>" + plenary["title"] + "</b>",
                "start": start,
                "end": end,
                "location": f"plenary_session_{uid}.html",
                "link": f"plenary_session_{uid}.html",
                "category": "time",
                "type": "Plenary Sessions",
                "view": "day",
            }
            site_data["overall_calendar"].append(event)
            assert start < end, "Session start after session end"

            all_sessions.append(session)

    blocks = compute_schedule_blocks(all_sessions)

    # Compute start and end of tutorial blocks
    for block in blocks:
        min_start = min([t["start_time"] for t in block])
        max_end = max([t["end_time"] for t in block])

        tz = pytz.timezone("America/Santo_Domingo")
        punta_cana_date = min_start.astimezone(tz)

        tab_id = punta_cana_date.strftime("%b%d").lower()

        event = {
            "title": "Plenary Session",
            "start": min_start,
            "end": max_end,
            "location": f"plenary_sessions.html#tab-{tab_id}",
            "link": f"plenary_sessions.html#tab-{tab_id}",
            "category": "time",
            "type": "Plenary Sessions",
            "view": "week",
        }
        site_data["overall_calendar"].append(event)


def generate_tutorial_events(site_data: Dict[str, Any]):
    """ We add sessions from tutorials and compute the overall tutorial blocks for the weekly view. """

    # Add tutorial sessions to calendar
    all_sessions: List[Dict[str, Any]] = []
    uc_sessions: List[Dict[str, Any]] = []
    for tutorial in site_data["tutorials"]:
        if "UC" in tutorial["UID"]:
            uid = tutorial["UID"]
            blocks = compute_schedule_blocks(tutorial["sessions"])

            for block in blocks:
                min_start = min([t["start_time"] for t in block])
                max_end = max([t["end_time"] for t in block])
                if uid == "UC":
                    event = {
                        "title": f"<b>{uid}: {tutorial['title']}</b><br/><i>{tutorial['organizers']}</i>",
                        "start": min_start,
                        "end": max_end,
                        "location": f"undergraduate_consortium.html",
                        "link": f"undergraduate_consortium.html",
                        "category": "time",
                        "type": "Undergraduate Consortium",
                        "view": "day",
                    }
                else:
                    event = {
                        "title": f"<b>{uid}: {tutorial['title']}</b><br/><i>{tutorial['organizers']}</i>",
                        "start": min_start,
                        "end": max_end,
                        "location": f"paper_{uid}.html",
                        "link": f"paper_{uid}.html",
                        "category": "time",
                        "type": "Undergraduate Consortium",
                        "view": "day",
                    }
                site_data["overall_calendar"].append(event)
                assert min_start < max_end, "Session start after session end"

            uc_sessions.extend(tutorial["sessions"])
        else:
            uid = tutorial["UID"]
            blocks = compute_schedule_blocks(tutorial["sessions"])

            for block in blocks:
                min_start = min([t["start_time"] for t in block])
                max_end = max([t["end_time"] for t in block])
                event = {
                    "title": f"<b>{uid}: {tutorial['title']}</b><br/><i>{tutorial['organizers']}</i>",
                    "start": min_start,
                    "end": max_end,
                    "location": f"tutorial_{uid}.html",
                    "link": f"tutorial_{uid}.html",
                    "category": "time",
                    "type": "Tutorials",
                    "view": "day",
                }
                site_data["overall_calendar"].append(event)
                assert min_start < max_end, "Session start after session end"

            all_sessions.extend(tutorial["sessions"])

    blocks = compute_schedule_blocks(all_sessions)

    # Compute start and end of tutorial blocks
    for block in blocks:
        min_start = min([t["start_time"] for t in block])
        max_end = max([t["end_time"] for t in block])

        event = {
            "title": "Tutorials",
            "start": min_start,
            "end": max_end,
            "location": "tutorials.html",
            "link": "tutorials.html",
            "category": "time",
            "type": "Tutorials",
            "view": "week",
        }
        site_data["overall_calendar"].append(event)

    uc_blocks = compute_schedule_blocks(uc_sessions)

    # Compute start and end of tutorial blocks
    for block in uc_blocks:
        min_start = min([t["start_time"] for t in block])
        max_end = max([t["end_time"] for t in block])

        event = {
            "title": "Undergraduate Consortium",
            "start": min_start,
            "end": max_end,
            "location": "undergraduate_consortium.html",
            "link": "undergraduate_consortium.html",
            "category": "time",
            "type": "Undergraduate Consortium",
            "view": "week",
        }
        site_data["overall_calendar"].append(event)

def generate_dc_events(site_data: Dict[str, Any]):
    """ We add sessions from tutorials and compute the overall dc blocks for the weekly view. """

    # Add tutorial sessions to calendar
    all_sessions: List[Dict[str, Any]] = []
    for dc in site_data["doctoral_consortium"]:
        uid = dc["UID"]
        blocks = compute_schedule_blocks(dc["sessions"])

        for block in blocks:
            min_start = min([t["start_time"] for t in block])
            max_end = max([t["end_time"] for t in block])
            event = {
                "title": f"<b>{uid}: {dc['title']}</b><br/><i>{dc['organizers']}</i>",
                "start": min_start,
                "end": max_end,
                "location": f"doctoral_consortium.html",
                "link": f"doctoral_consortium.html",
                "category": "time",
                "type": "Doctoral Consortium",
                "view": "day",
            }
            site_data["overall_calendar"].append(event)
            assert min_start < max_end, "Session start after session end"

        all_sessions.extend(dc["sessions"])

    blocks = compute_schedule_blocks(all_sessions)

    # Compute start and end of tutorial blocks
    for block in blocks:
        min_start = min([t["start_time"] for t in block])
        max_end = max([t["end_time"] for t in block])

        event = {
            "title": "Doctoral Consortium",
            "start": min_start,
            "end": max_end,
            "location": "doctoral_consortium.html",
            "link": "doctoral_consortium.html",
            "category": "time",
            "type": "Doctoral Consortium",
            "view": "week",
        }
        site_data["overall_calendar"].append(event)
        # print("*******************************")
        # for e in site_data["overall_calendar"]:
        #     print(e)


def generate_workshop_events(site_data: Dict[str, Any]):
    """ We add sessions from workshops and compute the overall workshops blocks for the weekly view. """
    # Add workshop sessions to calendar
    all_sessions: List[Dict[str, Any]] = []
    for workshop in site_data["workshops"]:
        uid = workshop["UID"]
        all_sessions.extend(workshop["sessions"])

        for block in compute_schedule_blocks(workshop["sessions"]):
            min_start = min([t["start_time"] for t in block])
            max_end = max([t["end_time"] for t in block])

            event = {
                "title": f"<b>{workshop['title']}</b><br/> <i>{workshop['organizers']}</i>",
                "start": min_start,
                "end": max_end,
                "location": f"workshop_{uid}.html",
                "link": f"workshop_{uid}.html",
                "category": "time",
                "type": "Workshops",
                "view": "day",
            }
            site_data["overall_calendar"].append(event)

            assert min_start < max_end, "Session start after session end"

    blocks = compute_schedule_blocks(all_sessions)

    # Compute start and end of workshop blocks
    for block in blocks:
        min_start = min([t["start_time"] for t in block])
        max_end = max([t["end_time"] for t in block])

        event = {
            "title": "Workshops",
            "start": min_start,
            "end": max_end,
            "location": "workshops.html",
            "link": "workshops.html",
            "category": "time",
            "type": "Workshops",
            "view": "week",
        }
        site_data["overall_calendar"].append(event)


def generate_paper_events(site_data: Dict[str, Any]):
    """ We add sessions from papers and compute the overall paper blocks for the weekly view. """
    # Add paper sessions to calendar

    all_grouped: Dict[str, List[Any]] = defaultdict(list)
    for uid, session in site_data["paper_sessions"].items():
        start = session["start_time"]
        end = session["end_time"]

        parts = session["long_name"].split(":", 1)

        event = {
            "title": f"<b>{parts[0]}</b><br>{parts[1]}",
            "start": start,
            "end": end,
            "location": "",
            "link": f"papers.html?session={uid}&program=all",
            "category": "time",
            "type": "QA Sessions",
            "view": "day",
        }
        site_data["overall_calendar"].append(event)

        assert start < end, "Session start after session end"

        # Sessions are suffixd with subsession id
        all_grouped[uid[:-1]].append(session)
    print(all_grouped)
    for uid, group in all_grouped.items():
        start_time = group[0]["start_time"]
        end_time = group[0]["end_time"]
        assert all(s["start_time"] == start_time for s in group)
        assert all(s["end_time"] == end_time for s in group)

        number = uid[1:]
        tab_id = (
            start_time.astimezone(pytz.utc).strftime("%b %d").replace(" ", "").lower()
        )

        if uid.startswith("z"):
            name = f"Zoom Q&A Session {number}"
        elif uid.startswith("g"):
            name = f"Gather Session {number}"
        else:
            raise Exception("Invalid session type")

        event = {
            "title": name,
            "start": start_time,
            "end": end_time,
            "location": "",
            "link": f"qa_sessions.html#tab-{tab_id}",
            "category": "time",
            "type": "QA Sessions",
            "view": "week",
        }
        site_data["overall_calendar"].append(event)


def generate_social_events(site_data: Dict[str, Any]):
    """ We add social sessions and compute the overall paper social for the weekly view. """
    # Add paper sessions to calendar

    all_sessions = []
    for social in site_data["socials"]:
        for session in social["sessions"]:
            start = session["start_time"]
            end = session["end_time"]

            uid = social["UID"]
            if uid.startswith("B"):
                name = "<b>Birds of a Feather</b><br>" + social["name"]
            elif uid.startswith("A"):
                name = "<b>Affinity group meeting</b><br>" + social["name"]
            else:
                name = social["name"]

            event = {
                "title": name,
                "start": start,
                "end": end,
                "location": "",
                "link": f"socials.html",
                "category": "time",
                "type": "Socials",
                "view": "day",
            }
            site_data["overall_calendar"].append(event)

            assert start < end, "Session start after session end"

            all_sessions.append(session)

    blocks = compute_schedule_blocks(all_sessions)

    # Compute start and end of tutorial blocks
    for block in blocks:
        min_start = min([t["start_time"] for t in block])
        max_end = max([t["end_time"] for t in block])

        event = {
            "title": f"Socials",
            "start": min_start,
            "end": max_end,
            "location": "",
            "link": f"socials.html",
            "category": "time",
            "type": "Socials",
            "view": "week",
        }
        site_data["overall_calendar"].append(event)


def build_schedule(overall_calendar: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    events = [
        copy.deepcopy(event)
        for event in overall_calendar
        if event["type"]
        in {
            "Plenary Sessions",
            "Tutorials",
            "Workshops",
            "QA Sessions",
            "Socials",
            "Sponsors",
            "Undergraduate Consortium",
            "Doctoral Consortium",
        }
    ]

    for event in events:
        event_type = event["type"]
        if event_type == "Plenary Sessions":
            event["classNames"] = ["calendar-event-plenary"]
            event["url"] = event["link"]
        elif event_type == "Tutorials":
            event["classNames"] = ["calendar-event-tutorial"]
            event["url"] = event["link"]
        elif event_type == "Workshops":
            event["classNames"] = ["calendar-event-workshops"]
            event["url"] = event["link"]
        elif event_type == "QA Sessions":
            event["classNames"] = ["calendar-event-qa"]
            event["url"] = event["link"]
        elif event_type == "Socials":
            event["classNames"] = ["calendar-event-socials"]
            event["url"] = event["link"]
        elif event_type == "Sponsors":
            event["classNames"] = ["calendar-event-sponsors"]
            event["url"] = event["link"]
        elif event_type == "Undergraduate Consortium":
            event["classNames"] = ["calendar-event-uc"]
            event["url"] = event["link"]
        elif event_type == "Doctoral Consortium":
            event["classNames"] = ["calendar-event-dc"]
            event["url"] = event["link"]
        else:
            event["classNames"] = ["calendar-event-other"]
            event["url"] = event["link"]

        event["classNames"].append("calendar-event")
    return events


def build_tutorial_schedule(
    overall_calendar: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    events = [
        copy.deepcopy(event)
        for event in overall_calendar
        if event["type"] in {"Tutorials"}
    ]

    for event in events:
        event["classNames"] = ["calendar-event-tutorial"]
        event["url"] = event["link"]
        event["classNames"].append("calendar-event")
    return events


def normalize_track_name(track_name: str) -> str:
    if track_name == "SRW":
        return "Student Research Workshop"
    elif track_name == "Demo":
        return "System Demonstrations"
    return track_name


def get_card_image_path_for_paper(paper_id: str, paper_images_path: str, default_image_path: str) -> str:
    file_name = f"{paper_images_path}/{paper_id}.png"
    dir_path = os.path.dirname(os.path.abspath(__file__))
    # get root path
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_file_name = os.path.join(root_path,file_name)
    if os.path.exists(abs_file_name):
        return f"{paper_images_path}/{paper_id}.png"
    else:
        return default_image_path


def build_papers(
    raw_papers: List[Dict[str, str]],
    paper_sessions: Dict[str, Any],
    paper_recs: Dict[str, List[str]],
    paper_images_path: str,
    default_image_path: str
) -> List[Paper]:
    """Builds the site_data["papers"].

    Each entry in the papers has the following fields:
    - UID: str
    - title: str
    - authors: str (separated by '|')
    - keywords: str (separated by '|')
    - track: str
    - paper_type: str (i.e., "Long", "Short", "SRW", "Demo")
    - pdf_url: str
    - demo_url: str

    """
    # build the lookup from (paper, slot) to zoom_link
    paper_id_to_link: Dict[str, str] = {}

    for session_id, session in paper_sessions.items():
        for paper_id in session["papers"]:
            assert paper_id not in paper_id_to_link, paper_id
            if session_id.startswith("z"):
                paper_id_to_link[paper_id] = session.get("zoom_link")
            elif session_id.startswith("g"):
                paper_id_to_link[
                    paper_id
                ] = "https://www.virtualchair.net/events/emnlp2020"

    # build the lookup from paper to slots
    sessions_for_paper: DefaultDict[str, List[SessionInfo]] = defaultdict(list)
    for session_name, session_info in paper_sessions.items():
        start_time = session_info["start_time"]
        end_time = session_info["end_time"]

        for paper_id in session_info["papers"]:

            #TODO  continue deal with it when we get session data
            # pass
            link = paper_id_to_link[paper_id]

            sessions_for_paper[paper_id].append(
                SessionInfo(
                    session_name=session_name,
                    start_time=start_time,
                    end_time=end_time,
                    link=link,
                )
            )

    papers = [
        Paper(
            id=item["UID"],
            forum=item["UID"],
            card_image_path=get_card_image_path_for_paper(
                item["UID"], paper_images_path, default_image_path
            ),
            presentation_id=item.get("presentation_id", None),
            presentation_id_intro=item.get("presentation_id_intro", None),
            content=PaperContent(
                title=item["title"],
                authors=extract_list_field(item, "authors"),
                keywords=extract_list_field(item, "keywords"),
                abstract=item["abstract"],
                tldr=item["abstract"][:250] + "...",
                pdf_url=item.get("pdf_url", "https://scholar.google.com/"),
                demo_url=item.get("demo_url", ""),
                material=item.get("material"),
                track=normalize_track_name(item.get("track", "")),
                paper_type=item.get("paper_type", ""),
                sessions=sessions_for_paper[item["UID"]],
                similar_paper_uids=paper_recs.get(item["UID"], [item["UID"]]),
                program=item["program"],
            ),
        )
        for item in raw_papers
    ]

    # throw warnings for missing information
    for paper in papers:
        if not paper.presentation_id and paper.content.program not in [
            "demo",
            "findings",
        ]:
            print(f"WARNING: presentation_id not set for {paper.id}")
        # if not paper.content.track:
        #     print(f"WARNING: track not set for {paper.id}")
        if paper.presentation_id and len(paper.content.sessions) != 1:
            print(
                f"WARNING: found {len(paper.content.sessions)} sessions for {paper.id}"
            )
        if not paper.content.similar_paper_uids:
            print(f"WARNING: empty similar_paper_uids for {paper.id}")

    return papers


def build_qa_sessions(
    raw_paper_sessions: Dict[str, Any]
) -> Tuple[List[QaSession], List[Tuple[str, str, str]]]:
    raw_subsessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for uid, subsession in raw_paper_sessions.items():
        overall_id = uid[:-1]
        raw_subsessions[overall_id].append(subsession)

    days = set()

    paper_sessions = []
    for uid, rs in raw_subsessions.items():
        number = uid[1:]
        if uid.startswith("z"):
            name = f"Zoom Q&A Session {number}"
        elif uid.startswith("g"):
            name = f"Gather Session {number}"
        else:
            raise Exception("Invalid session type")

        start_time = rs[0]["start_time"]
        end_time = rs[0]["end_time"]
        assert all(s["start_time"] == start_time for s in rs)
        assert all(s["end_time"] == end_time for s in rs)

        subsessions = []
        for s in rs:
            qa_subsession = QaSubSession(
                name=s["long_name"].split(":")[-1].strip(),
                link=s.get("zoom_link", "http://zoom.us"),
                # TODO  make qa_session.html pass
                papers=s["papers"],
                # papers=[],
            )
            subsessions.append(qa_subsession)

        qa_session = QaSession(
            uid=uid,
            name=name,
            start_time=start_time,
            end_time=end_time,
            subsessions=subsessions,
        )
        paper_sessions.append(qa_session)

        days.add(qa_session.day)

    qa_session_days = []
    for i, day in enumerate(sorted(days)):
        qa_session_days.append(
            (day.replace(" ", "").lower(), day, "active" if i == 0 else "")
        )

    return paper_sessions, qa_session_days


def build_tutorials(raw_tutorials: List[Dict[str, Any]]) -> List[Tutorial]:
    def build_tutorial_blocks(t: Dict[str, Any]) -> List[SessionInfo]:
        blocks = compute_schedule_blocks(t["sessions"])
        result = []
        for i, block in enumerate(blocks):
            min_start = min([t["start_time"] for t in block])
            max_end = max([t["end_time"] for t in block])

            assert all(s["zoom_link"] == block[0]["zoom_link"] for s in block)

            result.append(
                SessionInfo(
                    session_name=f"T-Live Session {i+1}",
                    start_time=min_start,
                    end_time=max_end,
                    link=block[0]["zoom_link"],
                )
            )
        return result

    return [
        Tutorial(
            id=item["UID"],
            title=item["title"],
            organizers=item["organizers"],
            abstract=item["abstract"],
            website=item.get("website", None),
            material=item.get("material", None),
            slides=item.get("slides", None),
            prerecorded=item.get("prerecorded", ""),
            rocketchat_channel=item.get("rocketchat_channel", ""),
            sessions=[
                TutorialSessionInfo(
                    session_name=session.get("name"),
                    start_time=session.get("start_time"),
                    end_time=session.get("end_time"),
                    hosts=session.get("hosts", ""),
                    livestream_id=session.get("livestream_id"),
                    zoom_link=session.get("zoom_link"),
                )
                for session in item.get("sessions")
            ],
            authors=[
                TutorialAuthorInfo(
                    author_name=author.get("name"),
                    author_description=author.get("description"),
                )
                for author in item.get("authors")
            ],
            blocks=build_tutorial_blocks(item),
            virtual_format_description=item["info"],
        )
        for item in raw_tutorials
    ]


def build_workshops(
    raw_workshops: List[Dict[str, Any]], raw_workshop_papers: List[Dict[str, Any]],
) -> List[Workshop]:
    def workshop_title(workshop_id):
        for wsh in raw_workshops:
            if wsh["UID"] == workshop_id:
                return wsh["title"]
        return ""

    def build_workshop_blocks(t: Dict[str, Any]) -> List[SessionInfo]:
        blocks = compute_schedule_blocks(t["sessions"], leeway=timedelta(hours=1))
        if len(blocks) == 0:
            return []

        result = []
        for i, block in enumerate(blocks):
            min_start = min([t["start_time"] for t in block])
            max_end = max([t["end_time"] for t in block])

            result.append(
                SessionInfo(
                    session_name=f"W-Live Session {i+1}",
                    start_time=min_start,
                    end_time=max_end,
                    link="",
                )
            )
        return result

    grouped_papers: DefaultDict[str, Any] = defaultdict(list)
    for paper in raw_workshop_papers:
        grouped_papers[paper["workshop"]].append(paper)

    ws_id_to_alias: Dict[str, str] = {w["UID"]: w["alias"] for w in raw_workshops}

    workshop_papers: DefaultDict[str, List[WorkshopPaper]] = defaultdict(list)
    for workshop_id, papers in grouped_papers.items():
        for item in papers:
            workshop_papers[workshop_id].append(
                WorkshopPaper(
                    id=item["UID"],
                    title=item["title"],
                    speakers=item["authors"],
                    presentation_id=item.get("presentation_id", None),
                    rocketchat_channel=f"paper-{ws_id_to_alias[workshop_id]}-{item['UID'].split('.')[-1]}",
                    content=PaperContent(
                        title=item["title"],
                        authors=extract_list_field(item, "authors"),
                        track=workshop_title(workshop_id),
                        paper_type="Workshop",
                        abstract=item.get("abstract"),
                        tldr=item["abstract"][:250] + "..."
                        if item["abstract"]
                        else None,
                        keywords=[],
                        pdf_url=item.get("pdf_url"),
                        demo_url=None,
                        sessions=[],
                        similar_paper_uids=[],
                        program="workshop",
                    ),
                )
            )

    workshops: List[Workshop] = [
        Workshop(
            id=item["UID"],
            title=item["title"],
            organizers=item["organizers"],
            abstract=item["abstract"],
            website=item["website"],
            livestream=item.get("livestream"),
            papers=workshop_papers[item["UID"]],
            schedule=item.get("schedule"),
            prerecorded_talks=item.get("prerecorded_talks"),
            rocketchat_channel=item["rocketchat_channel"],
            zoom_links=item.get("zoom_links", []),
            sessions=[
                SessionInfo(
                    session_name=session.get("name", ""),
                    start_time=session.get("start_time"),
                    end_time=session.get("end_time"),
                    link=session.get("zoom_link", ""),
                    hosts=session.get("hosts"),
                )
                for session in item.get("sessions")
            ],
            blocks=build_workshop_blocks(item),
        )
        for item in raw_workshops
    ]

    return workshops

def build_doctoral_consortium(raw_doctoral_consortiums: List[Dict[str, Any]]) -> List[DoctoralConsortium]:
    def build_doctoral_consortium_blocks(t: Dict[str, Any]) -> List[SessionInfo]:
        blocks = compute_schedule_blocks(t["sessions"])
        result = []
        for i, block in enumerate(blocks):
            min_start = min([t["start_time"] for t in block])
            max_end = max([t["end_time"] for t in block])

            assert all(s["zoom_link"] == block[0]["zoom_link"] for s in block)

            result.append(
                SessionInfo(
                    session_name=f"T-Live Session {i+1}",
                    start_time=min_start,
                    end_time=max_end,
                    link=block[0]["zoom_link"],
                )
            )
        return result

    return [
        DoctoralConsortium(
            id=item["UID"],
            title=item["title"],
            organizers=item["organizers"],
            abstract=item["abstract"],
            website=item.get("website", None),
            material=item.get("material", None),
            slides=item.get("slides", None),
            prerecorded=item.get("prerecorded", ""),
            rocketchat_channel=item.get("rocketchat_channel", ""),
            sessions=[
                SessionInfo(
                    session_name=session.get("name"),
                    start_time=session.get("start_time"),
                    end_time=session.get("end_time"),
                    hosts=session.get("hosts", ""),
                    link=session.get("zoom_link", ""),
                )
                for session in item.get("sessions")
            ],
            blocks=build_doctoral_consortium_blocks(item),
            virtual_format_description=item["info"],
        )
        for item in raw_doctoral_consortiums
    ]

def build_demonstrations(raw_demonstrations: List[Dict[str, Any]]) -> List[Demonstrations]:
    def build_demonstrations_blocks(t: Dict[str, Any]) -> List[SessionInfo]:
        blocks = compute_schedule_blocks(t["sessions"])
        result = []
        for i, block in enumerate(blocks):
            min_start = min([t["start_time"] for t in block])
            max_end = max([t["end_time"] for t in block])

            assert all(s["zoom_link"] == block[0]["zoom_link"] for s in block)

            result.append(
                SessionInfo(
                    session_name=f"T-Live Session {i+1}",
                    start_time=min_start,
                    end_time=max_end,
                    link=block[0]["zoom_link"],
                )
            )
        return result

    return [
        Demonstrations(
            id=item["UID"],
            title=item["title"],
            organizers=item["organizers"],
            abstract=item["abstract"],
            website=item.get("website", None),
            material=item.get("material", None),
            slides=item.get("slides", None),
            prerecorded=item.get("prerecorded", ""),
            rocketchat_channel=item.get("rocketchat_channel", ""),
            sessions=[
                SessionInfo(
                    session_name=session.get("name"),
                    start_time=session.get("start_time"),
                    end_time=session.get("end_time"),
                    hosts=session.get("hosts", ""),
                    livestream_id=session.get("livestream_id"),
                    zoom_link=session.get("zoom_link"),
                )
                for session in item.get("sessions")
            ],
            blocks=build_demonstrations_blocks(item),
            virtual_format_description=item["info"],
        )
        for item in raw_demonstrations
    ]

def build_socials(raw_socials: List[Dict[str, Any]]) -> List[SocialEvent]:
    return [
        SocialEvent(
            id=item["UID"],
            name=item["name"],
            description=item["description"],
            image=item.get("image"),
            location=item.get("location"),
            organizers=SocialEventOrganizers(
                members=item["organizers"]["members"],
                website=item["organizers"].get("website", ""),
            ),
            sessions=[
                SessionInfo(
                    session_name=session.get("name"),
                    start_time=session.get("start_time"),
                    end_time=session.get("end_time"),
                    link=session.get("link"),
                )
                for session in item["sessions"]
            ],
            rocketchat_channel=item.get("rocketchat_channel", ""),
            website=item.get("website", ""),
            zoom_link=item.get("zoom_link"),
        )
        for item in raw_socials
    ]


def build_sponsors(site_data, by_uid, display_time_format) -> None:
    def generate_schedule(schedule: List[Dict[str, Any]]) -> Dict[str, Any]:
        times: Dict[str, List[Any]] = defaultdict(list)

        for session in schedule:
            if session["start"] is None:
                continue

            start = session["start"].astimezone(pytz.timezone("GMT"))
            if session.get("end") is None:
                end = start + timedelta(hours=session["duration"])
            else:
                end = session["end"].astimezone(pytz.timezone("GMT"))
            day = start.strftime("%A, %b %d")
            start_time = start.strftime(display_time_format)
            end_time = end.strftime(display_time_format)
            time_string = "{} ({}-{} GMT)".format(day, start_time, end_time)

            times[day].append((time_string, session["label"]))
        return times

    by_uid["sponsors"] = {}

    for sponsor in site_data["sponsors"]:
        uid = "_".join(sponsor["name"].lower().split())
        sponsor["UID"] = uid
        by_uid["sponsors"][uid] = sponsor

    # Format the session start and end times
    for sponsor in by_uid["sponsors"].values():
        sponsor["zoom_times"] = generate_schedule(sponsor.get("schedule", []))
        sponsor["gather_times"] = generate_schedule(sponsor.get("gather_schedule", []))

        publications = sponsor.get("publications")
        if not publications:
            continue

        grouped_publications: Dict[str, List[Any]] = defaultdict(list)
        for paper_id in publications:
            if paper_id not in by_uid["papers"]: continue
            paper = by_uid["papers"][paper_id]
            grouped_publications[paper.content.paper_type].append(paper)

        sponsor["grouped_publications"] = grouped_publications

    # In the YAML, we just have a list of sponsors. We group them here by level
    sponsors_by_level: DefaultDict[str, List[Any]] = defaultdict(list)
    for sponsor in site_data["sponsors"]:
        if "level" in sponsor:
            sponsors_by_level[sponsor["level"]].append(sponsor)
        elif "levels" in sponsor:
            for level in sponsor["levels"]:
                sponsors_by_level[level].append(sponsor)

    site_data["sponsors_by_level"] = sponsors_by_level
    site_data["sponsor_levels"] = [
        "Diamond",
        "Platinum",
        "Gold",
        "Silver",
        "Bronze",
        "Supporter",
        "Publisher",
        "Diversity & Inclusion: Champion",
        "Diversity & Inclusion: In-Kind",
    ]

    assert all(lvl in site_data["sponsor_levels"] for lvl in sponsors_by_level)


def compute_schedule_blocks(
    events, leeway: Optional[timedelta] = None
) -> List[List[Dict[str, Any]]]:
    if leeway is None:
        leeway = timedelta()

    # Based on
    # https://stackoverflow.com/questions/54713564/how-to-find-gaps-given-a-number-of-start-and-end-datetime-objects
    if len(events) <= 1:
        return [events]

    # sort by start times
    events = sorted(events, key=lambda x: x["start_time"])

    # Start at the end of the first range
    now = events[0]["end_time"]

    blocks = []
    block: List[Dict[str, Any]] = []

    for pair in events:
        # if next start time is before current end time, keep going until we find a gap
        # if next start time is after current end time, found the first gap
        if pair["start_time"] - (now + leeway) > timedelta():
            blocks.append(block)
            block = [pair]
        else:
            block.append(pair)

        # need to advance "now" only if the next end time is past the current end time
        now = max(pair["end_time"], now)

    if len(block):
        blocks.append(block)

    return blocks
