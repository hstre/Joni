"""Self-development - how Joni keeps restructuring himself, even at "0 new".

Joni's protected core is frozen, so he does not rewrite his own logic. But his *epistemic*
state is his to organise - through Layer 9, and with the **DESi Semantic Layer** as the
authority on whether two claims actually relate.

The old rule let word-overlap decide ``supports`` vs ``contextualizes``. That is exactly
the interpretation that must not live in Joni. Now:

    lexical overlap (cheap trigger only)
        -> Layer 9 semantic adapter (DESi FrameDetector / LogicalAuditor / FrameTensionRouter)
        -> governed decision: duplicate | supports | complementary | tension | contradictory
           | unrelated | insufficient
        -> Joni acts on the *governed* decision (links, or opens a conflict), never on the
           overlap.

If the Semantic Layer is unavailable the decision is *insufficient* and Joni makes no link -
he never falls back to lexical overlap for a verdict. Every analysis is recorded by Layer 9
as an append-only annotation; the claims are never touched.
"""

from __future__ import annotations

from desi_layer9 import SemanticDecision
from desi_layer9.semantics import adapter, lexical_overlap
from desi_layer9.semantics.ports import NullSemanticLayer

_TRIGGER = 0.3      # cheap lexical trigger; below this we do not even ask the Semantic Layer

#: Zeitbudget des Paardurchlaufs je Zyklus. Wie bei der Navigation folgt die Grenze aus dem
#: Budget und nicht umgekehrt: gemessen 67,4 us je ``lexical_overlap``, bei 3.877 lebenden
#: Claims also 7.513.626 Paare und 8,4 Minuten fuer einen vollen Durchlauf.
DEVELOP_BUDGET_SECONDS = 10.0
_US_PER_PAIR = 67.4e-6


def max_pairs(budget_seconds: float = DEVELOP_BUDGET_SECONDS) -> int:
    """Wie viele Paare in ``budget_seconds`` verglichen werden koennen."""
    return int(budget_seconds / _US_PER_PAIR)


def _semantic_rev() -> str:
    """A tag for the current semantic measure, so a model change re-measures the backlog."""
    try:
        from . import embeddings
        if embeddings.available():
            return embeddings.info()["revision"]
    except Exception:  # noqa: BLE001
        pass
    return "none"


def develop(cs, extensions: dict, proto, cycle: int = 0, *, layer=None,
            max_links: int = 2, max_backfill: int = 3, max_review: int = 5,
            budget_seconds: float = DEVELOP_BUDGET_SECONDS) -> dict:
    """Ein Zyklus Selbstentwicklung - begrenzt auf die *geprueften Paare*, nicht nur die Treffer.

    ``max_links`` deckelte bisher, wie viele Verknuepfungen entstehen, nicht wie viel Arbeit
    dafuer getan wird. Das sieht aus wie eine Grenze und ist keine: bei 3.877 lebenden Claims
    laeuft die Doppelschleife ueber 7.513.626 Paare, solange nicht genug Treffer zusammenkommen -
    gemessen 8,4 Minuten, um hoechstens zwei Verknuepfungen zu finden.

    Statt eines harten Deckels ein **fortsetzbarer Zeiger**: jeder Zyklus prueft so viele Paare,
    wie ins Budget passen, und der naechste macht dort weiter. Ueber rund 51 Zyklen ist ein
    voller Durchlauf beisammen, und keine Claims hungern aus - ein Deckel, der immer vorn
    anfaengt, haette die hinteren nie erreicht. Am Ende eines Durchlaufs faengt der Zeiger von
    vorn an, damit neue Claims mitkommen.

    Was uebersprungen wurde, steht im Protokoll. Ein stiller Teildurchlauf saehe aus wie
    "nichts gefunden" und hiesse "nicht zu Ende gesucht".
    """
    layer = layer or NullSemanticLayer()
    rev = _semantic_rev()
    linked = set(extensions.get("linked", []))
    annotated = set(extensions.get("semantic_backfilled", []))   # "pair@rev" with a semantic record
    live = sorted(cs.active_claims(), key=lambda c: c.id)

    budget = max_pairs(budget_seconds)
    # Da weitermachen, wo der letzte Zyklus aufgehoert hat. Der Zeiger ist eine Claim-ID und
    # keine Position: die Liste aendert sich zwischen Zyklen, eine Zahl waere danach falsch.
    weiter_ab = extensions.get("develop_cursor") or ""
    start = next((i for i, c in enumerate(live) if c.id > weiter_ab), 0) if weiter_ab else 0

    new_links = 0
    geprueft = 0
    erschoepft = False
    zuletzt = weiter_ab
    for i in range(start, len(live)):
        a = live[i]
        if new_links >= max_links:
            break
        if geprueft >= budget:
            erschoepft = True
            break
        zuletzt = a.id
        for b in live[i + 1:]:
            if a.topic != b.topic or a.topic == "":
                continue
            key = f"{a.id}|{b.id}"
            if key in linked:
                continue
            geprueft += 1
            trigger = lexical_overlap(a.text, b.text)
            if trigger < _TRIGGER:
                continue                                  # cheap trigger only - never a verdict
            sc = adapter.analyse_pair(cs.core, a, b, layer=layer, lexical_trigger=trigger,
                                      run_id=f"joni-c{cycle}")
            linked.add(key)
            annotated.add(f"{key}@{rev}")                 # measured under this semantic rev
            acted = _act_on(cs, proto, cycle, a, b, sc)
            new_links += acted
            if acted:
                break

    if erschoepft:
        extensions["develop_cursor"] = zuletzt
        proto.record(cycle, "developed",
                     f"Paardurchlauf begrenzt: {geprueft} Paare geprueft ({budget_seconds:.0f}s "
                     f"Budget), weiter ab {zuletzt} - noch nicht der ganze Bestand gesehen")
    else:
        # Durchlauf komplett: von vorn, damit neu hinzugekommene Claims mitkommen.
        extensions["develop_cursor"] = ""
    extensions["linked"] = sorted(linked)[-1000:]

    backfilled = _backfill_legacy(cs, extensions, proto, cycle, linked, annotated, layer,
                                  max_backfill, rev)

    reviewed = 0
    for x in cs.core.open_conflicts():
        if reviewed >= max_review:                        # bounded per cycle, like every other step
            break
        if x.conflict_status.value == "open":
            cs.review_conflict(x.id)
            reviewed += 1
            proto.record(cycle, "developed", f"opened review of contradiction {x.id}")

    return {"links": new_links, "conflicts_reviewed": reviewed, "backfilled": backfilled,
            "pairs_examined": geprueft, "budget_exhausted": erschoepft,
            "cursor": extensions.get("develop_cursor", "")}


