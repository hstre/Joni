"""Joni's persona as a read-only projection of his *corrected errors*.

The operator's definition: **Expertise = verdichtete Geschichte korrigierter Irrtümer.** A persona
is not a dossier of facts or preferences ("mag X", "arbeitet an Y") - it is the distilled trail of
"ich hielt X für wahr -> es brach an Z -> jetzt Y". Identity, and expertise, live in the *deltas*,
not the current state. The depth of a theme is the density of errors it has metabolised.

This projector DERIVES that persona from the append-only Layer-9 ledger and the object statuses that
already record every revision. It writes NOTHING back into the core and mints no new fact - exactly
like the other read-only projectors. The immutable, hash-chained ledger is the guarantee behind the
operator's rule *"der Irrtum darf nie verschwinden"*: a corrected belief stays in the chain forever.
The projector only **abstracts it upward** into a per-theme lesson, keeping one or two concrete
errors as anchors; the full correction trail stays addressable beneath (never deleted, only not
surfaced up front).

Two stages, in the house order **rules for logic, LLM for language**:
  1. **Deterministic** (this module's core): which corrections exist, how they group by theme, when
     a theme crystallises into a lesson, which one or two errors anchor it, and how deep the theme's
     expertise runs. No model touches any of that - it is the ground truth.
  2. **LLM phrasing** (opt-in, guardrailed): a language pass may only *rephrase* the already-
     assembled lesson into a crisp maxim. It never changes the selection, the anchors, the depth or
     the trail; its output is stored *beside* the deterministic lesson, never replacing it. Off or
     erroring -> the deterministic lesson stands alone.
"""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass
from pathlib import Path

# A revision state = a corrected error. CANDIDATE/QUARANTINED are still provisional (not yet a
# lesson); CONTESTED is an open challenge, not a resolved one. REJECTED (belief killed) and
# SUPERSEDED (belief replaced) are the two terminal corrections a persona is built from.
_CORRECTION_STATUSES = frozenset({"rejected", "superseded"})
_DEFAULT_THRESHOLD = 2        # N corrected errors on one theme -> the theme has earned a lesson
_MAX_ANCHORS = 2              # "abstrahiert mit ein, zwei Beispielen" - never more up front

# Themes that are semantic sinks / undifferentiated labels: there is no *expertise* on 'unsorted'
# or 'forum', so a correction there earns no persona lesson. 'self-model' is a real theme, kept.
_SINK_THEMES = frozenset({"forum", "misc", "unknown", "unsorted", "gatemem", "assess",
                          "other", "general", "uncategorized", "untitled"})
_SERIES_CAP = 2000            # keep state/persona.jsonl bounded (it is appended once per cycle)


def _substantive_reason(reason: str, obj_id: str) -> bool:
    """True only for a reason richer than the generic auto-text a bare rejection records
    (``'C-5 rejected'``). Keeps that boilerplate from lifting the instructiveness score or posing as
    an explanation - only a real recorded reason (or a resolved conflict) counts as one."""
    r = (reason or "").strip().lower()
    oid = (obj_id or "").lower()
    return bool(r) and r not in {f"{oid} rejected", f"{oid} superseded", "rejected", "superseded"}


@dataclass(frozen=True)
class Correction:
    """One metabolised error: a belief that was held, what broke it, and what replaced it. Its
    provenance (the ledger event, any resolved conflict, the successor) is kept in ``trail_refs`` -
    the concrete error is never fabricated and never thrown away."""

    obj_id: str
    theme: str
    kind: str                 # "rejected" | "superseded"
    before: str               # the belief that was held
    trigger: str              # why it changed (ledger reason + any resolved conflict)
    after: str                # the belief that replaced it ("" if rejected / unknown - never faked)
    tick: int
    via_conflict: bool        # a resolved conflict drove this correction
    has_reason: bool = False  # a real reason was recorded (not the fallback naming of the move)
    trail_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"obj_id": self.obj_id, "theme": self.theme, "kind": self.kind,
                "before": self.before[:240], "trigger": self.trigger[:240],
                "after": self.after[:240], "tick": self.tick, "via_conflict": self.via_conflict,
                "has_reason": self.has_reason, "trail_refs": list(self.trail_refs)}


