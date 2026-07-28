"""π(s): der fehlende Builder. Text → Verteilung über einen Relationsraum, per LLM.

Der SPL (Alexandria-Semantic-Projection-Layer) enthält den Formalismus ganz - ``compute_jsd``,
``compute_h_norm``, die Emissionsregeln E0-E4, das Gateway. Was ihm fehlt, ist π(s): jede ``P_r`` im
gesamten Repo ist ein handgeschriebenes Literal in ``test_app.py``. Der einzige existierende Builder
(AleXionas ``clinical_spl._build_P_r``) baut die Verteilung *deterministisch aus zwei Skalaren*
(``claim_type``, ``ess``), die das LLM vorher gemeldet hat - die "Entropie" ist dort eine reine
Funktion von ``ess`` und misst nicht den Text, sondern die Selbsteinschätzung des Extraktors.

Dieser Builder macht es so, wie die Architektur es vorsieht: **das LLM projiziert Sprache, die
Regeln entscheiden.** Das Modell bekommt einen *geschlossenen, versionierten* Relationsraum
und verteilt Wahrscheinlichkeitsmasse darüber. Es entscheidet nichts - Emission, Schwellen
und Verdikt bleiben deterministisch im SPL.

Zwei Eigenschaften machen das erst zu einer Messung:

**Echte Builder-Unabhängigkeit.** alpha und beta sind *verschiedene Modelle* (deepseek-v4-pro und
-flash), nicht zweimal dasselbe mit anderer Temperatur. Nur dann heisst JSD(alpha, beta) etwas: sie
misst, wie weit zwei unabhängige Sprachverarbeiter über die Bedeutung desselben Satzes auseinander
liegen. Genau das ist E4 (BRANCH_CANDIDATE) - Mehrdeutigkeit statt vorschneller Festlegung.

**Illegale Masse wird gemessen, nicht weggeworfen.** Verteilt ein Builder Masse auf Relationen
ausserhalb des Raums, wird dieser Anteil als ``p_illegal`` geführt und speist E0 (strukturelle
Zurückweisung), statt still normalisiert zu werden. Ein Builder, der am Raum vorbeiredet, muss
auffallen.

Der Relationsraum ist bewusst allgemein (nicht klinisch) und gehasht, damit die Matrixversion
identifizierbar bleibt - der SPL führt einen ``matrix_seal_hash`` mit.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DEFAULT_SPL = _HERE.parents[2] / "Alexandria-Semantic-Projection-Layer_repo"
for _p in (os.getenv("SPL_ROOT", str(_DEFAULT_SPL)),):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

from spl import (  # noqa: E402
    EmissionEngine,
    SemanticProjection,
    SemanticUnit,
    SPLThresholds,
    compute_h_norm,
    compute_jsd,
)

ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

#: Der geschlossene Relationsraum ℛ. Allgemein gehalten - er muss jede Aussage aufnehmen können,
#: die ein Agent oder ein Paper über die Welt macht, ohne auf eine Domäne festgelegt zu sein.
RELATIONS: tuple[str, ...] = (
    "causes",            # A bewirkt B
    "prevents",          # A verhindert B
    "correlates_with",   # A geht mit B einher, ohne Wirkrichtung
    "is_a",              # Taxonomie / Klassenzugehörigkeit
    "part_of",           # Meronymie / Enthaltensein
    "has_property",      # A trägt Eigenschaft B
    "requires",          # A setzt B voraus
    "enables",           # A ermöglicht B
    "contradicts",       # A widerspricht B
    "supports",          # A stützt B als Evidenz
    "measured_as",       # A wird durch B quantifiziert
    "recommends",        # normativ: A empfiehlt B  (Handlungsanweisung!)
)

MATRIX_VERSION = "v1.0.0-GENERAL"
MATRIX_SEAL = hashlib.sha256(("|".join(RELATIONS) + MATRIX_VERSION).encode()).hexdigest()[:16]

BUILDERS = {"alpha": "deepseek-v4-pro", "beta": "deepseek-v4-flash"}

# Erste Fassung fragte das Modell direkt nach einer Verteilung ("verteile Masse über den Raum").
# Ergebnis über alle Testsätze: H_norm = 0.000, ausnahmslos - auch bei "Entropy increases in the
# system", dem kanonisch mehrdeutigen Fall. Ein LLM nach seinen eigenen Wahrscheinlichkeiten zu
# fragen liefert einen One-Hot-Vektor: es WÄHLT die beste Antwort, es introspektiert keine
# Verteilung. Damit war der Entropiekanal tot - derselbe Defekt wie in clinical_spl, nur auf
# anderem Weg erreicht.
#
# Diese Fassung fragt deshalb nach EINER Relation und gewinnt die Verteilung aus dem
# Stichprobenverhalten: N Ziehungen bei Temperatur > 0, P_r = empirische Häufigkeit. Die Verteilung
# entsteht dann aus dem, was das Modell TUT, nicht aus dem, was es über sich behauptet - und H_norm
# misst wieder echte Unsicherheit über die Bedeutung.
_SYSTEM = """You are a semantic projector. You do not judge, decide, or verify anything.

