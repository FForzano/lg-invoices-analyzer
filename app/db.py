"""Accesso a SQLite e repository minimali (Bill, Offer, impostazioni)."""
from __future__ import annotations

import dataclasses
import json
import sqlite3

from flask import Flask, current_app, g, has_request_context, request

from .migrations import migrate_database
from .services.layouts import Layout
from .services.proposal import Proposal, dump_terms, load_terms
from .models import SYSTEM_FIELDS, Bill, Offer, columns
from .services.seasonality import DEFAULT_INDEX_FACTORS

SETTING_DEFAULTS: dict[str, float | str] = {
    "pun": 0.12, "psv": 0.40, "loss_pct": 10.0, "dispatching_extra": 0.019, "default_power_kw": 3.0,
    # codici ISTAT della località di fornitura (default: Ferrara)
    "region": "08", "province": "038", "comune": "038008",
}
# impostazioni che valgono per il singolo profilo (appartamento); le altre sono globali
PROFILE_SETTINGS = ("region", "province", "comune", "default_power_kw")


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


def _insert(table: str, obj, **extra) -> int:
    values = {**{k: v for k, v in dataclasses.asdict(obj).items() if k not in SYSTEM_FIELDS}, **extra}
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


def _delete(table: str, id: int, **scope) -> None:
    db = get_db()
    where = "".join(f" AND {k} = ?" for k in scope)
    db.execute(f"DELETE FROM {table} WHERE id = ?{where}", (id, *scope.values()))
    db.commit()


# --- profili -----------------------------------------------------------------

def profile_id() -> int:
    """Profilo attivo: quello indicato dal client, se esiste ancora, altrimenti il primo."""
    if "profile_id" not in g:
        # il front-end manda il profilo scelto nell'header `X-Profile-Id` (niente cookie: l'app nativa non li ha affidabili)
        wanted = request.headers.get("X-Profile-Id", type=int) if has_request_context() else None
        row = get_db().execute("SELECT id FROM profiles WHERE id = ?", (wanted,)).fetchone() if wanted else None
        g.profile_id = row["id"] if row else get_db().execute("SELECT min(id) FROM profiles").fetchone()[0]
    return g.profile_id


def list_profiles() -> list[dict]:
    return [dict(r) for r in get_db().execute("SELECT * FROM profiles ORDER BY id")]


def current_profile() -> dict:
    return dict(get_db().execute("SELECT * FROM profiles WHERE id = ?", (profile_id(),)).fetchone())


def add_profile(name: str, region: str, province: str, comune: str, default_power_kw: float) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO profiles (name, region, province, comune, default_power_kw) VALUES (?, ?, ?, ?, ?)",
        (name, region, province, comune, default_power_kw),
    )
    db.commit()
    return cur.lastrowid


def rename_profile(id: int, name: str) -> None:
    db = get_db()
    db.execute("UPDATE profiles SET name = ? WHERE id = ?", (name, id))
    db.commit()


def delete_profile(id: int) -> list[str]:
    """Elimina il profilo con bollette e offerte attuali. Restituisce i PDF da cancellare dal disco."""
    db = get_db()
    pdfs = [r["pdf_path"] for r in db.execute("SELECT pdf_path FROM bills WHERE profile_id = ? AND pdf_path IS NOT NULL", (id,))]
    for table in ("bills", "offers", "proposals"):
        db.execute(f"DELETE FROM {table} WHERE profile_id = ?", (id,))
    db.execute("DELETE FROM profiles WHERE id = ?", (id,))
    db.commit()
    return pdfs


# --- bollette ---------------------------------------------------------------

def list_bills(commodity: str | None = None) -> list[Bill]:
    where, args = "WHERE profile_id = ?", [profile_id()]
    if commodity:
        where, args = where + " AND commodity = ?", [*args, commodity]
    return _fetch(Bill, f"SELECT {', '.join(columns(Bill))} FROM bills {where} ORDER BY period_start DESC", args)


def add_bill(bill: Bill) -> int:
    return _insert("bills", bill, profile_id=profile_id())


def delete_bill(id: int) -> None:
    _delete("bills", id, profile_id=profile_id())


# --- offerte ----------------------------------------------------------------

# Offerte visibili al profilo attivo: catalogo condiviso (profile_id NULL) più le proprie; la versione
# propria di un'offerta (stessa `source`) nasconde quella condivisa.
VISIBLE_OFFERS = (
    "(profile_id IS NULL OR profile_id = :p) AND NOT (profile_id IS NULL AND source IS NOT NULL "
    "AND source IN (SELECT source FROM offers WHERE profile_id = :p AND source IS NOT NULL))"  # senza il filtro, un NULL nella lista rende NULL tutto il NOT IN
)


def list_offers(commodity: str | None = None) -> list[Offer]:
    where = f"WHERE {VISIBLE_OFFERS}" + (" AND commodity = :c" if commodity else "")
    return _fetch(
        Offer, f"SELECT {', '.join(columns(Offer))} FROM offers {where} ORDER BY commodity, supplier, name",
        {"p": profile_id(), "c": commodity},
    )


def get_offer(id: int) -> Offer | None:
    rows = _fetch(
        Offer, f"SELECT {', '.join(columns(Offer))} FROM offers WHERE id = :id AND (profile_id IS NULL OR profile_id = :p)",
        {"id": id, "p": profile_id()},
    )
    return rows[0] if rows else None


