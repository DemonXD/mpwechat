import os
import json
import jinja2
from pathlib import Path
from typing import Union, Type, List
from flask import Response, Flask
from flask.templating import Environment
from flask.globals import request, session, g
from flask.helpers import get_flashed_messages, send_from_directory
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import NotFound
from responses.api import APIResponse


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

    # This class inherit from the main Flask application object and
    # override few methods to allow flask to support having multiple folders
    # serving static content.
    def _get_static_folder(self):
        if self._static_folder is not None:
            return [os.path.join(self.root_path, folder)
                    for folder in self._static_folder]
    def _set_static_folder(self, value):
        folders = value
        if isinstance(folders, (str, )):
            folders = [value]
        self._static_folder = folders
    static_folder = property(_get_static_folder, _set_static_folder)
    del _get_static_folder, _set_static_folder
 
    # Use the last entry in the list of static folder as it should be what
    # contains most of the files
    def _get_static_url_path(self):
        if self._static_url_path is not None:
            return self._static_url_path
        if self.static_folder is not None:
            return '/' + os.path.basename(self.static_folder[-1])
    def _set_static_url_path(self, value):
        self._static_url_path = value
    static_url_path = property(_get_static_url_path, _set_static_url_path)
    del _get_static_url_path, _set_static_url_path
 
 
    def send_static_file(self, filename):
        """Function used internally to send static files from the static
        folder to the browser.
 
        .. versionadded:: 0.5
        """
        if not self.has_static_folder:
            raise RuntimeError('No static folder for this object')
 
        # Ensure get_send_file_max_age is called in all cases.
        # Here, we ensure get_send_file_max_age is called for Blueprints.
        cache_timeout = self.get_send_file_max_age(filename)
 
        folders = self.static_folder
        if isinstance(self.static_folder, (str, )):
            folders = [self.static_folder]
 
        for directory in folders:
            try:
                return send_from_directory(
                    directory, filename, cache_timeout=cache_timeout)
            except NotFound:
                pass
        raise NotFound()