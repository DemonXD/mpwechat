"""
- CompanyProfile(公司简介)
    - sectionName
    - content
"""

import time
import string
import nanoid
import sqlalchemy as sa
from db import Model


class CompanyProfile(Model):
    __tablename__ = "profile"
    __repr_attrs__ = ["section_name"]
    
    uid = sa.Column(
        sa.Text,
        primary_key=True,
        index=True,
        default=lambda: nanoid.generate(string.ascii_letters + string.digits, 32),
    )
    section_name = sa.Column(sa.String(64), nullable=False)
    content = sa.Column(sa.Text, nullable=True)
