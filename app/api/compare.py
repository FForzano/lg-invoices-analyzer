from datetime import date
from urllib.parse import parse_qsl

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


def _chosen_preset() -> dict | None:
    """Il preferito con cui valutare la Home: `?preset=<id>`, `?preset=none` per nessuno, altrimenti quello predefinito."""
    items = db.list_presets()
    wanted = request.args.get("preset", "")
    if wanted == "none":
        return None
    if wanted.isdigit():
        return next((p for p in items if p["id"] == int(wanted)), None)
    return next((p for p in items if p["is_default"]), None)


@bp.get("/home")
def home():
    alerts = build_alerts(db.list_bills(), db.list_offers(), date.today())
    preset = _chosen_preset()
    args = dict(parse_qsl(preset["query"])) if preset else {}
    flt = OfferFilter.from_args(args) if preset else None
    power = float(args["power"]) if args.get("power") else None
    analyses = {c: analysis.analyze(c, flt=flt, power_kw=power if c == "power" else None) for c in COMMODITIES}
    dual = analysis.analyze_dual(*analyses.values(), flt=flt)
    out = {c: head(a) for c, a in analyses.items()}
    if flt:  # trasparenza: se senza filtri la migliore sarebbe un'altra, lo si dice (il filtro non nasconde un'offerta migliore)
        for c, a in analyses.items():
            free = analysis.analyze(c, power_kw=power if c == "power" else None)
            if a.verdict and free.verdict and free.verdict.best.offer.id != a.verdict.best.offer.id:
                b = free.verdict.best
                out[c]["unfiltered_best"] = {"name": b.offer.name, "supplier": b.offer.supplier, "saving": free.verdict.saving, "total": b.estimate.total}
    return jsonify(alerts=[msg(level, text) for level, text in alerts], analyses=out, dual={"verdict": dump(dual.verdict)},
                   filter={"active": preset is not None, "preset": preset, "presets": [{"id": p["id"], "name": p["name"]} for p in db.list_presets()]})


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
