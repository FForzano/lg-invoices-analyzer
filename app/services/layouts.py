"""Layout di lettura delle bollette come dati: regole «etichetta → valore».

Tre livelli, dal più preciso al più generico (vedi `extraction.extract_bill`):
1. `bill_parser`: regole scritte a mano per i layout noti (celle incollate, controlli incrociati).
2. Layout *forniti con l'app*: file JSON in `app/layouts/` (stesso formato di quelli esportati dall'utente).
3. Layout *insegnati dall'utente* (tabella `bill_layouts`).

Una regola dice solo dove cercare: un testo-etichetta e se il valore lo segue o lo precede. Non contiene mai
valori della bolletta, per questo si può condividere (`report`) per farla diventare un layout fornito.
Formato JSON:  {"version": 1, "name": "...", "signature": "testo che identifica il fornitore", "rules": [...]}
Regola:        {"field": "total_eur", "kind": "number", "anchor": "Totale da pagare", "side": "before", "index": 0}
               {"field": "commodity", "kind": "keyword", "anchor": "ENERGIA ELETTRICA", "value": "power"}"""
from __future__ import annotations

import dataclasses
import json
import re
import typing
from dataclasses import dataclass, field
from pathlib import Path

from ..models import SYSTEM_FIELDS, Bill
from .bill_parser import MONTHS, NUM, num

VERSION = 1
BUILTIN_DIR = Path(__file__).resolve().parent.parent / "layouts"
MAX_ANCHOR = 60  # un'etichetta più lunga è quasi certamente testo libero, non un'etichetta
WINDOW = 100  # caratteri in cui cercare il valore accanto all'etichetta
NOT_TEACHABLE = SYSTEM_FIELDS | {"pdf_path"}

_MONTH = "|".join(MONTHS)
# i valori sono «token» isolati: "F1" o "2026-06" non contano come numeri dentro un'etichetta
_EDGE_L, _EDGE_R = r"(?<![\w.,/-])", r"(?![\w/])(?![.,]\d)"
VALUE_RE = {
    "number": re.compile(_EDGE_L + NUM + _EDGE_R),
    "date": re.compile(
        _EDGE_L + r"(?:(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})|(\d{1,2})\s+(" + _MONTH + r")\s+(\d{4}))" + _EDGE_R, re.I
    ),
}
# etichette sospette: sequenze lunghe di cifre, e-mail, codici tipo IBAN/POD/CF
_PERSONAL = re.compile(r"\d{3,}|@|\b[A-Z]{2}\d{2}[A-Z0-9]{8,}|\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b|\bIT\d{3}[A-Z]\w{6,}", re.I)


@dataclass(frozen=True)
class Rule:
    field: str
    kind: str  # number | date | keyword | text
    anchor: str
    side: str = "before"  # il valore sta dopo (before) o prima (after) l'etichetta
    index: int = 0  # quale valore accanto all'etichetta (0 = il più vicino)
    value: str | None = None  # solo keyword: il valore del campo quando il testo compare

    def to_dict(self) -> dict:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict) -> Rule:
        return cls(d["field"], d["kind"], d["anchor"], d.get("side", "before"), int(d.get("index", 0)), d.get("value"))


@dataclass
class Layout:
    name: str
    signature: str
    rules: list[Rule] = field(default_factory=list)
    id: int | None = None
    builtin: bool = False

    def matches(self, text: str) -> bool:
        return self.signature.casefold() in text.casefold()

    def to_json(self) -> str:
        return json.dumps({"version": VERSION, "name": self.name, "signature": self.signature,
                           "rules": [r.to_dict() for r in self.rules]}, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, raw: str, **extra) -> Layout:
        d = json.loads(raw)
        if d.get("version") != VERSION:
            raise ValueError("versione del layout non supportata")
        return cls(d["name"], d["signature"], [Rule.from_dict(r) for r in d["rules"]], **extra)


