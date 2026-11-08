"""Login opzionale (AUTH_ENABLED=true). Spento, niente di questo si attiva e l'app funziona come sempre, senza account.

Acceso:
- password con **Argon2id** (le eventuali scrypt/pbkdf2 di versioni precedenti si verificano e si rinnovano al primo accesso);
- **access token JWT** breve (ACCESS_MINUTES, default 15) e **refresh token opaco a rotazione**, entrambi in cookie
  `HttpOnly` + `SameSite=Strict` (+ `Secure` in HTTPS): JavaScript non li legge, quindi un XSS non li può rubare;
- a ogni refresh il token cambia; se uno già usato ricompare (copiato da qualcuno) cade l'intera famiglia, cioè quell'accesso;
- contro il CSRF: SameSite=Strict e un header personalizzato obbligatorio sulle richieste che modificano (`X-Requested-With`);
- le richieste che non vengono dal front-end — il cron di aggiornamento delle offerte — usano CRON_TOKEN (Bearer, solo
  per quell'operazione) oppure il comando `flask --app app import-offers`, che non passa dal web."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash

from . import db
from .config import DEFAULT_ADMIN_PASSWORD
from .errors import ApiError

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
MIN_PASSWORD = 8
MAX_NAME = 80
REUSE_GRACE_SECONDS = 10  # due schede che rinnovano nello stesso istante non sono un furto
ACCESS_COOKIE, REFRESH_COOKIE = "bollette_access", "bollette_refresh"
CSRF_HEADER, CSRF_VALUE = "X-Requested-With", "bollette"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PUBLIC_ENDPOINTS = {"api.auth_session", "api.auth_login", "api.auth_register", "api.auth_refresh", "api.auth_logout", "api.simulate"}
# con la password da cambiare si può solo gestire il proprio account
ACCOUNT_ENDPOINTS = PUBLIC_ENDPOINTS | {"api.auth_me", "api.auth_update_me", "api.auth_password"}
CRON_ENDPOINTS = {"api.import_arera", "legacy_import_arera"}

HASHER = PasswordHasher()  # Argon2id, parametri consigliati da RFC 9106 (profilo a memoria ridotta); i test li abbassano
_DUMMY_HASH = HASHER.hash("password-inesistente")  # per confrontare comunque un hash quando l'utente non esiste


def enabled() -> bool:
    return bool(current_app.config["AUTH_ENABLED"])


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def _parse(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- password ---------------------------------------------------------------

def hash_password(password: str) -> str:
    return HASHER.hash(password)


def verify_password(stored: str, password: str) -> tuple[bool, bool]:
    """(corretta, da rinnovare). Gli hash non Argon2 (scrypt/pbkdf2 di versioni precedenti) si accettano e si rinnovano."""
    if stored.startswith("$argon2"):
        try:
            HASHER.verify(stored, password)
        except (VerificationError, InvalidHashError):
            return False, False
        return True, HASHER.check_needs_rehash(stored)
    ok = check_password_hash(stored, password)
    return ok, ok


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
            (email, name, hash_password(password), int(is_admin), int(must_change_password)),
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


def set_password(id: int, password: str, must_change: bool = False, keep_family: str | None = None) -> None:
    """Cambia la password. Gli access token già emessi smettono di valere subito (token_version) e gli altri accessi
    (famiglie di refresh) vengono chiusi, tranne quello indicato: chi aveva rubato la sessione non resta dentro."""
    d = db.get_db()
    d.execute("UPDATE users SET password_hash = ?, must_change_password = ?, failed_logins = 0, locked_until = NULL, "
              "token_version = token_version + 1 WHERE id = ?", (hash_password(password), int(must_change), id))
    d.commit()
    end_sessions(id, keep_family)


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


def is_admin() -> bool:
    """Con il login spento l'app è a utente unico: tutto è permesso. Acceso, solo gli amministratori."""
    return not enabled() or bool((g.get("user") or {}).get("is_admin"))


def require_admin(what: str = "Questa operazione") -> None:
    if not is_admin():
        raise ApiError(f"{what} è riservata agli amministratori.", 403)


# --- access token (JWT) -----------------------------------------------------

