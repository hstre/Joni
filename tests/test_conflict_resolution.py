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
