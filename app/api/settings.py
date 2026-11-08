from flask import jsonify, request

from .. import db
from . import ApiError, bp, msg


def _code(raw) -> str:
    """Codice ISTAT: solo cifre (può essere vuoto, per non filtrare per quel livello)."""
    raw = str(raw).strip()
    if raw and not raw.isdigit():
        raise ValueError(raw)
    return raw


@bp.get("/settings")
def get_settings():
    return jsonify(settings=db.get_settings(), defaults=db.SETTING_DEFAULTS)


@bp.put("/settings")
def put_settings():
    data = request.get_json(silent=True) or {}
    try:
        db.save_settings({
            k: _code(data[k]) if isinstance(default, str) else float(str(data[k]).replace(",", "."))
            for k, default in db.SETTING_DEFAULTS.items()
        })
    except (KeyError, ValueError):
        raise ApiError("Valori non validi.") from None
    return jsonify(settings=db.get_settings(), messages=[msg("info", "Impostazioni salvate.")])


@bp.post("/settings/use-recent")
def use_recent():
    s = db.get_settings()
    if "pun_recent" not in s:
        raise ApiError("Prezzi recenti non disponibili: aggiorna dal Portale Offerte.", 409)
    db.save_settings({"pun": s["pun_recent"], "psv": s["psv_recent"]})
    return jsonify(settings=db.get_settings(), messages=[msg("info", "PUN e PSV assunti aggiornati ai prezzi recenti.")])
