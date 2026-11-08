"""Database e storage alternativi. PostgreSQL e MinIO veri si provano impostando TEST_DATABASE_URL / TEST_S3_ENDPOINT
(vedi README, «Test»); S3 si prova sempre, con moto."""
import os

import pytest

from app import create_app
from app.storage import LocalStorage, S3Storage, from_config

PG = os.environ.get("TEST_DATABASE_URL")
MINIO = os.environ.get("TEST_S3_ENDPOINT")
BILL = {"commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-01-31", "total_eur": "50", "consumption": "100"}
PDF = b"%PDF-1.4 finto"


def roundtrip(store):
    store.put("a" * 32 + ".pdf", PDF)
    assert store.exists("a" * 32 + ".pdf") and store.get("a" * 32 + ".pdf") == PDF
    store.delete("a" * 32 + ".pdf")
    store.delete("a" * 32 + ".pdf")  # cancellare due volte non è un errore
    assert not store.exists("a" * 32 + ".pdf")
    with pytest.raises(FileNotFoundError):
        store.get("a" * 32 + ".pdf")
    with pytest.raises(ValueError):
        store.put("../fuori.pdf", PDF)


def test_local_storage(tmp_path):
    roundtrip(LocalStorage(tmp_path / "pdf"))


def test_s3_storage_with_moto():
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")
    with moto.mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="bollette")
        store = S3Storage("bollette", prefix="prod/pdf", region="us-east-1", access_key_id="x", secret_access_key="y")
        store.check()
        roundtrip(store)
        store.put("b" * 32 + ".pdf", PDF)
        assert store.client.list_objects_v2(Bucket="bollette")["Contents"][0]["Key"] == "prod/pdf/" + "b" * 32 + ".pdf"


def test_driver_selection(tmp_path):
    assert isinstance(create_app(str(tmp_path)).extensions["storage"], LocalStorage)  # predefinito: locale
    with pytest.raises(ValueError, match="STORAGE_DRIVER"):
        create_app(str(tmp_path), STORAGE_DRIVER="ftp")
    with pytest.raises(ValueError, match="S3_BUCKET"):
        create_app(str(tmp_path), STORAGE_DRIVER="s3", S3_BUCKET="")
    assert create_app(str(tmp_path)).config["DATABASE_URL"].startswith("sqlite:///")
    assert create_app(str(tmp_path)).config["AUTH_ENABLED"] is False


def test_app_stores_pdfs_in_s3_when_configured(tmp_path, monkeypatch):
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")
    from app.services import extraction

    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")
    with moto.mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="bollette")
        app = create_app(str(tmp_path), STORAGE_DRIVER="s3", S3_BUCKET="bollette", S3_REGION="us-east-1",
                         S3_ACCESS_KEY_ID="x", S3_SECRET_ACCESS_KEY="y")
        c = app.test_client()
        r = c.post("/api/bills/upload", data={"pdf": (__import__("io").BytesIO(PDF), "b.pdf")}, content_type="multipart/form-data")
        name = r.json["prefill"]["values"]["pdf_path"]
        assert not list((tmp_path / "pdf").glob("*")) if (tmp_path / "pdf").exists() else True  # niente su disco
        bill = c.post("/api/bills", json={**BILL, "pdf_path": name}).json["id"]
        assert c.get(f"/api/bills/{bill}/pdf").data == PDF
        pid = c.get("/api/profiles").json["profiles"][0]["id"]
        c.post("/api/profiles", json={"name": "Altra"})
        c.delete(f"/api/profiles/{pid}")  # elimina anche il PDF dal bucket
        assert not app.extensions["storage"].exists(name)


def test_upload_pdfs_command_copies_local_files_to_s3(tmp_path, monkeypatch):
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")
    from app.services import extraction

    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")
    old = create_app(str(tmp_path))  # installazione di prima: PDF su disco
    c = old.test_client()
    old.extensions["storage"].put("c" * 32 + ".pdf", PDF)
    c.post("/api/bills", json={**BILL, "pdf_path": "c" * 32 + ".pdf"})
    with moto.mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="bollette")
        new = create_app(str(tmp_path), STORAGE_DRIVER="s3", S3_BUCKET="bollette", S3_REGION="us-east-1",
                         S3_ACCESS_KEY_ID="x", S3_SECRET_ACCESS_KEY="y")
        out = new.test_cli_runner().invoke(args=["upload-pdfs"])
        assert out.exit_code == 0 and "Caricati 1 PDF" in out.output
        assert new.extensions["storage"].get("c" * 32 + ".pdf") == PDF


@pytest.mark.skipif(not MINIO, reason="TEST_S3_ENDPOINT non impostato")
def test_minio_storage():
    store = S3Storage(os.environ.get("TEST_S3_BUCKET", "bollette"), "test", MINIO, None,
                      os.environ.get("TEST_S3_KEY", "minio"), os.environ.get("TEST_S3_SECRET", "minio12345"))
    store.check()
    roundtrip(store)


