"""Stagionalità: profilo tipico dei consumi e andamento mensile di PUN/PSV.

Servono a due cose: proiettare a 12 mesi consumi noti solo per alcuni mesi (il gas d'inverno
pesa molto più che d'estate) e a stimare il prezzo medio dell'indice sui mesi in cui si consuma."""
from __future__ import annotations

import csv
import io
import statistics
from calendar import monthrange
from datetime import date, timedelta

# Quota percentuale del consumo annuo per mese (gen..dic), profilo tipico domestico
_CONSUMPTION_PROFILE = {
    "power": (9.5, 8.5, 8.5, 7.5, 7.5, 8, 9, 8, 7.5, 8, 8.5, 9.5),
    "gas": (19, 15.5, 12, 7, 4, 2, 1.5, 1.5, 2.5, 6.5, 12.5, 16),  # riscaldamento + cottura + acqua calda
}

# Fattori mensili medi (gen..dic, media 1) di PUN/PSV sul 2023-2025; si aggiornano dal Portale Offerte
DEFAULT_INDEX_FACTORS = {
    "pun": (1.17, 1.12, 0.98, 0.91, 0.84, 0.91, 0.96, 1.00, 0.98, 1.03, 1.06, 1.05),
    "psv": (1.24, 1.16, 1.00, 0.96, 0.90, 0.94, 0.89, 0.95, 0.95, 1.00, 1.03, 0.99),
}


def _normalize(values) -> tuple[float, ...]:
    total = sum(values)
    return tuple(v / total for v in values)


def consumption_profile(commodity: str) -> tuple[float, ...]:
    """Quote del consumo annuo per mese, somma 1."""
    return _normalize(_CONSUMPTION_PROFILE[commodity])


def share_of_year(shares: tuple[float, ...], start: date, end: date) -> float:
    """Quota del consumo annuo attesa nei giorni [start, end] (estremi inclusi)."""
    total, day = 0.0, start
    while day <= end:
        total += shares[day.month - 1] / monthrange(day.year, day.month)[1]
        day += timedelta(days=1)
    return total


def season_multiplier(shares: tuple[float, ...], factors: tuple[float, ...]) -> float:
    """Rapporto tra prezzo medio dell'indice sui mesi in cui si consuma e la sua media annua."""
    return sum(s * f for s, f in zip(shares, factors))


def _parse_history(text: str) -> dict[tuple[int, int], tuple[float, float]]:
    """CSV storico del Portale Offerte (`AAAAMM;PUN;PSV;…`, decimali con virgola) -> {(anno, mese): (PUN, PSV)}."""
    data: dict[tuple[int, int], tuple[float, float]] = {}
    for row in list(csv.reader(io.StringIO(text), delimiter=";"))[1:]:
        if len(row) >= 3 and row[0].isdigit() and row[1] and row[2]:
            data[(int(row[0][:4]), int(row[0][4:6]))] = (float(row[1].replace(",", ".")), float(row[2].replace(",", ".")))
    return data


def index_factors_from_csv(text: str, years: int = 3) -> dict[str, tuple[float, ...]]:
    """Fattori mensili di PUN e PSV sugli ultimi `years` anni completi. Ogni anno è normalizzato sulla propria media."""
    data = _parse_history(text)
    complete = sorted(y for y in {y for y, _ in data} if all((y, m) in data for m in range(1, 13)))[-years:]
    if not complete:
        raise ValueError("Il CSV dei prezzi storici non contiene anni completi")
    out = {}
    for i, name in enumerate(("pun", "psv")):
        per_year = []
        for y in complete:
            values = [data[(y, m)][i] for m in range(1, 13)]
            mean = statistics.mean(values)
            per_year.append([v / mean for v in values])
        avg = [statistics.mean(col) for col in zip(*per_year)]
        k = statistics.mean(avg)
        out[name] = tuple(round(v / k, 4) for v in avg)
    return out


def recent_index_levels(text: str, factors: dict[str, tuple[float, ...]], months: int = 3) -> dict[str, float | str]:
    """Livello medio annuo di PUN/PSV implicito negli ultimi `months` mesi del CSV: ogni mese è diviso per il
    proprio fattore stagionale, così un mese invernale non sembra più caro solo perché è inverno."""
    data = _parse_history(text)
    if not data:
        raise ValueError("Il CSV dei prezzi storici è vuoto")
    last = sorted(data)[-months:]
    out: dict[str, float | str] = {
        name: round(statistics.mean(data[ym][i] / factors[name][ym[1] - 1] for ym in last), 6)
        for i, name in enumerate(("pun", "psv"))
    }
    out["until"] = f"{last[-1][0]}-{last[-1][1]:02d}"
    return out
