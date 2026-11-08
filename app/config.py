"""Configurazione da variabili d'ambiente. Tutto è opzionale: senza nulla l'app funziona come sempre
(SQLite e PDF nella cartella dati, nessun login), che è quello che serve a un'installazione self-hosted in casa."""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

TRUE = {"1", "true", "yes", "on", "si", "sì"}
DEFAULT_ADMIN_EMAIL = "admin@bollette.local"
DEFAULT_ADMIN_PASSWORD = "admin"


def flag(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE


def from_env(env: Mapping[str, str] | None = None, data_dir: str | Path | None = None) -> dict:
    """Costruisce la configurazione dell'app (chiavi in maiuscolo, come `app.config`).

    Database:   DATABASE_URL  sqlite:///percorso.db | postgresql://utente:password@host:5432/nome  (default: SQLite in DATA_DIR)
    File:       STORAGE_DRIVER=local|s3
                local: STORAGE_PATH (default DATA_DIR/pdf)
                s3:    S3_BUCKET, S3_PREFIX, S3_ENDPOINT_URL (MinIO e simili), S3_REGION,
                       S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY (senza: catena standard di AWS), S3_ADDRESSING=path|virtual
    Login:      AUTH_ENABLED=true  (con ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY, ACCESS_MINUTES, SESSION_DAYS, COOKIE_SECURE, CRON_TOKEN)"""
    env = os.environ if env is None else env
    data = Path(data_dir or env.get("DATA_DIR") or "data")
    return {
        "DATA_DIR": data,
        "DATABASE_URL": env.get("DATABASE_URL") or f"sqlite:///{data / 'bollette.db'}",
        "STORAGE_DRIVER": (env.get("STORAGE_DRIVER") or "local").strip().lower(),
        "STORAGE_PATH": Path(env.get("STORAGE_PATH") or data / "pdf"),
        "S3_BUCKET": env.get("S3_BUCKET", ""),
        "S3_PREFIX": env.get("S3_PREFIX", ""),
        "S3_ENDPOINT_URL": env.get("S3_ENDPOINT_URL") or None,
        "S3_REGION": env.get("S3_REGION") or None,
        "S3_ACCESS_KEY_ID": env.get("S3_ACCESS_KEY_ID") or None,
        "S3_SECRET_ACCESS_KEY": env.get("S3_SECRET_ACCESS_KEY") or None,
        "S3_ADDRESSING": (env.get("S3_ADDRESSING") or "auto").strip().lower(),
        "AUTH_ENABLED": flag(env.get("AUTH_ENABLED")),
        "ADMIN_EMAIL": (env.get("ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL).strip().lower(),
        "ADMIN_PASSWORD": env.get("ADMIN_PASSWORD") or None,  # None = quella di default, da cambiare al primo accesso
        "SECRET_KEY": env.get("SECRET_KEY") or None,  # firma i JWT; None = ne viene generata una e conservata nel database
        "ACCESS_MINUTES": int(env.get("ACCESS_MINUTES") or 15),  # durata dell'access token
        "SESSION_DAYS": int(env.get("SESSION_DAYS") or 30),  # un accesso scade dopo tanti giorni senza usare l'app (il refresh ruota a ogni uso)
        "COOKIE_SECURE": (env.get("COOKIE_SECURE") or "auto").strip().lower(),  # auto = Secure se la richiesta arriva in HTTPS
        "CRON_TOKEN": env.get("CRON_TOKEN") or None,
    }
