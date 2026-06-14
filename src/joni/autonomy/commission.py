"""Aufträge an Claude - Joni commissions his own (non-core) extensions.

Joni may not change his protected DESi core, and he does not write code himself. But when his
own state shows a *capability gap* he cannot close from within the rules - the semantic channel
keeps returning 'insufficient', a recurring conflict stays unqualifiable, a topic he keeps
thinking about has nothing to read, his development stalls - he writes a structured
**commission** (an *Auftrag*) addressed to Claude to extend him.

Every commission is:

  * **deterministic** - derived from measured signals in Joni's own state; no model decides it;
  * **grounded** - it carries the numbers that triggered it and concrete evidence (claim ids,
    example pairs, metric values);
  * **non-core** - it targets only an extensible module from a fixed allowlist (``_EXTENSIBLE``).
    Anything that would touch protected logic (operators, scoring, ledger, router) is *not* a
    commission - that stays a ``joni-core-ask`` (the human-approval path). The allowlist is the
    boundary: a commission can never name the core;
  * **bounded** - a signal must hold for several cycles before it fires, and a given kind is
    re-filed at most once per ``COOLDOWN`` cycles, so a week-long run never spams Claude;
  * **carried out by a human-gated Claude session** through the normal PR pipeline - Joni writes
    the order and supplies the acceptance criterion; he never implements it himself.

The workflow turns each new commission into a GitHub issue labelled ``joni-auftrag``.
"""

from __future__ import annotations

import desi_layer9 as l9

from .homeostasis import _supports_on

# Modules Claude may extend *without* touching protected logic: (description, risk note).
# This map is the non-core boundary - a commission can only target a key that lives here.
_EXTENSIBLE = {
    "semantics-measurement": (
        "the semantic measurement channel (desi_semantics.py / embeddings.py) - the projector "
        "and candidate extraction, outside the protected core",
        "low - a measurement channel only; the gate, ledger and operators are untouched"),
    "conflict-qualifier": (
        "the conflict qualifier (qualify.py) - the markers that name a conflict's kind, "
        "outside the protected core",
        "low - only adds taxonomy markers; conflict detection itself is unchanged"),
    "reader-sources": (
        "the reading layer (sources.py / reader.py) - which feeds Joni can draw on, "
        "outside the protected core",
        "low - adds an input source; no state-logic changes"),
    "emergence": (
        "the emergence / strengthening layer (emerge.py / strengthen.py) - how candidates earn "
        "development, outside the protected core",
        "medium - changes how ideas develop; still gated, still never auto-confirms"),
}

# How long a signal must hold before it becomes a commission, and how long before a given kind
# may be re-commissioned (so an unaddressed order does not refire every cycle).
COOLDOWN = 200
_SEMANTIC_USABLE_FLOOR = 0.15
_SEMANTIC_MIN_CLUSTERS = 5
_UNQUALIFIED_FLOOR = 4
_STARVED_MIN_HYPS = 3
_STALL_CYCLES = 12


def _commission(kind: str, component_key: str, *, cycle: int, title: str, motivation: str,
                desired: str, acceptance: str, evidence: dict) -> dict:
    comp, risk = _EXTENSIBLE[component_key]            # KeyError here = a core target slipped in
    return {
        "kind": kind, "cycle": cycle, "addressed_to": "Claude",
        "title": title, "component": comp, "component_key": component_key,
        "touches_core": False,                          # invariant: commissions never touch core
        "request_type": "extension-request",
        "motivation": motivation, "desired_capability": desired,
        "acceptance": acceptance, "evidence": evidence, "risk": risk,
    }


