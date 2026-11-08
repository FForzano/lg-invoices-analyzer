"""Analisi di una fornitura: lega database e servizi (consumo, confronto, verdetto)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import db
from .models import Offer
from .services.consumption import Consumption, annual_consumption
from .services.power import PowerAdvice, power_advice
from .services.seasonality import consumption_profile, season_multiplier
from .services.pricing import Assumptions, Bundle, Estimate, Location, Ranked, compare, estimate, pair_bundles
from .services.verdict import DualVerdict, Verdict, ProposalVerdict, judge_proposal, make_dual_verdict, make_verdict


@dataclass
class Analysis:
    commodity: str
    settings: dict
    consumption: Consumption | None = None
    assumptions: Assumptions | None = None
    ranked: list[Ranked] = field(default_factory=list)
    dual_ranked: list[Ranked] = field(default_factory=list)  # attuale + metà di offerte luce+gas
    skipped: list[str] = field(default_factory=list)
    verdict: Verdict | None = None
    has_current: bool = False
    power_advice: PowerAdvice | None = None  # solo luce
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
    bills = db.list_bills(commodity)
    result.consumption = c = annual_consumption(bills)
    if commodity == "power":
        result.power_advice = power_advice(bills)
    all_offers = db.list_offers(commodity)
    result.has_current = any(o.is_current for o in all_offers)
    # le metà di offerte luce+gas valgono solo se sottoscritte insieme: fuori dal confronto singolo
    offers = [o for o in all_offers if not o.dual_with]
    if c:
        location = Location(settings["region"], settings["province"], settings["comune"])
        result.ranked, result.skipped = compare(offers, c, a, today, location)
        result.verdict = make_verdict(result.ranked, offers, c, a, today, location)
        result.dual_ranked, _ = compare([o for o in all_offers if o.dual_with or o.is_current], c, a, today, location)
    return result


@dataclass
class DualAnalysis:
    bundles: list[Bundle]
    verdict: DualVerdict | None


def analyze_dual(power: Analysis, gas: Analysis) -> DualAnalysis:
    bundles = pair_bundles(power.dual_ranked, gas.dual_ranked)
    return DualAnalysis(bundles, make_dual_verdict(bundles, power.verdict, gas.verdict))


def evaluate_proposal(commodity: str, proposal: Offer, today: date | None = None) -> tuple[Analysis, Estimate | None, ProposalVerdict | None]:
    """Stima una proposta non salvata e la confronta con l'offerta attuale (verdetto None se manca).
    Solleva ValueError se alla proposta mancano i prezzi."""
    base = analyze(commodity, today)
    if base.consumption is None:
        return base, None, None
    est = estimate(proposal, base.consumption, base.assumptions)
    current = next((o for o in db.list_offers(commodity) if o.is_current), None)
    verdict = judge_proposal(proposal, current, base.consumption, base.assumptions) if current else None
    return base, est, verdict
