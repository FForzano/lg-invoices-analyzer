import pytest

from app import auth, create_app
from app.services import extraction

PW = "una-password-lunga"


@pytest.fixture(autouse=True)
def fast_hashes(monkeypatch):
    monkeypatch.setattr(auth, "HASH_METHOD", "pbkdf2:sha256:1000")


def make(tmp_path, **cfg):
    app = create_app(str(tmp_path), AUTH_ENABLED=True, ADMIN_PASSWORD=PW, **cfg)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def app(tmp_path):
    return make(tmp_path)


def login(client, email="admin@bollette.local", password=PW):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    return r, {"Authorization": f"Bearer {r.json['token']}"} if r.status_code == 200 else {}


@pytest.fixture
def admin(app):
    c = app.test_client()
    return c, login(c)[1]


def new_user(c, h, email="anna@example.com", password="password-provvisoria", **extra):
    r = c.post("/api/users", json={"name": "Anna", "email": email, "password": password, **extra}, headers=h)
    assert r.status_code == 201, r.json
    return r.json["id"]


def test_login_off_by_default_everything_open(client):
    assert client.get("/api/auth/session").json == {"auth_enabled": False, "user": None}
    assert client.get("/api/bootstrap").status_code == 200
    assert client.post("/api/auth/login", json={}).status_code == 404
    assert client.get("/api/users").status_code == 404


def test_requests_need_a_token(app):
    c = app.test_client()
    assert c.get("/api/auth/session").json == {"auth_enabled": True, "user": None}
    assert c.get("/api/bootstrap").status_code == 401
    assert c.get("/api/bootstrap", headers={"Authorization": "Bearer finto"}).status_code == 401
    assert c.get("/health").status_code == 200  # healthcheck e pagine statiche restano pubblici


def test_default_admin_must_change_password(tmp_path):
    app = create_app(str(tmp_path), AUTH_ENABLED=True)  # nessuna ADMIN_PASSWORD: email e password di default
    c = app.test_client()
    r, h = login(c, password="admin")
    assert r.json["user"]["must_change_password"] and r.json["user"]["is_admin"]
    assert c.get("/api/bootstrap", headers=h).status_code == 403  # prima si cambia la password
    assert c.get("/api/auth/me", headers=h).status_code == 200
    bad = c.post("/api/auth/password", json={"current_password": "admin", "new_password": "corta"}, headers=h)
    assert bad.status_code == 400
    ok = c.post("/api/auth/password", json={"current_password": "admin", "new_password": PW}, headers=h)
    assert ok.status_code == 200 and not ok.json["user"]["must_change_password"]
    assert c.get("/api/bootstrap", headers=h).status_code == 200
    assert login(c, password="admin")[0].status_code == 401


def test_configured_admin_password_is_not_temporary(app):
    r, h = login(app.test_client())
    assert not r.json["user"]["must_change_password"]


def test_wrong_password_and_lockout(app):
    c = app.test_client()
    for _ in range(5):
        assert login(c, password="sbagliata")[0].status_code == 401
    r, _ = login(c)  # anche quella giusta, finché è bloccato
    assert r.status_code == 429
    assert login(c, email="nessuno@example.com")[0].status_code == 401  # stessa risposta se l'account non esiste


def test_logout_revokes_token(admin, app):
    c, h = admin
    assert c.post("/api/auth/logout", headers=h).status_code == 200
    assert c.get("/api/bootstrap", headers=h).status_code == 401


def test_update_personal_info(admin):
    c, h = admin
    r = c.put("/api/auth/me", json={"name": "Federico", "email": "Fede@Example.com"}, headers=h)
    assert r.json["user"]["name"] == "Federico" and r.json["user"]["email"] == "fede@example.com"
    assert c.put("/api/auth/me", json={"name": "", "email": "a@b.it"}, headers=h).status_code == 400
    assert c.put("/api/auth/me", json={"name": "X", "email": "non-una-email"}, headers=h).status_code == 400
    assert login(c, email="fede@example.com")[0].status_code == 200


def test_email_must_be_unique(admin):
    c, h = admin
    new_user(c, h)
    r = c.put("/api/auth/me", json={"name": "A", "email": "anna@example.com"}, headers=h)
    assert r.status_code == 409
    assert c.post("/api/users", json={"name": "B", "email": "ANNA@example.com", "password": "password-lunga"}, headers=h).status_code == 409


def test_change_password_needs_current_and_closes_other_sessions(admin):
    c, h = admin
    _, other = login(c)
    assert c.post("/api/auth/password", json={"current_password": "no", "new_password": "nuova-password"}, headers=h).status_code == 400
    assert c.post("/api/auth/password", json={"current_password": PW, "new_password": "nuova-password"}, headers=h).status_code == 200
    assert c.get("/api/auth/me", headers=h).status_code == 200  # la sessione che ha cambiato resta
    assert c.get("/api/auth/me", headers=other).status_code == 401
    assert login(c, password="nuova-password")[0].status_code == 200


def test_admin_creates_user_who_changes_temporary_password(admin):
    c, h = admin
    new_user(c, h)
    r, uh = login(c, "anna@example.com", "password-provvisoria")
    assert r.json["user"]["must_change_password"] and not r.json["user"]["is_admin"]
    assert c.get("/api/bootstrap", headers=uh).status_code == 403
    c.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": "la-mia-password"}, headers=uh)
    assert c.get("/api/bootstrap", headers=uh).status_code == 200