def _backfill_legacy(cs, extensions, proto, cycle, linked, done, layer, limit, rev) -> int:
    """Give already-linked pairs a Layer-9 semantic record under the current measure.

    The backlog was linked by lexical overlap under the old logic - with no governed
    semantic decision. We retroactively run the Semantic Layer over a few each cycle
    (append-only; the old link is not altered, but a contradiction/tension it now sees is
    opened honestly). Deduped by ``pair@rev`` so a *new* semantic measure (e.g. the
    embedding model coming online) re-measures the backlog once; then it goes quiet."""
    by_id = {c.id: c for c in cs.active_claims()}
    n = 0
    for key in sorted(linked):
        if n >= limit:
            break
        tag = f"{key}@{rev}"
        if tag in done:
            continue
        a_id, _, b_id = key.partition("|")
        a, b = by_id.get(a_id), by_id.get(b_id)
        if a is None or b is None:
            done.add(tag)                                 # not both live anymore - skip
            continue
        sc = adapter.analyse_pair(cs.core, a, b, layer=layer, run_id=f"joni-c{cycle}-bf")
        done.add(tag)
        n += 1
        if sc.decision.value in ("contradictory", "tension"):
            from .qualify import qualify_conflict
            sev = "hard" if sc.decision.value == "contradictory" else "soft"
            ck = qualify_conflict(a.text, b.text, severity=sev,
                                  contradictory=(sc.decision.value == "contradictory"))
            cid = cs.open_conflict((a_id, b_id), severity=sev, conflict_kind=ck)
            proto.record(cycle, "developed",
                         f"backfill: {a_id}/{b_id} {ck} -> {cid}")
        else:
            proto.record(cycle, "developed",
                         f"backfill: {a_id}/{b_id} semantic record = {sc.decision.value}")
    extensions["semantic_backfilled"] = sorted(done)[-4000:]
    return n


def _act_on(cs, proto, cycle, a, b, sc) -> int:
    """Act on Layer 9's governed decision. Returns 1 if a link was drawn, else 0."""
    d = sc.decision
    src = f"DESi {sc.semantic_layer}@{sc.semantic_layer_version}"
    if d is SemanticDecision.SUPPORTS:
        cs.corroborate(a.id, b, relation="supports")
        proto.record(cycle, "developed", f"linked {a.id} <-> {b.id} (supports · {src})")
        return 1
    if d is SemanticDecision.COMPLEMENTARY:
        cs.corroborate(a.id, b, relation="contextualizes")
        proto.record(cycle, "developed", f"linked {a.id} <-> {b.id} (complementary · {src})")
        return 1
    if d is SemanticDecision.CONTRADICTORY:
        from .qualify import qualify_conflict
        ck = qualify_conflict(a.text, b.text, severity="hard", contradictory=True)
        cid = cs.open_conflict((a.id, b.id), severity="hard", conflict_kind=ck)
        proto.record(cycle, "developed", f"{src}: {a.id} vs {b.id} {ck} -> {cid}")
        return 0
    if d is SemanticDecision.TENSION:
        from .qualify import qualify_conflict
        ck = qualify_conflict(a.text, b.text, severity="soft")
        cid = cs.open_conflict((a.id, b.id), severity="soft", conflict_kind=ck)
        proto.record(cycle, "developed", f"{src}: frame tension {a.id}/{b.id} ({ck}) -> {cid}")
        return 0
    # duplicate / unrelated / insufficient: recorded by Layer 9, no link asserted.
    proto.record(cycle, "developed", f"{a.id}/{b.id}: {d.value} - no link ({src})")
    return 0
