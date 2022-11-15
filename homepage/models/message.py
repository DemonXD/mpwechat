"""
- message(留言)
    - nickname
    - phone
    - email
    - address
    - content
"""
import time
import string
import nanoid
import sqlalchemy as sa
from db import Model


class Message(Model):
    __tablename__ = "message"
    __repr_attrs__ = ["nickname", "phone", "email", "content"]
    
    uid = sa.Column(
        sa.Text,
        primary_key=True,
        index=True,
        default=lambda: nanoid.generate(string.ascii_letters + string.digits, 32),
    )
    nickname = sa.Column(sa.String(64), nullable=False)
    phone = sa.Column(sa.String(16), nullable=True)
    email = sa.Column(sa.String(128), nullable=True)
    address = sa.Column(sa.String(512), nullable=True)
    content = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.BigInteger, nullable=False, default=lambda: int(time.time()))
