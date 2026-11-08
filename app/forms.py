"""Parsing di form/righe CSV in dataclass, guidato dai tipi dei campi."""
from __future__ import annotations

import dataclasses
import typing
from typing import Mapping, TypeVar

from .models import SYSTEM_FIELDS

# etichette dei form, per messaggi leggibili («Inizio periodo», non `period_start`); il CSV usa invece i nomi dei campi
LABELS = {
    "commodity": "Fornitura", "supplier": "Fornitore", "period_start": "Inizio periodo", "period_end": "Fine periodo",
    "reading_type": "Tipo di lettura", "total_eur": "Totale da pagare", "kwh_f1": "kWh F1", "kwh_f2": "kWh F2", "kwh_f3": "kWh F3",
    "power_kw": "Potenza impegnata", "max_power_kw": "Picco di potenza del mese", "annual_max_power_kw": "Picco di potenza ultimi 12 mesi",
    "power_rate_kw_month": "Quota potenza", "annual_f1": "Annuo F1", "annual_f2": "Annuo F2", "annual_f3": "Annuo F3",
    "mc": "Metri cubi", "coeff_c": "Coefficiente C", "consumption": "Consumo fatturato", "annual_consumption": "Consumo annuo in bolletta",
    "annual_spend": "Spesa annua in bolletta", "social_bonus_expires_on": "Scadenza bonus sociale",
    "name": "Nome offerta", "price_type": "Tipo di prezzo", "price": "Prezzo fisso", "price_f1": "Fisso F1", "price_f2": "Fisso F2",
    "price_f3": "Fisso F3", "avg_price": "Prezzo medio", "spread": "Spread", "fixed_fee_month": "Quota fissa",
    "power_fee_kw_month": "Quota potenza", "one_off_discount": "Sconti/bonus una tantum", "expires_on": "Scadenza",
    "loss_pct": "Perdite di rete", "dispatching": "Dispacciamento", "capacity": "Oneri di capacità", "gas_mgmt": "Gestione variabile",
    "pcs_adjustment": "Adeguamento PCS", "duration_months": "Durata delle condizioni", "started_on": "Attivata il",
}

T = TypeVar("T")


def parse(cls: type[T], data: Mapping[str, str | None], labels: Mapping[str, str] | None = LABELS) -> T:
    """Costruisce `cls` da una mappa di stringhe. Solleva ValueError con un messaggio leggibile."""
    hints = typing.get_type_hints(cls)
    labels = labels or {}
    values: dict = {}
    for f in dataclasses.fields(cls):
        if f.name in SYSTEM_FIELDS:
            continue
        tp = _base_type(hints[f.name])
        raw = (data.get(f.name) or "").strip()
        if tp is bool:
            values[f.name] = raw.lower() in ("on", "1", "true", "si", "sì")
        elif not raw:
            if f.default is dataclasses.MISSING:
                raise ValueError(f"Campo obbligatorio mancante: {labels.get(f.name, f.name)}")
            values[f.name] = None
        else:
            values[f.name] = _cast(tp, raw, f, labels.get(f.name, f.name))
    return cls(**values)


def _base_type(tp):
    args = [a for a in typing.get_args(tp) if a is not type(None)]
    return args[0] if args else tp


def _cast(tp, raw: str, f: dataclasses.Field, label: str):
    try:
        if tp is float:
            return float(raw.replace(",", "."))
        if tp is int:
            return int(raw)
    except ValueError:
        raise ValueError(f"Valore numerico non valido per «{label}»: {raw!r}") from None
    choices = f.metadata.get("choices")
    if choices and raw not in choices:
        raise ValueError(f"Valore non valido per «{label}»: {raw!r} (ammessi: {', '.join(choices)})")
    return raw
