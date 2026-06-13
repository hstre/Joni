"""Machine-readable provenance.

Provenance is structured, not free text: where a piece of state came from, which model
and sampling config produced it, under which run/call. Unknown facts are stored as
``unknown`` / ``unverified`` - never invented. This is what lets the gate reason about
authority and taint instead of trusting a model's self-description.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import OriginType

UNKNOWN = "unknown"
UNVERIFIED = "unverified"


@dataclass(frozen=True)
class Provenance:
    origin_type: OriginType = OriginType.UNKNOWN
    source_ids: tuple[str, ...] = ()
    model_id: str = UNKNOWN
    provider: str = UNKNOWN
    served_model: str = UNKNOWN
    sampling_config_sha256: str = UNVERIFIED
    run_id: str = UNKNOWN
    call_id: str = UNKNOWN

    # -- constructors for the common origins -------------------------------- #
    @classmethod
    def from_user(cls) -> Provenance:
        return cls(origin_type=OriginType.USER)

    @classmethod
    def from_human(cls) -> Provenance:
        return cls(origin_type=OriginType.HUMAN)

    @classmethod
    def from_operator(cls, run_id: str = UNKNOWN) -> Provenance:
        return cls(origin_type=OriginType.DETERMINISTIC_OPERATOR, run_id=run_id)

    @classmethod
    def from_source(cls, *source_ids: str) -> Provenance:
        return cls(origin_type=OriginType.SOURCE, source_ids=tuple(source_ids))

    @classmethod
    def from_model(
        cls, *, external: bool, model_id: str = UNKNOWN, provider: str = UNKNOWN,
        served_model: str = UNKNOWN, sampling_config_sha256: str = UNVERIFIED,
        run_id: str = UNKNOWN, call_id: str = UNKNOWN,
    ) -> Provenance:
        return cls(
            origin_type=OriginType.EXTERNAL_MODEL if external else OriginType.LOCAL_MODEL,
            model_id=model_id, provider=provider, served_model=served_model,
            sampling_config_sha256=sampling_config_sha256, run_id=run_id, call_id=call_id,
        )

    @classmethod
    def imported(cls, *source_ids: str) -> Provenance:
        return cls(origin_type=OriginType.IMPORTED_STATE, source_ids=tuple(source_ids))

    @property
    def is_model_output(self) -> bool:
        return self.origin_type in (OriginType.LOCAL_MODEL, OriginType.EXTERNAL_MODEL)

    def to_dict(self) -> dict:
        return {
            "origin_type": self.origin_type.value,
            "source_ids": list(self.source_ids),
            "model_id": self.model_id,
            "provider": self.provider,
            "served_model": self.served_model,
            "sampling_config_sha256": self.sampling_config_sha256,
            "run_id": self.run_id,
            "call_id": self.call_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Provenance:
        return cls(
            origin_type=OriginType(d.get("origin_type", "unknown")),
            source_ids=tuple(d.get("source_ids", ())),
            model_id=d.get("model_id", UNKNOWN),
            provider=d.get("provider", UNKNOWN),
            served_model=d.get("served_model", UNKNOWN),
            sampling_config_sha256=d.get("sampling_config_sha256", UNVERIFIED),
            run_id=d.get("run_id", UNKNOWN),
            call_id=d.get("call_id", UNKNOWN),
        )
