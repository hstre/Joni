"""Personal Store — Joni's model of the operator, subordinate to the constitution and strictly
separate from Layer 9 (docs/PERSONAL_STATE.md). Phase 1: Preferences + Projects, self only.

Design rules made STRUCTURAL here, not left to an LLM:
  * the system may write at most ``inferred``; only an explicit human/tool call creates
    ``confirmed``, and it must carry a provenance ref — there is no system path to ``confirmed``;
  * the use-policy is a pure function of (status, subject, sensitive): a claim that is stored is
    not thereby usable; sensitive / third-party / rejected / outdated are gated deterministically;
  * every write appends a ``personal_write`` event to the append-only protocol (audit).

Stdlib only, deterministic (ticks are passed in, never wall-clock).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path


class Status(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"
    OUTDATED = "outdated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class Use(StrEnum):
    ASSERT = "assert"        # confirmed self-fact: usable as a basis, openly referenceable
    SOFT = "soft"            # may colour phrasing, never asserted as fact
    INTERNAL = "internal"    # never in outputs shared beyond the operator
    NONE = "none"            # never used, never resurfaced


CATEGORIES = frozenset({"preferences", "projects"})   # phase-1 scope

# conservative per-category half-lives in days (docs §13); calibrated later, decay wired later
HALFLIFE_DAYS = {"preferences": 180, "goals": 90, "projects": 45, "relationships": 21}

DEFAULT_HALFLIFE_DAYS = 90
RECONFIRM_BELOW = 0.7   # surface for re-confirmation once the weight decays past this
OUTDATED_BELOW = 0.5    # mark outdated (unusable until re-confirmed) once it decays past this
_ACTIVE = (Status.OBSERVED, Status.INFERRED, Status.CONFIRMED)


@dataclass(frozen=True)
class PersonalClaim:
    id: str
    subject: str                       # "self" in phase 1; "other:<hash>" later
    category: str
    statement: str
    why: str = ""
    status: Status = Status.INFERRED
    sensitive: bool = False
    provenance: tuple[str, ...] = ()   # audit / confirmation refs
    created_tick: int = 0
    confirmed_tick: int | None = None
    tags: tuple[str, ...] = ()

    def to_json(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["provenance"] = list(self.provenance)
        d["tags"] = list(self.tags)
        return d

    @staticmethod
    def from_json(d: dict) -> PersonalClaim:
        return PersonalClaim(
            id=d["id"], subject=d["subject"], category=d["category"], statement=d["statement"],
            why=d.get("why", ""), status=Status(d.get("status", "inferred")),
            sensitive=bool(d.get("sensitive", False)), provenance=tuple(d.get("provenance", ())),
            created_tick=int(d.get("created_tick", 0)), confirmed_tick=d.get("confirmed_tick"),
            tags=tuple(d.get("tags", ())))


def use_policy(claim: PersonalClaim) -> Use:
    """Deterministic use-gate (docs §7): a stored claim is NOT thereby usable."""
    if claim.status in (Status.REJECTED, Status.OUTDATED, Status.SUPERSEDED):
        return Use.NONE
    if claim.sensitive or claim.subject != "self":
        return Use.INTERNAL
    if claim.status == Status.CONFIRMED:
        return Use.ASSERT
    return Use.SOFT   # observed / inferred


def weight(claim: PersonalClaim, now_tick: int) -> float:
    """Exponential decay in (0, 1] by the category half-life (ticks are DAYS for this store).
    Clock references the last freshening — ``confirmed_tick`` if set, else ``created_tick``;
    re-confirming resets it. Analogous to Layer 9's temporal half-lives."""
    ref = claim.confirmed_tick if claim.confirmed_tick is not None else claim.created_tick
    elapsed = max(0, now_tick - ref)
    half = HALFLIFE_DAYS.get(claim.category, DEFAULT_HALFLIFE_DAYS)
    return 0.5 ** (elapsed / half)


