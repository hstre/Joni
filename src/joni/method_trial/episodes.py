"""S0 of the Procedural Skill Consolidator (design note §6): the procedural episode.

A procedural episode is the atom the later stages induce over: ``(context, action, observation,
belastbarer Ausgang)`` - *in this situation, this action was taken, this was observed, with this
robust outcome*. It is built **read-only from real state** (measured trials now; PR outcomes and
Layer-9 status transitions on the same object next), so nothing is invented.

Two hard rules mirror the metacognition episode model (from which we reuse ``Outcome`` and
``ROBUST_OUTCOME_SOURCES`` as the one canonical vocabulary):

  * **``unknown`` stays ``unknown``.** A resolved outcome (success/failure/mixed) is only admitted
    when it rests on a *belastbare* source (``ROBUST_OUTCOME_SOURCES``); an episode with no such
    source stays ``unknown`` and is never silently upgraded. The extractor never *guesses* an
    outcome - a signal we cannot robustly classify yields no episode.
  * **No LLM reflection value.** Outcomes come from the deterministic checker / gate / CI - never
    from a model's self-assessment. This is the same boundary the whole architecture keeps.

An episode references real ids (``refs``) so a reader can check it against the core. It stores no
prompt/answer/secret - only ids, short categories and one bounded, pre-cleaned detail string.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..autonomy.metacognition.models import ROBUST_OUTCOME_SOURCES, Outcome

EPISODE_VERSION = "episode-v1"

# a measured sandbox verdict -> (outcome, its belastbare source). Everything else stays unknown.
_VERDICT_OUTCOME = {
    "benefit": (Outcome.SUCCESS, "deterministic_checker"),
    "harmful": (Outcome.FAILURE, "deterministic_checker"),
    "no_benefit": (Outcome.MIXED, "deterministic_checker"),
}

_EPISODE_FIELDS = frozenset({
    "context", "action", "observation", "outcome", "outcome_source", "refs", "cycle", "detail",
})


def _nonempty_str(name: str, v: object) -> None:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name} must be a non-empty str")


@dataclass(frozen=True)
class ProceduralEpisode:
    """One read-only, append-only procedural episode: (context, action, observation, outcome)."""

    context: str                              # the situation (e.g. "benchmark:frozen_unit_eq_v1")
    action: str                               # what was done (e.g. "apply_method:M-1")
    observation: str                          # what was measured (e.g. "delta=0.4 vs baseline")
    outcome: Outcome = Outcome.UNKNOWN        # success/failure/mixed only with a robust source
    outcome_source: str = ""                  # in ROBUST_OUTCOME_SOURCES when outcome != unknown
    refs: tuple[str, ...] = field(default_factory=tuple)   # real, checkable ids
    cycle: int = 0
    detail: str = ""                          # bounded, pre-cleaned; no prose/secrets

    def __post_init__(self) -> None:
        for name in ("context", "action", "observation"):
            _nonempty_str(name, getattr(self, name))
        if not isinstance(self.outcome, Outcome):
            raise ValueError("outcome must be an Outcome")
        if self.outcome is Outcome.UNKNOWN:
            if self.outcome_source:
                raise ValueError("an 'unknown' outcome must not claim a source")
        elif self.outcome_source not in ROBUST_OUTCOME_SOURCES:
            # unknown stays unknown: a resolved outcome needs a belastbare source
            raise ValueError(
                f"a resolved outcome needs a robust source, got {self.outcome_source!r}")
        if not isinstance(self.refs, tuple) or not self.refs:
            raise ValueError("refs must be a non-empty tuple of real ids")
        for r in self.refs:
            _nonempty_str("ref", r)
        if not isinstance(self.cycle, int) or isinstance(self.cycle, bool) or self.cycle < 0:
            raise ValueError("cycle must be an int >= 0")
        if not isinstance(self.detail, str):
            raise ValueError("detail must be a str")

    def episode_id(self) -> str:
        blob = json.dumps({"c": self.context, "a": self.action, "s": self.outcome_source,
                           "r": sorted(self.refs), "y": self.cycle},
                          sort_keys=True, ensure_ascii=False)
        return "ep-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def flow_key(self) -> tuple[str, str]:
        """The (context, action) signature S2 groups recurrent flows on. S0 only records; the
        abstraction over flows is S2's job."""
        return (self.context, self.action)

    def is_resolved(self) -> bool:
        return self.outcome is not Outcome.UNKNOWN

    def to_record(self) -> dict:
        return {"episode_id": self.episode_id(), "monitor_version": EPISODE_VERSION,
                "context": self.context, "action": self.action, "observation": self.observation,
                "outcome": self.outcome.value, "outcome_source": self.outcome_source,
                "refs": list(self.refs), "cycle": self.cycle, "detail": self.detail[:200]}

    @staticmethod
    def from_record(d: dict) -> ProceduralEpisode:
        if not isinstance(d, dict):
            raise ValueError("episode record must be a dict")
        extra = set(d) - _EPISODE_FIELDS - {"episode_id", "monitor_version"}
        if extra:
            raise ValueError(f"unknown episode field(s): {sorted(extra)}")
        return ProceduralEpisode(
            context=d["context"], action=d["action"], observation=d["observation"],
            outcome=Outcome(d.get("outcome", "unknown")),
            outcome_source=d.get("outcome_source", ""), refs=tuple(d.get("refs", ())),
            cycle=int(d.get("cycle", 0)), detail=d.get("detail", ""))


