"""
- ProjectAnnouncement(项目公示)
    - title: 泰州市...项目竣工公示
    - description: content[:50]
    - content:
    - author: default = 'company'
    - published_time: 
"""
import time
import string
import nanoid
import sqlalchemy as sa
from db import Model


class Announcement(Model):
    __tablename__ = "announcement"
    __repr_attrs__ = ["title", "description", "author", "published_time"]
    
    uid = sa.Column(
        sa.Text,
        primary_key=True,
        index=True,
        default=lambda: nanoid.generate(string.ascii_letters + string.digits, 32),
    )
    title = sa.Column(sa.String(256), nullable=False)
    description = sa.Column(sa.String(1024), nullable=True)
    content = sa.Column(sa.Text, nullable=True)
    author = sa.Column(sa.String(64), nullable=True)
    published_time = sa.Column(sa.BigInteger, nullable=False, default=lambda: int(time.time()))
