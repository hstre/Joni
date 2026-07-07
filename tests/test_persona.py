"""Jonis Persona = read-only Projektion korrigierter Irrtümer.

Pins the operator's contract: the persona is DERIVED from the ledger's corrected-error trail (never
a new fact), a lesson crystallises on any of the three triggers, it is abstracted to <=2 anchors
while the FULL trail is kept, and the LLM stage may only rephrase - never change the logic.
"""
from types import SimpleNamespace

from desi_layer9 import ObjectType
from joni.autonomy import persona
from joni.autonomy.core_state import CoreState, seed_core


def _status(v):
    return SimpleNamespace(value=v)


def _claim(cid, text, topic, status, *, ledger_event="", tick=0):
    return SimpleNamespace(id=cid, text=text, topic=topic, status=_status(status),
                           ledger_event=ledger_event, last_changed_tick=tick)


def _conflict(cid, claim_ids, status, reason=""):
    return SimpleNamespace(id=cid, claim_ids=tuple(claim_ids), conflict_status=_status(status),
                           resolution_reason=reason)


def _event(eid, reason, output_refs=()):
    return SimpleNamespace(id=eid, reason=reason, output_refs=tuple(output_refs))


class _FakeCore:
    """A minimal stand-in for the Layer-9 snapshot surface the projector reads."""

    def __init__(self, *, claims=(), conflicts=(), self_model=(), ledger=(), tick=1):
        self._by = {ObjectType.CLAIM: list(claims), ObjectType.CONFLICT: list(conflicts),
                    ObjectType.SELF_MODEL_CLAIM: list(self_model)}
        self.ledger = list(ledger)
        self.tick = tick
        self.objects = {o.id: o for o in [*claims, *self_model]}

    def all(self, objtype):
        return self._by.get(objtype, [])


def _cs(core):
    return SimpleNamespace(core=core)


# --- extraction -------------------------------------------------------------- #

def test_extract_reads_before_trigger_after_from_a_supersede():
    old = _claim("C-1", "routing is always local-first", "routing", "superseded",
                 ledger_event="E-9", tick=5)
    new = _claim("C-2", "routing is load-dependent", "routing", "active")
    ev = _event("E-9", "measured: local-first lost under load", output_refs=("C-2",))
    core = _FakeCore(claims=[old, new], ledger=[ev])
    cor = persona.extract_corrections(_cs(core))
    assert len(cor) == 1
    c = cor[0]
    assert c.before == "routing is always local-first"
    assert c.after == "routing is load-dependent"          # successor text, not fabricated
    assert "local-first lost under load" in c.trigger
    assert c.kind == "superseded" and c.theme == "routing"


def test_extract_marks_a_rejection_with_no_successor():
    dead = _claim("C-3", "attention is free", "attention", "rejected", ledger_event="E-1")
    core = _FakeCore(claims=[dead], ledger=[_event("E-1", "")])
    c = persona.extract_corrections(_cs(core))[0]
    assert c.kind == "rejected" and c.after == ""          # never invents an 'after'
    assert "verworfen" in c.trigger                        # falls back to naming the move


def test_a_rejections_own_id_in_output_refs_is_not_read_as_a_successor():
    # regression: a rejection's ledger event lists the rejected claim ITSELF in output_refs
    # (input==output). The 'after' must stay empty, not echo the claim's own before-text.
    dead = _claim("C-3", "attention is free", "attention", "rejected", ledger_event="E-1")
    core = _FakeCore(claims=[dead], ledger=[_event("E-1", "C-3 rejected", output_refs=("C-3",))])
    c = persona.extract_corrections(_cs(core))[0]
    assert c.after == ""                                   # own id is not a successor
    assert bool(c.after) is False


def test_a_real_supersede_successor_is_still_read():
    old = _claim("C-1", "local-first always", "routing", "superseded", ledger_event="E-9")
    new = _claim("C-2", "load-dependent", "routing", "active")
    core = _FakeCore(claims=[old, new],
                     ledger=[_event("E-9", "replaced", output_refs=("C-1", "C-2"))])
    c = persona.extract_corrections(_cs(core))[0]
    assert c.after == "load-dependent"                     # the DIFFERENT object is the successor


def test_active_and_candidate_claims_are_not_corrections():
    core = _FakeCore(claims=[_claim("C-4", "x", "t", "active"),
                             _claim("C-5", "y", "t", "candidate")])
    assert persona.extract_corrections(_cs(core)) == []


