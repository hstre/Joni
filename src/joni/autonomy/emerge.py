"""Emergent self-development - Joni deriving new structure from his *own* accumulated net.

The pairwise ``invent`` move is shallow: it bridges two topics and stops. This goes
deeper - it reads recurring patterns across everything Joni has learned and lets real
structure precipitate out of them. Three moves, each grounded in a *recurrence* (not a
single observation), each through the gate, none faking authority:

  * **emergent topic** - a content term that keeps recurring across many claims spanning
    several different topics is promoted to a topic Joni tracks in its own right;
  * **emergent synthesis** - when >=3 claims on one topic share a through-line term, Joni
    mints a higher-order *candidate* claim abstracting that cluster - **but only if Layer 9
    (via the DESi Semantic Layer) marks the cluster ``synthesis-eligible``**. Lexical
    recurrence is just the trigger; it never decides the claims belong together;
  * **emergent method** - a term that recurs across >=2 different topics is offered to
    Kevin as a *candidate method* - again **only after** a synthesis-eligible decision.

The lexical recurrence is a cheap candidate generator. The judgement that the underlying
claims are semantically compatible is the Semantic Layer's, governed by Layer 9. Each move
fires at most once per cycle, deduped; when the Semantic Layer is unavailable the cluster
is *insufficient* and no synthesis/method is produced.
"""

from __future__ import annotations

from collections import defaultdict

from desi_layer9 import SemanticDecision, SemanticState
from desi_layer9.semantics import adapter
from desi_layer9.semantics.ports import NullSemanticLayer

from ..conflict import _content
from . import quality, term_judge, topic_review

# Structural / meta words from Joni's own generated text - never a real emergent topic.
_META = frozenset({
    "topic", "track", "tracking", "tracked", "worth", "pattern", "behind", "might",
    "apply", "applies", "hypothesis", "claim", "claims", "across", "also", "using",
    "based", "approach", "paper", "study", "studies", "method", "methods", "model",
    "models", "system", "systems", "data", "results", "this", "that", "with", "from",
    "show", "open", "source", "github", "arxiv", "through", "line", "recurs", "recurring",
})

_MIN_CLAIMS = 3          # a term must recur across at least this many claims
# ...spanning at least this many topics to become a topic. Was 2 - which minted one generic
# word per cycle ('against', 'allowing', 'aimed'): virtually the entire junk-topic graveyard
# was born at exactly 2. A real concept recurs wider before it deserves tracking.
_MIN_TOPICS_FOR_TOPIC = 3
_MIN_TOPICS_FOR_METHOD = 2   # ...or to be a transferable lens (an emergent method)
_MAX_INSUFFICIENT_RETRIES = 3   # a layer-absent non-judgment is retried this often, not burned


def _is_synthetic(text: str) -> bool:
    """A claim Joni generated about his own bookkeeping - excluded from the vocabulary."""
    t = text.lower()
    return (t.startswith("hypothesis:") or t.startswith("across my")
            or "is a topic i track" in t or "is worth tracking" in t
            or "keeps recurring" in t)


# A synthesis resting solely on a semantic sink (a drain topic) is undifferentiated - never a real
# through-line. Mirrors the collapse-panel sink set.
_SINK_TOPICS = frozenset({"forum", "misc", "unknown", "unsorted", "gatemem", "assess"})
_EXTERNAL_SOURCE_KINDS = frozenset({"web", "paper", "dataset", "document", "observation"})


def _source_family(src) -> str | None:
    """An independent external source-family key (the uri host, else the id), or None if the source
    is internal (a conversation / self-reference / no external uri)."""
    import re
    kind = str(getattr(src, "kind", "") or "")
    uri = str(getattr(src, "uri", "") or "")
    if kind not in _EXTERNAL_SOURCE_KINDS and "://" not in uri:
        return None
    m = re.search(r"://([^/]+)", uri)
    if m:
        host = m.group(1).lower()
        return host[4:] if host.startswith("www.") else host
    return uri or str(getattr(src, "id", "")) or None


