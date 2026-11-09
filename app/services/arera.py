"""Import delle offerte del mercato libero dagli open data del Portale Offerte (Acquirente Unico / ARERA).

I file XML (luce e gas, ~15-20 MB) sono pubblici e senza autenticazione; il nome contiene la data
(`PO_Offerte_E_MLIBERO_AAAAMMGG.xml`), quindi l'URL corrente si legge dalla pagina open data.
Il manuale ufficiale elenca solo i valori ammessi dei codici, non il loro significato: la
decodifica qui sotto è dedotta dai dati e confermata dagli esempi del manuale (vedi CODES)."""
from __future__ import annotations

import re
from dataclasses import replace
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
COND_LIMITING = "01"  # LIMITANTE: condizione che restringe chi può sottoscrivere (pagamento, nuovi clienti...)
DURATION_NONE, DURATION_OTHER = -1, 99  # DURATA in mesi: -1 indeterminata, 99 altro
# frase del venditore su cosa succede a fine periodo ("Trascorsi 24 mesi ..."): solo testo da mostrare, mai nei calcoli
AFTER_TERM = re.compile(
    r"\b(trascors\w+|decors\w+|al termine|alla scadenza|scadut\w+)\b[^.]{0,60}\b(\d+|dodici|ventiquattro|trentasei)\b[^.]{0,20}\b(mesi|anni?)\b",
    re.I,
)
MAX_TEXT = 500
SOURCE_PREFIX = "arera:"
UNPAIRED = SOURCE_PREFIX + "?"  # offerta luce+gas non ancora abbinata alla sua metà (vedi `pair_dual_fuel`)
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
        offers, unpaired = pair_dual_fuel(offers)
        if unpaired:
            skipped["luce+gas non abbinabili"] += unpaired
        return offers, skipped
    except OSError as e:
        raise AreraError(f"Download non riuscito: {e}") from e


def parse_offers(source: IO[bytes] | str | Path, commodity: str) -> tuple[list[Offer], Counter]:
    """Interpreta il XML (file o percorso). Tiene le offerte domestiche; quelle luce+gas escono con
    `dual_with` provvisorio, da risolvere con `pair_dual_fuel` dopo aver letto entrambi i file."""
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
    single = _t(el, "DettaglioOfferta/OFFERTA_SINGOLA")
    if _t(el, "DettaglioOfferta/TIPO_CLIENTE") != CLIENT_DOMESTIC or single not in ("SI", "NO"):
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
    conditions, after_term = _condition_texts(el)
    common = dict(
        dispatching_extra=passthrough,
        commodity=commodity,
        supplier=_supplier(el),
        name=_t(el, "DettaglioOfferta/NOME_OFFERTA") or "(senza nome)",
        fixed_fee_month=round(yearly_fee / 12, 4),
        expires_on=_expiry(_t(el, "ValiditaOfferta/DATA_FINE")),
        zones=_zones(el.find(NS + "ZoneOfferta")),
        offer_url=_web_url(_t(el, "DettaglioOfferta/Contatti/URL_OFFERTA")),
        duration_months=_duration(_t(el, "DettaglioOfferta/DURATA")),
        conditions=conditions,
        after_term=after_term,
        source=SOURCE_PREFIX + (_t(el, "IdentificativiOfferta/COD_OFFERTA") or "?"),
        dual_with=None if single == "SI" else _dual_link(el),
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


def _dual_link(el: ET.Element) -> str:
    """Offerta luce+gas: l'altra metà dichiarata dal venditore (OffertaDual), se c'è."""
    for tag in ("OFFERTE_CONGIUNTE_EE", "OFFERTE_CONGIUNTE_GAS"):
        if code := el.findtext(f"{NS}OffertaDual/{NS}{tag}"):
            return SOURCE_PREFIX + code
    return UNPAIRED


def pair_dual_fuel(offers: list[Offer]) -> tuple[list[Offer], int]:
    """Abbina le metà luce e gas delle offerte luce+gas. Il venditore dichiara il legame solo per
    alcune: per le altre vale lo stesso fornitore e lo stesso nome a meno di «luce»/«gas», se univoco.
    Restituisce le offerte con le sole metà abbinate (dual_with = fonte dell'altra) e quante ne sono state scartate."""
    duals = [o for o in offers if o.dual_with]
    by_source = {o.source: o for o in duals}
    partner: dict[str, str] = {}

    def link(a: Offer, b: Offer) -> None:
        if a.commodity != b.commodity and a.source not in partner and b.source not in partner:
            partner[a.source], partner[b.source] = b.source, a.source

    for o in duals:  # legami dichiarati
        if (other := by_source.get(o.dual_with)) is not None:
            link(o, other)
    groups: dict[tuple[str, str], list[Offer]] = {}
    for o in duals:  # per nome
        if o.source not in partner:
            groups.setdefault((o.supplier, re.sub(r"luce|gas", "*", o.name.lower())), []).append(o)
    for group in groups.values():
        power = [o for o in group if o.commodity == "power"]
        gas = [o for o in group if o.commodity == "gas"]
        if len(power) == len(gas) == 1:
            link(power[0], gas[0])

    kept = [replace(o, dual_with=partner[o.source]) if o.dual_with else o for o in offers if not o.dual_with or o.source in partner]
    return kept, len(offers) - len(kept)


def _duration(raw: str | None) -> int | None:
    try:
        months = int(raw or "")
    except ValueError:
        return None
    return months if 0 < months < DURATION_OTHER else None


def _condition_texts(el: ET.Element) -> tuple[str | None, str | None]:
    """(condizioni limitanti, frase sul dopo-periodo) come testo del venditore, accorciato; solo da mostrare."""
    limiting: list[str] = []
    after: list[str] = []
    for c in el.findall(NS + "CondizioniContrattuali"):
        text = " ".join((c.findtext(NS + "DESCRIZIONE") or "").split())
        if not text:
            continue
        text = text if len(text) <= MAX_TEXT else text[:MAX_TEXT].rstrip() + "…"
        if AFTER_TERM.search(text):
            after.append(text)
        elif c.findtext(NS + "LIMITANTE") == COND_LIMITING and text not in limiting:
            limiting.append(text)
    return "\n".join(limiting[:6]) or None, "\n".join(after[:2]) or None


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


def _web_url(raw: str | None) -> str | None:
    """Indirizzo dichiarato dal venditore (contenuto non fidato): solo http/https con un host, altrimenti nessun link."""
    raw = (raw or "").strip()
    if not raw or len(raw) > 500 or any(c.isspace() or ord(c) < 32 for c in raw):
        return None
    parsed = urlparse(raw if "//" in raw else "https://" + raw)
    return parsed.geturl() if parsed.scheme in ("http", "https") and parsed.hostname and "." in parsed.hostname else None


def _supplier(el: ET.Element) -> str:
    """Il file non riporta la ragione sociale: uso il dominio del sito del venditore, altrimenti la P.IVA."""
    site = _t(el, "DettaglioOfferta/Contatti/URL_SITO_VENDITORE")
    if site:
        host = urlparse(site if "//" in site else "//" + site).hostname
        if host:
            return host.removeprefix("www.")
    return f"P.IVA {_t(el, 'IdentificativiOfferta/PIVA_UTENTE')}"
