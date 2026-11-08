"""API JSON per il front-end React (web e app nativa). Stessa logica delle pagine, senza HTML.

Il login è opzionale (AUTH_ENABLED, vedi auth.py): con la `Authorization: Bearer <token>` ottenuta da /auth/login.
Convenzioni: errori `{"error": "..."}` con status 4xx; le notifiche che prima erano `flash` tornano
in `messages: [{"level": "info"|"warn", "text": "..."}]`. Il profilo attivo arriva dall'header `X-Profile-Id`."""
from __future__ import annotations

import dataclasses
from typing import Any

from flask import Blueprint, current_app, jsonify

from .. import auth
from ..errors import ApiError

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


def storage():
    """Dove stanno i PDF (cartella o S3, vedi app/storage.py)."""
    return current_app.extensions["storage"]


def msg(level: str, text: str) -> dict:
    return {"level": level, "text": text}


@bp.before_request
def authenticate():
    """Con AUTH_ENABLED chiede un token valido a ogni richiesta (tranne login e stato della sessione); altrimenti non fa nulla."""
    auth.authenticate()


@bp.errorhandler(ApiError)
def _api_error(e: ApiError):
    return jsonify(error=e.text), e.status


@bp.errorhandler(404)
def _not_found(_e):
    return jsonify(error="Non trovato."), 404


from . import accounts, bills, compare, layouts, offers, profiles, proposals, public, settings  # noqa: E402,F401  (registrano le route)
