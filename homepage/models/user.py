"""
- User
    - name
    - password
    - created
    - modified
"""
import string
import nanoid
import sqlalchemy as sa
from db import Model


class User(Model):
    __tablename__ = "user"
    __repr_attrs__ = ["username"]
    
    uid = sa.Column(
        sa.Text,
        primary_key=True,
        index=True,
        default=lambda: nanoid.generate(string.ascii_letters + string.digits, 32),
    )
    username = sa.Column(sa.String(32), primary_key=True)
    password = sa.Column(sa.String(128))
