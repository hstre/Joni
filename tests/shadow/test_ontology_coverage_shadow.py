"""Ontology-coverage shadow — the pure measurement functions (no DB, deterministic).

Validates the addressable-pool / coverage / addressable-group accounting on a known subject map,
and that with no ontology the shadow reports an HONEST zero rather than faking coverage.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("DESI_REPO") or "/home/user/DESi")

import pytest  # noqa: E402

shadow = pytest.importorskip("shadow.ontology_coverage_shadow")
probe_mod = pytest.importorskip("desi_router.ontology_probe")


def test_tokens_of_key_parses_salient_tokens():
    assert shadow.tokens_of_key("topic:deploy|canary+rollout") == ("canary", "rollout")
    assert shadow.tokens_of_key("topic:deploy") == ()          # no salient tokens -> empty
    assert shadow.tokens_of_key("") == ()


def test_assess_counts_collision_pool_and_is_honest_when_ontology_empty():
    # two claims share a subject key (a #5 collision); one key is a singleton
    subjects = {
        "topic:t|operator+matrix": ["c1", "c2"],   # collision group
        "topic:t|database+schema": ["c3"],          # singleton
    }
    empty = probe_mod.OntologyProbe(None)            # no corpus -> fail-open
    rep = shadow.assess(subjects, empty)
    assert rep["collision_groups"] == 1
    assert rep["claims_in_collisions"] == 2
    assert rep["coverage_rate"] == 0.0               # honest zero, not a fabricated signal
    assert rep["addressable_collision_groups"] == 0  # nothing is addressable without coverage


def test_assess_addressable_group_needs_an_ambiguous_token():
    subjects = {"topic:t|operator+thing": ["c1", "c2"],   # 'operator' is ambiguous in the demo seed
                "topic:t|matrix+vector": ["c3", "c4"]}     # neither token ambiguous
    probe = probe_mod.OntologyProbe(shadow._demo_ontology())
    rep = shadow.assess(subjects, probe)
    assert rep["collision_groups"] == 2
    assert rep["addressable_collision_groups"] == 1        # only the 'operator' group is softenable
    assert "operator" in rep["sample_ambiguous"]
    assert rep["coverage_rate"] > 0.0                      # the demo seed covers some tokens
