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

# The reply drop box (state/forum_replies.txt) opens with this how-to; a human pastes replies
# below it, the loop ingests them as SOURCES and resets the file.
_REPLIES_TEMPLATE = (
    "# Antworten hier einfügen - eine pro Zeile, Format:\n"
    "#   plattform | handle | die Antwort als Text\n"
    "# Beispiel:\n"
    "#   hacker_news | userXY | Dein Punkt zu drift ignoriert die Saisonalität.\n"
    "# Joni hört das im nächsten Zyklus als QUELLE (nie als Autorität); danach wird diese\n"
    "# Datei wieder geleert. Zeilen mit '#' werden ignoriert.\n"
)


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


def ingest_replies_text(text: str) -> list[dict]:
    """Parse a human's pasted forum replies into inbox messages.

    One reply per line: ``platform | handle | text`` (handle optional). Blank lines and lines
    starting with ``#`` are ignored. Pure - the caller folds the result into the inbox."""
    out: list[dict] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|", 2)]
        if len(parts) == 3:
            platform, handle, body = parts
        elif len(parts) == 2:
            platform, handle, body = parts[0], "anon", parts[1]
        else:
            platform, handle, body = "forum", "anon", parts[0]
        if body:
            out.append({"platform": platform or "forum", "handle": handle or "anon",
                        "text": body})
    return out


def _fold_replies(paths) -> int:
    """Fold pasted replies (``state/forum_replies.txt``) into the inbox, then reset the drop
    box - so a human can feed forum replies back without hand-editing JSON."""
    rp = paths.forum_replies
    if not rp.exists():
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(_REPLIES_TEMPLATE, encoding="utf-8")
        return 0
    parsed = ingest_replies_text(rp.read_text(encoding="utf-8"))
    if not parsed:
        return 0
    inbox = _load(paths.forum_inbox, [])
    if not isinstance(inbox, list):
        inbox = []
    inbox.extend(parsed)
    _save(paths.forum_inbox, inbox)
    rp.write_text(_REPLIES_TEMPLATE, encoding="utf-8")      # consumed - reset the drop box
    return len(parsed)


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
    """Draft at most one polite forum question from an open need. Bounded and de-duplicated.

    A draft is only ever *drafted* - it is never posted by the loop. Posting is done later by
    the relay (on the VPS) and ONLY for drafts a human has approved (see ``select_postable``)."""
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
        fid = f"FA-{cycle}-{_fingerprint(platform, key, question)[:6]}"
        draft = {"id": fid, "cycle": cycle, "platform": platform, "need": key,
                 "question": question, "status": "drafted", "posted_url": None}
        out.append(draft)
        asked.append(key)
        drafts.append(draft)
        proto.record(cycle, "forum_draft",
                     f"drafted {fid} for {platform} (need {key}) - awaiting human approval")
    extensions["forum_outbox"] = out[-200:]
    extensions["forum_asked"] = asked[-500:]
    return drafts


def select_postable(outbox: list, approved_ids) -> list:
    """The moderation gate: of the drafted questions, only those a human has approved and that
    are not yet posted may be sent. Pure function - the relay calls this before posting."""
    approved = set(approved_ids or ())
    return [d for d in (outbox or [])
            if isinstance(d, dict) and d.get("id") in approved and d.get("status") != "posted"]


def render_post_sheet(outbox: list) -> str:
    """Render Joni's un-posted drafts as a copy-paste sheet for a human to post by hand."""
    drafts = [d for d in (outbox or [])
              if isinstance(d, dict) and d.get("status") != "posted" and d.get("question")]
    lines = [
        "# Joni's Post-Mappe",
        "",
        "Joni *textet*, **du** postest. Diese Fragen hat Joni selbst formuliert. Du",
        "entscheidest, ob, wo und ob überhaupt - poste unter **deinem** Account, wo es",
        "passt. Antworten trägst du in `state/forum_replies.txt` ein; Joni hört sie",
        "dann als **Quelle**, nie als Autorität.",
        "",
        f"_{len(drafts)} offene(r) Entwurf/Entwürfe._",
        "",
    ]
    if not drafts:
        return "\n".join([*lines, "Gerade nichts zu posten."]) + "\n"
    for d in drafts:
        lines += [
            f"## {d.get('id')} · Vorschlag: {d.get('platform')}",
            "",
            "```",
            str(d.get("question", "")).strip(),
            "```",
            "",
            "- Gepostet unter (URL): ____________",
            "",
        ]
    return "\n".join(lines) + "\n"


