"""API JSON per il front-end React (web e app nativa). Stessa logica delle pagine, senza HTML.

Convenzioni: errori `{"error": "..."}` con status 4xx; le notifiche che prima erano `flash` tornano
in `messages: [{"level": "info"|"warn", "text": "..."}]`. Il profilo attivo arriva dall'header `X-Profile-Id`."""
from __future__ import annotations

import dataclasses
from typing import Any

from flask import Blueprint, jsonify

bp = Blueprint("api", __name__, url_prefix="/api")


def dump(obj: Any) -> Any:
    """Dataclass (anche annidate) -> strutture JSON; aggiunge i valori calcolati che il front-end non deve rifare."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        out = {f.name: dump(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
        for name, attr in vars(type(obj)).items():  # proprietà calcolate (total, partial, tight...): il front-end non le rifà
            if isinstance(attr, property):
                out[name] = dump(getattr(obj, name))
        return out
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [dump(v) for v in obj]
    return obj


def msg(level: str, text: str) -> dict:
    return {"level": level, "text": text}


class ApiError(Exception):
    def __init__(self, text: str, status: int = 400):
        self.text, self.status = text, status


@bp.before_request
def authenticate():
    """Unico punto in cui verrà aggiunto il login (token/sessione): oggi non controlla nulla, per scelta.
    Per attivarlo: leggere qui l'header `Authorization` e rispondere 401 con `ApiError("...", 401)`;
    il front-end gestisce già il 401 (frontend/src/lib/api.ts, `onUnauthorized`)."""
    return None


@bp.errorhandler(ApiError)
def _api_error(e: ApiError):
    return jsonify(error=e.text), e.status


@bp.errorhandler(404)
def _not_found(_e):
    return jsonify(error="Non trovato."), 404


from . import bills, compare, layouts, offers, profiles, proposals, settings  # noqa: E402,F401  (registrano le route)
