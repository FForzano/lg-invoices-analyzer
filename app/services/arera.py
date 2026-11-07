"""Import delle offerte del mercato libero dagli open data del Portale Offerte (Acquirente Unico / ARERA).

I file XML (luce e gas, ~15-20 MB) sono pubblici e senza autenticazione; il nome contiene la data
(`PO_Offerte_E_MLIBERO_AAAAMMGG.xml`), quindi l'URL corrente si legge dalla pagina open data.
Il manuale ufficiale elenca solo i valori ammessi dei codici, non il loro significato: la
decodifica qui sotto è dedotta dai dati e confermata dagli esempi del manuale (vedi CODES)."""
from __future__ import annotations

import re
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path
from typing import IO
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

from ..models import Offer
from .consumption import DEFAULT_BAND_SPLIT
from .seasonality import index_factors_from_csv, recent_index_levels

HOST = "www.ilportaleofferte.it"
OPEN_DATA_PAGE = f"https://{HOST}/portaleOfferte/it/open-data.page"
NS = "{http://www.acquirenteunico.it/schemas/SII_AU/OffertaRetail/01}"

# Significato dei codici (dedotto dai dati reali)
CLIENT_DOMESTIC = "01"  # TIPO_CLIENTE
OFFER_FIXED, OFFER_INDEXED = "01", "02"  # TIPO_OFFERTA (02 sempre con indice PUN/PSV)
DISP_PASSTHROUGH = "14"  # TIPO_DISPACCIAMENTO "CdispD": dispacciamento al costo regolato, fuori dal prezzo
FASCE_SINGLE, FASCE_F1F2F3 = "01", "03"  # TIPOLOGIA_FASCE
UM_EUR_YEAR, UM_EUR_KWH, UM_EUR_SMC = "01", "03", "04"  # UNITA_MISURA; gli altri (02, 05) non sono gestiti
SOURCE_PREFIX = "arera:"
MAX_ENERGY_PRICE = {"power": 1.5, "gas": 5.0}  # oltre è un errore di unità del venditore


class AreraError(Exception):
    pass


def discover_urls(html: str) -> dict[str, str]:
    """{'power': url, 'gas': url} letti dalla pagina open data (contenuto non fidato: solo https e host atteso)."""
    urls = {}
    for path, kind in re.findall(r'href="([^"]*PO_Offerte_([EG])_MLIBERO_\d{8}\.xml)"', html):
        url = urljoin(OPEN_DATA_PAGE, path)
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc == HOST:
            urls["power" if kind == "E" else "gas"] = url
    if len(urls) != 2:
        raise AreraError("Link ai file open data non trovati: la pagina del Portale Offerte è cambiata?")
    return urls


def fetch_index_history() -> tuple[dict[str, tuple[float, ...]], dict[str, float | str]]:
    """(fattori stagionali, livelli recenti) di PUN/PSV dal CSV dei prezzi storici linkato nella pagina open data."""
    try:
        with _get(OPEN_DATA_PAGE) as r:
            html = r.read().decode("utf-8", errors="replace")
        m = re.search(r'href="(/portaleOfferte/resources/cms/documents/[0-9a-f]+\.csv)"', html)
        if not m:
            raise AreraError("CSV dei prezzi storici non trovato nella pagina open data")
        with _get(urljoin(OPEN_DATA_PAGE, m.group(1))) as r:
            text = r.read().decode("latin-1")
        factors = index_factors_from_csv(text)
        return factors, recent_index_levels(text, factors)
    except (OSError, ValueError) as e:
        raise AreraError(f"Prezzi storici non disponibili: {e}") from e


def _get(url: str, timeout: int = 60):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lg-invoices-analyzer"}), timeout=timeout)


def fetch_offers() -> tuple[list[Offer], Counter]:
    """Scarica e interpreta i file di luce e gas. Restituisce (offerte, motivi di scarto)."""
    try:
        with _get(OPEN_DATA_PAGE) as r:
            urls = discover_urls(r.read().decode("utf-8", errors="replace"))
        offers: list[Offer] = []
        skipped: Counter = Counter()
        for commodity, url in urls.items():
            with tempfile.TemporaryFile() as tmp, _get(url, timeout=120) as r:
                while chunk := r.read(1 << 20):
                    tmp.write(chunk)
                tmp.seek(0)
                found, why = parse_offers(tmp, commodity)
            offers += found
            skipped += why
        return offers, skipped
    except OSError as e:
        raise AreraError(f"Download non riuscito: {e}") from e


def parse_offers(source: IO[bytes] | str | Path, commodity: str) -> tuple[list[Offer], Counter]:
    """Interpreta il XML (file o percorso). Tiene solo offerte domestiche singole (non dual fuel)."""
    offers: list[Offer] = []
    skipped: Counter = Counter()
    for _, el in ET.iterparse(source):
        if el.tag != NS + "offerta":
            continue
        result = _convert(el, commodity)
        if isinstance(result, Offer):
            offers.append(result)
        elif result:
            skipped[result] += 1
        el.clear()
    return offers, skipped


