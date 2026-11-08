"""Connessione al database: SQLite (predefinito) o PostgreSQL, con la stessa interfaccia minima.

Il resto dell'app scrive SQL con segnaposto `?` e `:nome` e legge le righe per nome (o per posizione);
qui si traduce per il motore scelto. Niente ORM: le query sono poche e restano leggibili."""
from __future__ import annotations

import re
import sqlite3

from .migrations import is_postgres, pg_url, sqlite_path


class Row(dict):
    """Riga di PostgreSQL: come sqlite3.Row si legge per nome (`r["id"]`) o per posizione (`r[0]`)."""

    def __getitem__(self, key):
        return super().__getitem__(list(self)[key] if isinstance(key, int) else key)


def _row_factory(cursor):
    names = [c.name for c in cursor.description or []]
    return lambda values: Row(zip(names, values))


_LITERAL = re.compile(r"('(?:[^']|'')*')")
_NAMED = re.compile(r"(?<![:\w]):([A-Za-z_]\w*)")


def to_postgres(sql: str) -> str:
    """`?` -> `%s`, `:nome` -> `%(nome)s`; i `%` letterali (es. LIKE 'a:%') vanno raddoppiati. I testi tra apici restano intatti."""
    parts = _LITERAL.split(sql)
    for i, part in enumerate(parts):
        part = part.replace("%", "%%")
        parts[i] = part if i % 2 else _NAMED.sub(r"%(\1)s", part.replace("?", "%s"))
    return "".join(parts)


class Database:
    """Una connessione (per richiesta). `dialect` è 'sqlite' o 'postgres'."""

    def __init__(self, url: str):
        self.url = url
        if is_postgres(url):
            import psycopg

            self.dialect = "postgres"
            self.conn = psycopg.connect(pg_url(url), row_factory=_row_factory)
        else:
            self.dialect = "sqlite"
            self.conn = sqlite3.connect(sqlite_path(url), timeout=30)
            self.conn.row_factory = sqlite3.Row

    @property
    def is_sqlite(self) -> bool:
        return self.dialect == "sqlite"

    def execute(self, sql: str, args=()):
        return self.conn.execute(sql if self.is_sqlite else to_postgres(sql), args)

    def executemany(self, sql: str, rows) -> None:
        if self.is_sqlite:
            self.conn.executemany(sql, rows)
        else:
            self.conn.cursor().executemany(to_postgres(sql), list(rows))

    def insert(self, sql: str, args=()) -> int:
        """INSERT che restituisce l'id della riga creata (RETURNING: SQLite ≥ 3.35 e PostgreSQL)."""
        if self.is_sqlite and sqlite3.sqlite_version_info < (3, 35):
            return self.execute(sql, args).lastrowid
        return self.execute(f"{sql} RETURNING id", args).fetchone()["id"]

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        self.conn.close()
