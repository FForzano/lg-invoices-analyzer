"""Account: accesso, dati personali, password e (solo amministratori) gestione degli utenti.
Con AUTH_ENABLED spento esistono solo `/auth/session` (risponde «login spento») e nessun utente."""
from flask import current_app, g, jsonify, request

from .. import auth, db, ratelimit
from . import ApiError, bp, msg, storage


def _body() -> dict:
    return request.get_json(silent=True) or {}


def _need_auth() -> None:
    if not auth.enabled():
        raise ApiError("Il login non è attivo su questa installazione.", 404)


@bp.get("/auth/session")
def auth_session():
    """Pubblico: dice al front-end se serve il login e, se il cookie di accesso è valido, chi sei."""
    if not auth.enabled():
        return jsonify(auth_enabled=False, user=None)
    user = auth.user_from_access_token(request.cookies.get(auth.ACCESS_COOKIE, ""))
    return jsonify(auth_enabled=True, user=auth.public(user) if user else None,
                   registration_open=bool(current_app.config["ALLOW_REGISTRATION"]),
                   demo=db.has_catalog())  # la simulazione pubblica ha senso solo con un catalogo importato


def _with_session(user: dict, refresh: str, **extra):
    resp = jsonify(user=auth.public(user), **extra)
    auth.set_session_cookies(resp, user, refresh)
    return resp


@bp.post("/auth/login")
def auth_login():
    """I token non vengono mai restituiti nel corpo: arrivano solo come cookie HttpOnly."""
    _need_auth()
    data = _body()
    user, refresh = auth.login(str(data.get("email", "")), str(data.get("password", "")))
    return _with_session(user, refresh)


@bp.post("/auth/register")
def auth_register():
    """Registrazione aperta (solo con ALLOW_REGISTRATION): crea un account normale con il suo primo profilo e lo fa entrare."""
    _need_auth()
    if not current_app.config["ALLOW_REGISTRATION"]:
        raise ApiError("Le registrazioni non sono aperte su questa installazione.", 403)
    ratelimit.check("register", 5, 3600, "registrazioni")
    data = _body()
    email, name, password = auth.check_email(data.get("email", "")), auth.check_name(data.get("name", "")), auth.check_password(data.get("password", ""))
    id = auth.create_user(email, name, password)
    resp = _with_session(auth.get_user(id), auth.issue_refresh(id))
    resp.status_code = 201
    return resp


@bp.post("/auth/refresh")
def auth_refresh():
    """Scambia il refresh token (cookie) con un access token nuovo e un nuovo refresh token (rotazione)."""
    _need_auth()
    try:
        user, refresh = auth.rotate_refresh(request.cookies.get(auth.REFRESH_COOKIE, ""))
    except ApiError as e:
        resp = jsonify(error=e.text)
        resp.status_code = e.status
        auth.clear_session_cookies(resp)
        return resp
    return _with_session(user, refresh)


@bp.post("/auth/logout")
def auth_logout():
    """Chiude questo accesso (la famiglia di refresh token) e cancella i cookie."""
    _need_auth()
    auth.end_family(request.cookies.get(auth.REFRESH_COOKIE, ""))
    resp = jsonify(ok=True)
    auth.clear_session_cookies(resp)
    return resp


@bp.get("/auth/me")
def auth_me():
    _need_auth()
    return jsonify(user=auth.public(g.user))


@bp.put("/auth/me")
def auth_update_me():
    """Dati personali: nome ed email."""
    _need_auth()
    data = _body()
    auth.update_user(g.user["id"], name=auth.check_name(data.get("name", "")), email=auth.check_email(data.get("email", "")))
    return jsonify(user=auth.public(auth.get_user(g.user["id"])), messages=[msg("info", "Dati personali salvati.")])


@bp.post("/auth/password")
def auth_password():
    """Cambio password: serve quella attuale. Gli altri dispositivi vengono scollegati; questo resta dentro con un access token nuovo."""
    _need_auth()
    data = _body()
    if not auth.verify_password(g.user["password_hash"], str(data.get("current_password", "")))[0]:
        raise ApiError("La password attuale non è corretta.", 400)
    new = auth.check_password(data.get("new_password", ""))
    if new == data.get("current_password"):
        raise ApiError("La nuova password deve essere diversa da quella attuale.")
    auth.set_password(g.user["id"], new, keep_family=auth.current_family())
    user = auth.get_user(g.user["id"])
    resp = jsonify(user=auth.public(user), messages=[msg("info", "Password cambiata. Gli altri dispositivi dovranno accedere di nuovo.")])
    auth.set_access_cookie(resp, user)  # il token_version è cambiato: quello vecchio non vale più
    return resp


# --- gestione utenti (amministratori) -----------------------------------------

@bp.get("/users")
@auth.admin_required
def list_users():
    _need_auth()
    return jsonify(users=auth.list_users())


@bp.post("/users")
@auth.admin_required
def create_user():
    """L'amministratore sceglie una password provvisoria: l'utente dovrà cambiarla al primo accesso."""
    _need_auth()
    data = _body()
    id = auth.create_user(auth.check_email(data.get("email", "")), auth.check_name(data.get("name", "")),
                          auth.check_password(data.get("password", "")), bool(data.get("is_admin")), must_change_password=True)
    return jsonify(id=id, messages=[msg("info", "Utente creato: dovrà cambiare la password al primo accesso.")]), 201


def _target(id: int) -> dict:
    user = auth.get_user(id)
    if user is None:
        raise ApiError("Utente non trovato.", 404)
    return user


@bp.put("/users/<int:id>")
@auth.admin_required
def update_user(id: int):
    _need_auth()
    user, data = _target(id), _body()
    is_admin = bool(data.get("is_admin"))
    if user["is_admin"] and not is_admin and auth.admin_count() < 2:
        raise ApiError("Deve restare almeno un amministratore.", 409)
    auth.update_user(id, name=auth.check_name(data.get("name", "")), email=auth.check_email(data.get("email", "")), is_admin=int(is_admin))
    return jsonify(ok=True)


@bp.post("/users/<int:id>/password")
@auth.admin_required
def reset_password(id: int):
    """Reimposta la password di un utente: nuova provvisoria, da cambiare al prossimo accesso; i suoi accessi si chiudono."""
    _need_auth()
    _target(id)
    auth.set_password(id, auth.check_password(_body().get("password", "")), must_change=True)
    return jsonify(messages=[msg("info", "Password reimpostata: l'utente dovrà cambiarla al prossimo accesso.")])


@bp.delete("/users/<int:id>")
@auth.admin_required
def delete_user(id: int):
    _need_auth()
    user = _target(id)
    if id == g.user["id"]:
        raise ApiError("Non puoi eliminare il tuo stesso account.", 409)
    if user["is_admin"] and auth.admin_count() < 2:
        raise ApiError("Deve restare almeno un amministratore.", 409)
    for name in auth.delete_user(id):
        storage().delete(name)
    return jsonify(messages=[msg("info", "Utente eliminato con i suoi profili e le sue bollette.")])
