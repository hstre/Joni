"""H0 of HindsightTag (design-notes/HINDSIGHT_REVIEW.md §4/§9): the provisional-episodic layer.

The middle memory layer between the ephemeral working context and Layer 9. It holds things that
survive the immediate step but are NOT yet a settled state - observations, weak hints, unfinished
hypotheses, unusual events, open contradictions, ambiguous statements. It is a **staging zone**,
read-only with respect to Layer 9 and append-only in itself: nothing here is a store of record and
nothing consolidates itself (later stages H2/H3 add the review-trigger and the Layer-9 proposal;
this stage is only the object + its first, deterministic lifecycle transition).

Two quantities are kept **separate** on every entry (the central refinement over the paper):
  * ``attention_salience`` - how striking / novel / urgent it is; may be cheap/heuristic;
  * ``epistemic_significance`` - how much it would change a claim / conflict / decision; MEASURED,
    not LLM-estimated (0.0 until a later stage measures it). Only the epistemic quantity may ever
    pull toward consolidation; attention only governs what gets tagged and reactivated.

H0 acceptance: an entry moves ``ephemeral -> provisional`` deterministically; nothing is invented;
``unknown`` stays ``unknown``. Higher transitions (tagged / review_due / consolidated / …) are
defined in the enum for completeness but implemented in later stages.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import StrEnum

PROVISIONAL_VERSION = "provisional-v1"

# Default: an ephemeral entry settles into provisional only if it is at least mildly salient;
# otherwise it is left to expire. Deliberately a low bar - the point of the layer is to KEEP things
# briefly checkable, not to pre-judge them. The threshold is a dial, not a truth.
SETTLE_THRESHOLD = 0.25
DEFAULT_TTL = 24                      # cycles an entry stays checkable before it expires


class EntryKind(StrEnum):
    OBSERVATION = "observation"              # a noticed fact of the run
    WEAK_HINT = "weak_hint"                  # a faint signpost (e.g. a barred pattern hint)
    UNFINISHED_HYPOTHESIS = "unfinished_hypothesis"
    UNUSUAL_EVENT = "unusual_event"          # an out-of-distribution tool output / occurrence
    OPEN_CONTRADICTION = "open_contradiction"
    AMBIGUOUS = "ambiguous"                  # a statement whose meaning is not yet clear


class LifecycleStage(StrEnum):
    EPHEMERAL = "ephemeral"                  # just written; may not survive the step
    PROVISIONAL = "provisional"              # survived; checkable, not yet a settled state
    TAGGED = "tagged"                        # H1: carries a short-lived tag + capture window
    REVIEW_DUE = "review_due"                # H2: a later event reactivated it for review
    EXPIRED = "expired"                      # lifetime elapsed with no rescue
    CONSOLIDATED = "consolidated"            # H3: proposed into Layer 9 (human/gate decides)
    REJECTED = "rejected"                    # H3: review found it irrelevant
    LINKED_ONLY = "linked_only"              # H3: associative link only, no claim
    CONTRADICTION_DETECTED = "contradiction_detected"   # H3: feeds conflict condensation (#5)
    HYPOTHESIS_OPENED = "hypothesis_opened"  # H3: review opened a testable hypothesis


_ENTRY_FIELDS = frozenset({
    "kind", "content", "topic", "refs", "source", "stage", "created_cycle", "ttl",
    "tagged_cycle", "attention_salience", "epistemic_significance", "detail",
})


def _nonempty_str(name: str, v: object) -> None:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name} must be a non-empty str")


def _sal(name: str, v: object) -> None:
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.0 <= float(v) <= 1.0):
        raise ValueError(f"{name} must be a number in [0,1]")


@dataclass(frozen=True)
class ProvisionalEntry:
    """One provisional-episodic entry: a thing worth keeping briefly checkable, not yet settled."""

    kind: EntryKind
    content: str                                   # what was noticed (short, pre-cleaned)
    source: str                                    # provenance: where it came from (a short tag)
    topic: str = ""                                # optional topic tag
    refs: tuple[str, ...] = field(default_factory=tuple)     # real ids it references (may be empty)
    stage: LifecycleStage = LifecycleStage.EPHEMERAL
    created_cycle: int = 0
    ttl: int = DEFAULT_TTL
    tagged_cycle: int = -1                          # H1: cycle the tag was applied (-1 = untagged)
    attention_salience: float = 0.0                # cheap/heuristic - how striking (may be 0)
    epistemic_significance: float = 0.0            # MEASURED later - how much it moves the graph
    detail: str = ""                               # bounded, pre-cleaned; no prose/secrets

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EntryKind):
            raise ValueError("kind must be an EntryKind")
        _nonempty_str("content", self.content)
        _nonempty_str("source", self.source)
        if not isinstance(self.topic, str):
            raise ValueError("topic must be a str")
        if not isinstance(self.refs, tuple):
            raise ValueError("refs must be a tuple")
        for r in self.refs:
            _nonempty_str("ref", r)
        if not isinstance(self.stage, LifecycleStage):
            raise ValueError("stage must be a LifecycleStage")
        if not isinstance(self.created_cycle, int) or isinstance(self.created_cycle, bool) \
                or self.created_cycle < 0:
            raise ValueError("created_cycle must be an int >= 0")
        if not isinstance(self.ttl, int) or isinstance(self.ttl, bool) or self.ttl < 1:
            raise ValueError("ttl must be an int >= 1")
        if not isinstance(self.tagged_cycle, int) or isinstance(self.tagged_cycle, bool) \
                or self.tagged_cycle < -1:
            raise ValueError("tagged_cycle must be an int >= -1")
        _sal("attention_salience", self.attention_salience)
        _sal("epistemic_significance", self.epistemic_significance)
        if not isinstance(self.detail, str):
            raise ValueError("detail must be a str")

    def entry_id(self) -> str:
        blob = json.dumps({"k": self.kind.value, "c": self.content, "s": self.source,
                           "y": self.created_cycle}, sort_keys=True, ensure_ascii=False)
        return "prov-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def to_record(self) -> dict:
        return {"entry_id": self.entry_id(), "monitor_version": PROVISIONAL_VERSION,
                "kind": self.kind.value, "content": self.content, "source": self.source,
                "topic": self.topic, "refs": list(self.refs), "stage": self.stage.value,
                "created_cycle": self.created_cycle, "ttl": self.ttl,
                "tagged_cycle": self.tagged_cycle,
                "attention_salience": round(float(self.attention_salience), 4),
                "epistemic_significance": round(float(self.epistemic_significance), 4),
                "detail": self.detail[:200]}

    @staticmethod
    def from_record(d: dict) -> ProvisionalEntry:
        if not isinstance(d, dict):
            raise ValueError("entry record must be a dict")
        extra = set(d) - _ENTRY_FIELDS - {"entry_id", "monitor_version"}
        if extra:
            raise ValueError(f"unknown provisional field(s): {sorted(extra)}")
        return ProvisionalEntry(
            kind=EntryKind(d["kind"]), content=d["content"], source=d["source"],
            topic=d.get("topic", ""), refs=tuple(d.get("refs", ())),
            stage=LifecycleStage(d.get("stage", "ephemeral")),
            created_cycle=int(d.get("created_cycle", 0)), ttl=int(d.get("ttl", DEFAULT_TTL)),
            tagged_cycle=int(d.get("tagged_cycle", -1)),
            attention_salience=d.get("attention_salience", 0.0),
            epistemic_significance=d.get("epistemic_significance", 0.0),
            detail=d.get("detail", ""))


def settle(entry: ProvisionalEntry, *, threshold: float = SETTLE_THRESHOLD) -> ProvisionalEntry:
    """The one transition H0 implements: ``ephemeral -> provisional`` iff the entry clears the
    attention-salience bar; otherwise it stays ephemeral (and will expire). Deterministic, pure -
    returns a new entry, never mutates. A non-ephemeral entry is returned unchanged."""
    if entry.stage is not LifecycleStage.EPHEMERAL:
        return entry
    if entry.attention_salience >= threshold:
        return replace(entry, stage=LifecycleStage.PROVISIONAL)
    return entry


TAG_THRESHOLD = 0.5                   # attention-salience bar to earn a short-lived tag (H1)
CAPTURE_WINDOW = 6                    # cycles a tag stays live and reactivatable (H1/H2)


def tag(entry: ProvisionalEntry, cycle: int, *,
        threshold: float = TAG_THRESHOLD) -> ProvisionalEntry:
    """H1: a PROVISIONAL entry that clears the attention bar earns a short-lived tag - it becomes
    TAGGED and anchors its capture window at ``cycle``. Deterministic, pure. Only a PROVISIONAL
    entry tags (it must survive the step before carrying a tag); others return unchanged."""
    if entry.stage is not LifecycleStage.PROVISIONAL:
        return entry
    if entry.attention_salience >= threshold:
        return replace(entry, stage=LifecycleStage.TAGGED, tagged_cycle=cycle)
    return entry


def in_capture_window(entry: ProvisionalEntry, cycle: int,
                      *, window: int = CAPTURE_WINDOW) -> bool:
    """H2: is this TAGGED entry still within its bounded capture window at ``cycle``? Only a tagged
    entry inside its window can be reactivated by a later event."""
    return (entry.stage is LifecycleStage.TAGGED and entry.tagged_cycle >= 0
            and cycle <= entry.tagged_cycle + window)


def mark_review_due(entry: ProvisionalEntry) -> ProvisionalEntry:
    """H2: a later event reactivated this tagged entry - move it to REVIEW_DUE. Pure. This is only a
    reactivation for review; whether a real relationship exists is decided later (H3), not here."""
    if entry.stage is not LifecycleStage.TAGGED:
        return entry
    return replace(entry, stage=LifecycleStage.REVIEW_DUE)


def is_expired(entry: ProvisionalEntry, current_cycle: int) -> bool:
    """True once the entry's lifetime has elapsed. A settled provisional entry lives its full ttl;
    an ephemeral entry that never settled also expires by the same clock."""
    return current_cycle > entry.created_cycle + entry.ttl


def expire(entry: ProvisionalEntry) -> ProvisionalEntry:
    """Move a lived-out entry to EXPIRED (terminal). Pure; never mutates."""
    return replace(entry, stage=LifecycleStage.EXPIRED)


def record(entries: list, *, store_path) -> int:
    """Append entries to the append-only store (never rewrites earlier lines), de-duped within this
    write by entry_id. Returns the number written. Fail-open: 0 if unwritable."""
    if store_path is None or not entries:
        return 0
    seen, lines = set(), []
    for e in entries:
        eid = e.entry_id()
        if eid in seen:
            continue
        seen.add(eid)
        lines.append(json.dumps(e.to_record(), ensure_ascii=False))
    if not lines:
        return 0
    try:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        with store_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        return 0
    return len(lines)


def load(store_path) -> list[ProvisionalEntry]:
    """Latest record per entry_id from the append-only store (last line wins - so a later stage
    transition supersedes the write). Malformed lines skipped. [] if missing/unreadable."""
    if store_path is None:
        return []
    try:
        text = store_path.read_text(encoding="utf-8")
    except OSError:
        return []
    latest: dict[str, ProvisionalEntry] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            e = ProvisionalEntry.from_record(json.loads(line))
        except (ValueError, json.JSONDecodeError):
            continue
        latest[e.entry_id()] = e
    return list(latest.values())


__all__ = ["EntryKind", "LifecycleStage", "ProvisionalEntry", "settle", "tag", "in_capture_window",
           "mark_review_due", "is_expired", "expire", "record", "load", "SETTLE_THRESHOLD",
           "TAG_THRESHOLD", "CAPTURE_WINDOW", "DEFAULT_TTL", "PROVISIONAL_VERSION"]
