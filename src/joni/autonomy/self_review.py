"""Hourly self-review.

Once an hour (real time), Joni reviews itself: it reads its own measured operational
state and derives a few **provisional** self-model claims about its trajectory - through
the gate, as `SelfModelClaim`s, never as facts. It then composes a human-readable review
line (a `NarrativeSummary`) and reports it on the website. The rules are deterministic;
no model decides what Joni "is".

To keep the authoritative core from bloating, a self-model claim / narrative is only
minted when the assessment *changes*; the protocol entry and the website card update
every hour regardless.
"""

from __future__ import annotations

from datetime import UTC, datetime

_INTERVAL_SECONDS = 3600     # one hour


def should_review(extensions: dict, now: datetime) -> bool:
    last = extensions.get("last_review_ts")
    if not last:
        return True
    try:
        return (now - datetime.fromisoformat(last)).total_seconds() >= _INTERVAL_SECONDS
    except ValueError:
        return True


def _assessments(cs, *, days: int, spend: float, topics_added: int) -> list[dict]:
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
    if spend == 0:
        out.append({
            "text": "I operate almost entirely deterministically, at no model cost.",
            "evidence": [], "counterevidence": []})
    return out[:3]


def run_review(cs, extensions: dict, proto, cycle: int, *, days: int, spend: float) -> dict:
    now = datetime.now(UTC)
    snap = cs.snapshot()
    topics_added = len(extensions.get("topics_added", []))
    assessments = _assessments(cs, days=days, spend=spend, topics_added=topics_added)

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

    headline = (f"Reviewing myself at day {days}: {snap['claims_active']} active claims "
                f"over {len(snap['topics'])} topics, {snap['open_conflicts']} open "
                f"contradiction(s), €{spend:.4f} spent.")
    review_line = headline + " " + " ".join(a["text"] for a in assessments)
    if minted:
        cs.render_narrative(review_line, basis=minted)

    proto.record(cycle, "self_review", headline,
                 refs={"assessments": len(assessments), "minted": len(minted)})

    review = {
        "ts": now.isoformat(timespec="seconds"),
        "day": days,
        "headline": headline,
        "assessments": assessments,
        "metrics": {k: snap[k] for k in ("claims_active", "claims_total", "open_conflicts",
                                         "memory", "ledger", "preferences")},
    }
    extensions["last_review"] = review
    extensions["last_review_ts"] = now.isoformat(timespec="seconds")
    history = extensions.setdefault("review_history", [])
    history.append({"ts": review["ts"], "headline": headline})
    extensions["review_history"] = history[-30:]
    return review