def _write_post_sheet(paths, outbox: list) -> None:
    sheet = paths.post_sheet
    sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.write_text(render_post_sheet(outbox), encoding="utf-8")


def approve(approved_path: Path, draft_id: str) -> list:
    """Record a human approval for one drafted question (so the relay may post it). Returns the
    full approved-id list. This is the ONLY way a post ever leaves Joni - a deliberate gate."""
    ids = _load(approved_path, [])
    if not isinstance(ids, list):
        ids = []
    if draft_id not in ids:
        ids.append(draft_id)
    _save(approved_path, ids)
    return ids


def _registry(extensions: dict, platforms) -> list[dict]:
    """Where Joni is allowed to engage and whether posting is live. Registration with real
    credentials is a human step; here we record the allow-list and live state honestly."""
    reg = extensions.setdefault("forum_registry", {})
    for p in platforms:
        reg.setdefault(p, {"allowed": True, "registered": False})
    extensions["forum_registry"] = reg
    return [{"platform": p, **v} for p, v in reg.items()]


def _post_live(extensions: dict, proto, cycle: int, paths, live: bool, *, max_post: int = 2) -> int:
    """When live, post un-posted drafts to platforms with a *ready* adapter, paced per cycle.

    Two gates by platform kind: an **agent-only** network in ``forum_autopost()`` (Moltbook)
    posts WITHOUT per-post human approval - that's its intended use. A **human forum** posts
    only if a human approved the draft (and has no live adapter anyway). Either way it needs
    ``forum_live()`` on, the platform's adapter ready, and is bounded per cycle so Joni never
    floods. Each post is marked and recorded on the protocol."""
    if not live:
        return 0
    from joni.relay.adapters import NotReady, get_adapter

    from .config import forum_autopost
    autopost = set(forum_autopost())
    approved = set(_load(paths.forum_approved, []) or ())
    posted = 0
    for d in extensions.get("forum_outbox", []):
        if posted >= max_post:
            break
        if not isinstance(d, dict) or d.get("status") == "posted":
            continue
        platform = d.get("platform", "")
        if platform not in autopost and d.get("id") not in approved:
            continue                       # human forum -> needs approval; leave it queued
        adapter = get_adapter(platform)
        if not adapter.ready():
            continue                       # no live adapter for this platform - leave it queued
        try:
            url = adapter.post(d.get("question", ""))
        except NotReady:
            continue                       # not configured / transient - retry next cycle
        d["status"], d["posted_url"] = "posted", url
        posted += 1
        gate = "agent-net auto" if platform in autopost else "human-approved"
        proto.record(cycle, "forum_post",
                     f"posted {d.get('id')} to {platform} ({gate}) -> {url}")
    return posted


def interact(cs, extensions: dict, proto, cycle: int, *, paths, platforms, live: bool) -> dict:
    """One cycle of human/forum interaction: ingest replies (strictly), draft a question,
    keep the registry, and - when live - post any human-approved draft to a ready adapter."""
    extensions["forum_stance"] = STANCE
    registry = _registry(extensions, platforms)
    folded = _fold_replies(paths)          # a human's pasted replies -> inbox (then reset)
    if folded:
        proto.record(cycle, "heard", f"folded {folded} pasted reply(ies) into the inbox")
    heard = ingest_inbox(cs, extensions, proto, cycle, paths.forum_inbox)
    drafted = draft_outbox(cs, extensions, proto, cycle, platforms=platforms)

    # Posting is gated by forum_live(). Agent-only networks (Moltbook) post autonomously;
    # human forums need approval and stay on the "you post, Joni writes" path (outbox + the
    # copy-paste post sheet a human carries).
    posted = _post_live(extensions, proto, cycle, paths, live)
    _save(paths.forum_outbox, extensions.get("forum_outbox", []))
    _write_post_sheet(paths, extensions.get("forum_outbox", []))
    return {"heard": heard["heard"], "conflicts": heard["conflicts"],
            "drafted": len(drafted), "posted": posted, "folded": folded,
            "registry": registry, "live": live}


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
