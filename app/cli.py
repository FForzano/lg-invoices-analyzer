"""Comandi di servizio (`flask --app app <comando>`), per chi cambia database o storage su un'installazione già in uso."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import click
from flask import Flask

from . import db
from .services import arera, catalog
from .migrations import migrate_database, sqlite_path

# ordine di copia: prima le tabelle da cui le altre dipendono
TABLES = ("users", "profiles", "settings", "index_factors", "bill_layouts", "offers", "bills", "proposals")
WITH_ID = ("users", "profiles", "bill_layouts", "offers", "bills", "proposals")


def register(app: Flask) -> None:
    @app.cli.command("import-sqlite")
    @click.argument("source", type=click.Path(exists=True, dir_okay=False))
    def import_sqlite(source: str) -> None:
        """Copia i dati di un database SQLite (es. quello di prima: data/bollette.db) in quello configurato con DATABASE_URL.
        Il database di destinazione deve essere nuovo (senza bollette né offerte)."""
        target = db.get_db()
        if target.is_sqlite and sqlite_path(app.config["DATABASE_URL"]).resolve() == Path(source).resolve():
            raise click.ClickException("Origine e destinazione sono lo stesso database.")
        if any(target.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in ("bills", "offers", "proposals")):
            raise click.ClickException("Il database di destinazione contiene già dati: usa un database nuovo.")
        migrate_database(f"sqlite:///{source}")  # porta alla versione corrente un database vecchio
        src = sqlite3.connect(source)
        src.row_factory = sqlite3.Row
        have = {r["name"] for r in src.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        for table in reversed(TABLES):  # il profilo «Casa» creato dalla migrazione cede il posto a quelli importati
            target.execute(f"DELETE FROM {table}")
        for table in TABLES:
            if table not in have:
                continue
            cols = [d[0] for d in target.execute(f"SELECT * FROM {table} LIMIT 0").description]
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            names = [c for c in cols if c in rows[0].keys()] if rows else []
            if rows:
                target.executemany(f"INSERT INTO {table} ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})",
                                   [tuple(r[c] for c in names) for r in rows])
            click.echo(f"{table}: {len(rows)} righe")
        if not target.is_sqlite:  # con gli id copiati a mano la sequenza va riallineata
            for table in WITH_ID:
                target.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT max(id) FROM {table}), 0) + 1, false)")
        target.commit()
        src.close()
        click.echo("Fatto.")

    @app.cli.command("upload-pdfs")
    @click.option("--from", "source", type=click.Path(exists=True, file_okay=False), default=None,
                  help="Cartella con i PDF (default: DATA_DIR/pdf, dove stavano prima).")
    def upload_pdfs(source: str | None) -> None:
        """Carica nello storage configurato (es. S3) i PDF delle bollette che stanno ancora in una cartella locale."""
        folder = Path(source) if source else app.config["DATA_DIR"] / "pdf"
        storage = app.extensions["storage"]
        names = [r["pdf_path"] for r in db.get_db().execute("SELECT pdf_path FROM bills WHERE pdf_path IS NOT NULL")]
        sent = missing = 0
        for name in names:
            path = folder / name
            if storage.exists(name):
                continue
            if not path.is_file():
                missing += 1
                continue
            storage.put(name, path.read_bytes())
            sent += 1
        click.echo(f"Caricati {sent} PDF su {storage}; già presenti: {len(names) - sent - missing}; non trovati in {folder}: {missing}.")

    @app.cli.command("import-offers")
    def import_offers() -> None:
        """Aggiorna dal Portale Offerte ARERA il catalogo delle offerte e i prezzi storici di PUN/PSV, senza passare dal web.
        Con il login attivo è il modo più semplice per il cron: `docker exec bollette flask --app app import-offers`."""
        try:
            messages = catalog.refresh_catalog()
        except arera.AreraError as e:
            raise click.ClickException(str(e)) from None
        for m in messages:
            click.echo(m["text"])
