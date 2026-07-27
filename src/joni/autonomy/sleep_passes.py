"""Schlafmodus S1-S3: the three passes that run while Joni sleeps. All read-only, all deterministic.

They run whenever the state machine SAYS sleep - independently of whether the intake gate is armed.
That separation is deliberate: in observation mode Joni does the sleep *work* without the sleep
*fast*, so we can measure whether sleep work ripens anything before ever paying the price of
stopping intake.

**S1 - Refragmentierung.** Provisional entries were written one at a time, each blind to the others.
This pass re-cuts them into fragments and finds substantive fragments shared by entries that were
never linked. It proposes associative links and *nothing else* - no provenance is inferred from
topical similarity, entries are never mutated.

The bar is deliberately high, because we have already paid for the cheap version: lexical recurrence
produced hundreds of junk hypotheses. A fragment must carry at least ``MIN_FRAGMENT_WORDS``
content words after stop-words, and the whole pass is capped. Thin overlaps are counted and
discarded, so the rejection rate stays visible instead of the junk becoming output.

**S2 - Struktur-Audit.** A method can only be trialed if it is *shaped* like a procedure: it names
a trigger (when does it apply), steps (what to do), and a verification (how you would know it
worked). This pass scores every candidate method 0-3 on exactly those three, skipping the harvested
paper titles the breakdown already buckets as ``nicht_ausfuehrbar``. The 3/3-but-untested ones are
the honest drain targets: real procedures the trial pipeline could reach today.

**S3 - Revisionsvorschläge.** Fires ONLY on a concrete structural defect S2 measured: a real short
procedure missing exactly one of the three components. It writes a *defect report* - which piece is
missing and why the method cannot be trialed without it - never invented content, never a code
change, never applied. Deterministic, no model call: naming a gap is logic, not language.
Hard-capped per sleep window so a long sleep cannot flood the wake queue.
"""
from __future__ import annotations

import contextlib
import json
import re

MIN_FRAGMENT_WORDS = 3      # S1: a shared fragment thinner than this is noise, not a link
MAX_LINK_DEGREE = 4         # S1: a fragment in MORE entries than this is boilerplate, not a link
MIN_FAMILY = 3              # S1: this many fragments differing by one token = a template family
MAX_LINKS = 12              # S1: cap per pass
MAX_REVISIONS = 3           # S3: cap per pass - a long sleep may not flood the wake queue

_STOP_TEXT = """a an and are as at be been but by for from had has have in into is it its not
of on or that the their them then there these they this to was were which while with without would
der die das und oder aber ist sind war waren den dem des ein eine einer einem eines nicht auch noch
wenn dann dass wie bei von zu zum zur im in auf für mit"""
_STOP = frozenset(_STOP_TEXT.split())

_WORD = re.compile(r"[a-zA-ZÀ-ɏ]{2,}")

# S2: the three components a text must show to be trialable as a procedure.
_TRIGGER = re.compile(r"\b(when|if|whenever|given|applies? to|use (this|it) (when|for)|"
                      r"wenn|falls|sobald|bei|gilt für)\b", re.I)
_STEPS = re.compile(r"\b(step|steps|first|then|next|apply|compute|split|normalise|normalize|"
                    r"replace|iterate|for each|schritt|zuerst|danach|dann|wende|berechne)\b", re.I)
_VERIFY = re.compile(r"\b(verify|verified|check|measure|metric|compare|baseline|accuracy|"
                     r"error rate|test set|benchmark|succeeds? (if|when)|prüfe|messe|vergleiche|"
                     r"metrik|kriterium)\b", re.I)

_COMPONENTS = (("trigger", _TRIGGER), ("steps", _STEPS), ("verification", _VERIFY))


