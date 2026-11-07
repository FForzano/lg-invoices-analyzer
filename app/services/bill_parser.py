"""Lettura a regole delle bollette PDF (nessun LLM, nessun costo, nessun dato in uscita).

Si appoggia sulle etichette standard ARERA ("Periodo fatturato", "Consumo totale
fatturato", "Consumo annuo aggiornato", "Spesa annua sostenuta"…). I campi trovati
vengono controllati tra loro; se mancano quelli essenziali il chiamante ripiega sull'LLM."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

REQUIRED = ("commodity", "period_start", "period_end", "consumption", "total_eur")

MONTHS = {
    m: i for i, m in enumerate(
        "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split(), 1
    )
}
NUM = r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)"


@dataclass
class ParseResult:
    fields: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def missing(self) -> list[str]:
        return [f for f in REQUIRED if f not in self.fields]

    @property
    def complete(self) -> bool:
        return not self.missing


def num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _search(pattern: str, text: str, flags: int = re.I):
    return re.search(pattern, text, flags)


def parse_bill_text(text: str) -> ParseResult:
    r = ParseResult()
    f = r.fields

    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), None)
    if first_line:
        f["supplier"] = first_line.title()

    if _search(r"Fornitura:\s*ENERGIA ELETTRICA", text):
        f["commodity"] = "power"
    elif _search(r"Fornitura:\s*GAS", text):
        f["commodity"] = "gas"

    _period(text, f)

    if m := _search(r"Consumo totale fatturato\s*\[(?:kWh|Smc)\]\s*" + NUM, text):
        f["consumption"] = num(m.group(1))
    if m := _search(r"Totale da pagare\s+" + NUM, text) or _search(r"TOTALE DA PAGARE\s*" + NUM + r"\s*€", text):
        f["total_eur"] = num(m.group(1))
    if m := _search(r"Consumi (effettivi|stimati)", text):
        f["reading_type"] = "effettiva" if m.group(1).lower() == "effettivi" else "stimata"
    if m := _search(r"Spesa annua sostenuta", text):
        before = text[: m.start()]
        if e := re.search(r"€\s*" + NUM + r"\s*$", before.rstrip()):
            f["annual_spend"] = num(e.group(1))
    if m := _search(r"Data di scadenza del bonus sociale\s+(\d{2})/(\d{2})/(\d{4})", text):
        f["social_bonus_expires_on"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    if f.get("commodity") == "power":
        _power(text, f, r)
    elif f.get("commodity") == "gas":
        _gas(text, f)
    return r


def _period(text: str, f: dict) -> None:
    month = "|".join(MONTHS)
    # "Periodo fatturato 1-30 GIUGNO 2026"
    if m := _search(rf"Periodo fatturato\s+(\d{{1,2}})\s*-\s*(\d{{1,2}})\s+({month})\s+(\d{{4}})", text):
        d1, d2, mon, y = int(m.group(1)), int(m.group(2)), MONTHS[m.group(3).lower()], int(m.group(4))
        f["period_start"], f["period_end"] = f"{y}-{mon:02d}-{d1:02d}", f"{y}-{mon:02d}-{d2:02d}"
    # "Periodo fatturato dal 01/06/2026 al 30/06/2026"
    elif m := _search(r"Periodo fatturato\s+dal\s+(\d{2})/(\d{2})/(\d{4})\s+al\s+(\d{2})/(\d{2})/(\d{4})", text):
        f["period_start"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        f["period_end"] = f"{m.group(6)}-{m.group(5)}-{m.group(4)}"


def _power(text: str, f: dict, r: ParseResult) -> None:
    if m := _search(NUM + r"\s*kW\s*Potenza Impegnata", text):
        f["power_kw"] = num(m.group(1))
    if m := _search(
        r"Consumo annuo aggiornato\s+F1:\s*" + NUM + r"\s*(?:kWh)?\s*F2:\s*" + NUM + r"\s*(?:kWh)?\s*F3:\s*" + NUM, text
    ):
        f["annual_f1"], f["annual_f2"], f["annual_f3"] = (num(g) for g in m.groups())
        f["annual_consumption"] = round(f["annual_f1"] + f["annual_f2"] + f["annual_f3"], 2)

    if m := _search(r"Livello massimo mensile di potenza prelevata:\s*" + NUM + r"\s*\[kW\]", text):
        f["max_power_kw"] = num(m.group(1))
    if m := _search(r"kW\s+per\s+\d+\s+mesi\s+x\s+" + NUM + r"\s*€/kW/mese", text):
        f["power_rate_kw_month"] = num(m.group(1))
    # storico: riga dei mesi e riga dei 12 valori (1 decimale), incollati tra loro: "3,42,3 2,6kW 2,8 ..."
    if m := _search(r"Livello massimo della potenza prelevata[^\n]*\n[^\n]*\n([^\n]*)", text):
        levels = re.findall(r"\d{1,2},\d", m.group(1))
        if len(levels) == 12:
            f["annual_max_power_kw"] = max(num(v) for v in levels)

    # Tabella "Riepilogo consumi": nel testo estratto potenza max (1 decimale) e kWh (2 decimali)
    # sono incollati, es. "2,148,01F1Consumi effettivi" = potenza 2,1 + 48,01 kWh in F1.
    bands = {}
    for m in re.finditer(r"(\d{1,2},\d)(\d{1,4},\d{2})F([123])Consumi", text):
        bands.setdefault(int(m.group(3)), num(m.group(2)))
    if len(bands) == 3:
        if "consumption" in f and abs(sum(bands.values()) - f["consumption"]) > 0.05:
            r.warnings.append("Le fasce non tornano con il consumo totale: ignorate.")
        else:
            f["kwh_f1"], f["kwh_f2"], f["kwh_f3"] = bands[1], bands[2], bands[3]


def _gas(text: str, f: dict) -> None:
    if m := _search(r"Consumo annuo aggiornato\s+" + NUM + r"\s*Smc", text):
        f["annual_consumption"] = num(m.group(1))
    if m := _search(r"(\d,\d{6})\s*Coefficiente C", text):
        f["coeff_c"] = num(m.group(1))
        if "consumption" in f:
            f["mc"] = round(f["consumption"] / f["coeff_c"], 2)


# --- offerta attuale ricavata dalla bolletta -------------------------------------------------

# Quota di consumi in ore di picco Terna quando la bolletta non la rende leggibile
PEAK_SHARE_DEFAULT = 0.06


@dataclass
class OfferTerms:
    offer: dict  # campi di `Offer` (senza id/is_current/source)
    pun: float | None = None  # PUN medio del mese (€/kWh), per le ipotesi del confronto
    psv: float | None = None  # PSV del mese (€/Smc)


def parse_offer_terms(text: str, commodity: str) -> OfferTerms | None:
    """Condizioni dell'offerta stampate nel «Box dell'offerta». None se non si riconoscono con certezza."""
    name = _search(r"^(.+?)Nome dell.offerta commerciale", text, re.I | re.M)
    fee = _search(r"di cui spesa per vendita[^\n]*?" + NUM + r"\s*€/mese", text)
    if not (name and fee):
        return None
    unit = "kWh" if commodity == "power" else "Smc"
    terms = {"commodity": commodity, "name": name.group(1).strip(), "fixed_fee_month": num(fee.group(1))}
    if first := next((ln.strip() for ln in text.splitlines() if ln.strip()), None):
        terms["supplier"] = first.title()
    if m := _search(r"economiche applicate nell.offerta\s+(\d{2})/(\d{2})/(\d{4})", text):
        terms["expires_on"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    def monthly(label: str) -> float | None:
        m = _search(label + r"\s+\d{2}/\d{4}:\s*" + NUM, text)
        return num(m.group(1)) if m else None

    if _search(r"Offerta a prezzo fisso", text):
        m = _search(r"di cui spesa per vendita[^\n]*?(\d,\d{4,6})\s*(?:€|Euro)/" + unit, text)
        if not m:
            return None
        return OfferTerms({**terms, "price_type": "fixed", "price": num(m.group(1))})
    if not _search(r"Offerta a prezzo (?:variabile|indicizzato)", text):
        return None

    spread = monthly(r"\nSpread")
    if spread is None:
        return None
    terms |= {"price_type": "indexed", "spread": spread}
    if commodity == "gas":
        terms["gas_mgmt"] = monthly(r"Corrispettivo di gestione variabile")  # compare due volte: vale la prima
        return OfferTerms(terms, psv=monthly(r"PSV\w*(?:,\w+)?"))

    loss = monthly(r"Perdite di Rete")
    if loss is None:
        return None
    terms |= {"loss_pct": loss, "dispatching": monthly(r"\nDispacciamento"), "capacity": _capacity(text)}
    pun = _search(r"PUN\s+\d{2}/\d{4}:\s*F1\s*" + NUM + r"\s*F2\s*" + NUM + r"\s*F3\s*" + NUM, text)
    avg_pun = None
    if pun:
        from .consumption import DEFAULT_BAND_SPLIT  # import locale: evita dipendenze circolari tra servizi
        avg_pun = sum(num(g) * w for g, w in zip(pun.groups(), DEFAULT_BAND_SPLIT))
    return OfferTerms(terms, pun=avg_pun)


def _capacity(text: str) -> float | None:
    """Oneri di capacità medi €/kWh: prezzo orario picco/fuori picco pesato sui kWh effettivi."""
    peak = _search(r"ore picco Terna\s+\d{2}/\d{4}:\s*" + NUM, text)
    off = _search(r"fuori picco Terna\s+\d{2}/\d{4}:\s*" + NUM, text)
    if not (peak and off):
        return None
    p_peak, p_off = num(peak.group(1)), num(off.group(1))
    # righe di dettaglio con le celle incollate: IVA(2 cifre) imponibile kWh prezzo
    q_peak = _search(r"€/kWh\s*\d{2}\d+,\d{2}(\d+,\d{2})" + re.escape(peak.group(1)), text)
    q_off = _search(r"€/kWh\s*\d{2}\d+,\d{2}(\d+,\d{2})" + re.escape(off.group(1)), text)
    share = PEAK_SHARE_DEFAULT
    if q_peak and q_off:
        kwh_peak, kwh_off = num(q_peak.group(1)), num(q_off.group(1))
        share = kwh_peak / (kwh_peak + kwh_off)
    return p_peak * share + p_off * (1 - share)
