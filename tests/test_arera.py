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
    assert unit_price(idx, A) == pytest.approx((0.12 + 0.02 + 0.0088) * 1.10)

    fix = by["arera:FIX1"]
    assert fix.price_type == "fixed" and fix.price == 0.13 and fix.supplier == "P.IVA 111"
    assert fix.dispatching_extra and not idx.dispatching_extra
    assert unit_price(fix, Assumptions(0.12, 0.4, 3.0, dispatching_extra=0.019)) == pytest.approx(0.149)


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


def test_replace_imported_keeps_manual_and_current(client):
    from app import create_app
    app = client.application
    offers, _ = arera.parse_offers(FIX / "offers_sample.xml", "power")
    with app.app_context():
        assert db.replace_imported_offers(offers, arera.SOURCE_PREFIX) == 4
        current = next(o for o in db.list_offers() if o.source == "arera:FIX1")
        current.is_current = True
        db.save_offer(current, current.id)
        assert db.replace_imported_offers(offers, arera.SOURCE_PREFIX) == 3  # l'attuale non viene duplicata
        assert len(db.list_offers()) == 4


def test_dual_fuel_link_declared_by_seller_and_pairing():
    offers, _ = arera.parse_offers(FIX / "offers_sample.xml", "power")
    dual = next(o for o in offers if o.source == "arera:DUAL1")
    assert dual.dual_with == "arera:DUAL1G"
    assert all(o.dual_with is None for o in offers if o is not dual)  # le singole non sono toccate


def _half(commodity, name, code, link=arera.UNPAIRED, supplier="s.it"):
    from app.models import Offer
    return Offer(commodity=commodity, supplier=supplier, name=name, price_type="fixed", price=0.1,
                 source=arera.SOURCE_PREFIX + code, dual_with=link)


def test_pair_dual_fuel_by_declared_link_by_name_and_drops_ambiguous():
    single = _half("power", "Singola", "S1", link=None)
    declared = [_half("power", "A luce", "A1", "arera:A2"), _half("gas", "Altro nome", "A2", "arera:A1")]
    by_name = [_half("power", "Casa Luce", "B1"), _half("gas", "Casa Gas", "B2")]
    ambiguous = [_half("power", "Fix luce", "C1"), _half("power", "Fix luce", "C2"), _half("gas", "Fix gas", "C3")]
    other_supplier = [_half("power", "Casa Luce", "D1", supplier="x.it")]
    kept, dropped = arera.pair_dual_fuel([single, *declared, *by_name, *ambiguous, *other_supplier])
    assert {o.source for o in kept} == {"arera:S1", "arera:A1", "arera:A2", "arera:B1", "arera:B2"}
    assert dropped == 4
    partner = {o.source: o.dual_with for o in kept}
    assert partner["arera:B1"] == "arera:B2" and partner["arera:B2"] == "arera:B1" and partner["arera:S1"] is None
