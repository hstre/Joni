"""Weltwissens-Adapter: Wikidata + PubMed. Liefert **Zitate für Lücken**, keine Wahrheitsurteile.

Der Auditor scheitert an Prämissen, die niemand ausspricht — „39,1 °C ist Fieber", „96 mg/L CRP ist
erhöht". Der naheliegende Reflex ist, sie nachzuschlagen und einzusetzen. **Das wäre falsch**, und
eine Messung hat gezeigt warum:

* Wikidata `Q38933` („fever") hat 65 Eigenschaften und **null mit einem Zahlenwert**. Kein
  Schwellwert, keine Temperatur.
* PubMed liefert stattdessen PMID 33735515 — *„Threshold for defining fever varies with age,
  especially in children"*. **Es gibt keinen festen Schwellwert.**

Die Prämisse ist also keine abrufbare Tatsache, sondern eine kontextabhängige Konvention. Daraus
folgt die Aufgabe dieses Moduls: nicht die Lücke *füllen*, sondern sie **benennbar und zitierbar**
machen. Ein Auditor, der sagt

    missing_premise: erfordert die Konvention, dass ≥38 °C als Fieber gilt
                     — alters- und kontextabhängig (PMID 33735515)

ist ehrlicher und nützlicher als einer, der `entailed` behauptet.

**Die tragende Regel, strukturell und nicht bloss dokumentiert: kein Treffer ist keine
Widerlegung.** Es gibt in diesem Modul keinen Rückgabewert, der Abwesenheit in eine negative
Aussage übersetzt. ``found=False`` heisst *„hier steht nichts dazu"*, niemals *„es ist falsch"* —
und ``Evidence.refutes`` existiert nicht.

Zwei Quellen, beide **frei und ohne Zugangsdaten** (beide getestet):

* **Wikidata** — strukturierte Entitäts-Attribut-Fakten, mit Referenzen. Stark bei „Einstein wurde
  in Ulm geboren" (P19 → Q3012, 4 Referenzen).
* **PubMed** — Literatur. Stark dort, wo eine Konvention *umstritten* ist und man das belegen will.

Nicht enthalten: UMLS und SNOMED CT. Beide verlangen Lizenzvereinbarungen; ausserdem ist SNOMED
eine Terminologie und kodiert keine numerischen Referenzbereiche — für Schwellwerte vermutlich die
falsche Quelle. Erst messen, ob die freien Schichten tragen.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_UA = "DESi-research/0.1 (epistemic governance prototype; contact via repo)"
_TIMEOUT = 30

WIKIDATA_REST = "https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

#: Wie gut eine Aussage belegt ist. Wikidata-Aussagen schwanken stark - manche tragen Referenzen
#: und Zeitqualifikatoren, andere gar nichts. Das muss sichtbar bleiben.
CONFIDENCE_CLASSES = (
    "structured_referenced",      # Wikidata-Aussage MIT Referenzen
    "structured_unreferenced",    # Wikidata-Aussage OHNE Referenzen
    "literature_reference",       # PubMed-Fundstelle
)


@dataclass(frozen=True)
class Evidence:
    """Ein normalisiertes Evidenzobjekt. Beschreibt einen FUND, nie ein Urteil."""

    source_system: str
    statement: str
    confidence_class: str
    retrieved_at: str
    entity_id: str = ""
    property_id: str = ""
    value: str = ""
    external_id: str = ""                      # PMID, DOI …
    url: str = ""
    source_references: tuple[str, ...] = field(default_factory=tuple)
    qualifiers: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {"source_system": self.source_system, "statement": self.statement,
                "value": self.value, "entity_id": self.entity_id,
                "property_id": self.property_id, "external_id": self.external_id,
                "url": self.url, "retrieved_at": self.retrieved_at,
                "source_references": list(self.source_references),
                "qualifiers": list(self.qualifiers),
                "confidence_class": self.confidence_class}


@dataclass(frozen=True)
class Lookup:
    """Das Ergebnis einer Abfrage.

    ``found=False`` bedeutet **ausschliesslich**: in dieser Quelle steht dazu nichts. Es ist keine
    Aussage über die Welt und darf niemals als Widerlegung gelesen werden. Deshalb gibt es hier
    auch kein Feld, das eine solche Lesart erlauben würde."""

    query: str
    found: bool
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    ambiguous_candidates: tuple[dict, ...] = field(default_factory=tuple)
    note: str = ""

    #: Explizit und maschinenlesbar, damit kein Aufrufer es „vergisst".
    absence_is_not_refutation: bool = True

    def to_dict(self) -> dict:
        return {"query": self.query, "found": self.found,
                "evidence": [e.to_dict() for e in self.evidence],
                "ambiguous_candidates": list(self.ambiguous_candidates),
                "note": self.note,
                "absence_is_not_refutation": True}


# ── Cache ───────────────────────────────────────────────────────────────────────────────────────

class Cache:
    """Persistenter Cache (SQLite, stdlib). Zweck ist nicht nur Sparsamkeit, sondern
    **Reproduzierbarkeit**: eine Auditor-Messung soll beim zweiten Lauf dieselben Belege sehen."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path(__file__).with_name("world_knowledge_cache.sqlite")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self.path))
        self._con.execute("CREATE TABLE IF NOT EXISTS kv "
                          "(k TEXT PRIMARY KEY, v TEXT NOT NULL, at TEXT NOT NULL)")
        self._con.commit()

    def get(self, key: str) -> dict | None:
        row = self._con.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: dict) -> None:
        self._con.execute("INSERT OR REPLACE INTO kv VALUES (?,?,?)",
                          (key, json.dumps(value, ensure_ascii=False), _now()))
        self._con.commit()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:   # noqa: S310 - feste Hosts
        return json.loads(r.read())