def _fragments(text: str) -> set[str]:
    """Re-cut a text into substantive fragments: sentence-ish chunks reduced to their content words.
    A fragment is kept only if it still carries ``MIN_FRAGMENT_WORDS`` words after stop-words - the
    lesson from the recurrence-hypothesis junk is that thin lexical overlap is not a signal."""
    out: set[str] = set()
    for chunk in re.split(r"[.;:!?\n]+", text or ""):
        words = [w.lower() for w in _WORD.findall(chunk)]
        content = [w for w in words if w not in _STOP]
        if len(content) >= MIN_FRAGMENT_WORDS:
            out.add(" ".join(content))
    return out


def _template_families(fragments: list[str]) -> set[str]:
    """Fragments that differ from one another in a single token are a TEMPLATE, not a shared idea.

    Found live on the first run against the real store: every proposed 'link' was the same generated
    sentence with one word swapped ("across my forum claims **X** recurs through …"). What those
    entries share is the sentence Joni generates them with; the only part that carries meaning is
    exactly the token that differs. A family of ``MIN_FAMILY`` such variants is discarded whole.
    """
    by_shape: dict[tuple, list[str]] = {}
    for frag in fragments:
        words = frag.split()
        for i in range(len(words)):
            by_shape.setdefault((len(words), i, tuple(words[:i] + words[i + 1:])), []).append(frag)
    out: set[str] = set()
    for members in by_shape.values():
        if len(members) >= MIN_FAMILY:
            out.update(members)
    return out


def refragment(entries, *, max_links: int = MAX_LINKS) -> dict:
    """S1: propose associative links between provisional entries that share a substantive fragment.

    Read-only, and deliberately suspicious of its own output. Three filters, each counted so the
    pass can never look productive by hiding what it threw away:

      * **thin**       - the overlap carries fewer than ``MIN_FRAGMENT_WORDS`` content words;
      * **boilerplate** - the fragment appears in more than ``MAX_LINK_DEGREE`` entries. A genuine
        association is *rare*; a phrase two dozen entries share is a form, not a finding;
      * **template**   - the fragment is one of a family differing by a single token.
    """
    entries = list(entries)
    by_fragment: dict[str, list[str]] = {}
    thin = 0
    for e in entries:
        eid = e.entry_id()
        text = f"{getattr(e, 'content', '')} {getattr(e, 'detail', '')}"
        for chunk in re.split(r"[.;:!?\n]+", text):
            words = [w.lower() for w in _WORD.findall(chunk)]
            if 0 < len([w for w in words if w not in _STOP]) < MIN_FRAGMENT_WORDS:
                thin += 1
        for frag in _fragments(text):
            by_fragment.setdefault(frag, [])
            if eid not in by_fragment[frag]:
                by_fragment[frag].append(eid)
    shared = {f: ids for f, ids in by_fragment.items() if len(ids) >= 2}
    kept = {f: ids for f, ids in shared.items() if len(ids) <= MAX_LINK_DEGREE}
    boilerplate = len(shared) - len(kept)
    families = _template_families(sorted(shared))          # families judged over ALL shared forms
    template = sum(1 for f in kept if f in families)
    links = [{"fragment": f[:160], "entries": ids}
             for f, ids in sorted(kept.items()) if f not in families]
    return {"considered": len(entries), "fragments": len(by_fragment), "thin_discarded": thin,
            "boilerplate_discarded": boilerplate, "template_discarded": template,
            "links": links[:max_links], "links_total": len(links)}


def procedure_score(name: str, summary: str) -> tuple[int, list[str]]:
    """S2: how many of (trigger, steps, verification) a method text shows, and which are MISSING.
    Purely structural - it says nothing about whether the procedure is any good, only whether it is
    shaped so that a trial could ever be run against it."""
    text = f"{name} {summary}"
    missing = [key for key, pattern in _COMPONENTS if not pattern.search(text)]
    return len(_COMPONENTS) - len(missing), missing