def builtin_layouts() -> list[Layout]:
    """Layout in `app/layouts/*.json`. Un file non valido viene ignorato: non deve bloccare la lettura delle bollette."""
    out = []
    for path in sorted(BUILTIN_DIR.glob("*.json")):
        try:
            out.append(Layout.from_json(path.read_text(encoding="utf-8"), builtin=True))
        except (ValueError, KeyError, TypeError):
            continue
    return out


# --- campi insegnabili -------------------------------------------------------------------------

def teachable_fields() -> dict[str, str]:
    """Campo di `Bill` → tipo di regola. Deriva dai type hint, quindi un campo nuovo è insegnabile senza altro codice."""
    hints = typing.get_type_hints(Bill)
    kinds = {}
    for f in dataclasses.fields(Bill):
        if f.name in NOT_TEACHABLE:
            continue
        if f.metadata.get("choices"):
            kinds[f.name] = "keyword"
        elif f.name.endswith(("_on", "_start", "_end")):
            kinds[f.name] = "date"
        elif float in typing.get_args(hints[f.name]):
            kinds[f.name] = "number"
        else:
            kinds[f.name] = "text"
    return kinds


def choices(field_name: str) -> tuple[str, ...]:
    f = next(f for f in dataclasses.fields(Bill) if f.name == field_name)
    return tuple(f.metadata.get("choices", ()))


# --- applicare le regole -----------------------------------------------------------------------

def _anchor_re(anchor: str) -> re.Pattern:
    return re.compile(r"\s+".join(re.escape(t) for t in anchor.split()), re.I)


def _convert(kind: str, m: re.Match) -> str | float | None:
    if kind == "number":
        return num(m.group(1))
    g = m.groups()
    if g[0]:
        d, mo, y = int(g[0]), int(g[1]), int(g[2])
    else:
        d, mo, y = int(g[3]), MONTHS[g[4].lower()], int(g[5])
    return f"{y}-{mo:02d}-{d:02d}" if 1 <= d <= 31 and 1 <= mo <= 12 else None


def apply_rule(rule: Rule, text: str) -> str | float | None:
    anchor = _anchor_re(rule.anchor).search(text)
    if not anchor:
        return None
    if rule.kind == "keyword":
        return rule.value
    if rule.kind == "text":  # il resto della riga dopo l'etichetta
        rest = text[anchor.end():].split("\n", 1)[0].strip(" :")
        return rest or None
    pattern = VALUE_RE[rule.kind]
    if rule.side == "before":
        found = list(pattern.finditer(text[anchor.end(): anchor.end() + WINDOW]))
    else:
        found = list(pattern.finditer(text[max(0, anchor.start() - WINDOW): anchor.start()]))[::-1]
    return _convert(rule.kind, found[rule.index]) if rule.index < len(found) else None


def apply_layouts(text: str, fields: dict, layouts: list[Layout]) -> tuple[dict, list[str]]:
    """Completa `fields` con i layout il cui fornitore compare nel testo; non sovrascrive mai un campo già letto.
    Restituisce (campi, nomi dei layout usati)."""
    out, used = dict(fields), []
    for layout in layouts:
        if not layout.matches(text):
            continue
        added = False
        for rule in layout.rules:
            if rule.field in out:
                continue
            value = apply_rule(rule, text)
            if value is not None:
                out[rule.field], added = value, True
        if added:
            used.append(layout.name)
    if out.get("period_start") and out.get("period_end") and out["period_start"] > out["period_end"]:
        out.pop("period_start"), out.pop("period_end")  # date incoerenti: meglio chiederle che salvarle sbagliate
    return out, used


# --- imparare una regola da un esempio ---------------------------------------------------------

def _values_free(segment: str, kind: str) -> tuple[str, int]:
    """Taglia il segmento al primo valore (numero/data) e dice quanti valori seguono: l'etichetta non deve contenerne."""
    pattern = VALUE_RE.get(kind, VALUE_RE["number"])
    found = list(pattern.finditer(segment))
    return (segment[: found[0].start()] if found else segment), len(found)


