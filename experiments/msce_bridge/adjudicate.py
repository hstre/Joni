"""Prototype: a READ-ONLY DESi adjudication interface for MSCE's L2→L3 consolidation boundary.

Not part of Joni's autonomous loop. This is an experiment that answers one question before anyone
promises anything: **does DESi produce a meaningful verdict on a real MSCE L3 candidate, or does it
just return `insufficient-semantic-evidence`?**

MSCE (arXiv 2607.16621, code in MemTensor/MemOS ``apps/memos-local-plugin``) consolidates:

    L1 traces → L2 policies  f²=(φ,π,κ,ℬ,{f¹})  → L3 world model  f³=(ℰ,ℐ,𝒞,{f²})

The L3 step admits a cohort of L2 policies by embedding-centroid similarity (θ_sim = 0.62), hands it
to an LLM prompt, and stores the result. The post-LLM check (``core/memory/l3/abstract.ts``) checks
that ``title`` is a non-empty string and that ``environment`` / ``inference`` / ``constraints`` are
arrays. Nothing checks whether an entry is supported by the evidence it cites, whether it cites any,
or whether it contradicts what is already stored.

That is exactly the gap the MSCE team named in writing: *"Cross-episode recurrence can reduce
accidental correlations, but it cannot establish that an inferred environmental fact or regularity
is causally correct."*

**The mapping this prototype rests on.** Layer 9 already has a stage for "cheap recurrence found the
members": ``LEXICAL_CANDIDATE``. Its governing rule is that such a cluster may NOT feed a synthesis
until it has been semantically measured. A θ_sim cohort is precisely a lexical/embedding candidate,
and MSCE goes cohort → LLM → stored L3 in one step. So the two architectures disagree about exactly
one thing, and it is a thing Layer 9 already has vocabulary for.

Five deterministic checks, no LLM, no model call:

  C1 **anchoring**     - does each entry cite evidence that resolves into the row's own policy /
                         episode ids? An unresolvable or absent citation is not provenance.
  C2 **facet typing**  - MSCE's own prompt defines ℰ as facts of existence, ℐ as cause→effect, and
                         𝒞 as the environment fact that makes an action unsafe. An entry filed under
                         one facet whose language belongs to another is mis-typed.
  C3 **procedural drift** - the same prompt explicitly forbids action-prescription in L3 ("that's an
                         action plan, belongs to L2"). Prescriptive language here is a layer error.
  C4 **assumption**    - an unrestricted generalisation (all / always / every) with no evidence is
                         an assumption presented as an observation.
  C5 **confidence provenance** - MSCE's stored confidence is the LLM's own estimate multiplied by an
                         embedding-cohesion factor. Neither term is evidence about the world, so the
                         number is reported as non-epistemic rather than trusted.

Verdicts are Layer 9's existing ``SemanticState``, not a new vocabulary invented for this bridge.
Every verdict carries the checks that produced it, so the justification is auditable by design.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from desi_layer9.enums import SemanticState  # noqa: E402

# MSCE's boundary contract, made checkable. Sources: core/llm/prompts/l3-abstraction.ts (the GOOD /
# BAD examples are theirs) and core/types.ts (the ℰ/ℐ/𝒞 field docs).
#
# Deliberately narrow. A first pass also keyed on bare verbs (install / run / add / use) and
# promptly rejected "node_modules/ is rewritten by npm install; manual edits are lost on the next
# sync" - which is one of the prompt's own GOOD examples. "npm install" there names a command; it
# prescribes nothing. Prescription is carried by MODALS AND AVOIDANCE VERBS DIRECTED AT A READER,
# not by any verb that happens to denote an action. The prompt's GOOD examples are the gold
# standard: a checker that rejects them is wrong, and this one is held to that by a test.
_PRESCRIPTIVE = re.compile(
    r"\b(must|should|shall|ought to|avoid|avoids|avoiding|don'?t|do not|never |always |prefer|"
    r"prefers|ensure|make sure|be sure to)\b", re.I)
_CAUSAL = re.compile(
    r"\b(fail|fails|failing|raise|raises|cause|causes|caused|result|results|lead|leads|break|"
    r"breaks|incompatible|mismatch|does not propagate|no in-process|error|rejects?)\b", re.I)
_UNIVERSAL = re.compile(r"\b(all|always|every|any|never|none)\b", re.I)

FACETS = ("environment", "inference", "constraints")

# Ordered worst -> best. The row verdict is the worst of its entries.
_SEVERITY = [SemanticState.SYNTHESIS_REJECTED, SemanticState.HUMAN_REVIEW_REQUIRED,
             SemanticState.LEXICAL_CANDIDATE, SemanticState.SYNTHESIS_ELIGIBLE]


def _anchored(entry: dict, known_ids: set[str]) -> tuple[bool, str]:
    """C1. Evidence must be cited AND resolve into the row's own policy / episode ids."""
    ids = [i for i in (entry.get("evidenceIds") or []) if isinstance(i, str) and i]
    if not ids:
        return False, "keine evidenceIds - die Aussage nennt keine Stütze"
    unresolved = [i for i in ids if i not in known_ids]
    if unresolved:
        return False, f"evidenceIds nicht auflösbar: {', '.join(sorted(unresolved)[:3])}"
    return True, f"{len(ids)} Beleg(e) aufgelöst"


