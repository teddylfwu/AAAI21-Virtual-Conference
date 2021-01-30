import sys
sys.path.insert(0, "/var/www/AAAI21-Virtual-Conference")
sys.path.insert(0, "/home/ubuntu/anaconda3/lib/python3.8/site-packages")
from main import app as application
from main import site_data, by_uid
from miniconf.load_site_data import load_site_data
load_site_data("/var/www/AAAI21-Virtual-Conference/sitedata", site_data, by_uid)