def save_offer(offer: Offer, id: int | None = None) -> int:
    """Inserisce o aggiorna. L'offerta attuale è una sola per fornitura e per profilo e appartiene al profilo:
    se un'offerta condivisa diventa «attuale» se ne crea una copia del profilo, il catalogo non cambia."""
    existing = get_offer(id) if id is not None else None
    if id is not None and existing is None:
        raise LookupError(f"Offerta {id} non trovata")
    if existing is None or (offer.is_current and existing.profile_id is None):
        id = _insert("offers", offer, profile_id=profile_id() if offer.is_current else None)
    else:
        _update("offers", id, offer)
    if offer.is_current:
        db = get_db()
        db.execute(
            "UPDATE offers SET is_current = 0 WHERE commodity = ? AND id != ? AND profile_id = ?",
            (offer.commodity, id, profile_id()),
        )
        db.commit()
    return id


def save_detected_offer(offer: Offer) -> int:
    """Salva l'offerta letta da una bolletta come «attuale» del profilo: aggiorna quella già rilevata, se c'è."""
    row = get_db().execute(
        "SELECT id FROM offers WHERE commodity = ? AND source LIKE 'bolletta:%' AND is_current = 1 AND profile_id = ?",
        (offer.commodity, profile_id()),
    ).fetchone()
    return save_offer(offer, row["id"] if row else None)


def replace_imported_offers(offers: list[Offer], prefix: str) -> int:
    """Sostituisce il catalogo condiviso importato (`source` che inizia per `prefix`). Le copie dei profili
    (l'offerta attuale scelta tra quelle importate) restano. Restituisce il numero di offerte inserite."""
    db = get_db()
    db.execute("DELETE FROM offers WHERE source LIKE ? AND profile_id IS NULL", (prefix + "%",))
    db.commit()
    for o in offers:
        _insert("offers", o)
    return len(offers)


def delete_offer(id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM offers WHERE id = ? AND (profile_id IS NULL OR profile_id = ?)", (id, profile_id()))
    db.commit()


# --- proposte ricevute -------------------------------------------------------

def _proposal(row: sqlite3.Row) -> Proposal:
    return Proposal(load_terms(row["terms"]), row["id"], row["contact"], row["received_on"], row["notes"], row["created_at"])


def list_proposals() -> list[Proposal]:
    rows = get_db().execute("SELECT * FROM proposals WHERE profile_id = ? ORDER BY id DESC", (profile_id(),))
    return [_proposal(r) for r in rows]


def get_proposal(id: int) -> Proposal | None:
    row = get_db().execute("SELECT * FROM proposals WHERE id = ? AND profile_id = ?", (id, profile_id())).fetchone()
    return _proposal(row) if row else None


def save_proposal(p: Proposal) -> int:
    db = get_db()
    args = (p.offer.commodity, dump_terms(p.offer), p.contact, p.received_on, p.notes)
    if p.id is None:
        cur = db.execute(
            "INSERT INTO proposals (commodity, terms, contact, received_on, notes, profile_id) VALUES (?, ?, ?, ?, ?, ?)",
            (*args, profile_id()),
        )
        p.id = cur.lastrowid
    else:
        cur = db.execute(
            "UPDATE proposals SET commodity = ?, terms = ?, contact = ?, received_on = ?, notes = ? WHERE id = ? AND profile_id = ?",
            (*args, p.id, profile_id()),
        )
        if not cur.rowcount:
            raise LookupError(f"Proposta {p.id} non trovata")
    db.commit()
    return p.id


def delete_proposal(id: int) -> None:
    _delete("proposals", id, profile_id=profile_id())


# --- layout di lettura insegnati dall'utente (globali: descrivono un fornitore, non un appartamento) ---

def list_layouts() -> list[Layout]:
    rows = get_db().execute("SELECT id, name, signature, rules FROM bill_layouts ORDER BY id")
    return [Layout.from_json(json.dumps({"version": 1, "name": r["name"], "signature": r["signature"], "rules": json.loads(r["rules"])}), id=r["id"]) for r in rows]


def get_layout(id: int) -> Layout | None:
    return next((l for l in list_layouts() if l.id == id), None)


def save_layout(layout: Layout) -> int:
    """Un solo layout per fornitore: insegnarne un altro con la stessa firma lo sostituisce."""
    db = get_db()
    db.execute("DELETE FROM bill_layouts WHERE lower(signature) = lower(?)", (layout.signature,))
    cur = db.execute("INSERT INTO bill_layouts (name, signature, rules) VALUES (?, ?, ?)",
                     (layout.name, layout.signature, json.dumps([r.to_dict() for r in layout.rules], ensure_ascii=False)))
    db.commit()
    return cur.lastrowid


def delete_layout(id: int) -> None:
    _delete("bill_layouts", id)


# --- impostazioni -----------------------------------------------------------

def get_settings() -> dict[str, float | str]:
    """Impostazioni globali più quelle del profilo attivo (località, potenza di default)."""
    stored = {r["key"]: r["value"] for r in get_db().execute("SELECT key, value FROM settings")}
    profile = current_profile()
    return {**SETTING_DEFAULTS, **stored, **{k: profile[k] for k in PROFILE_SETTINGS}}


def save_settings(values: dict[str, float | str]) -> None:
    db = get_db()
    per_profile = {k: v for k, v in values.items() if k in PROFILE_SETTINGS}
    shared = {k: v for k, v in values.items() if k not in PROFILE_SETTINGS}
    db.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        shared.items(),
    )
    for key, value in per_profile.items():  # i nomi vengono da PROFILE_SETTINGS, mai dall'utente
        db.execute(f"UPDATE profiles SET {key} = ? WHERE id = ?", (value, profile_id()))
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