def classify_language(text: str) -> str:
    """What the WORDING makes this, regardless of the facet it was filed under."""
    if _PRESCRIPTIVE.search(text):
        return "prescription"
    if _CAUSAL.search(text):
        return "inference"
    return "observation"


def adjudicate_entry(facet: str, entry: dict, known_ids: set[str]) -> dict:
    """One (ℰ|ℐ|𝒞) entry -> a Layer 9 state plus the checks that produced it."""
    text = f"{entry.get('label', '')} {entry.get('description', '')}".strip()
    checks: list[dict] = []
    kind = classify_language(text)

    anchored, why = _anchored(entry, known_ids)
    checks.append({"check": "C1 anchoring", "pass": anchored, "detail": why})

    # C3 first: procedural drift is a layer error MSCE's own prompt already forbids.
    drift = kind == "prescription"
    checks.append({"check": "C3 procedural drift", "pass": not drift,
                   "detail": "handlungsvorschreibend - gehört nach L2, nicht L3" if drift
                             else "deklarativ formuliert"})

    # C2: the facet it was filed under vs what the wording actually is.
    expected = {"environment": "observation", "inference": "inference",
                "constraints": "observation"}.get(facet, "observation")
    mistyped = not drift and kind != expected
    checks.append({"check": "C2 facet typing", "pass": not mistyped,
                   "detail": f"unter '{facet}' abgelegt, Sprache ist '{kind}' (erwartet "
                             f"'{expected}')" if mistyped else f"Sprache passt zu '{facet}'"})

    # C4: an unrestricted generalisation with no evidence is an assumption, not an observation.
    assumption = bool(_UNIVERSAL.search(text)) and not anchored
    checks.append({"check": "C4 assumption", "pass": not assumption,
                   "detail": "unbeschränkte Verallgemeinerung ohne Beleg" if assumption
                             else "keine unbelegte Verallgemeinerung"})

    if drift:
        state = SemanticState.SYNTHESIS_REJECTED
        why_state = "Schichtfehler: das ist eine Handlungsanweisung (L2), keine Umweltaussage (L3)"
    elif mistyped:
        state = SemanticState.HUMAN_REVIEW_REQUIRED
        why_state = "als Tatsache abgelegt, aber als Schluss formuliert - Typisierung prüfen"
    elif not anchored:
        state = SemanticState.LEXICAL_CANDIDATE
        why_state = ("nur durch Kohortenähnlichkeit gestützt, kein aufgelöster Beleg - als "
                     "Hypothese halten, nicht konsolidieren")
    else:
        state = SemanticState.SYNTHESIS_ELIGIBLE
        why_state = "belegt, richtig typisiert, deklarativ - zulässig"

    return {"facet": facet, "label": entry.get("label", ""), "text": text,
            "language": kind, "state": state.value, "why": why_state, "checks": checks}


def adjudicate(row: dict) -> dict:
    """A full MSCE ``WorldModelRow`` -> a read-only DESi verdict with auditable justification."""
    known = {str(i) for i in (row.get("policyIds") or [])}
    known |= {str(i) for i in (row.get("sourceEpisodeIds") or [])}
    entries: list[dict] = []
    for facet in FACETS:
        for e in (row.get("structure") or {}).get(facet) or []:
            if isinstance(e, dict):
                entries.append(adjudicate_entry(facet, e, known))

    by_state: dict[str, int] = {}
    for e in entries:
        by_state[e["state"]] = by_state.get(e["state"], 0) + 1
    if not entries:
        overall = SemanticState.INSUFFICIENT_EVIDENCE
    else:
        overall = next(s for s in _SEVERITY if s.value in by_state)

    # C5 - reported, never used to raise a verdict: MSCE's confidence is the LLM's own estimate
    # times an embedding-cohesion factor. Both are properties of the generation, not of the world.
    conf = row.get("confidence")
    c5 = {"check": "C5 confidence provenance", "pass": False,
          "detail": f"gespeicherte confidence={conf} stammt aus LLM-Selbsteinschätzung × "
                    "Embedding-Kohäsion - kein Evidenzmaß; von DESi nicht verwendet"}

    return {"world_id": row.get("id", ""), "title": row.get("title", ""),
            "overall_state": overall.value, "entries": entries, "by_state": by_state,
            "row_checks": [c5],
            "admissible": overall == SemanticState.SYNTHESIS_ELIGIBLE}


def render(result: dict) -> str:
    lines = [f"L3-Kandidat: {result['title'] or result['world_id']}",
             f"  Gesamturteil: {result['overall_state']}", ""]
    for e in result["entries"]:
        lines.append(f"  [{e['facet']:<12}] {e['text'][:64]}")
        lines.append(f"      -> {e['state']}: {e['why']}")
        for c in e["checks"]:
            if not c["pass"]:
                lines.append(f"         ✗ {c['check']}: {c['detail']}")
    for c in result["row_checks"]:
        lines.append(f"  ! {c['check']}: {c['detail']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).with_name("corpus.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    totals: dict[str, int] = {}
    for row in rows:
        res = adjudicate(row)
        print(render(res))
        print()
        for e in res["entries"]:
            totals[e["state"]] = totals.get(e["state"], 0) + 1
    n = sum(totals.values())
    print(f"=== {n} L3-Einträge insgesamt ===")
    for state, count in sorted(totals.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>3}  {state}  ({count / n:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
