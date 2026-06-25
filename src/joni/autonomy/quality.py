"""A quality gate - keep epistemically weak structure from forming, and from leaving the system.

The cheap candidate generators (``emerge``, ``invent``) trigger on *lexical recurrence*, which
also surfaces stopwords (``about``, ``large``), generic adjectives (``visual``, ``modes``) and
one-off artifact tokens (``mllm``, ``mid-ir``). Unfiltered, these precipitate into hypotheses,
emergent topics, methods - and, worst, public forum questions. This module is the deterministic
gate a recurring term must pass before it may *seed structure* or *be asked about outside*.

It is a first, lexical layer: stopword + artifact filtering and a meaningfulness test. It does
**not** yet judge domain consistency (an off-domain real word like ``cotton`` recurring by chance
still passes) - that needs the semantic/embedding layer with reference definitions, the next step.
What it does remove is the large class of structural junk: function words, generic qualifiers,
vowelless/acronym fragments, and - via ``invent`` - bridging on Joni's own bookkeeping claims.
"""

from __future__ import annotations

import os
import re

# Domain-consistency reference anchors (the user's "Referenzdefinitionen"). A recurring term is
# off-domain when it is *clearly closer* to an off-domain anchor than to any in-domain one - that
# catches an off-domain real word ('cotton', 'glioma') that the lexical filter cannot. Contrastive
# (in vs out) rather than an absolute threshold, so it is robust and conservative.
DOMAIN_ANCHORS = (
    "large language models and AI agents",
    "model routing, inference and serving",
    "memory and continuity for autonomous agents",
    "alignment and safety of AI systems",
    "evaluation and benchmarking of machine learning models",
    "retrieval, calibration and distillation in machine learning",
    "reasoning, epistemics, claims, evidence and provenance",
    "semantic similarity, embeddings and knowledge representation",
    "software engineering, code and distributed systems",
    "data drift, privacy and robustness in machine learning",
)
OFFDOMAIN_ANCHORS = (
    "cotton, textiles, farming and agriculture",
    "clinical medicine, oncology and human disease",
    "geology, minerals and earth science",
    "cooking, food and recipes",
    "sports, games and athletics",
    "finance, banking and accounting",
    "music, painting and entertainment",
    "plants, animals and wildlife biology",
    "history, politics and law",
    "astronomy, planets and the cosmos",
    # generic developer content not specific to AI/agents/epistemics
    "general-purpose programming languages, C++ syntax and coding-style guidelines",
    "web development, frontend and UI frameworks",
    "devops, deployment, build tooling and infrastructure",
)

# Function words, generic qualifiers, and ML-paper filler - none of which names a concept Joni
# could actually develop. Domain terms (routing, alignment, calibration, retrieval, ...) are
# deliberately NOT here.
STOPWORDS = frozenset({
    # articles / conjunctions / prepositions / pronouns
    "the", "this", "that", "these", "those", "and", "but", "for", "nor", "with", "without",
    "from", "into", "onto", "over", "under", "above", "below", "between", "across", "through",
    "during", "before", "after", "while", "when", "where", "which", "what", "whom", "whose",
    "then", "than", "also", "such", "some", "any", "all", "each", "every", "both", "they",
    "them", "their", "your", "yours", "ours", "here", "there", "about", "within",
    "toward", "towards", "upon", "per", "via",
    "because", "therefore", "thus", "hence", "however", "moreover", "furthermore",
    "whether", "although", "though", "since", "unless", "whereas",
    # auxiliaries / modals
    "are", "was", "were", "been", "being", "have", "has", "had", "having", "will", "would",
    "could", "should", "must", "may", "might", "can", "cannot", "not", "does", "did", "done",
    "using", "used", "use", "uses", "based",
    # generic qualifiers / quantifiers that read like a concept but are not
    "large", "small", "big", "tiny", "huge", "novel", "new", "old", "good", "best", "high",
    "low", "fast", "slow", "full", "main", "single", "multiple", "various", "several",
    "different", "similar", "common", "general", "specific", "simple", "complex", "recent",
    "current", "total", "overall", "modes", "mode", "visual", "basic", "final", "initial",
    "long", "short", "wide", "deep", "broad", "many", "much", "more", "most", "less", "least",
    "very", "just", "only", "even", "still", "well", "able", "like", "make", "made", "given",
    # ML-paper filler (structural, not conceptual)
    "paper", "study", "studies", "approach", "approaches", "method", "methods", "model",
    "models", "framework", "frameworks", "system", "systems", "result", "results", "data",
    "dataset", "datasets", "task", "tasks", "work", "works", "propose", "proposed", "present",
    "introduce", "show", "shows", "shown", "demonstrate", "analysis", "performance", "state",
    "report", "preprint", "arxiv", "github", "source", "open",
    "hypothesis", "claim", "claims", "topic", "pattern", "behind", "recurs", "recurring",
    "line", "factor", "tracking", "track", "tracked", "worth", "apply", "applies",
    # generic content words that READ like a concept but are not a research subject - they were
    # leaking through as single-word topics ("user", "outputs", "complexity"), which is the junk a
    # tracked-topic list must not collect. (Domain terms like inference / attention / retrieval /
    # context / variance are deliberately NOT here.)
    "existing", "additional", "available", "possible", "potential", "important", "significant",
    "effective", "relevant", "particular", "actual", "typical", "standard", "default", "generic",
    "session", "sessions", "user", "users", "output", "outputs", "input", "inputs", "value",
    "values", "content", "contents", "information", "execution", "measure", "measures",
    "complexity", "computation", "computational", "deterministic", "language", "item", "items",
    "number", "numbers", "example", "examples", "case", "cases", "level", "levels", "step",
    "steps", "type", "types", "form", "forms", "field", "fields", "point", "points", "term",
    "terms", "aspect", "aspects", "range", "scope", "amount", "ability", "capacity",
})

