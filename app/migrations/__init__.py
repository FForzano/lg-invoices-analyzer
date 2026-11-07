"""Migrazioni SQLite: file `NNN_nome.sql` applicati in ordine, versione in `PRAGMA user_version`."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows: nessun lock, ok per un processo solo
    fcntl = None

DIR = Path(__file__).parent


def migration_files() -> list[tuple[int, Path]]:
    files = [(int(m.group(1)), p) for p in DIR.glob("*.sql") if (m := re.match(r"(\d+)_", p.name))]
    return sorted(files)


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Applica le migrazioni mancanti, ciascuna in una transazione. Restituisce i nomi applicati."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    applied = []
    for number, path in migration_files():
        if number <= current:
            continue
        # PRAGMA user_version è transazionale: se lo script fallisce non avanza la versione
        conn.executescript(f"BEGIN;\n{path.read_text()}\nPRAGMA user_version = {number};\nCOMMIT;")
        applied.append(path.name)
    return applied


def migrate_database(path: str | Path) -> list[str]:
    """Apre il database e lo migra. Un lock su file serializza i processi (es. i worker di gunicorn che
    avviano l'app insieme): senza, due worker potrebbero applicare la stessa migrazione."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "w") as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        conn = sqlite3.connect(path, timeout=30)
        try:
            return migrate(conn)
        finally:
            conn.close()
