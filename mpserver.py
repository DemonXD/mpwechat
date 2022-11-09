import functools
import string
from importlib import import_module
from pathlib import Path
from typing import Any

import typer

from application import get_application

get_application()
cli = typer.Typer()


def print_error(message: str) -> Any:
    typer.echo(typer.style(message, fg=typer.colors.RED), err=True)


def print_warning(message: str) -> Any:
    typer.echo(typer.style(message, fg=typer.colors.YELLOW), err=True)


def print_success(message: str) -> Any:
    typer.echo(typer.style(message, fg=typer.colors.GREEN))


def _with_db(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from db import DB

        with DB():
            func(*args, **kwargs)

    return wrapper


def _load_commands_from_path(pkg: str, path: Path) -> None:
    if not path.is_dir():
        return

    for filepath in path.glob("*.py"):
        file = filepath.name
        # 只有以英文字母开头的文件才注册命令, 其他文件忽略(如 `.`, `_` 等开头的文件)
        if file[0] not in string.ascii_letters:
            continue
        command_name = file[:-3]
        try:
            module = import_module(f"{pkg}.{command_name}")
            if not hasattr(module, "command"):
                typer.echo(
                    typer.style(
                        f"Warning: {pkg}.{command_name} 没有定义 command() 函数",
                        fg=typer.colors.RED,
                    )
                )
            else:
                command_func = getattr(module, "command")
                if getattr(command_func, "requires_db", True):
                    """
                    所有 command 默认用 with DB(): ... 包住, 一些命令不需要 DB 的, 
                    或者自行管理 DB 的(如 migrate), 可以为 command 添加 requires_db = False: 

                    def command(...):
                        ...

                    command.requires_db = False
                    """
                    command_func = _with_db(command_func)
                cli.command(command_name)(command_func)
        except ModuleNotFoundError as e:
            typer.echo(e)
            pass

def populate_application_commands():
    from apps import apps
    # _load_commands_from_path("fastframe.fastapp.commands", Path(__file__).parent)
    _load_commands_from_path("commands", Path(__file__).parent / "commands")

    for app in apps.app_configs.values():
        _load_commands_from_path(f"{app.module.__name__}.commands", app.path / "commands")


populate_application_commands()

if __name__ == "__main__":
    cli()
