"""Layer 9 distinguishes the *kind* of incompatibility, not just 'conflict'."""

import desi_layer9 as l9
from joni.autonomy.core_state import CoreState
from joni.autonomy.qualify import qualify_conflict

CK = l9.ConflictKind


def test_normal_vs_novel_is_a_scope_tension_not_a_contradiction():
    # the example from the review: both true, on different scopes
    a = "most requests can be served by a small local model"
    b = ("for novel problems without a matching pretrained pattern, "
         "parametric knowledge is not enough")
    assert qualify_conflict(a, b, severity="soft") == CK.SCOPE_TENSION.value
    # even if a contradiction signal fired, the clear scope split wins
    assert qualify_conflict(a, b, severity="hard", contradictory=True) == CK.SCOPE_TENSION.value


def test_explicit_exception_is_named():
    a = "the routing rule applies"
    b = "the routing rule does not hold unless the load is high"
    assert qualify_conflict(a, b) == CK.EXCEPTION.value


def test_explicit_condition_is_conditional_compatibility():
    a = "local routing is fast"
    b = "local routing is fast when the model is small enough"
    assert qualify_conflict(a, b) == CK.CONDITIONAL_COMPATIBILITY.value


def test_a_genuine_negation_is_a_contradiction():
    assert qualify_conflict("the cause is A", "the cause is not A",
                            severity="hard", contradictory=True) == CK.CONTRADICTION.value


def test_an_unmarked_soft_tension_defaults_to_scope_not_contradiction():
    # do not over-state opposition: an unqualified soft tension is a scope tension
    assert qualify_conflict("routing helps", "memory helps", severity="soft") == \
        CK.SCOPE_TENSION.value


def test_open_conflict_stores_the_qualified_kind():
    cs = CoreState(l9.Layer9())
    a = cs.learn("most queries are handled locally", "routing")
    b = cs.learn("novel queries need more than parametric knowledge", "routing")
    ck = qualify_conflict("most queries are handled locally",
                          "novel queries need more than parametric knowledge")
    cid = cs.open_conflict((a, b), severity="soft", conflict_kind=ck)
    x = cs.core.get(cid)
    assert x.conflict_kind is CK.SCOPE_TENSION
    # and it surfaces in the export for the map
    conflicts = cs.epistemic_export()["conflicts"]
    assert conflicts and conflicts[0]["conflict_kind"] == "scope_tension"


def test_detect_qualifies_a_negation_as_contradiction():
    cs = CoreState(l9.Layer9())
    cs.learn("the local model is sufficient for routing", "routing")
    cs.learn("the local model is not sufficient for routing", "routing")
    cs.detect_and_open_conflicts()
    kinds = [x.conflict_kind for x in cs.core.all(l9.ObjectType.CONFLICT)]
    assert CK.CONTRADICTION in kinds