def from_trial(trial: dict, *, cycle: int) -> ProceduralEpisode | None:
    """Form a procedural episode from one measured sandbox-trial result (the shape lifecycle /
    skill_lifecycle put in ``extensions``). Returns None - nothing invented - when the verdict is
    not a robustly classifiable outcome (e.g. ``no_solver``: the method was never actually applied)
    or the method id is missing. The outcome rests on the deterministic checker, never a model."""
    if not isinstance(trial, dict):
        return None
    verdict = str(trial.get("verdict", ""))
    if verdict not in _VERDICT_OUTCOME:
        return None                                    # unknown/no_solver -> no episode, no guess
    outcome, source = _VERDICT_OUTCOME[verdict]
    method_id = str(trial.get("method") or trial.get("method_id") or "").strip()
    if not method_id:
        return None
    task_set = str(trial.get("task_set") or "").strip() or "unknown_benchmark"
    skill_id = str(trial.get("skill_id") or "").strip()
    refs = tuple(r for r in (method_id, skill_id) if r)
    return ProceduralEpisode(
        context=f"benchmark:{task_set}",
        action=f"apply_method:{method_id}",
        observation=f"delta={trial.get('delta')} vs baseline (misclassification_rate)",
        outcome=outcome, outcome_source=source, refs=refs, cycle=cycle,
        detail=f"{trial.get('name', '')} :: {verdict}"[:200])


def extract_from_run(cs, extensions: dict, *, cycle: int) -> list[ProceduralEpisode]:
    """Read-only: form procedural episodes from the run's real, measured signals. Today that is the
    sandbox trials and skill re-trials this cycle produced (both robustly checked); PR outcomes and
    Layer-9 status transitions are the next extractors on the same object. Never raises - a bad
    signal row is skipped, not fatal; nothing is invented."""
    eps: list[ProceduralEpisode] = []
    for key in ("sandbox_trials", "skill_retrials"):
        for row in extensions.get(key, []) or []:
            try:
                ep = from_trial(row, cycle=cycle)
            except (ValueError, TypeError):
                ep = None
            if ep is not None:
                eps.append(ep)
    return eps


def record(episodes: list, *, store_path) -> int:
    """Append episodes to the append-only store (never rewrites earlier lines). De-dupes within this
    write by ``episode_id``. Returns the number written. Fail-open: 0 if the store is unwritable."""
    if store_path is None or not episodes:
        return 0
    seen, lines = set(), []
    for ep in episodes:
        eid = ep.episode_id()
        if eid in seen:
            continue
        seen.add(eid)
        lines.append(json.dumps(ep.to_record(), ensure_ascii=False))
    if not lines:
        return 0
    try:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        with store_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        return 0
    return len(lines)


def load(store_path) -> list[ProceduralEpisode]:
    """Latest record per ``episode_id`` from the append-only store (last line wins). Malformed
    lines are skipped. [] when the store is missing/unreadable. (S2 reads episodes through here.)"""
    if store_path is None:
        return []
    try:
        text = store_path.read_text(encoding="utf-8")
    except OSError:
        return []
    latest: dict[str, ProceduralEpisode] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            ep = ProceduralEpisode.from_record(json.loads(line))
        except (ValueError, json.JSONDecodeError):
            continue
        latest[ep.episode_id()] = ep
    return list(latest.values())


__all__ = ["ProceduralEpisode", "from_trial", "extract_from_run", "record", "load",
           "EPISODE_VERSION"]
