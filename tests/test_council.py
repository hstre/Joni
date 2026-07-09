"""Der Gesprächskreis: a sequential circle of LLMs in place of the forum.

Offline throughout - a fake ``ask`` stands in for the model calls. Pins the developmental and
epistemic contract: a relay where each seat sees the prior answers, the last seat falsifies,
answers enter as SOURCEs sharing ONE correlated family (never independent corroboration), and
disagreement inside the circle opens a real conflict.
"""
import desi_layer9 as l9
from joni.autonomy import council
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _a_need(cs):
    """Build a starved research topic so ``_open_need`` returns something to ask about:
    >=2 claims from >=2 independent sources, no supporting evidence."""
    cs.learn("routing decides which model serves a query", "routing", source_id="arxiv:a")
    cs.learn("routing tables need measured scores", "routing", source_id="arxiv:b")


def _seen_ask(seen):
    def ask(model, system, user):
        seen.append((model, system, user))
        return f"{model} says something concise about routing"
    return ask


def _env(monkeypatch, **kw):
    monkeypatch.setenv("JONI_COUNCIL", "1")
    monkeypatch.setenv("JONI_COUNCIL_MODELS", "m1,m2,m3")
    monkeypatch.setenv("JONI_COUNCIL_FOLLOWUPS", "0")   # tests opt into follow-ups explicitly
    for k, v in kw.items():
        monkeypatch.setenv(k, v)


def test_disabled_is_a_no_op(monkeypatch):
    monkeypatch.delenv("JONI_COUNCIL", raising=False)
    cs = CoreState(seed_core())
    _a_need(cs)
    out = council.converse(cs, {}, _Proto(), 1, ask=_seen_ask([]))
    assert out == {"heard": 0, "conflicts": 0, "models": 0, "topic": None, "rounds": 0}


def test_the_relay_shows_each_seat_the_prior_answers(monkeypatch):
    _env(monkeypatch)
    cs = CoreState(seed_core())
    _a_need(cs)
    seen = []
    out = council.converse(cs, {}, _Proto(), 1, ask=_seen_ask(seen))
    assert [m for m, _, _ in seen] == ["m1", "m2", "m3"]
    assert "Earlier voices" not in seen[0][2]                 # seat 1 sees no prior
    assert "m1 says" in seen[1][2]                            # seat 2 sees seat 1
    assert "m1 says" in seen[2][2] and "m2 says" in seen[2][2]  # seat 3 sees 1 and 2
    assert out["heard"] == 3 and out["models"] == 3


def test_the_last_seat_is_the_falsifier(monkeypatch):
    _env(monkeypatch)
    cs = CoreState(seed_core())
    _a_need(cs)
    seen = []
    council.converse(cs, {}, _Proto(), 1, ask=_seen_ask(seen))
    assert "CHALLENGE" in seen[-1][1]                         # last system prompt is the falsifier
    assert "CHALLENGE" not in seen[0][1] and "ADD" in seen[0][1]


def test_one_round_is_one_correlated_source_family(monkeypatch):
    _env(monkeypatch)
    cs = CoreState(seed_core())
    _a_need(cs)
    council.converse(cs, {}, _Proto(), 1, ask=_seen_ask([]))
    from joni.autonomy.core_state import _source_family
    circle = [c for c in cs.active_claims()
              if getattr(c, "provenance", None)
              and any(str(s).startswith("council:") for s in (c.provenance.source_ids or ()))]
    assert len(circle) == 3                                   # three answers heard
    fams = {_source_family(c) for c in circle}
    assert len(fams) == 1                                     # ...but ONE family - not 3 witnesses
    # the per-model id still rides along for the audit trail
    assert any("origin:m2" in " ".join(c.provenance.source_ids) for c in circle)


def test_disagreement_inside_the_circle_opens_a_conflict(monkeypatch):
    _env(monkeypatch)
    monkeypatch.setenv("JONI_COUNCIL_MODELS", "yea,nay,crit")
    cs = CoreState(seed_core())
    _a_need(cs)

    def ask(model, system, user):
        if model == "yea":
            return "routing is always best decided locally on the device"
        if model == "nay":
            return "routing is never best decided locally; it must be load-dependent"
        return "the local-first claim is the weaker one - it ignores load"
    out = council.converse(cs, {}, _Proto(), 1, ask=ask)
    assert out["heard"] == 3
    assert out["conflicts"] >= 1                              # the Falsifier seat earns its keep


def test_cadence_spaces_the_rounds(monkeypatch):
    _env(monkeypatch, JONI_COUNCIL_EVERY="6")
    cs = CoreState(seed_core())
    _a_need(cs)
    ext: dict = {}
    assert council.converse(cs, ext, _Proto(), 10, ask=_seen_ask([]))["heard"] == 3
    assert council.converse(cs, ext, _Proto(), 12, ask=_seen_ask([]))["heard"] == 0   # too soon
    # a fresh need so cycle 16 has something new to ask (routing was consumed at cycle 10)
    cs.learn("memory persists across sessions", "memory", source_id="arxiv:m1")
    cs.learn("memory recall needs an index", "memory", source_id="arxiv:m2")
    assert council.converse(cs, ext, _Proto(), 16, ask=_seen_ask([]))["heard"] == 3   # due again


