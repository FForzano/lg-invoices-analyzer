"""Consumo annuo di riferimento per il confronto."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ..models import Bill
from .seasonality import consumption_profile, share_of_year

# Ripartizione tipica usata quando la bolletta non riporta le fasce
DEFAULT_BAND_SPLIT = (0.33, 0.30, 0.37)

MIN_COVERAGE_DAYS = 330  # sotto questa copertura il consumo annuo è una proiezione poco affidabile


@dataclass(frozen=True)
class Consumption:
    total: float  # kWh o Smc annui
    bands: tuple[float, float, float] | None  # solo luce
    power_kw: float | None
    source: str  # descrizione leggibile dell'origine
    days_covered: int = 365  # giorni di consumo realmente noti

    @property
    def partial(self) -> bool:
        return self.days_covered < MIN_COVERAGE_DAYS

    def bands_or_default(self) -> tuple[float, float, float]:
        return self.bands or tuple(self.total * s for s in DEFAULT_BAND_SPLIT)


def annual_consumption(bills: list[Bill]) -> Consumption | None:
    """Preferisce il dato annuo stampato nella bolletta più recente che lo riporta;
    altrimenti proietta a 12 mesi i consumi degli ultimi 12 mesi."""
    if not bills:
        return None
    bills = sorted((b.with_derived_consumption() for b in bills), key=lambda b: b.period_end, reverse=True)
    power_kw = next((b.power_kw for b in bills if b.power_kw), None)

    printed = next((b for b in bills if b.annual_consumption), None)
    if printed:
        bands = (printed.annual_f1, printed.annual_f2, printed.annual_f3)
        return Consumption(
            total=printed.annual_consumption,
            bands=bands if all(b is not None for b in bands) else None,
            power_kw=power_kw,
            source=f"dato annuo stampato nella bolletta del {printed.period_end}",
        )

    latest_end = date.fromisoformat(bills[0].period_end)
    window = [
        b for b in bills
        if b.consumption is not None and date.fromisoformat(b.period_end) > latest_end - timedelta(days=365)
    ]
    if not window:
        return None
    shares = consumption_profile(window[0].commodity)
    days = sum((date.fromisoformat(b.period_end) - date.fromisoformat(b.period_start)).days + 1 for b in window)
    covered = sum(share_of_year(shares, date.fromisoformat(b.period_start), date.fromisoformat(b.period_end)) for b in window)
    scale = 1 / covered  # quota del consumo annuo attesa nei giorni noti, secondo il profilo stagionale tipico
    total = sum(b.consumption for b in window) * scale
    band_values = [[b.kwh_f1, b.kwh_f2, b.kwh_f3] for b in window]
    has_bands = all(all(v is not None for v in row) for row in band_values)
    bands = tuple(sum(row[i] for row in band_values) * scale for i in range(3)) if has_bands else None
    return Consumption(
        total=total, bands=bands, power_kw=power_kw, days_covered=min(days, 365),
        source=f"proiezione da {len(window)} bollette ({days} giorni noti) con profilo stagionale tipico",
    )