def test_normal_user_cannot_manage_users_or_import_offers(admin):
    c, h = admin
    new_user(c, h)
    _, uh = login(c, "anna@example.com", "password-provvisoria")
    c.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": "la-mia-password"}, headers=uh)
    assert c.get("/api/users", headers=uh).status_code == 403
    assert c.post("/api/users", json={}, headers=uh).status_code == 403
    assert c.post("/api/offers/import-arera", headers=uh).status_code == 403
    assert c.post("/offers/import-arera", headers=uh).status_code == 403  # anche dall'URL storico


def test_each_account_has_its_own_profiles_and_can_have_several(admin):
    c, h = admin
    new_user(c, h)
    _, ah = login(c, "anna@example.com", "password-provvisoria")
    c.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": "la-mia-password"}, headers=ah)
    mine = c.get("/api/bootstrap", headers=ah).json
    assert [p["name"] for p in mine["profiles"]] == ["Casa"]
    assert c.post("/api/profiles", json={"name": "Casa al mare"}, headers=ah).status_code == 201
    names = [p["name"] for p in c.get("/api/profiles", headers=ah).json["profiles"]]
    assert names == ["Casa", "Casa al mare"]
    admin_profiles = c.get("/api/profiles", headers=h).json["profiles"]
    assert [p["name"] for p in admin_profiles] == ["Casa"]  # l'unico dell'admin (quello preesistente alla migrazione)
    assert admin_profiles[0]["id"] != mine["profiles"][0]["id"]


def test_cannot_use_or_touch_someone_elses_profile(admin):
    c, h = admin
    new_user(c, h)
    _, ah = login(c, "anna@example.com", "password-provvisoria")
    c.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": "la-mia-password"}, headers=ah)
    admin_pid = c.get("/api/profiles", headers=h).json["profiles"][0]["id"]
    anna_pid = c.get("/api/profiles", headers=ah).json["profiles"][0]["id"]
    c.post("/api/bills", json={"commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-01-31", "total_eur": "50"}, headers={**h, "X-Profile-Id": str(admin_pid)})
    # Anna chiede il profilo dell'admin: riceve comunque il proprio, senza vedere le sue bollette
    seen = c.get("/api/bills", headers={**ah, "X-Profile-Id": str(admin_pid)})
    assert seen.status_code == 200 and seen.json["items"] == []
    assert c.delete(f"/api/profiles/{admin_pid}", headers=ah).status_code == 404
    assert c.post(f"/api/profiles/{admin_pid}/rename", json={"name": "x"}, headers=ah).status_code == 404
    assert anna_pid != admin_pid


def test_existing_profiles_go_to_the_admin(tmp_path):
    plain = create_app(str(tmp_path))  # installazione senza login, con dati
    c = plain.test_client()
    c.post("/api/profiles", json={"name": "Secondo"})
    assert len(c.get("/api/profiles").json["profiles"]) == 2
    app = make(tmp_path)  # stesso database, ora con il login
    ac = app.test_client()
    h = login(ac)[1]
    assert [p["name"] for p in ac.get("/api/profiles", headers=h).json["profiles"]] == ["Casa", "Secondo"]


def test_admin_user_management_guards(admin):
    c, h = admin
    me = c.get("/api/auth/me", headers=h).json["user"]["id"]
    assert c.delete(f"/api/users/{me}", headers=h).status_code == 409
    assert c.put(f"/api/users/{me}", json={"name": "A", "email": "admin@bollette.local", "is_admin": False}, headers=h).status_code == 409
    uid = new_user(c, h)
    assert c.put(f"/api/users/{uid}", json={"name": "Anna R.", "email": "anna@example.com", "is_admin": True}, headers=h).status_code == 200
    assert {u["email"]: u["is_admin"] for u in c.get("/api/users", headers=h).json["users"]}["anna@example.com"] is True
    assert c.post(f"/api/users/{uid}/password", json={"password": "corta"}, headers=h).status_code == 400
    assert c.post(f"/api/users/{uid}/password", json={"password": "reimpostata-123"}, headers=h).status_code == 200
    assert login(c, "anna@example.com", "reimpostata-123")[1]
    assert c.delete(f"/api/users/{uid}", headers=h).status_code == 200
    assert login(c, "anna@example.com", "reimpostata-123")[0].status_code == 401


def test_deleting_a_user_removes_profiles_and_pdfs(admin, app, monkeypatch):
    c, h = admin
    uid = new_user(c, h)
    _, ah = login(c, "anna@example.com", "password-provvisoria")
    c.post("/api/auth/password", json={"current_password": "password-provvisoria", "new_password": "la-mia-password"}, headers=ah)
    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")
    st = app.extensions["storage"]
    st.put("a" * 32 + ".pdf", b"%PDF")
    c.post("/api/bills", json={"commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-01-31", "pdf_path": "a" * 32 + ".pdf"}, headers=ah)
    assert c.delete(f"/api/users/{uid}", headers=h).status_code == 200
    assert not st.exists("a" * 32 + ".pdf")


def test_cron_token_only_opens_the_offers_import(tmp_path, monkeypatch):
    from app.api import offers

    app = make(tmp_path, CRON_TOKEN="segreto-del-cron")
    def offline():
        raise offers.arera.AreraError("rete assente nel test")

    monkeypatch.setattr(offers.arera, "fetch_offers", offline)
    c = app.test_client()
    cron = {"Authorization": "Bearer segreto-del-cron"}
    assert c.get("/api/bills", headers=cron).status_code == 401
    assert c.post("/api/offers/import-arera").status_code == 401
    for url in ("/api/offers/import-arera", "/offers/import-arera"):
        assert c.post(url, headers={"Authorization": "Bearer sbagliato"}).status_code == 401
        assert c.post(url, headers=cron).status_code != 401  # autorizzato (poi l'esito dipende dalla rete)
