"""Informazioni pubbliche sull'installazione (gestore, funzioni attive) e spazi pubblicitari. Servono a piè di pagina, termini e privacy,
che devono essere raggiungibili da chiunque, anche senza account."""
from __future__ import annotations

from flask import abort, current_app, jsonify, request, send_from_directory

from .. import ads, auth, mail
from ..services import extraction
from . import bp


@bp.get("/site")
def site_info():
    cfg = current_app.config
    return jsonify(
        operator={"name": cfg["OPERATOR_NAME"], "email": cfg["OPERATOR_EMAIL"], "address": cfg["OPERATOR_ADDRESS"], "vat": cfg["OPERATOR_VAT"], "registry": cfg["OPERATOR_REGISTRY"]},
        auth_enabled=auth.enabled(), registration_open=bool(cfg["ALLOW_REGISTRATION"]) and auth.enabled(),
        mail_enabled=mail.enabled(), llm_enabled=extraction.available(), ads_enabled=ads.enabled(),
        storage=cfg["STORAGE_DRIVER"], database="postgresql" if cfg["DATABASE_URL"].startswith("postgres") else "sqlite",
    )


@bp.get("/ads")
def ads_for_slot():
    """Un contenuto sponsorizzato per lo spazio richiesto, oppure `ad: null`. Mai tracciamento: è un file di testo scritto da chi gestisce il sito."""
    return jsonify(ad=ads.pick(request.args.get("slot", "")))


@bp.get("/ads/media/<name>")
def ads_media(name: str):
    """Immagine o video di un annuncio, dalla cartella del file ADS_FILE: solo quelli dichiarati in un annuncio valido."""
    folder = ads.media_dir()
    if not folder or not any(name in (a["image"], a["video"]) for a in ads.load()):
        abort(404)
    return send_from_directory(folder, name, max_age=3600)
