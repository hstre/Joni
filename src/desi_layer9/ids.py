"""Replay-stable id minting.

Ids are sequential per prefix (``C-1``, ``M-3``, ``L9-7741``) handed out in a
deterministic order by counters. No PRNG: the same operator sequence always yields the
same ids, which is what makes the whole authoritative state replayable from the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import ObjectType

# Short id prefixes per object class.
PREFIX: dict[ObjectType, str] = {
    ObjectType.CLAIM: "C",
    ObjectType.EVIDENCE: "E",
    ObjectType.EVIDENCE_LINK: "EL",
    ObjectType.CONSTRAINT: "CN",
    ObjectType.GOAL: "G",
    ObjectType.PREFERENCE: "PR",
    ObjectType.PROJECT: "P",
    ObjectType.METHOD: "M",
    ObjectType.MEMORY_EPISODE: "MEM",
    ObjectType.CONFLICT: "X",
    ObjectType.DECISION: "D",
    ObjectType.PROPOSAL: "PROP",
    ObjectType.REVIEW: "RV",
    ObjectType.SOURCE: "SRC",
    ObjectType.LEDGER_EVENT: "L9",
    ObjectType.OPERATIONAL_STATE: "OS",
    ObjectType.SELF_MODEL_CLAIM: "SM",
    ObjectType.NARRATIVE_SUMMARY: "NS",
}


@dataclass
class IdMinter:
    counters: dict[str, int] = field(default_factory=dict)

    def next(self, object_type: ObjectType) -> str:
        prefix = PREFIX[object_type]
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return f"{prefix}-{self.counters[prefix]}"

    def to_dict(self) -> dict[str, int]:
        return dict(self.counters)

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> IdMinter:
        return cls(counters={k: int(v) for k, v in d.items()})
