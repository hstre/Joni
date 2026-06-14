"""An Alexandria-style assessment panel - assessors, not authorities. They advise; Joni decides.

Built to the Alexandria Protocol (Hanns-Steffen Rentschler, v2.2), Sections IV-V:

  * **IV - Assessor, not Authority.** No single AI judges; there is no deciding instance and no
    aggregated "AI opinion". Models deliver formal judgment contributions, not truth verdicts -
    they answer "under which assumptions is this consistent?", never "what is true?".
  * **IV.3/IV.4 - functional diversity enforced.** The models take strictly separated roles with
    separate prompt sets: an **assessor** (category purity / consistency / explicit-vs-implicit
    assumptions), an **adversarial** model (alternative derivations, counter-assumptions, hidden
    contradictions), and a **consistency** model (can divergence resolve via precision /
    assumption-separation / decomposition).
  * **V - jury, not aggregation.** No averaging, no majority vote. Phase 1: parallel, isolated
    assessment. Phase 3: **cross-reconstruction** ("ueber Kreuz") - each model must trace the
    others' divergent judgements and may maintain a disagreement only by naming which assumption,
    category, or rule differs; unexplained dissent is inadmissible. The goal is *explained
    difference*, not agreement.

The panel's contributions enter Joni's net as **SOURCES** (candidate authority, never the
privileged HUMAN origin, never auto-confirmed). Marked dissent is preserved - when an assessment
contradicts something Joni holds, a conflict opens and is held open, never aggregated away. Joni
alone decides.

Three voices: **Claude** and **ChatGPT** via OpenRouter, **DeepSeek** via the DeepSeek key.
Opt-in (``JONI_EXPERTS=1``) and budget-gated; otherwise a no-op.
"""
from __future__ import annotations

import os

_EVERY = 20                       # at most one panel every N cycles
_DEFAULT_COST_EUR = 0.15          # conservative flat charge per convened round (budget caps it)

# Functional roles (Alexandria IV.3) - distinct rule sets, not interchangeable opinions.
_ROLE_RULES = {
    "assessor": ("Check formal criteria: category purity, logical consistency, and which "
                 "assumptions are explicit versus implicit. State under which assumptions the "
                 "proposition is consistent. Do not judge whether it is true."),
    "adversarial": ("Deliberately seek alternative derivations, counter-assumptions, and hidden "
                    "contradictions. Try to break the proposition on formal grounds. Do not judge "
                    "whether it is true."),
    "consistency": ("Reconstruct the derivation path and test whether apparent contradictions "
                    "resolve through precision, assumption-separation, or decomposition. Do not "
                    "judge whether it is true."),
}
_BASE = ("You sit on Joni's Alexandria assessment panel. Alexandria binds you: you are an "
         "ASSESSOR, NOT AN AUTHORITY. You never decide and never declare truth - Joni alone "
         "decides. You contribute a formal judgement only. Your role on this panel: ")


def enabled() -> bool:
    return os.getenv("JONI_EXPERTS") == "1"


def _experts() -> list[dict]:
    """The panel. Model ids and roles are env-overridable so you can pin exact versions
    (DeepSeek 'pro v4', the latest Claude/GPT) and reassign roles without code changes."""
    return [
        {"name": "claude", "role": os.getenv("JONI_EXPERT_CLAUDE_ROLE", "assessor"),
         "base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY",
         "model": os.getenv("JONI_EXPERT_CLAUDE", "anthropic/claude-3.7-sonnet")},
        {"name": "chatgpt", "role": os.getenv("JONI_EXPERT_GPT_ROLE", "adversarial"),
         "base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY",
         "model": os.getenv("JONI_EXPERT_GPT", "openai/gpt-4o")},
        {"name": "deepseek", "role": os.getenv("JONI_EXPERT_DEEPSEEK_ROLE", "consistency"),
         "base_url": "https://api.deepseek.com", "key_env": "DEEPSEEK_API_KEY",
         "model": os.getenv("JONI_EXPERT_DEEPSEEK", "deepseek-chat")},
    ]


