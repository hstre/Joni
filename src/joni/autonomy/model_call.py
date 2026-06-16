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
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
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
    ts: str = ""                           # ISO-8601 UTC time of this (replay or live) call
    # Instrumentation (review: do NOT guess why a call was empty - record the evidence). These
    # distinguish the failure classes: model returned nothing vs adapter lost it vs parser failed.
    finish_reason: str = ""                # "stop" | "length" | "content_filter" | "" (replay)
    served_actual: str = ""                # the model the provider says it served
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0              # tokens the reasoning model spent BEFORE the answer
    content_len: int = 0                   # length of the answer (`content`) field
    reasoning_len: int = 0                # length of a separate `reasoning_content` field, if any
    raw_sha: str = ""                      # hash of the full raw API response (preserved sidecar)


@dataclass(frozen=True)
class Raw:
    """A live call's full evidence - so an empty answer is *diagnosable*, not guessed at."""

    text: str
    finish_reason: str = ""
    served: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    reasoning_len: int = 0
    raw_json: str = ""


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _complete(profile: ModelProfile, system: str, user: str) -> Raw:
    """The one network seam: a single OpenAI-compatible call to the profile's pinned provider.
    No fallback. Raises on any error - the caller decides what to do, but never switches model.
    Returns the full evidence (``Raw``); tests may monkeypatch this to return a plain ``str``."""
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
    return _to_raw(resp)


def _to_raw(resp) -> Raw:
    """Parse a provider chat-completion response into the full ``Raw`` evidence. Extracted from the
    network seam so the *parsing* (the original empty-content bug locus) is testable without a call:
    a reasoning model that returns ``content=None`` + ``finish_reason='length'`` + nested
    ``reasoning_tokens`` must surface as ``text=''`` with the truncation evidence intact."""
    choice = resp.choices[0]
    msg = choice.message
    content = (getattr(msg, "content", None) or "").strip()
    reasoning = getattr(msg, "reasoning_content", None) or ""
    usage = getattr(resp, "usage", None)
    pt = int(getattr(usage, "prompt_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or 0)
    details = getattr(usage, "completion_tokens_details", None)
    rt = int(getattr(details, "reasoning_tokens", 0) or 0) if details is not None else 0
    try:
        raw_json = resp.model_dump_json() if hasattr(resp, "model_dump_json") else str(resp)
    except Exception:  # noqa: BLE001
        raw_json = ""
    return Raw(text=content, finish_reason=getattr(choice, "finish_reason", "") or "",
               served=getattr(resp, "model", "") or "", prompt_tokens=pt, completion_tokens=ct,
               reasoning_tokens=rt, reasoning_len=len(reasoning), raw_json=raw_json)


def _store(store_dir: Path) -> tuple[Path, Path]:
    out = store_dir / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out, store_dir / "calls.jsonl"


def call(profile: ModelProfile, system: str, user: str, *, run_id: str, store_dir: Path,
         escalation_reason: str | None = None, budget=None,
         runs_per_week: int = 0) -> tuple[str | None, Capture | None]:
    """Run (or replay) one pinned call. Returns ``(output, capture)``; ``(None, None)`` if the
    live call failed (best-effort: no proposal this cycle, never a silent fallback).

    ``escalation_reason`` is recorded in the capture: it names *why* an escalation model (DeepSeek)
    was invoked - a primary Granite call leaves it ``None``. It is metadata only and is NOT part of
    the replay key (same prompt + pinned config replays regardless of why it was reached).

    ``budget`` (optional): the weekly EUR cap governs the SEMANTIC ENGINE too, not just the panel.
    A *live* call is only made if ``budget.can_spend(est)`` allows it; otherwise it returns
    ``(None, None)`` (cap reached -> no proposal this cycle, never a fallback). Replays are free and
    never charged. With ``budget=None`` the call is ungoverned (tests / standalone)."""
    prompt = f"<<SYSTEM>>\n{system}\n<<USER>>\n{user}"
    prompt_sha = _sha(prompt)
    key = _sha(f"{profile.config_sha()}|{prompt_sha}")
    out_dir, log = _store(store_dir)
    cached = out_dir / f"{key}.txt"
    call_id = f"{run_id}:{prompt_sha[:12]}"

    def _record(output: str, replayed: bool, raw: Raw | None = None) -> Capture:
        cap = Capture(
            requested_model=profile.model_id, served_model=profile.served_slug,
            provider=profile.provider, temperature=profile.sampling.temperature,
            seed=profile.sampling.seed, max_tokens=profile.sampling.max_tokens,
            sampling_sha=profile.sampling.sha256(), state_k=profile.state_k,
            prompt_sha=prompt_sha, output_sha=_sha(output), run_id=run_id,
            call_id=call_id, replayed=replayed, escalation_reason=escalation_reason,
            ts=datetime.now(UTC).isoformat(timespec="seconds"),
            finish_reason=(raw.finish_reason if raw else ""),
            served_actual=(raw.served if raw else ""),
            prompt_tokens=(raw.prompt_tokens if raw else 0),
            completion_tokens=(raw.completion_tokens if raw else 0),
            reasoning_tokens=(raw.reasoning_tokens if raw else 0),
            content_len=len(output), reasoning_len=(raw.reasoning_len if raw else 0),
            raw_sha=(_sha(raw.raw_json) if raw and raw.raw_json else ""))
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(cap), sort_keys=True) + "\n")
        return cap

    if cached.exists():                                  # replay from the persisted capture
        output = cached.read_text(encoding="utf-8")
        return output, _record(output, replayed=True)    # replays are free - never charged

    # A LIVE call is about to cost money: the weekly cap governs the semantic engine here, at the
    # one seam every model path goes through. Cap reached -> no live call (best-effort, no fallbk).
    est = est_call_cost(profile)
    if budget is not None and est > 0 and not budget.can_spend(est, runs_per_week=runs_per_week):
        return None, None

    try:
        res = _complete(profile, system, user)
    except Exception:  # noqa: BLE001 - a failed pinned call is "no proposal", never a fallback
        return None, None
    if budget is not None and est > 0:
        budget.charge(est)                               # account the live call against the cap
    # the seam may return a plain str (tests) or the full Raw evidence (production)
    raw = res if isinstance(res, Raw) else None
    output = res.text if isinstance(res, Raw) else res
    # NEVER cache an empty answer. A content-addressed cache of "" would be replayed forever as a
    # stable "successful" empty result - laundering a model failure (truncation / wrong field /
    # filter) into a reproducible non-result that the empty-call classifier (live-only) can no
    # longer see. Leaving it uncached means the next cycle retries the call instead. The failure is
    # still recorded (with its finish_reason/tokens) so it stays diagnosable.
    if output.strip():
        cached.write_text(output, encoding="utf-8")
        if raw is not None and raw.raw_json:             # preserve the full raw response sidecar
            (out_dir / f"{key}.raw.json").write_text(raw.raw_json, encoding="utf-8")
    return output, _record(output, replayed=False, raw=raw)


