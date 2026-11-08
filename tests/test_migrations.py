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

    (tmp_path / "sqlite").mkdir()
    (tmp_path / "sqlite" / "001_ok.sql").write_text("CREATE TABLE a (x);")
    (tmp_path / "sqlite" / "002_bad.sql").write_text("CREATE TABLE b (x); INSERT INTO nope VALUES (1);")
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


def test_profiles_migration_moves_existing_data_to_first_profile():
    conn = sqlite3.connect(":memory:")
    for version, path in migration_files():
        if version <= 7:
            conn.executescript(path.read_text())
    conn.execute("PRAGMA user_version = 7")
    conn.execute("INSERT INTO bills (commodity, period_start, period_end) VALUES ('gas', '2026-06-01', '2026-06-30')")
    conn.execute("INSERT INTO offers (commodity, supplier, name, price_type, is_current) VALUES ('gas', 'S', 'Mia', 'fixed', 1)")
    conn.execute("INSERT INTO offers (commodity, supplier, name, price_type) VALUES ('gas', 'S', 'Catalogo', 'fixed')")
    conn.execute("INSERT INTO settings (key, value) VALUES ('comune', '027042'), ('default_power_kw', 4.5), ('pun', 0.15)")
    conn.commit()
    migrate(conn)
    assert conn.execute("SELECT name, comune, default_power_kw FROM profiles").fetchall() == [("Casa", "027042", 4.5)]
    assert conn.execute("SELECT profile_id FROM bills").fetchall() == [(1,)]
    assert dict(conn.execute("SELECT name, profile_id FROM offers").fetchall()) == {"Mia": 1, "Catalogo": None}
    assert [r[0] for r in conn.execute("SELECT key FROM settings")] == ["pun"]  # le impostazioni di profilo escono dalla tabella globale


def test_both_engines_have_the_same_latest_migration():
    """Ogni modifica allo schema va scritta per SQLite e per PostgreSQL con lo stesso numero (vedi migrations/README.md)."""
    assert migration_files("sqlite")[-1][0] == migration_files("postgres")[-1][0]
    assert {n for n, _ in migration_files("postgres")} <= {n for n, _ in migration_files("sqlite")} | {11}


def test_postgres_sql_translation():
    from app.database import to_postgres

    assert to_postgres("SELECT * FROM t WHERE a = ? AND b = :p AND c::int > 0") == "SELECT * FROM t WHERE a = %s AND b = %(p)s AND c::int > 0"
    assert to_postgres("WHERE source LIKE 'bolletta:%' AND x = ?") == "WHERE source LIKE 'bolletta:%%' AND x = %s"
    assert to_postgres("WHERE name = 'a ? :b' AND y = ?") == "WHERE name = 'a ? :b' AND y = %s"