def _claim_family_index(cs) -> tuple[dict, bool]:
    """claim_id -> set of independent external source families, and whether the graph exposes ANY
    Source objects at all. If it does not, the family gate fails OPEN (cannot judge unseen data)."""
    import desi_layer9 as l9
    sources = {s.id: s for s in cs.core.all(l9.ObjectType.SOURCE)}
    evidence = {e.id: e for e in cs.core.all(l9.ObjectType.EVIDENCE)}
    idx: dict[str, set] = defaultdict(set)
    for el in cs.core.all(l9.ObjectType.EVIDENCE_LINK):
        cid = getattr(el, "claim_id", None)
        if not cid:
            continue
        ev = evidence.get(getattr(el, "evidence_id", None))
        src = sources.get(getattr(ev, "source_id", None)) if ev is not None else None
        fam = _source_family(src) if src is not None else None
        if fam:
            idx[cid].add(fam)
    return idx, bool(sources)


def _live_conflict_pairs(cs) -> set:
    """Unordered claim-id pairs currently in a LIVE (open/under_review) conflict - two claims that
    contradict each other cannot be a 'majority-compatible' cluster to synthesise over."""
    pairs: set = set()
    for cf in cs.core.open_conflicts():
        ids = [str(x) for x in (getattr(cf, "claim_ids", None) or [])]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pairs.add(frozenset((ids[i], ids[j])))
    return pairs


def _term_index(claims) -> dict[str, dict]:
    """term -> {topics: set, claims: list[claim]} over real (non-synthetic) claims."""
    idx: dict[str, dict] = defaultdict(lambda: {"topics": set(), "claims": []})
    for c in claims:
        if not c.topic or _is_synthetic(c.text):
            continue
        for w in _content(c.text):
            if w in _META or not quality.is_meaningful_term(w):
                continue                        # quality gate: no stopwords / artifact tokens
            entry = idx[w]
            entry["topics"].add(c.topic)
            entry["claims"].append(c)
    return idx


def _eligible_cluster(cs, proto, cycle, claims, *, layer, surface_term):
    """Run the Layer-9 semantic adapter over a group; return the recorded SemanticCluster.
    Joni only proceeds if it comes back ``synthesis-eligible`` - he never decides this."""
    sc = adapter.analyse_cluster(cs.core, claims, layer=layer, surface_term=surface_term,
                                 run_id=f"joni-c{cycle}")
    if sc.semantic_state is not SemanticState.SYNTHESIS_ELIGIBLE:
        proto.record(cycle, "emerged",
                     f"'{surface_term}' cluster not synthesised: Layer 9 says "
                     f"{sc.decision.value} ({sc.semantic_state.value})")
    return sc


