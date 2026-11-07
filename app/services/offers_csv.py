"""Import offerte da CSV. Le colonne sono i nomi dei campi di `Offer`."""
from __future__ import annotations

import csv
import io

from .. import forms
from ..models import Offer


def parse_offers_csv(text: str) -> tuple[list[Offer], list[str]]:
    """Restituisce (offerte valide, errori per riga). Separatore , o ; riconosciuto dall'intestazione."""
    text = text.lstrip("﻿")
    header = text.splitlines()[0] if text.strip() else ""
    delimiter = ";" if header.count(";") > header.count(",") else ","
    offers, errors = [], []
    for n, row in enumerate(csv.DictReader(io.StringIO(text), delimiter=delimiter), start=2):
        try:
            offers.append(forms.parse(Offer, row))
        except ValueError as e:
            errors.append(f"Riga {n}: {e}")
    return offers, errors
