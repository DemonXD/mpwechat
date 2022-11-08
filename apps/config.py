import os
from pathlib import Path
from types import ModuleType
from typing import List, Optional, Type

from flask import Blueprint, Flask

from conf import Settings


class AppConfig:
    name: str
    module: ModuleType
    path: Path
    config_files: List[Path]
    # 一些 flaskapp 内置的应用没有 router，不需要提醒
    warn_missing_router: bool

    def __init__(self, app_name: str, app_module: ModuleType):
        self.name = app_name
        self.module = app_module

        if not hasattr(self, "path"):
            self.path = self._path_from_module(app_module)

        if not hasattr(self, "config_files"):
            self.config_files = []

        if not hasattr(self, "warn_missing_router"):
            self.warn_missing_router = True

    def ready(self, flaskapp: Flask, settings: Settings) -> None:
        """
        各应用可以重载此方法，做一些额外的设置。
        """
        return

    def _path_from_module(self, module):
        """Attempt to determine app's filesystem path from its module."""
        # This method is copied from django/apps/config.py
        # See #21874 for extended discussion of the behavior of this method in
        # various cases.
        # Convert paths to list because Python's _NamespacePath doesn't support
        # indexing.
        paths = list(getattr(module, "__path__", []))

        if len(paths) != 1:
            filename = getattr(module, "__file__", None)
            if filename is not None:
                paths = [os.path.dirname(filename)]
            else:
                # For unknown reasons, sometimes the list returned by __path__
                # contains duplicates that must be removed (#25246).
                paths = list(set(paths))

        if len(paths) > 1:
            raise RuntimeError(
                "The app module %r has multiple filesystem locations (%r); "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute." % (module, paths)
            )
        elif not paths:
            raise RuntimeError(
                "The app module %r has no filesystem location, "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute." % module
            )

        return Path(paths[0])

    def get_router(self) -> Optional[Blueprint]:
        from importlib import import_module

        try:
            module = import_module(f"{self.module.__name__}.router")
            if not hasattr(module, "router"):
                raise RuntimeError(f"应用的 router 模块中没有 router 属性: {self.module.__name__}.router")
            return getattr(module, "router")
        except ModuleNotFoundError as e:
            if e.name == f"{self.module.__name__}.router":
                if self.warn_missing_router:
                    print(f"应用没有 router 模块，将忽略: {self.module.__name__}.router")
            else:
                raise
        return None

    def has_dir(self, name: str) -> bool:
        """
        返回该应用的包目录下是否有指定的子目录
        """
        return (self.path / name).is_dir()

    def has_file(self, name: str) -> bool:
        """
        返回该应用的包目录下是否有指定的文件
        """
        return (self.path / name).is_file()

    @classmethod
    def create(cls: Type["AppConfig"], entry: str) -> "AppConfig":
        """
        entry 的写法: someapp.SomeAppConfig
        """
        from importlib import import_module

        mod_path, _, cls_name = entry.rpartition(".")
        module = import_module(mod_path)
        cls = getattr(module, cls_name)
        return cls(mod_path, module)
