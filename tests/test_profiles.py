BILL = {"commodity": "gas", "period_start": "2025-07-01", "period_end": "2026-06-30", "consumption": "500",
        "annual_consumption": "500", "total_eur": "300"}
OFFER = {"commodity": "gas", "supplier": "S", "price_type": "fixed", "price": "1"}
SETTINGS = {"pun": "0,13", "psv": "0,4", "loss_pct": "10", "dispatching_extra": "0,019", "default_power_kw": "6",
            "region": "08", "province": "038", "comune": "038008"}


def as_(pid):
    """Il front-end sceglie il profilo con l'header X-Profile-Id."""
    return {"headers": {"X-Profile-Id": str(pid)}}


def new_profile(client, name):
    return client.post("/api/profiles", json={"name": name}).json["id"]


def test_profiles_have_separate_bills_current_offer_and_settings(client):
    casa = client.get("/api/profiles").json["profile"]["id"]
    client.post("/api/bills", json=BILL)
    client.post("/api/offers", json={**OFFER, "name": "Attuale casa", "is_current": True})
    client.post("/api/offers", json={**OFFER, "name": "Catalogo"})
    client.put("/api/settings", json=SETTINGS)

    mare = new_profile(client, "Mare")
    # il nuovo profilo parte vuoto, con località/potenza copiate, ma vede il catalogo condiviso
    assert client.get("/api/bills", **as_(mare)).json["page"]["total"] == 0
    names = [o["name"] for o in client.get("/api/offers", **as_(mare)).json["items"]]
    assert "Catalogo" in names and "Attuale casa" not in names
    assert client.get("/api/settings", **as_(mare)).json["settings"]["default_power_kw"] == 6.0
    # l'offerta attuale è per profilo
    client.post("/api/offers", json={**OFFER, "name": "Attuale mare", "is_current": True}, **as_(mare))
    assert [o["name"] for o in client.get("/api/offers", **as_(mare)).json["items"] if o["is_current"]] == ["Attuale mare"]
    client.put("/api/settings", json={**SETTINGS, "default_power_kw": "3", "region": "01", "province": "001", "comune": "001001"}, **as_(mare))

    assert client.get("/api/bills", **as_(casa)).json["items"][0]["total_eur"] == 300
    names = [o["name"] for o in client.get("/api/offers", **as_(casa)).json["items"]]
    assert "Attuale casa" in names and "Attuale mare" not in names
    assert client.get("/api/settings", **as_(casa)).json["settings"]["comune"] == "038008"  # la località di Casa non è cambiata


def test_unknown_profile_header_falls_back_to_first(client):
    first = client.get("/api/profiles").json["profile"]["id"]
    assert client.get("/api/profiles", **as_(999)).json["profile"]["id"] == first


def test_profiles_list_counts_bills(client):
    client.post("/api/bills", json=BILL)
    mare = new_profile(client, "Mare")
    counts = {p["name"]: p["bills"] for p in client.get("/api/bootstrap").json["profiles"]}
    assert counts["Casa"] == 1 and counts["Mare"] == 0 and mare
    assert client.post("/api/profiles", json={"name": ""}).status_code == 400
    assert client.post("/api/profiles", json={"name": "x" * 61}).status_code == 400


def test_rename_profile(client):
    mare = new_profile(client, "Mare")
    assert client.post(f"/api/profiles/{mare}/rename", json={"name": "Montagna"}).status_code == 200
    assert "Montagna" in [p["name"] for p in client.get("/api/profiles").json["profiles"]]
    assert client.post("/api/profiles/999/rename", json={"name": "x"}).status_code == 404


def test_delete_profile_removes_its_data_and_pdfs_but_not_the_last_one(client, monkeypatch):
    from app.services import extraction

    monkeypatch.setattr(extraction, "pdf_text", lambda p: "")  # il PDF finto non contiene offerte da rilevare
    mare = new_profile(client, "Mare")
    pdf_dir = client.application.config["PDF_DIR"]
    (pdf_dir / "x.pdf").write_bytes(b"%PDF")
    client.post("/api/bills", json={**BILL, "pdf_path": "x.pdf"}, **as_(mare))
    client.post("/api/offers", json={**OFFER, "name": "Attuale mare", "is_current": True}, **as_(mare))
    assert client.delete(f"/api/profiles/{mare}").status_code == 200
    assert not (pdf_dir / "x.pdf").exists()
    assert "Mare" not in [p["name"] for p in client.get("/api/profiles").json["profiles"]]
    assert "Attuale mare" not in str(client.get("/api/offers").json)
    only = client.get("/api/profiles").json["profiles"][0]["id"]
    r = client.delete(f"/api/profiles/{only}")  # un solo profilo: non si elimina
    assert r.status_code == 409 and "almeno un profilo" in r.json["error"]


def test_cannot_edit_another_profiles_current_offer(client):
    casa = client.get("/api/profiles").json["profile"]["id"]
    oid = client.post("/api/offers", json={**OFFER, "name": "Attuale casa", "is_current": True}).json["id"]
    mare = new_profile(client, "Mare")
    assert client.get(f"/api/offers/{oid}", **as_(mare)).status_code == 404
    assert client.put(f"/api/offers/{oid}", json={**OFFER, "name": "Rubata"}, **as_(mare)).status_code == 404
    client.delete(f"/api/offers/{oid}", **as_(mare))
    assert "Attuale casa" in str(client.get("/api/offers", **as_(casa)).json)  # la cancellazione dell'altro profilo non ha effetto