# ── Wikidata ────────────────────────────────────────────────────────────────────────────────────

def resolve_entity(text: str, *, language: str = "en", cache: Cache | None = None) -> Lookup:
    """Text → Wikidata-Entität. Mehrdeutigkeit wird GEMELDET, nicht stillschweigend aufgelöst.

    Die Suche nach „fever" liefert als ersten Treffer ein Mixtape von Megan Thee Stallion. Ein
    falsch aufgelöstes Q-Item erzeugt perfekt formatierte, perfekt falsche Evidenz - deshalb gibt
    diese Funktion bei uneindeutigem Feld **alle** Kandidaten zurück und wählt nicht selbst.
    """
    cache = cache or Cache()
    key = f"wd:resolve:{language}:{text.lower()}"
    hit = cache.get(key)
    if hit is None:
        url = WIKIDATA_API + "?" + urllib.parse.urlencode(
            {"action": "wbsearchentities", "search": text, "language": language,
             "format": "json", "limit": 5})
        try:
            hit = _get_json(url)
        except Exception as exc:  # noqa: BLE001
            return Lookup(query=text, found=False, note=f"Quelle nicht erreichbar: {exc!s:.80}")
        cache.put(key, hit)
    cands = [{"id": r["id"], "label": r.get("label", ""),
              "description": r.get("description", "")} for r in hit.get("search", [])]
    if not cands:
        return Lookup(query=text, found=False, note="keine Entität gefunden")
    return Lookup(query=text, found=True, ambiguous_candidates=tuple(cands),
                  note=("mehrdeutig - der Aufrufer muss wählen" if len(cands) > 1
                        else "eindeutig"))


def get_claims(entity_id: str, *, properties: list[str] | None = None,
               cache: Cache | None = None) -> Lookup:
    """Alle (oder ausgewählte) Aussagen einer Entität, als Evidenzobjekte mit Provenienz."""
    cache = cache or Cache()
    key = f"wd:claims:{entity_id}"
    hit = cache.get(key)
    if hit is None:
        try:
            hit = _get_json(f"{WIKIDATA_REST}/{entity_id}/statements")
        except Exception as exc:  # noqa: BLE001
            return Lookup(query=entity_id, found=False,
                          note=f"Quelle nicht erreichbar: {exc!s:.80}")
        cache.put(key, hit)
    out: list[Evidence] = []
    for pid, statements in hit.items():
        if properties and pid not in properties:
            continue
        for st in statements:
            content = (st.get("value") or {}).get("content")
            refs = st.get("references") or []
            quals = st.get("qualifiers") or []
            out.append(Evidence(
                source_system="Wikidata",
                statement=f"{entity_id} {pid} {content}",
                value=str(content), entity_id=entity_id, property_id=pid,
                url=f"https://www.wikidata.org/wiki/{entity_id}#{pid}",
                retrieved_at=_now(),
                source_references=tuple(str(r.get("hash", ""))[:16] for r in refs),
                qualifiers=tuple(sorted({q.get("property", {}).get("id", "") for q in quals})),
                confidence_class=("structured_referenced" if refs
                                  else "structured_unreferenced")))
    return Lookup(query=entity_id, found=bool(out), evidence=tuple(out),
                  note="" if out else "Entität existiert, aber keine passende Aussage")


# ── PubMed ──────────────────────────────────────────────────────────────────────────────────────

