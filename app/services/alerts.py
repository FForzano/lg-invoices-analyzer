"""Avvisi mostrati in home."""
from __future__ import annotations

import calendar
from datetime import date

from ..models import COMMODITIES, COMMODITY_LABEL, Bill, Offer

EXPIRY_WARNING_DAYS = 60


def terms_end(offer: Offer) -> date | None:
    """Fine delle condizioni economiche: attivazione + durata. None se manca uno dei due."""
    if not (offer.started_on and offer.duration_months):
        return None
    start = date.fromisoformat(offer.started_on)
    index = start.month - 1 + offer.duration_months
    year, month = start.year + index // 12, index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def build_alerts(bills: list[Bill], offers: list[Offer], today: date) -> list[tuple[str, str]]:
    """Restituisce coppie (livello, messaggio), livello 'warn' o 'info'."""
    alerts: list[tuple[str, str]] = []
    for commodity in COMMODITIES:
        label = COMMODITY_LABEL[commodity]
        current = next((o for o in offers if o.commodity == commodity and o.is_current), None)
        if current is None:
            alerts.append(("info", f"{label}: nessuna offerta marcata come «attuale», il risparmio non può essere calcolato."))
        elif end := terms_end(current):
            # dopo l'attivazione la scadenza che conta è la fine delle condizioni, non quella dell'offerta in catalogo
            days = (end - today).days
            if days < 0:
                alerts.append((
                    "warn",
                    f"{label}: le condizioni economiche dell'offerta attuale sono terminate il {end.isoformat()}: "
                    "il prezzo potrebbe essere già cambiato. Controlla l'ultima bolletta e confronta le offerte.",
                ))
            elif days <= EXPIRY_WARNING_DAYS:
                alerts.append((
                    "warn",
                    f"{label}: le condizioni dell'offerta attuale finiscono tra {days} giorni ({end.isoformat()}). "
                    "Dopo il venditore può cambiare il prezzo: confronta le offerte e valuta di cambiare.",
                ))
        else:
            if current.duration_months and not current.started_on:
                alerts.append((
                    "info",
                    f"{label}: l'offerta attuale ha condizioni valide {current.duration_months} mesi. "
                    "Indica la data di attivazione (Offerte, modifica) per avere un avviso prima della fine.",
                ))
            if current.expires_on:
                days = (date.fromisoformat(current.expires_on) - today).days
                if days < 0:
                    alerts.append(("warn", f"{label}: l'offerta attuale è scaduta il {current.expires_on}."))
                elif days <= EXPIRY_WARNING_DAYS:
                    alerts.append(("warn", f"{label}: l'offerta attuale scade tra {days} giorni ({current.expires_on})."))

        latest = max((b for b in bills if b.commodity == commodity), key=lambda b: b.period_end, default=None)
        if latest and latest.social_bonus_expires_on:
            days = (date.fromisoformat(latest.social_bonus_expires_on) - today).days
            if days < 0:
                alerts.append(("warn", f"{label}: il bonus sociale risulta scaduto il {latest.social_bonus_expires_on}."))
            elif days <= EXPIRY_WARNING_DAYS:
                alerts.append((
                    "warn",
                    f"{label}: il bonus sociale scade tra {days} giorni ({latest.social_bonus_expires_on}): "
                    "presenta DSU/ISEE per rinnovarlo.",
                ))
        if latest and latest.reading_type == "stimata":
            alerts.append((
                "info",
                f"{label}: l'ultima bolletta ({latest.period_end}) ha una lettura stimata. "
                "Fai l'autolettura dal 1 al 5 del mese.",
            ))
    return alerts
