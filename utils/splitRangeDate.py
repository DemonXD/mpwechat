import datetime
from typing import List

from dateutil.parser import parse


def getRangefDatetime(datefrom: str, dateto: str) -> List[datetime.datetime]:
    """[summary]

    Args:
        datefrom ([str]): [时间字符串]
        dateto ([str]): [时间字符串]

    return:
        List[datetime.datetime...]
    """
    dayto = parse(dateto)
    dayfrom = parse(datefrom)
    numdays = dayto.day - dayfrom.day
    date_list = [dayto - datetime.timedelta(days=x) for x in range(numdays + 1)]
    return date_list
