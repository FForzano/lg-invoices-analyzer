from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import db, forms
from ..models import Offer
from ..services import arera
from ..services.paging import paginate
from ..services.offers_csv import parse_offers_csv

bp = Blueprint("offers", __name__)


PER_PAGE = 50


@bp.get("/offers")
def index():
    q = request.args.get("q", "").strip().lower()
    offers = db.list_offers()
    if q:
        offers = [o for o in offers if q in f"{o.supplier} {o.name}".lower()]
    # prima le offerte inserite a mano o marcate come attuali, poi quelle importate
    offers.sort(key=lambda o: (not o.is_current, (o.source or "").startswith(arera.SOURCE_PREFIX)))
    page = paginate(offers, request.args.get("page", 1, type=int), PER_PAGE)
    return render_template("offers.html", page=page, q=q)


@bp.get("/offers/new")
def new():
    return render_template("offer_form.html", v={"commodity": request.args.get("commodity", "power")}, id=None)


@bp.get("/offers/<int:id>")
def edit(id: int):
    offer = db.get_offer(id) or abort(404)
    return render_template("offer_form.html", v=vars(offer), id=id)


@bp.post("/offers/save")
def save():
    id = request.form.get("id", type=int)
    try:
        offer = forms.parse(Offer, request.form)
    except ValueError as e:
        flash(str(e), "warn")
        return render_template("offer_form.html", v=request.form, id=id), 400
    try:
        db.save_offer(offer, id)
    except LookupError:
        abort(404)  # id di un'offerta non visibile a questo profilo
    return redirect(url_for("offers.index"))


@bp.post("/offers/<int:id>/delete")
def delete(id: int):
    db.delete_offer(id)
    return redirect(url_for("offers.index"))


@bp.post("/offers/import")
def import_csv():
    file = request.files.get("csv")
    if not file or not file.filename:
        flash("Seleziona un file CSV.", "warn")
        return redirect(url_for("offers.index"))
    offers, errors = parse_offers_csv(file.read().decode("utf-8", errors="replace"))
    for offer in offers:
        db.save_offer(offer)
    flash(f"Importate {len(offers)} offerte.", "info")
    for error in errors:
        flash(error, "warn")
    return redirect(url_for("offers.index"))


@bp.post("/offers/import-arera")
def import_arera():
    try:
        offers, skipped = arera.fetch_offers()
    except arera.AreraError as e:
        flash(str(e), "warn")
        return redirect(url_for("offers.index"))
    n = db.replace_imported_offers(offers, arera.SOURCE_PREFIX)
    detail = ", ".join(f"{count} {why}" for why, count in skipped.items())
    flash(f"Importate {n} offerte domestiche dal Portale Offerte" + (f" (scartate: {detail})." if detail else "."), "info")
    try:
        factors, recent = arera.fetch_index_history()
        db.save_index_factors(factors)
        db.save_settings({"pun_recent": recent["pun"], "psv_recent": recent["psv"], "recent_until": recent["until"]})
        flash("Stagionalità e prezzi recenti di PUN/PSV aggiornati. Puoi adottare i prezzi recenti in Impostazioni.", "info")
    except arera.AreraError as e:
        flash(f"{e}: uso i valori predefiniti.", "warn")
    return redirect(url_for("offers.index"))