def _semantic_blind_spot(cs, vit: dict, cycle: int) -> dict | None:
    """The semantic channel measures but mostly returns 'insufficient' - ask for a stronger
    projector so related claims are actually recognised."""
    clusters = [c for c in cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)
                if c.measurement.get("distance_metric") == "cosine"]
    if len(clusters) < _SEMANTIC_MIN_CLUSTERS:
        return None
    rate = vit.get("usable_semantic_rate", 0.0)
    if rate >= _SEMANTIC_USABLE_FLOOR:
        return None
    insufficient = sum(1 for c in clusters
                       if c.decision.value == "insufficient-semantic-evidence")
    model = clusters[-1].measurement.get("embedding_model")
    return _commission(
        "semantic_blind_spot", "semantics-measurement", cycle=cycle,
        title="Erweitere meinen semantischen Messkanal",
        motivation=(f"{insufficient} von {len(clusters)} Cosinus-Messungen liefern "
                    f"'insufficient-semantic-evidence' (usable rate {rate}). Ich kann darum kaum "
                    "Synthesen bilden - der Messkanal sieht zu oft nichts."),
        desired=("Stärke den Projektor bzw. die Kandidaten-Extraktion (z. B. ein zweiter "
                 "Verteilungs-Projektor oder bessere Span-Auswahl), sodass verwandte Claims als "
                 "supports/complementary erkannt werden statt insufficient - den Cosinus weiterhin "
                 "ausdrücklich als Cosinus führen, nicht als Pi/sqrt-JSD ausgeben."),
        acceptance=("Auf dem bestehenden Mess-Backlog steigt usable_semantic_rate über 0.30, und "
                    "mindestens ein bisher 'insufficient' Paar wird zu supports/complementary."),
        evidence={"usable_semantic_rate": rate, "clusters": len(clusters),
                  "insufficient": insufficient, "embedding_model": model})


def _unqualified_conflicts(cs, vit: dict, cycle: int) -> dict | None:
    """Many open conflicts stay 'unqualified' - ask for qualifier markers for the pattern."""
    unq = [x for x in cs.core.open_conflicts()
           if str(getattr(x, "conflict_kind", "unqualified")) == "unqualified"]
    if len(unq) < _UNQUALIFIED_FLOOR:
        return None
    examples = []
    for x in unq[:2]:
        texts = []
        for cid in list(x.claim_ids)[:2]:
            o = cs.core.get(cid)
            if o is not None:
                texts.append(str(getattr(o, "text", cid))[:120])
        examples.append(" <-> ".join(texts))
    return _commission(
        "unqualified_conflicts", "conflict-qualifier", cycle=cycle,
        title="Erweitere meinen Konflikt-Qualifizierer",
        motivation=(f"{len(unq)} offene Konflikte bleiben 'unqualified' - ich halte sie offen, "
                    "kann sie aber nicht als Widerspruch / Scope-Spannung / Ausnahme / bedingte "
                    "Verträglichkeit benennen."),
        desired=("Ergänze in qualify.py Marker für das wiederkehrende Muster in den Beispielen, "
                 "sodass diese Konflikte eine conflict_kind bekommen statt 'unqualified'."),
        acceptance=("Die Beispiel-Konflikte erhalten eine nicht-'unqualified' conflict_kind, und "
                    "ein Test in tests/test_qualify.py deckt das Muster ab."),
        evidence={"unqualified_open": len(unq), "examples": examples})