def _secret() -> str:
    """SECRET_KEY, oppure una chiave casuale generata al primo avvio e conservata nel database."""
    app = current_app
    if "jwt_secret" not in app.extensions:
        cfg = app.config["SECRET_KEY"]
        if not cfg:
            d = db.get_db()
            d.execute("INSERT INTO auth_secrets (name, value) VALUES ('jwt', ?) ON CONFLICT (name) DO NOTHING", (secrets.token_hex(32),))
            d.commit()
            cfg = d.execute("SELECT value FROM auth_secrets WHERE name = 'jwt'").fetchone()["value"]
        app.extensions["jwt_secret"] = cfg
    return app.extensions["jwt_secret"]


def make_access_token(user: dict) -> str:
    now = utcnow()
    claims = {"sub": str(user["id"]), "v": user["token_version"], "typ": "access", "iat": now,
              "exp": now + timedelta(minutes=current_app.config["ACCESS_MINUTES"])}
    return jwt.encode(claims, _secret(), algorithm="HS256")


def user_from_access_token(token: str) -> dict | None:
    try:
        claims = jwt.decode(token, _secret(), algorithms=["HS256"], options={"require": ["exp", "sub", "iat"]})
        user = get_user(int(claims["sub"])) if claims.get("typ") == "access" else None
    except (jwt.InvalidTokenError, ValueError):
        return None
    return user if user and user["token_version"] == claims.get("v") else None


# --- refresh token (a rotazione) --------------------------------------------

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_refresh(user_id: int, family: str | None = None) -> str:
    """Un nuovo refresh token (opaco, 256 bit; nel database solo l'impronta). Senza famiglia ne inizia una: è un nuovo accesso."""
    token = secrets.token_urlsafe(32)
    d = db.get_db()
    d.execute("DELETE FROM sessions WHERE expires_at < ?", (_stamp(utcnow()),))  # pulizia: niente job a parte
    d.execute("INSERT INTO sessions (token_hash, user_id, family_id, expires_at) VALUES (?, ?, ?, ?)",
              (_digest(token), user_id, family or uuid.uuid4().hex, _stamp(utcnow() + timedelta(days=current_app.config["SESSION_DAYS"]))))
    d.commit()
    return token


def _family_of(token: str) -> str | None:
    row = db.get_db().execute("SELECT family_id FROM sessions WHERE token_hash = ?", (_digest(token),)).fetchone() if token else None
    return row["family_id"] if row else None


def rotate_refresh(token: str) -> tuple[dict, str]:
    """Scambia un refresh token valido con uno nuovo (e l'utente). Un token già scambiato che ricompare dopo la tolleranza
    è stato copiato: l'intera famiglia viene revocata e serve un nuovo accesso."""
    d = db.get_db()
    row = d.execute("SELECT * FROM sessions WHERE token_hash = ?", (_digest(token),)).fetchone() if token else None
    expired = ApiError("Sessione scaduta: accedi di nuovo.", 401)
    if row is None:
        raise expired
    now = utcnow()
    if row["expires_at"] <= _stamp(now):
        raise expired
    if row["used_at"]:
        if (now - _parse(row["used_at"])).total_seconds() > REUSE_GRACE_SECONDS:
            d.execute("DELETE FROM sessions WHERE family_id = ?", (row["family_id"],))
            d.commit()
            current_app.logger.warning("Riuso di un refresh token (utente %s): accesso revocato.", row["user_id"])
        raise expired
    marked = d.execute("UPDATE sessions SET used_at = ? WHERE id = ? AND used_at IS NULL", (_stamp(now), row["id"]))
    d.commit()
    user = get_user(row["user_id"])
    if not marked.rowcount or user is None:  # un'altra richiesta l'ha appena scambiato
        raise expired
    return user, issue_refresh(user["id"], row["family_id"])


def end_family(token: str) -> None:
    family = _family_of(token)
    if family:
        d = db.get_db()
        d.execute("DELETE FROM sessions WHERE family_id = ?", (family,))
        d.commit()


def end_sessions(user_id: int, keep_family: str | None = None) -> None:
    d = db.get_db()
    d.execute("DELETE FROM sessions WHERE user_id = ? AND (family_id IS NULL OR family_id != ?)", (user_id, keep_family or ""))
    d.commit()


def current_family() -> str | None:
    return _family_of(request.cookies.get(REFRESH_COOKIE, ""))


# --- cookie -----------------------------------------------------------------

def _secure() -> bool:
    mode = current_app.config["COOKIE_SECURE"]
    if mode in ("1", "true", "yes", "on"):
        return True
    if mode in ("0", "false", "no", "off"):
        return False
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https"


