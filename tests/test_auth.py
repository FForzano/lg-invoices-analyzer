from collections import Counter

import jwt
import pytest
from argon2 import PasswordHasher
from werkzeug.security import generate_password_hash

from app import auth, create_app
from app.services import arera, extraction

PW = "una-password-lunga"
ANNA_PW = "la-mia-password"
CSRF = {"X-Requested-With": "bollette"}


@pytest.fixture(autouse=True)
def fast_hashes(monkeypatch):
    monkeypatch.setattr(auth, "HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


class Api:
    """Un «browser»: un client di test con il suo vaso dei cookie, che aggiunge l'header anti-CSRF come fa il front-end."""

    def __init__(self, app):
        self.c = app.test_client()

    def _do(self, method, url, **kw):
        kw["headers"] = {**CSRF, **kw.get("headers", {})}
        return getattr(self.c, method)(url, **kw)

    get = lambda self, url, **kw: self._do("get", url, **kw)  # noqa: E731
    post = lambda self, url, **kw: self._do("post", url, **kw)  # noqa: E731
    put = lambda self, url, **kw: self._do("put", url, **kw)  # noqa: E731
    delete = lambda self, url, **kw: self._do("delete", url, **kw)  # noqa: E731

    def login(self, email="admin@bollette.local", password=PW):
        return self.post("/api/auth/login", json={"email": email, "password": password})

    def cookie(self, name, path="/api"):
        c = self.c.get_cookie(name, path=path)
        return c.value if c else None


def make(tmp_path, **cfg):
    app = create_app(str(tmp_path), AUTH_ENABLED=True, ADMIN_PASSWORD=PW, **cfg)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def app(tmp_path):
    return make(tmp_path)


@pytest.fixture
def admin(app):
    a = Api(app)
    assert a.login().status_code == 200
    return a


def new_user(admin, email="anna@example.com", password="password-provvisoria", **extra):
    r = admin.post("/api/users", json={"name": "Anna", "email": email, "password": password, **extra})
    assert r.status_code == 201, r.json
    return r.json["id"]


def anna(app, admin):
    """Un secondo «browser» con un utente normale che ha già scelto la sua password."""
    new_user(admin)
    a = Api(app)
    assert a.login("anna@example.com", "password-provvisoria").status_code == 200
    assert a.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": ANNA_PW}).status_code == 200
    return a


# --- login spento: come sempre -----------------------------------------------

def test_login_off_by_default_everything_open(client):
    assert client.get("/api/auth/session").json == {"auth_enabled": False, "user": None}
    assert client.get("/api/bootstrap").status_code == 200
    assert client.post("/api/profiles", json={"name": "Altro"}).status_code == 201  # nessun header speciale
    assert client.post("/api/auth/login", json={}).status_code == 404
    assert client.get("/api/users").status_code == 404


# --- cookie, JWT, refresh ---------------------------------------------------

def test_requests_need_a_session(app):
    a = Api(app)
    assert a.get("/api/auth/session").json == {"auth_enabled": True, "user": None}
    assert a.get("/api/bootstrap").status_code == 401
    assert a.get("/health").status_code == 200  # healthcheck e pagine statiche restano pubblici


def test_login_sets_httponly_strict_cookies_and_never_returns_tokens(app):
    a = Api(app)
    r = a.login()
    assert r.status_code == 200 and set(r.json) == {"user"}
    flags = {c.split("=")[0]: c for c in r.headers.getlist("Set-Cookie")}
    for name, path in ((auth.ACCESS_COOKIE, "/api"), (auth.REFRESH_COOKIE, "/api/auth")):
        assert "HttpOnly" in flags[name] and "SameSite=Strict" in flags[name] and f"Path={path}" in flags[name]
    assert "Secure" not in flags[auth.ACCESS_COOKIE]  # richiesta in HTTP
    https = Api(app).c.post("/api/auth/login", json={"email": "admin@bollette.local", "password": PW}, headers={**CSRF, "X-Forwarded-Proto": "https"})
    assert all("Secure" in c for c in https.headers.getlist("Set-Cookie"))


def test_access_token_is_a_short_lived_signed_jwt(app, admin):
    claims = jwt.decode(admin.cookie(auth.ACCESS_COOKIE), options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 15 * 60 and claims["typ"] == "access"


def test_changing_state_requires_the_csrf_header(app, admin):
    assert admin.c.post("/api/profiles", json={"name": "X"}).status_code == 403  # senza X-Requested-With
    assert admin.c.get("/api/profiles").status_code == 200  # le letture no
    assert admin.post("/api/profiles", json={"name": "X"}).status_code == 201


def test_forged_and_foreign_tokens_are_rejected(app, admin):
    other_key = jwt.encode({"sub": "1", "v": 0, "typ": "access", "iat": 1, "exp": 4102444800}, "altra-chiave-segreta-di-32-byte!!", algorithm="HS256")
    unsigned = jwt.encode({"sub": "1", "v": 0, "typ": "access", "iat": 1, "exp": 4102444800}, None, algorithm="none")
    for bad in (other_key, unsigned, "spazzatura"):
        a = Api(app)
        a.c.set_cookie(auth.ACCESS_COOKIE, bad, path="/api")
        assert a.get("/api/bootstrap").status_code == 401


def test_expired_access_token_is_renewed_with_refresh(app):
    app.config["ACCESS_MINUTES"] = -1  # access già scaduto al rilascio
    a = Api(app)
    a.login()
    assert a.get("/api/bootstrap").status_code == 401
    app.config["ACCESS_MINUTES"] = 15
    r = a.post("/api/auth/refresh")
    assert r.status_code == 200 and r.json["user"]["email"] == "admin@bollette.local"
    assert a.get("/api/bootstrap").status_code == 200


def test_refresh_token_rotates_on_every_use(app, admin):
    first = admin.cookie(auth.REFRESH_COOKIE, "/api/auth")
    assert admin.post("/api/auth/refresh").status_code == 200
    second = admin.cookie(auth.REFRESH_COOKIE, "/api/auth")
    assert second and second != first
    assert admin.post("/api/auth/refresh").status_code == 200
    assert admin.cookie(auth.REFRESH_COOKIE, "/api/auth") not in (first, second)


def test_reusing_a_rotated_refresh_token_revokes_the_whole_session(app, admin, monkeypatch):
    monkeypatch.setattr(auth, "REUSE_GRACE_SECONDS", -1)  # niente tolleranza: il riuso è subito un furto
    stolen = admin.cookie(auth.REFRESH_COOKIE, "/api/auth")
    assert admin.post("/api/auth/refresh").status_code == 200  # l'utente vero rinnova
    thief = Api(app)
    thief.c.set_cookie(auth.REFRESH_COOKIE, stolen, path="/api/auth")
    assert thief.post("/api/auth/refresh").status_code == 401  # il ladro riusa il vecchio...
    assert admin.post("/api/auth/refresh").status_code == 401  # ...e cade anche la sessione dell'utente vero


def test_concurrent_refresh_within_grace_is_not_treated_as_theft(app, admin):
    old = admin.cookie(auth.REFRESH_COOKIE, "/api/auth")
    assert admin.post("/api/auth/refresh").status_code == 200
    twin = Api(app)  # una seconda scheda con ancora il cookie vecchio, a pochi istanti
    twin.c.set_cookie(auth.REFRESH_COOKIE, old, path="/api/auth")
    assert twin.post("/api/auth/refresh").status_code == 401
    assert admin.post("/api/auth/refresh").status_code == 200  # la famiglia è intatta


def test_refresh_without_or_with_bad_cookie_fails_and_clears(app):
    a = Api(app)
    assert a.post("/api/auth/refresh").status_code == 401
    a.c.set_cookie(auth.REFRESH_COOKIE, "inventato", path="/api/auth")
    r = a.post("/api/auth/refresh")
    assert r.status_code == 401 and any("Max-Age=0" in c or "Expires=Thu, 01 Jan 1970" in c for c in r.headers.getlist("Set-Cookie"))


def test_expired_refresh_token_is_rejected(app, admin):
    from app import db

    with app.app_context():
        d = db.get_db()
        d.execute("UPDATE sessions SET expires_at = '2000-01-01 00:00:00'")
        d.commit()
    assert admin.post("/api/auth/refresh").status_code == 401


def test_logout_ends_this_session_only(app, admin):
    other = Api(app)
    other.login()
    assert admin.post("/api/auth/logout").status_code == 200
    assert admin.cookie(auth.ACCESS_COOKIE) is None and admin.cookie(auth.REFRESH_COOKIE, "/api/auth") is None
    assert admin.get("/api/bootstrap").status_code == 401
    assert other.get("/api/bootstrap").status_code == 200


def test_logout_revokes_the_refresh_token_even_if_it_was_copied(app, admin):
    copied = admin.cookie(auth.REFRESH_COOKIE, "/api/auth")
    admin.post("/api/auth/logout")
    thief = Api(app)
    thief.c.set_cookie(auth.REFRESH_COOKIE, copied, path="/api/auth")
    assert thief.post("/api/auth/refresh").status_code == 401


# --- password: Argon2id ------------------------------------------------------

def test_passwords_are_hashed_with_argon2id(app):
    from app import db

    with app.app_context():
        h = db.get_db().execute("SELECT password_hash FROM users").fetchone()["password_hash"]
    assert h.startswith("$argon2id$") and PW not in h


def test_default_parameters_are_the_argon2id_recommended_ones():
    from argon2 import Type
    from argon2.profiles import RFC_9106_LOW_MEMORY

    assert auth.HASHER.__class__ is PasswordHasher  # (nei test sostituito da una versione veloce, vedi fixture)
    default = PasswordHasher()
    assert default._parameters.type is Type.ID and default._parameters.memory_cost >= RFC_9106_LOW_MEMORY.memory_cost // 2


def test_legacy_scrypt_hash_still_works_and_is_upgraded_at_login(app):
    from app import db

    with app.app_context():
        d = db.get_db()
        d.execute("UPDATE users SET password_hash = ?", (generate_password_hash(PW, "scrypt"),))
        d.commit()
    a = Api(app)
    assert a.login(password="sbagliata").status_code == 401
    assert a.login().status_code == 200
    with app.app_context():
        assert db.get_db().execute("SELECT password_hash FROM users").fetchone()["password_hash"].startswith("$argon2id$")
    assert Api(app).login().status_code == 200


# --- account -----------------------------------------------------------------

def test_default_admin_must_change_password(tmp_path):
    app = create_app(str(tmp_path), AUTH_ENABLED=True)  # nessuna ADMIN_PASSWORD: email e password di default
    a = Api(app)
    r = a.login(password="admin")
    assert r.json["user"]["must_change_password"] and r.json["user"]["is_admin"]
    assert a.get("/api/bootstrap").status_code == 403  # prima si cambia la password
    assert a.get("/api/auth/me").status_code == 200
    assert a.post("/api/auth/password", json={"current_password": "admin", "new_password": "corta"}).status_code == 400
    ok = a.post("/api/auth/password", json={"current_password": "admin", "new_password": PW})
    assert ok.status_code == 200 and not ok.json["user"]["must_change_password"]
    assert a.get("/api/bootstrap").status_code == 200
    assert Api(app).login(password="admin").status_code == 401


def test_configured_admin_password_is_not_temporary(app):
    assert not Api(app).login().json["user"]["must_change_password"]


def test_wrong_password_and_lockout(app):
    a = Api(app)
    for _ in range(5):
        assert a.login(password="sbagliata").status_code == 401
    assert a.login().status_code == 429  # anche quella giusta, finché è bloccato
    assert a.login(email="nessuno@example.com").status_code == 401  # stessa risposta se l'account non esiste


def test_update_personal_info(admin):
    r = admin.put("/api/auth/me", json={"name": "Federico", "email": "Fede@Example.com"})
    assert r.json["user"]["name"] == "Federico" and r.json["user"]["email"] == "fede@example.com"
    assert admin.put("/api/auth/me", json={"name": "", "email": "a@b.it"}).status_code == 400
    assert admin.put("/api/auth/me", json={"name": "X", "email": "non-una-email"}).status_code == 400
    assert admin.login(email="fede@example.com").status_code == 200


def test_email_must_be_unique(admin):
    new_user(admin)
    assert admin.put("/api/auth/me", json={"name": "A", "email": "anna@example.com"}).status_code == 409
    assert admin.post("/api/users", json={"name": "B", "email": "ANNA@example.com", "password": "password-lunga"}).status_code == 409


def test_password_change_needs_current_and_signs_out_every_other_device(app, admin):
    other = Api(app)
    other.login()
    assert admin.post("/api/auth/password", json={"current_password": "no", "new_password": "nuova-password"}).status_code == 400
    assert admin.post("/api/auth/password", json={"current_password": PW, "new_password": "nuova-password"}).status_code == 200
    assert admin.get("/api/auth/me").status_code == 200  # questo dispositivo resta dentro (access token rinnovato)
    assert other.get("/api/auth/me").status_code == 401  # l'altro non vale più subito, senza aspettare i 15 minuti...
    assert other.post("/api/auth/refresh").status_code == 401  # ...e non può rinnovarsi
    assert Api(app).login(password="nuova-password").status_code == 200


def test_admin_creates_user_who_changes_temporary_password(app, admin):
    new_user(admin)
    a = Api(app)
    r = a.login("anna@example.com", "password-provvisoria")
    assert r.json["user"]["must_change_password"] and not r.json["user"]["is_admin"]
    assert a.get("/api/bootstrap").status_code == 403
    a.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": ANNA_PW})
    assert a.get("/api/bootstrap").status_code == 200


def test_each_account_has_its_own_profiles_and_can_have_several(app, admin):
    a = anna(app, admin)
    mine = a.get("/api/bootstrap").json
    assert [p["name"] for p in mine["profiles"]] == ["Casa"]
    assert a.post("/api/profiles", json={"name": "Casa al mare"}).status_code == 201
    assert [p["name"] for p in a.get("/api/profiles").json["profiles"]] == ["Casa", "Casa al mare"]
    admin_profiles = admin.get("/api/profiles").json["profiles"]
    assert [p["name"] for p in admin_profiles] == ["Casa"]  # l'unico dell'admin (quello preesistente alla migrazione)
    assert admin_profiles[0]["id"] != mine["profiles"][0]["id"]


def test_cannot_use_or_touch_someone_elses_profile(app, admin):
    a = anna(app, admin)
    admin_pid = admin.get("/api/profiles").json["profiles"][0]["id"]
    admin.post("/api/bills", json={"commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-01-31", "total_eur": "50"})
    seen = a.get("/api/bills", headers={"X-Profile-Id": str(admin_pid)})  # Anna chiede il profilo dell'admin
    assert seen.status_code == 200 and seen.json["items"] == []
    assert a.delete(f"/api/profiles/{admin_pid}").status_code == 404
    assert a.post(f"/api/profiles/{admin_pid}/rename", json={"name": "x"}).status_code == 404


def test_existing_profiles_go_to_the_admin(tmp_path):
    plain = create_app(str(tmp_path))  # installazione senza login, con dati
    c = plain.test_client()
    c.post("/api/profiles", json={"name": "Secondo"})
    assert len(c.get("/api/profiles").json["profiles"]) == 2
    a = Api(make(tmp_path))  # stesso database, ora con il login
    a.login()
    assert [p["name"] for p in a.get("/api/profiles").json["profiles"]] == ["Casa", "Secondo"]


def test_admin_user_management_guards(app, admin):
    me = admin.get("/api/auth/me").json["user"]["id"]
    assert admin.delete(f"/api/users/{me}").status_code == 409
    assert admin.put(f"/api/users/{me}", json={"name": "A", "email": "admin@bollette.local", "is_admin": False}).status_code == 409
    uid = new_user(admin)
    assert admin.put(f"/api/users/{uid}", json={"name": "Anna R.", "email": "anna@example.com", "is_admin": True}).status_code == 200
    assert {u["email"]: u["is_admin"] for u in admin.get("/api/users").json["users"]}["anna@example.com"] is True
    assert admin.post(f"/api/users/{uid}/password", json={"password": "corta"}).status_code == 400
    victim = Api(app)
    victim.login("anna@example.com", "password-provvisoria")
    assert admin.post(f"/api/users/{uid}/password", json={"password": "reimpostata-123"}).status_code == 200
    assert victim.get("/api/auth/me").status_code == 401  # la reimpostazione scollega subito i suoi dispositivi
    assert Api(app).login("anna@example.com", "reimpostata-123").status_code == 200
    assert admin.delete(f"/api/users/{uid}").status_code == 200
    assert Api(app).login("anna@example.com", "reimpostata-123").status_code == 401


def test_deleted_user_loses_access_immediately(app, admin):
    uid = new_user(admin)
    a = Api(app)
    a.login("anna@example.com", "password-provvisoria")
    admin.delete(f"/api/users/{uid}")
    assert a.get("/api/auth/me").status_code == 401


def test_deleting_a_user_removes_profiles_and_pdfs(app, admin, monkeypatch):
    uid = new_user(admin)
    a = Api(app)
    a.login("anna@example.com", "password-provvisoria")
    a.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": ANNA_PW})
    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")
    st = app.extensions["storage"]
    st.put("a" * 32 + ".pdf", b"%PDF")
    a.post("/api/bills", json={"commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-01-31", "pdf_path": "a" * 32 + ".pdf"})
    assert admin.delete(f"/api/users/{uid}").status_code == 200
    assert not st.exists("a" * 32 + ".pdf")


# --- catalogo e PUN/PSV: solo admin e cron -----------------------------------

OFFER = {"commodity": "gas", "supplier": "S", "name": "Fissa", "price_type": "fixed", "price": "0.5"}


def test_only_admins_manage_the_shared_catalog(app, admin):
    a = anna(app, admin)
    assert a.post("/api/offers", json=OFFER).status_code == 403  # offerta di catalogo
    assert a.post("/api/offers/import-csv", data={}).status_code == 403
    assert a.post("/api/offers/import-arera").status_code == 403
    created = admin.post("/api/offers", json=OFFER)
    assert created.status_code == 200
    oid = created.json["id"]
    assert a.put(f"/api/offers/{oid}", json={**OFFER, "name": "Cambiata"}).status_code == 403
    assert a.delete(f"/api/offers/{oid}").status_code == 403
    assert a.get(f"/api/offers/{oid}").status_code == 200  # il catalogo si legge
    assert admin.put(f"/api/offers/{oid}", json={**OFFER, "name": "Cambiata"}).status_code == 200
    assert admin.delete(f"/api/offers/{oid}").status_code == 200


def test_users_keep_their_own_current_offer(app, admin):
    a = anna(app, admin)
    mine = a.post("/api/offers", json={**OFFER, "is_current": True})
    assert mine.status_code == 200
    oid = mine.json["id"]
    assert a.put(f"/api/offers/{oid}", json={**OFFER, "name": "Mia", "is_current": True}).status_code == 200
    assert admin.get(f"/api/offers/{oid}").status_code == 404  # è del profilo di Anna: l'admin non la vede come sua
    cat = admin.post("/api/offers", json={**OFFER, "name": "Catalogo"}).json["id"]
    copy = a.put(f"/api/offers/{cat}", json={**OFFER, "name": "Catalogo", "is_current": True})  # «questa è la mia»: crea una copia
    assert copy.status_code == 200 and copy.json["id"] != cat
    assert a.delete(f"/api/offers/{oid}").status_code == 200  # la propria offerta attuale si può togliere


SETTINGS = {"pun": "0,15", "psv": "0,5", "loss_pct": "10", "dispatching_extra": "0,02", "default_power_kw": "4,5",
            "region": "08", "province": "038", "comune": "038008"}


def test_only_admins_change_pun_psv_and_global_assumptions(app, admin):
    a = anna(app, admin)
    before = a.get("/api/settings").json["settings"]
    r = a.put("/api/settings", json=SETTINGS)
    assert r.status_code == 200
    after = r.json["settings"]
    assert after["default_power_kw"] == 4.5  # località e potenza sono del suo profilo
    assert (after["pun"], after["psv"], after["loss_pct"]) == (before["pun"], before["psv"], before["loss_pct"])
    assert a.post("/api/settings/use-recent").status_code == 403
    assert admin.put("/api/settings", json=SETTINGS).json["settings"]["pun"] == 0.15
    assert a.get("/api/settings").json["settings"]["pun"] == 0.15  # e vale per tutti


def test_uploading_a_bill_does_not_change_global_pun_for_normal_users(app, admin, monkeypatch):
    from app.services.bill_parser import OfferTerms

    a = anna(app, admin)
    terms = OfferTerms(offer={"commodity": "power", "supplier": "S", "name": "Mia", "price_type": "indexed", "spread": 0.01}, pun=0.30)
    monkeypatch.setattr("app.api.bills.parse_offer_terms", lambda text, commodity: terms)
    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")
    app.extensions["storage"].put("d" * 32 + ".pdf", b"%PDF")
    before = admin.get("/api/settings").json["settings"]["pun"]
    r = a.post("/api/bills", json={"commodity": "power", "period_start": "2026-01-01", "period_end": "2026-01-31", "pdf_path": "d" * 32 + ".pdf", "consumption": "100"})
    assert r.status_code == 201
    assert admin.get("/api/settings").json["settings"]["pun"] == before
    app.extensions["storage"].put("e" * 32 + ".pdf", b"%PDF")  # lo stesso upload fatto da un admin riallinea PUN
    admin.post("/api/bills", json={"commodity": "power", "period_start": "2026-02-01", "period_end": "2026-02-28", "pdf_path": "e" * 32 + ".pdf", "consumption": "100"})
    assert admin.get("/api/settings").json["settings"]["pun"] != before


def test_cron_token_only_opens_the_offers_import(tmp_path, monkeypatch):
    def offline():
        raise arera.AreraError("rete assente nel test")

    monkeypatch.setattr(arera, "fetch_offers", offline)
    app = make(tmp_path, CRON_TOKEN="segreto-del-cron")
    c = app.test_client()
    cron = {"Authorization": "Bearer segreto-del-cron"}
    assert c.get("/api/bills", headers=cron).status_code == 401
    assert c.post("/api/offers/import-arera", headers=CSRF).status_code == 401
    for url in ("/api/offers/import-arera", "/offers/import-arera"):
        assert c.post(url, headers={"Authorization": "Bearer sbagliato"}).status_code in (401, 403)
        assert c.post(url, headers=cron).status_code == 502  # autorizzato: poi l'esito dipende dalla rete


def test_import_offers_cli_works_without_login_or_token(tmp_path, monkeypatch):
    monkeypatch.setattr(arera, "fetch_offers", lambda: ([], Counter()))
    monkeypatch.setattr(arera, "fetch_index_history", lambda: (_ for _ in ()).throw(arera.AreraError("niente rete")))
    app = make(tmp_path)  # login attivo
    out = app.test_cli_runner().invoke(args=["import-offers"])
    assert out.exit_code == 0 and "Importate 0 offerte" in out.output
    monkeypatch.setattr(arera, "fetch_offers", lambda: (_ for _ in ()).throw(arera.AreraError("rete assente")))
    bad = app.test_cli_runner().invoke(args=["import-offers"])
    assert bad.exit_code == 1 and "rete assente" in bad.output
