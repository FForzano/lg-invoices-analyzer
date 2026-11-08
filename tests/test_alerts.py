from datetime import date

from app.models import Offer
from app.services.alerts import build_alerts, terms_end


def current(**kw):
    return Offer(commodity="gas", supplier="S", name="N", price_type="fixed", price=0.5, is_current=True, **kw)


def gas_alerts(offer, today):
    return [text for _, text in build_alerts([], [offer], today) if text.startswith("Gas")]


def test_terms_end_adds_months_and_clamps_day():
    assert terms_end(current(started_on="2026-11-08", duration_months=24)) == date(2028, 11, 8)
    assert terms_end(current(started_on="2026-01-31", duration_months=1)) == date(2026, 2, 28)
    assert terms_end(current(started_on="2026-01-31")) is None and terms_end(current(duration_months=12)) is None


def test_warns_before_terms_end_and_suggests_comparing():
    offer = current(started_on="2026-11-08", duration_months=24, expires_on="2026-11-16")
    assert gas_alerts(offer, date(2027, 6, 1)) == []  # lontano; la scadenza del catalogo non conta dopo l'attivazione
    (text,) = gas_alerts(offer, date(2028, 10, 1))
    assert "finiscono tra 38 giorni" in text and "confronta le offerte" in text
    (text,) = gas_alerts(offer, date(2028, 12, 1))
    assert "sono terminate il 2028-11-08" in text and "potrebbe essere già cambiato" in text


def test_asks_for_start_date_when_duration_known_and_keeps_catalog_expiry():
    offer = current(duration_months=24, expires_on="2026-11-16")
    texts = gas_alerts(offer, date(2026, 11, 10))
    assert any("data di attivazione" in t for t in texts) and any("scade tra 6 giorni" in t for t in texts)