_VOWEL = re.compile(r"[aeiou]")
# subject terms a generated claim quotes, e.g. "...'cotton' recurs..." -> ['cotton']
_QUOTED = re.compile(r"'([^']+)'")

# Sentinel buckets - they LABEL a claim whose topic could not be classified, but they are NOT
# research subjects. "unsorted" must never become a tracked topic, a forum question, or a Kevin
# target: it is a signal that classification failed, not a concept.
_RESERVED_TOPICS = frozenset({"unsorted", "misc", "other", "general", "uncategorized", "untitled"})


def is_reserved_topic(term: str) -> bool:
    return (term or "").strip().lower() in _RESERVED_TOPICS


def is_meaningful_term(term: str) -> bool:
    """Could this single token plausibly name a concept worth developing or asking about?

    Rejects stopwords/qualifiers, too-short tokens, vowelless or digit-bearing fragments
    (``mllm``, ``gpt-4``) and hyphenated artifacts with a tiny part (``mid-ir``). It does not
    (yet) judge whether the concept is *on-domain* - that is the semantic layer's job."""
    t = (term or "").strip().lower()
    if not t or t in STOPWORDS or t in _RESERVED_TOPICS:
        return False
    parts = t.split("-")
    if any(len(p) < 3 or not p.isalpha() for p in parts):   # 'mid-ir', 'gpt-4', 'a-b'
        return False
    core = "".join(parts)
    return len(core) >= 4 and bool(_VOWEL.search(core))     # reject too-short or 'mllm'/'llms'


def subject_terms(text: str) -> list[str]:
    """The single-token subjects a generated claim quotes (multi-word quotes are not judged)."""
    return [m.strip() for m in _QUOTED.findall(text or "")
            if m.strip() and " " not in m.strip()]


def is_substantive_hypothesis(text: str) -> bool:
    """A hypothesis that names a single-token subject must name a *meaningful* one - so a
    through-line about 'cotton' or 'about' is held back from external communication."""
    subs = subject_terms(text)
    return all(is_meaningful_term(s) for s in subs) if subs else True


def _contrastive_on_domain(probe: str, margin: float | None) -> bool:
    """True unless ``probe`` is *clearly* closer to an off-domain anchor than to any in-domain
    one. **Fail-open** without an embedder - a measurement is never replaced by a lexical guess."""
    from . import embeddings
    if not embeddings.available():
        return True

    def _nearest(anchors) -> float | None:
        ds = [d for d in (embeddings.cosine_distance(probe, a) for a in anchors) if d is not None]
        return min(ds) if ds else None

    d_in, d_out = _nearest(DOMAIN_ANCHORS), _nearest(OFFDOMAIN_ANCHORS)
    if d_in is None or d_out is None:
        return True
    m = margin if margin is not None else float(os.getenv("JONI_DOMAIN_MARGIN", "0.04"))
    return not (d_out + m < d_in)              # reject only when clearly off-domain


def on_domain(term: str, *, margin: float | None = None) -> bool:
    """Is this single term within Joni's subject matter? Contrastive embedding check."""
    return _contrastive_on_domain(f"the concept of {(term or '').strip().lower()}", margin)


def on_domain_text(text: str, *, margin: float | None = None) -> bool:
    """Like :func:`on_domain` but for free text (a paper/method title + summary), so a generic
    off-domain artifact (C++ coding guidelines) is caught before it is harvested as a method."""
    return _contrastive_on_domain((text or "").strip()[:400], margin)


def is_core_sense(text: str, core_ref: str, other_ref: str, *, margin: float | None = None) -> bool:
    """Is ``text`` using a core concept in Joni's sense (``core_ref``) rather than an unrelated
    technical sense (``other_ref``)? Contrastive embedding check - rejects only when ``text`` is
    *clearly* closer to the other sense. Fail-open without an embedder. This is what tells a
    Layer-9 *operator* apart from an 'operator' in model reduction, before a core-ask is raised."""
    from . import embeddings
    if not embeddings.available():
        return True
    d_core = embeddings.cosine_distance(text, core_ref)
    d_other = embeddings.cosine_distance(text, other_ref)
    if d_core is None or d_other is None:
        return True
    m = margin if margin is not None else float(os.getenv("JONI_CORE_MARGIN", "0.04"))
    return not (d_other + m < d_core)


def admissible_term(term: str) -> bool:
    """A term may seed structure only if it is both lexically meaningful and on-domain."""
    return is_meaningful_term(term) and on_domain(term)


def is_good_topic(topic: str) -> bool:
    """A topic worth tracking: a single meaningful term, no compound '+' bridge. Deliberately
    **lexical only** (no embedding) - it runs over every claim/topic each cycle (the retire pass
    and the site), so it must be cheap; the embedding on-domain check is reserved for the few
    emergence *selection* points, not these hot paths."""
    t = (topic or "").strip()
    return bool(t) and "+" not in t and is_meaningful_term(t)


def hypothesis_admissible(text: str) -> bool:
    """A hypothesis may be carried outside only if it is substantive and its named subjects are
    on-domain (so an off-domain real word like 'cotton' is held back too)."""
    return is_substantive_hypothesis(text) and all(on_domain(s) for s in subject_terms(text))
