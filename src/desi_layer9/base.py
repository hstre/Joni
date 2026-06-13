"""The common base for every Layer-9 epistemic object.

Every object carries the same governance metadata: identity, status, authority,
machine-readable provenance, derivation, validity window, support, taint, and the
ledger event that last touched it. ``confidence_or_support`` is an internal support
metric in [0, 1] - **not a probability** and never to be presented as one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import Authority, ObjectType, Status
from .provenance import Provenance
from .taint import Taint


@dataclass
class EpistemicObject:
    id: str = ""
    object_type: ObjectType = ObjectType.CLAIM
    created_tick: int = 0
    last_changed_tick: int = 0
    status: Status = Status.CANDIDATE
    authority: Authority = Authority.UNTRUSTED
    provenance: Provenance = field(default_factory=Provenance)
    derived_from: tuple[str, ...] = ()
    scope: tuple[str, ...] = ()
    valid_from: int | None = None
    valid_until: int | None = None
    confidence_or_support: float = 0.5   # [0,1] support, NOT a probability
    taint: Taint = field(default_factory=Taint)
    created_by: str = "unknown"          # operator/actor that created it
    reviewed_by: str = ""                # who reviewed it (model/human), or ""
    ledger_event: str | None = None      # the L9-#### that last changed it

    def common_dict(self) -> dict:
        return {
            "id": self.id,
            "object_type": self.object_type.value,
            "created_tick": self.created_tick,
            "last_changed_tick": self.last_changed_tick,
            "status": self.status.value,
            "authority": self.authority.value,
            "provenance": self.provenance.to_dict(),
            "derived_from": list(self.derived_from),
            "scope": list(self.scope),
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "confidence_or_support": self.confidence_or_support,
            "taint": self.taint.to_dict(),
            "created_by": self.created_by,
            "reviewed_by": self.reviewed_by,
            "ledger_event": self.ledger_event,
        }
