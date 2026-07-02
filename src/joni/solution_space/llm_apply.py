"""The real ``apply_fn``: an LLM applies the proposed deep method to RESOLVE a checkable conflict.

Given (core, proposal) it reads the target conflict's two claims, optionally prepends the proposed
method (or a control preamble), asks the solver which claim is correct, checks the answer
DETERMINISTICALLY against the registry, and resolves the conflict in the core ONLY IF the answer is
right. So the cycle's grade (conflict resolved -> success) reflects a deterministically-correct
resolution, never a judgement — the one honest way to grade an executed method. The four modes give
the pre-registered control battery: method / none / scrambled / irrelevant.
"""

from __future__ import annotations

import re

from ..method_trial import checkers as C
from ..method_trial import deep_methods as D

_AB = re.compile(r"\b([AB])\b")


def _choice(ans: str) -> str | None:
    hits = _AB.findall(C.answer_region(ans).upper())
    return hits[-1] if hits else None


def _preamble(method_id: str, mode: str) -> str:
    if mode == "method":
        return D.as_preamble(method_id)
    if mode == "scrambled":
        return D.scrambled_deep(method_id)
    if mode == "irrelevant":
        return D.irrelevant_deep(method_id)
    return ""                                  # "none" -> the naked baseline


def make_llm_apply(solver, registry, *, mode: str = "method"):
    """Build an ``apply_fn(core, proposal)`` that resolves a conflict iff the solver (optionally
    guided by the proposed method) picks the objectively-correct claim. ``mode`` in
    {method, none, scrambled, irrelevant}."""
    import desi_layer9 as l9
    from desi_layer9 import ObjectType, Operator, ProposalType
    from desi_layer9.provenance import Provenance

    def _text(core, oid: str) -> str:
        return next((c.text for c in core.all(ObjectType.CLAIM) if c.id == oid), "")

    def apply(core, proposal) -> None:
        cid = proposal.target.split(":", 1)[-1]
        info = registry.get(cid)
        if not info:
            return
        a_text, b_text = _text(core, info["a_id"]), _text(core, info["b_id"])
        pre = _preamble(proposal.method_id, mode)
        head = f"{pre}\n\n" if pre else ""
        prompt = (f"{head}Two claims are in conflict; exactly one is correct.\n"
                  f"(A) {a_text}\n(B) {b_text}\n"
                  f"Which claim is correct? End with 'Answer: A' or 'Answer: B'.")
        choice = _choice(solver.solve(prompt))
        if choice is not None and choice == info["correct"]:
            core.submit(l9.make_proposal(
                ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_RESOLVE,
                payload={"to": "resolved", "resolution": f"claim {choice} is correct",
                         "reason": f"resolved via {proposal.method_id} ({mode})"},
                proposer="joni", provenance=Provenance.from_operator(),
                target_objects=(cid,)))
        # a wrong / missing answer leaves the conflict OPEN -> the cycle grades it no_benefit

    return apply
