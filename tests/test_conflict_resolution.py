"""Operator-in-the-loop conflict resolution: the ONLY path that settles a contradiction.

Pins the contract: Joni SURFACES decidable conflicts but never picks a winner; only the operator's
pasted decision settles one; applying it resolves the conflict, supersedes the loser (successor =
winner) and revives the winner - which is exactly what gives the persona a real 'X -> Y' revision.
"""
from types import SimpleNamespace

import desi_layer9 as l9
from desi_layer9 import Operator, ProposalType, Provenance, make_proposal
from joni.autonomy import conflict_resolution as cr
from joni.autonomy import persona
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _op(cs, oper, payload, targets, pt=ProposalType.CLAIM_PROPOSAL):
    return cs.core.submit(make_proposal(pt, oper, payload=payload, proposer="joni",
                          provenance=Provenance.from_operator(), target_objects=tuple(targets)),
                          actor="joni")


def _open_conflict(cs, a, b):
    _op(cs, Operator.CLAIM_CONTEST, {}, (a,))
    _op(cs, Operator.CLAIM_CONTEST, {}, (b,))
    _op(cs, Operator.CONFLICT_OPEN, {"claim_ids": [a, b], "kind": "contradiction",
                                     "severity": "soft"}, (), ProposalType.STATE_REVISION_PROPOSAL)
    return [c for c in cs.core.all(l9.ObjectType.CONFLICT)][-1].id


def _asymmetric_pair(cs):
    """a (no support) contradicts b (one independent support) -> a decidable conflict."""
    a = cs.learn("routing is always local-first", "routing", source_id="arxiv:a")
    b = cs.learn("routing is load-dependent", "routing", source_id="arxiv:b")
    sup = cs.learn("benchmarks show routing depends on load", "routing", source_id="arxiv:c")
    cs.corroborate(b, cs.core.objects[sup], relation="supports")
    return a, b, _open_conflict(cs, a, b)


def test_decidable_surfaces_asymmetry_and_never_picks_a_winner():
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    items = cr.decidable_conflicts(cs)
    assert items and items[0]["conflict_id"] == cid
    it = items[0]
    # BOTH claims are presented with their support; no 'winner' field exists - Joni does not decide
    assert {it["a"]["id"], it["b"]["id"]} == {a, b}
    assert "winner" not in it
    assert max(it["a"]["support"], it["b"]["support"]) == 1


def test_symmetric_conflicts_are_not_surfaced():
    cs = CoreState(seed_core())
    a = cs.learn("x always holds", "routing")
    b = cs.learn("x never holds", "routing")
    _open_conflict(cs, a, b)                               # both have 0 support -> symmetric
    assert cr.decidable_conflicts(cs) == []


def test_parse_decisions():
    parsed = cr.parse_decisions(
        "# a comment\n\nX-1 | C-5 | C-5 is corroborated\nX-2 | C-9\nbad line no pipe\n")
    assert parsed == [
        {"conflict_id": "X-1", "winner_id": "C-5", "reason": "C-5 is corroborated"},
        {"conflict_id": "X-2", "winner_id": "C-9", "reason": ""},
    ]


def test_apply_resolves_supersedes_loser_and_revives_winner():
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    n = cr.apply_decisions(cs, {}, _Proto(), 1,
                           [{"conflict_id": cid, "winner_id": b, "reason": "corroborated"}])
    assert n == 1
    assert cs.core.objects[a].status.value == "superseded"     # loser
    assert cs.core.objects[b].status.value == "active"         # winner revived (was contested)
    conf = cs.core.objects[cid]
    assert conf.conflict_status.value == "resolved" and conf.resolution == b
    assert "operator: corroborated" in (conf.resolution_reason or "")


def test_apply_skips_a_winner_not_in_the_conflict():
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    other = cs.learn("unrelated claim", "memory")
    n = cr.apply_decisions(cs, {}, _Proto(), 1,
                           [{"conflict_id": cid, "winner_id": other, "reason": "x"}])
    assert n == 0
    assert cs.core.objects[a].status.value != "superseded"     # nothing settled


def test_apply_is_bounded_per_cycle():
    cs = CoreState(seed_core())
    decisions = []
    for _ in range(5):
        a, b, cid = _asymmetric_pair(cs)
        decisions.append({"conflict_id": cid, "winner_id": b, "reason": "r"})
    applied = cr.apply_decisions(cs, {}, _Proto(), 1, decisions, max_apply=3)
    assert applied == 3                                        # capped


