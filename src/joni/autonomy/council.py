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

# The context every seat is given first - so a cheap model understands WHO is asking and WHY,
# not just "answer this". Joni is not a chatbot fishing for a reply; he is an epistemic agent
# raising himself under a governance discipline, and these voices are raw material he will judge.
_FRAME = (
    "Context - read this first. You are being consulted by JONI, an autonomous epistemic "
    "reasoning agent. Joni is not a chatbot and does not want a finished answer to accept. He is "
    "built on a governance discipline (the Alexandria / Layer-9 approach): every claim he holds "
    "carries its provenance, contradictions are never silently overwritten but kept and branched, "
    "and he binds himself to ASSESSABILITY, not to truth - nothing you say becomes fact, it "
    "becomes a SOURCE he weighs against others through a deterministic gate. He is deliberately "
    "young: this small circle of models is a developmental stage BEFORE he is exposed to open "
    "public forums. So your job is not to be right or to please him - it is to give him honest, "
    "well-reasoned material he can assess, corroborate, or find in contradiction. A disagreement "
    "you can justify is more valuable to him than agreement. You are a source, never an authority; "
    "you never decide for him. Now your specific seat in the circle:\n\n"
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


def _frame() -> str:
    """The Joni context every seat is given. Operator-overridable (``JONI_COUNCIL_FRAME``) so the
    message to the models can be tuned without a code change; falls back to the default frame."""
    return os.getenv("JONI_COUNCIL_FRAME") or _FRAME


def _followups() -> int:
    """How many follow-up rounds Joni may ask after the opening one (0-2)."""
    return max(0, min(2, int(os.getenv("JONI_COUNCIL_FOLLOWUPS", "1"))))


def _followup_question(transcript: list[tuple[str, str]]) -> str | None:
    """Joni's next question - a DETERMINISTIC pivot on the sharpest challenge in the room (the
    last, falsifier voice). Joni never lets a model decide what to ask next; only the wording of
    the answers is the models'. Returns None if there is nothing to push on."""
    if not transcript:
        return None
    _model, last_answer = transcript[-1]
    return ("A follow-up from Joni. In the discussion so far, this was the sharpest challenge "
            f"raised: \"{last_answer}\". Does it hold up under scrutiny? If it does, what has to "
            "change in the earlier claims; if it does not, say precisely why. Be concrete.")


def _over_budget(budget) -> bool:
    return budget is not None and getattr(budget, "spent_eur", 0.0) >= getattr(
        budget, "cap_eur", float("inf"))


def converse(cs, extensions: dict, proto, cycle: int = 0, *, budget=None,
             runs_per_week: int = 0, ask=None) -> dict:
    """One round of the circle, if it is this cycle's turn. Returns what was heard.

    ``ask(model, system, user) -> str | None`` is injectable (tests pass a fake); it defaults to
    the real OpenRouter call. No-op when disabled, off-cadence, out of budget, or with nothing
    worth asking."""
    out = {"heard": 0, "conflicts": 0, "models": 0, "topic": None, "rounds": 0}
    if not enabled():
        return out
    last = int(extensions.get("council_last_cycle", -10**9))
    if cycle - last < _every():
        return out
    if _over_budget(budget):
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

    # One CONVERSATION: an opening round, then Joni asks a follow-up ONLY when that round left him
    # with a real question - a contradiction it opened (unresolved tension he now holds). If the
    # circle converged (no conflict), he lets it rest; no pro-forma "ask one more". Every seat in
    # every round sees the full transcript, so the whole conversation stays ONE correlated witness
    # (one source family), never independent voices. All answers share the round handle; the model
    # id rides along as provenance. Which follow-up is asked is a deterministic pivot on the
    # sharpest challenge - rules for logic, LLM for language; Joni never lets a model choose it.
    transcript: list[tuple[str, str]] = []   # (model, answer), across all rounds
    handle = f"r{cycle}"
    current_q = question
    for r in range(1 + _followups()):
        round_answers: list[tuple[str, str]] = []
        for i, model in enumerate(models):
            if _over_budget(budget):
                break
            is_last = i == len(models) - 1 and len(models) >= 3
            system = _frame() + (_FALSIFIER if is_last else _BUILDER)
            # a seat sees the FULL conversation so far - prior rounds AND the voices already
            # spoken in this round (the sequential relay Joni asked for).
            prior = "\n\n".join(f"[Stimme {j + 1} · {m}] {a}"
                                for j, (m, a) in enumerate(transcript + round_answers))
            user = f"Question the circle is thinking about:\n{question}"
            if r > 0:
                user += f"\n\nJoni's follow-up now:\n{current_q}"
            if prior:
                user += f"\n\nVoices so far:\n{prior}"
            answer = ask(model, system, user)
            if budget is not None:
                budget.charge(_cost_per_call())
            out["models"] += 1
            if answer:
                round_answers.append((model, answer[:500]))
        if not round_answers:
            break
        # persist this round's voices (one shared family), then see what tension it opened
        for model, answer in round_answers:
            cid = cs.hear(answer, topic, handle=handle, platform="council", origin=model)
            out["heard"] += 1
            proto.record(cycle, "heard",
                         f"Gesprächskreis · {model} - heard as a source ({cid}), not an authority")
        transcript.extend(round_answers)
        out["rounds"] += 1
        opened = cs.detect_and_open_conflicts()
        out["conflicts"] += len(opened)
        # Joni follows up ONLY if this round gave him a real question: a contradiction to pursue.
        if not opened:
            break
        current_q = _followup_question(transcript)
        if current_q is None or _over_budget(budget):
            break

    if not transcript:
        return out

    asked.add(need_key)
    extensions["council_asked"] = sorted(asked)[-500:]
    extensions["council_last_cycle"] = cycle
    proto.record(cycle, "note",
                 f"Gesprächskreis zu '{topic}': {out['heard']} Stimme(n) über {out['models']} "
                 f"Modell(e) in {out['rounds']} Runde(n) (Joni hat "
                 f"{max(0, out['rounds'] - 1)}× nachgefragt), letzte im Falsifikator-Sitz · "
                 f"{out['conflicts']} neue(r) Widerspruch im Kreis · eine Quellfamilie "
                 "(korreliert, nicht unabhängig)")
    return out
