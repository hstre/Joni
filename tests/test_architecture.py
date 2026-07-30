"""Die Architekturkarte - und die Frage, ob sie noch stimmt.

Der Zweck der Seite ist, ein Missverstaendnis frueh sichtbar zu machen: gebaut wurde, was
dasteht, nicht was jemand beschrieben hat. Diese Eigenschaft haelt aber nur, solange die Seite
tatsaechlich neu gebaut wird. Eine veraltete Karte ist schlimmer als keine - sie sieht aus wie
ein Befund und ist eine Erinnerung.

Deshalb steht die Frischepruefung hier und nicht in der CI: die Workflow-Ausloeser sind seit dem
Projektabschluss stillgelegt, ein Schritt dort wuerde nie feuern. ``pytest`` laeuft.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from joni import architecture as arch  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
DOCS = REPO / "docs"


@pytest.fixture(scope="module")
def data() -> dict:
    return arch.analyse(SRC, REPO)


# ── Die eine Eigenschaft, auf der alles beruht ──────────────────────────────────────────────────

def test_die_seite_passt_zum_quelltext(data):
    """Wenn das hier rot ist: ``python -m joni.architecture``.

    Nicht der Test ist dann falsch, sondern die Seite ist alt.
    """
    gebaut = DOCS / "architecture.json"
    assert gebaut.exists(), "Die Seite wurde nie gebaut."
    erwartet = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    assert gebaut.read_text(encoding="utf-8") == erwartet, (
        "Die Architekturseite ist nicht mehr auf dem Stand des Quelltextes. "
        "Neu bauen: python -m joni.architecture"
    )


def test_die_karte_erfindet_keine_erklaerung(data):
    """Ein Modul ohne Docstring bekommt einen leeren Text, keinen ausgedachten."""
    ohne = set(data["undocumented"])
    assert ohne, "Erwartet wurden Module ohne Docstring - sonst prueft dieser Test nichts."
    for m in data["modules"]:
        assert (m["doc"] == "") == (m["name"] in ohne)


# ── Der Importgraph: was gezaehlt wird und was nicht ────────────────────────────────────────────

def _scan(tmp: Path, files: dict[str, str]) -> dict[str, arch.Module]:
    for rel, text in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return arch.scan(tmp)


def test_relative_importe_werden_aufgeloest(tmp_path):
    mods = _scan(tmp_path, {
        "joni/__init__.py": "",
        "joni/a.py": "from .b import x\n",
        "joni/b.py": "x = 1\n",
    })
    assert mods["joni.a"].imports == {"joni.b"}


def test_relativer_import_ueber_zwei_ebenen(tmp_path):
    """``from ..x import y`` aus einem Unterpaket - die Stelle, an der eine Ebene leicht
    danebengeht und der halbe Graph still falsch wird."""
    mods = _scan(tmp_path, {
        "joni/__init__.py": "",
        "joni/x.py": "y = 1\n",
        "joni/sub/__init__.py": "",
        "joni/sub/a.py": "from ..x import y\n",
    })
    assert mods["joni.sub.a"].imports == {"joni.x"}


def test_import_auf_ein_symbol_landet_beim_modul(tmp_path):
    """``from joni.b import Ding`` zeigt auf ein Symbol, nicht auf ein Modul namens ``Ding``."""
    mods = _scan(tmp_path, {
        "joni/__init__.py": "", "joni/b.py": "class Ding: pass\n",
        "joni/a.py": "from joni.b import Ding\n",
    })
    assert mods["joni.a"].imports == {"joni.b"}


def test_verzoegerte_importe_zaehlen_als_abhaengigkeit_und_sind_markiert(tmp_path):
    """Ein Import im Funktionsrumpf ist eine echte Abhaengigkeit - meist eine, die einen
    Zyklus umgeht. Beides muss sichtbar sein."""
    mods = _scan(tmp_path, {
        "joni/__init__.py": "", "joni/b.py": "x = 1\n",
        "joni/a.py": "def f():\n    from joni.b import x\n    return x\n",
    })
    assert mods["joni.a"].imports == {"joni.b"}
    assert mods["joni.a"].deferred == {"joni.b"}


def test_fremde_pakete_sind_keine_knoten(tmp_path):
    mods = _scan(tmp_path, {"joni/__init__.py": "", "joni/a.py": "import json\nimport os.path\n"})
    assert mods["joni.a"].imports == set()
    assert mods["joni.a"].external == {"json", "os"}


def test_ein_modul_haengt_nicht_an_sich_selbst(tmp_path):
    mods = _scan(tmp_path, {"joni/__init__.py": "", "joni/a.py": "from joni import a\n"})
    assert "joni.a" not in mods["joni.a"].imports


# ── Der erste Absatz, nicht der ganze Docstring ─────────────────────────────────────────────────

def test_nur_der_erste_absatz(tmp_path):
    mods = _scan(tmp_path, {
        "joni/__init__.py": "",
        "joni/a.py": '"""Erste Zeile.\nnoch erster Absatz.\n\nZweiter Absatz.\n"""\n',
    })
    assert mods["joni.a"].doc == "Erste Zeile. noch erster Absatz."


def test_leerer_docstring_bleibt_leer(tmp_path):
    mods = _scan(tmp_path, {"joni/__init__.py": "", "joni/a.py": '"""   """\nx = 1\n'})
    assert mods["joni.a"].doc == ""


# ── Zyklen und Erreichbarkeit ───────────────────────────────────────────────────────────────────

def test_zyklus_wird_gefunden(tmp_path):
    mods = _scan(tmp_path, {
        "joni/__init__.py": "",
        "joni/a.py": "from joni import b\n",
        "joni/b.py": "def f():\n    from joni import a\n",
    })
    assert arch.cycles(mods) == [["joni.a", "joni.b"]]


def test_ohne_zyklus_keine_meldung(tmp_path):
    mods = _scan(tmp_path, {
        "joni/__init__.py": "", "joni/a.py": "from joni import b\n", "joni/b.py": "x = 1\n"})
    assert arch.cycles(mods) == []


def test_erreichbarkeit_folgt_den_kanten(tmp_path):
    mods = _scan(tmp_path, {
        "joni/__init__.py": "", "joni/a.py": "from joni import b\n", "joni/b.py": "x = 1\n",
        "joni/allein.py": "x = 1\n"})
    reach = arch.reachable(mods, ["joni.a"])
    assert reach == {"joni.a", "joni.b"}
    assert "joni.allein" not in reach


# ── Die Einstiegspunkte werden gelesen, nicht geraten ───────────────────────────────────────────

def test_einstiegspunkte_kommen_aus_pyproject_und_workflows(tmp_path):
    """Eine handgepflegte Liste haette genau den Fehler, den die Seite vermeiden soll."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n\n[project.scripts]\njoni = "joni.cli:main"\n'
        'weg = "joni.gibtsnicht:main"\n\n[tool.ruff]\nline-length = 100\n', encoding="utf-8")
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "a.yml").write_text("jobs:\n  x:\n    steps:\n"
                              "      - run: python -m joni.autonomy --once\n", encoding="utf-8")
    known = {"joni.cli", "joni.autonomy", "joni.__main__", "joni.nichtdeklariert"}
    assert arch.entry_points(tmp_path, known) == ["joni.__main__", "joni.autonomy", "joni.cli"]


