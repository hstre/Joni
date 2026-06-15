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

Joni convenes the panel **when he is genuinely unsure** (an open contradiction he holds) **or
when Kevin proposes something** - a new method/lens or an invented cross-topic hypothesis. On a
suggestion the panel assesses *whether it is a good idea, and why or why not* (under which
assumptions it is sound vs where it breaks), so Joni gets an explained recommendation - never a
decision.

The panel is **integrated like the Moltbook forum**: a *periodic, bounded round*, not an
every-cycle reaction. It convenes at most once per cadence window (``JONI_PANEL_EVERY``,
default ~daily), only when there is genuinely something to assess, each thing assessed once;
the weekly budget is the hard cap. Nothing to assess, or not yet due -> no panel, nothing spent.

Three voices: **Claude** and **ChatGPT** via OpenRouter, **DeepSeek** via the DeepSeek key.
Opt-in (``JONI_EXPERTS=1``) and budget-gated; otherwise a no-op.
"""
from __future__ import annotations

import os

import desi_layer9 as l9

_DEFAULT_COST_EUR = 0.15          # conservative flat charge per convened round (budget caps it)


def _panel_every() -> int:
    """Cadence: convene at most once per this many cycles. The panel is now a **periodic round,
    like the Moltbook forum** - a scheduled, bounded activity, not a reaction in every cycle.
    Env-dialled (``JONI_PANEL_EVERY``); default ~daily at the hourly relauncher cadence."""
    return max(1, int(os.getenv("JONI_PANEL_EVERY", "24")))

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
         # OpenRouter retired anthropic/claude-3.7-sonnet; the alias resolves to the latest
         # Sonnet, with a confirmed Opus slug as fallback so a slug change never drops the voice.
         "model": os.getenv("JONI_EXPERT_CLAUDE", "anthropic/claude-sonnet-latest"),
         "fallback": "anthropic/claude-opus-4.8"},
        {"name": "chatgpt", "role": os.getenv("JONI_EXPERT_GPT_ROLE", "adversarial"),
         "base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY",
         "model": os.getenv("JONI_EXPERT_GPT", "openai/gpt-4o")},
        {"name": "deepseek", "role": os.getenv("JONI_EXPERT_DEEPSEEK_ROLE", "consistency"),
         "base_url": "https://api.deepseek.com", "key_env": "DEEPSEEK_API_KEY",
         # deepseek-v4-pro per the API docs; deepseek-chat (v4-flash) is being deprecated.
         "model": os.getenv("JONI_EXPERT_DEEPSEEK", "deepseek-v4-pro")},
    ]


def _ask(expert: dict, system: str, user: str, *, temperature: float = 0.3) -> str | None:
    """One OpenAI-compatible call. The single network seam (tests monkeypatch this). Returns the
    text, or None on any error - a panel is best-effort; an unreachable voice simply abstains."""
    key = os.getenv(expert["key_env"])
    if not key:
        return None
    # try the configured model, then a fallback slug (so a retired model id never silently drops
    # the voice and leaves a two-member panel).
    models = [expert["model"]] + ([expert["fallback"]] if expert.get("fallback") else [])
    for model in models:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url=expert["base_url"], timeout=20)
            resp = client.chat.completions.create(
                model=model, temperature=temperature,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}])
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:  # noqa: BLE001 - best-effort; try the fallback, else abstain
            continue
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


def _uncertainty_point(cs, asked=()) -> tuple[str, str, str, str] | None:
    """Find a proposition Joni is genuinely UNSURE about - worth asking the panel.

    Uncertainty is an **open contradiction he is holding**: two claims he cannot both keep. A
    hard contradiction is preferred over a softer tension. Conflicts already assessed once
    (``asked``) are skipped, so the panel works through distinct uncertainties rather than
    re-asking the same one. If he holds no un-assessed open conflict, he is not unsure -
    ``None`` means no panel. (A fresh untested hypothesis is not 'unsure', just untested.)"""
    asked = set(asked)
    open_conf = [x for x in cs.core.open_conflicts() if x.conflict_status.value == "open"]
    # hardest first: a flat contradiction is a sharper 'unsure' than a soft tension
    open_conf.sort(key=lambda x: 0 if getattr(x, "severity", "") == "hard" else 1)
    for x in open_conf:
        key = f"conflict:{x.id}"
        if key in asked:
            continue
        texts, topic = [], "panel"
        for cid in list(x.claim_ids)[:2]:
            c = cs.core.get(cid)
            if c is not None:
                texts.append(f"({cid}) {c.text}")
                topic = c.topic or topic
        if len(texts) == 2:
            sev = "a hard contradiction" if getattr(x, "severity", "") == "hard" else "tension"
            q = (f"Joni holds two claims in {sev} and is unsure how to reconcile them. Assess "
                 "under which assumptions each is consistent, and where they truly conflict:\n"
                 f"- {texts[0]}\n- {texts[1]}")
            return key, q, f"topic: {topic}", topic
    return None


def _idnum(oid: str) -> int:
    try:
        return int(str(oid).split("-")[-1])
    except (ValueError, AttributeError):
        return 0


def _suggestion_point(cs, asked=()) -> tuple[str, str, str, str] | None:
    """A fresh creative suggestion worth assessing - **when Kevin proposes something**: a newly
    proposed method/lens, else an invented cross-topic hypothesis. The panel is asked the plain
    question Joni needs answered: *is this a good idea, and why or why not?* Already-assessed
    suggestions (``asked``) are skipped. Returns (key, question, context, topic) or None."""
    asked = set(asked)
    ask = ("Beurteilt, ob das eine **gute Idee** ist: unter welchen Annahmen ist es tragfaehig "
           "(was dafuer spricht) und wo bricht es (was dagegen spricht)? Keine Entscheidung - "
           "eine begruendete Einschaetzung.")
    # 1. a proposed method (a transferable lens Kevin would trial)
    for m in sorted(cs.core.all(l9.ObjectType.METHOD), key=lambda o: _idnum(o.id), reverse=True):
        key = f"method:{m.id}"
        if key in asked:
            continue
        name = getattr(m, "name", m.id)
        summ = getattr(m, "summary", "") or ""
        applic = list(getattr(m, "applicable_to", ()) or ())
        topic = applic[0] if applic else "panel"
        q = f"Kevin/Joni schlaegt eine neue Methode (Linse) vor: \"{name}\" - {summ}\n\n{ask}"
        return key, q, f"kind: method suggestion; applicable to: {', '.join(applic)}", topic
    # 2. an invented cross-topic hypothesis (a creative leap; its topic carries a '+')
    for h in sorted(cs.hypotheses(), key=lambda c: _idnum(c.id), reverse=True):
        key = f"hyp:{h.id}"
        if key in asked or "+" not in (h.topic or ""):
            continue
        q = f"Kevin/Joni schlaegt eine Hypothese vor: \"{h.text}\"\n\n{ask}"
        return key, q, f"topic: {h.topic}", (h.topic or "panel")
    return None


def maybe_convene(cs, extensions: dict, proto, budget, cycle: int, *,
                  runs_per_week: int = 672) -> dict:
    """Convene the panel **when Joni is unsure** (an open contradiction he holds) **or when Kevin
    proposes something** (a method/lens or invented hypothesis - assessed as a good/bad idea with
    reasons) and take its assessments in as SOURCES. Opt-in (JONI_EXPERTS=1), cooldown-spaced,
    within budget. Joni decides - never the panel. Nothing to assess -> no panel, nothing spent."""
    out = {"convened": False, "question": None, "experts": [], "calls": 0}
    if not enabled():
        return out
    asked = set(extensions.get("panel_asked", []))
    # convene on a held uncertainty first, else on a fresh Kevin suggestion to assess
    dp = _uncertainty_point(cs, asked) or _suggestion_point(cs, asked)
    if dp is None:
        return out                              # nothing unsure and nothing new to assess
    key, question, context, topic = dp
    # The panel is a periodic round (like the Moltbook forum), not an every-cycle reaction: it
    # convenes at most once per cadence window, even if an uncertainty/suggestion is present.
    last = extensions.get("panel_last_cycle")
    if last is not None and cycle - last < _panel_every():
        return out
    # A panel is a deliberate spend - gate on weekly room. Each uncertainty is convened at most
    # once (panel_asked), which bounds total cost.
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
    extensions["panel_last_cycle"] = cycle      # cooldown anchor for the next uncertainty
    extensions["panel_last"] = {"question": question, "roles": record["roles"],
                                "phase3": record["phase3"], "cycle": cycle}
    proto.record(cycle, "panel",
                 f"Alexandria panel on {key}: {', '.join(record['experts'])} assessed "
                 f"(cross-reconstructed, {record['calls']} call(s)) - taken as sources, dissent "
                 "preserved, Joni decides")
    out.update({"convened": True, "question": question, "experts": record["experts"],
                "calls": record["calls"]})
    return out
