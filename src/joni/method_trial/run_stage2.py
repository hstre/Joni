"""Stage 2 — the pilot: does the a-priori method beat ALL four controls on the micro battery?

For each task and each of the five conditions: solve (temperature 0), grade with the deterministic
checker. Aggregate accuracy per condition and, for the intervention vs EACH control, a paired
bootstrap 95% CI of the accuracy difference over TASKS (the pre-registered independence unit). The
method 'wins' only if every ``intervention - control`` CI excludes 0 in the helpful direction — the
pre-registered success rule. Offline, budget-gated: nothing runs without a solver you pass in.

    python -m joni.method_trial.run_stage2 --dry      # cost estimate only, no calls
    python -m joni.method_trial.run_stage2 --out state/stage2.json   # real run (DEEPSEEK_API_KEY)
"""
from __future__ import annotations

import argparse
import json
import random

from . import conditions
from .gold_micro_v1 import CASES
from .preregistration import SPEC, content_hash


def run(solver, cases=None) -> dict:
    """Solve every (task, condition) and grade. Returns per-task correctness + raw answers."""
    cases = cases or CASES
    rows = []
    for t in cases:
        prompts = conditions.build(t)
        cond = {}
        for name, prompt in prompts.items():
            ans = solver.solve(prompt)
            cond[name] = {"correct": bool(t.checker(ans)), "answer": ans[-400:]}
        rows.append({"task": t.id, "skill": t.skill, "method_class": t.expected_method_class,
                     "conditions": cond})
    return {"rows": rows}


def accuracy(result: dict) -> dict[str, float]:
    rows = result["rows"]
    n = len(rows) or 1
    return {c: round(sum(r["conditions"][c]["correct"] for r in rows) / n, 3)
            for c in conditions.CONDITIONS}


def _paired_bootstrap_ci(diffs: list[int], *, seed: int,
                         iters: int = 4000) -> tuple[float, float, float]:
    """95% CI of the mean of paired per-task differences, by resampling tasks with replacement."""
    n = len(diffs)
    if n == 0:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        s = sum(diffs[rng.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[int(0.975 * iters) - 1]
    return (round(lo, 3), round(hi, 3), round(sum(diffs) / n, 3))


def decide(result: dict, *, seed: int = 20260702, iters: int = 4000) -> dict:
    """Intervention beats each control iff the paired accuracy-difference CI excludes 0 (lo > 0).
    The method WINS only if it beats all four controls (the pre-registered success rule)."""
    rows = result["rows"]
    controls = [c for c in conditions.CONDITIONS if c != "intervention"]
    vs = {}
    for c in controls:
        diffs = [int(r["conditions"]["intervention"]["correct"])
                 - int(r["conditions"][c]["correct"]) for r in rows]
        lo, hi, mean = _paired_bootstrap_ci(diffs, seed=seed, iters=iters)
        vs[c] = {"mean_diff": mean, "ci95": [lo, hi], "beats": lo > 0}
    return {
        "accuracy": accuracy(result),
        "vs_controls": vs,
        "method_wins": all(vs[c]["beats"] for c in controls),
        "n_tasks": len(rows),
        "note": "micro battery (pilot): falsifies only; a retain/retire decision needs the holdout",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="run only the first N tasks")
    ap.add_argument("--dry", action="store_true", help="print the call count, do not call")
    ap.add_argument("--out", default=None, help="write the full result + decision JSON here")
    ap.add_argument("--stub", action="store_true", help="always-wrong stub (no network/cost)")
    args = ap.parse_args(argv)

    cases = CASES[: args.limit] if args.limit else CASES
    calls = len(cases) * len(conditions.CONDITIONS)
    print(f"Stage 2 · {len(cases)} tasks x {len(conditions.CONDITIONS)} conditions = {calls} "
          f"solver calls (temperature 0)")
    print(f"  pre-registration {content_hash()[:12]} · controls={SPEC['controls']}")
    if args.dry:
        return 0

    if args.stub:
        from .solver import StubSolver
        solver = StubSolver(lambda p: "Answer: none")
    else:
        from .solver import DeepSeekSolver
        solver = DeepSeekSolver()

    result = run(solver, cases)
    dec = decide(result)
    print(f"\n  accuracy: {dec['accuracy']}")
    for c, v in dec["vs_controls"].items():
        mark = "BEATS" if v["beats"] else "no"
        print(f"  intervention vs {c:18s} Δ={v['mean_diff']:+.3f} CI95 {v['ci95']}  -> {mark}")
    print(f"\n  method_wins (beats all 4 controls): {dec['method_wins']}")
    if args.out:
        payload = {"solver": solver.name, "prereg_hash": content_hash(), "decision": dec,
                   "result": result}
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
