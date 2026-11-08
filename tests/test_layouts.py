import json
from pathlib import Path

import pytest

from app.services import extraction, layouts
from app.services.layouts import Layout, Rule, apply_layouts, learn_layout, learn_rule, report

FIX = Path(__file__).parent / "fixtures"
TEXT = (FIX / "bill_other_power.txt").read_text()
SAMPLES = {
    "commodity": ("Energia elettrica", "power"),
    "period_start": ("01/03/2026", None),
    "period_end": ("31/03/2026", None),
    "consumption": ("210,5", None),
    "total_eur": ("88,40", None),  # etichetta sulla riga sopra
    "power_kw": ("3", None),
    "reading_type": ("Letture effettive", "effettiva"),
}


def taught():
    layout, errors = learn_layout(TEXT, "Luce Esempio", "Luce Esempio SPA", SAMPLES)
    assert not errors, errors
    return layout


def test_learned_layout_reads_the_same_bill_back():
    fields, used = apply_layouts(TEXT, {}, [taught()])
    assert fields == {"commodity": "power", "period_start": "2026-03-01", "period_end": "2026-03-31", "consumption": 210.5,
                      "total_eur": 88.4, "power_kw": 3.0, "reading_type": "effettiva"}
    assert used == ["Luce Esempio"]


def test_learned_layout_works_on_another_bill_with_other_values():
    other = (TEXT.replace("01/03/2026", "01/04/2026").replace("31/03/2026", "30/04/2026")
             .replace("210,5", "1.234,56").replace("88,40", "1.020,10").replace("Mario Verdi", "Anna Neri"))
    f, _ = apply_layouts(other, {}, [taught()])
    assert (f["period_start"], f["period_end"], f["consumption"], f["total_eur"]) == ("2026-04-01", "2026-04-30", 1234.56, 1020.1)


def test_layout_is_ignored_for_other_suppliers_and_never_overrides_read_fields():
    layout = taught()
    assert apply_layouts(TEXT.replace("LUCE ESEMPIO", "ALTRO"), {}, [layout])[0] == {}
    assert apply_layouts(TEXT, {"total_eur": 1.0}, [layout])[0]["total_eur"] == 1.0


def test_second_value_after_same_label_uses_index():
    rule = learn_rule(TEXT, "period_end", "31/03/2026")
    assert (rule.anchor, rule.side, rule.index) == ("Dal", "before", 1)


def test_rejects_unusable_input_with_a_reason():
    with pytest.raises(ValueError, match="non compare"):
        learn_rule(TEXT, "total_eur", "99,99")
    with pytest.raises(ValueError, match="formato"):
        learn_rule(TEXT, "total_eur", "novantotto")
    with pytest.raises(ValueError, match="scegli"):
        learn_rule(TEXT, "commodity", "Energia elettrica")
    with pytest.raises(ValueError, match="fornitore"):
        learn_layout(TEXT, "x", "Altro fornitore", {})


def test_label_with_personal_data_is_not_used():
    text = "Cliente Mario Verdi 1234567890\n55,00\n"
    with pytest.raises(ValueError, match="dati personali"):
        learn_rule(text, "total_eur", "55,00")


def test_report_has_no_values_and_roundtrips():
    raw, dropped = report(taught())
    assert not dropped
    for secret in ("88,40", "210,5", "Mario", "Verdi", "4471", "2026"):
        assert secret not in raw
    assert Layout.from_json(raw).rules == taught().rules


def test_report_drops_rules_with_suspicious_labels():
    layout = Layout("x", "x", [Rule("total_eur", "number", "Cliente 12345678"), Rule("consumption", "number", "Consumo")])
    raw, dropped = report(layout)
    assert dropped == ["total_eur"] and "12345678" not in raw


def test_teachable_fields_follow_the_bill_model():
    kinds = layouts.teachable_fields()
    assert kinds["total_eur"] == "number" and kinds["period_start"] == "date" and kinds["commodity"] == "keyword"
    assert "id" not in kinds and "profile_id" not in kinds and "pdf_path" not in kinds


def test_extraction_uses_layouts_before_the_llm():
    fields, method = extraction.extract_text(TEXT.strip(), layouts=[taught()])
    assert method.startswith("layout") and fields["total_eur"] == 88.4
    with pytest.raises(extraction.ExtractionError) as e:  # senza layout e senza LLM: campi mancanti segnalati
        extraction.extract_text(TEXT.strip())
    assert "mancano" in str(e.value)


def test_builtin_layouts_are_loaded_from_json_files(tmp_path, monkeypatch):
    (tmp_path / "esempio.json").write_text(taught().to_json())
    (tmp_path / "rotto.json").write_text("{non json")
    monkeypatch.setattr(layouts, "BUILTIN_DIR", tmp_path)
    assert [l.name for l in layouts.builtin_layouts()] == ["Luce Esempio"]
    assert extraction.extract_text(TEXT.strip())[1].startswith("layout")


def _upload(client, monkeypatch, text):
    monkeypatch.setattr(extraction, "pdf_text", lambda path: text)
    import io
    return client.post("/bills/upload", data={"pdf": (io.BytesIO(b"%PDF-1.4"), "b.pdf"), "commodity": "power"}, content_type="multipart/form-data")


def test_teach_flow_then_next_bill_is_read_automatically(client, monkeypatch):
    r = _upload(client, monkeypatch, TEXT.strip())
    assert "Insegna all&#39;app a leggerlo" in r.text or "Insegna all'app a leggerlo" in r.text
    import re
    pdf = re.search(r"pdf=([0-9a-f]{32}\.pdf)", r.text).group(1)
    assert client.get(f"/layouts/pdf/{pdf}").mimetype == "application/pdf"  # lo stesso PDF già caricato, mostrato nella pagina
    page = client.get(f"/layouts/teach?pdf={pdf}")
    assert page.status_code == 200 and "Importo da pagare" in page.text and 'name="v_total_eur"' in page.text

    bad = client.post("/layouts/teach", data={"pdf": pdf, "signature": "Luce Esempio SPA", "v_total_eur": "99,99"})
    assert bad.status_code == 400 and "non compare" in bad.text

    data = {"pdf": pdf, "signature": "Luce Esempio SPA", "name": "Luce Esempio"}
    data |= {f"v_{f}": s for f, (s, _) in SAMPLES.items()} | {f"c_{f}": c for f, (_, c) in SAMPLES.items() if c}
    ok = client.post("/layouts/teach", data=data)
    assert ok.status_code == 200 and 'value="88.4"' in ok.text and "Layout" in ok.text

    again = _upload(client, monkeypatch, TEXT.replace("88,40", "12,00").strip())
    assert 'value="12.0"' in again.text and "layout" in again.text

    listing = client.get("/layouts").text
    assert "Luce Esempio" in listing
    report = client.get("/layouts/1/report")
    assert "88,40" not in report.text and "Mario" not in report.text and "issues/new" in report.text
    assert client.get("/layouts/1/report?download=1").mimetype == "application/json"
    client.post("/layouts/1/delete")
    assert "Luce Esempio" not in client.get("/layouts").text


def test_teach_rejects_unknown_pdf_names(client):
    assert client.get("/layouts/teach?pdf=../../etc/passwd").status_code == 404
    assert client.get("/layouts/teach").status_code == 404


def test_image_only_pdf_explains_what_to_do_and_does_not_offer_teaching(client, monkeypatch):
    page = _upload(client, monkeypatch, "").text
    assert "immagine" in page and "PDF digitale" in page and "Insegna" not in page
