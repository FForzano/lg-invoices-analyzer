"""Parsing di form/righe CSV in dataclass, guidato dai tipi dei campi."""
from __future__ import annotations

import dataclasses
import typing
from typing import Mapping, TypeVar

from .models import SYSTEM_FIELDS

T = TypeVar("T")


def parse(cls: type[T], data: Mapping[str, str | None]) -> T:
    """Costruisce `cls` da una mappa di stringhe. Solleva ValueError con un messaggio leggibile."""
    hints = typing.get_type_hints(cls)
    values: dict = {}
    for f in dataclasses.fields(cls):
        if f.name in SYSTEM_FIELDS:
            continue
        tp = _base_type(hints[f.name])
        raw = (data.get(f.name) or "").strip()
        if tp is bool:
            values[f.name] = raw.lower() in ("on", "1", "true", "si", "sì")
        elif not raw:
            if f.default is dataclasses.MISSING:
                raise ValueError(f"Campo obbligatorio mancante: {f.name}")
            values[f.name] = None
        else:
            values[f.name] = _cast(tp, raw, f)
    return cls(**values)


def _base_type(tp):
    args = [a for a in typing.get_args(tp) if a is not type(None)]
    return args[0] if args else tp


def _cast(tp, raw: str, f: dataclasses.Field):
    try:
        if tp is float:
            return float(raw.replace(",", "."))
        if tp is int:
            return int(raw)
    except ValueError:
        raise ValueError(f"Valore numerico non valido per {f.name}: {raw!r}") from None
    choices = f.metadata.get("choices")
    if choices and raw not in choices:
        raise ValueError(f"Valore non valido per {f.name}: {raw!r} (ammessi: {', '.join(choices)})")
    return raw
