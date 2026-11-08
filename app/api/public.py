"""Simulazione pubblica (senza account): «Carica la tua ultima bolletta». Con il login attivo è la porta d'ingresso della landing.

Niente viene salvato: il PDF si legge in memoria e si scarta, non si scrive nulla nel database. La lettura usa solo regole e layout
(mai l'LLM: chiunque può chiamare questo endpoint e non deve consumare la chiave dell'amministratore). Il confronto è sul catalogo
condiviso, con una sola bolletta: stima approssimativa, e lo dice."""
from __future__ import annotations

from flask import jsonify, request
from pypdf.errors import PyPdfError

from .. import analysis, auth, db, ratelimit
from ..models import Bill, Offer
from ..services import extraction
from ..services.bill_parser import parse_offer_terms
from . import ApiError, bp, dump
from .compare import head

MAX_PDF = 6 * 1024 * 1024
SIMULATIONS_PER_10_MIN = 10


@bp.post("/simulate")
def simulate():
    if not auth.enabled():
        raise ApiError("Non disponibile.", 404)
    ratelimit.check("simulate", SIMULATIONS_PER_10_MIN, 600, "simulazioni")
    if (request.content_length or 0) > MAX_PDF + 100_000:
        raise ApiError("Il file è troppo grande (massimo 6 MB).", 413)
    file = request.files.get("pdf")
    if not file or not file.filename:
        raise ApiError("Seleziona un file PDF.")
    data = file.read(MAX_PDF + 1)
    if len(data) > MAX_PDF:
        raise ApiError("Il file è troppo grande (massimo 6 MB).", 413)
    try:
        text = extraction.pdf_text(data).strip()
        fields, method = extraction.extract_text(text, layouts=db.list_layouts(), allow_llm=False)
        bill = Bill(**fields).with_derived_consumption()
    except PyPdfError:
        raise ApiError("Il file non è un PDF valido.") from None
    except extraction.NoTextError as e:
        raise ApiError(str(e) + ".", 422) from None
    except extraction.ExtractionError as e:
        raise ApiError(f"Non riesco a leggere questa bolletta in automatico: {e}. Registrandoti puoi inserirla a mano.", 422) from None
    except (TypeError, ValueError):
        raise ApiError("Non riesco a leggere questa bolletta: formato non riconosciuto.", 422) from None

    terms = parse_offer_terms(text, bill.commodity)
    current = Offer(**terms.offer, is_current=True, source="bolletta:simulazione") if terms else None
    catalog = db.list_catalog_offers(bill.commodity)
    # senza profilo non si conosce la zona: si considerano solo le offerte valide ovunque (le altre vanno verificate caso per caso)
    settings = {**db.get_global_settings(), "region": "", "province": "", "comune": ""}
    try:
        result = analysis.analyze_data(bill.commodity, [bill], [*catalog, *([current] if current else [])], settings, db.get_index_factors())
    except (TypeError, ValueError):
        raise ApiError("Non riesco a stimare questa bolletta: dati insufficienti.", 422) from None
    alternatives = [r for r in result.ranked if not r.offer.is_current][:3]
    return jsonify(
        commodity=bill.commodity, method=method, catalog_size=len(catalog),
        bill={k: getattr(bill, k) for k in ("supplier", "period_start", "period_end", "consumption", "total_eur", "reading_type")},
        analysis={k: v for k, v in head(result).items() if k != "settings"},
        current_offer={"name": current.name, "supplier": current.supplier} if current else None,
        alternatives=dump(alternatives),
    )