def _clean(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip(" :-–|")


def _good_anchor(label: str) -> bool:
    return len(re.findall(r"[^\W\d_]", label)) >= 3 and len(label) <= MAX_ANCHOR and not _PERSONAL.search(label)


def _candidates(text: str, start: int, end: int, kind: str):
    """Possibili (etichetta, lato, indice) intorno al valore in text[start:end], dal più vicino al più lontano."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end < 0 else line_end
    lines_before = [ln for ln in text[:line_start].split("\n") if ln.strip()]
    lines_after = [ln for ln in text[line_end:].split("\n") if ln.strip()]

    before_same = text[line_start:start]
    label, _ = _values_free(before_same, kind)
    yield _clean(label), "before", len(VALUE_RE.get(kind, VALUE_RE["number"]).findall(before_same[len(label):]))
    if lines_before:  # etichetta sulla riga sopra
        yield _clean(lines_before[-1]), "before", 0
    after_same = text[end:line_end]
    yield _clean(_values_free(after_same.lstrip(), kind)[0] if kind != "text" else after_same), "after", 0
    if lines_after:  # etichetta sulla riga sotto
        yield _clean(lines_after[0]), "after", 0


def learn_rule(text: str, field_name: str, sample: str, choice: str | None = None) -> Rule:
    """Ricava la regola che, applicata a `text`, restituisce di nuovo `sample`. ValueError con il motivo se non ci riesce."""
    kind = teachable_fields().get(field_name)
    sample = sample.strip()
    if kind is None or not sample:
        raise ValueError("campo non valido o valore vuoto")
    if kind == "keyword":
        if choice not in choices(field_name):
            raise ValueError("scegli a quale valore corrisponde il testo")
        if not (_anchor_re(sample).search(text) and _good_anchor(sample)):
            raise ValueError("questo testo non compare nella bolletta (o non è un'etichetta generica)")
        return Rule(field_name, "keyword", _clean(sample), value=choice)
    target = _convert(kind, m) if kind != "text" and (m := VALUE_RE[kind].fullmatch(sample)) else None
    if kind == "text":
        target = sample
    elif target is None:
        raise ValueError("il valore non ha il formato atteso (numero con virgola, o data come 01/06/2026)")
    rejected = "l'etichetta accanto al valore contiene dati personali o è troppo lunga"
    tried = False
    for m in re.finditer(re.escape(sample), text):
        for label, side, index in _candidates(text, m.start(), m.end(), kind):
            if not _good_anchor(label):
                continue
            rule = Rule(field_name, kind, label, side, index)
            tried = True
            if apply_rule(rule, text) == target:
                return rule
            rejected = "l'etichetta accanto al valore compare più volte con valori diversi"
    raise ValueError(rejected if tried or re.search(re.escape(sample), text) else "il valore non compare nel testo della bolletta")


def learn_layout(text: str, name: str, signature: str, samples: dict[str, tuple[str, str | None]]) -> tuple[Layout, dict[str, str]]:
    """`samples`: campo → (testo di esempio, valore scelto per i campi a scelta). Restituisce (layout, errori per campo)."""
    if signature.casefold() not in text.casefold() or not signature.strip():
        raise ValueError("il nome del fornitore deve comparire nel testo della bolletta")
    rules, errors = [], {}
    for name_, (sample, choice) in samples.items():
        if not sample.strip():
            continue
        try:
            rules.append(learn_rule(text, name_, sample, choice))
        except ValueError as e:
            errors[name_] = str(e)
    return Layout(name.strip() or signature.strip(), signature.strip(), rules), errors


# --- condividere un layout senza dati personali --------------------------------------------------

def report(layout: Layout) -> tuple[str, list[str]]:
    """JSON da condividere (solo etichette e formati, mai valori) e le regole escluse perché sospette."""
    safe, dropped = [], []
    for rule in layout.rules:
        if _good_anchor(rule.anchor):
            safe.append(rule)
        else:
            dropped.append(rule.field)
    return Layout(layout.name, layout.signature, safe).to_json(), dropped