Given ONE statement, name the SINGLE relation from the closed space below that the statement
asserts between its subject and object. Project MEANING, not confidence.

CLOSED RELATION SPACE (use exactly one of these keys):
{relations}

Return JSON exactly:
{{"relation": "<one key>", "subjects": ["..."], "objects": ["..."]}}

If the statement tells someone what to DO rather than what IS, the relation is "recommends"."""


def _call(model: str, text: str, *, temperature: float) -> dict:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY fehlt")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM.format(relations="\n".join(f"  - {r}"
                                                                             for r in RELATIONS))},
            {"role": "user", "content": text},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:      # noqa: S310 - fixed https endpoint
        payload = json.loads(r.read())
    return json.loads(payload["choices"][0]["message"]["content"])


N_SAMPLES = 7           # Ziehungen je Builder; P_r ist ihre empirische Häufigkeit
SAMPLE_TEMP = 1.0


def project(text: str, builder: str, *, n: int = N_SAMPLES,
            temperature: float = SAMPLE_TEMP) -> SemanticProjection:
    """π(s) für einen Builder: n Ziehungen, P_r = empirische Häufigkeit der gewählten Relation.

    Masse auf Relationen ausserhalb des Raums wird als ``p_illegal`` GEMESSEN (speist E0), nicht
    still verworfen - ein Builder, der am Raum vorbeiredet, muss auffallen."""
    def _draw(_i):
        try:
            return _call(BUILDERS[builder], text, temperature=temperature)
        except Exception:  # noqa: BLE001 - eine misslungene Ziehung ist Datum, kein Absturz
            return None

    with ThreadPoolExecutor(max_workers=min(n, 8)) as pool:
        draws = [d for d in pool.map(_draw, range(n)) if d is not None]

    picks: list[str] = []
    illegal = 0
    subjects: list[str] = []
    objects: list[str] = []
    for raw in draws:
        rel = str(raw.get("relation", "")).strip()
        if rel in RELATIONS:
            picks.append(rel)
        else:
            illegal += 1
        subjects += [str(s) for s in (raw.get("subjects") or [])][:2]
        objects += [str(o) for o in (raw.get("objects") or [])][:2]
    drawn = len(picks) + illegal
    p_illegal = (illegal / drawn) if drawn else 1.0
    P_r = {r: picks.count(r) / len(picks) for r in dict.fromkeys(picks)} if picks else {}
    raw = {"subjects": list(dict.fromkeys(subjects)), "objects": list(dict.fromkeys(objects))}
    unit = SemanticUnit.new(source_text=text, source_ref="spl-builder")
    proj = SemanticProjection(
        projection_id=str(uuid.uuid4()), unit_id=unit.unit_id, builder_origin=builder,
        matrix_version=MATRIX_VERSION, P_r=P_r,
        subject_candidates=[str(s) for s in (raw.get("subjects") or [])][:4],
        object_candidates=[str(o) for o in (raw.get("objects") or [])][:4],
        p_illegal=round(p_illegal, 4), matrix_seal_hash=MATRIX_SEAL)
    proj.h_norm = compute_h_norm(P_r) if P_r else 1.0
    return proj


def measure(text: str, *, thresholds: SPLThresholds | None = None) -> dict:
    """Volle Kette für einen Satz: zwei unabhängige Builder → JSD → E0-E4. Ab π deterministisch."""
    engine = EmissionEngine(thresholds)
    a = project(text, "alpha")
    b = project(text, "beta")
    # Reihenfolge ist wesentlich: emit() setzt status/rule über E0-E3 und würde ein zuvor gesetztes
    # BRANCH_CANDIDATE überschreiben. Erst emittieren, dann E4 - die Builder-Divergenz ist das
    # übergeordnete Urteil: uneinige Builder heissen Verzweigung, nicht fertiger Claim.
    cands = engine.emit(a)
    jsd = engine.apply_e4(a, b)                    # setzt BRANCH_CANDIDATE, wenn JSD > τ₄
    if a.emission_rule and a.emission_rule.value == "E4":
        cands = []                                 # verzweigt statt emittiert
    return {
        "text": text,
        "alpha": {"P_r": a.P_r, "h_norm": round(a.h_norm, 4), "p_illegal": a.p_illegal},
        "beta": {"P_r": b.P_r, "h_norm": round(b.h_norm, 4), "p_illegal": b.p_illegal},
        "jsd": round(jsd, 4),
        "status": a.status.value,
        "rule": a.emission_rule.value if a.emission_rule else None,
        "candidates": len(cands),
        "dominant_alpha": max(a.P_r, key=a.P_r.get) if a.P_r else None,
        "dominant_beta": max(b.P_r, key=b.P_r.get) if b.P_r else None,
    }


__all__ = ["RELATIONS", "MATRIX_VERSION", "MATRIX_SEAL", "BUILDERS", "project", "measure",
           "compute_jsd"]
