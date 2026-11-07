import uuid
from dataclasses import asdict
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for

from .. import db, forms
from ..models import COMMODITIES, Bill
from ..models import Offer
from ..services import extraction
from ..services.bill_parser import parse_offer_terms
from ..services.history import history

bp = Blueprint("bills", __name__)


@bp.get("/bills")
def index():
    return render_template("bills.html", bills=db.list_bills())


@bp.get("/bills/new")
def new():
    commodity = request.args.get("commodity", "power")
    return render_template("bill_form.html", v={"commodity": commodity}, can_extract=extraction.available())


@bp.post("/bills/upload")
def upload():
    """Salva il PDF, tenta l'estrazione LLM e mostra il modulo precompilato da confermare."""
    file = request.files.get("pdf")
    if not file or not file.filename:
        flash("Seleziona un file PDF.", "warn")
        return redirect(url_for("bills.new"))
    name = f"{uuid.uuid4().hex}.pdf"
    path = Path(current_app.config["PDF_DIR"]) / name
    file.save(path)
    values = {"pdf_path": name, "commodity": request.form.get("commodity", "power")}
    try:
        fields, method = extraction.extract_bill(str(path))
        values.update(fields)
        flash(f"Dati letti con {method}: controllali prima di salvare.", "info")
    except extraction.ExtractionError as e:
        values.update(e.partial)
        flash(f"Lettura non riuscita ({e}): completa il modulo a mano.", "warn")
    return render_template("bill_form.html", v=values, can_extract=extraction.available())


@bp.post("/bills")
def create():
    try:
        bill = forms.parse(Bill, request.form).with_derived_consumption()
    except ValueError as e:
        flash(str(e), "warn")
        return render_template("bill_form.html", v=request.form, can_extract=extraction.available()), 400
    bill_id = db.add_bill(bill)
    flash("Bolletta salvata.", "info")
    # l'offerta attuale si ricava dalla bolletta solo se non ne hai già una inserita a mano
    manual_current = any(
        o.is_current and not (o.source or "").startswith("bolletta:") for o in db.list_offers(bill.commodity)
    )
    if bill.pdf_path and not manual_current:
        flash(_detect_current_offer(bill_id, db.list_bills(bill.commodity)), "info")
    return redirect(url_for("verdict.index") if bill.pdf_path else url_for("bills.index"))


def _detect_current_offer(bill_id: int, bills: list[Bill]) -> str:
    """Crea/aggiorna l'offerta attuale dal PDF della bolletta e riallinea PUN/PSV al mese in bolletta."""
    bill = next(b for b in bills if b.id == bill_id)
    terms = parse_offer_terms(extraction.pdf_text(str(Path(current_app.config["PDF_DIR"]) / bill.pdf_path)), bill.commodity)
    if terms is None:
        return "Offerta attuale non riconosciuta nella bolletta: inseriscila a mano in Offerte per vedere il risparmio."
    db.save_detected_offer(Offer(**terms.offer, is_current=True, source=f"bolletta:{bill_id}"))
    message = f"Offerta attuale rilevata dalla bolletta: «{terms.offer['name']}»."
    latest = max(b.period_end for b in bills)
    key, value = ("pun", terms.pun) if terms.pun else ("psv", terms.psv)
    settings = db.get_settings()
    adopted_recent = settings.get(key + "_recent") == settings[key]  # l'utente ha scelto i prezzi recenti: non toccarli
    if bill.period_end >= latest and value and not adopted_recent:
        factor = db.get_index_factors()[key][int(bill.period_end[5:7]) - 1]  # il mese in bolletta non è un mese medio
        db.save_settings({key: round(value / factor, 6)})
        message += f" {key.upper()} medio annuo assunto: {value / factor:.4f} ({value:.4f} del mese ÷ {factor:.2f} stagionalità)."
    return message


@bp.post("/bills/<int:id>/detect-offer")
def detect_offer(id: int):
    bills = db.list_bills()
    bill = next((b for b in bills if b.id == id and b.pdf_path), None) or abort(404)
    flash(_detect_current_offer(id, [b for b in bills if b.commodity == bill.commodity]), "info")
    return redirect(url_for("verdict.index"))


@bp.get("/bills/<int:id>/pdf")
def pdf(id: int):
    bill = next((b for b in db.list_bills() if b.id == id and b.pdf_path), None)
    if bill is None:
        abort(404)
    return send_file(Path(current_app.config["PDF_DIR"]) / bill.pdf_path, mimetype="application/pdf")


@bp.post("/bills/<int:id>/delete")
def delete(id: int):
    db.delete_bill(id)
    return redirect(url_for("bills.index"))


@bp.get("/history")
def history_page():
    commodity = request.args.get("commodity", "power")
    if commodity not in COMMODITIES:
        abort(404)
    return render_template("history.html", commodity=commodity, rows=history(db.list_bills(commodity)))
