from pathlib import Path

import pytest

from app.services import extraction
from app.services.bill_parser import parse_bill_text

FIX = Path(__file__).parent / "fixtures"


def test_power_bill():
    r = parse_bill_text((FIX / "bill_power.txt").read_text())
    assert r.complete and not r.warnings
    f = r.fields
    assert (f["commodity"], f["period_start"], f["period_end"]) == ("power", "2026-06-01", "2026-06-30")
    assert (f["consumption"], f["total_eur"], f["power_kw"]) == (260.54, 95.05, 4.5)
    assert (f["kwh_f1"], f["kwh_f2"], f["kwh_f3"]) == (48.01, 54.69, 157.84)
    assert (f["annual_f1"], f["annual_f2"], f["annual_f3"]) == (431.93, 509.62, 1213.65)
    assert f["annual_spend"] == 824.44 and f["reading_type"] == "effettiva"
    assert f["social_bonus_expires_on"] == "2027-02-28"


def test_gas_bill():
    r = parse_bill_text((FIX / "bill_gas.txt").read_text())
    assert r.complete
    f = r.fields
    assert f["commodity"] == "gas" and f["consumption"] == 10.19 and f["total_eur"] == 27.77
    assert f["annual_consumption"] == pytest.approx(553.759264) and f["annual_spend"] == 813.01
    assert f["coeff_c"] == 1.018672 and f["mc"] == 10.0 and f["reading_type"] == "stimata"


def test_bands_not_matching_total_are_dropped():
    text = (FIX / "bill_power.txt").read_text().replace("Totale da pagare 95,05", "").replace("[kWh] 260,54", "[kWh] 300,00")
    r = parse_bill_text(text)
    assert "kwh_f1" not in r.fields and r.warnings


def test_unknown_layout_is_incomplete():
    r = parse_bill_text("Fattura di un altro fornitore\nImporto 10 euro")
    assert not r.complete and "commodity" in r.missing


class FakeClient:
    calls = 0

    class messages:
        @staticmethod
        def create(**kw):
            FakeClient.calls += 1
            block = type("B", (), {"type": "tool_use", "input": {"commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-01-31", "consumption": 5.0}})
            return type("R", (), {"content": [block]})


def test_rules_avoid_llm(monkeypatch):
    monkeypatch.setattr(extraction, "pdf_text", lambda p: (FIX / "bill_power.txt").read_text())
    FakeClient.calls = 0
    fields, method = extraction.extract_bill("x.pdf", client=FakeClient)
    assert method == "regole" and FakeClient.calls == 0 and fields["consumption"] == 260.54


def test_llm_fallback_keeps_rule_fields(monkeypatch):
    monkeypatch.setattr(extraction, "pdf_text", lambda p: "Fornitura: GAS NATURALE\nTotale da pagare 12,00")
    fields, method = extraction.extract_bill("x.pdf", client=FakeClient)
    assert method == "LLM" and fields["total_eur"] == 12.0 and fields["consumption"] == 5.0


def test_no_key_returns_partial(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(extraction, "pdf_text", lambda p: "Fornitura: GAS NATURALE")
    with pytest.raises(extraction.ExtractionError) as e:
        extraction.extract_bill("x.pdf")
    assert e.value.partial["commodity"] == "gas"


def test_current_offer_from_power_bill():
    from app.services.bill_parser import parse_offer_terms

    t = parse_offer_terms((FIX / "bill_power.txt").read_text(), "power")
    o = t.offer
    assert (o["name"], o["price_type"], o["spread"], o["loss_pct"], o["dispatching"]) == ("Zero pensieri casa index", "indexed", 0.025, 10.0, 0.0105)
    assert o["fixed_fee_month"] == 11.60
    assert o["capacity"] == pytest.approx((16.44 * 0.0715 + 244.09 * 0.003981) / (16.44 + 244.09))
    assert t.pun == pytest.approx(0.33 * 0.12576 + 0.30 * 0.1517 + 0.37 * 0.127236)


def test_current_offer_from_gas_bill():
    from app.services.bill_parser import parse_offer_terms

    t = parse_offer_terms((FIX / "bill_gas.txt").read_text(), "gas")
    assert (t.offer["spread"], t.offer["gas_mgmt"], t.offer["fixed_fee_month"]) == (0.165, 0.05, 11.50)
    assert t.psv == 0.504871


def test_offer_terms_none_when_unrecognised():
    from app.services.bill_parser import parse_offer_terms

    assert parse_offer_terms("Fornitura: GAS NATURALE\nTotale da pagare 12,00", "gas") is None
