import dataclasses

from flask import jsonify, request

from .. import analysis, db, forms
from ..models import Offer
from ..services.proposal import ALWAYS_CHECK, Proposal, checklist
from . import ApiError, bp, dump, msg
from .bills import strs
from .compare import head


def _parse(data: dict) -> Proposal:
    """Supplier e nome sono facoltativi nel form: la proposta non entra nel catalogo."""
    form = {k: v for k, v in strs(data).items() if v != ""}
    offer = forms.parse(Offer, {"supplier": "Proposta", "name": "Proposta ricevuta", **form})
    pid = form.get("id")
    return Proposal(offer, int(pid) if pid else None, form.get("contact"), form.get("received_on"), form.get("notes"))


def _values(p: Proposal) -> dict:
    return {**dataclasses.asdict(p.offer), "id": p.id, "contact": p.contact, "received_on": p.received_on, "notes": p.notes}


def _evaluation(offer: Offer) -> dict:
    base, est, verdict = analysis.evaluate_proposal(offer.commodity, offer)
    best = next((r for r in base.ranked if not r.offer.is_current), None)  # per confronto: la migliore offerta pubblicata
    return {"analysis": head(base), "estimate": dump(est), "verdict": dump(verdict), "best": dump(best)}


@bp.post("/proposals/evaluate")
def evaluate():
    try:
        p = _parse(request.get_json(silent=True) or {})
        return jsonify(**_evaluation(p.offer))
    except ValueError as e:
        raise ApiError(str(e)) from None


@bp.get("/proposals")
def list_proposals():
    return jsonify(items=[{**_values(p), "created_at": p.created_at} for p in db.list_proposals()])


@bp.post("/proposals")
def save_proposal():
    try:
        p = _parse(request.get_json(silent=True) or {})
    except ValueError as e:
        raise ApiError(str(e)) from None
    try:
        pid = db.save_proposal(p)
    except LookupError:
        raise ApiError("Proposta non trovata.", 404) from None
    return jsonify(id=pid, messages=[msg("info", "Proposta salvata.")])


@bp.get("/proposals/<int:id>")
def get_proposal(id: int):
    p = db.get_proposal(id)
    if p is None:
        raise ApiError("Proposta non trovata.", 404)
    out = {"proposal": _values(p), "checklist": checklist(p.offer), "always_check": ALWAYS_CHECK, "messages": []}
    try:
        out.update(_evaluation(p.offer))
    except ValueError as e:  # prezzi non ancora completi: il promemoria resta utile
        out["messages"].append(msg("warn", str(e)))
    return jsonify(out)


@bp.delete("/proposals/<int:id>")
def delete_proposal(id: int):
    db.delete_proposal(id)
    return jsonify(ok=True)
