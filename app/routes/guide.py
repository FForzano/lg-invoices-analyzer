from flask import Blueprint, render_template

bp = Blueprint("guide", __name__)


@bp.get("/guide")
def index():
    return render_template("guide.html")
