"""Der Gesprächskreis - a small, sequential circle of LLMs, in place of the public forum.

Developmental staging (the operator's insight): a mind becomes mündig through interaction,
guidance, and access to history - but at the right time. The open forum (anonymous strangers,
unfiltered) is too early. This is the controlled peer circle that comes first: three or four
models in a RELAY - each sees the question and every prior answer, and the last seat is asked
to CHALLENGE the others (Popper: conjecture and refutation; the Anti-Delphi Falsifier role).

Why this is not naive multi-model voting:
  * The answers are CORRELATED by construction - answer 2 saw answer 1 - so they must never
    count as independent corroboration (the Delphi error Alexandria forbids). All answers of
    one round therefore share ONE source family: a single deliberation is one witness with
    internal structure, not N witnesses. Provenance carries the round id first (the shared
    family the promotion logic sees) and the model id second (per-model audit).
  * Each answer still enters as a plain SOURCE (candidate authority, never HUMAN), through the
    same gate as any forum voice: judged, SPL-normalised, revenant-guarded, conflict-checked.
  * Disagreement WITHIN the circle is kept: distinct answers can contradict and open a conflict
    Joni holds - that is the whole point of the Falsifier seat.

Opt-in (``JONI_COUNCIL=1``), cadence-spaced (``JONI_COUNCIL_EVERY``), budget-metered. Models are
a configurable list of cheap OpenAI-compatible slugs (``JONI_COUNCIL_MODELS``) - they need not be
high-end to teach a young mind to hold a conversation.
"""

from __future__ import annotations

import os

from . import experts, humans

_DEFAULT_MODELS = (
    "meta-llama/llama-3.1-8b-instruct",
    "qwen/qwen-2.5-7b-instruct",
    "google/gemma-2-9b-it",
    "mistralai/mistral-7b-instruct",
)

_BUILDER = (
    "You are one voice in a small circle thinking together about a question. Read the question "
    "and every earlier voice, then ADD something the others have not yet said - a distinction, a "
    "mechanism, a piece of evidence, a caveat. One core claim, concise (<= 60 words), no preamble. "
    "You are a source, not an authority: you never decide, you contribute."
)
_FALSIFIER = (
    "You are the last voice in a small circle. Your job is Popper's: CHALLENGE the earlier voices. "
    "Name the weakest claim above and say precisely why it might be wrong, unsupported, or "
    "ambiguous - or, if they are all sound, name the strongest remaining objection an expert would "
    "still raise. One sharp point, concise (<= 60 words), no preamble. Disagreement with a named "
    "reason is the contribution; bland agreement is not."
)


def enabled() -> bool:
    return os.getenv("JONI_COUNCIL", "0") == "1"


def _models() -> list[str]:
    raw = os.getenv("JONI_COUNCIL_MODELS", "")
    got = tuple(m.strip() for m in raw.split(",") if m.strip()) if raw else _DEFAULT_MODELS
    return list(got[: max(2, int(os.getenv("JONI_COUNCIL_SEATS", "4")))])


def _every() -> int:
    return max(1, int(os.getenv("JONI_COUNCIL_EVERY", "6")))


def _cost_per_call() -> float:
    return float(os.getenv("JONI_COST_PER_COUNCIL_CALL", "0.0006"))


def _topic_of(cs, need_key: str) -> str:
    if need_key.startswith("topic:"):
        return need_key[len("topic:"):]
    obj = cs.core.get(need_key)
    return (getattr(obj, "topic", "") or "unsorted") if obj is not None else "unsorted"


def converse(cs, extensions: dict, proto, cycle: int = 0, *, budget=None,
             runs_per_week: int = 0, ask=None) -> dict:
    """One round of the circle, if it is this cycle's turn. Returns what was heard.

    ``ask(model, system, user) -> str | None`` is injectable (tests pass a fake); it defaults to
    the real OpenRouter call. No-op when disabled, off-cadence, out of budget, or with nothing
    worth asking."""
    out = {"heard": 0, "conflicts": 0, "models": 0, "topic": None}
    if not enabled():
        return out
    last = int(extensions.get("council_last_cycle", -10**9))
    if cycle - last < _every():
        return out
    if budget is not None and getattr(budget, "spent_eur", 0.0) >= getattr(budget, "cap_eur",
                                                                           float("inf")):
        return out
    ask = ask or experts.ask_model
    asked = set(extensions.get("council_asked", []))
    need = humans._open_need(cs, asked, tested=humans._tested_set(extensions))
    if need is None:
        return out
    need_key, question = need
    topic = _topic_of(cs, need_key)
    models = _models()
    out["topic"] = topic

    transcript: list[tuple[str, str]] = []   # (model, answer)
    for i, model in enumerate(models):
        if budget is not None and getattr(budget, "spent_eur", 0.0) >= getattr(
                budget, "cap_eur", float("inf")):
            break
        is_last = i == len(models) - 1 and len(models) >= 3
        system = _FALSIFIER if is_last else _BUILDER
        prior = "\n\n".join(f"[Stimme {j + 1} · {m}] {a}" for j, (m, a) in enumerate(transcript))
        user = (f"Question the circle is thinking about:\n{question}"
                + (f"\n\nEarlier voices in this round:\n{prior}" if prior else ""))
        answer = ask(model, system, user)
        if budget is not None:
            budget.charge(_cost_per_call())
        out["models"] += 1
        if not answer:
            continue
        transcript.append((model, answer[:500]))

    if not transcript:
        return out

    # All answers of THIS round share one source family (platform:handle) so the deliberation
    # counts as one correlated witness, never N independent ones; the model id rides along as
    # provenance for the audit trail. Entered as plain SOURCEs through the normal gate.
    handle = f"r{cycle}"
    for model, answer in transcript:
        cid = cs.hear(answer, topic, handle=handle, platform="council", origin=model)
        out["heard"] += 1
        proto.record(cycle, "heard",
                     f"Gesprächskreis · {model} - heard as a source ({cid}), not an authority")
    opened = cs.detect_and_open_conflicts()
    out["conflicts"] = len(opened)

    asked.add(need_key)
    extensions["council_asked"] = sorted(asked)[-500:]
    extensions["council_last_cycle"] = cycle
    proto.record(cycle, "note",
                 f"Gesprächskreis zu '{topic}': {out['heard']} Stimme(n) über {out['models']} "
                 f"Modell(e), letzte im Falsifikator-Sitz · {out['conflicts']} neue(r) Widerspruch "
                 "im Kreis · eine Quellfamilie (korreliert, nicht unabhängig)")
    return out
