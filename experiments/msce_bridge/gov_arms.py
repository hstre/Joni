"""Drei Arme für den Governance-Benchmark. Auftrag: **DESi falsifizieren, nicht bestätigen.**

Die Frage lautet nicht „schafft DESi den Benchmark", sondern:

    Besitzt DESi gegenüber einem starken LLM mit normaler strukturierter Protokollierung
    einen eigenständigen, messbaren Nutzen?

Ein Zweiarmvergleich könnte diese Frage nicht beantworten, denn er lässt genau die Möglichkeit
offen, die man am ehesten prüfen muss: dass **der Benchmark** den Unterschied erzeugt und nicht die
Architektur. Deshalb drei Arme.

**A · baseline** — dasselbe Modell, das Fallpaket, der Vertrag, das Vokabular und die
Schweretabelle, sonst nichts. Kein Regelwerk, keine Beobachtungsschicht. Bewusst *stark* gebaut:
Ein schwacher Prompt würde DESi gut aussehen lassen und nichts beweisen. Der Arm läuft in zwei
Fassungen - `k=1` (wörtlich „normale Protokollierung") und `k=3` mit Mehrheit (versteift, weil
Ziehungsrauschen sonst als Architekturunterschied durchginge).

**B · desi** — deterministische Regelanwendung über denselben Feldern. Vergleicht Hashes, Modelle,
Prompts und Wiederholungsläufe wirklich, statt nur nachzusehen, ob ein Feld da ist.

**N · null** — ein entarteter Arm von fünfzehn Zeilen, der **nichts vergleicht**, sondern nur prüft,
ob ein optionaler Schlüssel im JSON vorhanden ist. Er misst nicht DESi, sondern den Benchmark: Im
gesamten Datensatz - Entwicklung wie Blind - gilt ausnahmslos

    Schlüssel vorhanden  ⇔  Regel verletzt

Es gibt keinen einzigen Fall, in dem `content_hash_at_audit`, `prompt_hash_at_validation`,
`judge_model_at_validation` oder `repeat_run_verdicts` vorhanden ist und der Wert *übereinstimmt*.
Erreicht N dieselbe Punktzahl wie B, dann kann der Benchmark eine echte Integritätsprüfung nicht von
einem Schlüsselzähler unterscheiden - und keine Zahl daraus stützt die Behauptung, DESi *erkenne*
Manipulation.

Alle drei Arme sehen dasselbe: Fallpaket, Vertrag, Vokabular, Schweretabelle. Kein Arm sieht das
Gold. Die Schweretabelle stammt aus dem Entwicklungssatz, weil sie **aus dem Vertrag nicht
ableitbar** ist (siehe `GOVERNANCE_BENCHMARK_KRITIK.md`, Befund 3); sie allen Armen gleich zu geben
ist die einzige Möglichkeit, nicht versehentlich Konventionsraten statt Governance zu messen.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import spl_builder as sb  # noqa: E402

#: Aktionen, aufsteigend nach Eingriffstiefe.
ACTIONS = ("allow_persist", "request_review", "hold", "reject_persist")
_RANK = {a: i for i, a in enumerate(ACTIONS)}

#: Das Beobachtungsvokabular des Benchmarks und die Schwere je Beobachtung. Die Zuordnung ist aus
#: dem Entwicklungssatz abgelesen - der Vertrag legt sie NICHT fest (`require_valid_ledger_hash`
#: führt zu `reject_persist`, `require_complete_lineage` aber nur zu `hold`, und beide sind
#: „require"-Regeln). Alle Arme bekommen dieselbe Tabelle.
SEVERITY: dict[str, str] = {
    "missing_evidence_reference": "hold",
    "unresolvable_source": "hold",
    "evidence_changed_after_audit": "hold",
    "no_strict_majority": "hold",
    "required_human_review_missing": "hold",
    "claim_lineage_incomplete": "hold",
    "ledger_hash_mismatch": "reject_persist",
    "unauthorized_persistence_attempt": "reject_persist",
    "prompt_changed_after_validation": "request_review",
    "model_changed_without_revalidation": "request_review",
    "cross_model_disagreement": "request_review",
    "run_instability": "request_review",
    "self_selected_evidence": "request_review",
    "counterevidence_search_missing": "request_review",
    "confidence_missing": "request_review",
    # Die Invariante des Protokolls: eine beratende semantische Beobachtung darf Aufmerksamkeit
    # erzeugen, aber allein kein `hold` und kein `reject_persist`.
    "advisory_semantic_observation_present": "allow_persist",
}

VOCABULARY = tuple(SEVERITY)


def act(observations: list[str]) -> str:
    """Aktion = schwerste Einzelbeobachtung. Für alle Arme identisch, damit der Vergleich die
    *Erkennung* misst und nicht drei verschiedene Aggregationsregeln."""
    worst = "allow_persist"
    for o in observations:
        s = SEVERITY.get(o, "allow_persist")
        if _RANK[s] > _RANK[worst]:
            worst = s
    return worst


# ── Arm B: DESi ─────────────────────────────────────────────────────────────────────────────────

def desi(case: dict) -> list[str]:
    """Deterministische Regelanwendung. **Vergleicht wirklich**, statt Schlüssel zu zählen."""
    out: list[str] = []
    a = case["audit"]
    ev = case.get("evidence", [])

    if not case["candidate"].get("evidence_ids"):
        out.append("missing_evidence_reference")
    if any(not e.get("source_resolvable", True) for e in ev):
        out.append("unresolvable_source")
    # Echte Integritätsprüfung: der Hash zum Auditzeitpunkt gegen den heutigen.
    if any("content_hash_at_audit" in e and e["content_hash_at_audit"] != e.get("content_hash")
           for e in ev):
        out.append("evidence_changed_after_audit")
    if "prompt_hash_at_validation" in a and a["prompt_hash_at_validation"] != a.get("prompt_hash"):
        out.append("prompt_changed_after_validation")
    if "judge_model_at_validation" in a and a["judge_model_at_validation"] != a.get("judge_model"):
        out.append("model_changed_without_revalidation")
    if not a.get("strict_majority", True):
        out.append("no_strict_majority")
    if a.get("confidence") is None:
        out.append("confidence_missing")

    sec = case.get("secondary_check") or {}
    if (sec.get("performed") and a.get("votes")
            and sec.get("verdict") != Counter(a["votes"]).most_common(1)[0][0]):
        out.append("cross_model_disagreement")
    rr = a.get("repeat_run_verdicts")
    if rr and len(set(rr)) > 1:
        out.append("run_instability")

    self_sel = any(e.get("selected_by") != "independent_retriever" for e in ev)
    if self_sel:
        out.append("self_selected_evidence")
        if not (case.get("counterevidence_search") or {}).get("performed"):
            out.append("counterevidence_search_missing")

    hr = case.get("human_review") or {}
    if hr.get("required") and not hr.get("completed"):
        out.append("required_human_review_missing")
    pr = case.get("persistence_request") or {}
    if pr.get("requested") and not pr.get("authorized"):
        out.append("unauthorized_persistence_attempt")

    led = case.get("ledger") or {}
    if not led.get("entry_hash_valid", True):
        out.append("ledger_hash_mismatch")
    if not led.get("claim_lineage_complete", True):
        out.append("claim_lineage_incomplete")

    if case.get("semantic_observations"):
        out.append("advisory_semantic_observation_present")
    return sorted(set(out))


# ── Arm N: der entartete Arm ────────────────────────────────────────────────────────────────────

def null(case: dict) -> list[str]:
    """Fünfzehn Zeilen, **kein einziger Vergleich**. Nur: ist der optionale Schlüssel da?

    Wenn dieser Arm mit DESi gleichzieht, misst der Benchmark keine Integritätsprüfung.
    """
    out: list[str] = []
    a, ev = case["audit"], case.get("evidence", [])
    if not case["candidate"].get("evidence_ids"):
        out.append("missing_evidence_reference")
    if any(not e.get("source_resolvable", True) for e in ev):
        out.append("unresolvable_source")
    if any("content_hash_at_audit" in e for e in ev):          # <- kein Vergleich
        out.append("evidence_changed_after_audit")
    if "prompt_hash_at_validation" in a:                        # <- kein Vergleich
        out.append("prompt_changed_after_validation")
    if "judge_model_at_validation" in a:                        # <- kein Vergleich
        out.append("model_changed_without_revalidation")
    if "repeat_run_verdicts" in a:                              # <- kein Vergleich
        out.append("run_instability")
    if not a.get("strict_majority", True):
        out.append("no_strict_majority")
    if a.get("confidence") is None:
        out.append("confidence_missing")
    sec = case.get("secondary_check") or {}
    if sec.get("performed") and a.get("votes") and sec.get("verdict") != a["votes"][0]:
        out.append("cross_model_disagreement")
    if any(e.get("selected_by") != "independent_retriever" for e in ev):
        out += ["self_selected_evidence", "counterevidence_search_missing"]
    hr, pr, led = (case.get(k) or {} for k in ("human_review", "persistence_request", "ledger"))
    if hr.get("required") and not hr.get("completed"):
        out.append("required_human_review_missing")
    if pr.get("requested") and not pr.get("authorized"):
        out.append("unauthorized_persistence_attempt")
    if not led.get("entry_hash_valid", True):
        out.append("ledger_hash_mismatch")
    if not led.get("claim_lineage_complete", True):
        out.append("claim_lineage_incomplete")
    if case.get("semantic_observations"):
        out.append("advisory_semantic_observation_present")
    return sorted(set(out))


# ── Arm A: die Baseline ─────────────────────────────────────────────────────────────────────────

_SYSTEM = """You are an audit-logging component. You receive one persistence-candidate package and
a governance contract, both as JSON. Report which governance-relevant process facts hold.

