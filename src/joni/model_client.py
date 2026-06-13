"""The language boundary.

The renderer composes a deterministic, state-grounded **brief** of what Joni should
say. A model only *phrases* that brief in voice. It never invents state. This keeps
the ecosystem rule intact - **LLM for language, rules for logic** - and is the whole
reason the personhood stays dissolvable: the content is in Layer 9, the model just
gives it a mouth.

Default is a deterministic ``MockModel`` (offline, no key, replay-stable). A real
DeepSeek/OpenAI client phrases the brief in Joni's voice when enabled; the engines,
state and ledger are identical either way.
"""

from __future__ import annotations

import os
import time
from typing import Protocol, runtime_checkable

_TRANSIENT_MARKERS = (
    "resolve_no_records", "private/reserved", "temporarily", "timeout", "timed out",
    "connection", "overloaded", "rate limit", "too many requests",
    "502", "503", "504", "bad gateway", "service unavailable", "gateway timeout",
)
_TRANSIENT_EXCEPTIONS = {
    "APIConnectionError", "APITimeoutError", "RateLimitError",
    "InternalServerError", "APIStatusError",
}


def _is_transient(exc: Exception) -> bool:
    if type(exc).__name__ in _TRANSIENT_EXCEPTIONS:
        return True
    blob = str(exc).lower()
    return any(marker in blob for marker in _TRANSIENT_MARKERS)


@runtime_checkable
class ModelClient(Protocol):
    """The only surface through which language enters Joni."""

    def phrase(self, brief: str, *, voice: str) -> str:
        """Render a state-grounded brief in the given voice. Language only."""


class MockModel:
    """Deterministic, offline voice. Returns the brief as-is.

    Because the renderer's brief is already first-person and grounded, the mock voice
    is simply that brief - which makes the whole conversation replay-stable and keeps
    the Conversation View faithful to Layer 9 with zero setup. Swap in a real model
    for natural phrasing; nothing else changes.
    """

    def phrase(self, brief: str, *, voice: str) -> str:
        return brief


class OpenAICompatibleModel:
    """Real voice: DeepSeek / OpenAI, behind the same interface.

    Matches the ecosystem client: ``DEEPSEEK_API_KEY`` (or ``DEEPSEEK_API_KEY2``)
    takes priority over ``OPENAI_API_KEY``; model ``deepseek-chat`` or ``gpt-4o``.
    It rephrases the brief in voice but is instructed to add no new facts.
    """

    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - only without the extra
            raise RuntimeError(
                "The real model client needs the 'openai' package: pip install 'joni[llm]'"
            ) from exc
        deepseek = os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY2")
        openai_key = os.getenv("OPENAI_API_KEY")
        if deepseek:
            self._model = model or "deepseek-chat"
            self._client = OpenAI(api_key=deepseek, base_url=base_url or "https://api.deepseek.com")
        elif openai_key:
            self._model = model or "gpt-4o"
            self._client = OpenAI(api_key=openai_key, base_url=base_url)
        else:  # pragma: no cover - config error path
            raise RuntimeError(
                "No model key found. Set DEEPSEEK_API_KEY or OPENAI_API_KEY, "
                "or unset JONI_USE_REAL_LLM to use the MockModel."
            )
        self._max_retries = int(os.getenv("JONI_LLM_RETRIES", "4"))
        self._backoff_base = float(os.getenv("JONI_LLM_BACKOFF", "0.5"))

    def phrase(self, brief: str, *, voice: str) -> str:
        system = (
            f"You are the *voice* of an operative identity. Speak as: {voice}. "
            "Rephrase the brief below naturally in the first person. Add NO new facts, "
            "claims, numbers or commitments - the brief is the entire truth you may use."
        )
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": brief},
                    ],
                    temperature=0.7,
                )
                return (resp.choices[0].message.content or brief).strip()
            except Exception as exc:  # noqa: BLE001 - retry transient, re-raise the rest
                if attempt >= self._max_retries or not _is_transient(exc):
                    raise
                last = exc
                time.sleep(self._backoff_base * (2 ** attempt))
        raise last  # unreachable


def get_default_model() -> ModelClient:
    """Return the configured voice. MockModel unless ``JONI_USE_REAL_LLM=1``."""
    if os.getenv("JONI_USE_REAL_LLM") == "1":  # pragma: no cover - needs key + network
        return OpenAICompatibleModel()
    return MockModel()
