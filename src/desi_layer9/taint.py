"""Taint - contamination that survives derivation.

Taint records how an object may be epistemically compromised. Its defining property:
**taint does not disappear through summarisation or rephrasing.** A neutral summary
derived from contaminated material stays contaminated. Only an explicit human-validation
operator may set ``human_validated`` - and even then the contamination flags remain a
matter of record; ``human_validated`` marks that a human signed off *despite* them.
"""

from __future__ import annotations

from dataclasses import dataclass

# The contamination flags that propagate (logical OR) through any derivation.
_CONTAMINATION_FIELDS = (
    "source_exposed",
    "interaction_exposed",
    "affective_pressure",
    "adversarial_source",
    "frame_contamination_possible",
    "role_contamination_possible",
    "unverified_model_output",
)


@dataclass(frozen=True)
class Taint:
    source_exposed: bool = False
    interaction_exposed: bool = False
    affective_pressure: bool = False
    adversarial_source: bool = False
    frame_contamination_possible: bool = False
    role_contamination_possible: bool = False
    unverified_model_output: bool = False
    human_validated: bool = False

    @property
    def is_clean(self) -> bool:
        """Clean = no contamination flag set (regardless of human_validated)."""
        return not any(getattr(self, f) for f in _CONTAMINATION_FIELDS)

    @property
    def is_contaminated(self) -> bool:
        return not self.is_clean

    def merge(self, other: Taint) -> Taint:
        """Combine taint from multiple parents: contamination ORs, validation drops.

        A derived object is never automatically human-validated just because a parent
        was - validation must be re-asserted by a human operator on the new object.
        """
        merged = {f: getattr(self, f) or getattr(other, f) for f in _CONTAMINATION_FIELDS}
        return Taint(**merged, human_validated=False)

    def derive(self, *, unverified_model_output: bool = False) -> Taint:
        """Taint for an object derived from this one (e.g. a summary).

        Contamination is carried forward verbatim; a derivation can only *add* taint
        (e.g. a model rephrasing adds ``unverified_model_output``), never remove it, and
        is never human_validated by inheritance.
        """
        flags = {f: getattr(self, f) for f in _CONTAMINATION_FIELDS}
        flags["unverified_model_output"] = (
            flags["unverified_model_output"] or unverified_model_output
        )
        return Taint(**flags, human_validated=False)

    def with_human_validation(self) -> Taint:
        """Mark human-validated. Only a human operator may call this (gate-enforced)."""
        flags = {f: getattr(self, f) for f in _CONTAMINATION_FIELDS}
        return Taint(**flags, human_validated=True)

    def to_dict(self) -> dict:
        return {f: getattr(self, f) for f in (*_CONTAMINATION_FIELDS, "human_validated")}

    @classmethod
    def from_dict(cls, d: dict) -> Taint:
        return cls(**{k: bool(d.get(k, False))
                      for k in (*_CONTAMINATION_FIELDS, "human_validated")})


def merge_all(taints: list[Taint]) -> Taint:
    """OR-merge a list of taints (e.g. a claim derived from several evidence items)."""
    out = Taint()
    for t in taints:
        out = out.merge(t)
    return out
