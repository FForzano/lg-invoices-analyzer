from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("settings", __name__)


def _code(raw: str) -> str:
    """Codice ISTAT: solo cifre (può essere vuoto, per non filtrare per quel livello)."""
    raw = raw.strip()
    if raw and not raw.isdigit():
        raise ValueError(raw)
    return raw


@bp.route("/settings", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            db.save_settings({
                k: _code(request.form[k]) if isinstance(default, str) else float(request.form[k].replace(",", "."))
                for k, default in db.SETTING_DEFAULTS.items()
            })
        except (KeyError, ValueError):
            flash("Valori non validi.", "warn")
        else:
            flash("Impostazioni salvate.", "info")
        return redirect(url_for("settings.index"))
    return render_template("settings.html", s=db.get_settings())


@bp.post("/settings/use-recent")
def use_recent():
    s = db.get_settings()
    if "pun_recent" not in s:
        flash("Prezzi recenti non disponibili: aggiorna dal Portale Offerte.", "warn")
    else:
        db.save_settings({"pun": s["pun_recent"], "psv": s["psv_recent"]})
        flash("PUN e PSV assunti aggiornati ai prezzi recenti.", "info")
    return redirect(url_for("settings.index"))