_STOP_Q_TEXT = """the a an of in on for and or to with from by is are was were be been
that this these those it its as at not no varies vary define definition threshold"""
_STOP_Q = frozenset(_STOP_Q_TEXT.split())


def _substantive(q: str) -> set[str]:
    return {w.strip(".,;:()").lower() for w in q.split()
            if len(w.strip(".,;:()")) > 4 and w.strip(".,;:()").lower() not in _STOP_Q}


def _is_on_topic(query: str, title: str) -> bool:
    """Teilt die Fundstelle ueberhaupt einen inhaltlichen Begriff mit der Anfrage?

    PubMed zerlegt Anfragen und faellt auf einzelne haeufige Woerter zurueck: die Suche nach
    "xyzzy nonexistent quux flurble" lieferte drei Arbeiten zu Wissensgraphen und Aspirin-
    Reaktivitaet - weil "nonexistent" in Abstracts vorkommt. Eine irrelevante Zitatstelle an eine
    Praemisse zu heften ist SCHLIMMER als gar keine, weil es wie Fundierung aussieht.

    Die Pruefung ist bewusst streng: eine verworfene schwache Fundstelle kostet einen moeglichen
    Beleg, eine behaltene falsche erzeugt Scheinbelege. Asymmetrische Kosten, also strenge Seite.
    """
    qs = _substantive(query)
    if not qs:
        return True                      # nichts zu pruefen - dann nicht kuenstlich verwerfen
    ts = {w.strip(".,;:()").lower() for w in title.split()}
    return bool(qs & ts)


def find_literature(query: str, *, limit: int = 3, cache: Cache | None = None) -> Lookup:
    """Literatur zu einer Frage - besonders dort, wo eine Konvention UMSTRITTEN ist.

    Genau dafür ist die Quelle hier: nicht um einen Schwellwert zu liefern, sondern um belegen zu
    können, dass es keinen festen gibt.
    """
    cache = cache or Cache()
    key = f"pm:{limit}:{query.lower()}"
    hit = cache.get(key)
    if hit is None:
        try:
            search = _get_json(PUBMED + "/esearch.fcgi?" + urllib.parse.urlencode(
                {"db": "pubmed", "term": query, "retmax": limit, "retmode": "json",
                 "sort": "relevance"}))
            ids = (search.get("esearchresult") or {}).get("idlist") or []
            hit = {"ids": ids}
            if ids:
                hit["summary"] = _get_json(PUBMED + "/esummary.fcgi?" + urllib.parse.urlencode(
                    {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}))
        except Exception as exc:  # noqa: BLE001
            return Lookup(query=query, found=False, note=f"Quelle nicht erreichbar: {exc!s:.80}")
        cache.put(key, hit)
    result = (hit.get("summary") or {}).get("result") or {}
    all_hits = [(pmid, v) for pmid, v in result.items() if pmid != "uids"]
    on_topic = [(pmid, v) for pmid, v in all_hits if _is_on_topic(query, v.get("title", ""))]
    dropped = len(all_hits) - len(on_topic)
    out = [Evidence(
        source_system="PubMed", statement=v.get("title", ""), external_id=pmid,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", retrieved_at=_now(),
        qualifiers=(v.get("fulljournalname", ""), str(v.get("pubdate", ""))),
        confidence_class="literature_reference")
        for pmid, v in on_topic]
    if out:
        note = f"{dropped} Fundstelle(n) ohne inhaltlichen Bezug verworfen" if dropped else ""
    else:
        note = ("keine Fundstelle mit inhaltlichem Bezug - das ist KEINE Widerlegung"
                if all_hits else "keine Fundstelle - das ist KEINE Widerlegung")
    return Lookup(query=query, found=bool(out), evidence=tuple(out), note=note)


def premise_evidence(premise: str, *, cache: Cache | None = None) -> Lookup:
    """Die Funktion, für die dieses Modul existiert: Belege **zur Lücke**, nicht deren Füllung.

    Gibt Fundstellen zurück, die die unausgesprochene Prämisse betreffen - damit der Auditor sie
    zitierbar benennen kann. Sie beantwortet ausdrücklich **nicht**, ob die Prämisse zutrifft.
    """
    lit = find_literature(premise, cache=cache)
    note = ("Belege ZUR PRÄMISSE - kein Urteil über ihre Gültigkeit"
            if lit.found else "keine Fundstelle; die Prämisse bleibt unbelegt, nicht widerlegt")
    return Lookup(query=premise, found=lit.found, evidence=lit.evidence, note=note)


__all__ = ["Evidence", "Lookup", "Cache", "resolve_entity", "get_claims", "find_literature",
           "premise_evidence", "CONFIDENCE_CLASSES"]
