"""Live seam for the Personal Store (docs/PERSONAL_STATE.md §6/§8): the operator's own statements
enter here, the store decays each cycle, and the re-confirmation queue is surfaced.

The operator is the trusted HUMAN — unlike a forum reply, which is a SOURCE (see humans.py). A line
the operator writes into ``state/personal_inbox.txt`` is a deliberate self-statement, so it enters
as **confirmed** (``human_ref`` = the inbox line + cycle), never merely inferred by the system.
Phase 1 categories only (``store.CATEGORIES`` = preferences, projects); unknown categories are
dropped, never guessed into scope. Deterministic; the LLM is never in this path.
"""
from __future__ import annotations

from pathlib import Path

from joni.personal.store import CATEGORIES, PersonalStore

# The operator writes statements below this how-to; the loop ingests them as CONFIRMED self-claims,
# then resets the file (same "you write, Joni ingests, box is cleared" pattern as forum_replies).
_INBOX_TEMPLATE = (
    "# Persönlicher Eingang — eine Aussage pro Zeile, Format:\n"
    "#   kategorie | aussage\n"
    "# kategorie ∈ {preferences, projects}. Beispiel:\n"
    "#   preferences | bevorzugt direkte, ehrliche Rückmeldung — klar warnen wenn schwach\n"
    "#   projects | DESi: solution_space kalibriert, 4 Inseln bestätigt\n"
    "# Joni nimmt jede Zeile als BESTÄTIGTE Selbst-Aussage auf (du bist der vertraute Operator);\n"
    "# danach wird diese Datei geleert. Zeilen mit '#' werden ignoriert.\n"
)


def parse_inbox(text: str) -> list[tuple[str, str]]:
    """Parse operator inbox lines into ``(category, statement)``. Blank and ``#`` lines are ignored;
    a line whose category is out of phase-1 scope is dropped (never guessed into a scoped category).
    Pure — the caller folds the result into the store."""
    out: list[tuple[str, str]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|", 1)]
        if len(parts) != 2:
            continue
        category, statement = parts[0].lower(), parts[1]
        if category in CATEGORIES and statement:
            out.append((category, statement))
    return out


def render_reconfirm_sheet(due: list) -> str:
    """Render the decayed-but-relevant claims as a sheet: 'this is what I believe about you —
    correct me'. Pure. Confirming resets the clock; contradicting rejects the claim."""
    lines = [
        "# Joni — was ich über dich zu wissen glaube (bitte korrigieren)",
        "",
        "Diese Einträge sind am Verblassen. Bestätige sie (Uhr auf null) oder widersprich",
        "(dann verwerfe ich sie). Trag Korrekturen einfach in `state/personal_inbox.txt` ein.",
        "",
        f"_{len(due)} Eintrag/Einträge zur Re-Bestätigung._",
        "",
    ]
    if not due:
        return "\n".join([*lines, "Gerade nichts zu bestätigen."]) + "\n"
    for c in due:
        lines += [f"- **[{c.category}]** {c.statement}"]
    return "\n".join(lines) + "\n"


def interact(store: PersonalStore, proto, cycle: int, *, tick: int,
             inbox_path, reconfirm_path) -> dict:
    """One cycle of personal-store upkeep: ingest the operator's statements (as confirmed), age
    the store (decay → outdated), and surface the re-confirmation queue. Empty inbox → no-op."""
    inbox_path, reconfirm_path = Path(inbox_path), Path(reconfirm_path)
    entered = 0
    if inbox_path.exists():
        parsed = parse_inbox(inbox_path.read_text(encoding="utf-8"))
        for i, (category, statement) in enumerate(parsed):
            cid = f"PC-{cycle}-{i}"
            store.observe(cid, category, statement, tick=tick)           # arrives observed…
            store.confirm(cid, human_ref=f"personal_inbox@cycle{cycle}",  # …operator confirms it
                          tick=tick)
            entered += 1
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(_INBOX_TEMPLATE, encoding="utf-8")             # reset the drop box

    outdated = store.age(tick)                                          # decay → outdated (audited)
    due = store.due_for_reconfirm(tick)
    reconfirm_path.parent.mkdir(parents=True, exist_ok=True)
    reconfirm_path.write_text(render_reconfirm_sheet(due), encoding="utf-8")

    if entered or outdated or due:
        proto.record(cycle, "personal",
                     f"entered {entered} confirmed, {len(outdated)} outdated, "
                     f"{len(due)} due for re-confirmation")
    return {"entered": entered, "outdated": len(outdated), "reconfirm": len(due)}
