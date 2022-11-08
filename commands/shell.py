import typer


def command():
    import pkg_resources
    from IPython import start_ipython  # type: ignore[import]

    from conf import settings
    from db import DB

    user_ns = {}
    banner = [
        typer.style(
            f'Fastframe Flaskapp Application Shell',
            fg=typer.colors.MAGENTA,
        )
    ]

    if not settings.INSTALLED_APPS:
        banner.append(typer.style("No installed apps.", fg=typer.colors.RED))
    else:
        banner.append(
            "Installed Apps: " + ", ".join([typer.style(app, fg=typer.colors.GREEN) for app in settings.INSTALLED_APPS])
        )

    banner.append("")
    user_ns["DB"] = DB

    banner.append(
        "Auto populated vars: " + ", ".join([typer.style(var, fg=typer.colors.GREEN) for var in user_ns.keys()])
    )

    for message in banner:
        typer.echo(message)

    start_ipython(argv=[], display_banner=False, user_ns=user_ns)
