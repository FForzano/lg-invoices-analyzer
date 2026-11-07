import pytest

from app.models import Bill
from app.services.consumption import annual_consumption
from app.services.history import history
from app.services.seasonality import consumption_profile, share_of_year
from datetime import date


def bill(start, end, **kw):
    return Bill(commodity="power", period_start=start, period_end=end, **kw)


def test_prefers_printed_annual():
    b = bill("2026-06-01", "2026-06-30", consumption=260, annual_consumption=2155,
             annual_f1=432, annual_f2=510, annual_f3=1214, power_kw=4.5)
    c = annual_consumption([b])
    assert c.total == 2155 and c.bands == (432, 510, 1214) and c.power_kw == 4.5


def test_projects_when_no_annual():
    bills = [bill("2026-05-01", "2026-05-31", consumption=100), bill("2026-06-01", "2026-06-30", consumption=100)]
    c = annual_consumption(bills)
    covered = share_of_year(consumption_profile("power"), date(2026, 5, 1), date(2026, 6, 30))
    assert c.total == pytest.approx(200 / covered)
    assert c.bands is None and c.partial and c.days_covered == 61


def test_none_without_bills():
    assert annual_consumption([]) is None


def test_derived_consumption():
    assert bill("2026-06-01", "2026-06-30", kwh_f1=1, kwh_f2=2, kwh_f3=3).with_derived_consumption().consumption == 6
    gas = Bill(commodity="gas", period_start="2026-06-01", period_end="2026-06-30", mc=10, coeff_c=1.018672)
    assert gas.with_derived_consumption().consumption == pytest.approx(10.19)


def test_history_yoy():
    rows = history([
        bill("2025-06-01", "2025-06-30", consumption=200, total_eur=100),
        bill("2026-06-01", "2026-06-30", consumption=100, total_eur=60),
    ])
    assert rows[0].consumption_yoy == pytest.approx(-50)
    assert rows[0].unit_cost_yoy == pytest.approx((0.6 - 0.5) / 0.5 * 100)
    assert rows[1].consumption_yoy is None
