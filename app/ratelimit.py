"""Limite di richieste per chiave (es. IP) a finestra scorrevole, in memoria. Basta a scoraggiare abusi degli endpoint pubblici
(simulazione, registrazione); con più worker il limite effettivo è moltiplicato per il loro numero."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from flask import request

from .errors import ApiError

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def check(bucket: str, limit: int, window_seconds: int, what: str = "richieste") -> None:
    """Conta una richiesta di questo client in `bucket`; oltre `limit` nella finestra risponde 429."""
    now, key = time.monotonic(), f"{bucket}:{request.remote_addr}"
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            wait = int(window_seconds - (now - q[0])) // 60 + 1
            raise ApiError(f"Troppe {what}: riprova tra {wait} minuti.", 429)
        q.append(now)
        if len(_hits) > 10_000:  # niente crescita illimitata sotto un attacco da molti IP
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > window_seconds]:
                del _hits[k]


def reset() -> None:
    """Per i test."""
    with _lock:
        _hits.clear()
