def command(host: str = "0.0.0.0", port: int = 9000, reload: bool = True) -> None:
    from pathlib import Path
    from wsgi import app

    app.run(host=host, port=port, debug=True)

command.requires_db = False