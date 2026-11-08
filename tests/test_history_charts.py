def test_history_gives_chart_series_with_estimated_flags(client):
    for m in range(1, 4):
        client.post("/api/bills", json={
            "commodity": "power", "period_start": f"2026-0{m}-01", "period_end": f"2026-0{m}-28",
            "consumption": str(100 * m), "total_eur": "50", "reading_type": "stimata" if m == 2 else "effettiva",
        })
    chart = client.get("/api/history/power").json["chart"]
    assert chart["estimated"] == [False, True, False]
    assert chart["labels"] == ["2026-01", "2026-02", "2026-03"] and chart["consumption"] == [100, 200, 300]
    assert len(chart["unit_cost"]) == 3
