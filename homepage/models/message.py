"""
- message(留言)
    - nickname
    - phone
    - email
    - address
    - content
"""
import string
import nanoid
import sqlalchemy as sa
from db import Model


class Message(Model):
    __tablename__ = "Message"
    __repr_attrs__ = [""]
    
    uid = sa.Column(
        sa.Text,
        primary_key=True,
        default=lambda: nanoid.generate(string.ascii_letters + string.digits, 32),
    )
    nickname = sa.Column(sa.String(64), )