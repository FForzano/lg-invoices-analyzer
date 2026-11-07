"""Paginazione di liste già in memoria."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    items: list
    number: int
    pages: int
    total: int


def paginate(items: list, number: int, per_page: int) -> Page:
    """Pagina `number` (1-based, riportata nei limiti) di `items`."""
    pages = max(1, -(-len(items) // per_page))
    number = min(max(number, 1), pages)
    start = (number - 1) * per_page
    return Page(items[start : start + per_page], number, pages, len(items))
