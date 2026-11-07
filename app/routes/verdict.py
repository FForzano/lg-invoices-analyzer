from flask import Blueprint, redirect, url_for

bp = Blueprint("verdict", __name__)


@bp.get("/verdict")
def index():
    """Il verdetto sta in home: questo URL esiste per i redirect dopo il caricamento di una bolletta."""
    return redirect(url_for("home.index"))
