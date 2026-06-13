"""Migration of the existing Joni state and Kevin methods into the one core.

The old informal stores are not discarded: they are imported into Layer 9 through the
gate (so every imported object is audited and replayable), conservatively. Old Kevin
methods come in as **provisional** (a single migration gate - never straight to active).
Old Joni claims come in at most **active**, never auto-confirmed - re-confirmation must
go through the gate. Uninterpretable rows are **quarantined and reported**, not dropped.

Migration is deterministic and idempotent: the same inputs always produce the same
journal and snapshot hash.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .core import Layer9, make_proposal
from .enums import MemoryKind, Operator, ProposalType, Status
from .objects import Claim, Method
from .provenance import Provenance

# Old Joni claim status -> conservative new status (confirmed -> active: re-earn it).
_CLAIM_STATUS_MAP = {
    "tentative": Status.CANDIDATE,
    "active": Status.ACTIVE,
    "confirmed": Status.ACTIVE,
    "rejected": Status.REJECTED,
    "superseded": Status.SUPERSEDED,
}
# Minimal valid revise path from CANDIDATE to a target (see transition tables).
_CLAIM_PATH = {
    Status.CANDIDATE: (),
    Status.ACTIVE: (Status.ACTIVE,),
    Status.REJECTED: (Status.REJECTED,),
    Status.SUPERSEDED: (Status.ACTIVE, Status.SUPERSEDED),
    Status.QUARANTINED: (Status.QUARANTINED,),
}

_IMPORTED = Provenance.imported()
_OPERATOR_ACTOR = "migration"


@dataclass
class MigrationReport:
    imported: int = 0
    quarantined: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    def _bump(self, key: str) -> None:
        self.counts[key] = self.counts.get(key, 0) + 1


def _create_claim(core: Layer9, text: str, topic: str, target: Status) -> str:
    core.submit(make_proposal(
        ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
        payload={"text": text, "topic": topic}, proposer="migration",
        provenance=_IMPORTED), actor=_OPERATOR_ACTOR)
    # the created claim is the most recent CLAIM object
    claim = max((o for o in core.objects.values() if isinstance(o, Claim)),
                key=lambda o: int(o.id.split("-")[1]))
    for step in _CLAIM_PATH.get(target, ()):
        core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
            payload={"to_status": step.value}, proposer="migration",
            provenance=_IMPORTED, target_objects=(claim.id,)), actor=_OPERATOR_ACTOR)
    return claim.id


def _quarantine(core: Layer9, raw: str, report: MigrationReport) -> None:
    _create_claim(core, f"[quarantined import] {raw[:200]}", "quarantine", Status.QUARANTINED)
    report.quarantined.append(raw[:200])
    report._bump("quarantined")


def import_kevin_methods(core: Layer9, jsonl_text: str, report: MigrationReport) -> None:
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            name = rec["name"]
            steps = list(rec.get("steps", []))
        except (json.JSONDecodeError, KeyError):
            _quarantine(core, line, report)
            continue
        core.submit(make_proposal(
            ProposalType.METHOD_PROPOSAL, Operator.METHOD_PROPOSE,
            payload={"name": name, "summary": rec.get("summary", ""), "steps": steps,
                     "origin": rec.get("origin", "imported"),
                     "applicable_to": rec.get("affinities", [])},
            proposer="migration", provenance=_IMPORTED), actor=_OPERATOR_ACTOR)
        # find the method just created and promote once: candidate -> provisional.
        method = max((o for o in core.objects.values() if isinstance(o, Method)),
                     key=lambda o: int(o.id.split("-")[1]))
        core.submit(make_proposal(
            ProposalType.METHOD_PROPOSAL, Operator.METHOD_PROMOTE, payload={},
            proposer="migration", provenance=Provenance.from_operator(),
            target_objects=(method.id,)), actor=_OPERATOR_ACTOR)
        report.imported += 1
        report._bump("methods")


def import_joni_state(core: Layer9, state: dict, report: MigrationReport) -> dict[str, str]:
    """Import old Joni state; returns old_claim_id -> new_claim_id map."""
    idmap: dict[str, str] = {}
    for c in state.get("claims", []):
        try:
            target = _CLAIM_STATUS_MAP.get(c.get("status", "tentative"), Status.CANDIDATE)
            new_id = _create_claim(core, c["text"], c.get("topic", ""), target)
            idmap[c["id"]] = new_id
            report.imported += 1
            report._bump("claims")
        except (KeyError, TypeError):
            _quarantine(core, json.dumps(c)[:200], report)

    for g in state.get("goals", []):
        try:
            core.submit(make_proposal(
                ProposalType.GOAL_PROPOSAL, Operator.GOAL_CREATE,
                payload={"text": g["text"], "horizon": g.get("horizon", "long"),
                         "priority": g.get("priority", 0.5)},
                proposer="migration", provenance=Provenance.from_operator()),
                actor=_OPERATOR_ACTOR)
            report.imported += 1
            report._bump("goals")
        except (KeyError, TypeError):
            _quarantine(core, json.dumps(g)[:200], report)

    for m in state.get("memory", []):
        try:
            core.submit(make_proposal(
                ProposalType.STATE_REVISION_PROPOSAL, Operator.MEMORY_RECORD,
                payload={"kind": MemoryKind.EPISODIC.value, "summary": m["summary"],
                         "refs": [idmap.get(r, r) for r in m.get("refs", [])]},
                proposer="migration", provenance=_IMPORTED), actor=_OPERATOR_ACTOR)
            report.imported += 1
            report._bump("memory")
        except (KeyError, TypeError):
            _quarantine(core, json.dumps(m)[:200], report)

    return idmap


def migrate(*, joni_state: dict | None = None, kevin_jsonl: str | None = None,
            tick: int = 0) -> tuple[Layer9, MigrationReport]:
    """Deterministic, idempotent migration into a fresh Layer 9 core."""
    core = Layer9(tick=tick)
    report = MigrationReport()
    if joni_state is not None:
        import_joni_state(core, joni_state, report)
    if kevin_jsonl is not None:
        import_kevin_methods(core, kevin_jsonl, report)
    return core, report


def backup(path: str | Path) -> Path | None:
    """Copy a file to ``<name>.bak`` before migration touches anything."""
    path = Path(path)
    if not path.exists():
        return None
    dest = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, dest)
    return dest
