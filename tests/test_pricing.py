from datetime import date

import pytest

from app.models import Offer
from app.services.consumption import Consumption
from app.services.pricing import Assumptions, Location, available_in, compare, estimate, unit_price

A = Assumptions(pun=0.12, psv=0.40, default_power_kw=3.0)
C = Consumption(total=2000, bands=(500, 500, 1000), power_kw=4.5, source="test")


def offer(**kw):
    base = dict(commodity="power", supplier="S", name="N", price_type="fixed")
    return Offer(**{**base, **kw})


def test_indexed_power_formula_from_bills():
    # (PUN + spread + dispacciamento + capacità) * (1 + perdite), come stampato in bolletta
    o = offer(price_type="indexed", spread=0.025, loss_pct=10, dispatching=0.01, capacity=0.002)
    assert unit_price(o, A) == pytest.approx((0.12 + 0.025 + 0.01 + 0.002) * 1.10)


def test_indexed_gas_formula():
    o = offer(commodity="gas", price_type="indexed", spread=0.165, gas_mgmt=0.05, pcs_adjustment=0.01)
    assert unit_price(o, A) == pytest.approx(0.40 + 0.165 + 0.05 + 0.01)


def test_avg_price_overrides_formula():
    assert unit_price(offer(price_type="indexed", spread=1, avg_price=0.2), A) == 0.2


def test_fixed_bands_used_only_when_all_present():
    assert unit_price(offer(price=0.15, price_f1=0.1, price_f2=0.2), A, band=0) == 0.15
    assert unit_price(offer(price_f1=0.1, price_f2=0.2, price_f3=0.3), A, band=2) == 0.3


def test_missing_price_raises():
    with pytest.raises(ValueError):
        unit_price(offer(), A)


def test_estimate_power_totals():
    e = estimate(offer(price=0.15, fixed_fee_month=10, power_fee_kw_month=1, one_off_discount=50), C, A)
    assert e.energy == pytest.approx(300)
    assert e.fixed_fee == 120
    assert e.power_fee == pytest.approx(4.5 * 12)
    assert e.total == pytest.approx(300 + 120 + 54 - 50)


def test_default_band_split_when_no_bands():
    c = Consumption(total=1000, bands=None, power_kw=None, source="")
    e = estimate(offer(price_f1=0.1, price_f2=0.2, price_f3=0.3), c, A)
    assert e.energy == pytest.approx(330 * 0.1 + 300 * 0.2 + 370 * 0.3)


def test_compare_ranks_and_excludes_expired():
    current = offer(id=1, price=0.20, is_current=True)
    cheap = offer(id=2, price=0.10)
    expired = offer(id=3, price=0.01, expires_on="2020-01-01")
    ranked, skipped = compare([current, cheap, expired], C, A, date(2026, 11, 7))
    assert [r.offer.id for r in ranked] == [2, 1]
    assert ranked[0].saving == pytest.approx(200)


def test_compare_without_current_has_no_saving():
    ranked, _ = compare([offer(id=1, price=0.1)], C, A, date(2026, 11, 7))
    assert ranked[0].saving is None


def test_missing_loss_uses_assumption_and_bad_offers_are_skipped():
    o = offer(price_type="indexed", spread=0.02)
    assert unit_price(o, Assumptions(0.12, 0.4, 3.0, loss_pct=0)) == pytest.approx(0.14)
    assert unit_price(o, Assumptions(0.12, 0.4, 3.0, loss_pct=10)) == pytest.approx(0.154)
    ranked, skipped = compare([offer(id=1, price=0.1), offer(id=2)], C, A, date(2026, 11, 7))
    assert len(ranked) == 1 and len(skipped) == 1


def test_dispatching_extra_added_only_when_flagged():
    a = Assumptions(0.12, 0.4, 3.0, dispatching_extra=0.02)
    assert unit_price(offer(price=0.10, dispatching_extra=True), a) == pytest.approx(0.12)
    assert unit_price(offer(price=0.10), a) == pytest.approx(0.10)
    assert unit_price(offer(price=0.10, avg_price=0.15, dispatching_extra=True), a) == 0.15


def test_zone_restricted_offers_need_matching_location():
    aosta = offer(id=2, price=0.01, zones="R02")
    ferrara = offer(id=3, price=0.02, zones="P038,P004")
    anywhere = offer(id=4, price=0.03)
    loc = Location(region="08", province="038", comune="038008")
    assert [available_in(o, loc) for o in (aosta, ferrara, anywhere)] == [False, True, True]
    assert available_in(offer(zones="C038008"), loc)
    assert not available_in(aosta, Location())  # località ignota: le offerte limitate restano fuori
    ranked, _ = compare([aosta, ferrara, anywhere], C, A, date(2026, 11, 7), loc)
    assert [r.offer.id for r in ranked] == [3, 4]
    current_elsewhere = offer(id=5, price=0.5, zones="R02", is_current=True)
    assert len(compare([current_elsewhere], C, A, date(2026, 11, 7), loc)[0]) == 1


def test_bundles_pair_halves_and_compute_saving_against_both_current_offers():
    from app.services.pricing import pair_bundles
    from app.services.verdict import make_dual_verdict

    cur_p = offer(id=1, price=0.20, is_current=True, source="bolletta:1")
    cur_g = offer(id=2, commodity="gas", price=1.0, is_current=True, source="bolletta:2")
    half_p = offer(id=3, price=0.10, source="arera:P", dual_with="arera:G")
    half_g = offer(id=4, commodity="gas", price=0.5, source="arera:G", dual_with="arera:P")
    orphan = offer(id=5, price=0.05, source="arera:X", dual_with="arera:MISSING")
    c_gas = Consumption(total=500, bands=None, power_kw=None, source="test")
    rp, _ = compare([cur_p, half_p, orphan], C, A, date(2026, 11, 1))
    rg, _ = compare([cur_g, half_g], c_gas, A, date(2026, 11, 1))
    bundles = pair_bundles(rp, rg)
    assert len(bundles) == 1  # l'orfana non ha la sua metà
    b = bundles[0]
    assert b.total == pytest.approx(2000 * 0.10 + 500 * 0.5)
    assert b.saving == pytest.approx((2000 * 0.20 + 500 * 1.0) - b.total)
    v = make_dual_verdict(bundles, None, None)
    assert v.worthwhile and v.separate_saving == 0 and v.beats_separate
    assert make_dual_verdict([], None, None) is None


def test_bundle_without_current_offers_has_no_saving():
    from app.services.pricing import pair_bundles
    from app.services.verdict import make_dual_verdict

    half_p = offer(id=3, price=0.10, source="arera:P", dual_with="arera:G")
    half_g = offer(id=4, commodity="gas", price=0.5, source="arera:G", dual_with="arera:P")
    rp, _ = compare([half_p], C, A, date(2026, 11, 1))
    rg, _ = compare([half_g], Consumption(total=500, bands=None, power_kw=None, source="t"), A, date(2026, 11, 1))
    bundles = pair_bundles(rp, rg)
    assert bundles[0].saving is None and make_dual_verdict(bundles, None, None) is None
