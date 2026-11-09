from datetime import date

from flask import jsonify, request

from .. import analysis, db
from ..models import COMMODITIES
from ..services.consumption import annual_consumption
from ..services.alerts import build_alerts
from ..services.offer_filter import OfferFilter
from ..services.paging import paginate
from . import ApiError, bp, dump, msg

PER_PAGE = 30  # con l'import ARERA le offerte sono migliaia


def page_info(p) -> dict:
    return {"number": p.number, "pages": p.pages, "total": p.total}


def power_arg() -> float | None:
    """Potenza scelta nei filtri del confronto (kW); senza, vale quella delle bollette o del profilo."""
    v = request.args.get("power", type=float)
    return v if v and 0 < v <= 100 else None


def power_default() -> float:
    """Potenza del contratto senza la scelta fatta nei filtri: quella delle bollette, altrimenti quella del profilo."""
    c = annual_consumption(db.list_bills("power"))
    return (c.power_kw if c and c.power_kw else None) or db.get_settings()["default_power_kw"]


def head(a: analysis.Analysis) -> dict:
    """L'analisi senza le classifiche complete (migliaia di offerte): quelle stanno in /compare, paginate."""
    return {k: v for k, v in dump(a).items() if k not in ("ranked", "dual_ranked")}


@bp.get("/home")
def home():
    alerts = build_alerts(db.list_bills(), db.list_offers(), date.today())
    analyses = {c: analysis.analyze(c) for c in COMMODITIES}
    dual = analysis.analyze_dual(*analyses.values())
    return jsonify(alerts=[msg(level, text) for level, text in alerts],
                   analyses={c: head(a) for c, a in analyses.items()}, dual={"verdict": dump(dual.verdict)})


@bp.get("/compare/<commodity>")
def compare(commodity: str):
    if commodity not in COMMODITIES:
        raise ApiError("Fornitura non valida.", 404)
    a = analysis.analyze(commodity, power_kw=power_arg())
    flt = OfferFilter.from_args(request.args)
    ranked = [r for r in a.ranked if r.offer.is_current or flt.keep(r.offer)]  # l'offerta attuale resta sempre: è il termine di paragone
    page = paginate(ranked, request.args.get("page", 1, type=int), PER_PAGE)
    return jsonify(analysis=head(a), items=dump(page.items), page=page_info(page), power_default=power_default() if commodity == "power" else None)


@bp.get("/compare-dual")
def compare_dual():
    power, gas = analysis.analyze("power", power_kw=power_arg()), analysis.analyze("gas")
    dual = analysis.analyze_dual(power, gas)
    flt = OfferFilter.from_args(request.args)
    page = paginate([b for b in dual.bundles if flt.keep_bundle(b.power.offer, b.gas.offer)], request.args.get("page", 1, type=int), PER_PAGE)
    return jsonify(power=head(power), gas=head(gas), verdict=dump(dual.verdict), items=dump(page.items), page=page_info(page), power_default=power_default())
