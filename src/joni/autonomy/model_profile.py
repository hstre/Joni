"""Model profiles - the pinned, captured identity of every model call Joni makes.

The architecture rule is no longer "LLM only for the renderer". Real semantic model work is
allowed as a **non-authoritative proposal layer** (free text -> Claim/Evidence/Conflict
proposals, source interpretation, self-model proposals, pre-gate reviews). But every call must
be *pinned and reproducible*: a fixed model, fixed sampling, no provider fallback, no silent
model switch, and a full capture (see ``model_call.py``).

Two axes are kept **strictly separate**, exactly as specified:

* ``Sampling`` - the model's decoding config (``temperature`` / ``seed`` / ``max_tokens``);
* ``state_k`` - the **DESi state-slice density**: how many relevant Layer-9 state elements the
  semantic projector is allowed to see as context. This is NOT the ``top_k`` sampling argument.

Four profiles, each independently configurable (env-overridable so a profile can be re-pinned
without code changes), because they are optimised for different jobs:

  * ``joni-semantic`` - controlled semantic projection into proposals. Granite, ``state_k=1``.
  * ``reference``     - an explicit control/regression arm. Llama 3.1 8B, ``state_k=5``. Never an
    automatic fallback; selected only on purpose.
  * ``kevin``         - creative exploration. Its own model, NOT Joni's semantic model or k.
  * ``renderer``      - language/voice only. Separate interface and separate provenance, so a
    semantic projection and a phrasing call are never the same indistinguishable call.

The default ``model_id`` records the *requested* pin (e.g. ``granite-4.0-h-micro``); the
``served_slug`` is what the provider actually serves. The capture records both, so any
divergence is auditable - a substitution is explicit and logged, never silent.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Sampling:
    """Decoding configuration - deterministic by default (temperature 0, fixed seed)."""

    temperature: float = 0.0
    seed: int = 7
    max_tokens: int = 768

    def sha256(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class ModelProfile:
    name: str                 # joni-semantic | reference | kevin | renderer
    model_id: str             # the *requested* pin (identity), e.g. "granite-4.0-h-micro"
    provider: str             # "openrouter" | "ollama" | "pinned" - never falls back
    base_url: str
    key_env: str              # env var holding the api key (empty for a keyless local provider)
    served_slug: str          # the slug the provider is actually asked for (may differ; captured)
    sampling: Sampling
    state_k: int              # DESi state-slice density (0 = not a semantic projector)

    def config_sha(self) -> str:
        """A hash over the whole pinned config - part of a capture's replay key."""
        blob = json.dumps(
            {"model_id": self.model_id, "provider": self.provider, "served": self.served_slug,
             "sampling": self.sampling.sha256(), "state_k": self.state_k}, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


# Granite 4.0 H Micro is the *requested* semantic pin. It is not on OpenRouter today, so the
# served slug is configurable (JONI_GRANITE_SLUG); whatever serves it is captured, so the
# substitution is explicit, never silent. Re-pin by setting the env vars.
def joni_semantic() -> ModelProfile:
    return ModelProfile(
        name="joni-semantic",
        model_id=_env("JONI_SEMANTIC_MODEL_ID", "granite-4.0-h-micro"),
        provider=_env("JONI_SEMANTIC_PROVIDER", "openrouter"),
        base_url=_env("JONI_SEMANTIC_BASE_URL", "https://openrouter.ai/api/v1"),
        key_env=_env("JONI_SEMANTIC_KEY_ENV", "OPENROUTER_API_KEY"),
        served_slug=_env("JONI_GRANITE_SLUG", "ibm-granite/granite-4.1-8b-20260429"),
        sampling=Sampling(
            temperature=float(_env("JONI_SEMANTIC_TEMPERATURE", "0.0")),
            seed=int(_env("JONI_SEMANTIC_SEED", "7")),
            max_tokens=int(_env("JONI_SEMANTIC_MAX_TOKENS", "768"))),
        state_k=int(_env("JONI_SEMANTIC_STATE_K", "1")))


def reference() -> ModelProfile:
    """Explicit control arm - never an automatic fallback in the production path."""
    return ModelProfile(
        name="reference",
        model_id=_env("JONI_REFERENCE_MODEL_ID", "llama-3.1-8b"),
        provider=_env("JONI_REFERENCE_PROVIDER", "openrouter"),
        base_url=_env("JONI_REFERENCE_BASE_URL", "https://openrouter.ai/api/v1"),
        key_env=_env("JONI_REFERENCE_KEY_ENV", "OPENROUTER_API_KEY"),
        served_slug=_env("JONI_REFERENCE_SLUG", "meta-llama/llama-3.1-8b-instruct"),
        sampling=Sampling(
            temperature=float(_env("JONI_REFERENCE_TEMPERATURE", "0.0")),
            seed=int(_env("JONI_REFERENCE_SEED", "7")),
            max_tokens=int(_env("JONI_REFERENCE_MAX_TOKENS", "768"))),
        state_k=int(_env("JONI_REFERENCE_STATE_K", "5")))


def kevin() -> ModelProfile:
    """Kevin's own profile - creative exploration, NOT Joni's semantic model or k."""
    return ModelProfile(
        name="kevin",
        model_id=_env("JONI_KEVIN_MODEL_ID", "granite-4.0-h-micro"),
        provider=_env("JONI_KEVIN_PROVIDER", "openrouter"),
        base_url=_env("JONI_KEVIN_BASE_URL", "https://openrouter.ai/api/v1"),
        key_env=_env("JONI_KEVIN_KEY_ENV", "OPENROUTER_API_KEY"),
        served_slug=_env("JONI_KEVIN_SLUG", "ibm-granite/granite-4.1-8b-20260429"),
        sampling=Sampling(
            temperature=float(_env("JONI_KEVIN_TEMPERATURE", "0.7")),    # creative, not 0
            seed=int(_env("JONI_KEVIN_SEED", "7")),
            max_tokens=int(_env("JONI_KEVIN_MAX_TOKENS", "768"))),
        state_k=int(_env("JONI_KEVIN_STATE_K", "0")))    # Kevin does not use Joni's state slice


def renderer() -> ModelProfile:
    """Voice/phrasing only - separate interface and provenance from semantic projection."""
    return ModelProfile(
        name="renderer",
        model_id=_env("JONI_RENDERER_MODEL_ID", "granite-4.0-h-micro"),
        provider=_env("JONI_RENDERER_PROVIDER", "openrouter"),
        base_url=_env("JONI_RENDERER_BASE_URL", "https://openrouter.ai/api/v1"),
        key_env=_env("JONI_RENDERER_KEY_ENV", "OPENROUTER_API_KEY"),
        served_slug=_env("JONI_RENDERER_SLUG", "ibm-granite/granite-4.1-8b-20260429"),
        sampling=Sampling(
            temperature=float(_env("JONI_RENDERER_TEMPERATURE", "0.4")),
            seed=int(_env("JONI_RENDERER_SEED", "7")),
            max_tokens=int(_env("JONI_RENDERER_MAX_TOKENS", "512"))),
        state_k=0)


_PROFILES = {"joni-semantic": joni_semantic, "reference": reference,
             "kevin": kevin, "renderer": renderer}


def profile(name: str) -> ModelProfile:
    """The named profile (freshly read so env overrides apply). Raises on an unknown name -
    a profile is never silently substituted."""
    if name not in _PROFILES:
        raise KeyError(f"unknown model profile {name!r}; known: {sorted(_PROFILES)}")
    return _PROFILES[name]()
