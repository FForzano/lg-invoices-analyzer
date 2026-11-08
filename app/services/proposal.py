"""Proposte ricevute fuori catalogo (es. telefonata): promemoria da verificare nel contratto."""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass

from ..models import SYSTEM_FIELDS, Offer


@dataclass
class Proposal:
    offer: Offer
    id: int | None = None
    contact: str | None = None  # chi l'ha proposta / numero o riferimento della chiamata
    received_on: str | None = None
    notes: str | None = None  # promesse a voce non coperte dai campi (es. «nessuna penale»)
    created_at: str | None = None


def dump_terms(offer: Offer) -> str:
    return json.dumps({k: v for k, v in dataclasses.asdict(offer).items() if k not in SYSTEM_FIELDS})


def load_terms(text: str) -> Offer:
    known = {f.name for f in dataclasses.fields(Offer)} - SYSTEM_FIELDS
    return Offer(**{k: v for k, v in json.loads(text).items() if k in known})


def _n(x: float, unit: str) -> str:
    return f"{x:g} {unit}".replace(".", ",")


def checklist(offer: Offer) -> list[tuple[str, str]]:
    """(voce, valore dichiarato): ciò che nel contratto deve comparire uguale a quanto detto a voce."""
    unit = "€/kWh" if offer.commodity == "power" else "€/Smc"
    rows: list[tuple[str, str]] = [("Fornitore", offer.supplier)]
    if offer.price_type == "fixed":
        bands = [offer.price_f1, offer.price_f2, offer.price_f3]
        if offer.price is not None:
            rows.append(("Prezzo fisso", _n(offer.price, unit)))
        if all(b is not None for b in bands):
            rows.append(("Prezzo per fascia F1 / F2 / F3", " / ".join(_n(b, unit) for b in bands)))
    else:
        rows.append(("Indice di riferimento", "PUN" if offer.commodity == "power" else "PSV"))
        if offer.spread is not None:
            rows.append(("Spread", _n(offer.spread, unit)))
    optional = [
        ("Prezzo medio dichiarato", offer.avg_price, unit), ("Perdite di rete", offer.loss_pct, "%"),
        ("Dispacciamento", offer.dispatching, unit), ("Oneri di capacità", offer.capacity, unit),
        ("Gestione variabile", offer.gas_mgmt, unit), ("Adeguamento PCS", offer.pcs_adjustment, unit),
        ("Quota fissa", offer.fixed_fee_month, "€/mese"), ("Quota potenza", offer.power_fee_kw_month, "€/kW/mese"),
        ("Bonus / sconto una tantum", offer.one_off_discount, "€"), ("Durata delle condizioni", offer.duration_months, "mesi"),
    ]
    rows += [(label, _n(v, u)) for label, v, u in optional if v is not None]
    if offer.dispatching_extra:
        rows.append(("Dispacciamento/capacità", "fatturati a parte"))
    return rows


# domande da chiudere sempre, anche se a voce non se ne è parlato
ALWAYS_CHECK = (
    "Prezzi indicati senza IVA e imposte, come sopra",
    "Cosa succede alla fine del periodo (prezzo dopo la scadenza, rinnovo automatico)",
    "Condizioni e tempi di accredito dei bonus",
    "Costi di attivazione o altre spese una tantum",
    "Penali o vincoli per il recesso",
    "Data di attivazione e fine del contratto attuale",
)
