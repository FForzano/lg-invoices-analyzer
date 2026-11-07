from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from .. import db

bp = Blueprint("profiles", __name__)
MAX_NAME = 60


def _name() -> str:
    name = request.form.get("name", "").strip()
    if not name or len(name) > MAX_NAME:
        raise ValueError
    return name


def _safe_next(target: str) -> str:
    """Solo percorsi interni: il valore arriva da un campo del form."""
    return target if target.startswith("/") and not target.startswith("//") else url_for("home.index")


@bp.get("/profiles")
def index():
    counts = {r["profile_id"]: r["n"] for r in db.get_db().execute("SELECT profile_id, count(*) AS n FROM bills GROUP BY profile_id")}
    return render_template("profiles.html", counts=counts)


@bp.post("/profiles")
def create():
    try:
        name = _name()
    except ValueError:
        flash(f"Il nome è obbligatorio (massimo {MAX_NAME} caratteri).", "warn")
        return redirect(url_for("profiles.index"))
    here = db.current_profile()  # località e potenza di partenza: quelle del profilo attivo
    session["profile_id"] = db.add_profile(name, here["region"], here["province"], here["comune"], here["default_power_kw"])
    flash(f"Profilo «{name}» creato e selezionato: controlla località e potenza in Impostazioni.", "info")
    return redirect(url_for("settings.index"))


@bp.post("/profiles/switch")
def switch():
    wanted = request.form.get("profile_id", type=int)
    if wanted not in {p["id"] for p in db.list_profiles()}:
        abort(404)
    session["profile_id"] = wanted
    return redirect(_safe_next(request.form.get("next", "")))


@bp.post("/profiles/<int:id>/rename")
def rename(id: int):
    if id not in {p["id"] for p in db.list_profiles()}:
        abort(404)
    try:
        db.rename_profile(id, _name())
    except ValueError:
        flash(f"Il nome è obbligatorio (massimo {MAX_NAME} caratteri).", "warn")
    return redirect(url_for("profiles.index"))


@bp.post("/profiles/<int:id>/delete")
def delete(id: int):
    profiles = db.list_profiles()
    if id not in {p["id"] for p in profiles}:
        abort(404)
    if len(profiles) == 1:
        flash("Deve esistere almeno un profilo.", "warn")
        return redirect(url_for("profiles.index"))
    for name in db.delete_profile(id):
        (Path(current_app.config["PDF_DIR"]) / name).unlink(missing_ok=True)
    if session.get("profile_id") == id:
        session.pop("profile_id")
    flash("Profilo eliminato con le sue bollette.", "info")
    return redirect(url_for("profiles.index"))
