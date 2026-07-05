"""Anti-bloat: self-model traits and preferences must not re-mint on every recurrence.

Two duplication bugs found by materialising the live state into SQLite: 46 near-duplicate
self_model_claims that differed only by a ticking conflict count, and 12 identical 'router-note'
preferences. Both are fixed by deduping on a stable identity, and pinned here.
"""
import desi_layer9 as l9
from joni.autonomy import self_review
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def record(self, *a, **k):
        pass


def _n_contradiction_traits(cs) -> int:
    return sum(1 for c in cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM)
               if "contradictions open" in c.text)


def test_self_model_trait_not_reminted_when_only_the_count_changes():
    cs = CoreState(seed_core())
    a, b = cs.learn("a", "t"), cs.learn("b", "t")
    cs.open_conflict([a, b])
    ext: dict = {}
    self_review.run_review(cs, ext, _Proto(), 1, days=0, spend=0.0)
    assert _n_contradiction_traits(cs) == 1                 # trait recorded once

    # open a second conflict -> the live count changes; the trait text is count-free and keyed,
    # so it must NOT re-mint (before the fix this produced a second, near-duplicate claim)
    d, e = cs.learn("d", "t"), cs.learn("e", "t")
    cs.open_conflict([d, e])
    self_review.run_review(cs, ext, _Proto(), 2, days=0, spend=0.0)
    assert _n_contradiction_traits(cs) == 1                 # still one, not two

    # and the trait carries no volatile number in its wording
    trait = next(c for c in cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM)
                 if "contradictions open" in c.text)
    assert not any(ch.isdigit() for ch in trait.text)


def test_note_preference_is_idempotent_per_subject_stance():
    cs = CoreState(seed_core())
    first = cs.note_preference("router-note")
    again = cs.note_preference("router-note")               # same subject+stance -> reuse
    assert first == again
    prefs = [p for p in cs.core.all(l9.ObjectType.PREFERENCE)
             if getattr(p, "subject", None) == "router-note"]
    assert len(prefs) == 1                                   # one preference, not two

    # a genuinely different stance is a distinct preference, not swallowed by the dedup
    other = cs.note_preference("router-note", stance="rejects")
    assert other != first
    assert len({p.id for p in cs.core.all(l9.ObjectType.PREFERENCE)
                if getattr(p, "subject", None) == "router-note"}) == 2