def audit(cs) -> dict:
    """S2: score every candidate method's procedural structure. Read-only over the core.

    Paper titles are skipped, not scored - the breakdown already buckets them as
    ``nicht_ausfuehrbar`` and scoring them would only inflate the 0/3 bar with known junk.
    """
    from ..method_trial import method_breakdown, problems
    methods = method_breakdown._candidate_methods(cs)
    by_score = {i: 0 for i in range(len(_COMPONENTS) + 1)}
    skipped = 0
    complete: list[dict] = []
    defects: list[dict] = []
    for m in sorted(methods, key=lambda x: str(getattr(x, "id", ""))):
        name = str(getattr(m, "name", "") or "")
        summary = str(getattr(m, "summary", "") or "")
        if not problems.is_short_procedure_name(name):
            skipped += 1
            continue
        score, missing = procedure_score(name, summary)
        by_score[score] += 1
        row = {"id": str(getattr(m, "id", "")), "name": name[:90], "missing": missing}
        if score == len(_COMPONENTS):
            complete.append(row)
        elif len(missing) == 1:                 # exactly one gap = a concrete, nameable defect
            defects.append(row)
    return {"scored": sum(by_score.values()), "skipped_titles": skipped, "by_score": by_score,
            "complete": complete[:20], "defects": defects}


_WHY = {
    "trigger": "kein Auslöser genannt - unklar, wann das Verfahren überhaupt gilt",
    "steps": "keine Schritte genannt - es gibt nichts Ausführbares zu trialen",
    "verification": "kein Prüfkriterium genannt - ein Trial hätte keinen messbaren Ausgang",
}


def revisions(audit_result: dict, cycle: int, *, max_revisions: int = MAX_REVISIONS) -> list[dict]:
    """S3: turn each concrete one-component defect into a versioned revision proposal.

    A defect REPORT, not a rewrite: it names the missing component and why the method cannot be
    trialed without it. Nothing is invented, nothing is applied, no model is asked - naming a gap
    is logic. A human (or the Auftrag pipeline) decides what to do with it.
    """
    out = []
    for i, d in enumerate(audit_result.get("defects", [])[:max_revisions]):
        missing = (d.get("missing") or ["?"])[0]
        out.append({
            "rev": 1, "cycle": cycle, "method_id": d.get("id", ""), "name": d.get("name", ""),
            "missing": missing, "defect": _WHY.get(missing, "Strukturkomponente fehlt"),
            "proposal": f"Fehlende Komponente '{missing}' ergänzen oder die Methode verwerfen.",
            "applied": False, "index": i,
        })
    return out


def _append(path, rows) -> None:
    if path is None or not rows:
        return
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_passes(cs, extensions: dict, proto, cycle: int, *, paths) -> dict:
    """Run S1-S3 for one sleeping cycle, persist their artefacts, expose them on ``extensions``.
    Fail-open: any error yields ``{}`` and the cycle continues untouched."""
    try:
        from ..method_trial import provisional as pv
        entries = pv.load(getattr(paths, "provisional", None))
        frag = refragment(entries)
        aud = audit(cs)
        revs = revisions(aud, cycle)
        _append(getattr(paths, "refragment", None),
                [{"cycle": cycle, "considered": frag["considered"],
                  "thin_discarded": frag["thin_discarded"], "links_total": frag["links_total"],
                  "links": frag["links"]}])
        _append(getattr(paths, "sleep_audit", None), [{"cycle": cycle, **{
            k: aud[k] for k in ("scored", "skipped_titles", "by_score")}}])
        _append(getattr(paths, "sleep_revisions", None), revs)
        out = {"refragment": frag, "audit": aud, "revisions": revs}
        extensions["sleep_passes"] = out
        proto.record(cycle, "sleep_work",
                     f"S1 {frag['links_total']} Verknüpfungen ({frag['thin_discarded']} zu dünn "
                     f"verworfen) · S2 {aud['scored']} Methoden strukturiert, "
                     f"{len(aud['complete'])} vollständig · S3 {len(revs)} Defektberichte")
        return out
    except Exception as exc:  # noqa: BLE001 - a sleep pass must never break a cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "sleep_work", f"[Schlaf-Pass übersprungen] {type(exc).__name__}")
        return {}


__all__ = ["refragment", "procedure_score", "audit", "revisions", "run_passes",
           "MIN_FRAGMENT_WORDS", "MAX_LINKS", "MAX_REVISIONS"]
