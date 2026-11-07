"""Accesso a SQLite e repository minimali (Bill, Offer, impostazioni)."""
from __future__ import annotations

import dataclasses
import sqlite3

from flask import Flask, current_app, g

from .migrations import migrate_database
from .models import SYSTEM_FIELDS, Bill, Offer, columns
from .services.seasonality import DEFAULT_INDEX_FACTORS

SETTING_DEFAULTS: dict[str, float | str] = {
    "pun": 0.12, "psv": 0.40, "loss_pct": 10.0, "dispatching_extra": 0.019, "default_power_kw": 3.0,
    # codici ISTAT della località di fornitura (default: Ferrara)
    "region": "08", "province": "038", "comune": "038008",
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_app(app: Flask) -> None:
    migrate_database(app.config["DB_PATH"])
    app.teardown_appcontext(_close_db)


def _close_db(_exc) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --- generico -------------------------------------------------------------

def _fetch(cls, sql: str, args=()):
    return [cls(**dict(r)) for r in get_db().execute(sql, args)]


def _insert(table: str, obj) -> int:
    values = {k: v for k, v in dataclasses.asdict(obj).items() if k not in SYSTEM_FIELDS}
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    db = get_db()
    cur = db.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(values.values()))
    db.commit()
    return cur.lastrowid


def _update(table: str, id: int, obj) -> None:
    values = {k: v for k, v in dataclasses.asdict(obj).items() if k not in SYSTEM_FIELDS}
    sets = ", ".join(f"{k} = ?" for k in values)
    db = get_db()
    db.execute(f"UPDATE {table} SET {sets} WHERE id = ?", (*values.values(), id))
    db.commit()


def _delete(table: str, id: int) -> None:
    db = get_db()
    db.execute(f"DELETE FROM {table} WHERE id = ?", (id,))
    db.commit()


# --- bollette ---------------------------------------------------------------

def list_bills(commodity: str | None = None) -> list[Bill]:
    where, args = ("WHERE commodity = ?", (commodity,)) if commodity else ("", ())
    return _fetch(Bill, f"SELECT {', '.join(columns(Bill))} FROM bills {where} ORDER BY period_start DESC", args)


def add_bill(bill: Bill) -> int:
    return _insert("bills", bill)


def delete_bill(id: int) -> None:
    _delete("bills", id)


# --- offerte ----------------------------------------------------------------

def list_offers(commodity: str | None = None) -> list[Offer]:
    where, args = ("WHERE commodity = ?", (commodity,)) if commodity else ("", ())
    return _fetch(
        Offer, f"SELECT {', '.join(columns(Offer))} FROM offers {where} ORDER BY commodity, supplier, name", args
    )


def get_offer(id: int) -> Offer | None:
    rows = _fetch(Offer, f"SELECT {', '.join(columns(Offer))} FROM offers WHERE id = ?", (id,))
    return rows[0] if rows else None


def save_offer(offer: Offer, id: int | None = None) -> int:
    """Inserisce o aggiorna; l'offerta attuale è una sola per fornitura."""
    if id is None:
        id = _insert("offers", offer)
    else:
        _update("offers", id, offer)
    if offer.is_current:
        db = get_db()
        db.execute("UPDATE offers SET is_current = 0 WHERE commodity = ? AND id != ?", (offer.commodity, id))
        db.commit()
    return id


def save_detected_offer(offer: Offer) -> int:
    """Salva l'offerta letta da una bolletta come «attuale»: aggiorna quella già rilevata, se c'è."""
    row = get_db().execute(
        "SELECT id FROM offers WHERE commodity = ? AND source LIKE 'bolletta:%' AND is_current = 1", (offer.commodity,)
    ).fetchone()
    return save_offer(offer, row["id"] if row else None)


def replace_imported_offers(offers: list[Offer], prefix: str) -> int:
    """Sostituisce le offerte importate (`source` che inizia per `prefix`), tenendo quella
    marcata come attuale se ancora presente nel file. Restituisce il numero di offerte inserite."""
    db = get_db()
    kept = {r["source"] for r in db.execute("SELECT source FROM offers WHERE is_current = 1 AND source LIKE ?", (prefix + "%",))}
    db.execute("DELETE FROM offers WHERE source LIKE ? AND is_current = 0", (prefix + "%",))
    db.commit()
    new = [o for o in offers if o.source not in kept]
    for o in new:
        _insert("offers", o)
    return len(new)


def delete_offer(id: int) -> None:
    _delete("offers", id)


# --- impostazioni -----------------------------------------------------------

def get_settings() -> dict[str, float | str]:
    stored = {r["key"]: r["value"] for r in get_db().execute("SELECT key, value FROM settings")}
    return {**SETTING_DEFAULTS, **stored}


def save_settings(values: dict[str, float | str]) -> None:
    db = get_db()
    db.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        values.items(),
    )
    db.commit()


# --- stagionalità degli indici -----------------------------------------------

def get_index_factors() -> dict[str, tuple[float, ...]]:
    """Fattori mensili di PUN/PSV: quelli salvati dal Portale Offerte, altrimenti i predefiniti."""
    out = dict(DEFAULT_INDEX_FACTORS)
    for name in out:
        rows = get_db().execute(
            "SELECT factor FROM index_factors WHERE index_name = ? ORDER BY month", (name,)
        ).fetchall()
        if len(rows) == 12:
            out[name] = tuple(r["factor"] for r in rows)
    return out


def save_index_factors(factors: dict[str, tuple[float, ...]]) -> None:
    db = get_db()
    db.executemany(
        "INSERT INTO index_factors (index_name, month, factor) VALUES (?, ?, ?) "
        "ON CONFLICT(index_name, month) DO UPDATE SET factor = excluded.factor",
        [(name, month, f) for name, values in factors.items() for month, f in enumerate(values, 1)],
    )
    db.commit()