def emerge(cs, extensions: dict, proto, cycle: int = 0, *, layer=None,
           budget=None, runs_per_week: int = 0) -> dict:
    layer = layer or NullSemanticLayer()
    live = cs.active_claims()
    idx = _term_index(live)
    known_topics = set(cs.topics())
    out = {"topic": None, "synthesis": 0, "method": None, "pattern_hints": 0}
    # a Layer-9 non-judgment (layer absent/invalid) must not permanently consume a cluster
    insuff = dict(extensions.get("emerge_insufficient", {}))

    # -- 1. emergent topic: a cross-topic recurring term becomes a tracked topic -------- #
    done_topics = set(extensions.get("emerged_topics", []))
    cands = sorted(
        ((t, e) for t, e in idx.items()
         if t not in known_topics and t not in done_topics
         and len(e["claims"]) >= _MIN_CLAIMS and len(e["topics"]) >= _MIN_TOPICS_FOR_TOPIC),
        key=lambda kv: (-len(kv[1]["claims"]), kv[0]))
    cands = [(t, e) for t, e in cands if quality.on_domain(t)]   # domain-consistency gate
    # In-doubt term-judge (OFF by default): veto only the winning term; burn it so it is not
    # re-judged next cycle. A None/True verdict, or a disabled/over-budget judge, keeps the rule.
    while cands and term_judge.enabled() and \
            term_judge.judge(cands[0][0], budget=budget, cycle=cycle) is False:
        done_topics.add(cands[0][0])
        proto.record(cycle, "emerged",
                     f"emergent topic '{cands[0][0]}' vetoed by the term-judge in doubt; dropped")
        cands = cands[1:]
    if cands:
        term, e = cands[0]
        # Symmetry with moves 2 and 3: no structure without a semantic judgment. Lexical
        # recurrence + on_domain cannot tell a concept ('calibration') from a generic word
        # ('against') - the Granite topic gatekeeper can, and it judges BEFORE the mint, not
        # after ('against' at 1 claim never reached the post-hoc review). Non-authoritative:
        # an invalid verdict only withholds the mint; a no-verdict (gate off mid-run, call
        # failed) leaves the candidate unburned for a later cycle. Gate disabled -> the
        # lexical-only mode mints as before.
        verdict = (topic_review.judge_term(term, [c.text for c in e["claims"]],
                                           extensions=extensions, cycle=cycle,
                                           budget=budget, runs_per_week=runs_per_week)
                   if topic_review.enabled() else True)
        if verdict is False:
            done_topics.add(term)               # a real verdict: not a concept, never re-asked
            proto.record(cycle, "emerged",
                         f"topic candidate '{term}' rejected by the topic gate - not minted")
        elif verdict is True:
            cs.learn(f"'{term}' keeps recurring across {len(e['topics'])} of my topics, "
                     f"so I am tracking it as its own topic.", term)
            done_topics.add(term)
            minted = dict(extensions.get("emerged_topic_cycle", {}))
            minted[term] = cycle                # mint age: the orphan drain's grace period
            extensions["emerged_topic_cycle"] = dict(sorted(minted.items())[-2000:])
            out["topic"] = term
            proto.record(cycle, "emerged",
                         f"new topic '{term}' precipitated from a recurrence across "
                         f"{', '.join(sorted(e['topics']))}")
    extensions["emerged_topics"] = sorted(done_topics)

    # -- 2. emergent synthesis: a within-topic cluster -> a higher-order candidate ------ #
    done_syn = set(extensions.get("synthesized", []))
    made_syn = 0
    made_hints = 0
    by_topic_term: dict[tuple, list] = defaultdict(list)
    for c in live:
        if not c.topic or _is_synthetic(c.text):
            continue
        for w in _content(c.text):
            if w not in _META and quality.is_meaningful_term(w):
                by_topic_term[(c.topic, w)].append(c)
    # Minimum conditions for a synthesis to be worth judging (operator point 3), built once:
    # independent external grounding and no live intra-cluster contradiction. A synthesis must not
    # rest on token-recurrence + embedding-proximity alone.
    fam_idx, have_sources = _claim_family_index(cs)
    live_pairs = _live_conflict_pairs(cs)
    for (topic, term), cluster in sorted(by_topic_term.items(),
                                         key=lambda kv: (-len(kv[1]), kv[0])):
        if made_syn:
            break
        key = f"{topic}|{term}"
        if key in done_syn or len(cluster) < _MIN_CLAIMS:
            continue
        if topic in _SINK_TOPICS:
            done_syn.add(key)
            continue                            # a sink topic is not a real basis for synthesis
        if not quality.on_domain(term) or not quality.is_good_topic(term):
            done_syn.add(key)
            continue                            # off-domain / a name, slug or title fragment
        # >=2 independent EXTERNAL source families across the cluster (fail-open only if the graph
        # exposes no Source objects at all). Not burned: the cluster may gain sources later.
        if have_sources:
            fams: set = set()
            for c in cluster:
                fams |= fam_idx.get(c.id, set())
            if len(fams) < 2:
                continue
        # majority-compatible: no two cluster claims may be in a live contradiction. Not burned:
        # the conflict may later resolve.
        cids = [c.id for c in cluster]
        if any(frozenset((cids[i], cids[j])) in live_pairs
               for i in range(len(cids)) for j in range(i + 1, len(cids))):
            continue
        # in-doubt term-judge before minting a synthesis (OFF by default), like topics and methods
        if term_judge.enabled() and term_judge.judge(term, budget=budget, cycle=cycle) is False:
            done_syn.add(key)
            continue
        if insuff.get(key, 0) >= _MAX_INSUFFICIENT_RETRIES:
            done_syn.add(key)                               # several fair chances - finalise
            insuff.pop(key, None)
            continue
        sc = _eligible_cluster(cs, proto, cycle, cluster, layer=layer, surface_term=term)
        if sc.decision is SemanticDecision.INSUFFICIENT:
            insuff[key] = insuff.get(key, 0) + 1            # a non-judgment: retry on a later cycle
            continue
        done_syn.add(key)                                   # a real Layer-9 decision was rendered
        insuff.pop(key, None)
        if sc.semantic_state is not SemanticState.SYNTHESIS_ELIGIBLE:
            continue                                        # Layer 9 did not clear it
        parents = tuple(sorted(c.id for c in cluster))[:5]
        text = (f"Across my {topic} claims, the term '{term}' recurs; whether this reflects a "
                "shared mechanism remains untested.")
        # Priority 3, at the source: a bare recurrence observation is a *pattern hint*, not a
        # hypothesis. If it would be barred from reflection anyway, do NOT mint it as a candidate
        # claim (that is what floods the graph and the 'hypotheses' with lexical recurrence) -
        # record it as a hint. A future non-recurrence synthesis (well-formed) would still mint.
        from . import hypothesis_form
        if hypothesis_form.is_reflection_barred(text):
            made_hints += 1
            out["pattern_hints"] = made_hints
            extensions.setdefault("emerge_pattern_hints", []).append(
                {"topic": topic, "term": term, "parents": list(parents)})
            proto.record(cycle, "pattern_hint",
                         f"recurrence on {topic}: '{term}' - held as a pattern hint, not minted "
                         "as a hypothesis (lexical recurrence)")
            continue
        cs.hypothesize(text, topic, parents=parents)
        made_syn += 1
        out["synthesis"] = made_syn
        proto.record(cycle, "emerged",
                     f"synthesis on {topic}: '{term}' (Layer 9 synthesis-eligible, "
                     f"{sc.id}) from {len(cluster)} claims ({', '.join(parents)})")
    extensions["synthesized"] = sorted(done_syn)[-500:]

    # -- 3. emergent method: a cross-topic lens stored as a candidate for Kevin --------- #
    done_meth = set(extensions.get("emerged_methods", []))
    lenses = sorted(
        ((t, e) for t, e in idx.items()
         if t not in done_meth and len(e["topics"]) >= _MIN_TOPICS_FOR_METHOD
         and len(e["claims"]) >= _MIN_CLAIMS),
        key=lambda kv: (-len(kv[1]["topics"]), -len(kv[1]["claims"]), kv[0]))
    # A lens term must be a real, on-domain, non-sink concept - the same bar the synthesis move
    # applies. Blocks garbage/sink lens terms (gatemem, a proper name, a slug) at the source.
    lenses = [(t, e) for t, e in lenses
              if t not in _SINK_TOPICS and quality.is_good_topic(t) and quality.on_domain(t)]
    # In-doubt term-judge (OFF by default): veto only the winning lens term before it is minted
    # as an '<term>-as-a-lens' method; burn a vetoed term. Fails to the rule when unavailable.
    while lenses and term_judge.enabled() and \
            term_judge.judge(lenses[0][0], budget=budget, cycle=cycle) is False:
        done_meth.add(lenses[0][0])
        proto.record(cycle, "emerged",
                     f"method candidate '{lenses[0][0]}-as-a-lens' vetoed by the term-judge in "
                     "doubt (not a genuine transferable concept); dropped, not minted")
        lenses = lenses[1:]
    if lenses:
        term, e = lenses[0]
        topics = tuple(sorted(e["topics"]))
        mkey = f"meth:{term}"
        if insuff.get(mkey, 0) >= _MAX_INSUFFICIENT_RETRIES:
            done_meth.add(term)                             # several fair chances - finalise
            insuff.pop(mkey, None)
        else:
            # Kevin only receives a method after Layer 9 marks the cluster synthesis-eligible.
            sc = _eligible_cluster(cs, proto, cycle, e["claims"][:6], layer=layer,
                                   surface_term=term)
            if sc.decision is SemanticDecision.INSUFFICIENT:
                insuff[mkey] = insuff.get(mkey, 0) + 1      # a non-judgment: retry on a later cycle
            else:
                done_meth.add(term)                         # a real Layer-9 decision was rendered
                insuff.pop(mkey, None)
                if sc.semantic_state is SemanticState.SYNTHESIS_ELIGIBLE:
                    cs.propose_method(
                        name=f"{term}-as-a-lens",
                        summary=(
                            f"'{term}' recurs across {', '.join(topics)} in my own "
                            "evidence; treat it as a transferable lens and read a new "
                            "problem through it."
                        ),
                        applicable_to=topics, origin="joni:emergent")
                    out["method"] = term
                    proto.record(cycle, "emerged",
                                 f"method candidate for Kevin: '{term}-as-a-lens' (Layer 9 "
                                 f"synthesis-eligible, {sc.id}) across {', '.join(topics)}")
    extensions["emerged_methods"] = sorted(done_meth)
    extensions["emerge_insufficient"] = dict(sorted(insuff.items())[-1000:])

    return out
