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


def test_bulk_import_saves_complete_bills_and_reports_the_rest(client, monkeypatch):
    import io
    from pathlib import Path
    from app.services import extraction

    fix = Path(__file__).parent / "fixtures"
    texts = {b"power": (fix / "bill_power.txt").read_text(), b"gas": (fix / "bill_gas.txt").read_text(), b"junk": "nulla di utile"}
    monkeypatch.setattr(extraction, "pdf_text", lambda p: texts[Path(p).read_bytes()])
    files = [(io.BytesIO(k), f"{k.decode()}{i}.pdf") for i, k in enumerate([b"power", b"gas", b"power", b"junk"])]
    r = client.post("/bills/upload", data={"pdf": files}, content_type="multipart/form-data", follow_redirects=True)
    assert "Importate 2 bollette su 4" in r.text
    assert "power2.pdf: già presente" in r.text and "junk3.pdf" in r.text
    assert "Offerta attuale rilevata" in r.text
    assert len(list(client.application.config["PDF_DIR"].glob("*.pdf"))) == 2  # i PDF scartati non restano su disco


def test_lists_are_paginated(client):
    for i in range(60):
        client.post("/offers/save", data={"commodity": "power", "supplier": "X", "name": f"Offerta {i:02d}", "price_type": "fixed", "price": "0,1"})
    first = client.get("/offers").text
    assert "Offerta 00" in first and "Offerta 59" not in first and "Pagina 1 di 2" in first
    second = client.get("/offers?page=2").text
    assert "Offerta 59" in second and "Offerta 00" not in second
    assert "Pagina 2 di 2" in client.get("/offers?page=99").text  # pagina fuori limite: l'ultima


def test_dual_fuel_offers_stay_out_of_single_ranking_and_appear_in_bundles(client):
    for commodity, unit in (("power", "kWh"), ("gas", "Smc")):
        client.post("/bills", data={
            "commodity": commodity, "period_start": "2025-07-01", "period_end": "2026-06-30",
            "consumption": "2000", "annual_consumption": "2000", "total_eur": "500",
        })
    base = {"price_type": "fixed", "supplier": "S"}
    offers = [
        {"commodity": "power", "name": "Attuale luce", "price": "0,25", "is_current": "on"},
        {"commodity": "gas", "name": "Attuale gas", "price": "1", "is_current": "on"},
        {"commodity": "power", "name": "Pacchetto luce", "price": "0,10", "source": "arera:P", "dual_with": "arera:G"},
        {"commodity": "gas", "name": "Pacchetto gas", "price": "0,4", "source": "arera:G", "dual_with": "arera:P"},
    ]
    for o in offers:
        client.post("/offers/save", data={**base, **o})
    single = client.get("/compare?commodity=power").text
    assert "Pacchetto luce" not in single  # richiede anche il gas: non è un'alternativa singola
    page = client.get("/compare/dual").text
    assert "Pacchetto luce" in page and "Pacchetto gas" in page
    home = client.get("/").text
    assert "Luce e gas insieme" in home and "Conviene un'offerta luce+gas" in home
    assert "(luce+gas)" in client.get("/offers").text


def test_offer_terms_survive_edit_and_mark_current(client):
    data = {"commodity": "gas", "supplier": "S", "name": "Fix 24", "price_type": "fixed", "price": "0.555",
            "duration_months": "24", "conditions": "Solo nuovi clienti\nAddebito su conto", "after_term": "Trascorsi 24 mesi il prezzo cambia"}
    client.post("/offers/save", data=data)
    page = client.get("/offers/1").text
    assert 'value="24"' in page and "Solo nuovi clienti" in page and "Trascorsi 24 mesi" in page
    # salvare di nuovo dal form (anche marcandola attuale con la data) non deve perdere i testi
    form = {**data, "is_current": "on", "started_on": "2026-11-08"}
    client.post("/offers/save", data={**form, "id": "1"})
    offer = [o for o in db_offers(client) if o.is_current][0]
    assert offer.duration_months == 24 and offer.conditions.endswith("Addebito su conto") and offer.started_on == "2026-11-08"


def db_offers(client):
    from app import db
    with client.application.test_request_context("/"):
        return db.list_offers()


def test_home_shows_duration_and_seller_conditions(client, monkeypatch):
    import io
    import re
    from pathlib import Path
    from app.services import extraction

    monkeypatch.setattr(extraction, "pdf_text", lambda p: (Path(__file__).parent / "fixtures" / "bill_gas.txt").read_text())
    r = client.post("/bills/upload", data={"commodity": "gas", "pdf": (io.BytesIO(b"%PDF"), "b.pdf")}, content_type="multipart/form-data")
    form = dict(re.findall(r'name="(\w+)"[^>]*?value="([^"]*)"', r.text))
    form["commodity"] = "gas"
    client.post("/bills", data=form)
    client.post("/offers/save", data={"commodity": "gas", "supplier": "Rivale", "name": "Fix 24", "price_type": "fixed", "price": "0.10",
                                      "duration_months": "24", "conditions": "Solo nuovi clienti", "after_term": "Trascorsi 24 mesi il prezzo cambia"})
    home = client.get("/").text
    assert "Condizioni economiche valide 24 mesi" in home and "ti avviso prima della fine" in home
    assert "Solo nuovi clienti" in home and "Trascorsi 24 mesi il prezzo cambia" in home


def test_proposal_form_judges_against_current_offer(client):
    client.post("/bills", data={
        "commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-12-31",
        "mc": "1000", "coeff_c": "1", "annual_consumption": "1000",
    })
    client.post("/offers/save", data={"commodity": "gas", "supplier": "S", "name": "Att", "price_type": "fixed", "price": "0.80", "is_current": "on"})
    assert client.get("/proposal").status_code == 200
    base = {"commodity": "gas", "price_type": "fixed"}
    good = client.post("/proposal", data={**base, "price": "0.60"}).text
    assert "Conviene" in good and "200,00 €" in good
    bad = client.post("/proposal", data={**base, "price": "0.90"}).text
    assert "Non conviene" in bad
    assert client.post("/proposal", data=base).status_code == 400  # manca il prezzo
    assert "Proposta ricevuta" not in client.get("/offers").text  # non viene salvata


def test_proposal_save_and_contract_checklist(client):
    form = {"commodity": "gas", "price_type": "fixed", "price": "0,55", "supplier": "Acme", "one_off_discount": "50",
            "contact": "Mario, 3 nov", "notes": "Nessuna penale di recesso"}
    r = client.post("/proposal/save", data=form)
    assert r.status_code == 302
    page = client.get(r.headers["Location"]).text
    assert "Acme" in page and "0,55 €/Smc" in page and "50 €" in page and "Nessuna penale" in page and "Mario" in page
    assert "Acme" in client.get("/proposal/saved").text
    assert 'value="0.55"' in client.get("/proposal?from=1").text  # riparte dai dati salvati
    r = client.post("/proposal/save", data={**form, "id": "1", "price": "0,60"})
    assert "0,6 €/Smc" in client.get(r.headers["Location"]).text and client.get("/proposal/saved").text.count("Acme") == 1
    assert "Acme" not in client.get("/offers").text  # non entra nel catalogo
    client.post("/proposal/1/delete")
    assert client.get("/proposal/1").status_code == 404
