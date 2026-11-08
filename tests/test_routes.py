"""Scenari di dominio attraverso l'API JSON (le pagine ora sono nel front-end React)."""
import io
from pathlib import Path

import pytest

from app import create_app, db
from app.services import extraction

FIX = Path(__file__).parent / "fixtures"
OFFER = {"commodity": "power", "supplier": "S", "price_type": "fixed", "price": "0.1"}


def upload(client, files, commodity="power"):
    return client.post("/api/bills/upload", data={"commodity": commodity, "pdf": files}, content_type="multipart/form-data")


def save_from_pdf(client, monkeypatch, fixture, commodity):
    monkeypatch.setattr(extraction, "pdf_text", lambda p: (FIX / fixture).read_text())
    r = upload(client, (io.BytesIO(b"%PDF"), "b.pdf"), commodity).json["prefill"]
    return client.post("/api/bills", json={**r["values"], "commodity": commodity}), r


def test_api_pages_empty(client):
    for path in ("/home", "/bills", "/history/power", "/offers", "/compare/power", "/compare/gas", "/compare-dual", "/settings", "/profiles", "/layouts", "/proposals"):
        assert client.get(f"/api{path}").status_code == 200, path


def test_bill_flow_and_compare(client):
    r = client.post("/api/bills", json={
        "commodity": "power", "period_start": "2026-06-01", "period_end": "2026-06-30",
        "kwh_f1": "100", "kwh_f2": "80", "kwh_f3": "80.54", "annual_consumption": "2155",
        "annual_f1": "432", "annual_f2": "510", "annual_f3": "1214", "power_kw": "4,5", "total_eur": "95,05",
    })
    assert r.status_code == 201
    assert client.get("/api/bills").json["items"][0]["consumption"] == 260.54

    with open("examples/offers.csv", "rb") as f:
        client.post("/api/offers/import-csv", data={"csv": (f, "offers.csv")}, content_type="multipart/form-data")
    d = client.get("/api/compare/power").json
    names = [i["offer"]["name"] for i in d["items"]]
    assert "Luce Fissa 12" in names and any(i["offer"]["is_current"] for i in d["items"])
    assert d["analysis"]["consumption"]["total"] == 2155


def test_invalid_bill_rejected(client):
    assert client.post("/api/bills", json={"commodity": "power"}).status_code == 400


def test_only_one_current_offer(client):
    data = {"commodity": "gas", "supplier": "S", "name": "A", "price_type": "fixed", "price": "0.5", "is_current": True}
    client.post("/api/offers", json=data)
    client.post("/api/offers", json={**data, "name": "B"})
    assert sum(o["is_current"] for o in client.get("/api/offers").json["items"]) == 1


def test_settings_roundtrip_with_istat_codes(client):
    form = {"pun": "0,13", "psv": "0,4", "loss_pct": "10", "dispatching_extra": "0,019", "default_power_kw": "4,5",
            "region": "08", "province": "038", "comune": "038008"}
    assert client.put("/api/settings", json=form).status_code == 200
    s = client.get("/api/settings").json["settings"]
    assert s["comune"] == "038008" and s["pun"] == 0.13
    r = client.put("/api/settings", json={**form, "province": "FE"})
    assert r.status_code == 400 and "Valori non validi" in r.json["error"]


