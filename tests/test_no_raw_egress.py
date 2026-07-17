"""Phase 1 of the egress gate (docs/EGRESS_GATE.md §8/§11): no module may reach the outside world
through a raw primitive except the small, explicit allowlist below.

This is the enforcement that makes the effect broker real rather than cosmetic: the broker can only
be the single egress path if nothing else is allowed to import ``urllib.request`` / ``requests`` /
``socket`` / ``subprocess`` / ``openai`` etc. directly. Today the allowlist is the set of de-facto
brokers (network fetch, the model client, the git subprocess); when the broker module lands it
shrinks to just the broker. Any NEW module that adds raw egress fails here and must go via the
broker (or be added to the allowlist deliberately, with review).

Scope: the ``joni`` package (``src/joni``). Operator-run scripts under ``scripts/`` are out of it.
Note: ``urllib.parse`` is URL-string handling, NOT egress, and is deliberately not matched.
"""
from __future__ import annotations

import ast
from pathlib import Path

_NETWORK = {"requests", "httpx", "aiohttp", "socket", "smtplib", "ftplib", "paramiko"}

# The de-facto egress brokers today (path relative to repo root). Shrinks to the broker later.
_ALLOW = {
    "network": {
        "src/joni/autonomy/pdf.py",         # fetch a paper PDF (urllib.request)
        "src/joni/autonomy/sources.py",     # fetch fixed research sources (urllib.request)
        "src/joni/method_trial/solver.py",  # DeepSeek HTTP call (urllib.request)
        "src/joni/relay/adapters.py",       # relay HTTP adapters (urllib.request/.error)
    },
    "model_api": {
        "src/joni/autonomy/experts.py",     # expert panel model calls (openai client)
        "src/joni/autonomy/frugal.py",      # frugal executor model calls (openai client)
        "src/joni/autonomy/model_call.py",  # THE model-call channel (openai client)
        "src/joni/model_client.py",         # core model client (openai client)
    },
    "subprocess": {
        "src/joni/relay/__main__.py",       # local `git` invocation
        "src/joni/method_trial/sandbox.py",  # controlled-execution broker: runs an untrusted
                                             # solver in an isolated child (rlimits, import
                                             # allowlist, audit hook, process-group kill). The
                                             # subprocess IS the containment boundary
                                             # (METHOD_SANDBOX_AUFTRAG.md §4).
    },
}


def _category(module: str) -> str | None:
    """Map an imported module path to an egress category, or None if it is not egress."""
    if module.startswith(("urllib.request", "urllib.error", "http.client")):
        return "network"
    top = module.split(".")[0]
    if top in _NETWORK:
        return "network"
    if top == "openai":
        return "model_api"
    if top == "subprocess":
        return "subprocess"
    return None


def _imported_modules(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def test_no_raw_egress_outside_the_allowlist():
    root = Path(__file__).resolve().parents[1]
    pkg = root / "src" / "joni"
    violations: list[str] = []
    for py in sorted(pkg.rglob("*.py")):
        rel = py.relative_to(root).as_posix()
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for module in _imported_modules(tree):
            cat = _category(module)
            if cat is not None and rel not in _ALLOW[cat]:
                violations.append(f"{rel}: imports '{module}' ({cat}) — must go via the broker")
    assert not violations, (
        "Raw egress outside the broker allowlist (docs/EGRESS_GATE.md):\n  "
        + "\n  ".join(violations))
