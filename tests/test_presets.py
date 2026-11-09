from app.api.presets import clean_query


def test_clean_query_keeps_only_known_filters():
    assert clean_query("type=fixed&no_exit=1&evil=1&power=4.5&page=3&bonus=0") == "type=fixed&no_exit=1&power=4.5"
    assert clean_query("type=x&power=999&power=abc") == ""


def test_presets_per_profile(client):
    r = client.post("/api/filter-presets", json={"name": "Solo fisso", "query": "type=fixed&no_exit=1", "is_default": True})
    assert r.status_code == 201 and r.json["items"][0]["is_default"]
    client.post("/api/filter-presets", json={"name": "Solo fisso", "query": "type=fixed"})  # stesso nome: sostituisce
    items = client.get("/api/filter-presets").json["items"]
    assert [(p["name"], p["query"], p["is_default"]) for p in items] == [("Solo fisso", "type=fixed", False)]
    assert client.post("/api/filter-presets", json={"name": "x", "query": "page=2"}).status_code == 400
    client.put("/api/filter-presets/default", json={"id": items[0]["id"]})
    assert client.get("/api/filter-presets").json["items"][0]["is_default"]
    client.delete(f"/api/filter-presets/{items[0]['id']}")
    assert client.get("/api/filter-presets").json["items"] == []
