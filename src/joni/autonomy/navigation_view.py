"""Joni's navigation capability — run the solution-space navigation on the live Layer-9 core.

READ-ONLY: it projects the core into a prioritised exploration agenda (which unreached island / which
bridge to work next, with which deep-method operator and why) and returns it as a plain dict. It NEVER
mutates the core, never runs a model in the loop path, and lazy-imports ``solution_space`` so it adds
nothing to loop startup. Fail-open: if the package or the data is unavailable, it returns an empty,
clearly-marked result rather than raising.

This is the confirmed value of the solution-space work (navigation + discovery), wired as a capability
the autonomy loop can call — deliberately NOT the method-as-prompt lever that nine measurements found
null. The *acting* on the agenda (the creative exploration step) stays out of here; this only SURFACES
where the room is.
"""

from __future__ import annotations

#: Zeitbudget der Navigation je Zyklus, in Sekunden. Die Kartographie vergleicht ALLE Paare;
#: bei n Punkten sind das n*(n-1)/2 Vergleiche zu gemessenen 6,2 us. Aus dem Budget folgt die
#: Punktgrenze, nicht umgekehrt - so steht im Quelltext, was diese Zeile kosten darf, und nicht
#: eine gegriffene Zahl.
NAV_BUDGET_SECONDS = 5.0
_US_PER_PAIR = 6.2e-6


def max_points(budget_seconds: float = NAV_BUDGET_SECONDS) -> int:
    """Wie viele Punkte in ``budget_seconds`` paarweise vergleichbar sind."""
    import math
    return int(math.sqrt(2 * budget_seconds / _US_PER_PAIR)) + 1


def run_navigation(core, *, top: int = 8, allow_model: bool = False,
                   budget_seconds: float = NAV_BUDGET_SECONDS, **kw) -> dict:
    """Project ``core`` into a navigation agenda. ``allow_model`` defaults to False (deterministic
    lexical embeddings — no network in the loop). Returns ``{"available": bool, ...report}``.

    **Begrenzt, und zwar sichtbar.** Am 07.08.2026 gemessen: bei 10.958 Claims vergleicht die
    Kartographie 60.033.403 Paare und braucht dafuer 27 Minuten - je Zyklus, um *eine* beratende
    Zeile zu erzeugen, die nichts entscheidet und den Kern nicht anfasst. Das ist keine
    Langsamkeit, die man wegoptimiert, sondern ein Missverhaeltnis.

    Ueberschreitet der Zustand die Grenze, wird **nicht gekuerzt**, sondern abgelehnt und der
    Grund mitgegeben. Kuerzen hiesse zu entscheiden, welche Claims in die Karte gehoeren - eine
    Festlegung ueber ihren Zweck, die in einer Kostenbremse nichts zu suchen hat. Ablehnen ist
    genau das, was dieses Modul ohnehin fuer fehlende Daten vorsieht: ein leeres, klar
    gekennzeichnetes Ergebnis statt eines stillen Halbergebnisses.
    """
    grenze = max_points(budget_seconds)
    try:
        import desi_layer9 as _l9
        n = core.count(_l9.ObjectType.CLAIM)
    except Exception:  # noqa: BLE001 - fail-open wie der Rest dieses Moduls
        n = 0
    if n > grenze:
        return {"available": False, "agenda": [],
                "skipped": (f"{n} Claims ueberschreiten die Punktgrenze {grenze} "
                            f"({budget_seconds:.0f}s Budget bei paarweisem Vergleich; "
                            f"{n * (n - 1) // 2:,} Paare waeren noetig)"),
                "n_claims": n, "limit": grenze}
    try:
        from joni.solution_space import navigate_core
    except Exception:  # noqa: BLE001 -> package/optional dep missing: stay silent, never crash a cycle
        return {"available": False, "reason": "solution_space unavailable", "agenda": []}
    try:
        report = navigate_core(core, top=top, allow_model=allow_model, **kw)
    except Exception:  # noqa: BLE001 -> read-only projection must never break the loop
        return {"available": False, "reason": "navigation failed", "agenda": []}
    return {"available": True, **report.to_dict()}


def top_agenda_line(core, **kw) -> str:
    """A one-line human summary of the highest-priority next step (for a loop log).

    Wurde die Navigation wegen ihrer Kosten abgelehnt, steht **das** in der Zeile. Eine leere
    Zeile waere hier das Schlimmste: sie sieht aus wie "nichts zu tun" und heisst in Wahrheit
    "nicht nachgesehen".
    """
    rep = run_navigation(core, **kw)
    if rep.get("skipped"):
        return f"navigation: uebersprungen - {rep['skipped']}"
    agenda = rep.get("agenda") or []
    if not agenda:
        return ""
    a = agenda[0]
    return (f"navigation: {a['kind']} {a['target']} (prio {a['priority']}) "
            f"-> try {a['method_id']} — {a['reason']}")
