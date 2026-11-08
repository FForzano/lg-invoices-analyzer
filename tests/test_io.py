import pytest

from app import forms
from app.models import Bill, Offer
from app.services import extraction
from app.services.offers_csv import parse_offers_csv


def test_parse_italian_decimal_and_required():
    b = forms.parse(Bill, {"commodity": "gas", "period_start": "2026-06-01", "period_end": "2026-06-30", "mc": "10,5"})
    assert b.mc == 10.5
    # nel form i messaggi usano le etichette («Fine periodo»), non i nomi dei campi
    with pytest.raises(ValueError, match="Fine periodo") as e:
        forms.parse(Bill, {"commodity": "gas", "period_start": "2026-06-01"})
    assert "period_end" not in str(e.value)
    with pytest.raises(ValueError, match="«Fornitura»"):
        forms.parse(Bill, {"commodity": "acqua", "period_start": "a", "period_end": "b"})
    with pytest.raises(ValueError, match="«kWh F1»"):
        forms.parse(Bill, {"commodity": "power", "period_start": "a", "period_end": "b", "kwh_f1": "x"})
    # il CSV ha i nomi dei campi come intestazione e li vuole nei messaggi
    with pytest.raises(ValueError, match="period_end"):
        forms.parse(Bill, {"commodity": "gas", "period_start": "2026-06-01"}, labels=None)


def test_csv_import_reports_row_errors():
    text = "commodity;supplier;name;price_type;price\npower;A;X;fixed;0,1\npower;A;Y;boh;0,1\n"
    offers, errors = parse_offers_csv(text)
    assert len(offers) == 1 and offers[0].price == 0.1
    assert len(errors) == 1 and "Riga 3" in errors[0]


def test_example_csv_is_valid():
    offers, errors = parse_offers_csv(open("examples/offers.csv").read())
    assert len(offers) == 4 and not errors


def test_tool_schema_excludes_system_fields():
    props = extraction.tool_schema()["input_schema"]["properties"]
    assert "id" not in props and "pdf_path" not in props and "annual_spend" in props
