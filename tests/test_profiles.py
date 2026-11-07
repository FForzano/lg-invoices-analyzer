BILL = {"commodity": "gas", "period_start": "2025-07-01", "period_end": "2026-06-30", "consumption": "500",
        "annual_consumption": "500", "total_eur": "300"}
OFFER = {"commodity": "gas", "supplier": "S", "price_type": "fixed", "price": "1"}


def switch_to(client, name):
    page = client.get("/profiles").text
    import re
    pid = re.search(r'<option value="(\d+)"[^>]*>' + name + "</option>", page).group(1)
    return client.post("/profiles/switch", data={"profile_id": pid, "next": "/bills"})


def test_profiles_have_separate_bills_current_offer_and_settings(client):
    client.post("/bills", data=BILL)
    client.post("/offers/save", data={**OFFER, "name": "Attuale casa", "is_current": "on"})
    client.post("/offers/save", data={**OFFER, "name": "Catalogo"})
    client.post("/settings", data={"pun": "0,13", "psv": "0,4", "loss_pct": "10", "dispatching_extra": "0,019",
                                   "default_power_kw": "6", "region": "08", "province": "038", "comune": "038008"})

    r = client.post("/profiles", data={"name": "Mare"}, follow_redirects=True)
    assert "Profilo «Mare» creato" in r.text and "Mare</option>" in r.text
    # il nuovo profilo parte vuoto, con località/potenza copiate, ma vede il catalogo condiviso
    assert "Nessuna bolletta" in client.get("/bills").text
    offers = client.get("/offers").text
    assert "Catalogo" in offers and "Attuale casa" not in offers
    assert 'value="6.0"' in client.get("/settings").text
    # l'offerta attuale è per profilo
    client.post("/offers/save", data={**OFFER, "name": "Attuale mare", "is_current": "on"})
    assert client.get("/offers").text.count("<strong>attuale</strong>") == 1 and "Attuale mare" in client.get("/offers").text
    client.post("/settings", data={"pun": "0,13", "psv": "0,4", "loss_pct": "10", "dispatching_extra": "0,019",
                                   "default_power_kw": "3", "region": "01", "province": "001", "comune": "001001"})

    switch_to(client, "Casa")
    assert "260,54" not in client.get("/bills").text and "500,00" in client.get("/bills").text
    offers = client.get("/offers").text
    assert "Attuale casa" in offers and "Attuale mare" not in offers
    assert 'value="038008"' in client.get("/settings").text  # la località di Casa non è cambiata


def test_selected_profile_survives_requests_and_next_is_internal_only(client):
    client.post("/profiles", data={"name": "Mare"})
    assert client.get("/").text.count("· Mare") == 1
    r = client.post("/profiles/switch", data={"profile_id": "1", "next": "//evil.example/x"})
    assert r.headers["Location"] == "/"
    assert client.post("/profiles/switch", data={"profile_id": "999"}).status_code == 404


def test_delete_profile_removes_its_data_and_pdfs_but_not_the_last_one(client, monkeypatch):
    import re
    from app.services import extraction

    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")  # il PDF finto non contiene offerte da rilevare
    client.post("/profiles", data={"name": "Mare"})
    pdf_dir = client.application.config["PDF_DIR"]
    (pdf_dir / "x.pdf").write_bytes(b"%PDF")
    client.post("/bills", data={**BILL, "pdf_path": "x.pdf"})
    client.post("/offers/save", data={**OFFER, "name": "Attuale mare", "is_current": "on"})
    mare_id = re.findall(r"/profiles/(\d+)/delete", client.get("/profiles").text)[-1]
    client.post(f"/profiles/{mare_id}/delete")
    assert not (pdf_dir / "x.pdf").exists()
    assert "Mare</option>" not in client.get("/").text and "Attuale mare" not in client.get("/offers").text
    assert not re.findall(r"/profiles/(\d+)/delete", client.get("/profiles").text)  # un solo profilo: niente «elimina»
    assert "almeno un profilo" in client.post("/profiles/1/delete", follow_redirects=True).text


def test_cannot_edit_another_profiles_current_offer(client):
    import re

    client.post("/offers/save", data={**OFFER, "name": "Attuale casa", "is_current": "on"})
    offer_id = re.search(r"/offers/(\d+)\"", client.get("/offers").text).group(1)
    client.post("/profiles", data={"name": "Mare"})
    assert client.get(f"/offers/{offer_id}").status_code == 404
    assert client.post("/offers/save", data={**OFFER, "id": offer_id, "name": "Rubata"}).status_code == 404
    client.post(f"/offers/{offer_id}/delete")
    switch_to(client, "Casa")
    assert "Attuale casa" in client.get("/offers").text  # la cancellazione dell'altro profilo non ha effetto
