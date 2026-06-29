"""Governance - the DESi rule Joni runs under when off the leash.

The single hard rule: **Joni may not change his protected DESi core without asking.**
He may research, learn, and build *peripheral* improvements into himself autonomously,
but the core engine - the deterministic state, operators, conflict resolution, router,
persistence, the ledger - is frozen. Any change there is blocked and turned into an
*ask* (a human-approval request), never self-applied.

Two mechanisms enforce it:

  * a **core lock** - a manifest of sha256 hashes of the protected modules. Before any
    autonomous run commits anything, the live hashes are re-checked against the lock; a
    mismatch is a fail-safe stop (the run refuses to proceed).
  * a **write allowlist** - autonomous commits may only touch peripheral data paths
    (state/, protocol/, docs/). Logic lives in the protected core and is off-limits.

This mirrors DESi's own invariants: read-only governance over the protected core, and
human-approval gates for anything that would mutate it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Modules that make up the protected DESi core. Frozen: never auto-modified.
PROTECTED_CORE: tuple[str, ...] = (
    "models.py",
    "state.py",
    "operators.py",
    "conflict.py",
    "router.py",
    "memory.py",
    "persistence.py",
    "loops.py",
    "renderer.py",
    "identity.py",
    "model_client.py",
    "seed.py",
    "autonomy/governance.py",   # the guard guards itself
)

# The vendored DESi engine (``src/desi_layer9/``) IS the protected core too — it carries the
# deterministic state, the gate, the integrity hashing and replay. The lock historically covered
# only ``src/joni/*.py``; Phase A (incremental hashing) touched the kernel, so the lock now covers
# every kernel module — discovered dynamically, so a re-``lock`` always freezes the current set.

# Paths (relative to repo root) autonomous runs are allowed to write/commit.
PERIPHERAL_WRITE_ALLOW: tuple[str, ...] = (
    "state/",
    "protocol/",
    "docs/",
)

LOCK_FILE = "joni_core.lock"


def _package_dir() -> Path:
    return Path(__file__).resolve().parent.parent  # .../src/joni


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _kernel_modules() -> list[str]:
    """Every desi_layer9 kernel module, as a ``desi_layer9/<file>.py`` name relative to ``src/``.
    Discovered dynamically so a re-``lock`` always covers the current engine, additions included."""
    pkg = _package_dir().parent / "desi_layer9"
    return sorted(f"desi_layer9/{p.name}" for p in pkg.glob("*.py"))


def compute_core_hashes() -> dict[str, str]:
    """Current sha256 of every protected-core module — the ``src/joni`` modules plus the whole
    vendored desi_layer9 kernel. ``src/joni`` names resolve against ``src/joni``; ``desi_layer9/..``
    names resolve against ``src``."""
    base = _package_dir()                 # src/joni
    src = base.parent                     # src
    hashes = {name: _sha256(base / name) for name in PROTECTED_CORE}
    for name in _kernel_modules():
        hashes[name] = _sha256(src / name)
    return hashes


def write_lock(repo_root: Path | str = ".") -> Path:
    """Freeze the current core into the lock file (run by a human, not by Joni)."""
    path = Path(repo_root) / LOCK_FILE
    path.write_text(json.dumps(compute_core_hashes(), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def load_lock(repo_root: Path | str = ".") -> dict[str, str]:
    path = Path(repo_root) / LOCK_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def verify_core(repo_root: Path | str = ".") -> tuple[bool, list[str]]:
    """Check the live core against the lock. Returns (ok, list of changed modules).

    A missing lock is treated as 'not yet frozen' (ok=True, empty) so a fresh clone
    does not hard-fail; CI runs ``lock`` first. A present lock that disagrees is a
    governance violation.
    """
    lock = load_lock(repo_root)
    if not lock:
        return True, []
    live = compute_core_hashes()
    changed = sorted(
        name for name in set(lock) | set(live) if lock.get(name) != live.get(name)
    )
    return (not changed), changed


class CoreChangeBlocked(RuntimeError):
    """Raised when an autonomous run would touch the protected core."""


def assert_core_unchanged(repo_root: Path | str = ".") -> None:
    """Fail-safe: stop the autonomous run if the protected core was altered."""
    ok, changed = verify_core(repo_root)
    if not ok:
        raise CoreChangeBlocked(
            "Protected DESi core changed without approval: "
            + ", ".join(changed)
            + ". Autonomous run refuses to proceed - this requires a human."
        )


def is_peripheral_path(path: str) -> bool:
    """Whether a path is inside the autonomous write allowlist."""
    norm = path.lstrip("./")
    return any(norm == p.rstrip("/") or norm.startswith(p) for p in PERIPHERAL_WRITE_ALLOW)


# --------------------------------------------------------------------------- #
# Classifying a proposed self-improvement
# --------------------------------------------------------------------------- #

# Improvement kinds Joni may apply to *himself* autonomously (peripheral, data-level).
PERIPHERAL_KINDS: frozenset[str] = frozenset(
    {"track_topic", "add_source", "note_capability"}
)
# Anything that would need new logic in the protected core. Ask-only.
CORE_KINDS: frozenset[str] = frozenset({"core_change"})


def is_autonomous(kind: str) -> bool:
    """True if Joni may build this kind of improvement in by himself."""
    return kind in PERIPHERAL_KINDS


def requires_human(kind: str) -> bool:
    """True if this kind must be raised as an ask and left for a human."""
    return kind not in PERIPHERAL_KINDS
