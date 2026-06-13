"""One autonomous cycle - research, learn, improve (within the rule), publish.

A single cycle, intended to be fired hourly by the workflow over a week:

  0. fail-safe: verify the protected core is unchanged (governance) - else stop.
  1. respect the runtime window (retire after a week).
  2. read the sources for Joni's current topics (deterministic offline / live online).
  3. judge relevance (free), learn what fits (claims), resolve any contradictions
     (audited opinion changes).
  4. derive improvements; build the peripheral ones into himself; raise core ones as
     asks for a human - never self-applied.
  5. account for any model spend against the weekly budget.
  6. persist state, append the protocol, regenerate the public site.

Everything is deterministic and free by default; the model ladder is touched only on
escalation, within budget.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .. import desi_link
from . import core_state, governance, self_review, site
from .budget import load as load_budget
from .budget import save as save_budget
from .config import online, paths, runs_per_week, runtime_days, weekly_budget_eur
from .improve import derive, judge
from .protocol import Protocol
from .sources import get_fetchers

_DEFAULT_QUERIES = ["privacy", "routing", "memory", "drift"]


def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def one_cycle() -> dict:
    p = paths()
    # 0. Fail-safe governance check: never proceed on a tampered core.
    governance.assert_core_unchanged(p.root)

    proto = Protocol(p.protocol)
    cycle = proto.next_cycle()

    # 1. Runtime window.
    window = _load_json(p.window, None) or {
        "start": datetime.now(UTC).isoformat(timespec="seconds"), "runs": 0, "retired": False
    }
    started = datetime.fromisoformat(window["start"])
    now = datetime.now(UTC)
    expired = now - started > timedelta(days=runtime_days())
    days_running = (now.date() - started.date()).days     # real time - no tick jumps

    cs = core_state.load_or_migrate(p)
    cs.set_day(days_running)
    budget = load_budget(p.budget, cap_eur=weekly_budget_eur())
    extensions = _load_json(p.extensions, {})
    extensions.setdefault("topics_added", [])
    extensions.setdefault("notes", [])
    extensions.setdefault("asks", [])
    extensions.setdefault("seen", [])

    if expired:
        if not window.get("retired"):
            window["retired"] = True
            proto.record(cycle, "retired", "runtime window of "
                         f"{runtime_days()} days reached - Joni stands down")
        _finish(p, cs, budget, window, extensions, proto, None)
        return {"cycle": cycle, "retired": True}

    window["runs"] += 1
    budget.runs += 1

    # 2. Read the sources.
    queries = cs.topics() or _DEFAULT_QUERIES
    seen = set(extensions["seen"])
    fetched: list = []
    for fetcher in get_fetchers(online=online()):
        items = fetcher.fetch(queries, limit=4)
        proto.record(cycle, "fetched", f"{fetcher.name}: {len(items)} item(s)",
                     refs={"source": fetcher.name})
        fetched.extend(items)

    new_items = [it for it in fetched if it.key not in seen]

    # 3. Judge and learn (claims via the gate); contradictions OPEN, never force-resolved.
    judged: list = []
    for item in new_items:
        rel = judge(cs, item)
        seen.add(item.key)
        proto.record(cycle, "judged",
                     f"{'relevant' if rel.relevant else 'skip'}: {item.title[:80]}",
                     refs={"source": item.key, "topic": rel.topic, "new_topic": rel.new_topic,
                           "url": item.url})
        if not rel.relevant:
            continue
        judged.append((item, rel))
        if rel.topic:
            cs.learn(item.title, rel.topic)

    for conflict_id in cs.detect_and_open_conflicts():
        proto.record(cycle, "conflict_open",
                     f"opened {conflict_id} - two claims held open, not smoothed away")

    # 4. Improvements, split by governance (peripheral ones applied via the gate).
    asks_new: list = []
    for imp in derive(cs, judged):
        if imp.autonomous:
            refs = _apply(cs, extensions, imp)
            proto.record(cycle, "improved", f"{imp.kind}: {imp.title[:80]}",
                         refs={**refs, "source": imp.source_key, "url": imp.source_url})
        else:
            ask = {"kind": imp.kind, "target": imp.target, "rationale": imp.rationale,
                   "source_url": imp.source_url, "cycle": cycle}
            extensions["asks"].append(ask)
            asks_new.append(ask)
            proto.record(cycle, "asked",
                         f"core change needs approval: {imp.target} ({imp.title[:60]})",
                         refs={"url": imp.source_url})

    extensions["seen"] = sorted(seen)[-2000:]   # bound the dedup set

    # 5. Hourly self-review -> provisional self-model claims, reported on the site.
    reviewed = False
    if self_review.should_review(extensions, now):
        self_review.run_review(cs, extensions, proto, cycle,
                               days=days_running, spend=budget.spent_eur)
        reviewed = True

    # 6. Reflect through DESi: its real routing table + deterministic tools (free).
    reflect = _reflect(cs, window, budget, judged, proto, cycle)

    proto.record(cycle, "note",
                 f"cycle done · {len(new_items)} new · spend €{budget.spent_eur:.4f} "
                 f"· routing via {reflect['routing_engine']}")

    _save_json(p.asks_new, asks_new)
    _finish(p, cs, budget, window, extensions, proto, reflect)
    return {"cycle": cycle, "new_items": len(new_items), "asks": len(asks_new),
            "spend": budget.spent_eur, "retired": False, "routing": reflect["routing_engine"],
            "days_running": days_running, "reviewed": reviewed}


def _apply(cs: core_state.CoreState, extensions: dict, imp) -> dict:
    """Apply a peripheral improvement through the gate (claims/preferences only)."""
    if imp.kind == "track_topic":
        cid = cs.learn(f"{imp.target} is worth tracking as a topic", imp.target)
        extensions.setdefault("topics_added", [])
        if imp.target not in extensions["topics_added"]:
            extensions["topics_added"].append(imp.target)
        return {"claim": cid, "topic": imp.target}
    if imp.kind == "note_capability":
        pid = cs.note_preference(imp.target)
        extensions.setdefault("notes", [])
        extensions["notes"].append({"note": imp.rationale, "source": imp.source_url})
        return {"preference": pid}
    return {}


def _reflect(cs, window: dict, budget, judged: list, proto: Protocol,
             cycle: int) -> dict:
    """Use DESi's real routing logic + tools, with a deterministic fallback.

    Free by default: a DESi tool computes Joni's runtime age (a non-math module), and
    DESi's routing table decides the cheapest model to assess this cycle's top claim
    (decision logged, not executed). When DESi is off/absent, both fall back to Joni's
    own deterministic path.
    """
    out = {"routing_engine": desi_link.routing_engine(), "days_running": None,
           "last_route": None}

    start_date = window["start"][:10]
    today = datetime.now(UTC).date().isoformat()
    tool = desi_link.try_tool(f"days between {start_date} and {today}")
    if tool is not None:
        out["days_running"] = tool["result"]
        proto.record(cycle, "tooled",
                     f"DESi {tool['tool']}: {tool['result']} day(s) running",
                     refs={"task_class": tool["task_class"]}, model=f"desi:{tool['tool']}")
    else:
        out["days_running"] = (datetime.now(UTC).date()
                               - datetime.fromisoformat(window["start"]).date()).days

    if judged:
        allowance_usd = round(budget.per_run_allowance(runs_per_week()) * 1.07, 6)
        route = desi_link.route_model("scientific_claim", budget_usd=max(allowance_usd, 1e-4))
        if route is not None:
            out["last_route"] = route
            proto.record(cycle, "routed",
                         f"DESi routes scientific_claim -> {route['model']} "
                         f"(~${route['cost_usd']:.6f})",
                         refs={"reason": route["reason"][:140], "task_class": "scientific_claim"},
                         model=route["model"], cost_eur=0.0)
    return out


def _finish(p, cs: core_state.CoreState, budget, window, extensions,
            proto: Protocol, reflect=None) -> None:
    core_state.save(cs, p)
    save_budget(budget, p.budget)
    _save_json(p.window, window)
    _save_json(p.extensions, extensions)
    snap = cs.snapshot()
    snap.update(reflect or {"routing_engine": desi_link.routing_engine()})
    site.render(p.docs_index, p.docs_data, {
        "snapshot": snap,
        "budget": {"spent_eur": budget.spent_eur, "cap_eur": budget.cap_eur, "runs": budget.runs},
        "window": window,
        "extensions": extensions,
        "protocol": proto.all(),
    })


def runs_per_week_value() -> int:
    return runs_per_week()
