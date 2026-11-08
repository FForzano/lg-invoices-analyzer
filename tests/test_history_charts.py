def test_history_page_embeds_chart_data_and_library(client):
    for m in range(1, 4):
        client.post("/bills", data={
            "commodity": "power", "period_start": f"2026-0{m}-01", "period_end": f"2026-0{m}-28",
            "consumption": str(100 * m), "total_eur": "50", "reading_type": "stimata" if m == 2 else "effettiva",
        })
    page = client.get("/history").text
    assert page.count("<canvas") == 3 and '"estimated": [false, true, false]' in page.replace('"estimated":[', '"estimated": [')
    assert client.get("/static/vendor/chart.umd.js").status_code == 200


def test_nav_has_menu_toggle(client):
    assert 'class="nav-toggle"' in client.get("/").text
