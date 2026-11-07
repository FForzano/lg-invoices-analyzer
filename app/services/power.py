"""Potenza impegnata: si può scendere di livello senza superare i picchi reali?

La quota potenza di rete è regolata e uguale per tutti i fornitori, quindi questo consiglio è
indipendente dal confronto delle offerte."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ..models import Bill

POWER_STEPS = (1.5, 3.0, 4.5, 6.0, 7.5, 10.0)  # livelli di potenza contrattuale comuni nel domestico, kW
TIGHT_MARGIN = 0.9  # picco oltre il 90% del livello suggerito: margine ridotto
FULL_YEAR_MONTHS = 12


@dataclass(frozen=True)
class PowerAdvice:
    contracted: float
    peak: float  # massimo prelevato nel periodo osservato
    months: int
    suggested: float | None  # livello inferiore sufficiente; None se non c'è margine
    saving_year: float | None  # None se in bolletta manca la quota potenza €/kW/mese

    @property
    def partial(self) -> bool:
        return self.months < FULL_YEAR_MONTHS

    @property
    def tight(self) -> bool:
        return self.suggested is not None and self.peak > self.suggested * TIGHT_MARGIN


def power_advice(bills: list[Bill]) -> PowerAdvice | None:
    """None se mancano potenza impegnata o picchi di potenza nelle bollette di luce."""
    bills = sorted((b for b in bills if b.commodity == "power"), key=lambda b: b.period_end, reverse=True)
    contracted = next((b.power_kw for b in bills if b.power_kw), None)
    if not bills or not contracted:
        return None
    rate = next((b.power_rate_kw_month for b in bills if b.power_rate_kw_month), None)

    with_history = next((b for b in bills if b.annual_max_power_kw), None)
    if with_history:
        # lo storico stampato copre 12 mesi fino a quella bolletta; si aggiungono i picchi successivi
        later = [b.max_power_kw for b in bills if b.period_end > with_history.period_end and b.max_power_kw]
        peak, months = max([with_history.annual_max_power_kw, *later]), FULL_YEAR_MONTHS
    else:
        start = date.fromisoformat(bills[0].period_end) - timedelta(days=365)
        window = [b for b in bills if b.max_power_kw and date.fromisoformat(b.period_end) > start]
        if not window:
            return None
        peak, months = max(b.max_power_kw for b in window), len({b.period_end[:7] for b in window})

    fits = next((s for s in POWER_STEPS if s >= peak), None)
    suggested = fits if fits is not None and fits < contracted else None
    saving = (contracted - suggested) * rate * 12 if suggested is not None and rate else None
    return PowerAdvice(contracted, peak, months, suggested, saving)
