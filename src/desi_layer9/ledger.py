"""The audit ledger event.

Every accepted (or rejected) operator application is one ledger event. PR 2 fills the
operational fields; PR 3 hash-chains the ledger (``before_hash`` / ``after_hash`` /
``previous_event_hash`` / ``event_hash``) and adds replay. The hash fields exist here
so the schema is stable across PRs; they are populated in PR 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import Operator


@dataclass
class LedgerEvent:
    id: str
    sequence: int
    tick: int
    operator: Operator
    actor: str
    decision: str                       # submitted | accepted | rejected
    reason: str = ""
    input_refs: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    reviewed_by: str = ""
    cost: float = 0.0
    timestamp: str = ""                 # set at persistence time (PR 3); replay ignores it
    sampling_provenance: dict = field(default_factory=dict)
    # Hash chain - populated in PR 3.
    before_hash: str = ""
    after_hash: str = ""
    previous_event_hash: str = ""
    event_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "sequence": self.sequence, "tick": self.tick,
            "operator": self.operator.value, "actor": self.actor,
            "decision": self.decision, "reason": self.reason,
            "input_refs": list(self.input_refs), "output_refs": list(self.output_refs),
            "reviewed_by": self.reviewed_by, "cost": self.cost,
            "timestamp": self.timestamp, "sampling_provenance": self.sampling_provenance,
            "before_hash": self.before_hash, "after_hash": self.after_hash,
            "previous_event_hash": self.previous_event_hash, "event_hash": self.event_hash,
        }
