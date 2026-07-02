"""Coordinate plumbing: records -> SolutionPoints (embedding + normalised StateVector).

Forces the deterministic lexical fallback (``allow_model=False``) so tests never touch the network;
the real fastembed backend swaps in automatically when installed and its model loads.
"""
from __future__ import annotations

import math

from joni.solution_space.cartography import cartograph
from joni.solution_space.coordinates import (
    build_points,
    embed_texts,
    embeddings_backend,
    state_vector_of,
)


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def test_backend_reports_a_known_value():
    assert embeddings_backend() in ("fastembed", "lexical-hash-fallback")


def test_lexical_embed_is_deterministic_and_topic_sensitive():
    a1, a2, b = embed_texts(
        ["pneumonia lung infection fever", "lung infection pneumonia cough",
         "stock market interest rate"], allow_model=False)
    assert embed_texts(["pneumonia lung infection fever"], allow_model=False)[0] == a1   # determ.
    # two same-topic texts are closer than a same-topic vs an off-topic one
    assert _cos(a1, a2) > _cos(a1, b)


def test_state_vector_of_accepts_tuple_dict_and_to_tuple_object():
    assert state_vector_of((1, 2, 3)) == (1.0, 2.0, 3.0)
    d = {"frame_id": 1, "contradiction_load": 2, "confidence": 5}
    sv = state_vector_of(d)
    assert len(sv) == 9 and sv[0] == 1.0 and sv[1] == 2.0 and sv[5] == 5.0

    class _SV:
        def to_tuple(self):
            return (0.5,) * 9
    assert state_vector_of(_SV()) == (0.5,) * 9


def test_build_points_assembles_solution_points():
    recs = [
        {"id": "c1", "text": "pneumonia lung infection", "state_vector": (0.0,) * 9,
         "anchored": True},
        {"id": "c2", "text": "acute respiratory distress", "state_vector": {"novelty": 0.9},
         "anchored": False, "label": "ARDS"},
    ]
    pts = build_points(recs, allow_model=False)
    assert [p.id for p in pts] == ["c1", "c2"]
    assert pts[0].anchored is True and pts[1].anchored is False
    assert pts[1].label == "ARDS"
    assert len(pts[1].state_vector) == 9 and pts[1].state_vector[4] == 0.9   # novelty axis
    assert any(x > 0 for p in pts for x in p.embedding)          # embeddings are non-trivial


def test_built_points_feed_the_cartographer():
    recs = [
        {"id": "a1", "text": "sepsis infection blood", "state_vector": (0.0,) * 9,
         "anchored": True},
        {"id": "a2", "text": "sepsis blood infection severe", "state_vector": (0.0,) * 9,
         "anchored": True},
        {"id": "b1", "text": "quantum field gauge symmetry", "state_vector": (9.0,) * 9,
         "anchored": False},
    ]
    pts = build_points(recs, allow_model=False)
    cart = cartograph(pts, tau=0.3)
    # the two sepsis points cluster; the far off-topic point is its own (unanchored) island
    assert len(cart.islands) >= 2
    assert any(not i.anchored for i in cart.islands)