@dataclass(frozen=True)
class Lesson:
    """A per-theme lesson: the abstracted heuristic, 1-2 anchoring errors, the measured depth (=
    density of corrected errors), and the FULL correction trail beneath (nothing forgotten)."""

    theme: str
    depth: int                        # number of corrected errors = measured expertise depth
    heuristic: str                    # deterministic assembly - the ground truth
    anchors: tuple[Correction, ...]   # the 1-2 concrete errors that anchor the lesson
    trail: tuple[str, ...]            # all correction obj_ids on the theme (kept, never gone)
    trigger_kind: str                 # "resolved_conflict" | "threshold" | "self_review"
    heuristic_phrased: str | None = None   # optional LLM rephrasing; None unless the pass ran

    def to_dict(self) -> dict:
        return {"theme": self.theme, "depth": self.depth, "heuristic": self.heuristic,
                "heuristic_phrased": self.heuristic_phrased,
                "anchors": [a.to_dict() for a in self.anchors], "trail": list(self.trail),
                "trigger_kind": self.trigger_kind}


# --------------------------------------------------------------------------- #
# Stage 1 - deterministic: extract corrections, crystallise lessons.          #
# --------------------------------------------------------------------------- #

def _all(s, name: str) -> list:
    from desi_layer9 import ObjectType
    try:
        return list(s.all(getattr(ObjectType, name)))
    except Exception:  # noqa: BLE001 - an object type this core build lacks is simply absent
        return []


def _text_of(s, obj_id: str) -> str:
    o = s.objects.get(obj_id) if hasattr(s, "objects") else None
    return (getattr(o, "text", "") or "").strip() if o is not None else ""


def _trigger_text(reason: str, conflicts: list, kind: str) -> str:
    """A human-readable trigger: the ledger reason and any resolved-conflict reason. Deterministic,
    never invented - falls back to naming the terminal move when no reason was recorded."""
    parts: list[str] = []
    if reason:
        parts.append(reason)
    for cf in conflicts:
        r = (getattr(cf, "resolution_reason", "") or "").strip()
        parts.append(f"Konflikt {cf.id} aufgelöst" + (f": {r}" if r else ""))
    if not parts:
        parts.append("verworfen" if kind == "rejected" else "durch eine spätere Fassung ersetzt")
    return " · ".join(parts)