def test_ruff_abschnitt_liefert_keine_einstiegspunkte(tmp_path):
    """Nur ``[project.scripts]`` zaehlt - jeder andere Abschnitt mit ``=`` waere sonst einer."""
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\njoni = "joni.cli:main"\n\n[tool.x]\nfoo = "joni.autonomy"\n',
        encoding="utf-8")
    assert arch.entry_points(tmp_path, {"joni.cli", "joni.autonomy"}) == ["joni.cli"]


def test_die_echten_einstiegspunkte_enthalten_was_mir_nicht_eingefallen_waere(data):
    """``joni-layer9-convert`` steht in pyproject.toml und waere in einer Handliste gefehlt."""
    assert "joni.layer9_v2.convert" in data["entry_points"]
    assert "joni.cli" in data["entry_points"]


# ── Die Seite selbst ────────────────────────────────────────────────────────────────────────────

def test_seite_ist_in_sich_geschlossen():
    """Kein externes Skript, kein CDN, keine Schriftart von aussen - sonst ist die Seite von
    einem fremden Dienst abhaengig, den niemand mehr betreibt, wenn es darauf ankommt."""
    h = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "<script src=" not in h
    assert "cdn." not in h
    assert "https://fonts" not in h


def test_daten_koennen_den_skriptblock_nicht_verlassen():
    """Ein ``</script>`` im Datensatz waere der einzige Weg, wie Inhalt zu Code wuerde."""
    from joni import architecture_page as page
    h = page.render({
        "modules": [{"name": "joni.x", "path": "src/joni/x.py", "group": "joni",
                     "doc": "</script><script>alert(1)</script>", "loc": 1, "imports": [],
                     "deferred": [], "external": [], "dependents": [], "fan_in": 0,
                     "fan_out": 0, "reachable": True, "in_cycle": False}],
        "groups": [{"name": "joni", "label": "Kern", "note": None, "modules": ["joni.x"],
                    "loc": 1}],
        "group_edges": [], "cycles": [], "entry_points": [], "unreachable": [],
        "undocumented": [], "joni_on_desi": [],
        "totals": {"modules": 1, "edges": 0, "loc": 1, "groups": 1},
    })
    assert "</script><script>alert(1)" not in h
    assert h.count("<script>") == 2  # nur die beiden eigenen Bloecke


