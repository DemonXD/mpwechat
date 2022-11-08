import functools
import inspect
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Optional, Dict

from sqlalchemy.orm import Session, sessionmaker


class FlaskAppSession(Session):
    """
    在 2.0-style 中, 如果有 Nested Transaction, session.commit() 总是会 commit 最外层的事务, 
    session.rollback() 总是会 rollback 最外层的事务。如果需要 commit/rollback 当前的 nested
    事务, 需要使用 transaction.commit()/rollback()。

    见文档: https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#nested-transaction

    我们希望这两个函数可以实现类似 1.0-style 的逻辑, 因此对这两个方法进行封装。该逻辑实际上也参考了
    Django 的实现思路。Django 默认为 AUTO COMMIT 模式, 但在事务中时会关闭 AUTO COMMIT。
    我们的 AUTO COMMIT 逻辑实际上是在 CRUD 方法中手动执行的, 而我们的嵌套事务则与 Django 的事务等同。
    """

    def commit(self):
        """
        如果当前在嵌套事务中, 我们直接忽略 commit() 操作, 否则该嵌套事务会立刻被关闭, 
        后续操作会在父事务中进行, 这往往不是预期的。嵌套事务应当由 begin_nested()
        自行关闭。
        """
        if self.in_nested_transaction():
            # 注意, 这里需要 flush()
            # 对于新建的对象, 例如 foo = FooModel(), foo.save(), 如果不 flush, 那么
            # 有默认值的字段（以及由数据库自动维护的 id 字段）都不会生成, 导致后面的代码读取不到。
            super().flush()
            return
        return super().commit()

    def rollback(self):
        if self.in_nested_transaction():
            print("WARNING: 在 nested session 中调用 rollback() 将不执行任何操作。")
            return
        return super().commit()


def _create_sessionmaker(params: Optional[Dict[str, str]] = None) -> sessionmaker:
    """
    params: like, {"pg1": "postgresql+psycopg2://....."}
    """
    from .engine import _engines_cache, _create_engine
    bind_engine = _engines_cache["default"]

    if params is not None:
        for key, val in params.items():
            _engines_cache[key] = _create_engine(val)
            bind_engine = _engines_cache[key]

    return sessionmaker(
        class_=FlaskAppSession,
        bind=bind_engine,
        future=True,
    )


@dataclass
class _DBStateInContext:
    session_args: dict
    session: Optional[Session] = None
    custom_session_params: Dict[str, str] = None


_dbstate: ContextVar[Optional[_DBStateInContext]] = ContextVar("_dbstate", default=None)


class DBMeta(type):
    @property
    def session(self) -> Session:
        dbstate = _dbstate.get()
        if dbstate is None:
            raise RuntimeError("dbstate 未初始化。请在 `with DB():` 代码块中使用数据库。")

        if dbstate.session is None:
            if dbstate.custom_session_params != {}:
                dbstate.session = _create_sessionmaker(dbstate.custom_session_params)(**dbstate.session_args)
            else:
                dbstate.session = _create_sessionmaker()(**dbstate.session_args)

        return dbstate.session


class DB(metaclass=DBMeta):
    def __init__(self, session_args: Optional[dict] = None, custom_session_params: Optional[dict] = None):
        self.custom_session_params: Optional[dict] = custom_session_params or {}
        self.session_args: Optional[dict] = session_args or {}
        self.token: Optional[Token] = None

    def __enter__(self):
        self.token = _dbstate.set(
            _DBStateInContext(
                session_args=self.session_args,
                custom_session_params=self.custom_session_params
            )
        )
        return type(self)

    def __exit__(self, exc_type, exc_value, traceback):
        dbstate = _dbstate.get()

        if dbstate.session is not None:
            """
            如果 session 为 None, 表示没有代码使用过数据库, 无需进行清理。

            我们使用 commit as you go 的思想, 每次写操作之后, 应用都应该自己 commit, 
            因此, 理论上这里无需进行 commit 或 rollback 的操作。但由于现在大量的代码还
            没有修改, 不会自动 commit, 所以这里需要 commit() 一下。另外需要注意的是, 
            raise ResponseException 会被提前处理掉, 不会走到这里, 因此此类事务不会被回滚。
            """
            if exc_type is not None:
                dbstate.session.rollback()
            else:
                dbstate.session.commit()

        _dbstate.reset(self.token)
        self.token = None


def atomic(func):
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with DB.session.begin_nested():
                return await func(*args, **kwargs)

        return wrapper
    else:

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with DB.session.begin_nested():
                return func(*args, **kwargs)

        return wrapper
