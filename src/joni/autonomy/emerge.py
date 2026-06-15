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
from . import quality

# Structural / meta words from Joni's own generated text - never a real emergent topic.
_META = frozenset({
    "topic", "track", "tracking", "tracked", "worth", "pattern", "behind", "might",
    "apply", "applies", "hypothesis", "claim", "claims", "across", "also", "using",
    "based", "approach", "paper", "study", "studies", "method", "methods", "model",
    "models", "system", "systems", "data", "results", "this", "that", "with", "from",
    "show", "open", "source", "github", "arxiv", "through", "line", "recurs", "recurring",
})

_MIN_CLAIMS = 3          # a term must recur across at least this many claims
_MIN_TOPICS_FOR_TOPIC = 2    # ...spanning at least this many topics to become a topic
_MIN_TOPICS_FOR_METHOD = 2   # ...or to be a transferable lens (an emergent method)
_MAX_INSUFFICIENT_RETRIES = 3   # a layer-absent non-judgment is retried this often, not burned


def _is_synthetic(text: str) -> bool:
    """A claim Joni generated about his own bookkeeping - excluded from the vocabulary."""
    t = text.lower()
    return (t.startswith("hypothesis:") or t.startswith("across my")
            or "is a topic i track" in t or "is worth tracking" in t
            or "keeps recurring" in t)


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


def emerge(cs, extensions: dict, proto, cycle: int = 0, *, layer=None) -> dict:
    layer = layer or NullSemanticLayer()
    live = cs.active_claims()
    idx = _term_index(live)
    known_topics = set(cs.topics())
    out = {"topic": None, "synthesis": 0, "method": None}
    # a Layer-9 non-judgment (layer absent/invalid) must not permanently consume a cluster
    insuff = dict(extensions.get("emerge_insufficient", {}))

    # -- 1. emergent topic: a cross-topic recurring term becomes a tracked topic -------- #
    done_topics = set(extensions.get("emerged_topics", []))
    cands = sorted(
        ((t, e) for t, e in idx.items()
         if t not in known_topics and t not in done_topics
         and len(e["claims"]) >= _MIN_CLAIMS and len(e["topics"]) >= _MIN_TOPICS_FOR_TOPIC),
        key=lambda kv: (-len(kv[1]["claims"]), kv[0]))
    if cands:
        term, e = cands[0]
        cs.learn(f"'{term}' keeps recurring across {len(e['topics'])} of my topics, "
                 f"so I am tracking it as its own topic.", term)
        done_topics.add(term)
        out["topic"] = term
        proto.record(cycle, "emerged",
                     f"new topic '{term}' precipitated from a recurrence across "
                     f"{', '.join(sorted(e['topics']))}")
    extensions["emerged_topics"] = sorted(done_topics)

    # -- 2. emergent synthesis: a within-topic cluster -> a higher-order candidate ------ #
    done_syn = set(extensions.get("synthesized", []))
    made_syn = 0
    by_topic_term: dict[tuple, list] = defaultdict(list)
    for c in live:
        if not c.topic or _is_synthetic(c.text):
            continue
        for w in _content(c.text):
            if w not in _META and quality.is_meaningful_term(w):
                by_topic_term[(c.topic, w)].append(c)
    for (topic, term), cluster in sorted(by_topic_term.items(),
                                         key=lambda kv: (-len(kv[1]), kv[0])):
        if made_syn:
            break
        key = f"{topic}|{term}"
        if key in done_syn or len(cluster) < _MIN_CLAIMS:
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
        cs.hypothesize(
            f"Across my {topic} claims, '{term}' recurs as a through-line worth testing "
            "as a single underlying factor.", topic, parents=parents)
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