def test_a_revised_self_model_claim_is_a_persona_correction():
    sm = _claim("S-1", "I never contradict myself", "", "rejected", ledger_event="E-2")
    core = _FakeCore(self_model=[sm], ledger=[_event("E-2", "found a contradiction")])
    c = persona.extract_corrections(_cs(core))[0]
    assert c.theme == "self-model" and c.kind == "rejected"


# --- crystallisation (the three triggers) ------------------------------------ #

def _corr(theme, kind="superseded", *, via_conflict=False, tick=0, after="y", oid="o",
          has_reason=False, trigger="t"):
    return persona.Correction(obj_id=oid, theme=theme, kind=kind, before="x", trigger=trigger,
                              after=after, tick=tick, via_conflict=via_conflict,
                              has_reason=has_reason, trail_refs=("E-1",))


def test_threshold_trigger_needs_two_errors_on_a_theme():
    one = [_corr("routing", oid="a")]
    assert persona.crystallize(one, self_review=False) == []        # a single error is not a lesson
    two = [_corr("routing", oid="a", tick=1), _corr("routing", oid="b", tick=2)]
    lessons = persona.crystallize(two, self_review=False)
    assert len(lessons) == 1 and lessons[0].trigger_kind == "threshold" and lessons[0].depth == 2


def test_a_resolved_conflict_crystallises_even_a_single_error():
    c = [_corr("memory", via_conflict=True, oid="a")]
    lessons = persona.crystallize(c, self_review=False)
    assert lessons and lessons[0].trigger_kind == "resolved_conflict"


def test_self_review_window_crystallises_the_rest():
    c = [_corr("drift", oid="a")]
    assert persona.crystallize(c, self_review=False) == []
    lessons = persona.crystallize(c, self_review=True)
    assert lessons and lessons[0].trigger_kind == "self_review"


def test_sink_themes_earn_no_persona_lesson():
    # no expertise on an undifferentiated sink; corrections on 'unsorted'/'forum' earn no lesson
    for sink in ("unsorted", "forum", "misc"):
        c = [_corr(sink, oid="a", via_conflict=True), _corr(sink, oid="b")]
        assert persona.crystallize(c, self_review=True) == []
    # a real theme with the same shape still crystallises
    real = [_corr("routing", oid="a", via_conflict=True)]
    assert persona.crystallize(real, self_review=False)


def test_generic_auto_reason_does_not_count_as_a_reason(tmp_path):
    # reject_claim records a generic 'C-5 rejected'; it must not lift has_reason or pose as trigger
    gen = _claim("C-5", "x", "routing", "rejected", ledger_event="E-1")
    core = _FakeCore(claims=[gen], ledger=[_event("E-1", "C-5 rejected")])
    c = persona.extract_corrections(_cs(core))[0]
    assert c.has_reason is False                            # generic boilerplate is not a reason
    assert "verworfen" in c.trigger and "C-5 rejected" not in c.trigger
    # a substantive reason DOES count
    sub = _claim("C-6", "x", "routing", "rejected", ledger_event="E-2")
    core2 = _FakeCore(claims=[sub], ledger=[_event("E-2", "measured: it broke under load")])
    c2 = persona.extract_corrections(_cs(core2))[0]
    assert c2.has_reason is True and "broke under load" in c2.trigger


def test_persona_jsonl_is_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(persona, "_SERIES_CAP", 3)
    paths = SimpleNamespace(root=tmp_path, model_calls=tmp_path / "mc")
    core = _FakeCore(claims=[_claim("C-1", "x", "routing", "rejected", ledger_event="E-1"),
                             _claim("C-2", "y", "routing", "rejected", ledger_event="E-1")],
                     ledger=[_event("E-1", "")])
    for _ in range(6):
        persona.project(_cs(core), paths=paths, self_review=True, phrase=False)
    lines = (tmp_path / "state" / "persona.jsonl").read_text().splitlines()
    assert len(lines) == 3                                  # bounded, not 6


def test_anchors_pick_the_most_instructive_not_the_most_recent():
    # a shallow but very recent rejection must NOT out-anchor an older, instructive correction that
    # resolved a contradiction with a recorded reason - date plays no role in the choice.
    shallow_recent = _corr("routing", kind="rejected", oid="a", tick=999, after="",
                           trigger="verworfen")
    plain = _corr("routing", oid="b", tick=2)                       # has an 'after' only
    instructive = _corr("routing", oid="c", tick=1, via_conflict=True, has_reason=True,
                        trigger="measured: local-first lost under load")
    lessons = persona.crystallize([shallow_recent, plain, instructive], self_review=False)
    anchors = {a.obj_id for a in lessons[0].anchors}
    assert "c" in anchors                       # the most instructive is kept...
    assert "a" not in anchors                   # ...and recency does not save the shallow one
    assert lessons[0].anchors[0].obj_id == "c"  # most instructive leads


