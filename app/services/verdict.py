"""Verdetto: conviene cambiare offerta? Quanto si risparmia in un anno?"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from ..models import Offer
from .consumption import Consumption
from .pricing import Assumptions, Location, Ranked, compare

MIN_SAVING_EUR = 30.0  # sotto questa soglia (o sotto il 5%) il cambio non vale lo sforzo
MIN_SAVING_PCT = 5.0
SENSITIVITY = (0.8, 1.2)  # PUN/PSV -20% / +20%


@dataclass(frozen=True)
class Verdict:
    current: Ranked
    best: Ranked
    saving: float
    saving_pct: float
    saving_range: tuple[float, float]  # risparmio della stessa offerta con PUN/PSV -20% e +20%
    worthwhile: bool
    robust: bool  # risparmio sopra soglia anche negli scenari estremi


def make_verdict(
    ranked: list[Ranked], offers: list[Offer], c: Consumption, a: Assumptions, today: date, location: Location
) -> Verdict | None:
    """None se manca l'offerta attuale o non ci sono alternative."""
    current = next((r for r in ranked if r.offer.is_current), None)
    best = next((r for r in ranked if not r.offer.is_current), None)
    if current is None or best is None:
        return None
    saving = current.estimate.total - best.estimate.total
    pct = saving / current.estimate.total * 100 if current.estimate.total else 0.0

    scenario_savings = []
    for factor in SENSITIVITY:
        scenario, _ = compare(offers, c, replace(a, pun=a.pun * factor, psv=a.psv * factor), today, location)
        cur = next(r for r in scenario if r.offer.is_current)
        alt = next((r for r in scenario if r.offer.id == best.offer.id), None)
        scenario_savings.append(cur.estimate.total - alt.estimate.total if alt else saving)

    def ok(s: float) -> bool:
        return s >= MIN_SAVING_EUR and s / current.estimate.total * 100 >= MIN_SAVING_PCT

    return Verdict(
        current=current, best=best, saving=saving, saving_pct=pct,
        saving_range=(min(scenario_savings), max(scenario_savings)),
        worthwhile=ok(saving), robust=all(ok(s) for s in scenario_savings),
    )
