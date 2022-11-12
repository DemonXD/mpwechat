import configparser
from typing import Optional

from flask import Response
from flask_apscheduler import APScheduler
from flask_session import Session

from apps import apps
from conf import settings
from custom import CusFlask
from exception_handlers import logical_exception_handler


def patch_pydantic_datetime_serializer():
    """
    pydantic.json.ENCODERS_BY_TYPE 没有提供自定义的机制，我们希望自定义 datetime 的序列化格式，
    因此使用这种比较 dirty 的方式进行 hack。
    """
    import datetime

    from pydantic.json import ENCODERS_BY_TYPE

    ENCODERS_BY_TYPE[datetime.date] = lambda o: o.strftime("%Y-%m-%d")
    ENCODERS_BY_TYPE[datetime.time] = lambda o: o.strftime("%H:%M:%S")
    ENCODERS_BY_TYPE[datetime.datetime] = lambda o: o.strftime("%Y-%m-%d %H:%M:%S")


# cors
def after_request(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

_app_instance: Optional[CusFlask] = None


def get_application() -> CusFlask:
    import logging.config
    import os
    import sys
    from pathlib import Path

    if isinstance(settings.LOG_CONFIG_FILE, str):
        try:
            logging.config.fileConfig(settings.LOG_CONFIG_FILE)
        except FileNotFoundError:
            cp = configparser.ConfigParser()
            cp.read(settings.LOG_CONFIG_FILE)
            log_dir = cp["DEFAULT"]["LOG_DIR"].strip("'")
            if not (settings.BASE_DIR / log_dir).exists():
                (settings.BASE_DIR / Path(log_dir)).mkdir()
            logging.config.fileConfig(settings.LOG_CONFIG_FILE)

    global _app_instance
    if _app_instance is not None:
        return _app_instance

    sys.path.insert(0, os.getcwd())
    patch_pydantic_datetime_serializer()

    app = CusFlask(__name__)
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()
    Session(app)

    apps.populate(settings.INSTALLED_APPS, flaskapp=app, settings=settings)

    for app_config in apps.app_configs.values():
        router = app_config.get_router()
        if router:
            app.register_blueprint(router)

    app.after_request(after_request)
    app.register_error_handler(400, logical_exception_handler)
    _app_instance = app
    return _app_instance
