"""Migrazioni: file `NNN_nome.sql` applicati in ordine, uno per motore (`sqlite/`, `postgres/`, vedi README.md)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows: nessun lock, ok per un processo solo
    fcntl = None

DIR = Path(__file__).parent
PG_LOCK_KEY = 726354  # chiave del lock consultivo che serializza le migrazioni PostgreSQL


def migration_files(dialect: str = "sqlite") -> list[tuple[int, Path]]:
    files = [(int(m.group(1)), p) for p in (DIR / dialect).glob("*.sql") if (m := re.match(r"(\d+)_", p.name))]
    return sorted(files)


def migrate(conn: sqlite3.Connection) -> list[str]:
    """SQLite: applica le migrazioni mancanti, ciascuna in una transazione. Restituisce i nomi applicati."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    applied = []
    for number, path in migration_files("sqlite"):
        if number <= current:
            continue
        # PRAGMA user_version è transazionale: se lo script fallisce non avanza la versione
        conn.executescript(f"BEGIN;\n{path.read_text()}\nPRAGMA user_version = {number};\nCOMMIT;")
        applied.append(path.name)
    return applied


def migrate_postgres(conn) -> list[str]:
    """PostgreSQL: tutto in una transazione sotto lock consultivo (gli altri worker aspettano e poi non trovano nulla da fare)."""
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (PG_LOCK_KEY,))
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT max(version) FROM schema_version").fetchone()
    current = row[0] or 0
    applied = []
    for number, path in migration_files("postgres"):
        if number <= current:
            continue
        conn.execute(path.read_text())  # nessun parametro: più istruzioni per file vanno bene
        conn.execute("INSERT INTO schema_version (version) VALUES (%s)", (number,))
        applied.append(path.name)
    conn.commit()
    return applied


def sqlite_path(url: str) -> Path:
    """`sqlite:///relativo.db` -> relativo.db, `sqlite:////assoluto.db` -> /assoluto.db. Accetta anche un percorso nudo."""
    return Path(url[len("sqlite:///"):] if url.startswith("sqlite:///") else url)


def migrate_database(url: str | Path) -> list[str]:
    """Migra il database indicato dall'URL (o dal percorso di un file SQLite)."""
    url = str(url)
    if is_postgres(url):
        import psycopg

        with psycopg.connect(pg_url(url)) as conn:
            return migrate_postgres(conn)
    # Un lock su file serializza i processi (es. i worker di gunicorn che avviano l'app insieme):
    # senza, due worker potrebbero applicare la stessa migrazione.
    path = sqlite_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "w") as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        conn = sqlite3.connect(path, timeout=30)
        try:
            return migrate(conn)
        finally:
            conn.close()


def is_postgres(url: str) -> bool:
    return url.split(":", 1)[0].split("+", 1)[0] in ("postgres", "postgresql")


def pg_url(url: str) -> str:
    """libpq non conosce `postgresql+psycopg://`: toglie l'eventuale suffisso del driver."""
    scheme, rest = url.split(":", 1)
    return f"postgresql:{rest}" if "+" in scheme or scheme == "postgres" else url