def est_call_cost(profile: ModelProfile) -> float:
    """Estimated EUR for ONE live call on this profile, from the same env-dialled per-call rates the
    telemetry uses. DeepSeek (the metered escalation/Kevin path) carries the real cost; Granite via
    prepaid OpenRouter is €0 by default (so the EUR cap meaningfully governs the metered paths)."""
    if profile.provider == "deepseek":
        return _cost_per_call("JONI_COST_PER_DEEPSEEK_CALL", "0.004")
    if profile.provider:
        return _cost_per_call("JONI_COST_PER_GRANITE_CALL", "0.0")
    return 0.0


def _cost_per_call(env: str, default: str) -> float:
    try:
        return float(os.getenv(env, default))
    except ValueError:
        return float(default)


def telemetry(store_dir: Path) -> dict:
    """Aggregate the capture log into dashboard telemetry, so whether the semantic engine is
    actually working is read off real records - never guessed from a €0 line. Counts live vs
    replayed (cached) calls per provider, the escalation count, the last call's time, and an
    *estimated* API cost (per-call rates are env-dialled; exact spend is on the provider page)."""
    log = store_dir / "calls.jsonl"
    out = {"llm_calls": 0, "granite_calls": 0, "deepseek_escalations": 0, "kevin_calls": 0,
           "cached_calls": 0, "live_calls": 0, "last_call": "", "est_cost_eur": 0.0,
           "by_model": {},
           # Empty-call diagnosis (review: do NOT guess - classify). An empty answer is one of
           # several distinct failures; these counters keep them separate, never conflated.
           "empty_calls": 0,            # live calls whose `content` came back empty
           "empty_truncated": 0,        # content empty AND finish_reason == "length" (PROVES the
           #                              token-budget cause: reasoning consumed the whole budget)
           "empty_with_reasoning": 0,   # content empty but a reasoning field had text (adapter /
           #                              wrong-field bug, NOT a budget problem)
           "empty_silent": 0,           # content empty, no reasoning, finish_reason not "length"
           "by_finish_reason": {}}
    if not log.exists():
        return out
    g_cost = _cost_per_call("JONI_COST_PER_GRANITE_CALL", "0.0")   # OpenRouter prepaid by default
    d_cost = _cost_per_call("JONI_COST_PER_DEEPSEEK_CALL", "0.004")
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        out["llm_calls"] += 1
        provider = r.get("provider", "")
        served = r.get("served_model", "?")
        out["by_model"][served] = out["by_model"].get(served, 0) + 1
        replayed = bool(r.get("replayed"))
        out["cached_calls" if replayed else "live_calls"] += 1
        ts = r.get("ts") or ""
        if ts > out["last_call"]:
            out["last_call"] = ts
        is_deepseek = provider == "deepseek"
        if r.get("escalation_reason") and is_deepseek:
            out["deepseek_escalations"] += 1
        if "granite" in served.lower():
            out["granite_calls"] += 1
        if served.startswith("deepseek") and r.get("run_id", "").startswith("kevin"):
            out["kevin_calls"] += 1
        if not replayed:                                  # only live calls cost money
            out["est_cost_eur"] += d_cost if is_deepseek else (g_cost if provider else 0.0)
            fr = r.get("finish_reason", "") or "unknown"
            out["by_finish_reason"][fr] = out["by_finish_reason"].get(fr, 0) + 1
            if r.get("content_len", -1) == 0:             # an empty answer - classify why
                out["empty_calls"] += 1
                if r.get("finish_reason") == "length":
                    out["empty_truncated"] += 1
                elif r.get("reasoning_len", 0) > 0:
                    out["empty_with_reasoning"] += 1
                else:
                    out["empty_silent"] += 1
    out["est_cost_eur"] = round(out["est_cost_eur"], 4)
    return out
