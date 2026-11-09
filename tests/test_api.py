"""API JSON per il front-end React: stessa logica delle pagine, risposte in JSON."""

OFFER = {"commodity": "power", "supplier": "A", "name": "Attuale", "price_type": "fixed", "price": 0.14, "fixed_fee_month": 8, "is_current": True}
ALT = {**OFFER, "supplier": "B", "name": "Alternativa", "price": 0.10, "fixed_fee_month": 5, "is_current": False}


def seed(client):
    for m in range(1, 13):
        r = client.post("/api/bills", json={"commodity": "power", "period_start": f"2025-{m:02d}-01", "period_end": f"2025-{m:02d}-28", "consumption": 250, "total_eur": 80})
        assert r.status_code == 201, r.json
    assert client.post("/api/offers", json=OFFER).status_code == 200
    assert client.post("/api/offers", json=ALT).status_code == 200


def test_bootstrap_has_profile_and_help(client):
    d = client.get("/api/bootstrap").json
    assert d["profile"]["name"] and d["profiles"] and "price_type" in d["help"] and isinstance(d["can_extract"], bool)


def test_home_gives_verdict_as_json(client):
    seed(client)
    d = client.get("/api/home").json
    v = d["analyses"]["power"]["verdict"]
    assert v["worthwhile"] is True and v["saving"] > 30 and v["best"]["offer"]["name"] == "Alternativa"
    assert d["analyses"]["gas"]["verdict"] is None and "ranked" not in d["analyses"]["power"]


def test_compare_is_paginated_and_validates_commodity(client):
    seed(client)
    d = client.get("/api/compare/power").json
    assert d["page"]["total"] == 2 and d["items"][0]["offer"]["name"] == "Alternativa"
    assert client.get("/api/compare/xyz").status_code == 404


def test_errors_are_json(client):
    r = client.post("/api/bills", json={"commodity": "power"})
    assert r.status_code == 400 and "obbligatorio" in r.json["error"]


def test_profile_header_selects_profile(client):
    seed(client)
    client.post("/api/profiles", json={"name": "Mare"})
    mare = next(p for p in client.get("/api/profiles").json["profiles"] if p["name"] == "Mare")
    assert client.get("/api/bills", headers={"X-Profile-Id": str(mare["id"])}).json["page"]["total"] == 0
    assert client.get("/api/bills").json["page"]["total"] == 12


def test_settings_roundtrip(client):
    s = client.get("/api/settings").json["settings"]
    s["pun"] = "0,15"
    assert client.put("/api/settings", json=s).json["settings"]["pun"] == 0.15
    assert client.put("/api/settings", json={**s, "pun": "x"}).status_code == 400


def test_proposal_evaluate_and_save(client):
    seed(client)
    body = {**ALT, "is_current": False, "supplier": "", "name": ""}
    r = client.post("/api/proposals/evaluate", json=body).json
    assert r["verdict"]["saving"] > 0
    pid = client.post("/api/proposals", json=body).json["id"]
    d = client.get(f"/api/proposals/{pid}").json
    assert d["checklist"] and d["always_check"] and d["verdict"]
    assert client.delete(f"/api/proposals/{pid}").json["ok"]


def test_history_and_offers_crud(client):
    seed(client)
    h = client.get("/api/history/power").json
    assert h["unit"] == "kWh" and len(h["chart"]["labels"]) == 12
    items = client.get("/api/offers").json["items"]
    oid = items[0]["id"]
    assert client.put(f"/api/offers/{oid}", json={**OFFER, "name": "Nuovo nome"}).status_code == 200
    assert client.get(f"/api/offers/{oid}").json["offer"]["name"] == "Nuovo nome"
    assert client.delete(f"/api/offers/{oid}").json["ok"]


def test_computed_properties_are_serialized(client):
    seed(client)
    a = client.get("/api/home").json["analyses"]["power"]
    assert a["verdict"]["best"]["estimate"]["total"] > 0 and isinstance(a["consumption"]["partial"], bool)
    assert "beats_separate" not in a  # solo nel verdetto luce+gas


def test_compare_accepts_filters_and_power(client):
    qs = "?type=fixed&no_exit=1&bonus=1&no_domic=1&power=4.5&q=x"
    for path in ("/api/compare/power", "/api/compare/gas", "/api/compare-dual"):
        assert client.get(path + qs).status_code == 200
    assert client.get("/api/compare/power?power=abc").status_code == 200  # valore non valido: ignorato
    assert client.get("/api/compare/power").json["power_default"] == 3.0
