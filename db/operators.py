from typing import Union

from sqlalchemy import Column, and_, extract, func, not_, text  # noqa: F401
from sqlalchemy.sql.elements import BooleanClauseList

# from fastframe.fastapp.utils.data import DateTimeRange
from utils import timezone


def region_in(column: Column, code: str) -> Union[str, bool]:
    if code[2:] == "0000":
        return column.startswith(code[:2])

    elif code[4:] == "00":
        return column.startswith(code[:4])
    else:
        return column == code


def is_today(column: Column, value: bool) -> bool:
    today = timezone.now().date()
    expr = func.date(column) == today

    if value is True:
        return expr
    elif value is False:
        return not_(expr)
    else:
        raise ValueError('value for "is_today" operator must be True or False')


def is_this_month(column: Column, value: bool) -> BooleanClauseList:
    now = timezone.now().date()
    year, month = now.year, now.month
    expr = and_(extract("year", column) == year, extract("month", column) == month)

    if value is True:
        return expr
    elif value is False:
        return not_(expr)
    else:
        raise ValueError('value for "is_this_month" operator must be True or False')


# def datetime_range(column: Column, value: DateTimeRange):
#     if not isinstance(value, DateTimeRange):
#         raise ValueError('value for "datetime_range" operator must be DateTimeRange type')

#     if value.begin and value.end:
#         return and_(column >= value.begin, column <= value.end)
#     elif value.begin and not value.end:
#         return column >= value.begin
#     elif not value.begin and value.end:
#         return column <= value.end
#     else:
#         # XXX 是否有更好的写法？
#         return text("1=1")
