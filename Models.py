
from main import db

# 定义数据模型, 设置表格中各个字段的数据类型
class User(db.Model):
    id = db.Column(db.Integer,primary_key=True,autoincrement=True)
    email = db.Column(db.String(200),nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=True)
    __tablename__ = 'user'
    def __init__(self, email, password):
        self.email = email
        self.password = password

