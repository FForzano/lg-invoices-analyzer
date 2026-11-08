from datetime import date

from flask import jsonify, request

from .. import analysis, db
from ..models import COMMODITIES
from ..services.alerts import build_alerts
from ..services.paging import paginate
from . import ApiError, bp, dump, msg

PER_PAGE = 30  # con l'import ARERA le offerte sono migliaia


def page_info(p) -> dict:
    return {"number": p.number, "pages": p.pages, "total": p.total}


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
    a = analysis.analyze(commodity)
    page = paginate(a.ranked, request.args.get("page", 1, type=int), PER_PAGE)
    return jsonify(analysis=head(a), items=dump(page.items), page=page_info(page))


@bp.get("/compare-dual")
def compare_dual():
    power, gas = (analysis.analyze(c) for c in COMMODITIES)
    dual = analysis.analyze_dual(power, gas)
    page = paginate(dual.bundles, request.args.get("page", 1, type=int), PER_PAGE)
    return jsonify(power=head(power), gas=head(gas), verdict=dump(dual.verdict), items=dump(page.items), page=page_info(page))
