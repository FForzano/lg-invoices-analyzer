"""Accesso al database (SQLite o PostgreSQL, vedi database.py) e repository minimali (Bill, Offer, impostazioni)."""
from __future__ import annotations

import dataclasses
import json

from flask import Flask, current_app, g, has_request_context, request

from .database import Database
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


def get_db() -> Database:
    if "db" not in g:
        g.db = Database(current_app.config["DATABASE_URL"])
    return g.db


def init_app(app: Flask) -> None:
    migrate_database(app.config["DATABASE_URL"])
    app.teardown_appcontext(_close_db)


def _close_db(_exc) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --- generico -------------------------------------------------------------

def _fetch(cls, sql: str, args=()):
    return [cls(**dict(r)) for r in get_db().execute(sql, args)]


def _plain(values: dict) -> dict:
    """I booleani diventano 0/1: le colonne sono INTEGER in entrambi i motori (PostgreSQL non li converte da solo)."""
    return {k: int(v) if isinstance(v, bool) else v for k, v in values.items()}


def _insert(table: str, obj, **extra) -> int:
    values = _plain({**{k: v for k, v in dataclasses.asdict(obj).items() if k not in SYSTEM_FIELDS}, **extra})
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    db = get_db()
    id = db.insert(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(values.values()))
    db.commit()
    return id


def _update(table: str, id: int, obj) -> None:
    values = _plain({k: v for k, v in dataclasses.asdict(obj).items() if k not in SYSTEM_FIELDS})
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

def current_user() -> dict | None:
    """L'utente autenticato (None con il login spento: allora tutti i profili sono visibili, come sempre)."""
    return g.get("user") if has_request_context() else None


def profile_id() -> int:
    """Profilo attivo: quello indicato dal client, se esiste ancora (ed è dell'utente), altrimenti il primo."""
    if "profile_id" not in g:
        ids = [p["id"] for p in list_profiles()]
        if not ids:  # utente senza profili (es. creato a mano nel database): ne nasce uno vuoto
            here = SETTING_DEFAULTS
            ids = [add_profile("Casa", here["region"], here["province"], here["comune"], here["default_power_kw"])]
        # il front-end manda il profilo scelto nell'header `X-Profile-Id` (niente cookie: l'app nativa non li ha affidabili)
        wanted = request.headers.get("X-Profile-Id", type=int) if has_request_context() else None
        g.profile_id = wanted if wanted in ids else ids[0]
    return g.profile_id


def list_profiles() -> list[dict]:
    user = current_user()
    where, args = ("WHERE user_id = ?", (user["id"],)) if user else ("", ())
    return [dict(r) for r in get_db().execute(f"SELECT * FROM profiles {where} ORDER BY id", args)]


def current_profile() -> dict:
    return dict(get_db().execute("SELECT * FROM profiles WHERE id = ?", (profile_id(),)).fetchone())


def add_profile(name: str, region: str, province: str, comune: str, default_power_kw: float, user_id: int | None = None) -> int:
    """Nuovo profilo; con il login attivo appartiene a chi lo crea (o all'utente indicato)."""
    if user_id is None and (user := current_user()):
        user_id = user["id"]
    db = get_db()
    id = db.insert(
        "INSERT INTO profiles (name, region, province, comune, default_power_kw, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (name, region, province, comune, default_power_kw, user_id),
    )
    db.commit()
    return id


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

def _proposal(row) -> Proposal:
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
        p.id = db.insert(
            "INSERT INTO proposals (commodity, terms, contact, received_on, notes, profile_id) VALUES (?, ?, ?, ?, ?, ?)",
            (*args, profile_id()),
        )
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
    id = db.insert("INSERT INTO bill_layouts (name, signature, rules) VALUES (?, ?, ?)",
                   (layout.name, layout.signature, json.dumps([r.to_dict() for r in layout.rules], ensure_ascii=False)))
    db.commit()
    return id


def delete_layout(id: int) -> None:
    _delete("bill_layouts", id)


# --- impostazioni -----------------------------------------------------------

def _setting(key: str, value):
    """Le impostazioni numeriche tornano numeri (in PostgreSQL il valore è testo); i codici ISTAT restano testo."""
    if isinstance(SETTING_DEFAULTS.get(key, 0.0), float) or key.endswith("_recent"):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    return str(value)


def get_settings() -> dict[str, float | str]:
    """Impostazioni globali più quelle del profilo attivo (località, potenza di default)."""
    stored = {r["key"]: _setting(r["key"], r["value"]) for r in get_db().execute("SELECT key, value FROM settings")}
    profile = current_profile()
    return {**SETTING_DEFAULTS, **stored, **{k: profile[k] for k in PROFILE_SETTINGS}}


def save_settings(values: dict[str, float | str]) -> None:
    db = get_db()
    per_profile = {k: v for k, v in values.items() if k in PROFILE_SETTINGS}
    shared = {k: v for k, v in values.items() if k not in PROFILE_SETTINGS}
    db.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        [(k, str(v)) for k, v in shared.items()],  # colonna di testo: i numeri si rileggono con _setting
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
