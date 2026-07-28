"""The MSCE↔DESi bridge prototype: a read-only adjudication of an L3 candidate.

The load-bearing test here is the GOLD STANDARD one: MSCE's own prompt ships GOOD examples of what
an L3 entry should look like. A checker that rejects those is wrong, and an earlier draft did
exactly that (it keyed on the bare verb 'install' and threw out "node_modules/ is rewritten by npm
install"). That case is pinned below so the mistake cannot come back.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "msce_bridge"))

adjudicate = pytest.importorskip("adjudicate")

CORPUS = Path(__file__).resolve().parents[1] / "experiments" / "msce_bridge" / "corpus.json"


def _row(**over):
    base = {"id": "w1", "title": "t", "policyIds": ["po_1"], "sourceEpisodeIds": ["ep_1"],
            "confidence": 0.7, "structure": {"environment": [], "inference": [], "constraints": []}}
    base.update(over)
    return base


def _entry(facet, label, description, **over):
    e = {"label": label, "description": description}
    e.update(over)
    return _row(structure={"environment": [], "inference": [], "constraints": [], facet: [e]})


# --- the gold standard: the prompt's own GOOD examples must survive -----------------------------

def test_the_prompts_own_good_examples_are_never_rejected_or_mistyped():
    rows = json.loads(CORPUS.read_text(encoding="utf-8"))
    gold = [r for r in rows if "prompt_examples" in r["id"]]
    assert gold, "the corpus must carry MSCE's own GOOD examples as the gold standard"
    entries = [e for r in gold for e in adjudicate.adjudicate(r)["entries"]]
    assert len(entries) == 7
    for e in entries:
        assert e["state"] != "synthesis-rejected", f"gold example wrongly rejected: {e['text']}"
        assert e["state"] != "human-review-required", f"gold example wrongly mistyped: {e['text']}"


def test_a_command_name_is_not_a_prescription():
    # the regression: 'npm install' names a command; the sentence prescribes nothing
    r = _entry("constraints", "node_modules",
               "node_modules/ is rewritten by npm install; manual edits are lost on the next sync",
               evidenceIds=["po_1"])
    out = adjudicate.adjudicate(r)
    assert out["overall_state"] == "synthesis-eligible"
    assert adjudicate.classify_language("rewritten by npm install") == "observation"


# --- C3: real procedural drift IS caught --------------------------------------------------------

@pytest.mark.parametrize("text", ["must compile from source", "avoid binary wheels",
                                  "don't edit node_modules directly", "always use apk"])
def test_prescriptive_language_is_a_layer_error(text):
    assert adjudicate.classify_language(text) == "prescription"
    out = adjudicate.adjudicate(_entry("constraints", "x", text, evidenceIds=["po_1"]))
    assert out["overall_state"] == "synthesis-rejected"


# --- C1: anchoring ------------------------------------------------------------------------------

def test_an_unanchored_claim_is_a_hypothesis_not_a_fact():
    out = adjudicate.adjudicate(_entry("environment", "musl", "no glibc"))
    e = out["entries"][0]
    assert e["state"] == "lexical-candidate"          # Layer 9: found by cheap recurrence only
    assert "keine evidenceIds" in e["checks"][0]["detail"]


def test_evidence_that_does_not_resolve_is_not_provenance():
    out = adjudicate.adjudicate(_entry("environment", "musl", "no glibc",
                                       evidenceIds=["po_does_not_exist"]))
    assert out["entries"][0]["state"] == "lexical-candidate"
    assert "nicht auflösbar" in out["entries"][0]["checks"][0]["detail"]


def test_a_resolved_anchor_makes_a_well_typed_entry_admissible():
    out = adjudicate.adjudicate(_entry("environment", "musl", "no glibc", evidenceIds=["po_1"]))
    assert out["entries"][0]["state"] == "synthesis-eligible" and out["admissible"] is True


# --- C2: facet typing ---------------------------------------------------------------------------

def test_a_causal_claim_filed_as_a_bare_fact_needs_review():
    out = adjudicate.adjudicate(_entry("environment", "wheels", "binary wheels fail on musl",
                                       evidenceIds=["po_1"]))
    e = out["entries"][0]
    assert e["state"] == "human-review-required" and e["language"] == "inference"


# --- C5: the confidence number is reported, never trusted ---------------------------------------

def test_the_stored_confidence_is_never_used_to_raise_a_verdict():
    low = adjudicate.adjudicate(_entry("environment", "musl", "no glibc", evidenceIds=["po_1"]))
    r = _entry("environment", "musl", "no glibc", evidenceIds=["po_1"])
    r["confidence"] = 0.99
    assert adjudicate.adjudicate(r)["overall_state"] == low["overall_state"]
    assert adjudicate.adjudicate(r)["row_checks"][0]["pass"] is False    # always flagged


# --- the row verdict is the worst of its entries ------------------------------------------------

def test_the_row_verdict_is_the_worst_entry():
    r = _row(structure={
        "environment": [{"label": "a", "description": "musl only", "evidenceIds": ["po_1"]}],
        "inference": [],
        "constraints": [{"label": "b", "description": "avoid binary wheels"}]})
    assert adjudicate.adjudicate(r)["overall_state"] == "synthesis-rejected"


def test_an_empty_row_yields_insufficient_evidence():
    assert adjudicate.adjudicate(_row())["overall_state"] == "insufficient-semantic-evidence"
