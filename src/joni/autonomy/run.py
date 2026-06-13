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

from .. import persistence
from ..conflict import detect_conflicts, weaker_claim
from ..models import ClaimStatus, Trigger
from ..operators import assert_claim, resolve_conflict
from ..seed import seed_identity
from ..state import Layer9
from . import governance, site
from .budget import load as load_budget
from .budget import save as save_budget
from .config import online, paths, runs_per_week, runtime_days, weekly_budget_eur
from .improve import apply_peripheral, derive, judge
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


def _snapshot(state: Layer9) -> dict:
    return {
        "tick": state.tick,
        "topics": state.topics(),
        "claims_total": len(state.claims),
        "claims_active": len(state.active_claims()),
        "memory": len(state.memory),
        "ledger": len(state.ledger),
        "open_conflicts": len(state.open_conflicts()),
        "goals": len(state.active_goals()),
        "projects": len(state.active_projects()),
        "preferences": len(state.preferences),
    }


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
    expired = datetime.now(UTC) - started > timedelta(days=runtime_days())

    state = persistence.load(p.state) or seed_identity()
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
        _finish(p, state, budget, window, extensions, proto)
        return {"cycle": cycle, "retired": True}

    state.tick += 1
    window["runs"] += 1
    budget.runs += 1

    # 2. Read the sources.
    queries = state.topics() or _DEFAULT_QUERIES
    seen = set(extensions["seen"])
    fetched: list = []
    for fetcher in get_fetchers(online=online()):
        items = fetcher.fetch(queries, limit=4)
        proto.record(cycle, "fetched", f"{fetcher.name}: {len(items)} item(s)",
                     refs={"source": fetcher.name})
        fetched.extend(items)

    new_items = [it for it in fetched if it.key not in seen]

    # 3. Judge, learn, resolve contradictions.
    judged: list = []
    for item in new_items:
        rel = judge(state, item)
        seen.add(item.key)
        proto.record(cycle, "judged",
                     f"{'relevant' if rel.relevant else 'skip'}: {item.title[:80]}",
                     refs={"source": item.key, "topic": rel.topic, "new_topic": rel.new_topic,
                           "url": item.url})
        if not rel.relevant:
            continue
        judged.append((item, rel))
        if rel.topic:
            assert_claim(state, item.title, rel.topic, support=item.score and 0.6 or 0.58,
                         status=ClaimStatus.ACTIVE, trigger=Trigger.RESEARCH_HARVEST,
                         reviewed_by="deterministic")

    for conflict in list(_resolve_conflicts(state)):
        proto.record(cycle, "changed_mind",
                     f"resolved {conflict} - a claim was rejected on new evidence")

    # 4. Improvements, split by governance.
    asks_new: list = []
    for imp in derive(state, judged):
        if imp.autonomous:
            refs = apply_peripheral(state, extensions, imp)
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
    proto.record(cycle, "note",
                 f"cycle done · {len(new_items)} new · spend €{budget.spent_eur:.4f}")

    _save_json(p.asks_new, asks_new)
    _finish(p, state, budget, window, extensions, proto)
    return {"cycle": cycle, "new_items": len(new_items), "asks": len(asks_new),
            "spend": budget.spent_eur, "retired": False}


def _resolve_conflicts(state: Layer9) -> list[str]:
    """Detect and resolve contradictions; return ids of resolved conflicts."""
    detect_conflicts(state)
    resolved = []
    for conflict in list(state.open_conflicts()):
        loser = weaker_claim(state, conflict)
        resolve_conflict(state, conflict.id, reject=loser, reviewed_by="deterministic")
        resolved.append(conflict.id)
    return resolved


def _finish(p, state, budget, window, extensions, proto: Protocol) -> None:
    persistence.save(state, p.state)
    save_budget(budget, p.budget)
    _save_json(p.window, window)
    _save_json(p.extensions, extensions)
    site.render(p.docs_index, p.docs_data, {
        "snapshot": _snapshot(state),
        "budget": {"spent_eur": budget.spent_eur, "cap_eur": budget.cap_eur, "runs": budget.runs},
        "window": window,
        "extensions": extensions,
        "protocol": proto.all(),
    })


def runs_per_week_value() -> int:
    return runs_per_week()