def test_budget_stops_the_circle(monkeypatch):
    _env(monkeypatch)
    cs = CoreState(seed_core())
    _a_need(cs)

    class _Budget:
        spent_eur = 100.0
        cap_eur = 20.0

        def charge(self, a):
            self.spent_eur += a
    out = council.converse(cs, {}, _Proto(), 1, ask=_seen_ask([]), budget=_Budget())
    assert out["heard"] == 0                                  # over cap -> no calls


def test_nothing_to_ask_is_a_clean_no_op(monkeypatch):
    _env(monkeypatch)
    cs = CoreState(seed_core())                               # no starved topic, no hypothesis
    out = council.converse(cs, {}, _Proto(), 1, ask=_seen_ask([]))
    assert out["heard"] == 0 and out["topic"] is None


def test_a_dead_model_voice_is_simply_absent(monkeypatch):
    _env(monkeypatch)
    cs = CoreState(seed_core())
    _a_need(cs)

    def ask(model, system, user):
        return None if model == "m2" else f"{model} contributes on routing"
    proto = _Proto()
    out = council.converse(cs, {}, proto, 1, ask=ask)
    assert out["heard"] == 2 and out["models"] == 3           # m2 silent, the round still stands
    assert any(k == "note" and "Gesprächskreis zu 'routing'" in msg for k, msg in proto.events)


def test_answers_enter_as_candidate_sources_never_authoritative(monkeypatch):
    _env(monkeypatch)
    cs = CoreState(seed_core())
    _a_need(cs)
    council.converse(cs, {}, _Proto(), 1, ask=_seen_ask([]))
    circle = [c for c in cs.core.all(l9.ObjectType.CLAIM)
              if any(str(s).startswith("council:") for s in (c.provenance.source_ids or ()))]
    assert circle
    for c in circle:
        assert c.authority.value != "authoritative"          # a source, never an authority


def test_every_seat_is_told_who_joni_is(monkeypatch):
    # a cheap model must be given the frame - who is asking and why - not just its role.
    _env(monkeypatch)
    cs = CoreState(seed_core())
    _a_need(cs)
    seen = []
    council.converse(cs, {}, _Proto(), 1, ask=_seen_ask(seen))
    for _model, system, _user in seen:
        assert "JONI" in system                              # who is asking
        assert "Alexandria" in system or "Layer-9" in system  # what is behind him
        assert "source, never an authority" in system        # the stance
    # the role still follows the frame
    assert "ADD" in seen[0][1] and "CHALLENGE" in seen[-1][1]


def test_the_frame_is_operator_overridable(monkeypatch):
    _env(monkeypatch, JONI_COUNCIL_FRAME="CUSTOM FRAME FROM THE OPERATOR. ")
    cs = CoreState(seed_core())
    _a_need(cs)
    seen = []
    council.converse(cs, {}, _Proto(), 1, ask=_seen_ask(seen))
    assert all("CUSTOM FRAME FROM THE OPERATOR" in sysmsg for _m, sysmsg, _u in seen)


def test_joni_asks_a_follow_up_and_it_deepens_the_same_conversation(monkeypatch):
    # 1 opening round + 1 follow-up = 2 rounds; the follow-up seats see the whole prior transcript,
    # and the follow-up question pivots on the last (falsifier) voice.
    _env(monkeypatch, JONI_COUNCIL_FOLLOWUPS="1")
    cs = CoreState(seed_core())
    _a_need(cs)
    seen = []
    out = council.converse(cs, {}, _Proto(), 1, ask=_seen_ask(seen))
    assert out["rounds"] == 2 and out["models"] == 6           # 3 seats x 2 rounds
    assert "follow-up" in seen[3][2].lower()                   # round-2 seat sees Joni's follow-up
    assert "m3 says" in seen[3][2]                             # ...and the full prior transcript


def test_the_whole_conversation_is_still_one_source_family(monkeypatch):
    _env(monkeypatch, JONI_COUNCIL_FOLLOWUPS="2")
    cs = CoreState(seed_core())
    _a_need(cs)
    council.converse(cs, {}, _Proto(), 1, ask=_seen_ask([]))
    from joni.autonomy.core_state import _source_family
    circle = [c for c in cs.active_claims()
              if any(str(s).startswith("council:") for s in (c.provenance.source_ids or ()))]
    assert len(circle) == 9                                    # 3 seats x 3 rounds (1 + 2)
    assert len({_source_family(c) for c in circle}) == 1       # still ONE correlated witness


def test_follow_ups_are_capped_at_two(monkeypatch):
    _env(monkeypatch, JONI_COUNCIL_FOLLOWUPS="9")
    cs = CoreState(seed_core())
    _a_need(cs)
    out = council.converse(cs, {}, _Proto(), 1, ask=_seen_ask([]))
    assert out["rounds"] == 3                                  # 1 + min(2, 9)