def set_access_cookie(resp, user: dict) -> None:
    resp.set_cookie(ACCESS_COOKIE, make_access_token(user), max_age=current_app.config["ACCESS_MINUTES"] * 60, path="/api",
                    httponly=True, samesite="Strict", secure=_secure())


def set_session_cookies(resp, user: dict, refresh: str) -> None:
    """Access (valido su tutta l'API) e refresh (inviato solo a /api/auth, dove serve a rinnovare e a uscire)."""
    set_access_cookie(resp, user)
    resp.set_cookie(REFRESH_COOKIE, refresh, max_age=current_app.config["SESSION_DAYS"] * 86400, path="/api/auth",
                    httponly=True, samesite="Strict", secure=_secure())


def clear_session_cookies(resp) -> None:
    resp.delete_cookie(ACCESS_COOKIE, path="/api")
    resp.delete_cookie(REFRESH_COOKIE, path="/api/auth")


# --- accesso ----------------------------------------------------------------

def login(email: str, password: str) -> tuple[dict, str]:
    """Verifica le credenziali. Dopo 5 errori l'account resta bloccato 15 minuti (il contatore sta nel database: vale per tutti i worker).
    Restituisce l'utente e il primo refresh token di un nuovo accesso."""
    user = get_user_by_email(email or "")
    d = db.get_db()
    now = _stamp(utcnow())
    if user and user["locked_until"] and user["locked_until"] > now:
        left = max(1, int((_parse(user["locked_until"]) - utcnow()).total_seconds() // 60) + 1)
        raise ApiError(f"Troppi tentativi: riprova tra {left} minuti.", 429)
    ok, rehash = verify_password(user["password_hash"] if user else _DUMMY_HASH, password or "")
    if not (user and ok):
        if user:
            failed = user["failed_logins"] + 1
            lock = _stamp(utcnow() + timedelta(minutes=LOCK_MINUTES)) if failed >= MAX_FAILED_LOGINS else None
            d.execute("UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?", (0 if lock else failed, lock, user["id"]))
            d.commit()
        raise ApiError("Email o password errate.", 401)
    d.execute("UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = ?", (user["id"],))
    if rehash:  # hash di una versione precedente o con parametri vecchi: lo si aggiorna ora che la password è in chiaro
        d.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user["id"]))
    d.commit()
    return user, issue_refresh(user["id"])


def bootstrap_admin() -> None:
    """Primo avvio con il login attivo: crea l'amministratore (ADMIN_EMAIL / ADMIN_PASSWORD, altrimenti quelli di default
    con cambio password obbligatorio al primo accesso) e gli assegna i profili esistenti, che prima non avevano proprietario."""
    cfg = current_app.config
    d = db.get_db()
    _secret()  # se serve, genera subito la chiave dei JWT
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


def authenticate() -> None:
    """Imposta `g.user` o risponde 401. Con il login spento non fa nulla (`g.user` resta vuoto: nessun filtro per utente)."""
    if not enabled():
        return
    endpoint = request.endpoint or ""
    token, cron = _bearer(), current_app.config["CRON_TOKEN"]
    if token and cron and endpoint in CRON_ENDPOINTS and hmac.compare_digest(token, cron):
        g.user = get_user(db.get_db().execute("SELECT min(id) AS id FROM users WHERE is_admin = 1").fetchone()["id"])
        return
    # anti-CSRF: un altro sito non può aggiungere questo header alle sue richieste (servirebbe un permesso CORS che non c'è)
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise ApiError("Richiesta non valida.", 403)
    if endpoint in PUBLIC_ENDPOINTS:
        return
    user = user_from_access_token(request.cookies.get(ACCESS_COOKIE, ""))
    if user is None:
        raise ApiError("Accedi per continuare.", 401)  # il front-end prova a rinnovare con il refresh token e riprova
    if user["must_change_password"] and endpoint not in ACCOUNT_ENDPOINTS:
        raise ApiError("Cambia la password per continuare.", 403)
    g.user = user


def guard(view):
    """Per le route fuori dal blueprint /api (l'URL storico del cron): stessi controlli e stesso formato d'errore."""
    try:
        authenticate()
        return view()
    except ApiError as e:
        return jsonify(error=e.text), e.status


def admin_required(view):
    """Con il login attivo solo gli amministratori; con il login spento l'app è a utente unico e passa tutto."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        require_admin()
        return view(*args, **kwargs)
    return wrapper
