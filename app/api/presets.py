from urllib.parse import parse_qsl, urlencode

from flask import jsonify, request

from .. import db
from . import ApiError, bp, msg

MAX_NAME = 40
MAX_PRESETS = 20
FLAGS = ("no_exit", "bonus", "no_domic", "online")


def clean_query(raw: str) -> str:
    """Solo i filtri noti, con valori validi: il preferito è testo del client e finisce di nuovo nell'indirizzo."""
    out: dict[str, str] = {}
    for k, v in parse_qsl(raw):
        if k == "type" and v in ("fixed", "indexed"):
            out[k] = v
        elif k in FLAGS and v == "1":
            out[k] = v
        elif k == "power":
            try:
                if 0 < float(v) <= 100:
                    out[k] = v
            except ValueError:
                pass
    return urlencode(out)


@bp.get("/filter-presets")
def list_presets():
    return jsonify(items=db.list_presets())


@bp.post("/filter-presets")
def create_preset():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    query = clean_query(str(data.get("query") or ""))
    if not name or len(name) > MAX_NAME:
        raise ApiError(f"Il nome è obbligatorio (massimo {MAX_NAME} caratteri).")
    if not query:
        raise ApiError("Scegli almeno un filtro da salvare.")
    if len(db.list_presets()) >= MAX_PRESETS and name not in {p["name"] for p in db.list_presets()}:
        raise ApiError(f"Puoi salvare al massimo {MAX_PRESETS} preferiti: eliminane uno.")
    id = db.save_preset(name, query, bool(data.get("is_default")))
    return jsonify(id=id, items=db.list_presets(), messages=[msg("info", f"Filtri «{name}» salvati.")]), 201


@bp.put("/filter-presets/default")
def set_default():
    wanted = (request.get_json(silent=True) or {}).get("id")
    db.set_default_preset(int(wanted) if isinstance(wanted, int) else None)
    return jsonify(items=db.list_presets())


@bp.delete("/filter-presets/<int:id>")
def delete_preset(id: int):
    db.delete_preset(id)
    return jsonify(items=db.list_presets())
