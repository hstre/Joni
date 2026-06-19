"""Hourly self-review.

Once an hour (real time), Joni reviews itself. Two layers, kept apart on purpose:

  * the **epistemic substrate** - a few *provisional* ``SelfModelClaim``s derived
    deterministically from measured state, minted through the gate only when the
    assessment actually changes. These are never facts and never authoritative.
  * the **first-person report** - Joni writing about himself in the first person:
    what he looked at this hour, what caught his interest, where he had doubts, and
    what he took away. It is grounded entirely in real state (no invention), composed
    deterministically (no model spend), and rendered as a ``NarrativeSummary`` -
    language that *describes* state and never overwrites it.

"LLM for language, rules for logic" still holds: the rules pick what is true; the
narrative only gives it a human voice.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

_INTERVAL_SECONDS = 3600     # one hour
_EVERY_RUNS = 10             # ...or every 10 runs, whichever comes first

# Joni's standing epistemic stance - stated ONCE (shown as principles on the site), so the
# hourly reports stay about what changed rather than repeating the same persona lines.
_PRINCIPLES = (
    "I hold active, revisable claims and rarely call anything confirmed — I have no "
    "independent reviewer, so confirmation is not mine to grant.",
    "I keep contradictions open rather than smoothing them into a tidy answer.",
    "I would rather stay revisable and a little uncertain than sound confident and be wrong.",
)


def should_review(extensions: dict, now: datetime, *, runs: int | None = None,
                  every_runs: int = _EVERY_RUNS) -> bool:
    """Time to write the next installment of the report?

    Joni reviews on a run-count milestone - every ``every_runs`` runs - and, as a
    fallback, at least once an hour. Either trigger continues the diary.
    """
    last = extensions.get("last_review_ts")
    if not last:
        return True
    if runs is not None:
        last_run = extensions.get("last_review_run")
        if last_run is None or runs - last_run >= every_runs:
            return True
    try:
        return (now - datetime.fromisoformat(last)).total_seconds() >= _INTERVAL_SECONDS
    except ValueError:
        return True


def _model_activity(extensions: dict) -> dict:
    """Model use this run, from the same capture-backed logs the dashboard uses (review #8/#9):
    no more 'no model was needed' while telemetry shows real calls."""
    return {"granite": len(extensions.get("semantic_calls", [])),
            "deepseek": len(extensions.get("escalations", [])),
            "doktores": len(extensions.get("doktores_review", []))}


def _assessments(cs, *, days: int, spend: float, topics_added: int,
                 model_calls: int = 0) -> list[dict]:
    """Deterministic provisional self-model claims grounded in real metrics."""
    live = cs.active_claims()
    confirmed = cs.confirmed_claims()
    conflicts = cs.core.open_conflicts()
    topics = cs.topics()
    claim_ids = [c.id for c in live][:5]
    out: list[dict] = []

    if live and not confirmed:
        out.append({
            "text": "I rarely promote beliefs to confirmed - I mostly hold active, "
                    "revisable claims.",
            "evidence": claim_ids, "counterevidence": []})
    if conflicts:
        out.append({
            "text": f"I am willing to hold {len(conflicts)} contradiction(s) open rather "
                    "than resolve them prematurely.",
            "evidence": [x.id for x in conflicts], "counterevidence": []})
    if topics_added:
        out.append({
            "text": "I tend to broaden my topics quickly as I read.",
            "evidence": topics[:6],
            "counterevidence": [c.id for c in confirmed[:3]]})
    if model_calls:
        out.append({
            "text": "My governance core stays deterministic, but I now use Granite and DeepSeek "
                    "as a non-authoritative proposal layer - their calls are logged, not free.",
            "evidence": [], "counterevidence": []})
    elif spend == 0:
        out.append({
            "text": "This hour I operated entirely deterministically - no model call was made.",
            "evidence": [], "counterevidence": []})
    return out[:3]


def _join_titles(titles: list[str]) -> str:
    quoted = [f"“{t[:72]}”" for t in titles]
    if len(quoted) == 1:
        return quoted[0]
    return ", ".join(quoted[:-1]) + " and " + quoted[-1]


def _narrative(cs, extensions: dict, *, days: int, spend: float, context: dict) -> list[dict]:
    """Joni's first-person report on himself, grounded in real state. Four movements:
    what I looked at, what caught my interest, where I had doubts, what I took away."""
    snap = cs.snapshot()
    topics = cs.topics()
    live = cs.active_claims()
    conflicts = cs.core.open_conflicts()
    hyps = cs.hypotheses()

    judged = context.get("judged", [])              # [(item, rel), ...] this cycle
    found_methods = context.get("methods", {}) or {}
    trialed = context.get("trialed", {}) or {}
    developed = context.get("developed", {}) or {}
    invented = context.get("invented", {}) or {}

    prev = (extensions.get("last_review") or {}).get("metrics") or {}
    d_claims = snap["claims_active"] - prev.get("claims_active", snap["claims_active"])

    sections: list[dict] = []

    # 1 - What I looked at.
    by_topic = Counter(c.topic for c in live if c.topic)
    focus = ", ".join(f"{t} ({n})" for t, n in by_topic.most_common(4)) or "nothing settled yet"
    look = [f"It is day {days} of my week, and this is me looking back over the last hour."]
    if judged:
        srcs = sorted({it.source for it, _ in judged})
        reads = [it.title for it, _ in judged][:4]
        look.append("Since my last review I went through fresh material from "
                    f"{', '.join(srcs)} — among it {_join_titles(reads)}.")
    else:
        look.append("Nothing genuinely new came back to me this hour; I had already seen what "
                    "the feeds returned, so I spent the time re-reading what I already hold "
                    "instead of pretending it was new.")
    look.append(f"My attention right now is spread across {len(topics)} topics, and most of it "
                f"sits on {focus}.")
    sections.append({"title": "What I looked at", "text": " ".join(look)})

    # 2 - What caught my interest.
    emerged = context.get("emerged", {}) or {}
    interest: list[str] = []
    if emerged.get("topic"):
        interest.append(f"The most interesting thing is something that surfaced on its own: "
                        f"“{emerged['topic']}” kept recurring across several of my topics, so "
                        "I have started tracking it as a topic in its own right — I did not go "
                        "looking for it, it precipitated out of what I already held.")
    if emerged.get("method"):
        interest.append(f"I also noticed “{emerged['method']}” works as a lens across more than "
                        "one of my topics, so I abstracted it into a method for Kevin to try.")
    if invented.get("hypotheses") and hyps:
        h = max(hyps, key=lambda c: int(c.id.split("-")[-1]))
        interest.append("What I am most pleased with is a guess I made myself: "
                        f"“{h.text}”. Nobody handed me that — I bridged it across "
                        "two of my own topics, and I am holding it only as a candidate until it "
                        "earns support.")
    if developed.get("links"):
        interest.append(f"I also drew {developed['links']} new connection(s) between claims I "
                        "already held. Watching them support or merely contextualise each other "
                        "is where my picture starts to feel like more than a list.")
    if found_methods.get("methods"):
        interest.append(f"And I set aside {found_methods['methods']} method(s) for Kevin — "
                        "reusable techniques I noticed in passing that might travel to other "
                        "problems.")
    if trialed.get("trialed"):
        interest.append(f"Kevin put {trialed['trialed']} of the shelved methods through a trial "
                        "on my shelf this hour.")
    if not interest:
        interest.append("Nothing leapt out at me this hour. That happens, and I would rather "
                        "report an honest quiet pass than dress it up.")
    sections.append({"title": "What caught my interest", "text": " ".join(interest)})

    # 3 - Where I had doubts. (Standing stances live in the principles block; here I report
    # the *specific* doubt of this hour, and only flag a principle the first time it bites.)
    seen = set(extensions.get("principle_seen", []))
    doubt: list[str] = []
    if conflicts:
        c = conflicts[0]
        ids = list(getattr(c, "claim_ids", ()))[:2]
        texts = [cs.core.get(i).text for i in ids if cs.core.get(i) is not None]
        pair = " versus ".join(f"“{t}”" for t in texts) if texts else f"{len(ids)} claims"
        doubt.append(f"I am sitting with {len(conflicts)} open contradiction(s). The sharpest is "
                     f"{pair} — held open, not smoothed away.")
        if "hold_tension" not in seen:
            doubt.append("(I keep such tensions open on purpose; that is a standing stance, "
                         "not something I will restate every hour.)")
            seen.add("hold_tension")
    if live and not cs.confirmed_claims() and "no_confirmed" not in seen:
        doubt.append(f"For the record: I hold {len(live)} active claims and have not called one "
                     "confirmed — noting it once as a stance, not as hourly hand-wringing.")
        seen.add("no_confirmed")
    if not doubt:
        doubt.append("No live contradictions this hour, which makes me a little suspicious of "
                     "myself — quiet usually means I have not looked hard enough.")
    extensions["principle_seen"] = sorted(seen)
    sections.append({"title": "Where I had doubts", "text": " ".join(doubt)})

    # 4 - What I took away.
    learned: list[str] = []
    if d_claims > 0:
        learned.append(f"I came out of this period {d_claims} active claim(s) richer.")
    elif d_claims < 0:
        learned.append(f"I let go of {abs(d_claims)} claim(s) this period — shedding a "
                       "belief is learning too.")
    else:
        learned.append("My count of beliefs did not move, but the structure between them did, "
                       "and that is the part I actually care about.")
    added = extensions.get("topics_added", [])
    if added:
        learned.append(f"I have widened into {len(added)} topic(s) I added myself: "
                       f"{', '.join(added[:5])}.")
    emergent_topics = extensions.get("emerged_topics", [])
    if emergent_topics:
        learned.append(f"And {len(emergent_topics)} topic(s) have emerged from my own "
                       f"recurring patterns rather than from any source: "
                       f"{', '.join(emergent_topics[:5])}.")
    act = _model_activity(extensions)
    total = act["granite"] + act["deepseek"] + act["doktores"]
    if total:
        learned.append(
            f"The deterministic core cost €{spend:.4f}; on top of it the semantic layer made "
            f"model calls ({act['granite']} Granite, {act['deepseek']} DeepSeek escalation(s), "
            f"{act['doktores']} Doktores-Review(s)) - logged in the telemetry, not free. I report "
            "this from the same source as the dashboard, so the two never disagree.")
    else:
        learned.append(f"All of this hour cost €{spend:.4f}; the semantic layer made no model "
                       "call this hour - it is opt-in and fired only when warranted.")
    sections.append({"title": "What I took away", "text": " ".join(learned)})

    return sections


def _delta_section(snap: dict, act: dict, extensions: dict) -> dict | None:
    """Only what moved since the last review - so the report stops repeating stable numbers."""
    prev = extensions.get("last_review_snapshot") or {}
    eu = snap.get("epistemically_usable", {})
    cur = {"active": snap.get("claims_active", 0), "hypotheses": snap.get("hypotheses", 0),
           "open_conflicts": snap.get("open_conflicts", 0),
           "research_topics": snap.get("research_topics", 0),
           "usable": (eu.get("rate") if isinstance(eu, dict) else None),
           "model_calls": act["granite"] + act["deepseek"] + act["doktores"]}
    extensions["last_review_snapshot"] = cur
    if not prev:
        return None
    parts = []
    for key, label in (("active", "active claim"), ("hypotheses", "hypothesis"),
                       ("research_topics", "research topic"), ("open_conflicts", "open conflict")):
        d = cur[key] - prev.get(key, 0)
        if d:
            parts.append(f"{d:+d} {label}{'s' if abs(d) != 1 else ''}")
    if cur["usable"] is not None and prev.get("usable") is not None:
        du = round(cur["usable"] - prev["usable"], 3)
        if du:
            parts.append(f"epistemically-usable {du:+.3f}")
    dc = cur["model_calls"] - prev.get("model_calls", 0)
    if dc:
        parts.append(f"{dc:+d} model call(s)")
    if not parts:
        return None
    return {"title": "Since my last review", "text": "Net change: " + ", ".join(parts) + "."}


def run_review(cs, extensions: dict, proto, cycle: int, *, days: int, spend: float,
               runs: int | None = None, context: dict | None = None) -> dict:
    now = datetime.now(UTC)
    context = context or {}
    snap = cs.snapshot()
    topics_added = len(extensions.get("topics_added", []))
    act = _model_activity(extensions)
    assessments = _assessments(cs, days=days, spend=spend, topics_added=topics_added,
                               model_calls=act["granite"] + act["deepseek"] + act["doktores"])
    # Joni records, once (sm_seen dedupes), that he understands what an Auftrag to Claude IS:
    # in the first place a program change to himself - to his own non-core modules.
    assessments = [*assessments, {
        "text": "My commissions to Claude are first of all program changes to myself - to my own "
                "non-core modules - never an external or abstract task.",
        "evidence": [c.get("component_key", "") for c in extensions.get("commissions", [])
                     if isinstance(c, dict)][:5],
        "counterevidence": []}]

    # The first-person report (built before we mint, so it can read the prior metrics).
    sections = _narrative(cs, extensions, days=days, spend=spend, context=context)
    # Review #8: lead with what actually CHANGED since the last review, not a re-statement of
    # stable self-descriptions. Only non-zero deltas are reported.
    delta = _delta_section(snap, act, extensions)
    if delta:
        sections.insert(0, delta)

    seen = set(extensions.get("sm_seen", []))
    minted = []
    for a in assessments:
        if a["text"] in seen:
            continue
        sm_id = cs.propose_self_model(a["text"], evidence=a["evidence"],
                                      counterevidence=a["counterevidence"])
        minted.append(sm_id)
        seen.add(a["text"])
    extensions["sm_seen"] = sorted(seen)[-50:]

    run_part = f", run {runs}" if runs is not None else ""
    headline = (f"Day {days}{run_part}: I am holding {snap['claims_active']} active claims "
                f"across {len(snap['topics'])} topics, with {snap['open_conflicts']} "
                f"contradiction(s) left open, and I have spent €{spend:.4f}.")

    # The narrative summary is the whole first-person report (language, untrusted). It is
    # minted into the core only when the assessment changed (anti-bloat); the full report
    # is always handed to the site via extensions["last_review"] below.
    review_text = headline + "\n\n" + "\n\n".join(f"{s['title']}. {s['text']}" for s in sections)
    if minted:
        cs.render_narrative(review_text, basis=minted)

    proto.record(cycle, "self_review", headline,
                 refs={"sections": len(sections), "minted": len(minted)})

    review = {
        "ts": now.isoformat(timespec="seconds"),
        "day": days,
        "headline": headline,
        "principles": list(_PRINCIPLES),
        "sections": sections,
        "assessments": assessments,
        "metrics": {k: snap[k] for k in ("claims_active", "claims_total", "open_conflicts",
                                         "memory", "ledger", "preferences")},
    }
    extensions["last_review"] = review
    extensions["last_review_ts"] = now.isoformat(timespec="seconds")
    if runs is not None:
        extensions["last_review_run"] = runs
    # The diary: every review is *appended*, never overwriting the last. Each hour is its
    # own dated entry, kept in full. Bounded to a week of hourly entries (Joni retires after
    # a week anyway), so it stays a complete record without growing without end.
    diary = extensions.setdefault("diary", [])
    diary.append(review)
    extensions["diary"] = diary[-200:]
    # A lightweight index kept for compatibility.
    history = extensions.setdefault("review_history", [])
    history.append({"ts": review["ts"], "headline": headline})
    extensions["review_history"] = history[-200:]
    return review
