from flask import jsonify, request

from .. import db
from ..glossary import HELP
from ..services import extraction
from . import ApiError, bp, msg, storage

MAX_NAME = 60


def _name() -> str:
    name = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if not name or len(name) > MAX_NAME:
        raise ApiError(f"Il nome è obbligatorio (massimo {MAX_NAME} caratteri).")
    return name


def _profiles() -> list[dict]:
    counts = {r["profile_id"]: r["n"] for r in db.get_db().execute("SELECT profile_id, count(*) AS n FROM bills GROUP BY profile_id")}
    return [{**p, "bills": counts.get(p["id"], 0)} for p in db.list_profiles()]


@bp.get("/bootstrap")
def bootstrap():
    """Tutto ciò che serve all'avvio: profili, profilo attivo, spiegazioni dei tastini (i)."""
    return jsonify(profiles=_profiles(), profile=db.current_profile(), help=HELP, can_extract=extraction.available())


@bp.get("/profiles")
def profiles():
    return jsonify(profiles=_profiles(), profile=db.current_profile())


@bp.post("/profiles")
def create_profile():
    name = _name()
    here = db.current_profile()  # località e potenza di partenza: quelle del profilo attivo
    pid = db.add_profile(name, here["region"], here["province"], here["comune"], here["default_power_kw"])
    return jsonify(id=pid, messages=[msg("info", f"Profilo «{name}» creato e selezionato: controlla località e potenza in Impostazioni.")]), 201


def _known(id: int) -> list[dict]:
    profiles = db.list_profiles()
    if id not in {p["id"] for p in profiles}:
        raise ApiError("Profilo non trovato.", 404)
    return profiles


@bp.post("/profiles/<int:id>/rename")
def rename_profile(id: int):
    _known(id)
    db.rename_profile(id, _name())
    return jsonify(ok=True)


@bp.delete("/profiles/<int:id>")
def delete_profile(id: int):
    if len(_known(id)) == 1:
        raise ApiError("Deve esistere almeno un profilo.", 409)
    for name in db.delete_profile(id):
        storage().delete(name)
    return jsonify(messages=[msg("info", "Profilo eliminato con le sue bollette.")])
