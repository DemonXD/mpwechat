import threading
from typing import Dict, List

from flask import Flask

from conf import Settings

from .config import AppConfig


class Apps:
    """
    仿照 Django 实现了一个简化版的 App Registry
    """

    app_configs: Dict[str, AppConfig]
    ready: bool
    flaskapp: Flask

    _lock: threading.RLock
    _loading: bool

    def __init__(self):
        self.app_configs = {}
        self.ready = False
        self.Flask = None

        self._lock = threading.RLock()
        self._loading = False

    def populate(self, installed_apps: List[str], flaskapp: Flask, settings: Settings) -> None:
        if self.ready:
            return

        # populate() might be called by two threads in parallel on servers
        # that create threads before initializing the WSGI callable.
        with self._lock:
            if self.ready:
                return

            # An RLock prevents other threads from entering this section. The
            # compare and set operation below is atomic.
            if self._loading:
                # Prevent reentrant calls to avoid running AppConfig.ready()
                # methods twice.
                raise RuntimeError("populate() isn't reentrant")
            self._loading = True

            # 加载所有 app
            for entry in installed_apps:
                app_config: AppConfig = AppConfig.create(entry)
                self.app_configs[app_config.name] = app_config

            # 预加载所有 models
            self._load_models(settings)

        self.ready = True
        self.flaskapp = flaskapp

        self._ready(flaskapp=flaskapp, settings=settings)

    def _load_models(self, settings: Settings) -> None:
        from importlib import import_module

        for app_label, app_config in self.app_configs.items():
            models_module_name = f"{app_config.module.__name__}.models"
            try:
                import_module(models_module_name)
            except ModuleNotFoundError as e:
                if e.name == models_module_name:
                    print(f"App has no models module: {app_config.module}")
                else:
                    raise

    def _ready(self, flaskapp: Flask, settings: Settings) -> None:
        for app_label, app_config in self.app_configs.items():
            app_config.ready(flaskapp=flaskapp, settings=settings)


apps = Apps()
