import pytest

from app.models import Bill
from app.services.power import power_advice


def bill(end="2026-06-30", **kw):
    return Bill(commodity="power", period_start=end[:8] + "01", period_end=end, power_kw=4.5, power_rate_kw_month=2.0, **kw)


def test_suggests_lower_level_and_saving():
    a = power_advice([bill(max_power_kw=2.5, annual_max_power_kw=2.9)])
    assert a.suggested == 3.0 and a.saving_year == pytest.approx(1.5 * 2.0 * 12)
    assert not a.partial and a.tight  # 2,9 è oltre il 90% di 3 kW


def test_no_margin_when_peak_close_to_contract():
    a = power_advice([bill(max_power_kw=3.0, annual_max_power_kw=4.4)])
    assert a.suggested is None and a.saving_year is None and a.peak == 4.4


def test_later_bill_can_raise_the_peak():
    older = bill("2026-06-30", max_power_kw=2.0, annual_max_power_kw=2.2)
    newer = bill("2026-07-31", max_power_kw=4.0)
    assert power_advice([older, newer]).suggested is None


def test_without_history_uses_months_seen_and_flags_partial():
    a = power_advice([bill("2026-05-31", max_power_kw=1.8), bill("2026-06-30", max_power_kw=2.1)])
    assert a.months == 2 and a.partial and a.suggested == 3.0


def test_no_data_no_advice():
    assert power_advice([]) is None
    assert power_advice([bill()]) is None  # nessun picco rilevato
    assert power_advice([Bill(commodity="power", period_start="2026-06-01", period_end="2026-06-30", max_power_kw=2.0)]) is None


def test_saving_unknown_without_rate():
    b = bill(max_power_kw=2.0, annual_max_power_kw=2.0)
    b.power_rate_kw_month = None
    a = power_advice([b])
    assert a.suggested == 3.0 and a.saving_year is None
