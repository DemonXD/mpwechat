from typing import Union, Dict
from sqlalchemy.engine import Engine, create_engine

from conf import settings
from conf.exceptions import ImproperlyConfigured

_engines_cache = {
    "default": None
}

def _create_engine(dsn):
    if dsn.startswith("sqlite"):
        execution_options: dict = {
            "isolation_level": "SERIALIZABLE",
        }
    else:
        execution_options: dict = {
            "isolation_level": "READ COMMITTED",
        }

    engine: Engine = create_engine(
        dsn,
        echo=settings.DEBUG_DB,
        pool_pre_ping=True,
        execution_options=execution_options,
        future=True,
    )

    return engine

def init_engine():
    # 这里在载入数据库配置文件的时候就排除了None的可能性
    # 所以这里传入的值为设置的dsn或者sqlite://（内存）
    dsn: Union[str, Dict[str, str]] = settings.DATABASE

    if isinstance(dsn, str):
        _engines_cache["default"] = _create_engine(dsn)
    
    if isinstance(dsn, dict):
        if "default" not in dsn.keys():
            raise ImproperlyConfigured("default not in DATABASES")

        for key, val in dsn.items():
            _engines_cache[key] = _create_engine(val)

init_engine()

default_engine = _engines_cache["default"]
