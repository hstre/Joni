"""Persona v3 - the corrected-error history BINDS future transitions (forward-binding).

The manifesto's demand, verbatim: "Deshalb darf ein ähnlicher Übergang künftig nicht ohne
zusätzliche Prüfung akzeptiert werden." Two mechanisms pin it:

  * **Revenant guard**: a text near-duplicating an already-corrected (REJECTED/SUPERSEDED) claim
    is never auto-activated again - it re-enters as a CANDIDATE derived from its corrected
    predecessor (auditable lineage) and must EARN fresh, independent support via the strengthen
    ladder. Never blocked - epistemics stays revisable; the bar is just real.
  * **Burned themes**: a theme with a deep correction history raises the promotion bar (one more
    independent family, a single external card no longer suffices, coherence alone cannot mature
    an idea there). A hold is protocolled, never silent.
"""
from joni.autonomy import persona, strengthen
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _burn(cs, topic: str, n: int = 3) -> None:
    """Metabolise n corrected errors on a topic (reject n distinct claims)."""
    for i in range(n):
        x = cs.learn(f"{topic} wrong idea number {i} about latency and load", topic)
        cs.reject_claim(x)


# --- revenant guard ---------------------------------------------------------------------------- #

def test_a_corrected_belief_does_not_reactivate_it_must_earn_its_way_back():
    cs = CoreState(seed_core())
    dead = cs.learn("routing is always local-first", "routing", source_id="arxiv:a")
    cs.reject_claim(dead)                                     # the corrected error
    rid = cs.learn("routing is always local-first", "routing", source_id="arxiv:b")
    c = cs.core.objects[rid]
    assert c.status.value == "candidate"                      # NOT auto-active
    assert dead in c.derived_from                             # auditable lineage
    assert f"revenant-of:{dead}" in c.provenance.source_ids   # explicit marker
    assert any(h.id == rid for h in cs.hypotheses())          # enters the strengthen ladder


def test_a_forum_voice_repeating_a_corrected_belief_is_guarded_too():
    cs = CoreState(seed_core())
    dead = cs.learn("routing is always local-first", "routing")
    cs.reject_claim(dead)
    rid = cs.hear("routing is always local-first", "routing", handle="u", platform="hn")
    assert cs.core.objects[rid].status.value == "candidate"
    assert f"revenant-of:{dead}" in cs.core.objects[rid].provenance.source_ids


def test_a_numeric_only_paraphrase_of_a_corrected_belief_is_a_revenant():
    cs = CoreState(seed_core())
    dead = cs.learn("the benchmark shows 31 exchanges per session", "routing")
    cs.reject_claim(dead)
    rid = cs.learn("the benchmark shows 34 exchanges per session", "routing")
    assert cs.core.objects[rid].status.value == "candidate"


def test_normal_learning_is_unaffected_by_the_guard():
    cs = CoreState(seed_core())
    dead = cs.learn("routing is always local-first", "routing")
    cs.reject_claim(dead)
    fresh = cs.learn("attention improves recall on long contexts", "attention")
    assert cs.core.objects[fresh].status.value == "active"    # unrelated text: activates as before


def test_a_revenant_can_earn_activation_with_fresh_independent_support():
    # never blocked - a corrected belief may yet turn out right, it just has to EARN it.
    cs = CoreState(seed_core())
    dead = cs.learn("routing is always local-first", "memory")   # non-burned theme (1 correction)
    cs.reject_claim(dead)
    rid = cs.learn("routing is always local-first", "memory", source_id="arxiv:r")
    s1 = cs.learn("study one finds local-first wins", "memory", source_id="arxiv:s1")
    s2 = cs.learn("study two finds local-first wins", "memory", source_id="arxiv:s2")
    cs.corroborate(rid, cs.core.objects[s1])
    cs.corroborate(rid, cs.core.objects[s2])
    strengthen.strengthen(cs, {}, _Proto(), 1)
    assert cs.core.objects[rid].status.value == "active"      # earned its way back


# --- burned themes ----------------------------------------------------------------------------- #

def test_burned_themes_need_the_configured_depth_and_exclude_sinks():
    cs = CoreState(seed_core())
    _burn(cs, "routing", 3)
    _burn(cs, "memory", 2)                                    # below the default depth of 3
    _burn(cs, "unsorted", 3)                                  # a sink earns no lesson
    burned = persona.burned_themes(cs)
    assert burned.get("routing") == 3
    assert "memory" not in burned and "unsorted" not in burned


def test_burned_themes_fails_open_on_a_broken_core():
    class _Boom:
        @property
        def core(self):
            raise RuntimeError("boom")
    assert persona.burned_themes(_Boom()) == {}               # no hint -> no binding, never a crash


def _hyp_with_supports(cs, topic: str, n_supports: int) -> str:
    p = cs.learn(f"{topic} parent claim about admission", topic, source_id="arxiv:p")
    h = cs.hypothesize(f"Hypothesis: {topic} benefits from admission control", topic, parents=(p,))
    for i in range(n_supports):
        s = cs.learn(f"paper {i} supports admission control in {topic}", topic,
                     source_id=f"arxiv:s{i}")
        cs.corroborate(h, cs.core.objects[s])
    return h


def test_on_a_burned_theme_the_normal_bar_is_held_and_the_hold_is_protocolled():
    cs = CoreState(seed_core())
    _burn(cs, "routing", 3)
    h = _hyp_with_supports(cs, "routing", 2)                  # meets the NORMAL bar exactly
    proto = _Proto()
    strengthen.strengthen(cs, {}, proto, 1)
    assert cs.core.objects[h].status.value == "candidate"     # held, not promoted
    assert any("held by the burned-theme bar" in s for _, s in proto.events)   # visible, not silent


def test_on_a_burned_theme_one_more_independent_family_promotes():
    cs = CoreState(seed_core())
    _burn(cs, "routing", 3)
    h = _hyp_with_supports(cs, "routing", 3)                  # the RAISED bar
    strengthen.strengthen(cs, {}, _Proto(), 1)
    assert cs.core.objects[h].status.value == "active"


def test_coherence_alone_cannot_mature_an_idea_on_a_burned_theme(monkeypatch):
    # the plateau lever (Doktores-coherent, no support needed) is exactly the plausible-but-
    # unearned transition the correction history warns about - disabled on burned themes.
    monkeypatch.setenv("JONI_PROMOTE_ON_COHERENCE", "1")
    cs = CoreState(seed_core())
    _burn(cs, "routing", 3)
    p = cs.learn("routing parent claim", "routing", source_id="arxiv:p")
    h = cs.hypothesize("Hypothesis: routing likes admission control", "routing", parents=(p,))
    ext = {"doktores_hyp_log": [{"hypothesis": h, "coherent": True}]}
    strengthen.strengthen(cs, ext, _Proto(), 1)
    assert cs.core.objects[h].status.value == "candidate"     # coherence alone does not promote