def extract_corrections(cs) -> list[Correction]:
    """The corrected-error trail, read straight from Layer 9. Read-only, fabricates nothing: a
    missing successor stays ``""``, a missing reason falls back to the terminal move by name."""
    s = cs.core
    ledger_by_id = {e.id: e for e in getattr(s, "ledger", []) or []}
    resolved_by_claim: dict[str, list] = {}
    for cf in _all(s, "CONFLICT"):
        if getattr(getattr(cf, "conflict_status", None), "value", "") == "resolved":
            for cid in getattr(cf, "claim_ids", ()) or ():
                resolved_by_claim.setdefault(cid, []).append(cf)

    out: list[Correction] = []
    # (object type, how to name the theme). A self-model claim's "theme" is the self - a revised
    # belief about oneself is the purest persona correction.
    for name, theme_of in (("CLAIM", lambda o: getattr(o, "topic", "") or "unsorted"),
                           ("SELF_MODEL_CLAIM", lambda o: "self-model")):
        for o in _all(s, name):
            st = getattr(getattr(o, "status", None), "value", "")
            if st not in _CORRECTION_STATUSES:
                continue
            ev = ledger_by_id.get(getattr(o, "ledger_event", "") or "")
            reason = (getattr(ev, "reason", "") or "").strip() if ev else ""
            # A successor is a DIFFERENT object. A rejection's ledger event lists the rejected claim
            # itself in output_refs (input==output), so without this filter every rejection would
            # echo its own text as its 'after' - a nonsensical „X" → „X". Excluding the object's own
            # id keeps a real supersede's new claim and yields no 'after' for a bare rejection.
            successors = tuple(sid for sid in (getattr(ev, "output_refs", ()) or ())
                               if sid and sid != o.id) if ev else ()
            after = next((t for t in (_text_of(s, sid) for sid in successors) if t), "")
            conflicts = resolved_by_claim.get(o.id, [])
            # A generic auto-reason ('C-5 rejected') is not a real explanation: it neither displays
            # as a trigger nor lifts the instructiveness score. Only a substantive reason (or a
            # resolved conflict) counts.
            substantive = _substantive_reason(reason, o.id)
            trail = tuple(dict.fromkeys(
                x for x in (getattr(o, "ledger_event", ""), *[c.id for c in conflicts], *successors)
                if x))
            out.append(Correction(
                obj_id=o.id, theme=theme_of(o), kind=st,
                before=(getattr(o, "text", "") or "").strip(),
                trigger=_trigger_text(reason if substantive else "", conflicts, st), after=after,
                tick=int(getattr(o, "last_changed_tick", 0) or 0),
                via_conflict=bool(conflicts), has_reason=substantive or bool(conflicts),
                trail_refs=trail))
    return out


