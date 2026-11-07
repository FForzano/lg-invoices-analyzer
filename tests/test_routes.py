def test_pages_render_empty(client):
    for path in ("/", "/bills", "/bills/new", "/history", "/offers", "/offers/new", "/compare", "/compare?commodity=gas", "/settings"):
        assert client.get(path).status_code == 200, path


def test_bill_flow_and_compare(client):
    r = client.post("/bills", data={
        "commodity": "power", "period_start": "2026-06-01", "period_end": "2026-06-30",
        "kwh_f1": "100", "kwh_f2": "80", "kwh_f3": "80.54", "annual_consumption": "2155",
        "annual_f1": "432", "annual_f2": "510", "annual_f3": "1214", "power_kw": "4,5", "total_eur": "95,05",
    })
    assert r.status_code == 302
    assert "260,54" in client.get("/bills").text

    with open("examples/offers.csv", "rb") as f:
        client.post("/offers/import", data={"csv": (f, "offers.csv")}, content_type="multipart/form-data")
    page = client.get("/compare").text
    assert "Luce Fissa 12" in page and "attuale" in page and "2 155" in page


def test_invalid_bill_rejected(client):
    r = client.post("/bills", data={"commodity": "power"})
    assert r.status_code == 400


def test_only_one_current_offer(client):
    data = {"commodity": "gas", "supplier": "S", "name": "A", "price_type": "fixed", "price": "0.5", "is_current": "on"}
    client.post("/offers/save", data=data)
    client.post("/offers/save", data={**data, "name": "B"})
    assert client.get("/offers").text.count("<strong>attuale</strong>") == 1


def test_settings_roundtrip_with_istat_codes(client):
    form = {"pun": "0,13", "psv": "0,4", "loss_pct": "10", "dispatching_extra": "0,019", "default_power_kw": "4,5",
            "region": "08", "province": "038", "comune": "038008"}
    assert client.post("/settings", data=form).status_code == 302
    page = client.get("/settings").text
    assert 'value="038008"' in page and 'value="0.13"' in page
    assert "Valori non validi" in client.post("/settings", data={**form, "province": "FE"}, follow_redirects=True).text


def test_upload_detects_current_offer_and_gives_verdict(client, monkeypatch):
    import io
    from pathlib import Path
    from app.services import extraction

    fix = Path(__file__).parent / "fixtures"
    monkeypatch.setattr(extraction, "pdf_text", lambda p: (fix / "bill_power.txt").read_text())
    r = client.post("/bills/upload", data={"commodity": "power", "pdf": (io.BytesIO(b"%PDF"), "b.pdf")}, content_type="multipart/form-data")
    assert "Dati letti con regole" in r.text
    import re
    form = dict(re.findall(r'name="(\w+)"[^>]*?value="([^"]*)"', r.text))
    form["commodity"] = "power"
    r = client.post("/bills", data=form, follow_redirects=True)
    assert "Offerta attuale rilevata" in r.text and "PUN medio annuo assunto" in r.text
    assert "Nessuna offerta alternativa" in r.text  # c'è l'attuale ma nessun concorrente

    cheap = {"commodity": "power", "supplier": "Rivale", "name": "Fissa economica", "price_type": "fixed", "price": "0.10", "fixed_fee_month": "5"}
    client.post("/offers/save", data=cheap)
    home = client.get("/").text
    assert "Conviene cambiare" in home and "Fissa economica" in home

    # un'offerta attuale inserita a mano non viene sovrascritta da una nuova bolletta
    client.post("/offers/save", data={**cheap, "name": "Mia manuale", "is_current": "on"})
    client.post("/bills", data={**form, "period_start": "2026-07-01", "period_end": "2026-07-31"})
    page = client.get("/offers").text
    assert page.count("<strong>attuale</strong>") == 1
    assert re.search(r"Mia manuale.*?<strong>attuale</strong>", page, re.S)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.text == "ok"


def test_unwritable_data_dir_gives_clear_error(tmp_path):
    import os
    import pytest
    from app import create_app

    if os.geteuid() == 0:
        pytest.skip("root ignora i permessi")
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(RuntimeError, match="non scrivibile"):
            create_app(str(tmp_path / "data"))
    finally:
        tmp_path.chmod(0o700)
