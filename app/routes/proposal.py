import dataclasses

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import analysis, db, forms
from ..models import COMMODITIES, Offer
from ..services.proposal import ALWAYS_CHECK, Proposal, checklist

bp = Blueprint("proposal", __name__)


def _parse(form) -> Proposal:
    """Supplier e nome sono facoltativi nel form: la proposta non entra nel catalogo."""
    data = {k: v for k, v in form.items() if v != ""}
    offer = forms.parse(Offer, {"supplier": "Proposta", "name": "Proposta ricevuta", **data})
    return Proposal(offer, form.get("id", type=int), form.get("contact") or None,
                    form.get("received_on") or None, form.get("notes") or None)


def _values(p: Proposal) -> dict:
    return {**dataclasses.asdict(p.offer), "id": p.id, "contact": p.contact, "received_on": p.received_on, "notes": p.notes}


def _render_form(v, **extra):
    return render_template("proposal.html", v=v, id=v.get("id"), saved_count=len(db.list_proposals()), **extra)


@bp.get("/proposal")
def index():
    """Valuta una proposta ricevuta (es. da un operatore); con ?from=<id> riparte da una salvata."""
    saved = request.args.get("from", type=int)
    if saved:
        p = db.get_proposal(saved) or abort(404)
        return _render_form(_values(p))
    return _render_form({"commodity": request.args.get("commodity", "power")})


@bp.post("/proposal")
def evaluate():
    try:
        p = _parse(request.form)
        base, est, verdict = analysis.evaluate_proposal(p.offer.commodity, p.offer)
    except ValueError as e:
        flash(str(e), "warn")
        return _render_form(request.form), 400
    return _render_form(request.form, a=base, est=est, verdict=verdict, offer=p.offer)


@bp.post("/proposal/save")
def save():
    try:
        p = _parse(request.form)
    except ValueError as e:
        flash(str(e), "warn")
        return _render_form(request.form), 400
    try:
        id = db.save_proposal(p)
    except LookupError:
        abort(404)
    return redirect(url_for("proposal.show", id=id))


@bp.get("/proposal/saved")
def saved():
    return render_template("proposal_saved.html", proposals=db.list_proposals())


@bp.get("/proposal/<int:id>")
def show(id: int):
    p = db.get_proposal(id) or abort(404)
    try:
        base, est, verdict = analysis.evaluate_proposal(p.offer.commodity, p.offer)
    except ValueError as e:  # prezzi non ancora completi: il promemoria resta utile
        flash(str(e), "warn")
        base = est = verdict = None
    return render_template("proposal_show.html", p=p, offer=p.offer, a=base, est=est, verdict=verdict,
                           items=checklist(p.offer), always=ALWAYS_CHECK)


@bp.post("/proposal/<int:id>/delete")
def delete(id: int):
    db.delete_proposal(id)
    return redirect(url_for("proposal.saved"))
