"""Ontology-coverage shadow — does an ontology probe have purchase on Joni's REAL terms?

PURE OBSERVER. The slice shadow showed supersession (#5) over-fires because same subject-key is
taken as same scope. The Ontology Probe's promise is to SOFTEN those false same-scope groups: when a
subject token is ambiguous across kinds (``operator`` = math object vs. person), the probe marks the
scope uncertain and the router withholds the supersession flag. Whether that is REAL depends on
coverage — so, like the slice shadow before adopting #3/#4, this measures it on real data first:

  * addressable pool   — how many same-subject-key COLLISION groups exist (the #5 over-fire pool)
                         and how many live claims sit in them. A real number from Joni's graph.
  * coverage           — of the salient subject tokens, how many the ontology even knows (returns
                         senses for). With no corpus installed this is 0 — reported, not faked.
  * addressable groups — collision groups with a token the ontology flags as ambiguous across kinds:
                         the groups the probe could LEGITIMATELY soften (separate-only).

    python shadow/ontology_coverage_shadow.py [--db ...] [--seed-demo] [--limit N] [--json]

``--seed-demo`` loads a tiny, labelled in-memory ontology of recurring ambiguous terms so the
mechanism is visible without WordNet/OpenCyc; the DEFAULT is the real WordNet adapter (fail-open,
0 coverage when no corpus). It never writes Joni state and never touches the loop.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, os.environ.get("DESI_REPO") or os.environ.get("DESI_ROOT") or "/home/user/DESi")

from joni.layer9_v2.checks.subject import subject_key  # noqa: E402

try:
    from desi_router.ontology_probe import (
        OntologyProbe,
        Sense,
        StaticOntologyAdapter,
        WordNetAdapter,
        requires_disambiguation,
    )
except Exception as exc:  # noqa: BLE001 — decoupled; never silently faked
    OntologyProbe = None
    _IMPORT_ERR = exc


def tokens_of_key(key: str) -> tuple[str, ...]:
    """The salient subject tokens encoded in a subject key ``topic:x|a+b+c`` (empty if none)."""
    if "|" not in (key or ""):
        return ()
    return tuple(t for t in key.split("|", 1)[1].split("+") if t)


def _demo_ontology():
    """A tiny, clearly-labelled seed of recurring across-kind-ambiguous terms — NOT a knowledge
    base, just enough to make the separate-only mechanism visible on real keys without a corpus."""
    def A(name, *kinds):
        return Sense(name, tuple(kinds))
    return StaticOntologyAdapter({
        "operator": (A("math_operator", "abstract", "math"), A("human_op", "person", "worker")),
        "kernel": (A("os_kernel", "artifact", "software"), A("seed_kernel", "plant_part")),
        "model": (A("ml_model", "artifact", "abstraction"), A("fashion_model", "person")),
        "agent": (A("software_agent", "artifact", "process"), A("human_agent", "person")),
        "memory": (A("computer_memory", "artifact"), A("cognitive_memory", "process", "cognition")),
        "python": (A("language", "artifact", "software"), A("snake", "animal", "organism")),
    }, source="demo_seed")


def assess(subjects: dict[str, list[str]], probe) -> dict:
    """``subjects`` maps subject_key -> list of claim ids. Returns the coverage report. Pure: no
    I/O, deterministic given the probe."""
    collisions = {k: v for k, v in subjects.items() if len(v) > 1}
    tokens: Counter = Counter()
    for k, members in subjects.items():
        for t in tokens_of_key(k):
            tokens[t] += len(members)
    distinct = sorted(tokens)
    covered, ambiguous = set(), set()
    for t in distinct:
        h = probe.probe(t)
        if h.candidate_senses:
            covered.add(t)
        if requires_disambiguation(h):
            ambiguous.add(t)
    addressable = {k: v for k, v in collisions.items()
                   if any(tok in ambiguous for tok in tokens_of_key(k))}
    n_tokens = len(distinct) or 1
    return {
        "ontology_source": probe.source,
        "subject_keys": len(subjects),
        "collision_groups": len(collisions),
        "claims_in_collisions": sum(len(v) for v in collisions.values()),
        "distinct_tokens": len(distinct),
        "covered_tokens": len(covered),
        "ambiguous_tokens": len(ambiguous),
        "coverage_rate": round(len(covered) / n_tokens, 3),
        "addressable_collision_groups": len(addressable),
        "addressable_rate": round(len(addressable) / (len(collisions) or 1), 3),
        "sample_ambiguous": sorted(ambiguous)[:20],
    }


def _live_subjects(db_path, statuses, limit) -> dict[str, list[str]]:
    from joni.layer9_v2.storage import sqlite as S
    conn = S.open_db(db_path)
    try:
        placeholders = ",".join("?" for _ in statuses)
        subjects: dict[str, list[str]] = {}
        rows = conn.execute(
            f"SELECT id, payload_json, title FROM objects WHERE space='content' AND type='claim' "
            f"AND status IN ({placeholders})", statuses)
        for n, (oid, payload, title) in enumerate(rows):
            if limit and n >= limit:
                break
            f = (json.loads(payload) or {}).get("fields", {})
            topic = f.get("topic") or "_untopiced"
            subjects.setdefault(subject_key(f.get("text") or title, topic), []).append(oid)
        return subjects
    finally:
        conn.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(_REPO / "state" / "layer9_v2.sqlite"))
    ap.add_argument("--statuses", default="active,contested")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed-demo", action="store_true",
                    help="use the labelled demo ontology, not the fail-open WordNet adapter")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if OntologyProbe is None:
        print(f"FATAL: cannot import desi_router.ontology_probe ({_IMPORT_ERR}).", file=sys.stderr)
        return 2
    if not Path(args.db).exists():
        print(f"FATAL: v2 store {args.db} not found — build it with `joni-layer9-convert` first.",
              file=sys.stderr)
        return 2
    statuses = tuple(s.strip() for s in args.statuses.split(",") if s.strip())
    probe = OntologyProbe(_demo_ontology() if args.seed_demo else WordNetAdapter())
    subjects = _live_subjects(args.db, statuses, args.limit)
    rep = assess(subjects, probe)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"Ontology-coverage shadow · source={rep['ontology_source']} · live={list(statuses)} · "
          f"real v2 graph\n")
    print(f"  addressable pool : {rep['collision_groups']} same-subject collision groups "
          f"({rep['claims_in_collisions']} claims)")
    print(f"  coverage         : {rep['covered_tokens']}/{rep['distinct_tokens']} tokens "
          f"({rep['coverage_rate']}) · ambiguous-across-kinds: {rep['ambiguous_tokens']}")
    print(f"  addressable      : {rep['addressable_collision_groups']}/{rep['collision_groups']} "
          f"groups carry an ambiguous token ({rep['addressable_rate']})")
    if rep["coverage_rate"] == 0.0:
        print("\n  -> coverage 0: no corpus reachable. The probe stays a silent no-op;\n"
              "     NOT justified on this data yet (mechanism is validated in DESi unit tests).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
