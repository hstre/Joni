"""Baustein C — the discoverer: learn method↔gap-kind affinities from trials, holdout-validated.

The honest, tractable form of 'Joni finds deep methods itself': from the ``DeepMethodTrial`` history
it mines which (method-KIND → gap-KIND) pairings *reliably* succeed — including ones the a-priori
taxonomy never listed (``is_new``) — and proposes them as new operator edges. It does NOT synthesise
a novel procedure's STEPS from pass/fail data (needs generative reasoning, out of scope); it
discovers TRANSFERS/affinities, which is exactly what feeds Baustein B's ``extra_kind_affinities``.

The load-bearing discipline, carried from the method-trial batteries: a discovered edge is only
**confirmed** if it also holds on a HELD-OUT set of gaps. The split is by gap id (the pre-registered
independence unit — a whole gap is train or holdout, never both), so a train-only fluke fails the
gate. Deterministic given a history; the synthetic benchmark measures the mechanism's
false-positive / false-negative rates against a known ground truth.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from joni.method_trial import deep_methods as D

from .operators import _METHOD_KINDS_BY_GAP

_REAL_SIGNAL = ("success", "no_benefit", "harmful")   # trials that carry a methodological signal


@dataclass(frozen=True)
class DiscoveredAffinity:
    method_kind: str
    gap_kind: str
    train_rate: float
    holdout_rate: float
    support_train: int
    support_holdout: int
    is_new: bool                           # not in the a-priori taxonomy for this gap_kind
    confirmed: bool                        # passed the holdout gate


def _in_holdout(target: str, holdout_pct: int) -> bool:
    h = int(hashlib.sha256(target.encode()).hexdigest()[:8], 16) % 100
    return h < holdout_pct


def _method_kind(method_id: str) -> str | None:
    m = D.by_id(method_id)
    return m.kind if m else None


def _rates(trials) -> dict[tuple[str, str], list[int]]:
    """(method_kind, gap_kind) -> [successes, real_signal_total] over the given trials."""
    agg: dict[tuple[str, str], list[int]] = {}
    for t in trials:
        if t.result not in _REAL_SIGNAL:
            continue
        mk = _method_kind(t.method_id)
        if mk is None or not t.gap_kind or t.gap_kind == "unknown":
            continue
        key = (mk, t.gap_kind)
        cell = agg.setdefault(key, [0, 0])
        cell[1] += t.count
        if t.result == "success":
            cell[0] += t.count
    return agg


def _is_new(method_kind: str, gap_kind: str) -> bool:
    listed = dict(_METHOD_KINDS_BY_GAP.get(gap_kind, ()))
    return method_kind not in listed


def discover_affinities(trials, *, holdout_pct: int = 30, min_support: int = 4,
                        min_rate: float = 0.6) -> list[DiscoveredAffinity]:
    """Mine (method_kind → gap_kind) edges that succeed on TRAIN and hold up on the HELD-OUT gaps.
    Returns every candidate (train support >= ``min_support`` and train rate >= ``min_rate``) with a
    ``confirmed`` flag set iff it ALSO clears the same bar on holdout. Deterministic."""
    train = [t for t in trials if not _in_holdout(t.target, holdout_pct)]
    hold = [t for t in trials if _in_holdout(t.target, holdout_pct)]
    tr, ho = _rates(train), _rates(hold)

    out: list[DiscoveredAffinity] = []
    for key, (succ, tot) in tr.items():
        if tot < min_support:
            continue
        train_rate = succ / tot
        if train_rate < min_rate:
            continue
        hs, ht = ho.get(key, [0, 0])
        holdout_rate = (hs / ht) if ht else 0.0
        confirmed = ht >= min_support and holdout_rate >= min_rate
        out.append(DiscoveredAffinity(
            method_kind=key[0], gap_kind=key[1], train_rate=round(train_rate, 4),
            holdout_rate=round(holdout_rate, 4), support_train=tot, support_holdout=ht,
            is_new=_is_new(key[0], key[1]), confirmed=confirmed))
    out.sort(key=lambda d: (-d.holdout_rate, -d.train_rate, d.gap_kind, d.method_kind))
    return out


def to_extra_affinities(discovered, *, only_confirmed: bool = True) -> dict:
    """Turn discovered edges into the ``extra_kind_affinities`` dict Baustein B consumes; the edge
    weight is its HOLD-OUT success rate (validated evidence, not the train-set optimism)."""
    extra: dict[str, list[tuple[str, float]]] = {}
    for d in discovered:
        if only_confirmed and not d.confirmed:
            continue
        extra.setdefault(d.gap_kind, []).append((d.method_kind, round(d.holdout_rate, 4)))
    return {gk: tuple(v) for gk, v in extra.items()}


def discovery_report(trials, **kwargs) -> dict:
    """A human-facing summary of what the discoverer learned: the CONFIRMED edges (held up on
    holdout), the CANDIDATES that cleared train but not holdout, and how many are NEW (absent from
    the a-priori taxonomy). Honest: an empty/thin history yields an empty confirmed set."""
    disc = discover_affinities(trials, **kwargs)
    confirmed = [d for d in disc if d.confirmed]
    candidates = [d for d in disc if not d.confirmed]

    def _row(d):
        return {"method_kind": d.method_kind, "gap_kind": d.gap_kind, "train_rate": d.train_rate,
                "holdout_rate": d.holdout_rate, "support_train": d.support_train,
                "support_holdout": d.support_holdout, "is_new": d.is_new}

    return {
        "n_trials": len(list(trials)),
        "n_confirmed": len(confirmed),
        "n_confirmed_new": sum(1 for d in confirmed if d.is_new),
        "confirmed": [_row(d) for d in confirmed],
        "candidates_unconfirmed": [_row(d) for d in candidates],
    }
