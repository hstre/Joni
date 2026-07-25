"""Operator measure 2: a visible breakdown of WHY the method pipeline is starved.

360 candidate methods, 14 old trials, 0 activations - but is that because benchmarks are missing,
or because the harvested "methods" are not procedures at all? This READ-ONLY diagnostic classifies
every candidate method into exactly the operator's five buckets, so the answer is visible:

  * ``testbereit``      - matches a hand-curated benchmark (``problems.match``) -> could be trialed;
  * ``kein_benchmark``  - a real short procedure/lens, but no benchmark keyword matches (we lack a
                          gold set for it, not a broken extraction);
  * ``nicht_ausfuehrbar`` - the "method" name is a long harvested paper title, not a procedure -
                          the extraction shelved a paper, not a technique;
  * ``scope_unklar``    - short-named but no procedural cue at all - we cannot tell what it does;
  * ``duplikat``        - its normalised name+summary repeats an earlier candidate.

It writes only its own artefacts (``docs/method_breakdown.md`` + a compact ``state`` count row) and
exposes the counts in ``extensions``. It never trials, retires, or writes Layer 9 - it only tells
the operator whether the fix is 'add benchmarks' (many ``kein_benchmark``) or 'fix extraction'
(many ``nicht_ausfuehrbar`` / ``scope_unklar``).
"""
from __future__ import annotations

import contextlib
import json
import re

import desi_layer9 as l9

from . import problems

BUCKETS = ("testbereit", "kein_benchmark", "nicht_ausfuehrbar", "scope_unklar", "duplikat")

# procedural cue words: a candidate that mentions doing something is at least a plausible procedure.
_CUES = frozenset({
    "normalise", "normalize", "canonical", "canonicalise", "convert", "compare", "dedup",
    "deduplicate", "duplicate", "parse", "sort", "order", "rank", "filter", "cluster", "detect",
    "classify", "match", "align", "merge", "extract", "map", "score", "threshold", "aggregate",
    "segment", "count", "measure", "group", "split", "join", "select", "weight", "scale", "encode",
    "decode", "embed", "retrieve", "route", "verify", "check", "resolve", "lens", "transform",
})
_WORD = re.compile(r"[a-z][a-z-]+")


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def _has_cue(text: str) -> bool:
    low = (text or "").lower()
    if "-as-a-lens" in low or low.endswith("-lens"):
        return True
    return any(w in _CUES for w in _WORD.findall(low))


def classify(name: str, summary: str, seen: set) -> str:
    """Assign one method to a bucket. ``seen`` accumulates normalised texts for duplicate detection
    (call in a stable order). Deterministic; lexical only."""
    norm = _norm(f"{name} | {summary}")
    if norm and norm in seen:
        return "duplikat"
    if norm:
        seen.add(norm)
    if not problems.is_short_procedure_name(name):
        return "nicht_ausfuehrbar"                     # a long paper title, not a procedure name
    if problems.match(name, summary) is not None:
        return "testbereit"
    if _has_cue(f"{name} {summary}"):
        return "kein_benchmark"                        # a real short procedure, just no gold set
    return "scope_unklar"


def _candidate_methods(cs) -> list:
    out = []
    with contextlib.suppress(Exception):
        for m in cs.core.all(l9.ObjectType.METHOD):
            if getattr(getattr(m, "status", None), "value", "") in ("candidate", "provisional"):
                out.append(m)
    return out


def compute(cs) -> dict:
    """Classify every candidate method; return counts + a few examples per bucket. Read-only."""
    methods = sorted(_candidate_methods(cs), key=lambda m: str(getattr(m, "id", "")))
    counts = {b: 0 for b in BUCKETS}
    examples: dict = {b: [] for b in BUCKETS}
    seen: set = set()
    for m in methods:
        name = str(getattr(m, "name", "") or "")
        summary = str(getattr(m, "summary", "") or "")
        bucket = classify(name, summary, seen)
        counts[bucket] += 1
        if len(examples[bucket]) < 4:
            examples[bucket].append((name or str(getattr(m, "id", "")))[:90])
    return {"total": len(methods), "counts": counts, "examples": examples}


def render_sheet(rec: dict) -> str:
    c = rec["counts"]
    lines = [
        "# Joni — Methoden-Breakdown (warum ist die Trial-Pipeline ausgehungert?)",
        "",
        f"**{rec['total']} Kandidaten-Methoden**  ",
        "",
        "_Read-only Diagnose. Zeigt, ob der Fix „mehr Benchmarks\" (viel `kein_benchmark`) oder "
        "„Extraktion reparieren\" (viel `nicht_ausfuehrbar`/`scope_unklar`) ist. Kein Trial, "
        "keine Retirierung, kein Layer-9-Schreiben._",
        "",
        "| Bucket | Anzahl | Bedeutung |",
        "|---|---|---|",
        f"| testbereit | {c['testbereit']} | matcht ein Benchmark → trialbar |",
        f"| kein_benchmark | {c['kein_benchmark']} | echtes kurzes Verfahren, aber kein Gold-Set |",
        f"| nicht_ausfuehrbar | {c['nicht_ausfuehrbar']} | langer Paper-Titel, kein Verfahren |",
        f"| scope_unklar | {c['scope_unklar']} | kurz, aber kein Verfahrens-Hinweis |",
        f"| duplikat | {c['duplikat']} | wiederholt einen früheren Kandidaten |",
        "",
    ]
    for b in BUCKETS:
        ex = rec["examples"].get(b, [])
        if ex:
            lines.append(f"**{b}** (Beispiele): " + " · ".join(f"`{e}`" for e in ex))
    lines.append("")
    return "\n".join(lines) + "\n"


def run_breakdown(cs, extensions: dict, proto, cycle: int = 0, *, paths=None) -> dict:
    """Compute + persist the method breakdown. Read-only; never raises."""
    try:
        rec = compute(cs)
        extensions["method_breakdown"] = rec["counts"]
        if paths is not None:
            sheet = getattr(paths, "method_breakdown_sheet", None)
            series = getattr(paths, "method_breakdown_series", None)
            if sheet is not None:
                sheet.parent.mkdir(parents=True, exist_ok=True)
                sheet.write_text(render_sheet(rec), encoding="utf-8")
            if series is not None:
                series.parent.mkdir(parents=True, exist_ok=True)
                with series.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"cycle": cycle, "total": rec["total"],
                                        **rec["counts"]}, ensure_ascii=False) + "\n")
        c = rec["counts"]
        proto.record(cycle, "method_breakdown",
                     f"{rec['total']} methods: {c['testbereit']} testbereit · "
                     f"{c['kein_benchmark']} kein-benchmark · {c['nicht_ausfuehrbar']} "
                     f"nicht-ausführbar · {c['scope_unklar']} scope-unklar · {c['duplikat']} dup")
        return rec
    except Exception as exc:  # noqa: BLE001 - a read-only diagnostic must never break the cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "method_breakdown", f"[breakdown error] {type(exc).__name__}")
        return {"total": 0, "counts": {b: 0 for b in BUCKETS}, "examples": {}}


__all__ = ["BUCKETS", "classify", "compute", "render_sheet", "run_breakdown"]
