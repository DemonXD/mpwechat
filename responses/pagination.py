import math
from typing import List, Tuple

from sqlalchemy.orm import Query

from db.model import Model


def get_pagination(query: Query, page: int = 1, page_size: int = 10) -> Tuple[List[Model], dict]:
    if page <= 0:
        raise AttributeError("page needs to be >= 1")
    if page_size <= 0:
        raise AttributeError("page_size needs to be >= 1")

    items = query.limit(page_size).offset((page - 1) * page_size).all()
    total = query.order_by(None).count()

    pagination = dict(
        total=total,
        page=page,
        page_size=page_size,
        last_page=int(math.ceil(total / float(page_size))),
    )

    return (items, pagination)