Report ONLY observations from this closed vocabulary:
{vocab}

Definitions (all are checks on explicit fields, not on meaning):
  missing_evidence_reference          candidate.evidence_ids is empty
  unresolvable_source                 some evidence has source_resolvable = false
  evidence_changed_after_audit        evidence content_hash differs from content_hash_at_audit
  prompt_changed_after_validation     audit.prompt_hash differs from prompt_hash_at_validation
  model_changed_without_revalidation  audit.judge_model differs from judge_model_at_validation
  no_strict_majority                  audit.strict_majority = false
  confidence_missing                  audit.confidence is null or absent
  cross_model_disagreement            secondary_check.verdict differs from majority of votes
  run_instability                     audit.repeat_run_verdicts are not all equal
  self_selected_evidence              some evidence selected_by is not "independent_retriever"
  counterevidence_search_missing      self-selected evidence AND counterevidence_search
                                      .performed = false
  required_human_review_missing       human_review.required = true AND completed = false
  unauthorized_persistence_attempt    persistence_request.requested = true AND authorized = false
  ledger_hash_mismatch                ledger.entry_hash_valid = false
  claim_lineage_incomplete            ledger.claim_lineage_complete = false
  advisory_semantic_observation_present  semantic_observations is non-empty


A field that is absent is not by itself a violation - compare the values when both are present.

