import json
import configparser
import jinja2
from typing import Optional, Type, Union, List

from pathlib import Path
from flask import Response, Flask
from flask.templating import Environment
from flask.globals import request, session, g
from flask.helpers import get_flashed_messages
from flask.typing import ResponseReturnValue
from flask_apscheduler import APScheduler
from flask_session import Session

from apps import apps
from conf import settings
from responses.api import APIResponse
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


class CusFlask(Flask):
    def make_response(self, rv: Union[ResponseReturnValue, Type[APIResponse]]) -> Response:
        if issubclass(type(rv), APIResponse):
            body, status_code = rv.content # type: ignore [union-attr]
            return Response(json.dumps(body), status=status_code, content_type="application/json")
        return super().make_response(rv)

    def create_jinja_environment(self) -> Environment:
        """Create the Jinja environment based on :attr:`jinja_options`
        and the various Jinja-related methods of the app. Changing
        :attr:`jinja_options` after this will have no effect. Also adds
        Flask-related globals and filters to the environment.

        .. versionchanged:: 0.11
           ``Environment.auto_reload`` set in accordance with
           ``TEMPLATES_AUTO_RELOAD`` configuration option.

        .. versionadded:: 0.5
        """
        options = dict(self.jinja_options)

        if "autoescape" not in options:
            options["autoescape"] = self.select_jinja_autoescape

        if "auto_reload" not in options:
            auto_reload = self.config["TEMPLATES_AUTO_RELOAD"]

            if auto_reload is None:
                auto_reload = self.debug

            options["auto_reload"] = auto_reload

        from apps import apps

        loaders: List[jinja2.BaseLoader] = []
        # 默认添加 ${PWD}/templates/ 目录
        loaders.append(jinja2.FileSystemLoader("templates"))
        # 添加所有 installed apps 的 templates 目录
        for app in apps.app_configs.values():
            if Path(f"{app.module.__name__}/templates").exists():
                loaders.append(jinja2.PackageLoader(f"{app.module.__name__}", "templates"))


        rv = self.jinja_environment(self, **options)
        rv.loader = jinja2.ChoiceLoader(loaders)
        rv.globals.update(
            url_for=self.url_for,
            get_flashed_messages=get_flashed_messages,
            config=self.config,
            # request, session and g are normally added with the
            # context processor for efficiency reasons but for imported
            # templates we also want the proxies in there.
            request=request,
            session=session,
            g=g,
        )
        rv.policies["json.dumps_function"] = self.json.dumps
        return rv


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