def test_interact_folds_a_pasted_decision_and_writes_the_sheet(tmp_path):
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    paths = SimpleNamespace(conflict_decisions=tmp_path / "decisions.txt",
                            resolve_sheet=tmp_path / "to_resolve.md")
    paths.conflict_decisions.write_text(f"{cid} | {b} | corroborated under load\n")
    res = cr.interact(cs, {}, _Proto(), 1, paths=paths)
    assert res["applied"] == 1
    assert cs.core.objects[a].status.value == "superseded"
    # the drop box is consumed (reset) and a fresh sheet was written
    assert "corroborated under load" not in paths.conflict_decisions.read_text()
    assert paths.resolve_sheet.exists() and "Konflikt-Mappe" in paths.resolve_sheet.read_text()


def test_the_full_flow_feeds_the_persona_a_real_revision():
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    cr.apply_decisions(cs, {}, _Proto(), 1,
                       [{"conflict_id": cid, "winner_id": b, "reason": "corroborated under load"}])
    cor = [c for c in persona.extract_corrections(cs) if c.obj_id == a][0]
    assert cor.before == "routing is always local-first"
    assert cor.after == "routing is load-dependent"           # a real X -> Y, not a bare rejection
    assert "corroborated under load" in cor.trigger


# --- Remonstration: Joni questions the operator's decisions ------------------------------------ #

def test_an_evidence_contradicting_decision_is_held_with_a_reasoned_objection():
    # the operator picks the side with LESS independent support -> Joni does not apply; he records
    # a reasoned objection (protocolled) and the decision rests one round. Mündigkeit, kein Veto.
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)                    # a: 0 supports, b: 1 support
    ext: dict = {}
    proto = _Proto()
    n = cr.apply_decisions(cs, ext, proto, 1,
                           [{"conflict_id": cid, "winner_id": a, "reason": "bauchgefühl"}])
    assert n == 0                                       # NOT applied
    assert cs.core.objects[cid].conflict_status.value == "open"     # conflict still open
    assert any(kind == "einspruch" for kind, _ in proto.events)     # the objection is protocolled
    assert ext["conflict_objections"][cid]["winner_id"] == a


def test_reentering_the_same_decision_confirms_over_the_objection():
    # the operator stays the authority: re-entering the decision applies it - but the objection is
    # preserved immutably in the conflict's resolution_reason (the richer persona lesson later).
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    ext: dict = {}
    cr.apply_decisions(cs, ext, _Proto(), 1,
                       [{"conflict_id": cid, "winner_id": a, "reason": "bauchgefühl"}])
    n = cr.apply_decisions(cs, ext, _Proto(), 2,
                           [{"conflict_id": cid, "winner_id": a, "reason": "bauchgefühl"}])
    assert n == 1                                       # confirmed -> applied
    conf = cs.core.objects[cid]
    assert conf.conflict_status.value == "resolved" and conf.resolution == a
    assert "Einspruch" in (conf.resolution_reason or "")            # the objection travels along
    assert cs.core.objects[b].status.value == "superseded"          # the supported side lost
    assert cid not in ext["conflict_objections"]                    # pending register cleared


def test_a_different_winner_after_an_objection_gets_a_fresh_check():
    # an objection for winner X does not confirm a later decision for winner Y: Y is checked on its
    # own merits (here evidence-aligned -> applies immediately, no objection).
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    ext: dict = {}
    cr.apply_decisions(cs, ext, _Proto(), 1,
                       [{"conflict_id": cid, "winner_id": a, "reason": "x"}])   # objection for a
    n = cr.apply_decisions(cs, ext, _Proto(), 2,
                           [{"conflict_id": cid, "winner_id": b, "reason": "y"}])
    assert n == 1                                       # evidence-aligned -> applied at once
    assert cs.core.objects[cid].resolution == b
    assert "Einspruch" not in (cs.core.objects[cid].resolution_reason or "")


def test_a_symmetric_decision_applies_immediately_without_objection():
    # no measured asymmetry -> nothing to object to; the operator's call applies at once.
    cs = CoreState(seed_core())
    a = cs.learn("x always holds", "routing")
    b = cs.learn("x never holds", "routing")
    cid = _open_conflict(cs, a, b)                      # 0 vs 0 supports
    proto = _Proto()
    n = cr.apply_decisions(cs, {}, proto, 1, [{"conflict_id": cid, "winner_id": a, "reason": "r"}])
    assert n == 1
    assert not any(kind == "einspruch" for kind, _ in proto.events)


