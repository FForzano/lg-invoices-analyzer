"""Filtri di ricerca sulle offerte, uguali per l'elenco Offerte e per il Confronto."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from ..models import Offer


@dataclass(frozen=True)
class OfferFilter:
    q: str = ""
    price_type: str | None = None  # "fixed" | "indexed"
    no_exit: bool = False  # esclude le offerte con oneri di recesso anticipato dichiarati
    bonus: bool = False  # solo offerte con bonus o sconti dichiarati

    @classmethod
    def from_args(cls, args: Mapping[str, str]) -> OfferFilter:
        kind = args.get("type", "")
        return cls(q=args.get("q", "").strip().lower(), price_type=kind if kind in ("fixed", "indexed") else None,
                   no_exit=args.get("no_exit") == "1", bonus=args.get("bonus") == "1")

    def keep(self, o: Offer) -> bool:
        if self.q and self.q not in f"{o.supplier} {o.name}".lower():
            return False
        if self.price_type and o.price_type != self.price_type:
            return False
        if self.no_exit and o.exit_terms:
            return False
        return not (self.bonus and not o.bonus_terms)

    def keep_bundle(self, power: Offer, gas: Offer) -> bool:
        """Luce + gas insieme: gli altri limiti valgono per entrambe le metà, il bonus basta su una."""
        each = replace(self, bonus=False)
        return each.keep(power) and each.keep(gas) and (not self.bonus or bool(power.bonus_terms or gas.bonus_terms))
