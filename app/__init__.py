import os
from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory

from . import db

# Il front-end React compilato (frontend/dist). In Docker è copiato in /srv/frontend/dist; sovrascrivibile con FRONTEND_DIR.
DEFAULT_FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def create_app(data_dir: str | None = None, frontend_dir: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    data = Path(data_dir or os.environ.get("DATA_DIR", "data"))
    app.config.update(
        DATA_DIR=data,
        DB_PATH=data / "bollette.db",
        PDF_DIR=data / "pdf",
        FRONTEND_DIR=Path(frontend_dir or os.environ.get("FRONTEND_DIR", DEFAULT_FRONTEND)),
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

    from .api import bp as api_bp
    from .api import offers as api_offers

    app.register_blueprint(api_bp)

    @app.get("/health")
    def health():
        """Per healthcheck del container: nessuna query, risponde se l'app è su."""
        return "ok"

    # URL storico usato dagli script di aggiornamento già installati (cron sul NAS): resta valido
    app.add_url_rule("/offers/import-arera", "legacy_import_arera", lambda: api_offers.import_arera(), methods=["POST"])

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        """File statici del front-end; ogni altro percorso è una pagina dell'app React (routing lato client)."""
        root: Path = app.config["FRONTEND_DIR"]
        if path.startswith("api/"):
            return jsonify(error="Non trovato."), 404
        if not (root / "index.html").is_file():
            abort(503, "Front-end non compilato: esegui `npm run build` in frontend/ (o usa `npm run dev`).")
        target = (root / path).resolve()
        if path and target.is_file() and root.resolve() in target.parents:
            return send_from_directory(root, path, max_age=31536000 if path.startswith("assets/") else 0)
        return send_from_directory(root, "index.html", max_age=0)

    return app
