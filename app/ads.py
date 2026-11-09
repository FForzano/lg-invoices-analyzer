"""Spazi pubblicitari predisposti ma spenti: senza ADS_FILE non compare nulla.

Il file è JSON, scritto a mano da chi gestisce il sito (deploy/ads.example.json). Sono contenuti **propri** (anche la promozione di un
altro prodotto del gestore): testo, un link e, se serve, un'immagine o un video **messi nella stessa cartella del file** e serviti da questo
stesso server. Nessuno script, pixel o cookie e nessuna richiesta verso altri siti, quindi non serve il consenso previsto dall'art. 122 del
Codice privacy. Reti pubblicitarie con tracciamento e video incorporati da YouTube e simili NON sono previsti: richiederebbero un banner di
consenso e un'informativa diversa.
Ogni annuncio è mostrato dal front-end con la dicitura «Sponsorizzato» (D.Lgs. 70/2003, art. 8).

Spazi (`slot`): simulation-result (risultato della simulazione pubblica), bills-list (elenco delle bollette, dove si arriva dopo averne caricata una),
compare-end (in fondo al confronto). Un annuncio può valere per più spazi; `from`/`to` (AAAA-MM-GG) ne limitano il periodo."""
from __future__ import annotations

import json
import random
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app

SLOTS = ("simulation-result", "bills-list", "compare-end")
LIMITS = {"sponsor": 60, "title": 90, "text": 240, "cta": 30, "alt": 140}
IMAGES, VIDEOS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}, {".mp4", ".webm"}
MEDIA = re.compile(r"[\w][\w .-]*")  # solo un nome di file: niente percorsi, niente ".."


def media_dir() -> Path | None:
    path = current_app.config["ADS_FILE"]
    return Path(path).resolve().parent if path else None


def _media(raw: object, allowed: set[str]) -> str:
    """Nome di un file nella cartella degli annunci, se esiste e ha un'estensione ammessa; altrimenti vuoto."""
    name, folder = str(raw or "").strip(), media_dir()
    if not folder or not MEDIA.fullmatch(name) or Path(name).suffix.lower() not in allowed or not (folder / name).is_file():
        return ""
    return name


def _clean(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    ad = {k: str(raw.get(k, "")).strip()[:n] for k, n in LIMITS.items()}
    url = urlparse(str(raw.get("url", "")).strip())
    if not (ad["sponsor"] and ad["title"] and url.scheme == "https" and url.netloc):  # solo https, e sempre un nome dello sponsor
        return None
    slots = [s for s in raw.get("slots", []) if s in SLOTS] if isinstance(raw.get("slots"), list) else []
    return {**ad, "cta": ad["cta"] or "Scopri di più", "url": url.geturl(), "slots": slots,
            "image": _media(raw.get("image"), IMAGES), "video": _media(raw.get("video"), VIDEOS),
            "from": str(raw.get("from", "")), "to": str(raw.get("to", ""))}


def load() -> list[dict]:
    path = current_app.config["ADS_FILE"]
    if not path:
        return []
    try:
        with open(path, encoding="utf-8") as f:
            items = json.load(f).get("ads", [])
    except (OSError, ValueError, AttributeError):
        current_app.logger.warning("ADS_FILE non leggibile (%s): nessun annuncio.", path)
        return []
    return [a for a in map(_clean, items) if a]


def enabled() -> bool:
    return bool(load())


def pick(slot: str, today: date | None = None) -> dict | None:
    today = (today or date.today()).isoformat()
    live = [a for a in load() if slot in a["slots"] and (not a["from"] or a["from"] <= today) and (not a["to"] or today <= a["to"])]
    if not live:
        return None
    ad = random.choice(live)
    media = {k: f"/api/ads/media/{ad[k]}" if ad[k] else None for k in ("image", "video")}
    return {k: ad[k] for k in ("sponsor", "title", "text", "cta", "url")} | media | {"alt": ad["alt"] or ad["title"]}
