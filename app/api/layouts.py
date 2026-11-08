import io
import os
import re
from urllib.parse import quote

from flask import Response, jsonify, request, send_file

from .. import db
from ..services import extraction, layouts
from ..services.bill_parser import REQUIRED
from . import ApiError, bp, dump, msg, storage
from .bills import prefill

REPO_URL = "https://github.com/FForzano/lg-invoices-analyzer"  # `REPORT_REPO_URL` per un fork
PDF_NAME = re.compile(r"[0-9a-f]{32}\.pdf")
FIELD_LABEL = {  # più chiari delle descrizioni per l'LLM in FIELD_HELP; i campi non elencati usano quelle
    "commodity": "Fornitura (luce o gas)", "period_start": "Inizio del periodo fatturato", "period_end": "Fine del periodo fatturato",
    "consumption": "Consumo fatturato (kWh o Smc)", "total_eur": "Totale da pagare (€)", "reading_type": "Tipo di lettura (effettiva o stimata)",
    "supplier": "Nome del fornitore", "power_kw": "Potenza impegnata (kW)",
}
CHOICE_LABEL = {"power": "Luce", "gas": "Gas", "effettiva": "Effettiva", "stimata": "Stimata"}


def _pdf(name: str | None) -> bytes:
    """Il PDF dallo storage. Il nome deve essere uno di quelli generati dall'app (esclude percorsi e chiavi arbitrarie)."""
    if not (name and PDF_NAME.fullmatch(name)):
        raise ApiError("PDF non trovato.", 404)
    try:
        return storage().get(name)
    except FileNotFoundError:
        raise ApiError("PDF non trovato.", 404) from None


@bp.get("/layouts")
def list_layouts():
    return jsonify(mine=dump(db.list_layouts()), builtin=dump(layouts.builtin_layouts()))


def _teach_info(name: str, text: str, samples=None, errors=None) -> dict:
    try:
        found, _ = layouts.apply_layouts(text, extraction.parse_bill_text(text).fields, db.list_layouts())
    except Exception:  # la pagina serve proprio quando la lettura non funziona
        found = {}
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    kinds = layouts.teachable_fields()
    return {
        "pdf": name, "text": text, "kinds": kinds, "found": found, "samples": samples or {}, "errors": errors or {},
        "help": {**extraction.FIELD_HELP, **FIELD_LABEL}, "required": list(REQUIRED),
        "choices": {f: list(layouts.choices(f)) for f, k in kinds.items() if k == "keyword"},
        "labels": CHOICE_LABEL, "supplier": (samples or {}).get("_signature") or first_line.title(),
    }


@bp.get("/layouts/teach")
def teach_info():
    name = request.args.get("pdf")
    return jsonify(_teach_info(name, extraction.pdf_text(_pdf(name)).strip()))


@bp.post("/layouts/teach")
def teach_save():
    data = request.get_json(silent=True) or {}
    name = data.get("pdf")
    pdf = _pdf(name)
    text = extraction.pdf_text(pdf).strip()
    samples = {f: ((data.get("values") or {}).get(f, ""), (data.get("choices") or {}).get(f)) for f in layouts.teachable_fields()}
    signature = (data.get("signature") or "").strip()
    plain = {**{f: s[0] for f, s in samples.items()}, "_signature": signature}
    try:
        layout, errors = layouts.learn_layout(text, data.get("name", ""), signature, samples)
    except ValueError as e:
        return jsonify(_teach_info(name, text, plain, {"_signature": str(e)})), 400
    if errors or not layout.rules:
        return jsonify(_teach_info(name, text, plain, errors or {"_all": "Indica almeno un valore."})), 400
    db.save_layout(layout)
    result = prefill(name, pdf, data.get("commodity", "power"))
    result["messages"].insert(0, msg("info", f"Layout «{layout.name}» salvato ({len(layout.rules)} regole): le prossime bollette dello stesso fornitore si leggeranno da sole."))
    return jsonify(prefill=result)


@bp.get("/layouts/pdf/<name>")
def layout_pdf(name: str):
    """Il PDF da mostrare nella pagina «Insegna» (anche prima che la bolletta sia salvata)."""
    return send_file(io.BytesIO(_pdf(name)), mimetype="application/pdf")


@bp.delete("/layouts/<int:id>")
def delete_layout(id: int):
    db.delete_layout(id)
    return jsonify(ok=True)


@bp.get("/layouts/<int:id>/report")
def layout_report(id: int):
    layout = db.get_layout(id)
    if layout is None:
        raise ApiError("Layout non trovato.", 404)
    raw, dropped = layouts.report(layout)
    if request.args.get("download"):
        return Response(raw, mimetype="application/json", headers={"Content-Disposition": f'attachment; filename="layout-{id}.json"'})
    repo = os.environ.get("REPORT_REPO_URL", REPO_URL)
    body = f"Layout di lettura per «{layout.name}» (nessun valore, solo etichette).\n\n```json\n{raw}\n```\n"
    issue = f"{repo}/issues/new?title={quote('Nuovo layout bolletta: ' + layout.name)}&body={quote(body)}"
    return jsonify(layout=dump(layout), raw=raw, dropped=dropped, issue=issue if len(issue) < 7000 else None)
