"""DESi link - Joni uses the real DESi routing logic and tools, not a lookalike.

When ``JONI_USE_DESI=1`` and the sibling ``desi-governance`` package is importable,
Joni routes through DESi's own machinery:

  * **the empirical routing table** (`EpistemicRouter`): given a task class, DESi
    returns the Pareto-cheapest capable model and its expected cost - Joni adopts that
    decision and audits the reason. (A free table lookup; Joni classifies the task
    itself, so DESi's paid OpenRouter classifier is never invoked.)
  * **the deterministic tool registry** - and not only arithmetic: ``date_math``,
    ``unit_conversion`` (and ``retrieval`` with a corpus). When a sub-task is exactly
    covered by a tool, Joni uses it: exact, replay-stable, ~$0.

Soft dependency: if DESi is absent or the flag is off, every function here returns
``None`` and Joni falls back to its own frugal layer - deterministic and replay-stable
either way.
"""

from __future__ import annotations

import importlib
import os
import re
import sys


def _desi_router():
    """Return the ``desi_router`` module, or None.

    DESi's router ships as a repo-root ``desi_router/`` package (not part of the
    pip-installed ``desi`` package), so we either import it directly or point at a
    DESi checkout via ``DESI_ROOT``.
    """
    try:
        return importlib.import_module("desi_router")
    except Exception:  # noqa: BLE001
        root = os.getenv("DESI_ROOT")
        if root and os.path.isdir(os.path.join(root, "desi_router")):
            if root not in sys.path:
                sys.path.insert(0, root)
            try:
                return importlib.import_module("desi_router")
            except Exception:  # noqa: BLE001
                return None
        return None

# Joni task patterns -> DESi tool task classes. Deterministic, no model.
_TOOL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("date_math", re.compile(r"\bdays?\s+between\b|[+\-]\s*\d+\s*days?\b", re.I)),
    ("unit_conversion", re.compile(r"\b\d+(?:\.\d+)?\s*[a-z]+\s+(?:in|to)\s+[a-z]+\b", re.I)),
    ("math_arithmetic", re.compile(r"^[\d\s().+\-*/%^]+$")),
]


def available() -> bool:
    return _desi_router() is not None


def enabled() -> bool:
    return os.getenv("JONI_USE_DESI") == "1" and available()


def try_tool(query: str) -> dict | None:
    """Run a DESi deterministic tool if one covers the query. Free, exact, or None."""
    if not enabled():
        return None
    try:
        from desi_router.tool_registry import default_registry
    except Exception:  # noqa: BLE001
        return None
    registry = default_registry()
    q = query.strip()
    for task_class, pattern in _TOOL_PATTERNS:
        if pattern.search(q):
            tool = registry.find(task_class)
            if tool is None:
                continue
            try:
                return {"tool": tool.name, "task_class": task_class, "result": tool.run(q)}
            except Exception:  # noqa: BLE001 - tool said 'inapplicable'; try the next
                continue
    return None


def route_model(task_class: str, *, budget_usd: float) -> dict | None:
    """Ask DESi's routing table for the cheapest capable model for a task class.

    Decision only (free) - returns model + expected cost + DESi's reason. Joni logs
    this; executing the model is a separate, budgeted choice. Valid task classes come
    from DESi's routing_table.json: ``scientific_claim``, ``memory_recall``,
    ``code_audit``.
    """
    if not enabled():
        return None
    try:
        from desi_router.router import EpistemicRouter, RouteRequest
        decision = EpistemicRouter().route(
            RouteRequest(task_class=task_class, cost_budget_usd=budget_usd)
        )
        return {
            "model": decision.model,
            "cost_usd": float(decision.expected_cost_usd),
            "reason": decision.reason,
            "task_class": task_class,
        }
    except Exception:  # noqa: BLE001 - unknown task class / table issue -> fall back
        return None


def routing_engine() -> str:
    return "DESi" if enabled() else "joni-builtin"