@pytest.fixture
def pg_url():
    import psycopg

    with psycopg.connect(PG, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    return PG


@pytest.mark.skipif(not PG, reason="TEST_DATABASE_URL non impostato")
class TestPostgres:
    def test_schema_matches_models(self, pg_url):
        import psycopg

        from app.models import Bill, Offer, columns

        create_app("unused-data", DATABASE_URL=pg_url)
        with psycopg.connect(pg_url) as conn:
            cols = lambda t: {r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (t,))}  # noqa: E731
            assert cols("bills") == set(columns(Bill)) and cols("offers") == set(columns(Offer))
            from app.migrations import migration_files

            assert conn.execute("SELECT max(version) FROM schema_version").fetchone()[0] == migration_files("postgres")[-1][0]

    def test_full_flow(self, pg_url, tmp_path):
        app = create_app(str(tmp_path), DATABASE_URL=pg_url)
        c = app.test_client()
        bill = c.post("/api/bills", json=BILL)
        assert bill.status_code == 201
        assert c.get("/api/bills").json["items"][0]["consumption"] == 100.0
        assert c.put("/api/settings", json={"pun": "0,15", "psv": "0,4", "loss_pct": "10", "dispatching_extra": "0,019",
                                           "default_power_kw": "4,5", "region": "08", "province": "038", "comune": "038008"}).status_code == 200
        s = c.get("/api/settings").json["settings"]
        assert s["pun"] == 0.15 and s["default_power_kw"] == 4.5 and s["comune"] == "038008"
        offer = {"commodity": "gas", "supplier": "S", "name": "Fissa", "price_type": "fixed", "price": "0,5", "is_current": "1"}
        assert c.post("/api/offers", json=offer).status_code in (200, 201)
        assert c.get("/api/compare/gas").status_code == 200
        c.post("/api/profiles", json={"name": "Seconda"})
        assert len(c.get("/api/profiles").json["profiles"]) == 2

    def test_auth_and_migrations_twice(self, pg_url, tmp_path):
        create_app(str(tmp_path), DATABASE_URL=pg_url)
        app = create_app(str(tmp_path), DATABASE_URL=pg_url, AUTH_ENABLED=True, ADMIN_PASSWORD="una-password-lunga")  # secondo avvio: niente da migrare
        c, h = app.test_client(), {"X-Requested-With": "bollette"}
        assert c.post("/api/auth/login", json={"email": "admin@bollette.local", "password": "una-password-lunga"}, headers=h).status_code == 200
        assert [p["name"] for p in c.get("/api/profiles").json["profiles"]] == ["Casa"]
        assert c.post("/api/users", json={"name": "A", "email": "a@b.it", "password": "password-lunga"}, headers=h).status_code == 201
        assert c.post("/api/users", json={"name": "A", "email": "a@b.it", "password": "password-lunga"}, headers=h).status_code == 409
        # rotazione del refresh token su PostgreSQL (UPDATE ... WHERE used_at IS NULL, rowcount, famiglie)
        assert c.post("/api/auth/refresh", headers=h).status_code == 200 and c.post("/api/auth/refresh", headers=h).status_code == 200
        assert c.post("/api/auth/logout", headers=h).status_code == 200 and c.post("/api/auth/refresh", headers=h).status_code == 401
        key = app.extensions["jwt_secret"]
        second = create_app(str(tmp_path / "altra"), DATABASE_URL=pg_url, AUTH_ENABLED=True)  # un'altra istanza sullo stesso database
        assert len(key) == 64 and second.extensions["jwt_secret"] == key  # la chiave dei JWT sta nel database, condivisa

    def test_import_sqlite_command(self, pg_url, tmp_path):
        old = create_app(str(tmp_path / "old"))
        oc = old.test_client()
        oc.post("/api/bills", json=BILL)
        oc.post("/api/profiles", json={"name": "Seconda"})
        oc.put("/api/settings", json={"pun": "0,2", "psv": "0,4", "loss_pct": "10", "dispatching_extra": "0,019",
                                     "default_power_kw": "3", "region": "08", "province": "038", "comune": "038008"})
        new = create_app(str(tmp_path / "new"), DATABASE_URL=pg_url)
        out = new.test_cli_runner().invoke(args=["import-sqlite", str(tmp_path / "old" / "bollette.db")])
        assert out.exit_code == 0, out.output
        c = new.test_client()
        assert len(c.get("/api/bills").json["items"]) == 1
        assert [p["name"] for p in c.get("/api/profiles").json["profiles"]] == ["Casa", "Seconda"]
        assert c.get("/api/settings").json["settings"]["pun"] == 0.2
        assert c.post("/api/profiles", json={"name": "Terza"}).status_code == 201  # le sequenze sono state riallineate
        again = new.test_cli_runner().invoke(args=["import-sqlite", str(tmp_path / "old" / "bollette.db")])
        assert again.exit_code != 0  # non sovrascrive un database con dati
