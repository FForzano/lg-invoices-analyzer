from pathlib import Path

import pytest

from app import db
from app.services import arera
from app.services.pricing import Assumptions, unit_price

FIX = Path(__file__).parent / "fixtures"
A = Assumptions(pun=0.12, psv=0.40, default_power_kw=3.0)


def test_parse_sample():
    offers, skipped = arera.parse_offers(FIX / "offers_sample.xml", "power")
    by = {o.source: o for o in offers}
    assert set(by) == {"arera:IDX1", "arera:FIX1", "arera:ZONE1", "arera:DUAL1"}  # business scartata in silenzio, errore di unità segnalato
    assert dict(skipped) == {"prezzo fuori scala": 1}

    idx = by["arera:IDX1"]
    assert by["arera:ZONE1"].zones == "R02" and idx.zones is None
    assert idx.price_type == "indexed" and idx.spread == pytest.approx(0.02)
    assert idx.fixed_fee_month == 12.0 and idx.expires_on == "2027-01-10"
    assert idx.dispatching == pytest.approx(0.0088) and idx.supplier == "esempio.it"
    assert idx.offer_url == "https://www.esempio.it/offerte/indicizzata" and by["arera:FIX1"].offer_url is None
    assert unit_price(idx, A) == pytest.approx((0.12 + 0.02 + 0.0088) * 1.10)

    fix = by["arera:FIX1"]
    assert fix.price_type == "fixed" and fix.price == 0.13 and fix.supplier == "P.IVA 111"
    assert fix.dispatching_extra and not idx.dispatching_extra
    assert unit_price(fix, Assumptions(0.12, 0.4, 3.0, dispatching_extra=0.019)) == pytest.approx(0.149)

    # durata e testi del venditore: solo da mostrare; le condizioni non limitanti e senza dopo-periodo non entrano
    assert fix.duration_months == 24 and idx.duration_months is None
    assert fix.conditions == "Valida solo con addebito su conto."
    assert fix.after_term.startswith("Trascorsi 24 mesi") and idx.conditions is None and idx.after_term is None
    assert fix.exit_terms == "Onere di recesso anticipato di 2,00 € per ogni mese residuo." and idx.exit_terms is None
    assert fix.bonus_terms == "Bonus benvenuto: Bonus una tantum di 30 € in prima fattura." and idx.bonus_terms is None


def test_discover_urls_only_trusts_expected_host():
    html = (
        '<a href="/portaleOfferte/resources/opendata/csv/offerteML/2026_11/PO_Offerte_E_MLIBERO_20261107.xml">e</a>'
        '<a href="/portaleOfferte/resources/opendata/csv/offerteML/2026_11/PO_Offerte_G_MLIBERO_20261107.xml">g</a>'
    )
    urls = arera.discover_urls(html)
    assert urls["power"].startswith("https://www.ilportaleofferte.it/") and urls["gas"].endswith("G_MLIBERO_20261107.xml")
    evil = html.replace('href="/portale', 'href="https://evil.example/portale', 1)
    with pytest.raises(arera.AreraError):
        arera.discover_urls(evil)


def test_replace_imported_keeps_profile_copies_and_catalog_stays_shared(client):
    app = client.application
    offers, _ = arera.parse_offers(FIX / "offers_sample.xml", "power")
    with app.app_context():
        assert db.replace_imported_offers(offers, arera.SOURCE_PREFIX) == 4
        shared = next(o for o in db.list_offers() if o.source == "arera:FIX1")
        shared.is_current = True
        db.save_offer(shared, shared.id)  # «attuale» = copia del profilo, il catalogo non cambia
        assert db.replace_imported_offers(offers, arera.SOURCE_PREFIX) == 4
        listed = db.list_offers()
        assert len(listed) == 4  # la copia del profilo nasconde l'originale condiviso, nessun doppione
        assert [o.profile_id for o in listed if o.source == "arera:FIX1"] == [db.profile_id()] and listed