# --- the three-axis decidability (support · families · provenance) ----------------------------- #

def test_a_paper_vs_a_forum_voice_is_decidable_even_without_corroboration():
    # 0-vs-0 supports, but one side is an external research source and the other a pseudonymous
    # forum voice: the provenance axis leans - surfaced for the operator (still never decided).
    cs = CoreState(seed_core())
    a = cs.hear("routing is always local-first", "routing", handle="bob", platform="hn")
    b = cs.learn("routing is load-dependent", "routing", source_id="arxiv:b")
    cid = _open_conflict(cs, a, b)
    items = cr.decidable_conflicts(cs)
    assert [it["conflict_id"] for it in items] == [cid]
    assert "winner" not in items[0]                     # presenting, not deciding


def test_axes_pointing_in_opposite_directions_stay_unsurfaced():
    # a: forum voice WITH independent support; b: paper with none. Support leans to a, provenance
    # leans to b -> genuinely ambiguous, exactly what the operator sheet must NOT pre-frame.
    cs = CoreState(seed_core())
    a = cs.hear("routing is always local-first", "routing", handle="bob", platform="hn")
    b = cs.learn("routing is load-dependent", "routing", source_id="arxiv:b")
    sup = cs.learn("a note backing local-first", "routing", source_id="arxiv:s")
    cs.corroborate(a, cs.core.objects[sup])
    _open_conflict(cs, a, b)
    assert cr.decidable_conflicts(cs) == []


def test_the_sheet_shows_the_measured_axes():
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    sheet = cr.render_sheet(cr.decidable_conflicts(cs), {})
    assert "Evidenzlage" in sheet and "Quellfamilien" in sheet and "Provenienz" in sheet


def test_an_ambiguous_balance_is_the_operators_call_no_objection():
    # the operator decides an axes-disagree conflict: Joni applies at once - remonstration is
    # only for a decision the measured lean STRICTLY contradicts, never for ambiguity.
    cs = CoreState(seed_core())
    a = cs.hear("routing is always local-first", "routing", handle="bob", platform="hn")
    b = cs.learn("routing is load-dependent", "routing", source_id="arxiv:b")
    sup = cs.learn("a note backing local-first", "routing", source_id="arxiv:s")
    cs.corroborate(a, cs.core.objects[sup])
    cid = _open_conflict(cs, a, b)
    proto = _Proto()
    n = cr.apply_decisions(cs, {}, proto, 1, [{"conflict_id": cid, "winner_id": b, "reason": "r"}])
    assert n == 1
    assert not any(kind == "einspruch" for kind, _ in proto.events)


def test_deciding_against_a_paper_for_a_bare_forum_voice_draws_an_objection():
    cs = CoreState(seed_core())
    a = cs.hear("routing is always local-first", "routing", handle="bob", platform="hn")
    b = cs.learn("routing is load-dependent", "routing", source_id="arxiv:b")
    cid = _open_conflict(cs, a, b)
    ext: dict = {}
    proto = _Proto()
    n = cr.apply_decisions(cs, ext, proto, 1,
                           [{"conflict_id": cid, "winner_id": a, "reason": "gefaellt mir"}])
    assert n == 0                                       # held: provenance leans to the paper
    assert any(kind == "einspruch" for kind, _ in proto.events)
    assert "Provenienz" in ext["conflict_objections"][cid]["axes"]


def test_the_sheet_lists_pending_objections(tmp_path):
    cs = CoreState(seed_core())
    a, b, cid = _asymmetric_pair(cs)
    paths = SimpleNamespace(conflict_decisions=tmp_path / "decisions.txt",
                            resolve_sheet=tmp_path / "to_resolve.md")
    paths.conflict_decisions.write_text(f"{cid} | {a} | bauchgefühl\n")   # the weaker side
    res = cr.interact(cs, {}, _Proto(), 1, paths=paths)
    assert res["applied"] == 0                          # held by the objection
    sheet = paths.resolve_sheet.read_text()
    assert "Einsprüche" in sheet and cid in sheet       # visible + confirmable on the sheet