def _ask(expert: dict, system: str, user: str, *, temperature: float = 0.3) -> str | None:
    """One OpenAI-compatible call. The single network seam (tests monkeypatch this). Returns the
    text, or None on any error - a panel is best-effort; an unreachable voice simply abstains."""
    key = os.getenv(expert["key_env"])
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=expert["base_url"], timeout=45)
        resp = client.chat.completions.create(
            model=expert["model"], temperature=temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return (resp.choices[0].message.content or "").strip() or None
    except Exception:  # noqa: BLE001 - best-effort; an unreachable advisor abstains
        return None


def convene(question: str, context: str = "", *, max_words: int = 170) -> dict | None:
    """Run the Alexandria cross-assessment cycle on one proposition. Returns the panel record, or
    None if fewer than two assessors could answer. Pure apart from the ``_ask`` calls."""
    panel = [e for e in _experts() if os.getenv(e["key_env"])]
    if len(panel) < 2:
        return None
    q = question.strip()
    ctx = f"\n\nClaim graph / context Joni has:\n{context.strip()}" if context.strip() else ""
    brief = (f"Proposition to assess (do not decide it - assess its formal admissibility):\n{q}"
             f"{ctx}\n\nBe concrete and concise (<= {max_words} words). No preamble.")

    # Phase 1 (V.4): parallel, isolated assessment - no exchange, no coordination.
    phase1: dict[str, str] = {}
    for e in panel:
        sys_p = f"{_BASE}{e['role']}. {_ROLE_RULES.get(e['role'], '')}"
        a = _ask(e, sys_p, brief)
        if a:
            phase1[e["name"]] = a
    if len(phase1) < 2:
        return None

    # Phase 3 (V.6): cross-reconstruction - trace the others; dissent only with a named reason.
    phase3: dict[str, str] = {}
    for e in panel:
        if e["name"] not in phase1:
            continue
        others = "\n\n".join(f"[{n} · {dict((x['name'], x['role']) for x in panel)[n]}] {t}"
                             for n, t in phase1.items() if n != e["name"])
        sys_x = (f"{_BASE}{e['role']}. Cross-reconstruction (Alexandria V.6): trace each other "
                 "assessor's divergent judgement. You may keep a disagreement ONLY by naming which "
                 "assumption, category, or rule differs - unexplained dissent is inadmissible. "
                 "Then give your reconciled, or explicitly-justified-dissent, assessment. Still no "
                 "truth verdict, still no decision (Joni decides). "
                 f"Concise (<= {max_words} words).")
        a = _ask(e, sys_x, f"{brief}\n\nOther assessors' phase-1 judgements:\n{others}")
        if a:
            phase3[e["name"]] = a

    return {"question": q, "roles": {e["name"]: e["role"] for e in panel if e["name"] in phase1},
            "phase1": phase1, "phase3": phase3,
            "experts": [n for n in phase1], "calls": len(phase1) + len(phase3)}


def _decision_point(cs) -> tuple[str, str, str, str] | None:
    """Find one hard, open proposition worth a panel: a live hard contradiction, else the most
    recent unsupported hypothesis. Returns (key, question, context, topic) or None."""
    for x in cs.core.open_conflicts():
        if getattr(x, "severity", "") == "hard" and x.conflict_status.value == "open":
            texts, topic = [], "panel"
            for cid in list(x.claim_ids)[:2]:
                c = cs.core.get(cid)
                if c is not None:
                    texts.append(f"({cid}) {c.text}")
                    topic = c.topic or topic
            if len(texts) == 2:
                q = ("Joni holds two claims he cannot both keep. Assess under which assumptions "
                     "each is consistent, and where they truly conflict:\n"
                     f"- {texts[0]}\n- {texts[1]}")
                return f"conflict:{x.id}", q, f"topic: {topic}", topic
    from .homeostasis import _supports_on
    for h in sorted(cs.hypotheses(), key=lambda c: int(c.id.split("-")[-1]), reverse=True):
        if _supports_on(cs, h.id) == 0:
            q = (f"Joni's own hypothesis, so far unsupported: \"{h.text}\". Assess under which "
                 "assumptions it is consistent, and where it is most likely to break.")
            derived = ", ".join(getattr(h, "derived_from", ()) or ())
            ctx = f"topic: {h.topic}; derived from: {derived}"
            return f"hyp:{h.id}", q, ctx, (h.topic or "panel")
    return None


def maybe_convene(cs, extensions: dict, proto, budget, cycle: int, *,
                  runs_per_week: int = 672) -> dict:
    """Occasionally convene the panel on a decision point and take its assessments in as SOURCES.
    Opt-in (JONI_EXPERTS=1), rate-limited, within budget. Joni decides - never the panel."""
    out = {"convened": False, "question": None, "experts": [], "calls": 0}
    if not enabled() or _EVERY <= 0 or cycle % _EVERY != 0:
        return out
    dp = _decision_point(cs)
    if dp is None:
        return out
    key, question, context, topic = dp
    asked = set(extensions.get("panel_asked", []))
    if key in asked:
        return out
    # A panel is a rare, deliberate spend - gate on weekly room, not the per-run pace. Each
    # decision point is convened at most once (panel_asked), which bounds total cost.
    cost = float(os.getenv("JONI_EXPERT_COST_EUR", _DEFAULT_COST_EUR))
    if budget.remaining() < cost:
        proto.record(cycle, "panel", "panel deferred - weekly budget has no room")
        return out

    record = convene(question, context=context)
    asked.add(key)
    extensions["panel_asked"] = sorted(asked)[-200:]
    if record is None:
        proto.record(cycle, "panel", "panel could not convene (fewer than two reachable assessors)")
        return out

    budget.charge(cost)
    # Take each assessor's cross-reconstructed judgement in as a SOURCE - candidate authority,
    # never confirmed; marked dissent is preserved (a contradiction opens a conflict, held open).
    for name in record["experts"]:
        text = record["phase3"].get(name) or record["phase1"].get(name)
        if text:
            role = record["roles"].get(name, "assessor")
            cs.hear(f"[Alexandria-Bewertung · {role} · keine Entscheidung] {text}", topic,
                    handle=f"expert:{name}", platform="panel")
    record["cycle"] = cycle
    extensions["panel_last"] = {"question": question, "roles": record["roles"],
                                "phase3": record["phase3"], "cycle": cycle}
    proto.record(cycle, "panel",
                 f"Alexandria panel on {key}: {', '.join(record['experts'])} assessed "
                 f"(cross-reconstructed, {record['calls']} call(s)) - taken as sources, dissent "
                 "preserved, Joni decides")
    out.update({"convened": True, "question": question, "experts": record["experts"],
                "calls": record["calls"]})
    return out
