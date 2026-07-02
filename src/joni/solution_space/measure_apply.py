"""The FIRST real measurement of the executed apply: does the method-guided resolution beat controls?

For each mode (method / none / scrambled / irrelevant) it seeds a FRESH core of checkable conflicts,
lets Baustein B propose a deep operator per conflict, applies the real LLM ``apply_fn`` (which resolves
a conflict only on a deterministically-correct answer), and measures the RESOLUTION ACCURACY — the
fraction of conflicts actually resolved. It also writes the real ``DeepMethodTrial`` outcomes to a
store, so Baustein C can be run on genuine data. Offline via ``--stub``; real via DeepSeek.

This is the executed-scaffold question the six-battery null left open, now flowing through the whole
pipeline (from_core -> apply -> grade-by-resolution -> store). A null here (method ~= none) is the same
honest outcome as the batteries; a real lift would be the first sign the method matters when EXECUTED.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from ..method_trial import deep_methods as D
from .llm_apply import make_llm_apply
from .operator_cycle import grade_by_resolution, open_conflict_ids
from .operators import DeepMethodProposal, DeepMethodTrial, propose_operators
from .resolvable_conflicts import CASES, HARD_CASES, seed_core
from .trial_store import record_trial

MODES = ("method", "none", "scrambled", "irrelevant")


@dataclass(frozen=True)
class _Gap:
    id: str
    kind: str
    severity: str = "soft"
    unresolved_since: int = 0


@dataclass(frozen=True)
class _Snap:
    conflicts: tuple = ()
    provenance: object = None


def propose_for_core(core, *, top_k_per_gap: int = 1):
    """Rank deep operators for a core's open conflicts WITHOUT the DESi projector — a small local
    snapshot from the vendored Layer-9 conflicts (so the measurement needs no external DESi)."""
    conflicts = tuple(
        _Gap(id=c.id, kind=getattr(getattr(c, "conflict_kind", None), "value", "unqualified"),
             severity=getattr(c, "severity", "soft"))
        for c in core.open_conflicts())
    return propose_operators(_Snap(conflicts=conflicts), top_k_per_gap=top_k_per_gap)


def _fair_proposal(cid: str, method_id: str) -> DeepMethodProposal:
    """A proposal carrying the conflict's RIGHT method (from the battery), bypassing the taxonomy —
    so the intervention actually supplies the fitting deep method, not the gap-kind default."""
    m = D.by_id(method_id)
    return DeepMethodProposal(
        target=f"conflict:{cid}", method_id=method_id, method_name=m.name if m else method_id,
        core_question=m.core_question if m else "", method_kind=m.kind if m else "",
        reason=(), expected_information_gain="high", priority=1.0, gap_kind="checkable_fact")


def run_mode(solver, mode: str, *, store_path: str | None = None, cases=None,
             fair_routing: bool = False) -> dict:
    core, registry = seed_core(cases)
    apply = make_llm_apply(solver, registry, mode=mode)
    if fair_routing:                    # route each conflict's DECLARED right method (no confound)
        proposals = {cid: _fair_proposal(cid, registry[cid]["method"]) for cid in registry}
    else:
        proposals = {p.target.split(":", 1)[-1]: p for p in propose_for_core(core, top_k_per_gap=1)}
    results: dict[str, str] = {}
    for cid in list(registry):
        p = proposals.get(cid)
        if p is None:
            continue
        before = open_conflict_ids(core)
        errored = False
        try:
            apply(core, p)
        except Exception:  # noqa: BLE001
            errored = True
        after = open_conflict_ids(core)
        res = grade_by_resolution(cid, before, after, errored=errored)
        results[cid] = res
        if store_path and mode == "method":       # only the real-method trials feed the discoverer
            record_trial(store_path, DeepMethodTrial(
                method_id=p.method_id, target=cid, result=res, scope="measure_apply",
                gap_kind=p.gap_kind or "unknown"))
    n = len(results) or 1
    acc = sum(1 for r in results.values() if r == "success") / n
    return {"mode": mode, "n": len(results), "accuracy": round(acc, 3), "results": results}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--battery", choices=("easy", "hard"), default="easy",
                    help="easy = trivially checkable facts; hard = computation-heavy (real headroom)")
    ap.add_argument("--model", default="deepseek-chat",
                    help="DeepSeek model id (e.g. deepseek-chat, deepseek-reasoner)")
    ap.add_argument("--list-models", action="store_true",
                    help="print the models the DeepSeek API serves, then exit (discover a small one)")
    ap.add_argument("--stub", action="store_true", help="offline: a stub that always answers 'A'")
    ap.add_argument("--store", default=None, help="write real-method trials here (feeds Baustein C)")
    ap.add_argument("--out", default=None, help="write the full result JSON here")
    args = ap.parse_args(argv)
    cases = HARD_CASES if args.battery == "hard" else CASES

    if args.list_models:
        from ..method_trial.solver import list_models
        print("DeepSeek models served by the API:")
        for mid in list_models():
            print(f"  - {mid}")
        return 0

    if args.stub:
        from ..method_trial.solver import StubSolver
        solver = StubSolver(lambda p: "Answer: A")
    else:
        from ..method_trial.solver import DeepSeekSolver
        solver = DeepSeekSolver(model=args.model)

    fair = args.battery == "hard"       # the hard battery declares each conflict's right method
    per_mode = {m: run_mode(solver, m, store_path=args.store, cases=cases, fair_routing=fair)
                for m in MODES}
    base = per_mode["none"]["accuracy"]
    summary = {
        "solver": getattr(solver, "name", "stub"), "model": getattr(solver, "model", "stub"),
        "battery": args.battery,
        "routing": "fair (declared right method)" if fair else "taxonomy (gap-kind default)",
        "accuracy": {m: per_mode[m]["accuracy"] for m in MODES},
        "method_minus_none": round(per_mode["method"]["accuracy"] - base, 3),
        "method_beats_all_controls": all(
            per_mode["method"]["accuracy"] > per_mode[c]["accuracy"] for c in MODES if c != "method"),
    }
    print("  resolution accuracy by mode:")
    for m in MODES:
        print(f"    {m:12s} {per_mode[m]['accuracy']:.3f}  ({per_mode[m]['n']} conflicts)")
    print(f"  method - none = {summary['method_minus_none']:+.3f}   "
          f"beats all controls: {summary['method_beats_all_controls']}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "per_mode": per_mode}, f, ensure_ascii=False, indent=2)
        print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
