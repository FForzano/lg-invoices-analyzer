import sqlite3

from app.migrations import migrate, migration_files
from app.models import Bill, Offer, columns


def table_columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_fresh_db_matches_models():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    assert table_columns(conn, "bills") == set(columns(Bill))
    assert table_columns(conn, "offers") == set(columns(Offer))
    assert conn.execute("PRAGMA user_version").fetchone()[0] == migration_files()[-1][0]


def test_migrate_is_idempotent():
    conn = sqlite3.connect(":memory:")
    assert migrate(conn)
    assert migrate(conn) == []


def test_upgrade_from_pre_migration_db_keeps_data():
    # DB creato prima del sistema di migrazioni: tabelle presenti, user_version = 0
    first = migration_files()[0][1].read_text()
    conn = sqlite3.connect(":memory:")
    conn.executescript(first)
    conn.execute("INSERT INTO bills (commodity, period_start, period_end) VALUES ('gas', '2026-06-01', '2026-06-30')")
    conn.commit()
    migrate(conn)
    assert "social_bonus_expires_on" in table_columns(conn, "bills")
    assert conn.execute("SELECT count(*) FROM bills").fetchone()[0] == 1


def test_failed_migration_does_not_advance_version(tmp_path, monkeypatch):
    from app import migrations

    (tmp_path / "001_ok.sql").write_text("CREATE TABLE a (x);")
    (tmp_path / "002_bad.sql").write_text("CREATE TABLE b (x); INSERT INTO nope VALUES (1);")
    monkeypatch.setattr(migrations, "DIR", tmp_path)
    conn = sqlite3.connect(":memory:", isolation_level=None)
    try:
        migrate(conn)
    except sqlite3.OperationalError:
        pass
    conn.execute("ROLLBACK") if conn.in_transaction else None
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    assert not conn.execute("SELECT name FROM sqlite_master WHERE name = 'b'").fetchall()


def test_concurrent_startup_applies_each_migration_once(tmp_path):
    """Più worker (gunicorn) avviano l'app insieme: una sola migrazione per versione, nessun errore."""
    import threading

    from app.migrations import migrate_database

    path = tmp_path / "bollette.db"
    barrier, errors = threading.Barrier(6), []

    def start():
        barrier.wait()
        try:
            migrate_database(path)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=start) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    assert sqlite3.connect(path).execute("PRAGMA user_version").fetchone()[0] == migration_files()[-1][0]