def test_upload_detects_current_offer_and_gives_verdict(client, monkeypatch):
    r, pre = save_from_pdf(client, monkeypatch, "bill_power.txt", "power")
    assert any("Dati letti con regole" in m["text"] for m in pre["messages"])
    texts = [m["text"] for m in r.json["messages"]]
    assert any("Offerta attuale rilevata" in t for t in texts) and any("PUN medio annuo assunto" in t for t in texts)
    power = client.get("/api/home").json["analyses"]["power"]
    assert power["has_current"] and power["verdict"] is None  # c'è l'attuale ma nessun concorrente

    cheap = {"commodity": "power", "supplier": "Rivale", "name": "Fissa economica", "price_type": "fixed", "price": "0.10", "fixed_fee_month": "5"}
    client.post("/api/offers", json=cheap)
    v = client.get("/api/home").json["analyses"]["power"]["verdict"]
    assert v["worthwhile"] and v["best"]["offer"]["name"] == "Fissa economica"

    # un'offerta attuale inserita a mano non viene sovrascritta da una nuova bolletta
    client.post("/api/offers", json={**cheap, "name": "Mia manuale", "is_current": True})
    client.post("/api/bills", json={**pre["values"], "commodity": "power", "period_start": "2026-07-01", "period_end": "2026-07-31"})
    current = [o for o in client.get("/api/offers").json["items"] if o["is_current"]]
    assert [o["name"] for o in current] == ["Mia manuale"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.text == "ok"


def test_unwritable_data_dir_gives_clear_error(tmp_path):
    import os

    if os.geteuid() == 0:
        pytest.skip("root ignora i permessi")
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(RuntimeError, match="non scrivibile"):
            create_app(str(tmp_path / "data"))
    finally:
        tmp_path.chmod(0o700)


def test_bulk_import_saves_complete_bills_and_reports_the_rest(client, monkeypatch):
    texts = {b"power": (FIX / "bill_power.txt").read_text(), b"gas": (FIX / "bill_gas.txt").read_text(), b"junk": "nulla di utile"}
    monkeypatch.setattr(extraction, "pdf_text", lambda p: texts[Path(p).read_bytes()])
    files = [(io.BytesIO(k), f"{k.decode()}{i}.pdf") for i, k in enumerate([b"power", b"gas", b"power", b"junk"])]
    bulk = upload(client, files).json["bulk"]
    text = " ".join(m["text"] for m in bulk["messages"])
    assert bulk["imported"] == 2 and "Importate 2 bollette su 4" in text
    assert "power2.pdf: già presente" in text and "junk3.pdf" in text and "Offerta attuale rilevata" in text
    assert len(list(client.application.config["PDF_DIR"].glob("*.pdf"))) == 2  # i PDF scartati non restano su disco


def test_lists_are_paginated(client):
    for i in range(60):
        client.post("/api/offers", json={**OFFER, "name": f"Offerta {i:02d}"})
    first = client.get("/api/offers").json
    names = [o["name"] for o in first["items"]]
    assert "Offerta 00" in names and "Offerta 59" not in names and first["page"] == {"number": 1, "pages": 2, "total": 60}
    second = client.get("/api/offers?page=2").json
    assert "Offerta 59" in [o["name"] for o in second["items"]] and second["page"]["number"] == 2
    assert client.get("/api/offers?page=99").json["page"]["number"] == 2  # pagina fuori limite: l'ultima
    assert [o["name"] for o in client.get("/api/offers?q=offerta 07").json["items"]] == ["Offerta 07"]


def test_dual_fuel_offers_stay_out_of_single_ranking_and_appear_in_bundles(client):
    for commodity in ("power", "gas"):
        client.post("/api/bills", json={"commodity": commodity, "period_start": "2025-07-01", "period_end": "2026-06-30",
                                        "consumption": "2000", "annual_consumption": "2000", "total_eur": "500"})
    base = {"price_type": "fixed", "supplier": "S"}
    for o in [
        {"commodity": "power", "name": "Attuale luce", "price": "0,25", "is_current": True},
        {"commodity": "gas", "name": "Attuale gas", "price": "1", "is_current": True},
        {"commodity": "power", "name": "Pacchetto luce", "price": "0,10", "source": "arera:P", "dual_with": "arera:G"},
        {"commodity": "gas", "name": "Pacchetto gas", "price": "0,4", "source": "arera:G", "dual_with": "arera:P"},
    ]:
        client.post("/api/offers", json={**base, **o})
    single = [i["offer"]["name"] for i in client.get("/api/compare/power").json["items"]]
    assert "Pacchetto luce" not in single  # richiede anche il gas: non è un'alternativa singola
    bundles = client.get("/api/compare-dual").json["items"]
    assert bundles[0]["power"]["offer"]["name"] == "Pacchetto luce" and bundles[0]["gas"]["offer"]["name"] == "Pacchetto gas"
    dual = client.get("/api/home").json["dual"]["verdict"]
    assert dual["worthwhile"] and dual["best"]["power"]["offer"]["name"] == "Pacchetto luce" and isinstance(dual["beats_separate"], bool)
    assert any(o["dual_with"] for o in client.get("/api/offers").json["items"])


def test_offer_terms_survive_edit_and_mark_current(client):
    data = {"commodity": "gas", "supplier": "S", "name": "Fix 24", "price_type": "fixed", "price": "0.555",
            "duration_months": "24", "conditions": "Solo nuovi clienti\nAddebito su conto", "after_term": "Trascorsi 24 mesi il prezzo cambia"}
    oid = client.post("/api/offers", json=data).json["id"]
    got = client.get(f"/api/offers/{oid}").json["offer"]
    assert got["duration_months"] == 24 and "Solo nuovi clienti" in got["conditions"] and "Trascorsi 24 mesi" in got["after_term"]
    # salvare di nuovo dal form (anche marcandola attuale con la data) non deve perdere i testi
    cid = client.put(f"/api/offers/{oid}", json={**data, "is_current": True, "started_on": "2026-11-08"}).json["id"]  # «attuale» = copia del profilo
    offer = client.get(f"/api/offers/{cid}").json["offer"]
    assert offer["is_current"] and offer["duration_months"] == 24 and offer["conditions"].endswith("Addebito su conto") and offer["started_on"] == "2026-11-08"


def test_home_carries_duration_and_seller_conditions(client, monkeypatch):
    save_from_pdf(client, monkeypatch, "bill_gas.txt", "gas")
    client.post("/api/offers", json={"commodity": "gas", "supplier": "Rivale", "name": "Fix 24", "price_type": "fixed", "price": "0.10",
                                     "duration_months": "24", "conditions": "Solo nuovi clienti", "after_term": "Trascorsi 24 mesi il prezzo cambia"})
    best = client.get("/api/home").json["analyses"]["gas"]["verdict"]["best"]["offer"]
    assert best["duration_months"] == 24 and best["conditions"] == "Solo nuovi clienti" and best["after_term"].startswith("Trascorsi")


def test_proposal_evaluation_judges_against_current_offer(client):
    client.post("/api/bills", json={"commodity": "gas", "period_start": "2026-01-01", "period_end": "2026-12-31", "mc": "1000", "coeff_c": "1", "annual_consumption": "1000"})
    client.post("/api/offers", json={"commodity": "gas", "supplier": "S", "name": "Att", "price_type": "fixed", "price": "0.80", "is_current": True})
    base = {"commodity": "gas", "price_type": "fixed"}
    good = client.post("/api/proposals/evaluate", json={**base, "price": "0.60"}).json
    assert good["verdict"]["worthwhile"] and round(good["verdict"]["saving"]) == 200
    assert not client.post("/api/proposals/evaluate", json={**base, "price": "0.90"}).json["verdict"]["worthwhile"]
    assert client.post("/api/proposals/evaluate", json=base).status_code == 400  # manca il prezzo
    assert "Proposta ricevuta" not in str(client.get("/api/offers").json)  # non viene salvata


def test_proposal_save_and_contract_checklist(client):
    form = {"commodity": "gas", "price_type": "fixed", "price": "0,55", "supplier": "Acme", "one_off_discount": "50",
            "contact": "Mario, 3 nov", "notes": "Nessuna penale di recesso"}
    pid = client.post("/api/proposals", json=form).json["id"]
    d = client.get(f"/api/proposals/{pid}").json
    check = dict(map(tuple, d["checklist"]))
    assert check["Prezzo fisso"] == "0,55 €/Smc" and check["Bonus / sconto una tantum"] == "50 €"
    assert d["proposal"]["notes"] == "Nessuna penale di recesso" and d["proposal"]["contact"] == "Mario, 3 nov" and d["always_check"]
    assert [p["supplier"] for p in client.get("/api/proposals").json["items"]] == ["Acme"]
    client.post("/api/proposals", json={**form, "id": pid, "price": "0,60"})
    assert dict(map(tuple, client.get(f"/api/proposals/{pid}").json["checklist"]))["Prezzo fisso"] == "0,6 €/Smc"
    assert len(client.get("/api/proposals").json["items"]) == 1
    assert "Acme" not in str(client.get("/api/offers").json)  # non entra nel catalogo
    client.delete(f"/api/proposals/{pid}")
    assert client.get(f"/api/proposals/{pid}").status_code == 404


def test_help_texts_for_info_buttons(client):
    help_ = client.get("/api/bootstrap").json["help"]
    assert "PUN (Prezzo Unico Nazionale)" in help_["pun"] and "FISSO:" in help_["price_type"] and help_["t_saving"]


def test_frontend_is_served_with_client_side_routing(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<div id=root></div>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    c = create_app(str(tmp_path / "data"), str(dist)).test_client()
    assert "root" in c.get("/").text and "root" in c.get("/bills/new").text  # le pagine sono rotte del front-end
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/api/nulla").status_code == 404 and c.get("/api/nulla").json["error"]
    assert c.get("/../../etc/passwd").status_code in (200, 404)  # mai un file fuori da dist/
    assert "etc" not in c.get("/..%2f..%2fetc/passwd").text


def test_frontend_missing_says_how_to_build(tmp_path):
    c = create_app(str(tmp_path / "data"), str(tmp_path / "nessun-dist")).test_client()
    assert c.get("/").status_code == 503 and "npm run build" in c.get("/").text


def test_factors_unused(client):
    with client.application.app_context():
        assert db.get_index_factors()["pun"]


def test_legacy_cron_url_still_works(client, monkeypatch):
    from app.services import arera

    monkeypatch.setattr(arera, "fetch_offers", lambda: ([], {}))
    monkeypatch.setattr(arera, "fetch_index_history", lambda: (_ for _ in ()).throw(arera.AreraError("offline")))
    assert client.post("/offers/import-arera").status_code == 200  # deploy/refresh-offers.example.sh di versioni precedenti
