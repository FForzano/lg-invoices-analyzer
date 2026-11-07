from flask import Blueprint, abort, render_template, request

from .. import analysis
from ..models import COMMODITIES

bp = Blueprint("compare", __name__)
TOP = 30  # righe mostrate; con l'import ARERA le offerte sono migliaia


@bp.get("/compare")
def index():
    commodity = request.args.get("commodity", "power")
    if commodity not in COMMODITIES:
        abort(404)
    result = analysis.analyze(commodity)
    return render_template("compare.html", a=result, ranked=result.ranked[:TOP], total=len(result.ranked))
