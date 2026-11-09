"""Stima del costo annuo della sola parte decisa dal fornitore.

Trasporto, oneri di sistema e imposte sono uguali per tutti e restano fuori.
Bonus sociali e canone TV non dipendono dal fornitore e restano fuori."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from ..models import Offer
from .consumption import Consumption


@dataclass(frozen=True)
class Assumptions:
    pun: float  # €/kWh
    psv: float  # €/Smc
    default_power_kw: float
    loss_pct: float = 10.0  # perdite di rete assunte quando l'offerta non le specifica
    dispatching_extra: float = 0.0  # €/kWh assunti per le offerte con dispacciamento/capacità a parte


@dataclass(frozen=True)
class Location:
    """Dove e per chi si cerca l'offerta: località ISTAT, residenza, potenza impegnata e fornitore attuale."""
    region: str = ""
    province: str = ""
    comune: str = ""
    resident: bool = True
    power_kw: float | None = None  # solo luce
    supplier: str = ""  # fornitore dell'offerta attuale

    def tokens(self) -> set[str]:
        return {t for t in (f"R{self.region}" if self.region else "", f"P{self.province}" if self.province else "",
                            f"C{self.comune}" if self.comune else "") if t}


NEW_CUSTOMERS_ONLY = re.compile(r"\b(solo|riservat\w+|esclusivamente|valid\w+)\b[^.]{0,40}\bnuov[oi] client\w*", re.I)


def _same_supplier(a: str, b: str) -> bool:
    """«enel.it» e «Enel Energia» sono lo stesso fornitore: confronto sulle sole lettere, per inclusione."""
    x, y = (re.sub(r"[^a-z0-9]", "", re.sub(r"\.(it|com|eu)\b.*", "", v.lower())) for v in (a, b))
    return bool(x) and bool(y) and (x in y or y in x)


def available_in(offer: Offer, location: Location, annual: float | None = None) -> bool:
    """L'offerta vale per te: zona, residenza, potenza, consumo annuo e, se riservata ai nuovi clienti, fornitore diverso dall'attuale."""
    if offer.zones and not set(offer.zones.split(",")) & location.tokens():
        return False
    if offer.residency and (offer.residency == "resident") != location.resident:
        return False
    if offer.commodity == "power" and location.power_kw is not None:
        if (offer.power_min and location.power_kw < offer.power_min) or (offer.power_max and location.power_kw > offer.power_max):
            return False
    if annual is not None and ((offer.consumption_min and annual < offer.consumption_min) or (offer.consumption_max and annual > offer.consumption_max)):
        return False
    if offer.valid_for:  # specifiche SII: cambio fornitore (switch), prima attivazione, riattivazione, voltura, sempre
        cases = set(offer.valid_for.split(","))
        if "always" not in cases and "switch" not in cases:
            return False  # non vale per chi cambia fornitore
        if cases == {"switch"} and location.supplier and _same_supplier(offer.supplier, location.supplier):
            return False  # vale solo cambiando fornitore: non è proponibile dal fornitore attuale
    if location.supplier and offer.conditions and NEW_CUSTOMERS_ONLY.search(offer.conditions) and _same_supplier(offer.supplier, location.supplier):
        return False
    return True


@dataclass(frozen=True)
class Estimate:
    energy: float
    fixed_fee: float
    power_fee: float
    discount: float

    @property
    def total(self) -> float:
        return self.energy + self.fixed_fee + self.power_fee - self.discount


@dataclass(frozen=True)
class Ranked:
    offer: Offer
    estimate: Estimate
    saving: float | None  # rispetto all'offerta attuale; positivo = si risparmia


def unit_price(offer: Offer, a: Assumptions, band: int | None = None) -> float:
    """Prezzo dell'energia in €/kWh (luce, `band` 0-2 per F1-F3) o €/Smc (gas)."""
    base = _base_price(offer, a, band)
    if offer.commodity == "power" and offer.dispatching_extra and offer.avg_price is None:
        base += a.dispatching_extra
    return base


# Indici per cui non c'è un valore assunto: l'offerta non si stima (il Portale usa Psbil come PSV, noi pure)
UNSUPPORTED_INDEXES = {"ttf": "TTF", "pe": "PE", "pfor": "Pfor", "cmem": "Cmem", "other": "non standard"}


