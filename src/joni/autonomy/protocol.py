"""The protocol - an append-only record of everything Joni does off the leash.

Every autonomous action - a paper fetched, a relevance judgement (and which tier
made it, at what cost), an improvement applied, an ask raised, budget spent - is one
line here. The public website is just a rendering of this file. Nothing Joni does is
allowed to be invisible.

Append-only and plain JSONL, in the spirit of the DESi ledger: readable, diff-able,
never rewritten.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class ProtocolEvent:
    ts: str
    cycle: int
    kind: str                 # fetched | judged | improved | asked | spent | tick | note | retired
    summary: str
    refs: dict = field(default_factory=dict)   # arbitrary structured detail
    model: str = "deterministic"
    cost_eur: float = 0.0


class Protocol:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: ProtocolEvent) -> ProtocolEvent:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event

    def record(self, cycle: int, kind: str, summary: str, **kw) -> ProtocolEvent:
        event = ProtocolEvent(
            ts=datetime.now(UTC).isoformat(timespec="seconds"),
            cycle=cycle, kind=kind, summary=summary,
            refs=kw.get("refs", {}), model=kw.get("model", "deterministic"),
            cost_eur=round(kw.get("cost_eur", 0.0), 6),
        )
        return self.append(event)

    def all(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def next_cycle(self) -> int:
        events = self.all()
        return (max((e.get("cycle", 0) for e in events), default=0) + 1) if events else 1
