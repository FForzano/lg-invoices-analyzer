from datetime import date

import pytest

from app import db
from app.models import Bill
from app.services.consumption import annual_consumption
from app.services.seasonality import (
    DEFAULT_INDEX_FACTORS, consumption_profile, index_factors_from_csv, season_multiplier, share_of_year,
)


def test_profiles_sum_to_one():
    for commodity in ("power", "gas"):
        assert sum(consumption_profile(commodity)) == pytest.approx(1)
    assert sum(share_of_year(consumption_profile("gas"), date(2026, 1, 1), date(2026, 12, 31)) for _ in [0]) == pytest.approx(1)


def test_gas_summer_month_projects_far_above_naive_scaling():
    june = Bill(commodity="gas", period_start="2026-06-01", period_end="2026-06-30", consumption=10.19)
    c = annual_consumption([june])
    assert c.partial and c.days_covered == 30
    assert 400 < c.total < 700  # annuo reale 553,76 Smc; la proiezione piatta darebbe ~124


def test_winter_month_projects_lower_than_summer_scaling_for_gas():
    jan = Bill(commodity="gas", period_start="2026-01-01", period_end="2026-01-31", consumption=100)
    assert annual_consumption([jan]).total == pytest.approx(100 / consumption_profile("gas")[0])


def test_full_year_is_not_partial():
    bills = [
        Bill(commodity="power", period_start=f"2025-{m:02d}-01", period_end=f"2025-{m:02d}-28", consumption=100)
        for m in range(1, 13)
    ]
    assert not annual_consumption(bills).partial  # 336 giorni


def test_printed_annual_is_never_partial():
    b = Bill(commodity="gas", period_start="2026-06-01", period_end="2026-06-30", consumption=10, annual_consumption=554)
    assert not annual_consumption([b]).partial


def test_season_multiplier_gas_above_one_in_winter_heavy_profile():
    assert season_multiplier(consumption_profile("gas"), DEFAULT_INDEX_FACTORS["psv"]) > 1.0
    assert season_multiplier(consumption_profile("power"), (1,) * 12) == pytest.approx(1)


def test_index_factors_from_csv():
    def year(y, pun, psv):
        return "".join(f"{y}{m:02d};{pun[m-1]};{psv[m-1]};0,1;0,1;;0,1\r\n".replace(".", ",") for m in range(1, 13))
    pun = [0.2] * 6 + [0.1] * 6  # prima metà dell'anno doppia
    csv_text = "AnnoMese;PUN (€/kWh);PSV (€/Smc);PE;CMEM;Pfor;Psbil\r\n" + year(2024, pun, [0.5] * 12) + year(2025, pun, [0.5] * 12) + "202601;0,3;0,6;;;;\r\n"
    f = index_factors_from_csv(csv_text)
    assert f["pun"][0] == pytest.approx(1.3333, abs=1e-3) and f["pun"][11] == pytest.approx(0.6667, abs=1e-3)
    assert f["psv"] == (1.0,) * 12
    with pytest.raises(ValueError):
        index_factors_from_csv("AnnoMese;PUN;PSV\r\n202601;0,1;0,2\r\n")


def test_factors_roundtrip_in_db(client):
    with client.application.app_context():
        assert db.get_index_factors()["pun"] == DEFAULT_INDEX_FACTORS["pun"]
        db.save_index_factors({"pun": (2.0,) * 12})
        got = db.get_index_factors()
        assert got["pun"] == (2.0,) * 12 and got["psv"] == DEFAULT_INDEX_FACTORS["psv"]


def test_recent_levels_are_deseasonalized():
    from app.services.seasonality import recent_index_levels

    factors = {"pun": (2.0,) + (1.0,) * 11, "psv": (1.0,) * 12}
    text = "AnnoMese;PUN;PSV\r\n202511;0,10;0,50\r\n202512;0,10;0,50\r\n202601;0,40;0,60\r\n"
    r = recent_index_levels(text, factors, months=3)
    assert r["pun"] == pytest.approx((0.10 + 0.10 + 0.40 / 2.0) / 3, abs=1e-6)  # gennaio vale doppio: 0,40 -> 0,20
    assert r["psv"] == pytest.approx((0.5 + 0.5 + 0.6) / 3, abs=1e-6)
    assert r["until"] == "2026-01"


def test_use_recent_adopts_values(client):
    with client.application.app_context():
        db.save_settings({"pun_recent": 0.185, "psv_recent": 0.7, "recent_until": "2026-09"})
    assert client.get("/api/settings").json["settings"]["pun_recent"] == 0.185
    client.post("/api/settings/use-recent")
    with client.application.app_context():
        s = db.get_settings()
        assert s["pun"] == 0.185 and s["psv"] == 0.7


def test_bill_detection_respects_adopted_recent_prices(client, monkeypatch):
    import io
    from pathlib import Path
    from app.services import extraction

    monkeypatch.setattr(extraction, "pdf_text", lambda p: (Path(__file__).parent / "fixtures" / "bill_power.txt").read_text())

    def upload():
        r = client.post("/api/bills/upload", data={"commodity": "power", "pdf": (io.BytesIO(b"%PDF"), "b.pdf")}, content_type="multipart/form-data")
        client.post("/api/bills", json={**r.json["prefill"]["values"], "commodity": "power"})

    with client.application.app_context():
        db.save_settings({"pun_recent": 0.185, "psv_recent": 0.7, "recent_until": "2026-09"})
    upload()  # recenti non adottati: PUN ricavato dalla bolletta
    with client.application.app_context():
        assert db.get_settings()["pun"] != 0.12 and db.get_settings()["pun"] != 0.185
    client.post("/api/settings/use-recent")
    upload()  # adottati: la bolletta non li sovrascrive
    with client.application.app_context():
        assert db.get_settings()["pun"] == 0.185
