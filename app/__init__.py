import os
from pathlib import Path

from flask import Flask

from . import db


def create_app(data_dir: str | None = None) -> Flask:
    app = Flask(__name__)
    data = Path(data_dir or os.environ.get("DATA_DIR", "data"))
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATA_DIR=data,
        DB_PATH=data / "bollette.db",
        PDF_DIR=data / "pdf",
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,
    )
    try:
        app.config["PDF_DIR"].mkdir(parents=True, exist_ok=True)
        db.init_app(app)
    except PermissionError as e:
        raise RuntimeError(
            f"Cartella dati non scrivibile: {data}. Dai i permessi all'utente del processo "
            "(in Docker di default uid 1000, gid 100: `chown 1000:100 <cartella>`) oppure imposta `user:` nel compose."
        ) from e

    from .routes import bills, compare, home, offers, profiles, proposal, settings, verdict

    for module in (home, bills, offers, compare, proposal, settings, profiles, verdict):
        app.register_blueprint(module.bp)

    @app.context_processor
    def _profiles():
        return {"profiles": db.list_profiles(), "profile": db.current_profile()}

    return app
