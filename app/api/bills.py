import io
import uuid
from flask import current_app, jsonify, request, send_file
from pypdf.errors import PyPdfError

from .. import auth, db, forms
from ..models import COMMODITIES, UNIT, Bill, Offer
from ..services import extraction
from ..services.bill_parser import parse_offer_terms
from ..services.history import chart_data, history
from ..services.paging import paginate
from . import ApiError, bp, dump, msg, storage
from .compare import page_info

PER_PAGE = 25


def _save_pdf(file) -> tuple[str, bytes]:
    """Salva il PDF nello storage (cartella o S3) e lo restituisce anche in memoria, per leggerlo subito."""
    data = file.read()
    name = f"{uuid.uuid4().hex}.pdf"
    storage().put(name, data)
    return name, data


def _has_manual_current(commodity: str) -> bool:
    """L'offerta attuale si ricava dalla bolletta solo se non ne hai già una inserita a mano."""
    return any(o.is_current and not (o.source or "").startswith("bolletta:") for o in db.list_offers(commodity))


def _detect_current_offer(bill_id: int, bills: list[Bill]) -> str:
    """Crea/aggiorna l'offerta attuale dal PDF della bolletta e riallinea PUN/PSV al mese in bolletta."""
    bill = next(b for b in bills if b.id == bill_id)
    terms = parse_offer_terms(extraction.pdf_text(storage().get(bill.pdf_path)), bill.commodity)
    if terms is None:
        return "Offerta attuale non riconosciuta nella bolletta: inseriscila a mano in Offerte per vedere il risparmio."
    db.save_detected_offer(Offer(**terms.offer, is_current=True, source=f"bolletta:{bill_id}"))
    message = f"Offerta attuale rilevata dalla bolletta: «{terms.offer['name']}»."
    latest = max(b.period_end for b in bills)
    key, value = ("pun", terms.pun) if terms.pun else ("psv", terms.psv)
    settings = db.get_settings()
    adopted_recent = settings.get(key + "_recent") == settings[key]  # l'utente ha scelto i prezzi recenti: non toccarli
    if bill.period_end >= latest and value and not adopted_recent and auth.is_admin():  # PUN/PSV sono globali: non li cambia chi carica una bolletta
        factor = db.get_index_factors()[key][int(bill.period_end[5:7]) - 1]  # il mese in bolletta non è un mese medio
        db.save_settings({key: round(value / factor, 6)})
        message += f" {key.upper()} medio annuo assunto: {value / factor:.4f} ({value:.4f} del mese ÷ {factor:.2f} stagionalità)."
    return message


def strs(data: dict) -> dict:
    """Valori JSON -> stringhe come in un form HTML, così `forms.parse` resta l'unico parser."""
    return {k: ("on" if v is True else "" if v in (None, False) else str(v)) for k, v in data.items()}


@bp.get("/bills")
def list_bills():
    page = paginate(db.list_bills(), request.args.get("page", 1, type=int), PER_PAGE)
    return jsonify(items=dump(page.items), page=page_info(page))


@bp.post("/bills")
def create_bill():
    try:
        bill = forms.parse(Bill, strs(request.get_json(silent=True) or {})).with_derived_consumption()
    except ValueError as e:
        raise ApiError(str(e)) from None
    bill_id = db.add_bill(bill)
    messages = [msg("info", "Bolletta salvata.")]
    if bill.pdf_path and not _has_manual_current(bill.commodity):
        messages.append(msg("info", _detect_current_offer(bill_id, db.list_bills(bill.commodity))))
    return jsonify(id=bill_id, messages=messages), 201


@bp.delete("/bills/<int:id>")
def delete_bill(id: int):
    db.delete_bill(id)
    return jsonify(ok=True)


@bp.post("/bills/<int:id>/detect-offer")
def detect_offer(id: int):
    bills = db.list_bills()
    bill = next((b for b in bills if b.id == id and b.pdf_path), None) or ApiError("Bolletta non trovata.", 404)
    if isinstance(bill, ApiError):
        raise bill
    return jsonify(messages=[msg("info", _detect_current_offer(id, [b for b in bills if b.commodity == bill.commodity]))])


