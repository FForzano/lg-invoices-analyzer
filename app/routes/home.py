from datetime import date

from flask import Blueprint, render_template

from .. import analysis, db
from ..models import COMMODITIES
from ..services.alerts import build_alerts

bp = Blueprint("home", __name__)


@bp.get("/")
def index():
    alerts = build_alerts(db.list_bills(), db.list_offers(), date.today())
    analyses = [analysis.analyze(c) for c in COMMODITIES]
    dual = analysis.analyze_dual(*analyses)
    return render_template("index.html", alerts=alerts, analyses=analyses, dual=dual)


@bp.get("/health")
def health():
    """Per healthcheck del container: nessuna query, risponde se l'app è su."""
    return "ok"
