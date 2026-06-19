"""Reconstruction-trick plausibility ranker (Auftrag #135): build a compatible vs contradiction
reading of a claim pair and let the model rank which is more plausible -> the conflict KIND.
Opt-in, bounded, non-core (only chooses a qualify.py marker). Uses Joni's own captured model."""

import desi_layer9 as l9
from joni.autonomy import model_call, plausibility
from joni.autonomy.qualify import qualify_conflict

CK = l9.ConflictKind


def _env(monkeypatch, tmp_path, reply, *, on=True):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_PLAUSIBILITY_QUALIFIER", "1" if on else "0")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda profile, system, user: reply)


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.delenv("JONI_PLAUSIBILITY_QUALIFIER", raising=False)
    assert plausibility.enabled() is False
    assert plausibility.ranker_for() is None


def test_contradiction_reading_wins(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "B")
    r = plausibility.ranker_for(cycle=1)
    assert r("routing is always local", "routing is never local") == CK.CONTRADICTION.value


def test_compatible_reading_wins(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "A")
    r = plausibility.ranker_for(cycle=1)
    assert r("X holds for small inputs", "X fails for huge inputs") == CK.SCOPE_TENSION.value


def test_ranker_is_bounded_per_cycle(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "B")
    r = plausibility.ranker_for(cycle=1, max_calls=1)
    assert r("a", "b") == CK.CONTRADICTION.value
    assert r("c", "d") is None                      # cap reached -> no further ranking this cycle


def test_qualify_uses_ranker_only_for_the_ambiguous_default(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "B")
    r = plausibility.ranker_for(cycle=1)
    # ambiguous soft pair, no surface marker -> the ranker decides (contradiction here)
    got = qualify_conflict("apples are red", "bananas are blue", ranker=r)
    assert got == CK.CONTRADICTION.value
    # a clear scope marker still wins; the ranker is never consulted
    a, b = "most requests are local", "novel unseen problems need more"
    assert qualify_conflict(a, b, ranker=plausibility.ranker_for(cycle=1)) == CK.SCOPE_TENSION.value


def test_qualify_without_ranker_is_unchanged(monkeypatch, tmp_path):
    assert qualify_conflict("apples are red", "bananas are blue") == CK.SCOPE_TENSION.value
