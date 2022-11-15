"""
- Consultation(咨询项目类型)
    - Column:
        - avatar: "http://..../xx.png"
        - title: 环评
        - description: 规划环评，项目环评，后评价，跟踪评价
    - example：
        - 环评
        - 验收
        - 环保管家
        - 场地调查
        - 环保工程
        - 应急预案
        - 环境监理
        - 其他咨询
        - 萤火计划
- ConsultationProject(咨询项目内容)
    - Column:
        - title: relation to Consultation.title
        - content
"""
import time
import string
import nanoid
import sqlalchemy as sa
from db import Model


class Consultation(Model):
    __tablename__ = "consultation"
    __repr_attrs__ = ["title"]
    
    uid = sa.Column(
        sa.Text,
        primary_key=True,
        index=True,
        default=lambda: nanoid.generate(string.ascii_letters + string.digits, 32),
    )
    avatar = sa.Column(sa.String(512), nullable=False)
    title = sa.Column(sa.String(128), nullable=True)
    description = sa.Column(sa.String(512), nullable=True)
    


class ConsultationContent(Model):
    __tablename__ = "consultation_content"
    __repr_attrs__ = ["title"]

    uid = sa.Column(
        sa.Text,
        primary_key=True,
        index=True,
        default=lambda: nanoid.generate(string.ascii_letters + string.digits, 32),
    )
    content = sa.Column(sa.Text, nullable=True)
