"""A-priori-plausible thinking methods for Stage 2 — pre-registered, never tuned to a result.

Each entry is a real problem-solving discipline documented in the reasoning/heuristics literature; its
plausibility for the matching task skill is declared HERE, before any task is run (per the
pre-registration's method-plausibility rule). These supply the *intervention* and the two
method-shaped controls (scrambled = same words, structure destroyed; irrelevant = a real method for a
different skill). Deterministic, no model.
"""
from __future__ import annotations

import random

# method-class -> (discipline text, a-priori rationale). Text is what gets prepended as the discipline.
METHODS: dict[str, tuple[str, str]] = {
    "adversarial": (
        "Method: try to BREAK each statement. Assume each could be false and look for the one it "
        "collides with. Name the exact pair that cannot both hold.",
        "adversarial / falsification is the standard move for finding contradictions"),
    "exclusion": (
        "Method: rule out the option whose failure is IRREVERSIBLE or catastrophic first, regardless "
        "of how likely it is. Eliminate the unrecoverable branch before ranking the rest.",
        "exclusion / rule-out-the-catastrophic is standard triage under risk"),
    "boundary": (
        "Method: decompose the quantity into a rate times a time (or a product of simple factors), "
        "estimate each factor to one significant figure, then multiply.",
        "Fermi decomposition is the standard bounded-estimation discipline"),
    "decomposition": (
        "Method: split into disjoint, exhaustive CASES; count each case with its own constraints; "
        "sum them. Verify no case overlaps and none is missing.",
        "case decomposition is the standard combinatorial counting discipline"),
    "causal": (
        "Method: separate correlation from cause. Look for a common PRIOR variable that could produce "
        "both effects, and name the confounder you must hold fixed.",
        "confounder search is the standard causal-inference move"),
    "provenance": (
        "Method: trace each claim to its ROOT source. Count independent roots, not citations; two "
        "claims sharing one root are one source.",
        "source-independence tracing is the standard provenance discipline"),
    "invariant": (
        "Method: identify the quantity that must be CONSERVED, then check whether the described "
        "process secretly adds or removes it. Name the conservation that is violated.",
        "invariant / conservation checking is standard in physical reasoning"),
    "inversion": (
        "Method: INVERT the goal. Ask what would most reliably GUARANTEE the bad outcome; the single "
        "most catastrophic-and-reliable action is the answer.",
        "inversion (Jacobi's 'invert, always invert') is a standard heuristic"),
}


def method_text(method_class: str) -> str:
    return METHODS[method_class][0]


def scrambled(method_class: str) -> str:
    """Same words, structure destroyed — isolates whether STRUCTURE (not tone/length) is what helps.
    Deterministic: seeded by the class name, so the scramble is replay-stable."""
    words = method_text(method_class).split()
    rng = random.Random(hash_seed(method_class))
    rng.shuffle(words)
    return " ".join(words)


def irrelevant_for(method_class: str) -> str:
    """A REAL method for a DIFFERENT skill — isolates 'methodical tone' without relevance. Picked
    deterministically (the next class in sorted order), so it is a genuine but off-target discipline."""
    classes = sorted(METHODS)
    i = classes.index(method_class)
    return method_text(classes[(i + 1) % len(classes)])


def neutral_preamble(method_class: str) -> str:
    """A content-free 'be careful' preamble, length-matched to the method — isolates the pure
    token/attention effect ('more prompt = more care')."""
    target = len(method_text(method_class).split())
    filler = ("Take your time. Read the problem carefully. Work step by step. Be precise and "
              "double-check before you commit to a final answer.")
    base = filler.split()
    out = []
    while len(out) < target:
        out.extend(base)
    return " ".join(out[:target])


def hash_seed(s: str) -> int:
    import hashlib
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)