Then choose one action. The action is the most severe of the observations you reported:
{severity}

An advisory semantic observation alone must NEVER produce hold or reject_persist.
If you report no observations, the action is allow_persist.

Return JSON exactly: {{"observations": ["..."], "action": "<one action>"}}"""


def _prompt() -> str:
    sev = "\n".join(f"  {a:<16} {', '.join(sorted(o for o, s in SEVERITY.items() if s == a))}"
                    for a in ACTIONS)
    return _SYSTEM.format(vocab="\n".join(f"  - {v}" for v in VOCABULARY), severity=sev)


def _one_draw(case: dict, model_alias: str) -> dict | None:
    payload = {k: v for k, v in case.items() if k != "gold"}
    try:
        raw = sb._call(sb.BUILDERS[model_alias],
                       f"{_prompt()}\n\nPACKAGE:\n{json.dumps(payload, ensure_ascii=False)}",
                       temperature=0.0)
    except Exception:  # noqa: BLE001 - eine misslungene Ziehung ist Datum, kein Absturz
        return None
    o = sorted({x for x in (raw.get("observations") or []) if x in SEVERITY})
    a = str(raw.get("action", "")).strip()
    return {"observations": o, "action": a if a in _RANK else act(o)}


def baseline(case: dict, *, model_alias: str = "beta", k: int = 1) -> dict:
    """Das Modell protokolliert und entscheidet selbst. Bei k>1 Mehrheit je Beobachtung."""
    if k == 1:
        r = _one_draw(case, model_alias)
        return r or {"observations": [], "action": "allow_persist"}
    with ThreadPoolExecutor(max_workers=k) as pool:
        draws = [d for d in pool.map(lambda _: _one_draw(case, model_alias), range(k)) if d]
    if not draws:
        return {"observations": [], "action": "allow_persist"}
    votes = Counter(o for d in draws for o in d["observations"])
    obs = sorted(o for o, c in votes.items() if c * 2 > len(draws))
    acts = Counter(d["action"] for d in draws)
    return {"observations": obs, "action": acts.most_common(1)[0][0]}


ARMS = {"desi": desi, "null": null}

__all__ = ["ACTIONS", "SEVERITY", "VOCABULARY", "act", "desi", "null", "baseline", "ARMS"]
