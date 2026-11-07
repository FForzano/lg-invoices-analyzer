"""Entità del dominio. I campi delle dataclass sono la fonte di verità per
colonne SQL, parsing dei form, import CSV e schema di estrazione LLM."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field, replace

COMMODITIES = ("power", "gas")
COMMODITY_LABEL = {"power": "Luce", "gas": "Gas"}
UNIT = {"power": "kWh", "gas": "Smc"}


@dataclass(kw_only=True)
class Bill:
    commodity: str = field(metadata={"choices": COMMODITIES})
    period_start: str
    period_end: str
    supplier: str | None = None
    consumption: float | None = None  # kWh (luce) o Smc (gas) fatturati
    kwh_f1: float | None = None
    kwh_f2: float | None = None
    kwh_f3: float | None = None
    mc: float | None = None
    coeff_c: float | None = None
    power_kw: float | None = None
    reading_type: str | None = field(default=None, metadata={"choices": ("effettiva", "stimata")})
    total_eur: float | None = None
    annual_consumption: float | None = None  # stampato in bolletta
    annual_f1: float | None = None
    annual_f2: float | None = None
    annual_f3: float | None = None
    annual_spend: float | None = None
    social_bonus_expires_on: str | None = None
    pdf_path: str | None = None
    id: int | None = None
    created_at: str | None = None

    def with_derived_consumption(self) -> Bill:
        """Completa `consumption` quando la bolletta riporta solo fasce o mc x C."""
        if self.consumption is not None:
            return self
        if self.commodity == "power":
            bands = [self.kwh_f1, self.kwh_f2, self.kwh_f3]
            if any(b is not None for b in bands):
                return replace(self, consumption=sum(b or 0 for b in bands))
        elif self.mc is not None and self.coeff_c is not None:
            return replace(self, consumption=round(self.mc * self.coeff_c, 2))
        return self


@dataclass(kw_only=True)
class Offer:
    commodity: str = field(metadata={"choices": COMMODITIES})
    supplier: str
    name: str
    price_type: str = field(metadata={"choices": ("fixed", "indexed")})
    price: float | None = None  # fisso: €/kWh o €/Smc
    price_f1: float | None = None  # fisso luce per fascia (se tutte e tre presenti)
    price_f2: float | None = None
    price_f3: float | None = None
    avg_price: float | None = None  # alternativa alla formula: prezzo medio di vendita
    spread: float | None = None  # indicizzato: €/kWh o €/Smc sopra PUN/PSV
    fixed_fee_month: float | None = None
    power_fee_kw_month: float | None = None
    one_off_discount: float | None = None  # sconti/bonus una tantum (€, primo anno)
    expires_on: str | None = None
    is_current: bool = False
    source: str | None = None
    zones: str | None = None  # se limitata: codici ISTAT separati da virgola (R08 regione, P038 provincia, C038008 comune)
    # componenti formula indicizzata luce
    loss_pct: float | None = None
    dispatching: float | None = None  # €/kWh
    capacity: float | None = None  # €/kWh
    dispatching_extra: bool = False  # dispacciamento/capacità fatturati a parte al costo regolato
    # componenti formula indicizzata gas
    gas_mgmt: float | None = None  # €/Smc
    pcs_adjustment: float | None = None  # €/Smc
    id: int | None = None
    created_at: str | None = None


SYSTEM_FIELDS = {"id", "created_at"}


def columns(cls) -> list[str]:
    return [f.name for f in dataclasses.fields(cls)]
