import functools
from datetime import datetime, tzinfo
from typing import Optional

import pytz


@functools.lru_cache()
def get_default_timezone() -> tzinfo:
    # 我们短期内没有国际化的需求，不需要处理时区问题，因此我们总是使用北京时区
    return pytz.timezone("Asia/Shanghai")


def now() -> datetime:
    # Django 的代码中使用 datetime.utcnow(tzinfo=pytz.utc)，并注释说比用 now(tz=utc) 快 24%
    # 我们实测：
    # >>> tz = pytz.timezone("Asia/Shanghai")
    # >>> timeit datetime.now(tz=tz)
    # 5.38 µs ± 432 ns per loop (mean ± std. dev. of 7 runs, 100000 loops each)
    # >>> timeit datetime.utcnow().replace(tzinfo=pytz.utc)
    # 2.25 µs ± 237 ns per loop (mean ± std. dev. of 7 runs, 1000000 loops each)
    # 后者快了一倍多，但后者返回的时间是 utc 时间，如果某些处理过程不支持时区（如
    # 某些库内置的 datetime 序列化代码，某些 ORM 等），则实际保存的时间可能发生
    # 时区错位。因此我们使用前者。
    return datetime.now(get_default_timezone())


# 以下代码直接摘自 Django 源码，将 get_current_timezone() 改为 get_default_timezone()


def is_aware(value: datetime) -> bool:
    """
    Determine if a given datetime.datetime is aware.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value: datetime) -> bool:
    """
    Determine if a given datetime.datetime is naive.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None


def make_aware(value: datetime, timezone: tzinfo = None, is_dst: Optional[bool] = None) -> datetime:
    """Make a naive datetime.datetime in a given time zone aware."""
    if timezone is None:
        timezone = get_default_timezone()
    if hasattr(timezone, "localize"):
        # This method is available for pytz time zones.
        return timezone.localize(value, is_dst=is_dst)  # type: ignore[attr-defined]
    else:
        # Check that we won't overwrite the timezone of an aware datetime.
        if is_aware(value):
            raise ValueError("make_aware expects a naive datetime, got %s" % value)
        # This may be wrong around DST changes!
        return value.replace(tzinfo=timezone)


def make_naive(value: datetime, timezone: tzinfo = None) -> datetime:
    """Make an aware datetime.datetime naive in a given time zone."""
    if timezone is None:
        timezone = get_default_timezone()
    # Emulate the behavior of astimezone() on Python < 3.6.
    if is_naive(value):
        raise ValueError("make_naive() cannot be applied to a naive datetime")
    return value.astimezone(timezone).replace(tzinfo=None)