class PersonalStore:
    """``state/personal.json`` + append-only protocol audit. Fail-safe on the confirm rule."""

    def __init__(self, state_path, protocol_path) -> None:
        self.state_path = Path(state_path)
        self.protocol_path = Path(protocol_path)
        self._claims: dict[str, PersonalClaim] = {}
        self._load()

    def _load(self) -> None:
        if self.state_path.exists():
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self._claims = {c["id"]: PersonalClaim.from_json(c) for c in data.get("claims", [])}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "claims": [c.to_json() for c in self._claims.values()]}
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    def _audit(self, action: str, claim: PersonalClaim) -> None:
        self.protocol_path.parent.mkdir(parents=True, exist_ok=True)
        ev = {"kind": "personal_write", "action": action, "id": claim.id,
              "subject": claim.subject, "category": claim.category,
              "status": claim.status.value, "sensitive": claim.sensitive}
        with self.protocol_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def get(self, cid: str):
        return self._claims.get(cid)

    def all(self):
        return tuple(self._claims.values())

    def _put(self, claim: PersonalClaim, action: str) -> PersonalClaim:
        if claim.category not in CATEGORIES:
            raise ValueError(f"category {claim.category!r} not in scope {sorted(CATEGORIES)}")
        self._claims[claim.id] = claim
        self._save()
        self._audit(action, claim)
        return claim

    def observe(self, cid, category, statement, *, subject="self", why="", sensitive=False,
                tick=0, tags=()) -> PersonalClaim:
        return self._put(PersonalClaim(cid, subject, category, statement, why, Status.OBSERVED,
                                       sensitive, (), tick, None, tuple(tags)), "observe")

    def infer(self, cid, category, statement, *, subject="self", why="", sensitive=False,
              tick=0, tags=()) -> PersonalClaim:
        return self._put(PersonalClaim(cid, subject, category, statement, why, Status.INFERRED,
                                       sensitive, (), tick, None, tuple(tags)), "infer")

    def confirm(self, cid, *, human_ref, tick=0) -> PersonalClaim:
        """Elevate an existing claim to ``confirmed``. Reachable ONLY with an explicit human/tool
        provenance ref — structural: there is no system path to ``confirmed``."""
        if not human_ref:
            raise PermissionError("confirmed requires an explicit human/tool provenance ref")
        c = self._claims.get(cid)
        if c is None:
            raise KeyError(cid)
        return self._put(replace(c, status=Status.CONFIRMED, confirmed_tick=tick,
                                 provenance=c.provenance + (str(human_ref),)), "confirm")

    def reject(self, cid, *, ref="") -> PersonalClaim:
        c = self._claims.get(cid)
        if c is None:
            raise KeyError(cid)
        prov = c.provenance + ((str(ref),) if ref else ())
        return self._put(replace(c, status=Status.REJECTED, provenance=prov), "reject")

    def age(self, now_tick: int) -> list[str]:
        """Maintenance pass: transition active claims decayed past OUTDATED_BELOW to
        ``outdated`` (use_policy -> NONE). Deterministic given ``now_tick``; audited."""
        aged: list[str] = []
        for cid, c in list(self._claims.items()):
            if c.status in _ACTIVE and weight(c, now_tick) <= OUTDATED_BELOW:
                self._put(replace(c, status=Status.OUTDATED), "outdated")
                aged.append(cid)
        return aged

    def due_for_reconfirm(self, now_tick: int) -> list[PersonalClaim]:
        """Read-only: claims worth surfacing for re-confirmation — already ``outdated``,
        or active but decayed past RECONFIRM_BELOW. Most-decayed first. Surfacing is the caller job;
        a re-confirmation routes back through confirm(), a contradiction through reject()."""
        due = [c for c in self._claims.values()
               if c.status == Status.OUTDATED
               or (c.status in _ACTIVE and weight(c, now_tick) <= RECONFIRM_BELOW)]
        return sorted(due, key=lambda c: (weight(c, now_tick), c.id))