def test_lesson_abstracts_to_two_anchors_but_keeps_the_full_trail():
    c = [_corr("routing", oid=f"o{i}", tick=i) for i in range(5)]
    ls = persona.crystallize(c, self_review=False)[0]
    assert ls.depth == 5
    assert len(ls.anchors) == persona._MAX_ANCHORS == 2      # abstrahiert mit ein, zwei Beispielen
    assert set(ls.trail) == {f"o{i}" for i in range(5)}      # ...but nothing is forgotten
    assert str(ls.depth) in ls.heuristic


# --- LLM phrasing: language only, never logic -------------------------------- #

def test_phrasing_fills_only_the_phrased_field_and_keeps_the_heuristic(monkeypatch):
    from joni.autonomy import model_call
    monkeypatch.setattr(model_call, "call",
                        lambda *a, **k: ("Lokal ist nicht immer besser.", None))
    ls = persona.crystallize([_corr("routing", oid="a", tick=1), _corr("routing", oid="b", tick=2)],
                             self_review=False)
    det = ls[0].heuristic
    phrased = persona.phrase_lessons(ls, store_dir=None)
    assert phrased[0].heuristic == det                       # ground truth untouched
    assert phrased[0].heuristic_phrased == "Lokal ist nicht immer besser."
    assert phrased[0].anchors == ls[0].anchors and phrased[0].trail == ls[0].trail


def test_phrasing_fails_open_when_the_model_errors(monkeypatch):
    from joni.autonomy import model_call

    def _boom(*a, **k):
        raise RuntimeError("model down")

    monkeypatch.setattr(model_call, "call", _boom)
    ls = persona.crystallize([_corr("routing", oid="a"), _corr("routing", oid="b")],
                             self_review=False)
    phrased = persona.phrase_lessons(ls, store_dir=None)
    assert phrased[0].heuristic_phrased is None              # lesson stands, cycle not broken


# --- orchestration + read-only output ---------------------------------------- #

def test_project_writes_persona_md_and_jsonl_readonly(tmp_path):
    paths = SimpleNamespace(root=tmp_path, model_calls=tmp_path / "mc")
    old = _claim("C-1", "local-first always", "routing", "superseded", ledger_event="E-9", tick=5)
    new = _claim("C-2", "load-dependent", "routing", "active")
    core = _FakeCore(claims=[old, new], ledger=[_event("E-9", "lost under load", ("C-2",))])
    res = persona.project(_cs(core), paths=paths, self_review=True, phrase=False)
    assert res["corrections"] == 1
    md = (tmp_path / "state" / "persona.md").read_text(encoding="utf-8")
    assert "routing" in md and "load-dependent" in md
    assert (tmp_path / "state" / "persona.jsonl").exists()


def test_project_is_fail_open_on_an_empty_core():
    # a valid-but-empty core: no corrections, no lesson, no crash (the common case)
    res = persona.project(_cs(_FakeCore()), phrase=False)
    assert res["corrections"] == 0 and res["lessons"] == 0 and not res.get("error")


def test_project_swallows_a_broken_core():
    # a core whose access raises must NOT break the cycle - the projector fails open with error=True
    class _Boom:
        @property
        def core(self):
            raise RuntimeError("core exploded")

    res = persona.project(_Boom(), phrase=False)
    assert res["error"] is True and res["lessons"] == 0


# --- real-core smoke test: the accessors line up with Layer 9 ---------------- #

def test_real_core_rejected_claims_become_a_lesson():
    cs = CoreState(seed_core())
    a = cs.learn("routing reduces latency always", "routing", source_id="arxiv:a")
    b = cs.learn("routing never adds overhead", "routing", source_id="arxiv:b")
    cs.reject_claim(a)
    cs.reject_claim(b)
    cor = persona.extract_corrections(cs)
    themes = {c.theme for c in cor}
    assert "routing" in themes
    assert {a, b} <= {c.obj_id for c in cor}                 # both rejections surfaced
    # real ledger events list the rejected claim itself in output_refs - it must NOT be read as a
    # successor (the regression this guards): a real rejection has no 'after'.
    assert all(c.after == "" for c in cor if c.obj_id in {a, b})
    lessons = persona.crystallize(cor, self_review=False)
    routing = [ls for ls in lessons if ls.theme == "routing"]
    assert routing and routing[0].depth >= 2 and set(routing[0].trail) >= {a, b}
