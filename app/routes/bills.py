import uuid
from dataclasses import asdict
from pathlib import Path

from pypdf.errors import PyPdfError
from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, send_file, url_for

from .. import db, forms
from ..models import COMMODITIES, UNIT, Bill
from ..models import Offer
from ..services import extraction
from ..services.bill_parser import parse_offer_terms
from ..services.history import chart_data, history
from ..services.paging import paginate

bp = Blueprint("bills", __name__)
PER_PAGE = 25


@bp.get("/bills")
def index():
    page = paginate(db.list_bills(), request.args.get("page", 1, type=int), PER_PAGE)
    return render_template("bills.html", page=page)


@bp.get("/bills/new")
def new():
    commodity = request.args.get("commodity", "power")
    return render_template("bill_form.html", v={"commodity": commodity}, can_extract=extraction.available())


def _save_pdf(file) -> tuple[str, Path]:
    name = f"{uuid.uuid4().hex}.pdf"
    path = Path(current_app.config["PDF_DIR"]) / name
    file.save(path)
    return name, path


@bp.post("/bills/upload")
def upload():
    """Un PDF: modulo precompilato da confermare. Più PDF: import in blocco."""
    files = [f for f in request.files.getlist("pdf") if f.filename]
    if not files:
        flash("Seleziona un file PDF.", "warn")
        return redirect(url_for("bills.new"))
    if len(files) > 1:
        return _bulk_import(files)
    name, path = _save_pdf(files[0])
    return prefill_form(name, path, request.form.get("commodity", "power"))


def prefill_form(name: str, path: Path, commodity: str = "power") -> str:
    """Modulo bolletta precompilato dalla lettura del PDF; se la lettura non basta offre di insegnare il layout."""
    values = {"pdf_path": name, "commodity": commodity}
    failed = False
    try:
        fields, method = extraction.extract_bill(str(path), layouts=db.list_layouts())
        values.update(fields)
        flash(f"Dati letti con {method}: controllali prima di salvare.", "info")
    except extraction.ExtractionError as e:
        values.update(e.partial)
        failed = not isinstance(e, extraction.NoTextError)  # su un'immagine non c'è niente da insegnare
        flash(f"Lettura non riuscita ({e}): completa il modulo a mano.", "warn")
    return render_template("bill_form.html", v=values, can_extract=extraction.available(), teach_pdf=name if failed else None)


def _bulk_import(files) -> Response:
    """Salva solo le bollette lette per intero e non già presenti; le altre vengono segnalate e scartate."""
    known = {(b.commodity, b.period_start, b.period_end) for b in db.list_bills()}
    latest: dict[str, int] = {}  # fornitura -> id della bolletta importata con il periodo più recente
    latest_end: dict[str, str] = {}
    problems = []
    layouts = db.list_layouts()
    for file in files:
        name, path = _save_pdf(file)
        try:
            fields, _ = extraction.extract_bill(str(path), layouts=layouts)
            bill = Bill(**fields, pdf_path=name).with_derived_consumption()
            key = (bill.commodity, bill.period_start, bill.period_end)
            if key in known:
                raise ValueError("già presente")
        except (extraction.ExtractionError, PyPdfError, TypeError, ValueError) as e:
            path.unlink(missing_ok=True)
            hint = " Caricalo da solo per insegnare all'app a leggerlo." if isinstance(e, extraction.ExtractionError) and not isinstance(e, extraction.NoTextError) else ""
            problems.append(f"{file.filename}: {e}.{hint}")
            continue
        known.add(key)
        bill_id = db.add_bill(bill)
        if bill.period_end >= latest_end.get(bill.commodity, ""):
            latest[bill.commodity], latest_end[bill.commodity] = bill_id, bill.period_end
    imported = len(files) - len(problems)
    flash(f"Importate {imported} bollette su {len(files)}.", "info" if imported else "warn")
    for problem in problems:
        flash(problem, "warn")
    for commodity, bill_id in latest.items():
        if not _has_manual_current(commodity):
            flash(_detect_current_offer(bill_id, db.list_bills(commodity)), "info")
    return redirect(url_for("verdict.index") if imported else url_for("bills.new"))


def _has_manual_current(commodity: str) -> bool:
    """L'offerta attuale si ricava dalla bolletta solo se non ne hai già una inserita a mano."""
    return any(o.is_current and not (o.source or "").startswith("bolletta:") for o in db.list_offers(commodity))


@bp.post("/bills")
def create():
    try:
        bill = forms.parse(Bill, request.form).with_derived_consumption()
    except ValueError as e:
        flash(str(e), "warn")
        return render_template("bill_form.html", v=request.form, can_extract=extraction.available()), 400
    bill_id = db.add_bill(bill)
    flash("Bolletta salvata.", "info")
    if bill.pdf_path and not _has_manual_current(bill.commodity):
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
    rows = history(db.list_bills(commodity))
    return render_template("history.html", commodity=commodity, rows=rows, chart=chart_data(rows), unit=UNIT[commodity])
