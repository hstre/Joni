"""The solver seam — pluggable, so the harness is model-agnostic and testable without spend.

``DeepSeekSolver`` calls DeepSeek's OpenAI-compatible endpoint (temperature 0, reads
``DEEPSEEK_API_KEY`` from the ENVIRONMENT — never a hard-coded secret). ``StubSolver`` proves the
whole Stage-2 pipeline end-to-end deterministically, no network, no cost. The solver only
*produces text*; grading is the separate deterministic checker (no self-grading, by construction).
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.request
from collections.abc import Callable


class Solver:
    name: str = "solver"

    def solve(self, prompt: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class StubSolver(Solver):
    """Deterministic offline solver for tests: delegates to a callable ``prompt -> answer text``."""

    name = "stub"

    def __init__(self, fn: Callable[[str], str]) -> None:
        self._fn = fn

    def solve(self, prompt: str) -> str:
        return self._fn(prompt)


def _ssl_context() -> ssl.SSLContext | None:
    # Trust the agent-proxy CA bundle if present (this environment routes HTTPS through a proxy).
    ca = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
    if ca and os.path.exists(ca):
        return ssl.create_default_context(cafile=ca)
    return None


class DeepSeekSolver(Solver):
    """OpenAI-compatible DeepSeek client. temp=0 for replay-stability; never stores the key."""

    name = "deepseek"

    def __init__(self, *, model: str = "deepseek-chat", temperature: float = 0.0,
                 max_tokens: int = 512, timeout: int = 60,
                 base_url: str = "https://api.deepseek.com/chat/completions") -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.base_url = base_url

    def solve(self, prompt: str) -> str:
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Add it to the environment secrets (never paste a key "
                "into chat), then re-run.")
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=body, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout, context=_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


def list_models(*, base_url: str = "https://api.deepseek.com/models") -> list[str]:
    """Ask the DeepSeek API which models it actually serves (GET /models). Reads DEEPSEEK_API_KEY
    from the environment. Used to DISCOVER whether a smaller model exists rather than guess an id."""
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set.")
    req = urllib.request.Request(base_url, method="GET", headers={
        "Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [m.get("id", "?") for m in data.get("data", [])]