def _instructiveness(c: Correction) -> int:
    """How much an error *teaches* - not how recent it is. A correction that resolved a real
    contradiction, carries a recorded reason, and replaced (not merely dropped) a belief is the most
    instructive; a richer explanation adds a little. Deterministic, integer, date-free."""
    return (2 * int(c.via_conflict)          # it resolved a genuine contradiction
            + int(c.has_reason)              # a real reason was recorded (not the fallback)
            + int(bool(c.after))             # it *revised* a belief, not just discarded one
            + min(len(c.trigger) // 40, 2))  # a richer explanation, capped so it can't dominate


def _rank_anchors(corrections: list[Correction]) -> list[Correction]:
    """Deterministically pick which errors anchor a lesson: the **most instructive** first (see
    ``_instructiveness``), NOT the most recent - the lesson keeps the errors that teach most. Ties
    break on ``obj_id`` for stability; date deliberately plays no role."""
    return sorted(corrections, key=lambda c: (_instructiveness(c), c.obj_id), reverse=True)


def _heuristic(theme: str, corrections: list[Correction], anchors: list[Correction]) -> str:
    """Assemble the lesson deterministically - this is the ground truth the LLM may only rephrase.
    It states the measured depth, the dominant corrective move, and the anchoring error(s)."""
    n_sup = sum(1 for c in corrections if c.kind == "superseded")
    n_rej = sum(1 for c in corrections if c.kind == "rejected")
    move = ("Annahmen wurden ersetzt" if n_sup > n_rej else
            "Annahmen wurden verworfen" if n_rej > n_sup else "ersetzt und verworfen gleich oft")
    depth = len(corrections)
    head = (f"Auf '{theme}': {depth} korrigierte(r) Irrtum/Irrtümer "
            f"({n_sup}× ersetzt, {n_rej}× verworfen). Muster: {move}.")
    anchor_bits = []
    for a in anchors:
        arrow = f"→ „{a.after}“" if a.after else "→ verworfen"
        anchor_bits.append(f"„{a.before}“ {arrow} ({a.trigger})")
    return head + (" Anker: " + " ; ".join(anchor_bits) if anchor_bits else "")


def crystallize(corrections: list[Correction], *, self_review: bool = False,
                threshold: int = _DEFAULT_THRESHOLD) -> list[Lesson]:
    """Group corrections by theme and crystallise the ones that have earned a lesson. Triggered by
    EITHER a resolved conflict on the theme, OR the threshold count, OR the self-review window -
    exactly the "beides" the operator asked for. Deterministic and pure."""
    by_theme: dict[str, list[Correction]] = {}
    for c in corrections:
        by_theme.setdefault(c.theme, []).append(c)

    lessons: list[Lesson] = []
    for theme, cs_ in sorted(by_theme.items()):
        if theme.strip().lower() in _SINK_THEMES:
            continue                                   # no expertise on an undifferentiated sink
        via_conflict = any(c.via_conflict for c in cs_)
        if via_conflict:
            trigger_kind = "resolved_conflict"
        elif len(cs_) >= threshold:
            trigger_kind = "threshold"
        elif self_review:
            trigger_kind = "self_review"
        else:
            continue                                   # not yet enough metabolised error to teach
        anchors = _rank_anchors(cs_)[:_MAX_ANCHORS]
        lessons.append(Lesson(
            theme=theme, depth=len(cs_), heuristic=_heuristic(theme, cs_, anchors),
            anchors=tuple(anchors),
            trail=tuple(c.obj_id for c in sorted(cs_, key=lambda c: (c.tick, c.obj_id))),
            trigger_kind=trigger_kind))
    # deepest expertise first - the themes with the most metabolised error lead the persona
    lessons.sort(key=lambda ls: (ls.depth, ls.theme), reverse=True)
    return lessons


# --------------------------------------------------------------------------- #
# Stage 2 - LLM phrasing (opt-in): language only, never logic.                 #
# --------------------------------------------------------------------------- #

_PHRASE_SYS = (
    "Du formulierst eine bereits festgelegte Lehre knapp und klar um - eine Maxime in EINEM Satz. "
    "Du darfst NICHTS hinzufügen, keine Fakten erfinden und die Auswahl nicht ändern; nur die "
    "vorgegebene Lehre sprachlich schärfen. Antworte ausschließlich mit dem einen Satz.")


def enabled_llm() -> bool:
    from . import extension_review, projection
    return (projection.enabled() and os.getenv("JONI_PERSONA_LLM", "0") == "1"
            and extension_review.active("persona_llm"))


def _phrase_prompt(lesson: Lesson) -> str:
    anchors = "\n".join(f"- „{a.before}“ → {a.after or 'verworfen'} ({a.trigger})"
                        for a in lesson.anchors)
    return (f"Thema: {lesson.theme}\nLehre (deterministisch, nicht ändern):\n{lesson.heuristic}\n"
            f"Konkrete Irrtümer als Beleg:\n{anchors}\n\nFormuliere die Lehre als eine Maxime.")


def phrase_lessons(lessons: list[Lesson], *, budget=None, store_dir: Path | None = None,
                   runs_per_week: int = 0) -> list[Lesson]:
    """Rephrase each lesson's heuristic into a one-sentence maxim via the captured, budget-metered
    model seam. Guardrail: the deterministic ``heuristic`` is untouched; only ``heuristic_phrased``
    is filled. A dormant switch, a cap hit, or any error leaves it ``None`` (the lesson stands)."""
    from . import model_call, model_profile
    from .config import paths
    store = store_dir or paths().model_calls
    out: list[Lesson] = []
    for ls in lessons:
        try:
            text, _cap = model_call.call(
                model_profile.profile("joni-semantic"), _PHRASE_SYS, _phrase_prompt(ls),
                run_id="persona", store_dir=store, escalation_reason="persona",
                budget=budget, runs_per_week=runs_per_week)
        except Exception:  # noqa: BLE001 - the language pass must never break the projection
            text = None
        phrased = (text or "").strip() or None
        out.append(dataclasses.replace(ls, heuristic_phrased=phrased))
    return out


# --------------------------------------------------------------------------- #
# Orchestration + read-only output.                                           #
# --------------------------------------------------------------------------- #

@dataclass
class _Paths:
    md: Path
    jsonl: Path


def _out_paths(root: Path) -> _Paths:
    state = root / "state"
    return _Paths(md=state / "persona.md", jsonl=state / "persona.jsonl")


def render_md(lessons: list[Lesson], corrections: list[Correction], tick: int) -> str:
    lines = [
        "# Jonis Persona — verdichtete Geschichte korrigierter Irrtümer",
        "",
        "> Expertise = die verdichtete Geschichte korrigierter Irrtümer. Diese Seite ist eine",
        "> **read-only** Projektion aus dem unveränderlichen Layer-9-Ledger: kein neuer Fakt,",
        "> nichts gelöscht. Der Irrtum bleibt in der Kette; hier steht er nur abstrahiert, mit",
        "> ein, zwei Beispielen. Die Lehre ist deterministisch; eine LLM-Fassung (falls vorhanden)",
        "> schärft nur die Sprache, nie die Auswahl.",
        "",
        f"_Stand: Tick {tick} · {len(corrections)} korrigierte(r) Irrtum/Irrtümer · "
        f"{len(lessons)} Lehre(n)._",
        "",
    ]
    if not lessons:
        lines.append("Noch keine Lehre kristallisiert — zu wenig Irrtümer metabolisiert.")
        return "\n".join(lines) + "\n"
    for ls in lessons:
        lines.append(f"## {ls.theme} · Tiefe {ls.depth} ({ls.trigger_kind})")
        lines.append("")
        if ls.heuristic_phrased:
            lines.append(f"**{ls.heuristic_phrased}**")
            lines.append("")
            lines.append(f"_deterministisch:_ {ls.heuristic}")
        else:
            lines.append(f"**{ls.heuristic}**")
        lines.append("")
        for a in ls.anchors:
            arrow = f"→ „{a.after}“" if a.after else "→ verworfen"
            lines.append(f"- Anker: „{a.before}“ {arrow} — {a.trigger}")
        lines.append(f"- _volle Spur ({len(ls.trail)}):_ {', '.join(ls.trail)}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _write(root: Path, lessons: list[Lesson], corrections: list[Correction], tick: int) -> None:
    p = _out_paths(root)
    p.md.parent.mkdir(parents=True, exist_ok=True)
    p.md.write_text(render_md(lessons, corrections, tick), encoding="utf-8")
    row = {"tick": tick, "corrections": len(corrections), "lessons": len(lessons),
           "themes": {ls.theme: ls.depth for ls in lessons}}
    with p.jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    # The series is appended once per cycle; keep it bounded so it can never grow without limit
    # (the state/ bloat that once broke persistence). Cheap: the file stays small by construction.
    try:
        existing = p.jsonl.read_text(encoding="utf-8").splitlines()
        if len(existing) > _SERIES_CAP:
            p.jsonl.write_text("\n".join(existing[-_SERIES_CAP:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def project(cs, *, paths=None, self_review: bool = False, budget=None, runs_per_week: int = 0,
            phrase: bool | None = None) -> dict:
    """One read-only persona projection. Deterministic core always runs; the LLM phrasing runs only
    when enabled (``phrase``/``enabled_llm``). Fail-open: any error yields an empty projection and
    never breaks the cycle. Writes ``state/persona.md`` + ``state/persona.jsonl`` when ``paths`` is
    given."""
    try:
        corrections = extract_corrections(cs)
        lessons = crystallize(corrections, self_review=self_review)
        do_phrase = enabled_llm() if phrase is None else phrase
        if do_phrase and lessons:
            store = paths.model_calls if paths is not None else None
            lessons = phrase_lessons(lessons, budget=budget, store_dir=store,
                                     runs_per_week=runs_per_week)
        tick = int(getattr(cs.core, "tick", 0) or 0)
        if paths is not None:
            _write(paths.root, lessons, corrections, tick)
        return {"corrections": len(corrections), "lessons": len(lessons),
                "phrased": bool(do_phrase), "themes": {ls.theme: ls.depth for ls in lessons}}
    except Exception:  # noqa: BLE001 - a projector must never break the loop
        return {"corrections": 0, "lessons": 0, "phrased": False, "themes": {}, "error": True}
