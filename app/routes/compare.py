from flask import Blueprint, abort, render_template, request

from .. import analysis
from ..models import COMMODITIES
from ..services.paging import paginate

bp = Blueprint("compare", __name__)
PER_PAGE = 30  # con l'import ARERA le offerte sono migliaia


@bp.get("/compare")
def index():
    commodity = request.args.get("commodity", "power")
    if commodity not in COMMODITIES:
        abort(404)
    result = analysis.analyze(commodity)
    page = paginate(result.ranked, request.args.get("page", 1, type=int), PER_PAGE)
    return render_template("compare.html", a=result, page=page)
