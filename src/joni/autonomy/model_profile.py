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

Model choice follows the operator's own benchmark results (README): a **small-LLM extraction
layer is harmful** (micro-extraction -40%, hybrid evidence cards -60%, question-aware
extraction -80%), so Joni does NOT use a tiny model as its semantic core. Instead:

  * **Difficult** semantic work (hard conflicts, source/contradiction analysis) -> **DeepSeek
    Pro v4, called directly via the DeepSeek API** (``joni-hard``).
  * **The rest** - structured paper/state audits, claim extraction/projection -> **Granite
    4.1 8B** (``joni-semantic``).

``state_k`` is **task-specific and is NOT inherited** between profiles (the README is explicit:
calibrate ``k`` per task) - each profile pins its own density.

Profiles, each independently configurable (env-overridable so a profile can be re-pinned
without code changes), because they are optimised for different jobs:

  * ``joni-semantic`` - structured projection into proposals. Granite 4.1 8B, ``state_k=1``.
  * ``joni-hard``     - difficult semantic analysis. DeepSeek Pro v4 via the DeepSeek API,
    richer ``state_k``. Selected only for hard tasks; never an automatic fallback.
  * ``reference``     - an explicit control/regression arm. Llama 3.1 8B, ``state_k=5``. Never an
    automatic fallback; selected only on purpose.
  * ``kevin``         - creative exploration. Its own model, NOT Joni's semantic model or k.
  * ``renderer``      - language/voice only. Separate interface and separate provenance, so a
    semantic projection and a phrasing call are never the same indistinguishable call.

The default ``model_id`` records the *requested* pin (e.g. ``granite-4.1-8b``); the
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


# "The rest" - structured paper/state audits and claim projection - use **Granite 4.1 8B**
# (NOT a micro model: the operator's own tests show small-LLM extraction is harmful). Served via
# OpenRouter (prepaid). The requested pin equals the served slug, so there is no divergence to
# explain; re-pin by setting the env vars.
def joni_semantic() -> ModelProfile:
    return ModelProfile(
        name="joni-semantic",
        model_id=_env("JONI_SEMANTIC_MODEL_ID", "granite-4.1-8b"),
        provider=_env("JONI_SEMANTIC_PROVIDER", "openrouter"),
        base_url=_env("JONI_SEMANTIC_BASE_URL", "https://openrouter.ai/api/v1"),
        key_env=_env("JONI_SEMANTIC_KEY_ENV", "OPENROUTER_API_KEY"),
        served_slug=_env("JONI_GRANITE_SLUG", "ibm-granite/granite-4.1-8b-20260429"),
        sampling=Sampling(
            temperature=float(_env("JONI_SEMANTIC_TEMPERATURE", "0.0")),
            seed=int(_env("JONI_SEMANTIC_SEED", "7")),
            max_tokens=int(_env("JONI_SEMANTIC_MAX_TOKENS", "768"))),
        # state_k start value for calibration over {3,5,10} - NOT a shared default with joni-hard,
        # NOT a sampling top_k. Sweep via JONI_SEMANTIC_STATE_K on real Joni tasks.
        state_k=int(_env("JONI_SEMANTIC_STATE_K", "5")))