def test_das_javascript_ist_syntaktisch_heil():
    """Die Seite hat keine Testumgebung. Wenigstens die Klammern muessen aufgehen."""
    h = (DOCS / "index.html").read_text(encoding="utf-8")
    js = h.split("<script>")[-1].split("</script>")[0]
    for auf, zu in "{}", "()", "[]":
        assert js.count(auf) == js.count(zu), f"unbalanciert: {auf}{zu}"


def test_die_karte_kennt_ihre_eigenen_grenzen():
    """Die Einschraenkungen stehen auf der Seite, nicht nur im Quelltext."""
    h = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "nicht ausgefuehrt" in h
    assert "importlib" in h


def test_von_hand_geschriebene_saetze_sind_als_solche_markiert(data):
    """Der eine Textteil, der vom Bau abweichen kann, muss sichtbar getrennt sein."""
    h = (DOCS / "index.html").read_text(encoding="utf-8")
    mit_note = [g for g in data["groups"] if g["note"]]
    assert mit_note
    assert h.count("class=note") == len(mit_note)
    for g in mit_note:
        assert g["note"][:40] in h


def test_gruppen_ohne_einordnung_bekommen_keinen_erfundenen_satz(data):
    ohne = [g for g in data["groups"] if not g["note"]]
    assert ohne, "Erwartet wurden Gruppen ohne Einordnung."


# ── Was die Karte ueber dieses Repository sagt ──────────────────────────────────────────────────

def test_jedes_modul_ist_genau_einer_gruppe_zugeordnet(data):
    aus_gruppen = [n for g in data["groups"] for n in g["modules"]]
    assert sorted(aus_gruppen) == sorted(m["name"] for m in data["modules"])
    assert len(aus_gruppen) == len(set(aus_gruppen))


def test_kanten_sind_beidseitig_konsistent(data):
    """Wenn A von B abhaengt, muss B A als abhaengig kennen - sonst zeigt die Seite zwei
    verschiedene Graphen an, je nachdem von welcher Seite man schaut."""
    by = {m["name"]: m for m in data["modules"]}
    for m in data["modules"]:
        for dep in m["imports"]:
            assert m["name"] in by[dep]["dependents"], f"{m['name']} -> {dep} fehlt rueckwaerts"


def test_der_eingebettete_desi_kern_ist_die_teuerste_stelle(data):
    """Kein Stimmungsbild: der Kern hat den hoechsten Fan-in im ganzen Repository."""
    by = {m["name"]: m for m in data["modules"]}
    spitze = max(data["modules"], key=lambda m: m["fan_in"])
    assert spitze["name"] == "desi_layer9"
    assert by["desi_layer9"]["fan_in"] > 30
    assert len(data["joni_on_desi"]) > 30
