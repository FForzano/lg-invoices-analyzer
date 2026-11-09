"""Analisi di una fornitura: lega database e servizi (consumo, confronto, verdetto)."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from . import db
from .models import Offer
from .services.offer_filter import OfferFilter
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


def analyze(commodity: str, today: date | None = None, power_kw: float | None = None, flt: OfferFilter | None = None) -> Analysis:
    """Analisi dei dati del profilo attivo."""
    return analyze_data(commodity, db.list_bills(commodity), db.list_offers(commodity), db.get_settings(), db.get_index_factors(), today, power_kw, flt)


def analyze_data(commodity: str, bills: list, all_offers: list[Offer], settings: dict, factors: dict, today: date | None = None, power_kw: float | None = None, flt: OfferFilter | None = None) -> Analysis:
    """Lo stesso calcolo su dati qualsiasi: serve anche alla simulazione pubblica, che non ha profilo né database dell'utente."""
    today = today or date.today()
    result = Analysis(commodity, settings)
    index = "pun" if commodity == "power" else "psv"
    mult = season_multiplier(consumption_profile(commodity), factors[index])
    result.season_multiplier = mult
    # PUN/PSV nelle impostazioni sono medie annue: per la fornitura analizzata si usa la media sui mesi di consumo
    result.assumptions = a = Assumptions(
        settings["pun"] * (mult if index == "pun" else 1), settings["psv"] * (mult if index == "psv" else 1),
        settings["default_power_kw"], settings["loss_pct"], settings["dispatching_extra"],
    )
    result.consumption = c = annual_consumption(bills)
    if c and power_kw and commodity == "power":  # potenza scelta nel confronto al posto di quella delle bollette
        result.consumption = c = replace(c, power_kw=power_kw)
    if commodity == "power":
        result.power_advice = power_advice(bills)
    result.has_current = any(o.is_current for o in all_offers)
    # le metà di offerte luce+gas valgono solo se sottoscritte insieme: fuori dal confronto singolo
    # con un filtro, la «migliore alternativa» è la migliore tra le offerte che lo rispettano (l'attuale resta sempre)
    offers = [o for o in all_offers if not o.dual_with and (flt is None or o.is_current or flt.keep(o))]
    half = None if flt is None else replace(flt, bonus=False)  # luce+gas: il bonus si guarda sulla coppia (analyze_dual)
    if c:
        current = next((o for o in all_offers if o.is_current), None)
        power = (c.power_kw or settings["default_power_kw"]) if commodity == "power" else None
        location = Location(settings["region"], settings["province"], settings["comune"], bool(settings.get("resident", 1)), power, current.supplier if current else "")
        result.ranked, result.skipped = compare(offers, c, a, today, location)
        result.verdict = make_verdict(result.ranked, offers, c, a, today, location)
        result.dual_ranked, _ = compare([o for o in all_offers if o.is_current or (o.dual_with and (half is None or half.keep(o)))], c, a, today, location)
    return result


@dataclass
class DualAnalysis:
    bundles: list[Bundle]
    verdict: DualVerdict | None


def analyze_dual(power: Analysis, gas: Analysis, flt: OfferFilter | None = None) -> DualAnalysis:
    bundles = pair_bundles(power.dual_ranked, gas.dual_ranked)
    if flt is not None:
        bundles = [b for b in bundles if flt.keep_bundle(b.power.offer, b.gas.offer)]
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
