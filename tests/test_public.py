"""Simulazione pubblica («Carica la tua ultima bolletta») e registrazione aperta."""
import io
from pathlib import Path

import pytest
from argon2 import PasswordHasher

from app import auth, create_app, db
from app.services import extraction

FIX = Path(__file__).parent / "fixtures"
CSRF = {"X-Requested-With": "bollette"}
PW = "una-password-lunga"


@pytest.fixture(autouse=True)
def fast_hashes(monkeypatch):
    monkeypatch.setattr(auth, "HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


def make(tmp_path, **cfg):
    app = create_app(str(tmp_path), AUTH_ENABLED=True, ADMIN_PASSWORD=PW, **cfg)
    app.config["TESTING"] = True
    return app


def seed_catalog(app):
    with app.app_context():
        for name, price in (("Economica", 0.10), ("Media", 0.14), ("Cara", 0.30)):
            db.save_offer(db_offer(name, price))


def db_offer(name, price):
    from app.models import Offer

    return Offer(commodity="power", supplier="Fornitore", name=name, price_type="fixed", price=price, fixed_fee_month=5.0)


def upload(client, fixture="bill_power.txt", name="bolletta.pdf", data=b"%PDF-finto"):
    return client.post("/api/simulate", data={"pdf": (io.BytesIO(data), name)}, content_type="multipart/form-data", headers=CSRF)


@pytest.fixture
def read_bill(monkeypatch):
    monkeypatch.setattr(extraction, "pdf_text", lambda p: (FIX / "bill_power.txt").read_text())


def test_simulation_needs_the_login_mode(client, read_bill):
    assert upload(client).status_code == 404  # senza login non c'è landing né simulazione


def test_session_tells_what_is_available(tmp_path):
    app = make(tmp_path, ALLOW_REGISTRATION=True)
    c = app.test_client()
    assert c.get("/api/auth/session").json == {"auth_enabled": True, "user": None, "registration_open": True, "demo": False}
    seed_catalog(app)
    assert c.get("/api/auth/session").json["demo"] is True


def test_anonymous_simulation_reads_the_bill_and_ranks_the_catalog(tmp_path, read_bill):
    app = make(tmp_path)
    seed_catalog(app)
    r = upload(app.test_client())
    assert r.status_code == 200, r.json
    out = r.json
    assert out["commodity"] == "power" and out["bill"]["consumption"] and out["bill"]["total_eur"]
    assert out["analysis"]["consumption"]["total"] > 0  # la bolletta di prova riporta il consumo annuo stampato
    assert "settings" not in out["analysis"]
    totals = [a["estimate"]["total"] for a in out["alternatives"]]
    assert totals == sorted(totals) and len(totals) == 3
    assert [a["offer"]["name"] for a in out["alternatives"]][0] == "Economica"


def test_simulation_with_recognized_current_offer_gives_a_verdict(tmp_path, monkeypatch):
    from app.services.bill_parser import OfferTerms

    app = make(tmp_path)
    seed_catalog(app)
    monkeypatch.setattr(extraction, "pdf_text", lambda p: (FIX / "bill_power.txt").read_text())
    current = {"commodity": "power", "supplier": "Attuale", "name": "Vecchia", "price_type": "fixed", "price": 0.40, "fixed_fee_month": 10.0}
    monkeypatch.setattr("app.api.public.parse_offer_terms", lambda text, commodity: OfferTerms(offer=current))
    out = upload(app.test_client()).json
    assert out["current_offer"] == {"name": "Vecchia", "supplier": "Attuale"}
    v = out["analysis"]["verdict"]
    assert v["worthwhile"] is True and v["saving"] > 0 and v["best"]["offer"]["name"] == "Economica"


def test_simulation_writes_nothing(tmp_path, read_bill):
    app = make(tmp_path)
    seed_catalog(app)
    before = (len(list((tmp_path / "pdf").glob("*"))), )
    upload(app.test_client())
    with app.app_context():
        d = db.get_db()
        assert d.execute("SELECT count(*) AS n FROM bills").fetchone()["n"] == 0
        assert d.execute("SELECT count(*) AS n FROM offers WHERE profile_id IS NOT NULL").fetchone()["n"] == 0
    assert (len(list((tmp_path / "pdf").glob("*"))), ) == before  # nessun PDF salvato


def test_simulation_never_uses_the_llm(tmp_path, monkeypatch):
    app = make(tmp_path)
    monkeypatch.setattr(extraction, "pdf_text", lambda p: "Fornitura: GAS NATURALE")  # lettura incompleta
    monkeypatch.setattr(extraction, "available", lambda: True)  # ...con la chiave dell'amministratore configurata
    monkeypatch.setattr(extraction, "_llm_extract", lambda *a, **k: pytest.fail("chiamato l'LLM da un utente anonimo"))
    r = upload(app.test_client())
    assert r.status_code == 422 and "Registrandoti" in r.json["error"]


def test_simulation_errors(tmp_path, monkeypatch):
    app = make(tmp_path)
    c = app.test_client()
    assert c.post("/api/simulate", data={}, content_type="multipart/form-data", headers=CSRF).status_code == 400
    assert upload(c, data=b"non un pdf").status_code == 400  # PdfReadError
    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")
    assert upload(c).status_code == 422  # scansione senza testo
    assert upload(c, data=b"x" * (7 * 1024 * 1024)).status_code == 413


def test_simulation_is_rate_limited(tmp_path, read_bill):
    app = make(tmp_path)
    seed_catalog(app)
    c = app.test_client()
    codes = [upload(c).status_code for _ in range(12)]
    assert codes[:10] == [200] * 10 and codes[10:] == [429, 429]


def test_registration_closed_by_default(tmp_path):
    c = make(tmp_path).test_client()
    r = c.post("/api/auth/register", json={"name": "A", "email": "a@example.com", "password": "password-lunga"}, headers=CSRF)
    assert r.status_code == 403


def test_open_registration_creates_a_normal_account_and_logs_in(tmp_path):
    app = make(tmp_path, ALLOW_REGISTRATION=True)
    c = app.test_client()
    r = c.post("/api/auth/register", json={"name": "Anna", "email": "Anna@Example.com", "password": "password-lunga"}, headers=CSRF)
    assert r.status_code == 201 and r.json["user"]["email"] == "anna@example.com"
    assert r.json["user"]["is_admin"] is False and not r.json["user"]["must_change_password"]
    assert [p["name"] for p in c.get("/api/profiles").json["profiles"]] == ["Casa"]  # già dentro, con il suo profilo
    assert c.post("/api/users", json={}, headers=CSRF).status_code == 403  # e non è admin
    dup = make(tmp_path, ALLOW_REGISTRATION=True).test_client().post(
        "/api/auth/register", json={"name": "B", "email": "anna@example.com", "password": "password-lunga"}, headers=CSRF)
    assert dup.status_code == 409


def test_registration_validates_and_is_rate_limited(tmp_path):
    c = make(tmp_path, ALLOW_REGISTRATION=True).test_client()
    bad = c.post("/api/auth/register", json={"name": "A", "email": "non-una-email", "password": "password-lunga"}, headers=CSRF)
    assert bad.status_code == 400
    assert c.post("/api/auth/register", json={"name": "A", "email": "a@example.com", "password": "corta"}, headers=CSRF).status_code == 400
    codes = [c.post("/api/auth/register", json={"name": "A", "email": f"u{i}@example.com", "password": "password-lunga"}, headers=CSRF).status_code for i in range(6)]
    assert 429 in codes


def test_trust_proxy_uses_forwarded_ip(tmp_path, read_bill):
    app = make(tmp_path, TRUST_PROXY=True)
    seed_catalog(app)
    c = app.test_client()
    for _ in range(10):
        assert upload(c).status_code == 200
    other = c.post("/api/simulate", data={"pdf": (io.BytesIO(b"%PDF"), "b.pdf")}, content_type="multipart/form-data",
                   headers={**CSRF, "X-Forwarded-For": "203.0.113.9"})
    assert other.status_code == 200  # un altro cliente dietro lo stesso proxy ha il suo limite
