"""Pinned model calls with full capture + replay - reproducibility without removing semantics.

Replay-stability used to come from *not* calling a model. Here it comes from **persisted
captures**: every call records its full identity (requested + served model, provider, sampling,
DESi ``state_k``, prompt hash, output hash, run/call id) and its output. A re-run with the same
pinned config and prompt returns the *captured* output instead of calling again - so the
semantic layer is replay-stable while still being real model work.

Hard rules, enforced here:

  * **No provider fallback.** One profile, one provider, one served slug. A failure raises (the
    caller treats it as "no proposal this cycle"); it is never silently retried on another model.
  * **No silent model switch.** The capture records requested vs served; a substitution is
    explicit and auditable.

``_complete`` is the single network seam (tests monkeypatch it); nothing else here touches the
network. Captures live under ``state/model_calls/`` - a content-addressed output store plus an
append-only ``calls.jsonl`` audit log.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .model_profile import ModelProfile


@dataclass(frozen=True)
class Capture:
    """The reproducibility record persisted for every model call."""

    requested_model: str
    served_model: str
    provider: str
    temperature: float
    seed: int
    max_tokens: int
    sampling_sha: str
    state_k: int
    prompt_sha: str
    output_sha: str
    run_id: str
    call_id: str
    replayed: bool
    escalation_reason: str | None = None   # why DeepSeek was invoked (None = primary/Granite)


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _complete(profile: ModelProfile, system: str, user: str) -> str:
    """The one network seam: a single OpenAI-compatible call to the profile's pinned provider.
    No fallback. Raises on any error - the caller decides what to do, but never switches model.
    Tests monkeypatch this function."""
    import os

    from openai import OpenAI
    key = os.getenv(profile.key_env) if profile.key_env else "local"
    if not key:
        raise RuntimeError(f"no key in {profile.key_env} for profile {profile.name}")
    client = OpenAI(api_key=key, base_url=profile.base_url, timeout=30)
    resp = client.chat.completions.create(
        model=profile.served_slug,
        temperature=profile.sampling.temperature,
        max_tokens=profile.sampling.max_tokens,
        seed=profile.sampling.seed,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return (resp.choices[0].message.content or "").strip()


def _store(store_dir: Path) -> tuple[Path, Path]:
    out = store_dir / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out, store_dir / "calls.jsonl"


def call(profile: ModelProfile, system: str, user: str, *, run_id: str, store_dir: Path,
         escalation_reason: str | None = None) -> tuple[str | None, Capture | None]:
    """Run (or replay) one pinned call. Returns ``(output, capture)``; ``(None, None)`` if the
    live call failed (best-effort: no proposal this cycle, never a silent fallback).

    ``escalation_reason`` is recorded in the capture: it names *why* an escalation model (DeepSeek)
    was invoked - a primary Granite call leaves it ``None``. It is metadata only and is NOT part of
    the replay key (same prompt + pinned config replays regardless of why it was reached)."""
    prompt = f"<<SYSTEM>>\n{system}\n<<USER>>\n{user}"
    prompt_sha = _sha(prompt)
    key = _sha(f"{profile.config_sha()}|{prompt_sha}")
    out_dir, log = _store(store_dir)
    cached = out_dir / f"{key}.txt"
    call_id = f"{run_id}:{prompt_sha[:12]}"

    def _record(output: str, replayed: bool) -> Capture:
        cap = Capture(
            requested_model=profile.model_id, served_model=profile.served_slug,
            provider=profile.provider, temperature=profile.sampling.temperature,
            seed=profile.sampling.seed, max_tokens=profile.sampling.max_tokens,
            sampling_sha=profile.sampling.sha256(), state_k=profile.state_k,
            prompt_sha=prompt_sha, output_sha=_sha(output), run_id=run_id,
            call_id=call_id, replayed=replayed, escalation_reason=escalation_reason)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(cap), sort_keys=True) + "\n")
        return cap

    if cached.exists():                                  # replay from the persisted capture
        output = cached.read_text(encoding="utf-8")
        return output, _record(output, replayed=True)

    try:
        output = _complete(profile, system, user)
    except Exception:  # noqa: BLE001 - a failed pinned call is "no proposal", never a fallback
        return None, None
    cached.write_text(output, encoding="utf-8")
    return output, _record(output, replayed=False)
