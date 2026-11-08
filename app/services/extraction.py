"""Estrazione dei campi di una bolletta PDF.

1. Parser a regole (`bill_parser`): gratuito e locale, usato sempre per primo.
2. Solo se i campi essenziali mancano, ripiego su un LLM: il testo della bolletta
   (dati personali) viene inviato all'API Anthropic e quindi esce dal NAS.
Senza ANTHROPIC_API_KEY il ripiego non c'è e si completa il modulo a mano."""
from __future__ import annotations

import dataclasses
import os
import typing

from pypdf import PdfReader

from ..models import SYSTEM_FIELDS, Bill
from .bill_parser import REQUIRED, parse_bill_text
from .layouts import Layout, apply_layouts, builtin_layouts

DEFAULT_MODEL = "claude-sonnet-5-5"

FIELD_HELP = {
    "commodity": "'power' per luce, 'gas' per gas",
    "period_start": "inizio periodo fatturato, YYYY-MM-DD",
    "period_end": "fine periodo fatturato, YYYY-MM-DD",
    "consumption": "consumo fatturato: kWh totali (luce) o Smc (gas)",
    "kwh_f1": "kWh fatturati in fascia F1 (solo luce)",
    "kwh_f2": "kWh fatturati in fascia F2 (solo luce)",
    "kwh_f3": "kWh fatturati in fascia F3 (solo luce)",
    "mc": "metri cubi misurati (solo gas)",
    "coeff_c": "coefficiente di conversione C (solo gas)",
    "power_kw": "potenza impegnata in kW (solo luce)",
    "max_power_kw": "livello massimo mensile di potenza prelevata in kW (solo luce)",
    "annual_max_power_kw": "il più alto tra i 12 livelli mensili di potenza prelevata dello storico, in kW (solo luce)",
    "power_rate_kw_month": "quota potenza di rete in €/kW/mese (solo luce)",
    "reading_type": "'effettiva' o 'stimata'",
    "total_eur": "totale da pagare in euro",
    "annual_consumption": "consumo annuo già calcolato in bolletta (sezione informazioni storiche)",
    "annual_f1": "consumo annuo F1 stampato in bolletta (solo luce)",
    "annual_f2": "consumo annuo F2 stampato in bolletta (solo luce)",
    "annual_f3": "consumo annuo F3 stampato in bolletta (solo luce)",
    "annual_spend": "spesa annua già calcolata in bolletta, in euro",
    "supplier": "nome del fornitore",
    "social_bonus_expires_on": "data di scadenza del bonus sociale, YYYY-MM-DD",
}

PROMPT = (
    "Estrai i dati dalla bolletta italiana di luce o gas qui sotto. "
    "Usa solo valori presenti nel testo, lascia fuori i campi assenti, non calcolare nulla. "
    "I numeri usano il punto come separatore decimale.\n\n{text}"
)


class ExtractionError(Exception):
    def __init__(self, message: str, partial: dict | None = None):
        super().__init__(message)
        self.partial = partial or {}


class NoTextError(ExtractionError):
    """PDF fatto di sole immagini (scansione, fac-simile): non c'è testo da leggere né da insegnare."""


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def pdf_text(path: str) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def tool_schema() -> dict:
    hints = typing.get_type_hints(Bill)
    props = {}
    for f in dataclasses.fields(Bill):
        if f.name in SYSTEM_FIELDS or f.name == "pdf_path":
            continue
        base = [a for a in typing.get_args(hints[f.name]) if a is not type(None)] or [hints[f.name]]
        props[f.name] = {"type": "number" if base[0] is float else "string", "description": FIELD_HELP[f.name]}
    return {
        "name": "registra_bolletta",
        "description": "Registra i campi estratti dalla bolletta",
        "input_schema": {"type": "object", "properties": props, "required": ["commodity", "period_start", "period_end"]},
    }


def extract_bill(path: str, client=None, layouts: list[Layout] = ()) -> tuple[dict, str]:
    """Restituisce (campi, metodo): "regole", «layout …» (forniti o insegnati) o "LLM". `client` è iniettabile per i test.
    In caso di fallimento solleva ExtractionError con i campi parziali già letti dalle regole."""
    return extract_text(pdf_text(path).strip(), client, layouts)


def extract_text(text: str, client=None, layouts: list[Layout] = ()) -> tuple[dict, str]:
    if not text:
        raise NoTextError("Il PDF è un'immagine, senza testo da leggere. Scarica dal sito o dall'area clienti del fornitore la bolletta in PDF digitale (non una scansione o una foto)")
    parsed = parse_bill_text(text)
    if parsed.complete:
        return parsed.fields, "regole"
    fields, used = apply_layouts(text, parsed.fields, [*builtin_layouts(), *layouts])
    if all(f in fields for f in REQUIRED):
        return fields, f"layout «{', '.join(used)}»"
    missing = [f for f in REQUIRED if f not in fields]
    if client is None and not available():
        raise ExtractionError(f"lettura automatica incompleta (mancano: {', '.join(missing)})", fields)
    try:
        llm_fields = _llm_extract(text, client)
    except ExtractionError as e:
        raise ExtractionError(str(e), fields) from e
    return {**llm_fields, **fields}, "LLM"  # i campi delle regole, controllati, prevalgono


def _llm_extract(text: str, client) -> dict:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    tool = tool_schema()
    try:
        response = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
            max_tokens=2048,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": PROMPT.format(text=text)}],
        )
    except Exception as e:  # errori di rete/API: l'utente ripiega sul modulo manuale
        raise ExtractionError(f"Chiamata all'API fallita: {e}") from e
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise ExtractionError("Risposta del modello senza dati strutturati")
