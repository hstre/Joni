"""Joni may talk to people - and must not bow to them.

Permission: Joni may interact with humans and register on forums (Hugging Face, Hacker News,
Reddit, LessWrong, ...). Stance, enforced mechanically: **a person is a source like any other.**
Polite in tone, but held to exactly the same epistemic standard as a paper or a web post -
measured, open to contradiction, never auto-confirmed, and never granted authority because
"a person said so".

How the strictness is real (not just a slogan):

  * **Inbound** - a forum reply enters through ``cs.hear``, which records it as a SOURCE
    (``OriginType.SOURCE``), *never* ``OriginType.HUMAN``. That matters: the protected core
    privileges ``HUMAN`` (it may confirm claims, resolve conflicts, touch the control plane)
    and reserves it for the trusted operator. A stranger on a forum is generative-only: an
    active claim whose authority stays ``candidate`` until it earns independent corroboration,
    and which opens a *conflict* - held open, not decided in the human's favour - when it
    contradicts something Joni holds. Identical treatment to any other source.

  * **Outbound** - Joni drafts polite questions/posts (to get critique or evidence) into an
    outbox. Actually posting is an outward, public, irreversible act, so it is gated: off
    unless the operator opts a platform in *and* supplies credentials (``forum_live()``).
    Until then drafts queue for a human to post, and replies return through the inbox - and
    are held just as strictly.

Deterministic throughout: which need becomes a question is a fixed rule; a model may later
phrase the outer voice, but it never decides what Joni believes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .homeostasis import _supports_on

# The standing stance, shown on the page so the rule is visible, not buried in code.
STANCE = ("Menschen sind eine Quelle, keine Autorität: höflich im Ton, aber genau so streng "
          "geprüft wie jede andere Quelle - aufgenommen als Kandidat, widerlegbar, nie allein "
          "deshalb geglaubt, weil ein Mensch es gesagt hat.")


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def _fingerprint(platform: str, handle: str, text: str) -> str:
    return hashlib.sha256(f"{platform}|{handle}|{text}".encode()).hexdigest()[:16]


def _topic_for(cs, text: str) -> str:
    """Attach a forum utterance to the topic it most overlaps with, else a generic bucket."""
    words = {w.strip(".,;:!?'\"()").lower() for w in text.split() if len(w) > 3}
    best, score = "forum", 0
    for topic in cs.topics():
        overlap = len(words & {w.lower() for w in topic.split()}
                      | (words & {topic.lower()}))
        if overlap > score:
            best, score = topic, overlap
    return best


def ingest_inbox(cs, extensions: dict, proto, cycle: int, inbox_path: Path) -> dict:
    """Take each new human/forum reply in as a SOURCE and run the normal conflict check.

    Returns what was heard and how it was treated - including any contradiction it opened
    (which is *not* resolved in the human's favour)."""
    inbox = _load(inbox_path, [])
    if not isinstance(inbox, list):
        return {"heard": 0, "conflicts": 0}
    seen = set(extensions.setdefault("forum_inbox_seen", []))
    log = extensions.setdefault("forum_heard", [])
    heard = 0
    before = len(cs.core.open_conflicts())

    for msg in inbox:
        if not isinstance(msg, dict):
            continue
        text = str(msg.get("text", "")).strip()
        if not text:
            continue
        platform = str(msg.get("platform", "forum"))
        handle = str(msg.get("handle", "anon"))
        fp = _fingerprint(platform, handle, text)
        if fp in seen:
            continue
        topic = str(msg.get("topic") or _topic_for(cs, text))
        cid = cs.hear(text, topic, handle=handle, platform=platform)
        seen.add(fp)
        heard += 1
        log.append({"cycle": cycle, "platform": platform, "handle": handle,
                    "topic": topic, "claim": cid, "text": text[:200],
                    "treated_as": "source (candidate authority) - not an authority"})
        proto.record(cycle, "heard",
                     f"{platform}:{handle} - heard as a source ({cid}), not an authority")

    opened = cs.detect_and_open_conflicts() if heard else []
    for conflict_id in opened:
        proto.record(cycle, "conflict_open",
                     f"{conflict_id} - a human input contradicts a held claim; held open, "
                     "not decided in the human's favour")

    extensions["forum_inbox_seen"] = sorted(seen)[-3000:]
    extensions["forum_heard"] = log[-200:]
    after = len(cs.core.open_conflicts())
    return {"heard": heard, "conflicts": max(0, after - before)}


def _open_need(cs, extensions: dict) -> tuple[str, str] | None:
    """Pick one thing worth asking a forum about: a hypothesis Joni cannot corroborate, or a
    topic he works on but has no evidence for. Returns (need_key, question) or None."""
    asked = set(extensions.get("forum_asked", []))

    # 1. an unsupported hypothesis - ask for evidence or a counter-argument.
    for h in sorted(cs.hypotheses(), key=lambda c: int(c.id.split("-")[-1]), reverse=True):
        if _supports_on(cs, h.id) == 0 and h.id not in asked:
            q = (f"Ich pruefe gerade eine eigene Hypothese und wuerde mich ueber Gegenargumente "
                 f"oder Belege freuen (ich nehme beides gleich ernst): \"{h.text}\" - "
                 "wo koennte das brechen?")
            return h.id, q

    # 2. a topic with claims but no evidence links at all.
    for topic in sorted(cs.topics()):
        key = f"topic:{topic}"
        if key in asked:
            continue
        claims = cs.claims_on(topic)
        if len(claims) >= 2 and sum(_supports_on(cs, c.id) for c in claims) == 0:
            q = (f"Hat jemand gute Quellen oder Erfahrungen zu '{topic}'? Ich sammle dazu "
                 "Material und pruefe es kritisch - Widerspruch ist willkommen.")
            return key, q
    return None


def draft_outbox(cs, extensions: dict, proto, cycle: int, *, platforms, max_new: int = 1) -> list:
    """Draft at most one polite forum question from an open need. Bounded and de-duplicated;
    posting itself is gated elsewhere."""
    if not platforms:
        return []
    out = extensions.setdefault("forum_outbox", [])
    asked = extensions.setdefault("forum_asked", [])
    drafts: list = []
    for _ in range(max_new):
        need = _open_need(cs, extensions)
        if need is None:
            break
        key, question = need
        platform = platforms[len(asked) % len(platforms)]      # rotate, deterministic
        draft = {"cycle": cycle, "platform": platform, "need": key, "question": question,
                 "status": "queued", "posted_url": None}
        out.append(draft)
        asked.append(key)
        drafts.append(draft)
        proto.record(cycle, "forum_draft",
                     f"drafted a polite question for {platform} (need {key}) - queued")
    extensions["forum_outbox"] = out[-200:]
    extensions["forum_asked"] = asked[-500:]
    return drafts


def _registry(extensions: dict, platforms) -> list[dict]:
    """Where Joni is allowed to engage and whether posting is live. Registration with real
    credentials is a human step; here we record the allow-list and live state honestly."""
    reg = extensions.setdefault("forum_registry", {})
    for p in platforms:
        reg.setdefault(p, {"allowed": True, "registered": False})
    extensions["forum_registry"] = reg
    return [{"platform": p, **v} for p, v in reg.items()]


def interact(cs, extensions: dict, proto, cycle: int, *, paths, platforms, live: bool) -> dict:
    """One cycle of human/forum interaction: ingest replies (strictly), draft a question, and
    keep the registry. Posting stays gated: when not live, drafts wait for a human to post."""
    extensions["forum_stance"] = STANCE
    registry = _registry(extensions, platforms)
    heard = ingest_inbox(cs, extensions, proto, cycle, paths.forum_inbox)
    drafted = draft_outbox(cs, extensions, proto, cycle, platforms=platforms)

    posted = 0
    if live:
        # Live posting is deliberately not wired to a real network call here: it is an
        # outward, public, irreversible act that needs per-platform credentials and the
        # operator's explicit go-ahead. Until that exists, even in "live" mode we leave the
        # draft queued and flag it, rather than silently posting on someone's behalf.
        for d in extensions.get("forum_outbox", []):
            if d.get("status") == "queued":
                d["status"] = "needs_credentials"
        proto.record(cycle, "forum_note",
                     "forum_live is on but no platform credentials are wired - drafts held")

    # Persist the queues so a human can act on them and feed replies back.
    _save(paths.forum_outbox, extensions.get("forum_outbox", []))
    return {"heard": heard["heard"], "conflicts": heard["conflicts"],
            "drafted": len(drafted), "posted": posted,
            "registry": registry, "live": live}


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
