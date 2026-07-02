"""Throw the WHOLE toolbox at each task — the 'did you try ALL methods?' experiment.

Every earlier run gave each task its ONE pre-registered method. This asks the complementary question two
ways, honestly:
- PORTFOLIO (kitchen-sink): prepend ALL deep methods at once and let the model pick — does having the
  whole toolbox in front of it help, or does the mostly-irrelevant bulk drown it?
- ORACLE (best-of): try EACH method separately as the intervention; a task counts solved if ANY single
  method flips it to correct. This is an optimistic UPPER BOUND (many independent tries), so a lone flip
  is weak evidence — but if even best-of-all-methods can't beat the naked baseline, the null is decisive.

Offline, non-core, budget-gated (needs a solver). Grading is the same deterministic per-task checker; the
baseline is the naked prompt, so every comparison is apples-to-apples. Reports baseline vs portfolio vs
oracle, and per task WHICH methods (if any) solved it — including whether the pre-registered one did.

    python -m joni.method_trial.run_allmethods --battery search --out state/all.json
"""
from __future__ import annotations

import argparse
import json

from . import deep_methods as D


def portfolio_preamble() -> str:
    lines = ["You may use ANY of the following general problem-solving methods. Choose whichever "
             "actually fits this problem and ignore the rest.", ""]
    for m in D.DEEP_METHODS:
        lines.append(f"- {m.name} ({m.aka}) — {m.core_question}")
        for s in m.steps:
            lines.append(f"    * {s}")
    return "\n".join(lines)


def build_conditions(task) -> dict[str, str]:
    conds = {
        "plain_baseline": task.prompt,
        "portfolio": f"{portfolio_preamble()}\n\n{task.prompt}",
    }
    for m in D.DEEP_METHODS:
        conds[f"m:{m.id}"] = f"{D.as_preamble(m.id)}\n\n{task.prompt}"
    return conds


def _battery(name: str):
    if name == "search":
        from .gold_search_v1 import CASES
    elif name == "novel":
        from .gold_novel_v1 import CASES
    elif name == "cross":
        from .gold_cross_v1 import CASES
    elif name == "deep":
        from .gold_deep_v1 import CASES
    else:
        from .gold_micro_v1 import CASES
    return CASES


def run(solver, cases) -> list[dict]:
    rows = []
    for t in cases:
        conds = build_conditions(t)
        res = {name: bool(t.checker(solver.solve(p))) for name, p in conds.items()}
        rows.append({"task": t.id, "registered": t.expected_method_class, "res": res})
    return rows


def summarize(rows: list[dict]) -> dict:
    n = len(rows) or 1
    method_keys = [k for k in rows[0]["res"] if k.startswith("m:")]
    baseline = sum(r["res"]["plain_baseline"] for r in rows) / n
    portfolio = sum(r["res"]["portfolio"] for r in rows) / n
    oracle = sum(any(r["res"][k] for k in method_keys) for r in rows) / n
    per_task = []
    rescued = 0            # baseline WRONG, but some single method got it right
    reg_helped = 0         # the pre-registered method specifically rescued a baseline failure
    for r in rows:
        solvers = sorted(k[2:] for k in method_keys if r["res"][k])
        base_ok = r["res"]["plain_baseline"]
        if not base_ok and solvers:
            rescued += 1
            if r["registered"] in solvers:
                reg_helped += 1
        per_task.append({"task": r["task"], "registered": r["registered"],
                         "baseline": base_ok, "portfolio": r["res"]["portfolio"],
                         "n_methods_solving": len(solvers), "solved_by": solvers})
    return {
        "n_tasks": n, "n_methods": len(method_keys),
        "baseline": round(baseline, 3), "portfolio": round(portfolio, 3),
        "oracle_best_of_any_method": round(oracle, 3),
        "tasks_rescued_by_some_method": rescued,
        "of_which_by_the_registered_method": reg_helped,
        "per_task": per_task,
        "note": "oracle = best of many independent tries -> an OPTIMISTIC upper bound; a single flip is "
                "weak evidence (multiple comparisons). Baseline is the naked prompt.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--battery", default="search",
                    choices=("search", "novel", "cross", "deep", "micro"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--stub", action="store_true")
    args = ap.parse_args(argv)

    cases = _battery(args.battery)
    cases = cases[: args.limit] if args.limit else cases
    per_task_calls = 2 + len(D.DEEP_METHODS)
    calls = len(cases) * per_task_calls
    print(f"All-methods · {len(cases)} tasks x ({per_task_calls} conditions: baseline + portfolio + "
          f"{len(D.DEEP_METHODS)} single methods) = {calls} solver calls (temperature 0)")
    if args.dry:
        return 0

    if args.stub:
        from .solver import StubSolver
        solver = StubSolver(lambda p: "Answer: none")
    else:
        from .solver import DeepSeekSolver
        solver = DeepSeekSolver()

    rows = run(solver, cases)
    s = summarize(rows)
    print(f"\n  baseline {s['baseline']} · portfolio (all at once) {s['portfolio']} · "
          f"oracle (best of any single method) {s['oracle_best_of_any_method']}")
    print(f"  tasks rescued by SOME method: {s['tasks_rescued_by_some_method']} "
          f"(by the pre-registered one: {s['of_which_by_the_registered_method']})")
    for pt in s["per_task"]:
        b = "1" if pt["baseline"] else "."
        p = "1" if pt["portfolio"] else "."
        print(f"    {pt['task']:18s} base={b} port={p} solved_by={pt['n_methods_solving']:2d} "
              f"{pt['solved_by'] if pt['solved_by'] else ''}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"solver": solver.name, "battery": args.battery, "summary": s, "rows": rows},
                      f, ensure_ascii=False, indent=2)
        print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
