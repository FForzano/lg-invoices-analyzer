"""Layout di lettura: insegnare all'app a leggere una bolletta non riconosciuta e segnalarne la struttura (anonima)."""
import os
import re
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for

from .. import db
from ..services import extraction, layouts
from ..services.bill_parser import REQUIRED
from . import bills

bp = Blueprint("layouts", __name__)
REPO_URL = "https://github.com/FForzano/lg-invoices-analyzer"  # `REPORT_REPO_URL` per un fork
PDF_NAME = re.compile(r"[0-9a-f]{32}\.pdf")
FIELD_LABEL = {  # più chiari delle descrizioni per l'LLM in FIELD_HELP; i campi non elencati usano quelle
    "commodity": "Fornitura (luce o gas)", "period_start": "Inizio del periodo fatturato", "period_end": "Fine del periodo fatturato",
    "consumption": "Consumo fatturato (kWh o Smc)", "total_eur": "Totale da pagare (€)", "reading_type": "Tipo di lettura (effettiva o stimata)",
    "supplier": "Nome del fornitore", "power_kw": "Potenza impegnata (kW)",
}
CHOICE_LABEL = {"power": "Luce", "gas": "Gas", "effettiva": "Effettiva", "stimata": "Stimata"}


def _pdf(name: str | None) -> Path:
    path = Path(current_app.config["PDF_DIR"]) / (name or "")
    if not (name and PDF_NAME.fullmatch(name) and path.is_file()):
        abort(404)
    return path


def _teach_page(name: str, text: str, samples: dict | None = None, errors: dict | None = None, status: int = 200):
    try:
        found, _ = layouts.apply_layouts(text, extraction.parse_bill_text(text).fields, db.list_layouts())
    except Exception:  # la pagina serve proprio quando la lettura non funziona
        found = {}
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    kinds = layouts.teachable_fields()
    return render_template(
        "teach.html", pdf=name, text=text, kinds=kinds, found=found, samples=samples or {}, errors=errors or {},
        help={**extraction.FIELD_HELP, **FIELD_LABEL}, required=REQUIRED, choices={f: layouts.choices(f) for f, k in kinds.items() if k == "keyword"},
        labels=CHOICE_LABEL, supplier=(samples or {}).get("_signature") or first_line.title(),
    ), status


@bp.get("/layouts")
def index():
    return render_template("layouts.html", mine=db.list_layouts(), builtin=layouts.builtin_layouts())


@bp.get("/layouts/teach")
def teach():
    name = request.args.get("pdf")
    return _teach_page(name, extraction.pdf_text(str(_pdf(name))).strip())


@bp.post("/layouts/teach")
def teach_save():
    name = request.form.get("pdf")
    path = _pdf(name)
    text = extraction.pdf_text(str(path)).strip()
    form = request.form
    samples = {f: (form.get(f"v_{f}", ""), form.get(f"c_{f}")) for f in layouts.teachable_fields()}
    signature = form.get("signature", "").strip()
    try:
        layout, errors = layouts.learn_layout(text, form.get("name", ""), signature, samples)
    except ValueError as e:
        return _teach_page(name, text, {**{f: s[0] for f, s in samples.items()}, "_signature": signature}, {"_signature": str(e)}, 400)
    if errors or not layout.rules:
        errors = errors or {"_all": "Indica almeno un valore."}
        return _teach_page(name, text, {**{f: s[0] for f, s in samples.items()}, "_signature": signature}, errors, 400)
    db.save_layout(layout)
    flash(f"Layout «{layout.name}» salvato ({len(layout.rules)} regole): le prossime bollette dello stesso fornitore si leggeranno da sole.", "info")
    return bills.prefill_form(name, path, request.form.get("commodity", "power"))


@bp.post("/layouts/<int:id>/delete")
def delete(id: int):
    db.delete_layout(id)
    return redirect(url_for("layouts.index"))


@bp.get("/layouts/<int:id>/report")
def report(id: int):
    layout = db.get_layout(id) or abort(404)
    raw, dropped = layouts.report(layout)
    if request.args.get("download"):
        return Response(raw, mimetype="application/json", headers={"Content-Disposition": f'attachment; filename="layout-{id}.json"'})
    repo = os.environ.get("REPORT_REPO_URL", REPO_URL)
    body = f"Layout di lettura per «{layout.name}» (nessun valore, solo etichette).\n\n```json\n{raw}\n```\n"
    issue = f"{repo}/issues/new?title={quote('Nuovo layout bolletta: ' + layout.name)}&body={quote(body)}"
    return render_template("layout_report.html", layout=layout, raw=raw, dropped=dropped, issue=issue if len(issue) < 7000 else None)