def _base_price(offer: Offer, a: Assumptions, band: int | None) -> float:
    if offer.avg_price is not None:
        return offer.avg_price
    if offer.price_type == "fixed":
        band_prices = (offer.price_f1, offer.price_f2, offer.price_f3)
        if offer.commodity == "power" and band is not None and all(p is not None for p in band_prices):
            return band_prices[band]
        return _need(offer.price, offer, "price")
    if offer.index_name in UNSUPPORTED_INDEXES:
        raise ValueError(f"Offerta «{offer.name}»: indice {UNSUPPORTED_INDEXES[offer.index_name]} non gestito")
    spread = _need(offer.spread, offer, "spread")
    if offer.commodity == "power":
        loss = a.loss_pct if offer.loss_pct is None else offer.loss_pct
        return (a.pun + spread + (offer.dispatching or 0) + (offer.capacity or 0)) * (1 + loss / 100)
    return a.psv + spread + (offer.gas_mgmt or 0) + (offer.pcs_adjustment or 0)


def _need(value, offer: Offer, name: str) -> float:
    if value is None:
        raise ValueError(f"Offerta «{offer.name}»: manca il campo {name}")
    return value


def estimate(offer: Offer, c: Consumption, a: Assumptions) -> Estimate:
    if offer.commodity == "power":
        energy = sum(kwh * unit_price(offer, a, band) for band, kwh in enumerate(c.bands_or_default()))
        power_fee = (offer.power_fee_kw_month or 0) * (c.power_kw or a.default_power_kw) * 12
    else:
        energy = c.total * unit_price(offer, a)
        power_fee = 0.0
    return Estimate(
        energy=energy,
        fixed_fee=(offer.fixed_fee_month or 0) * 12,
        power_fee=power_fee,
        discount=offer.one_off_discount or 0,
    )


def is_expired(offer: Offer, today: date) -> bool:
    return bool(offer.expires_on) and date.fromisoformat(offer.expires_on) < today


def compare(offers: list[Offer], c: Consumption, a: Assumptions, today: date, location: Location = Location()) -> tuple[list[Ranked], list[str]]:
    """Offerte non scadute e valide nella zona (più l'attuale, sempre) ordinate per costo annuo.
    Le offerte con dati insufficienti sono saltate e segnalate nel secondo elemento."""
    estimates: dict[int, Estimate] = {}
    skipped: list[str] = []
    for o in offers:
        if not o.is_current and (is_expired(o, today) or not available_in(o, location, c.total)):
            continue
        try:
            estimates[o.id] = estimate(o, c, a)
        except ValueError as e:
            skipped.append(str(e))
    current = next((o for o in offers if o.is_current and o.id in estimates), None)
    base = estimates[current.id].total if current else None
    ranked = [
        Ranked(o, estimates[o.id], None if base is None else base - estimates[o.id].total)
        for o in offers if o.id in estimates
    ]
    return sorted(ranked, key=lambda r: r.estimate.total), skipped


@dataclass(frozen=True)
class Bundle:
    """Offerta luce+gas dello stesso fornitore: le due metà vanno sottoscritte insieme."""
    power: Ranked
    gas: Ranked
    total: float
    saving: float | None  # rispetto alle due offerte attuali


def pair_bundles(power: list[Ranked], gas: list[Ranked]) -> list[Bundle]:
    """Abbina le metà luce+gas già valutate (`Offer.dual_with`); ordinate per costo annuo totale.
    Una coppia manca se una delle metà è scaduta, fuori zona o non valutabile."""
    gas_by_source = {r.offer.source: r for r in gas if not r.offer.is_current}
    current = [next((r for r in ranked if r.offer.is_current), None) for ranked in (power, gas)]
    base = None if None in current else sum(r.estimate.total for r in current)
    bundles = []
    for p in power:
        g = gas_by_source.get(p.offer.dual_with)
        if g is not None and not p.offer.is_current:
            total = p.estimate.total + g.estimate.total
            bundles.append(Bundle(p, g, total, None if base is None else base - total))
    return sorted(bundles, key=lambda b: b.total)
