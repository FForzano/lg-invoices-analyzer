"""Storico consumi e costo medio, con confronto anno su anno."""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Bill


@dataclass(frozen=True)
class HistoryRow:
    bill: Bill
    unit_cost: float | None  # totale bolletta / consumo (include voci non confrontabili)
    consumption_yoy: float | None  # variazione % rispetto allo stesso periodo dell'anno prima
    unit_cost_yoy: float | None


def history(bills: list[Bill]) -> list[HistoryRow]:
    bills = sorted((b.with_derived_consumption() for b in bills), key=lambda b: b.period_start, reverse=True)
    by_month = {b.period_start[:7]: b for b in bills}
    rows = []
    for b in bills:
        prev = by_month.get(f"{int(b.period_start[:4]) - 1}{b.period_start[4:7]}")
        unit = _unit_cost(b)
        prev_unit = _unit_cost(prev) if prev else None
        rows.append(HistoryRow(
            bill=b,
            unit_cost=unit,
            consumption_yoy=_pct(b.consumption, prev.consumption if prev else None),
            unit_cost_yoy=_pct(unit, prev_unit),
        ))
    return rows


def _unit_cost(b: Bill) -> float | None:
    return b.total_eur / b.consumption if b.total_eur is not None and b.consumption else None


def _pct(now: float | None, before: float | None) -> float | None:
    return (now - before) / before * 100 if now is not None and before else None


def chart_data(rows: list[HistoryRow], last: int = 24) -> dict:
    """Serie cronologiche per i grafici dello storico (ultime `last` bollette)."""
    rows = sorted(rows, key=lambda r: r.bill.period_start)[-last:]
    return {
        "labels": [r.bill.period_end[:7] for r in rows],
        "consumption": [r.bill.consumption for r in rows],
        "total": [r.bill.total_eur for r in rows],
        "unit_cost": [r.unit_cost for r in rows],
        "estimated": [r.bill.reading_type == "stimata" for r in rows],
    }
