"""Analisi di una fornitura: lega database e servizi (consumo, confronto, verdetto)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import db
from .services.consumption import Consumption, annual_consumption
from .services.seasonality import consumption_profile, season_multiplier
from .services.pricing import Assumptions, Location, Ranked, compare
from .services.verdict import Verdict, make_verdict


@dataclass
class Analysis:
    commodity: str
    settings: dict
    consumption: Consumption | None = None
    assumptions: Assumptions | None = None
    ranked: list[Ranked] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    verdict: Verdict | None = None
    has_current: bool = False
    season_multiplier: float = 1.0  # prezzo medio dell'indice sui mesi di consumo / media annua


def analyze(commodity: str, today: date | None = None) -> Analysis:
    today = today or date.today()
    settings = db.get_settings()
    result = Analysis(commodity, settings)
    index = "pun" if commodity == "power" else "psv"
    mult = season_multiplier(consumption_profile(commodity), db.get_index_factors()[index])
    result.season_multiplier = mult
    # PUN/PSV nelle impostazioni sono medie annue: per la fornitura analizzata si usa la media sui mesi di consumo
    result.assumptions = a = Assumptions(
        settings["pun"] * (mult if index == "pun" else 1), settings["psv"] * (mult if index == "psv" else 1),
        settings["default_power_kw"], settings["loss_pct"], settings["dispatching_extra"],
    )
    result.consumption = c = annual_consumption(db.list_bills(commodity))
    offers = db.list_offers(commodity)
    result.has_current = any(o.is_current for o in offers)
    if c:
        location = Location(settings["region"], settings["province"], settings["comune"])
        result.ranked, result.skipped = compare(offers, c, a, today, location)
        result.verdict = make_verdict(result.ranked, offers, c, a, today, location)
    return result