def _t(el: ET.Element, path: str) -> str | None:
    return el.findtext("/".join(NS + p for p in path.split("/")))


def _convert(el: ET.Element, commodity: str) -> Offer | str | None:
    """Offerta, oppure il motivo dello scarto (None = fuori perimetro, non conteggiata)."""
    if _t(el, "DettaglioOfferta/TIPO_CLIENTE") != CLIENT_DOMESTIC or _t(el, "DettaglioOfferta/OFFERTA_SINGOLA") != "SI":
        return None
    kind = _t(el, "DettaglioOfferta/TIPO_OFFERTA")
    if kind not in (OFFER_FIXED, OFFER_INDEXED):
        return "tipo offerta non gestito"
    fasce = _t(el, "TipoPrezzo/TIPOLOGIA_FASCE") if commodity == "power" else None
    if fasce not in (None, FASCE_SINGLE, FASCE_F1F2F3):
        return "fasce orarie non gestite"

    energy_um = UM_EUR_KWH if commodity == "power" else UM_EUR_SMC
    bands = [0.0, 0.0, 0.0]
    yearly_fee = 0.0
    for comp in el.findall(NS + "ComponenteImpresa"):
        for ip in comp.findall(NS + "IntervalloPrezzi"):
            um, raw = ip.findtext(NS + "UNITA_MISURA"), ip.findtext(NS + "PREZZO")
            if raw is None:
                continue
            price = float(raw)
            if um == UM_EUR_YEAR:
                yearly_fee += price
            elif um == energy_um:
                band = ip.findtext(NS + "FASCIA_COMPONENTE")
                if fasce == FASCE_F1F2F3 and band in ("01", "02", "03"):
                    bands[int(band) - 1] += price
                elif fasce == FASCE_F1F2F3 and band is not None:
                    return "fasce orarie non gestite"
                else:  # monoraria o componente valida per ogni fascia
                    bands = [b + price for b in bands]
            else:
                return "unità di misura non gestita"

    if max(bands) > MAX_ENERGY_PRICE[commodity]:
        return "prezzo fuori scala"

    passthrough = commodity == "power" and any(
        d.findtext(NS + "TIPO_DISPACCIAMENTO") == DISP_PASSTHROUGH for d in el.findall(NS + "Dispacciamento")
    )
    common = dict(
        dispatching_extra=passthrough,
        commodity=commodity,
        supplier=_supplier(el),
        name=_t(el, "DettaglioOfferta/NOME_OFFERTA") or "(senza nome)",
        fixed_fee_month=round(yearly_fee / 12, 4),
        expires_on=_expiry(_t(el, "ValiditaOfferta/DATA_FINE")),
        zones=_zones(el.find(NS + "ZoneOfferta")),
        source=SOURCE_PREFIX + (_t(el, "IdentificativiOfferta/COD_OFFERTA") or "?"),
    )
    if kind == OFFER_FIXED:
        if not any(bands):
            return "prezzo mancante"
        uniform = len({round(b, 8) for b in bands}) == 1
        return Offer(
            price_type="fixed", price=bands[0] if uniform else None,
            price_f1=None if uniform else bands[0], price_f2=None if uniform else bands[1],
            price_f3=None if uniform else bands[2], **common,
        )

    spread = sum(b * w for b, w in zip(bands, DEFAULT_BAND_SPLIT))  # PUN/PSV unico nelle ipotesi: spread medio pesato
    dispatching = sum(float(d.text) for d in el.iter(NS + "VALORE_DISP") if d.text) if commodity == "power" else None
    return Offer(price_type="indexed", spread=spread, dispatching=dispatching or None, **common)


def _expiry(raw: str | None) -> str | None:
    """'10/01/2027_23:59:59' -> '2027-01-10'."""
    if m := re.match(r"(\d{2})/(\d{2})/(\d{4})", raw or ""):
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def _zones(el: ET.Element | None) -> str | None:
    """Zone di validità come token 'R08,P038,C038008'; None se l'offerta vale ovunque."""
    if el is None:
        return None
    tokens = [f"{prefix}{e.text}" for tag, prefix in (("REGIONE", "R"), ("PROVINCIA", "P"), ("COMUNE", "C"))
              for e in el.findall(NS + tag) if e.text]
    return ",".join(tokens) or None


def _supplier(el: ET.Element) -> str:
    """Il file non riporta la ragione sociale: uso il dominio del sito del venditore, altrimenti la P.IVA."""
    site = _t(el, "DettaglioOfferta/Contatti/URL_SITO_VENDITORE")
    if site:
        host = urlparse(site if "//" in site else "//" + site).hostname
        if host:
            return host.removeprefix("www.")
    return f"P.IVA {_t(el, 'IdentificativiOfferta/PIVA_UTENTE')}"