@bp.get("/bills/<int:id>/pdf")
def bill_pdf(id: int):
    bill = next((b for b in db.list_bills() if b.id == id and b.pdf_path), None)
    if bill is None:
        raise ApiError("Bolletta non trovata.", 404)
    try:
        return send_file(io.BytesIO(storage().get(bill.pdf_path)), mimetype="application/pdf")
    except FileNotFoundError:
        raise ApiError("PDF non trovato.", 404) from None


def prefill(name: str, pdf: bytes, commodity: str = "power") -> dict:
    """Valori del modulo bolletta letti dal PDF; se la lettura non basta indica il PDF da cui insegnare il layout."""
    values: dict = {"pdf_path": name, "commodity": commodity}
    messages, teach = [], None
    try:
        fields, method = extraction.extract_bill(pdf, layouts=db.list_layouts())
        values.update(fields)
        messages.append(msg("info", f"Dati letti con {method}: controllali prima di salvare."))
    except extraction.ExtractionError as e:
        values.update(e.partial)
        teach = None if isinstance(e, extraction.NoTextError) else name  # su un'immagine non c'è niente da insegnare
        messages.append(msg("warn", f"Lettura non riuscita ({e}): completa il modulo a mano."))
    return {"values": values, "teach_pdf": teach, "messages": messages}


@bp.post("/bills/upload")
def upload():
    """Un PDF: valori precompilati da confermare. Più PDF: import in blocco."""
    files = [f for f in request.files.getlist("pdf") if f.filename]
    if not files:
        raise ApiError("Seleziona un file PDF.")
    if len(files) > 1:
        return jsonify(bulk=_bulk_import(files))
    name, pdf = _save_pdf(files[0])
    try:
        return jsonify(prefill=prefill(name, pdf, request.form.get("commodity", "power")))
    except PyPdfError:
        storage().delete(name)
        raise ApiError("Il file non è un PDF valido.") from None


def _bulk_import(files) -> dict:
    """Salva solo le bollette lette per intero e non già presenti; le altre vengono segnalate e scartate."""
    known = {(b.commodity, b.period_start, b.period_end) for b in db.list_bills()}
    latest: dict[str, int] = {}
    latest_end: dict[str, str] = {}
    problems = []
    layouts = db.list_layouts()
    for file in files:
        name, pdf = _save_pdf(file)
        try:
            fields, _ = extraction.extract_bill(pdf, layouts=layouts)
            bill = Bill(**fields, pdf_path=name).with_derived_consumption()
            key = (bill.commodity, bill.period_start, bill.period_end)
            if key in known:
                raise ValueError("già presente")
        except (extraction.ExtractionError, PyPdfError, TypeError, ValueError) as e:
            storage().delete(name)
            hint = " Caricalo da solo per insegnare all'app a leggerlo." if isinstance(e, extraction.ExtractionError) and not isinstance(e, extraction.NoTextError) else ""
            problems.append(f"{file.filename}: {e}.{hint}")
            continue
        known.add(key)
        bill_id = db.add_bill(bill)
        if bill.period_end >= latest_end.get(bill.commodity, ""):
            latest[bill.commodity], latest_end[bill.commodity] = bill_id, bill.period_end
    imported = len(files) - len(problems)
    messages = [msg("info" if imported else "warn", f"Importate {imported} bollette su {len(files)}.")]
    messages += [msg("warn", p) for p in problems]
    for commodity, bill_id in latest.items():
        if not _has_manual_current(commodity):
            messages.append(msg("info", _detect_current_offer(bill_id, db.list_bills(commodity))))
    return {"imported": imported, "total": len(files), "messages": messages}


@bp.get("/history/<commodity>")
def history_data(commodity: str):
    if commodity not in COMMODITIES:
        raise ApiError("Fornitura non valida.", 404)
    rows = history(db.list_bills(commodity))
    return jsonify(unit=UNIT[commodity], rows=dump(rows), chart=chart_data(rows))
