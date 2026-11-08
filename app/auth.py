"""Login opzionale (AUTH_ENABLED=true). Spento, niente di questo si attiva e l'app funziona come sempre, senza account.

Acceso: email + password → un token opaco (`Authorization: Bearer ...`), valido SESSION_DAYS giorni e revocabile.
Niente cookie, così funziona identico nel browser e in un'app nativa. Nel database resta solo l'impronta SHA-256 del token
e l'hash (scrypt) della password. Le richieste che non vengono dal front-end — il cron di aggiornamento delle offerte —
possono usare CRON_TOKEN, valido solo per quell'operazione."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .config import DEFAULT_ADMIN_PASSWORD
from .errors import ApiError

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
MIN_PASSWORD = 8
MAX_NAME = 80
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PUBLIC_ENDPOINTS = {"api.auth_session", "api.auth_login"}
# con la password da cambiare si può solo gestire il proprio account
ACCOUNT_ENDPOINTS = PUBLIC_ENDPOINTS | {"api.auth_me", "api.auth_update_me", "api.auth_password", "api.auth_logout"}
CRON_ENDPOINTS = {"api.import_arera", "legacy_import_arera"}
HASH_METHOD = "scrypt"  # i test lo abbassano: scrypt è lento di proposito
_DUMMY_HASH = generate_password_hash("password-inesistente")  # per confrontare comunque un hash quando l'utente non esiste


def enabled() -> bool:
    return bool(current_app.config["AUTH_ENABLED"])


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- utenti -----------------------------------------------------------------

USER_FIELDS = "id, email, name, is_admin, must_change_password, created_at"


def public(user: dict) -> dict:
    """L'utente come lo vede il client: mai hash o contatori interni."""
    return {**{k: user[k] for k in ("id", "email", "name", "created_at")}, "is_admin": bool(user["is_admin"]),
            "must_change_password": bool(user["must_change_password"])}


def get_user(id: int) -> dict | None:
    row = db.get_db().execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    row = db.get_db().execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict]:
    rows = db.get_db().execute(
        f"SELECT {USER_FIELDS}, (SELECT count(*) FROM profiles WHERE user_id = users.id) AS profiles FROM users ORDER BY id")
    return [{**public(dict(r)), "profiles": r["profiles"]} for r in rows]


def check_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not EMAIL.fullmatch(email) or len(email) > 200:
        raise ApiError("Indirizzo email non valido.")
    return email


def check_name(name: str) -> str:
    name = (name or "").strip()
    if not name or len(name) > MAX_NAME:
        raise ApiError(f"Il nome è obbligatorio (massimo {MAX_NAME} caratteri).")
    return name


def check_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise ApiError(f"La password deve avere almeno {MIN_PASSWORD} caratteri.")
    if len(password) > 200:
        raise ApiError("La password è troppo lunga.")
    return password


def _integrity_error(e: Exception) -> bool:
    import sqlite3

    try:
        import psycopg

        return isinstance(e, (sqlite3.IntegrityError, psycopg.errors.IntegrityError))
    except ImportError:
        return isinstance(e, sqlite3.IntegrityError)


def create_user(email: str, name: str, password: str, is_admin: bool = False, must_change_password: bool = False,
                with_profile: bool = True) -> int:
    """Crea l'account con un primo profilo «Casa» (poi ne può avere quanti vuole)."""
    d = db.get_db()
    try:
        id = d.insert(
            "INSERT INTO users (email, name, password_hash, is_admin, must_change_password) VALUES (?, ?, ?, ?, ?)",
            (email, name, generate_password_hash(password, HASH_METHOD), int(is_admin), int(must_change_password)),
        )
        d.commit()
    except Exception as e:  # noqa: BLE001
        d.rollback()
        if _integrity_error(e):
            raise ApiError("Esiste già un account con questa email.", 409) from None
        raise
    if with_profile:
        here = db.SETTING_DEFAULTS
        db.add_profile("Casa", here["region"], here["province"], here["comune"], here["default_power_kw"], user_id=id)
    return id


def update_user(id: int, **fields) -> None:
    """Aggiorna nome, email, ruolo (solo le chiavi presenti: i nomi colonna vengono dal codice, mai dal client)."""
    d = db.get_db()
    sets = ", ".join(f"{k} = ?" for k in fields)
    try:
        d.execute(f"UPDATE users SET {sets} WHERE id = ?", (*fields.values(), id))
        d.commit()
    except Exception as e:  # noqa: BLE001
        d.rollback()
        if _integrity_error(e):
            raise ApiError("Esiste già un account con questa email.", 409) from None
        raise


def set_password(id: int, password: str, must_change: bool = False, keep_token: str | None = None) -> None:
    """Cambia la password ed esce da tutte le sessioni (tranne quella indicata): chi l'aveva rubata non entra più."""
    d = db.get_db()
    d.execute("UPDATE users SET password_hash = ?, must_change_password = ?, failed_logins = 0, locked_until = NULL WHERE id = ?",
              (generate_password_hash(password, HASH_METHOD), int(must_change), id))
    d.commit()
    end_sessions(id, keep_token)


def delete_user(id: int) -> list[str]:
    """Elimina l'account con sessioni, profili e bollette. Restituisce i PDF da cancellare dallo storage."""
    pdfs: list[str] = []
    d = db.get_db()
    for row in d.execute("SELECT id FROM profiles WHERE user_id = ?", (id,)).fetchall():
        pdfs += db.delete_profile(row["id"])
    d.execute("DELETE FROM sessions WHERE user_id = ?", (id,))
    d.execute("DELETE FROM users WHERE id = ?", (id,))
    d.commit()
    return pdfs


