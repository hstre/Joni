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

import re

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
})

_VOWEL = re.compile(r"[aeiou]")
# subject terms a generated claim quotes, e.g. "...'cotton' recurs..." -> ['cotton']
_QUOTED = re.compile(r"'([^']+)'")


def is_meaningful_term(term: str) -> bool:
    """Could this single token plausibly name a concept worth developing or asking about?

    Rejects stopwords/qualifiers, too-short tokens, vowelless or digit-bearing fragments
    (``mllm``, ``gpt-4``) and hyphenated artifacts with a tiny part (``mid-ir``). It does not
    (yet) judge whether the concept is *on-domain* - that is the semantic layer's job."""
    t = (term or "").strip().lower()
    if not t or t in STOPWORDS:
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
