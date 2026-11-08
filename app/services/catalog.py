"""Aggiornamento del catalogo offerte e di PUN/PSV dal Portale Offerte ARERA. Lo usano l'API (solo amministratori)
e il comando `flask --app app import-offers` (cron senza passare dal web)."""
from __future__ import annotations

from .. import db
from . import arera


def refresh_catalog() -> list[dict]:
    """Scarica e sostituisce le offerte importate, poi aggiorna stagionalità e prezzi recenti. Restituisce i messaggi
    (`{"level", "text"}`); alza `arera.AreraError` se il download delle offerte fallisce."""
    offers, skipped = arera.fetch_offers()
    n = db.replace_imported_offers(offers, arera.SOURCE_PREFIX)
    detail = ", ".join(f"{count} {why}" for why, count in skipped.items())
    messages = [{"level": "info", "text": f"Importate {n} offerte domestiche dal Portale Offerte" + (f" (scartate: {detail})." if detail else ".")}]
    try:
        factors, recent = arera.fetch_index_history()
        db.save_index_factors(factors)
        db.save_settings({"pun_recent": recent["pun"], "psv_recent": recent["psv"], "recent_until": recent["until"]})
        messages.append({"level": "info", "text": "Stagionalità e prezzi recenti di PUN/PSV aggiornati. Puoi adottare i prezzi recenti in Impostazioni."})
    except arera.AreraError as e:
        messages.append({"level": "warn", "text": f"{e}: uso i valori predefiniti."})
    return messages