def admin_count() -> int:
    return db.get_db().execute("SELECT count(*) AS n FROM users WHERE is_admin = 1").fetchone()["n"]


# --- sessioni ---------------------------------------------------------------

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    d = db.get_db()
    d.execute("DELETE FROM sessions WHERE expires_at < ?", (_stamp(utcnow()),))  # pulizia: niente job a parte
    d.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
              (_digest(token), user_id, _stamp(utcnow() + timedelta(days=current_app.config["SESSION_DAYS"]))))
    d.commit()
    return token


def user_from_token(token: str) -> dict | None:
    row = db.get_db().execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?",
        (_digest(token), _stamp(utcnow()))).fetchone()
    return dict(row) if row else None


def end_session(token: str) -> None:
    d = db.get_db()
    d.execute("DELETE FROM sessions WHERE token_hash = ?", (_digest(token),))
    d.commit()


def end_sessions(user_id: int, keep_token: str | None = None) -> None:
    d = db.get_db()
    d.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?", (user_id, _digest(keep_token or "")))
    d.commit()


def login(email: str, password: str) -> tuple[dict, str]:
    """Verifica le credenziali. Dopo 5 errori l'account resta bloccato 15 minuti (il contatore sta nel database: vale per tutti i worker)."""
    user = get_user_by_email(email or "")
    d = db.get_db()
    now = _stamp(utcnow())
    if user and user["locked_until"] and user["locked_until"] > now:
        left = max(1, int((datetime.strptime(user["locked_until"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) - utcnow()).total_seconds() // 60) + 1)
        raise ApiError(f"Troppi tentativi: riprova tra {left} minuti.", 429)
    ok = check_password_hash(user["password_hash"] if user else _DUMMY_HASH, password or "")
    if not (user and ok):
        if user:
            failed = user["failed_logins"] + 1
            lock = _stamp(utcnow() + timedelta(minutes=LOCK_MINUTES)) if failed >= MAX_FAILED_LOGINS else None
            d.execute("UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?", (0 if lock else failed, lock, user["id"]))
            d.commit()
        raise ApiError("Email o password errate.", 401)
    d.execute("UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = ?", (user["id"],))
    d.commit()
    return user, start_session(user["id"])


def bootstrap_admin() -> None:
    """Primo avvio con il login attivo: crea l'amministratore (ADMIN_EMAIL / ADMIN_PASSWORD, altrimenti quelli di default
    con cambio password obbligatorio al primo accesso) e gli assegna i profili esistenti, che prima non avevano proprietario."""
    cfg = current_app.config
    d = db.get_db()
    if d.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 0:
        password = cfg["ADMIN_PASSWORD"] or DEFAULT_ADMIN_PASSWORD
        default = not cfg["ADMIN_PASSWORD"]
        try:
            create_user(cfg["ADMIN_EMAIL"], "Amministratore", password, is_admin=True, must_change_password=default, with_profile=False)
            if default:
                current_app.logger.warning("Creato l'amministratore %s con la password di default «%s»: va cambiata al primo accesso "
                                           "(o imposta ADMIN_PASSWORD).", cfg["ADMIN_EMAIL"], DEFAULT_ADMIN_PASSWORD)
        except ApiError:  # un altro worker, partito insieme a questo, l'ha già creato
            pass
    admin = d.execute("SELECT min(id) AS id FROM users WHERE is_admin = 1").fetchone()["id"]
    d.execute("UPDATE profiles SET user_id = ? WHERE user_id IS NULL", (admin,))
    d.commit()
    if not d.execute("SELECT 1 FROM profiles WHERE user_id = ?", (admin,)).fetchone():
        here = db.SETTING_DEFAULTS
        db.add_profile("Casa", here["region"], here["province"], here["comune"], here["default_power_kw"], user_id=admin)


# --- richieste --------------------------------------------------------------

def _bearer() -> str:
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header[:7].lower() == "bearer " else ""


def current_token() -> str:
    return _bearer()


def authenticate() -> None:
    """Imposta `g.user` o risponde 401. Con il login spento non fa nulla (`g.user` resta vuoto: nessun filtro per utente)."""
    if not enabled():
        return
    endpoint = request.endpoint or ""
    if endpoint in PUBLIC_ENDPOINTS:
        return
    token = _bearer()
    cron = current_app.config["CRON_TOKEN"]
    if token and cron and endpoint in CRON_ENDPOINTS and hmac.compare_digest(token, cron):
        g.user = get_user(db.get_db().execute("SELECT min(id) AS id FROM users WHERE is_admin = 1").fetchone()["id"])
        return
    user = user_from_token(token) if token else None
    if user is None:
        raise ApiError("Accedi per continuare.", 401)
    if user["must_change_password"] and endpoint not in ACCOUNT_ENDPOINTS:
        raise ApiError("Cambia la password per continuare.", 403)
    g.user = user


def guard(view):
    """Per le route fuori dal blueprint /api (l'URL storico del cron): stessi controlli e stesso formato d'errore."""
    from flask import jsonify

    try:
        authenticate()
        return view()
    except ApiError as e:
        return jsonify(error=e.text), e.status


def admin_required(view):
    """Con il login attivo solo gli amministratori; con il login spento l'app è a utente unico e passa tutto."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if enabled() and not (g.get("user") or {}).get("is_admin"):
            raise ApiError("Serve un account amministratore.", 403)
        return view(*args, **kwargs)
    return wrapper
