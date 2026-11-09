"""Posta in uscita, opzionale: serve solo al recupero password. Senza MAIL_HOST e MAIL_FROM non si invia nulla e l'app lo dichiara."""
from __future__ import annotations

import smtplib
import ssl
import threading
from email.message import EmailMessage

from flask import current_app


def enabled() -> bool:
    cfg = current_app.config
    return bool(cfg["MAIL_HOST"] and cfg["MAIL_FROM"])


def _send(cfg: dict, msg: EmailMessage) -> None:
    ctx = ssl.create_default_context()
    if cfg["MAIL_SECURITY"] == "ssl":
        server = smtplib.SMTP_SSL(cfg["MAIL_HOST"], cfg["MAIL_PORT"], timeout=15, context=ctx)
    else:
        server = smtplib.SMTP(cfg["MAIL_HOST"], cfg["MAIL_PORT"], timeout=15)
    with server:
        if cfg["MAIL_SECURITY"] == "starttls":
            server.starttls(context=ctx)
        if cfg["MAIL_USER"]:
            server.login(cfg["MAIL_USER"], cfg["MAIL_PASSWORD"])
        server.send_message(msg)


def send(to: str, subject: str, body: str) -> None:
    """Invia in un thread a parte: la risposta HTTP non deve dire (col tempo che ci mette) se l'indirizzo esiste. Gli errori vanno nel log."""
    app = current_app._get_current_object()  # noqa: SLF001
    cfg = dict(app.config)
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = cfg["MAIL_FROM"], to, subject
    msg.set_content(body)

    def run() -> None:
        try:
            _send(cfg, msg)
        except Exception:  # noqa: BLE001
            app.logger.exception("Invio email a %s non riuscito.", to)

    if app.testing:
        run()
    else:
        threading.Thread(target=run, daemon=True).start()