# **Difficult** semantic work - hard conflicts, source/contradiction analysis - goes to
# **DeepSeek Pro v4, called directly through the DeepSeek API** (not via OpenRouter). Per the
# DeepSeek API docs the model id is ``deepseek-v4-pro`` (the most capable; ``deepseek-chat`` is
# the smaller v4-flash and is being deprecated 2026/07/24, so we do NOT default to it). Requested
# pin == served slug here, so there is no divergence; re-pin via JONI_DEEPSEEK_SLUG. state_k is
# calibrated for this task separately (a richer slice for hard reasoning), NOT inherited.
def joni_hard() -> ModelProfile:
    return ModelProfile(
        name="joni-hard",
        model_id=_env("JONI_HARD_MODEL_ID", "deepseek-v4-pro"),
        provider=_env("JONI_HARD_PROVIDER", "deepseek"),
        base_url=_env("JONI_HARD_BASE_URL", "https://api.deepseek.com"),
        key_env=_env("JONI_HARD_KEY_ENV", "DEEPSEEK_API_KEY"),
        served_slug=_env("JONI_DEEPSEEK_SLUG", "deepseek-v4-pro"),
        sampling=Sampling(
            temperature=float(_env("JONI_HARD_TEMPERATURE", "0.0")),
            seed=int(_env("JONI_HARD_SEED", "7")),
            # deepseek-v4-pro reasons before answering, so the budget must cover thought + answer
            # or `content` truncates to empty. Evidenced by the empty-rate gradient (768: 95%
            # empty; 1024: 29%). 2048 put this escalation path at ~71%+ non-empty; left here
            # (frequent, cost-sensitive) until the instrumented finish_reason shows it needs more.
            max_tokens=int(_env("JONI_HARD_MAX_TOKENS", "2048"))),
        # state_k start value for calibration over {3,5} - its own knob, never inherited from
        # joni-semantic, never the sampling top_k. Sweep via JONI_HARD_STATE_K.
        state_k=int(_env("JONI_HARD_STATE_K", "3")))


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
    """Kevin's own profile - creative exploration on **DeepSeek Pro v4** (operator's choice), via
    the DeepSeek API directly. NOT Joni's structured semantic model or k: its own warm sampling
    and no state slice, so a creative leap is never confused with a structured projection."""
    return ModelProfile(
        name="kevin",
        model_id=_env("JONI_KEVIN_MODEL_ID", "deepseek-v4-pro"),
        provider=_env("JONI_KEVIN_PROVIDER", "deepseek"),
        base_url=_env("JONI_KEVIN_BASE_URL", "https://api.deepseek.com"),
        key_env=_env("JONI_KEVIN_KEY_ENV", "DEEPSEEK_API_KEY"),
        served_slug=_env("JONI_KEVIN_SLUG", "deepseek-v4-pro"),
        sampling=Sampling(
            temperature=float(_env("JONI_KEVIN_TEMPERATURE", "0.7")),    # creative, not 0
            seed=int(_env("JONI_KEVIN_SEED", "7")),
            # deepseek-v4-pro reasons before answering: the budget must cover the internal thought
            # AND the answer, or `content` comes back empty (truncated mid-reasoning). This is
            # evidenced, not assumed - the same model showed a clear empty-rate gradient by budget:
            # at 768 tokens 19/20 Kevin calls were empty (95%); at 1024 only 16/55 (29%). 2048 was
            # still tight, so Kevin (infrequent, cadence-spaced) gets generous headroom toward a ~0
            # empty rate. The instrumented capture (finish_reason=length, reasoning_tokens) confirms
            # the mechanism per call. Env-overridable.
            max_tokens=int(_env("JONI_KEVIN_MAX_TOKENS", "4096"))),
        state_k=int(_env("JONI_KEVIN_STATE_K", "0")))    # Kevin does not use Joni's state slice


def renderer() -> ModelProfile:
    """Voice/phrasing only - separate interface and provenance from semantic projection."""
    return ModelProfile(
        name="renderer",
        model_id=_env("JONI_RENDERER_MODEL_ID", "granite-4.1-8b"),
        provider=_env("JONI_RENDERER_PROVIDER", "openrouter"),
        base_url=_env("JONI_RENDERER_BASE_URL", "https://openrouter.ai/api/v1"),
        key_env=_env("JONI_RENDERER_KEY_ENV", "OPENROUTER_API_KEY"),
        served_slug=_env("JONI_RENDERER_SLUG", "ibm-granite/granite-4.1-8b-20260429"),
        sampling=Sampling(
            temperature=float(_env("JONI_RENDERER_TEMPERATURE", "0.4")),
            seed=int(_env("JONI_RENDERER_SEED", "7")),
            max_tokens=int(_env("JONI_RENDERER_MAX_TOKENS", "512"))),
        state_k=0)


_PROFILES = {"joni-semantic": joni_semantic, "joni-hard": joni_hard, "reference": reference,
             "kevin": kevin, "renderer": renderer}


def profile(name: str) -> ModelProfile:
    """The named profile (freshly read so env overrides apply). Raises on an unknown name -
    a profile is never silently substituted."""
    if name not in _PROFILES:
        raise KeyError(f"unknown model profile {name!r}; known: {sorted(_PROFILES)}")
    return _PROFILES[name]()


# Tasks the operator classified as "difficult" - hard conflicts and source/contradiction
# analysis - route to DeepSeek; everything else (structured extraction/projection/audit) to
# Granite 4.1 8B. This is a deliberate, named routing, not a fallback chain.
_HARD_TASKS = frozenset({"conflict", "source-analysis", "contradiction", "hard"})


def for_task(kind: str) -> ModelProfile:
    """Pick the pinned profile for a semantic task by difficulty class. Difficult tasks ->
    ``joni-hard`` (DeepSeek Pro v4); the rest -> ``joni-semantic`` (Granite 4.1 8B)."""
    return profile("joni-hard" if kind in _HARD_TASKS else "joni-semantic")
