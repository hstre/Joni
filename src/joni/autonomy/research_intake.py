"""The receiving end of Doktores - Joni's independent research organisation.

Doktores (Theorist -> Literature Scout -> Falsifier -> Experimental Designer -> Method
Reviewer -> Paper Builder -> Adversarial Reviewer) turns Joni's Layer-9 conflicts and Kevin's
candidates into worked research. It hands results back as a structured ``research_output``
**package** - never by writing into Layer 9 directly. This module is the only place those
packages enter Joni, and it enforces the governance contract:

* **Two channels.** The *epistemic* channel (``recommended_claim_updates``) enters Layer 9 as
  SOURCES - exactly as strict as a forum reply or a paper: candidate authority, conflict-checked,
  never auto-confirmed. The *publication* channel (paper / report / protocol / replication /
  summary) is archived under ``docs/research/`` and carries **no** epistemic weight - a
  well-written paper is not a stronger belief than its actual results.

* **Joni decides.** A package is a SOURCE with clear provenance: *internally produced, method-
  checked, not externally replicated*. Joni's normal governance (operators-only confirmation,
  conflicts held open) decides what, if anything, is adopted. An ``adversarial_reviewer`` verdict
  of ``reject`` skips the epistemic channel entirely (the publication is still archived, marked
  rejected, for the audit trail).

The package schema both sides agree on lives in ``RESEARCH_OUTPUT_SCHEMA`` below.
"""

from __future__ import annotations

import contextlib
import json
import re
from pathlib import Path

# The provenance origin stamped on every claim that enters through this path. It is NOT the
# privileged HUMAN origin and NOT a confirmed authority - it marks "internal research output".
RESEARCH_ORIGIN = "internal-research"
RESEARCH_PLATFORM = "research"
RESEARCH_HANDLE = "doktores"

# The contract Doktores targets. Documented here so the producer and this consumer never drift.
RESEARCH_OUTPUT_SCHEMA = {
    "id": "stable package id (used for dedupe)",
    "source_hypothesis_ids": "[Layer-9 claim/conflict ids that seeded the research]",
    "theory": "the precise theory the Theorist formulated",
    "predictions": "[falsifiable predictions]",
    "evidence_for": "[{text, ref, strength}]",
    "evidence_against": "[{text, ref, strength}]",
    "experiments": "[{design, baselines, metrics, stop_criteria}]",
    "results": "what the experiments/analysis found (may be 'not yet run')",
    "limitations": "[known limitations]",
    "reviewer_verdict": "accept | revise | reject  (the Adversarial Reviewer's call)",
    "confidence": "0.0-1.0 internal confidence (NOT a probability of truth)",
    "recommended_claim_updates": (
        "[{op: add_claim|open_conflict, text, topic, against?: [claim_ids]}]  "
        "- the epistemic channel; each enters as a SOURCE, never a belief"
    ),
    "publication": "{kind: paper|report|protocol|replication|summary, title, markdown}",
}

_SLUG = re.compile(r"[^a-z0-9]+")


def _load(path: Path, default):
    if path.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            return json.loads(path.read_text(encoding="utf-8"))
    return default


def _slug(text: str) -> str:
    return _SLUG.sub("-", (text or "").lower()).strip("-")[:60] or "untitled"


