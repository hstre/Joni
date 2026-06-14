"""Calibration harness for the embedding thresholds on a small labelled Joni-claim set.

Runs against the *real* local embedding model when installed (skips otherwise). It checks
that the conservative thresholds classify a labelled set acceptably and - the property the
brief insists on - that no genuinely unrelated pair is forced to ``synthesis-eligible``.
The labelled set is the seed for future calibration; thresholds live in
``desi_layer9.semantics.decision`` and are deliberately conservative.
"""

import pytest

from desi_layer9 import SemanticDecision, SemanticState
from desi_layer9.semantics import decision
from desi_layer9.semantics.ports import SemanticMeasurement
from joni.autonomy import embeddings

# (claim_a, claim_b, label) - label in {duplicate, related, unrelated}
LABELLED: list[tuple[str, str, str]] = [
    ("local routing reduces request latency", "routing locally lowers latency", "duplicate"),
    ("memory pressure changes routing", "memory load shifts how routing is decided", "related"),
    ("cheap local models handle most routing", "small on-device models do most routing", "related"),
    ("privacy budgets constrain routing", "differential privacy limits routing choices", "related"),
    ("routing reduces latency", "the moon orbits the earth", "unrelated"),
    ("calibration improves evaluation", "the recipe needs more salt", "unrelated"),
    ("drift detection needs calibration", "a thermostat controls room temperature", "unrelated"),
]


def _measure(a: str, b: str) -> SemanticMeasurement:
    d = embeddings.cosine_distance(a, b)
    info = embeddings.info()
    return SemanticMeasurement(
        cosine_distance=d, distance_metric="cosine", embedding_model=info["model"],
        embedding_revision=info["revision"], embedding_dim=info["dim"],
        embedding_normalized=info["normalized"], duplicate=(d is not None and d <= 0.10),
        components=(f"local_embedding:{info['model']}@{info['revision']}",))


def test_thresholds_are_conservative_on_a_labelled_set():
    if not embeddings.available():
        pytest.skip("no local embedding model installed; calibration runs where one is present")

    rows = []
    for a, b, label in LABELLED:
        d, state, _ = decision.classify(_measure(a, b))
        rows.append((label, d, state))

    # the hard guarantee: an unrelated pair must NEVER be synthesis-eligible.
    for label, d, state in rows:
        if label == "unrelated":
            assert state is not SemanticState.SYNTHESIS_ELIGIBLE, (label, d)

    # duplicates must be recognised as duplicates (not merged into a synthesis).
    for label, d, _state in rows:
        if label == "duplicate":
            assert d is SemanticDecision.DUPLICATE, (label, d)

    # most 'related' pairs should be usable (not insufficient); allow a margin since the
    # threshold is conservative on purpose.
    related = [r for r in rows if r[0] == "related"]
    usable = [r for r in related if r[1] is not SemanticDecision.INSUFFICIENT]
    assert len(usable) >= max(1, len(related) - 1)
