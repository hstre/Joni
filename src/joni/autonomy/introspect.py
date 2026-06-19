"""Joni's self-diagnostic: what isn't working yet, and how he could function better.

Every self-review Joni now asks the one question that actually drives improvement: *what is keeping
me from functioning optimally, and how could it be fixed?* From his own MEASURED state he derives
concrete weaknesses, each with a direction to improve, a search query, and the non-core module it
points at. Those queries flow into his **topic search** (so he reads about his own bottlenecks, not
just his topics) and the top weakness **steers Doktores** to scout that module next - turning the
review from a static report into the engine of his self-improvement.

Purely deterministic, from measured signals; it only proposes (queries + a steer). Nothing here
confirms, promotes or changes the protected core - the gated pipeline still decides everything.
"""

from __future__ import annotations

from . import reader


def diagnose(cs, extensions: dict) -> list[dict]:
    """Derive Joni's current self-improvement findings from his measured state. Each finding:
    ``{issue, improve, query, module}``. Bounded, ordered by how much it blocks progress."""
    vit = extensions.get("vitality", {}) if isinstance(extensions.get("vitality"), dict) else {}
    findings: list[dict] = []

    if vit.get("development", 0) == 0 and vit.get("stagnation_cycles", 0) >= 2:
        findings.append({
            "issue": "Ich entwickle meine Ideen kaum weiter (development 0, degenerating).",
            "improve": "Verwandte Kandidaten zu Synthesen verbinden und Hypothesen mit Evidenz "
                       "stützen, damit sie candidate→active reifen können.",
            "query": "automated hypothesis development scientific synthesis",
            "module": "emergence"})

    rate = vit.get("usable_semantic_rate", 1.0)
    if isinstance(rate, (int, float)) and rate < 0.30:
        findings.append({
            "issue": f"Mein semantischer Messkanal ist schwach (nutzbare Rate {rate}).",
            "improve": "Bessere Ähnlichkeits-/Projektionsmessung, damit verwandte Claims als "
                       "stützend/komplementär erkannt werden statt 'insufficient'.",
            "query": "semantic textual similarity sentence embeddings",
            "module": "semantics-measurement"})

    starved = reader.starved_topics(cs)
    if starved:
        findings.append({
            "issue": f"{len(starved)} Topics, auf denen ich denke, haben keine stützende Evidenz: "
                     f"{', '.join(starved[:4])}.",
            "improve": "Gezielt Quellen zu genau diesen Topics suchen, damit die Ideen testbar "
                       "werden statt barren zu bleiben.",
            "query": " ".join(starved[:3]), "module": "reader-sources"})

    unq = [x for x in cs.core.open_conflicts()
           if str(getattr(x, "conflict_kind", "unqualified")) == "unqualified"]
    if len(unq) >= 4:
        findings.append({
            "issue": f"{len(unq)} offene Konflikte bleiben 'unqualified' - ihre Art unklar "
                     "benennen.",
            "improve": "Konfliktarten besser markieren (Widerspruch vs. Scope-Spannung vs. "
                       "Ausnahme).",
            "query": "contradiction detection natural language inference",
            "module": "conflict-qualifier"})

    if vit.get("stagnation_cycles", 0) >= 5:
        findings.append({
            "issue": "Die Feeds liefern mir nichts genuin Neues mehr (Sättigung).",
            "improve": "Quellen-Vielfalt erhöhen, neue Anfragen aus offenen Fragen bilden.",
            "query": "open problems autonomous research agents self-improvement",
            "module": "reader-sources"})

    return findings[:4]


def apply(cs, extensions: dict, proto, cycle: int = 0) -> dict:
    """Run the self-diagnostic and let it act: store the findings (for the review), push their
    queries into the topic search (``learned_queries``) and set the top weakness as the steer for
    Doktores' next scout. Returns the findings. Deterministic; proposes only."""
    findings = diagnose(cs, extensions)
    extensions["introspection"] = findings
    if not findings:
        extensions.pop("introspection_module", None)
        return {"findings": 0}

    learned = list(extensions.get("learned_queries", []))
    for f in findings:
        q = (f.get("query") or "").strip()
        if q and q not in learned:
            learned.append(q)
    extensions["learned_queries"] = learned[-12:]        # bounded; the topic search reads these
    extensions["introspection_module"] = findings[0]["module"]    # steer Doktores to the top gap
    proto.record(cycle, "note",
                 f"self-diagnostic: {len(findings)} thing(s) to improve · top: "
                 f"{findings[0]['issue'][:80]} -> searching '{findings[0]['query'][:40]}', "
                 f"steer Doktores at {findings[0]['module']}")
    return {"findings": len(findings)}