def _ingest_one(cs, pkg: dict, proto, cycle: int, paths, heard: list) -> dict:
    """Ingest one research_output package. Returns per-package counters. Never raises."""
    pid = str(pkg.get("id") or _slug(pkg.get("theory", "")) or f"RO-{cycle}")
    verdict = str(pkg.get("reviewer_verdict", "revise")).lower()
    confidence = pkg.get("confidence")
    seeds = list(pkg.get("source_hypothesis_ids", []) or [])
    candidates = 0
    conflicts = 0

    # Epistemic channel - only when the internal review did not reject the work. Each
    # recommended update enters as a SOURCE (candidate authority), conflict-checked, never
    # confirmed. Joni's governance decides downstream what, if anything, is adopted.
    if verdict != "reject":
        existing = {c.id for c in cs.active_claims()}
        for upd in pkg.get("recommended_claim_updates", []) or []:
            if not isinstance(upd, dict):
                continue
            text = str(upd.get("text", "")).strip()
            if not text:
                continue
            topic = str(upd.get("topic") or (seeds[0] if seeds else "research"))
            cid = cs.hear(text, topic, handle=RESEARCH_HANDLE,
                          platform=RESEARCH_PLATFORM, origin=RESEARCH_ORIGIN)
            candidates += 1
            heard.append({"cycle": cycle, "package": pid, "claim": cid, "topic": topic,
                          "verdict": verdict, "confidence": confidence,
                          "source_hypothesis_ids": seeds, "text": text[:200],
                          "treated_as": ("source (internal research, method-checked, "
                                         "not externally replicated) - not an authority")})
            # An explicit contradiction the research wants on record: held open, never decided
            # in the research's favour, exactly like any other conflict.
            if str(upd.get("op", "add_claim")) == "open_conflict":
                for against in upd.get("against", []) or []:
                    if against in existing:
                        with contextlib.suppress(Exception):
                            cs.open_conflict((cid, against), severity="soft",
                                             conflict_kind="internal-research")
                            conflicts += 1
        # Surface any further contradictions the new SOURCES opened against held claims.
        with contextlib.suppress(Exception):
            conflicts += len(cs.detect_and_open_conflicts())

    # Publication channel - archived, provenance-stamped, with NO epistemic weight of its own.
    published = _archive_publication(pkg, pid, verdict, confidence, paths)

    proto.record(cycle, "research",
                 f"ingested {pid} ({verdict}, conf {confidence}) -> {candidates} candidate "
                 f"update(s) as SOURCE, {conflicts} conflict(s) held open"
                 + (f"; published {published}" if published else ""))
    return {"candidates": candidates, "conflicts": conflicts, "published": bool(published)}


def _archive_publication(pkg: dict, pid: str, verdict: str, confidence, paths) -> str:
    """Write the publication artifact under docs/research/. Returns its kind, or '' if none."""
    pub = pkg.get("publication")
    if not isinstance(pub, dict) or not (pub.get("markdown") or pub.get("title")):
        return ""
    kind = str(pub.get("kind", "report"))
    title = str(pub.get("title", pid))
    out_dir = paths.research_dir
    with contextlib.suppress(OSError):
        out_dir.mkdir(parents=True, exist_ok=True)
        header = (
            f"# {title}\n\n"
            f"> **Provenance:** internal research output (Doktores) — *method-checked, "
            f"not externally replicated*. This is a SOURCE, not a confirmed belief.\n"
            f"> **Adversarial-reviewer verdict:** {verdict} · **internal confidence:** "
            f"{confidence}\n"
            f"> **Kind:** {kind} · **package:** `{pid}`\n\n---\n\n")
        (out_dir / f"{pid}.md").write_text(header + str(pub.get("markdown", "")),
                                           encoding="utf-8")
    return kind


def ingest(cs, extensions: dict, proto, cycle: int, *, paths) -> dict:
    """Ingest every new research_output package from ``state/research_inbox.json``.

    Best-effort and idempotent: packages are deduped by id, a malformed package is skipped (it
    never crashes a cycle), and nothing here ever confirms a claim. Returns a summary."""
    packages = _load(paths.research_inbox, [])
    if not isinstance(packages, list) or not packages:
        return {"ingested": 0, "candidates": 0, "conflicts": 0, "published": 0}

    seen = set(extensions.setdefault("research_seen", []))
    heard = extensions.setdefault("research_heard", [])
    ingested = candidates = conflicts = published = 0
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        pid = str(pkg.get("id") or _slug(pkg.get("theory", "")) or f"RO-{cycle}")
        if pid in seen:
            continue
        try:
            r = _ingest_one(cs, pkg, proto, cycle, paths, heard)
        except Exception as exc:                 # one bad package must not stop the cycle
            proto.record(cycle, "research", f"skipped malformed package {pid}: {exc}")
            seen.add(pid)
            continue
        seen.add(pid)
        ingested += 1
        candidates += r["candidates"]
        conflicts += r["conflicts"]
        published += int(r["published"])

    extensions["research_seen"] = sorted(seen)[-2000:]
    extensions["research_heard"] = heard[-200:]
    return {"ingested": ingested, "candidates": candidates,
            "conflicts": conflicts, "published": published}
