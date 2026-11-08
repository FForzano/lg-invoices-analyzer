from flask import jsonify, request

from .. import auth, db, forms
from ..models import Offer
from ..services import arera, catalog
from ..services.offers_csv import parse_offers_csv
from ..services.paging import paginate
from . import ApiError, bp, dump, msg
from .bills import strs
from .compare import page_info

PER_PAGE = 50


@bp.get("/offers")
def list_offers():
    q = request.args.get("q", "").strip().lower()
    offers = db.list_offers()
    if q:
        offers = [o for o in offers if q in f"{o.supplier} {o.name}".lower()]
    # prima le offerte inserite a mano o marcate come attuali, poi quelle importate
    offers.sort(key=lambda o: (not o.is_current, (o.source or "").startswith(arera.SOURCE_PREFIX)))
    page = paginate(offers, request.args.get("page", 1, type=int), PER_PAGE)
    return jsonify(items=dump(page.items), page=page_info(page), q=q, catalog_empty=not db.list_offers())


@bp.get("/offers/<int:id>")
def get_offer(id: int):
    offer = db.get_offer(id)
    if offer is None:
        raise ApiError("Offerta non trovata.", 404)
    return jsonify(offer=dump(offer))


CATALOG_ONLY_ADMIN = "Il catalogo delle offerte"


def _save(id: int | None):
    try:
        offer = forms.parse(Offer, strs(request.get_json(silent=True) or {}))
    except ValueError as e:
        raise ApiError(str(e)) from None
    if not offer.is_current:  # un'offerta non «attuale» è del catalogo, condiviso: la gestiscono gli amministratori
        existing = db.get_offer(id) if id is not None else None
        if existing is None and id is not None:
            raise ApiError("Offerta non trovata.", 404)
        if existing is None or existing.profile_id is None:
            auth.require_admin(CATALOG_ONLY_ADMIN)
    try:
        new_id = db.save_offer(offer, id)
    except LookupError:
        raise ApiError("Offerta non trovata.", 404) from None  # id di un'offerta non visibile a questo profilo
    return jsonify(id=new_id, messages=[msg("info", "Offerta salvata.")])


@bp.post("/offers")
def create_offer():
    return _save(None)


@bp.put("/offers/<int:id>")
def update_offer(id: int):
    return _save(id)


@bp.delete("/offers/<int:id>")
def delete_offer(id: int):
    offer = db.get_offer(id)
    if offer is not None and offer.profile_id is None:
        auth.require_admin(CATALOG_ONLY_ADMIN)
    db.delete_offer(id)
    return jsonify(ok=True)


@bp.post("/offers/import-csv")
@auth.admin_required
def import_csv():
    file = request.files.get("csv")
    if not file or not file.filename:
        raise ApiError("Seleziona un file CSV.")
    offers, errors = parse_offers_csv(file.read().decode("utf-8", errors="replace"))
    for offer in offers:
        db.save_offer(offer)
    return jsonify(messages=[msg("info", f"Importate {len(offers)} offerte."), *(msg("warn", e) for e in errors)])


@bp.post("/offers/import-arera")
@auth.admin_required
def import_arera():
    try:
        messages = catalog.refresh_catalog()
    except arera.AreraError as e:
        raise ApiError(str(e), 502) from None
    return jsonify(messages=messages)