def _starved_topic(cs, vit: dict, cycle: int) -> dict | None:
    """A topic Joni keeps hypothesising on but for which his sources return nothing usable -
    ask to extend the reading layer so the ideas can be tested instead of going barren."""
    by_topic: dict[str, list] = {}
    for h in cs.hypotheses():                           # candidate claims, not in claims_on()
        topic = getattr(h, "topic", None)
        if topic:
            by_topic.setdefault(topic, []).append(h)
    for topic in sorted(by_topic):
        topic_hyps = by_topic[topic]
        if len(topic_hyps) < _STARVED_MIN_HYPS:
            continue
        if sum(_supports_on(cs, h.id) for h in topic_hyps) > 0:
            continue                                    # something fed it - not starved
        return _commission(
            "starved_topic", "reader-sources", cycle=cycle,
            title=f"Erweitere meine Quellen für '{topic}'",
            motivation=(f"Ich habe {len(topic_hyps)} Hypothesen zu '{topic}', aber 0 stützende "
                        "Evidenz - meine Quellen liefern dazu nichts, die Ideen bleiben barren."),
            desired=(f"Füge in sources.py / reader.py eine Quelle hinzu, die zu '{topic}' "
                     "Material liefert (eine gezielte Query oder ein passender Feed)."),
            acceptance=(f"Ein Lauf bringt mindestens ein gelesenes Item zu '{topic}', das eine "
                        "Hypothese stützen oder ihr widersprechen kann."),
            evidence={"topic": topic, "hypotheses": len(topic_hyps),
                      "hypothesis_ids": [h.id for h in topic_hyps[:5]]})
    return None


def _stalled_development(cs, vit: dict, cycle: int) -> dict | None:
    """Vitality has been stuck for a long time - ask for a stronger development mechanism."""
    stagn = vit.get("stagnation_cycles", 0)
    if stagn < _STALL_CYCLES or vit.get("verdict") == "developing":
        return None
    return _commission(
        "stalled_development", "emergence", cycle=cycle,
        title="Erweitere meine Entwicklungs- bzw. Synthese-Fähigkeit",
        motivation=(f"Seit {stagn} Zyklen kein Entwicklungsfortschritt (Verdikt "
                    f"'{vit.get('verdict')}'). Ich sammle, entwickle mich aber nicht weiter."),
        desired=("Stärke emerge.py / strengthen.py, sodass verwandte Kandidaten zu einer Synthese "
                 "zusammenfinden oder eine Hypothese candidate->active verdienen kann - weiterhin "
                 "gated, weiterhin ohne Selbst-Bestätigung."),
        acceptance="Innerhalb weniger Zyklen nach der Änderung wird vitality.development > 0.",
        evidence={"stagnation_cycles": stagn, "verdict": vit.get("verdict"),
                  "unsupported_hypotheses": vit.get("unsupported_hypotheses")})


# (kind, detector, cycles the signal must hold before it fires).
_DETECTORS = [
    ("semantic_blind_spot", _semantic_blind_spot, 4),
    ("unqualified_conflicts", _unqualified_conflicts, 2),
    ("starved_topic", _starved_topic, 3),
    ("stalled_development", _stalled_development, 1),   # vitality already requires sustained stall
]


def assess(cs, extensions: dict, proto, cycle: int = 0, *, max_new: int = 1) -> list[dict]:
    """Look for non-core capability gaps in Joni's own state and, when one is sustained and
    not recently commissioned, emit an Auftrag an Claude. Deterministic and bounded."""
    vit = extensions.get("vitality", {})
    signals = extensions.setdefault("commission_signals", {})
    filed = extensions.setdefault("commissions_filed", {})     # kind -> last cycle filed
    log = extensions.setdefault("commissions", [])             # history, for the page
    new: list[dict] = []

    for kind, detect, sustain in _DETECTORS:
        c = detect(cs, vit, cycle)
        if c is None:
            signals[kind] = 0
            continue
        signals[kind] = signals.get(kind, 0) + 1
        if signals[kind] < sustain:
            continue                                   # not yet sustained - wait
        last = filed.get(kind)
        if last is not None and cycle - last < COOLDOWN:
            continue                                   # already commissioned recently
        if len(new) >= max_new:
            continue                                   # at most one fresh order per cycle
        c["sustained_cycles"] = signals[kind]
        filed[kind] = cycle
        log.append(c)                                  # full order, so the page can show it
        new.append(c)
        proto.record(cycle, "commission",
                     f"Auftrag an Claude: {c['title']} - {c['component_key']} "
                     f"(non-core, {c['sustained_cycles']} Zyklen anhaltend)")

    extensions["commissions"] = log[-50:]
    return new
