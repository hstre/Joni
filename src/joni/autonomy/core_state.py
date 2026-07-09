"""The autonomous loop on the one authoritative core.

This retires the legacy ``joni.state.Layer9`` as the autonomy store: Joni's claims,
preferences, conflicts and memories now live in ``desi_layer9.Layer9`` and change only
through its gate. A ``CoreState`` wraps the core with the read shape the loop needs
(``topics`` / ``claims_on``) and gate-backed writes (learn a claim, note a preference,
open - never force-resolve - a conflict).

Time is real: the core's ``tick`` is the real number of days since Joni started, set from
the wall clock each cycle. There are no artificial per-cycle time jumps.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path

import desi_layer9 as l9
from desi_layer9 import Operator, ProposalType, Status, make_proposal, migration, persistence
from desi_layer9.provenance import Provenance

from ..conflict import _ANTONYMS, _NEGATIONS, _content, _overlap, _tokens
from .config import Paths

_SEED_TOPICS = ("privacy", "routing", "memory", "drift")

# The taint contamination flags shown in the influence map (mirrors desi_layer9.taint).
_CONTAMINATION_FIELDS = (
    "source_exposed", "interaction_exposed", "affective_pressure", "adversarial_source",
    "frame_contamination_possible", "role_contamination_possible", "unverified_model_output",
)


def _source_family(obj) -> str:
    """A stable key for a claim's *independent origin* - so two claims from the same paper, forum
    thread, or model run count as ONE source, not two. The first explicit source id wins; else the
    origin type plus the model run/call that produced it (paraphrases of one comment are not two
    sources). Used for source-independence in topic and claim promotion."""
    prov = getattr(obj, "provenance", None)
    if prov is None:
        return "unknown"
    sids = tuple(prov.source_ids or ())
    if sids:
        return f"src:{sids[0]}"
    origin = getattr(prov.origin_type, "value", str(prov.origin_type))
    return f"origin:{origin}:{prov.run_id or prov.call_id or ''}"


_NUM = re.compile(r"\d+(?:\.\d+)?")
_VIA = re.compile(r"\bvia\s+([A-Za-z]+-\d+)")


def _numeric_discrepancy(a: str, b: str) -> bool:
    """The two texts mention different numbers - the 'differ only in a count' case the review
    described (31 vs 34 exchanges)."""
    na, nb = set(_NUM.findall(a or "")), set(_NUM.findall(b or ""))
    return bool(na or nb) and na != nb


def _numeric_only_difference(a: str, b: str) -> bool:
    """True when the two texts are the SAME once numbers are removed, but the numbers differ - a
    numeric discrepancy, not a contradiction. Deliberately number-based, NOT embedding-based: an
    embedding cannot see negation, so 'X is good' vs 'X is not good' must NOT be mistaken for a
    duplicate. Stripping numbers leaves a 'not' in place, so a real negation is never caught here;
    only '...31 exchanges...' vs '...34 exchanges...' (identical residual) is."""
    import os
    if not _numeric_discrepancy(a, b):
        return False
    ra, rb = _NUM.sub("#", (a or "").lower()), _NUM.sub("#", (b or "").lower())
    return ra.strip() == rb.strip() or _overlap(ra, rb) >= float(
        os.getenv("JONI_NUMERIC_PARAPHRASE_OVERLAP", "0.9"))


class CoreState:
    def __init__(self, core: l9.Layer9) -> None:
        self.core = core

    # -- reads (duck-typed to the old Layer9 interface improve.judge expects) -- #
    def _live_claims(self) -> list:
        return [c for c in self.core.all(l9.ObjectType.CLAIM)
                if c.status in (Status.ACTIVE, Status.CONFIRMED)]

    def active_claims(self) -> list:
        return self._live_claims()

    def claims_on(self, topic: str) -> list:
        return [c for c in self._live_claims() if c.topic == topic]

    def topics(self) -> list[str]:
        counts = Counter(c.topic for c in self._live_claims() if c.topic)
        return [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    def research_topics(self, *, min_claims: int | None = None,
                        min_sources: int | None = None) -> list[str]:
        """The topics that have actually *earned* the status of a research direction - not every
        word that recurs. A topic qualifies only when it is lexically meaningful (no stopword, no
        ``unsorted`` sentinel) AND it appears in at least ``min_claims`` live claims drawn from at
        least ``min_sources`` *independent* origins. This is what keeps 'principle' or 'convex'
        from becoming a research subject on word-repetition alone. Used by the action consumers
        (forum questions, Kevin, invention), not just the display."""
        import os

        from . import quality
        mc = min_claims if min_claims is not None else int(os.getenv("JONI_TOPIC_MIN_CLAIMS", "3"))
        ms = (min_sources if min_sources is not None
              else int(os.getenv("JONI_TOPIC_MIN_SOURCES", "2")))
        counts: Counter = Counter()
        fams: dict[str, set] = {}
        for c in self._live_claims():
            t = c.topic
            if not t or not quality.is_good_topic(t):
                continue
            counts[t] += 1
            fams.setdefault(t, set()).add(_source_family(c))
        good = [t for t in counts if counts[t] >= mc and len(fams[t]) >= ms]
        return sorted(good, key=lambda t: (-counts[t], t))

    # -- gate-backed writes -------------------------------------------------- #
    def _op(self, ptype, op, payload, targets=()):
        return self.core.submit(make_proposal(
            ptype, op, payload=payload, proposer="joni",
            provenance=Provenance.from_operator(), target_objects=tuple(targets)), actor="joni")

    def corrected_twin(self, text: str) -> str | None:
        """The id of a REJECTED/SUPERSEDED claim this text near-duplicates, else ``None``.

        The revenant check (the manifesto's forward-binding demand): a belief Joni already
        corrected must not re-enter unexamined just because a source repeats it. Near-duplicate =
        high Jaccard overlap (env ``JONI_REVENANT_OVERLAP``, default 0.75) or a numeric-only
        paraphrase. Deterministic and conservative - only near-identical texts count."""
        import os
        t = (text or "").strip()
        if not t:
            return None
        thr = float(os.getenv("JONI_REVENANT_OVERLAP", "0.75"))
        for c in self.core.all(l9.ObjectType.CLAIM):
            if c.status not in (Status.REJECTED, Status.SUPERSEDED):
                continue
            if _overlap(t, c.text) >= thr or _numeric_only_difference(t, c.text):
                return c.id
        return None

    def _mint_revenant(self, text: str, topic: str, twin: str, sources: list[str],
                       proposer: str) -> str:
        """Mint a claim that near-duplicates a corrected error - as a CANDIDATE, never auto-active.

        The revenant is not blocked (epistemics stays revisable - a corrected belief may yet turn
        out right), but it must EARN its way back: it enters derived from its corrected predecessor
        (auditable lineage, and thereby into the ``strengthen`` ladder, where it is adversarially
        challenged and needs independent support to activate). Provenance carries an explicit
        ``revenant-of:<id>`` marker."""
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": topic, "support": 0.4}, proposer=proposer,
            provenance=Provenance.from_source(*sources, f"revenant-of:{twin}"),
            target_objects=(twin,)), actor="joni")
        return self._newest(l9.ObjectType.CLAIM).id

    def learn(self, text: str, topic: str, *, source_id: str | None = None) -> str:
        """A source (paper) creates a candidate claim; the operator activates it.

        ``source_id`` anchors the claim to where it came from (a paper id / PDF url), so
        provenance is real and source-diversity is measurable downstream.

        **Revenant guard**: a text near-duplicating an already-corrected (REJECTED/SUPERSEDED)
        claim is NOT auto-activated - it re-enters as a candidate that must earn fresh, independent
        support ("ein ähnlicher Übergang darf nicht ohne zusätzliche Prüfung akzeptiert werden")."""
        twin = self.corrected_twin(text)
        if twin:
            return self._mint_revenant(text, topic, twin,
                                       [source_id] if source_id else [], "source")
        prov = Provenance.from_source(source_id) if source_id else Provenance.from_source()
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": topic}, proposer="source",
            provenance=prov), actor="joni")
        claim = self._newest(l9.ObjectType.CLAIM)
        self._op(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
                 {"to_status": "active"}, targets=(claim.id,))
        return claim.id

    def hear(self, text: str, topic: str, *, handle: str, platform: str,
             origin: str = "forum") -> str:
        """A person on a forum is a SOURCE, never an authority.

        Same path as ``learn``: the person is held *exactly* as strictly as a paper - an
        active claim whose authority stays ``candidate`` until it earns independent
        corroboration, and which is open to contradiction like any other source. It is
        deliberately NOT ``OriginType.HUMAN``: that origin is privileged by the protected
        core (it may confirm, resolve, touch the control plane) and is reserved for the
        trusted operator. A stranger on Hacker News is not that - polite in tone, but no
        authority. The handle/platform is recorded as the source id so it is auditable.

        ``origin`` carries *what the source was reacting to*. ``predecessor-thread`` marks a
        reaction to a legacy (pre-Joni) post under the same agent identity - kept as a second,
        auditable source id so Joni can tell a reaction-to-his-own-post from a reaction to an
        inherited, possibly drifted premise. It is provenance only: still a plain SOURCE,
        never weighted up, never an authority."""
        sid = f"{platform}:{handle}"
        sources = [sid]
        if origin and origin not in ("forum", "own-post"):
            sources.append(f"origin:{origin}")
        # Revenant guard, exactly as in ``learn``: a forum voice repeating an already-corrected
        # belief does not get it re-activated - it re-enters as a candidate that must earn support.
        twin = self.corrected_twin(text)
        if twin:
            return self._mint_revenant(text, topic, twin, sources, f"forum:{platform}")
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": topic}, proposer=f"forum:{platform}",
            provenance=Provenance.from_source(*sources)), actor="joni")
        claim = self._newest(l9.ObjectType.CLAIM)
        self._op(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
                 {"to_status": "active"}, targets=(claim.id,))
        return claim.id

    def note_preference(self, subject: str, *, stance: str = "values",
                        strength: float = 0.6) -> str:
        """Note a preference, idempotent per ``(subject, stance)``. A recurring capability note
        (e.g. 'router-note' seen every run a routing item shows up) reuses the existing preference
        instead of minting a duplicate — anti-bloat, so the active set stays one-per-stance."""
        for p in self.core.all(l9.ObjectType.PREFERENCE):
            if (getattr(p, "subject", None) == subject
                    and getattr(p, "stance", None) == stance
                    and getattr(p, "status", None) is not Status.REJECTED):
                return p.id
        self._op(ProposalType.PREFERENCE_PROPOSAL, Operator.PREFERENCE_PROPOSE,
                 {"subject": subject, "stance": stance, "strength": strength})
        return self._newest(l9.ObjectType.PREFERENCE).id

    def open_conflict(self, claim_ids, *, severity: str = "soft",
                      conflict_kind: str = "unqualified") -> str:
        # Idempotent: one conflict object per claim pair. Both detect_and_open_conflicts and the
        # semantic develop step can flag the same pair (a lexical clash that is also a semantic
        # contradiction); without this guard that opened two Conflict nodes for one contradiction,
        # double-counting it downstream. If a conflict for this pair already exists, reuse it.
        pair = frozenset(claim_ids)
        for x in self.core.all(l9.ObjectType.CONFLICT):
            if frozenset(x.claim_ids[:2]) == pair:
                return x.id
        self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_OPEN,
                 {"claim_ids": list(claim_ids), "severity": severity,
                  "conflict_kind": conflict_kind}, targets=tuple(claim_ids))
        return self._newest(l9.ObjectType.CONFLICT).id

    def propose_self_model(self, text: str, *, evidence=(), counterevidence=()) -> str:
        """A provisional belief Joni holds about itself - never a fact (§6)."""
        self._op(ProposalType.SELF_MODEL_PROPOSAL, Operator.SELF_MODEL_PROPOSE,
                 {"text": text, "evidence": list(evidence),
                  "counterevidence": list(counterevidence)})
        return self._newest(l9.ObjectType.SELF_MODEL_CLAIM).id

    def render_narrative(self, text: str, *, basis=()) -> str:
        """Language only - describes state, never overwrites it."""
        self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.NARRATIVE_RENDER,
                 {"text": text, "basis": list(basis)}, targets=tuple(basis))
        return self._newest(l9.ObjectType.NARRATIVE_SUMMARY).id

    def confirmed_claims(self) -> list:
        return [c for c in self.core.all(l9.ObjectType.CLAIM) if c.status is Status.CONFIRMED]

    def corroborate(self, claim_id: str, by_claim, *, relation: str = "supports") -> str:
        """Attach an (unreviewed) evidence link from another claim's content.

        Honest self-organisation: it builds the evidence web but does NOT review or
        confirm anything - confirmation still needs an independent human reviewer.
        ``relation`` is ``supports`` for strong overlap, else ``contextualizes``.

        **Idempotent**: an identical link (same claim, same supporter, same relation) is not
        attached twice - so a pair re-encountered after a bounded dedup-set truncation cannot
        inflate the raw support count with duplicate links. Returns the existing link's id."""
        marker = f"{relation} via {by_claim.id}:"
        ev_by_id = {e.id: e for e in self.core.all(l9.ObjectType.EVIDENCE)}
        for el in self.core.all(l9.ObjectType.EVIDENCE_LINK):
            if el.claim_id == claim_id and el.relation.value == relation:
                ev = ev_by_id.get(el.evidence_id)
                if ev is not None and (getattr(ev, "content", "") or "").startswith(marker):
                    return el.id                  # already corroborated by this supporter+relation
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.EVIDENCE_ATTACH,
            payload={"content": f"{relation} via {by_claim.id}: {by_claim.text}",
                     "relation": relation, "review_status": "unreviewed"},
            proposer="joni", provenance=Provenance.from_operator(),
            target_objects=(claim_id,)), actor="joni")
        return self._newest(l9.ObjectType.EVIDENCE_LINK).id

    def review_conflict(self, conflict_id: str):
        return self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_REVIEW,
                        {}, targets=(conflict_id,))

    def resolve_conflict(self, conflict_id: str, *, winner_id: str, reason: str):
        """Settle a contradiction in favour of ``winner_id`` (recorded in the conflict's
        ``resolution`` field) with an explicit ``reason``. The loop never decides this itself
        (``open conflicts, never force-resolve``); it is only ever applied on the trusted operator's
        instruction (see ``conflict_resolution``), which is the ONE authority that may settle a
        dispute. Deterministic bookkeeping of a human decision, gate-recorded like every op."""
        return self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_RESOLVE,
                        {"to": "resolved", "resolution": winner_id, "reason": reason},
                        targets=(conflict_id,))

    def tolerate_conflict(self, conflict_id: str, *, reason: str):
        """Close a conflict as TOLERATED - the operator's 'kein Widerspruch' call: the pairing was
        spurious (unrelated or compatible claims), so NO claim is superseded and no false 'X -> Y'
        ever reaches the persona. Kernel-legal (OPEN/UNDER_REVIEW -> TOLERATED), gate-recorded."""
        return self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_RESOLVE,
                        {"to": "tolerated", "reason": reason}, targets=(conflict_id,))

    def supersede_claim(self, claim_id: str):
        """Mark a claim SUPERSEDED - a belief replaced by a later one (the successor is carried by
        the resolving conflict's ``resolution`` field, not here). Only used when the operator
        resolves a conflict against this claim; never an autonomous force-resolve."""
        return self._op(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
                        {"to_status": "superseded"}, targets=(claim_id,))

    def refile_claim(self, claim_id: str, new_topic: str) -> str:
        """Move a claim to the topic its CONTENT names - the Layer-9 way, without mutation.

        The kernel has no topic-revision operator, and rightly so: the honest move is to mint a
        successor with the same text and the same source provenance (plus an explicit
        ``refile-of:<id>`` marker and derived_from lineage), carry the original's LIVE support
        links, then supersede the original. Nothing is lost - the mis-filed claim stays in the
        chain forever; the successor just stands where the content says it belongs. Category
        purity in action: 'forum' is a *provenance*, not a *topic* - platform/handle stay in the
        provenance, the topic becomes what the claim is about."""
        old = self.core.get(claim_id)          # objects-property deep-copies the whole store
        sids = list(getattr(old.provenance, "source_ids", ()) or ())
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": old.text, "topic": new_topic}, proposer="joni:refile",
            provenance=Provenance.from_source(*sids, f"refile-of:{claim_id}"),
            target_objects=(claim_id,)), actor="joni")
        new = self._newest(l9.ObjectType.CLAIM)
        self._op(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
                 {"to_status": "active"}, targets=(new.id,))
        # carry the LIVE support (same content -> the 'via C-x' supporter families and external
        # cards keep their meaning); a void link from a dead supporter is deliberately left behind
        ev_by_id = {e.id: e for e in self.core.all(l9.ObjectType.EVIDENCE)}
        status = {c.id: c.status.value for c in self.core.all(l9.ObjectType.CLAIM)}
        for el in list(self.core.all(l9.ObjectType.EVIDENCE_LINK)):
            if el.claim_id != claim_id or el.relation.value not in ("supports", "contextualizes"):
                continue
            content = getattr(ev_by_id.get(el.evidence_id), "content", "") or ""
            m = _VIA.search(content)
            if m is not None and status.get(m.group(1)) in ("rejected", "superseded"):
                continue
            self.core.submit(make_proposal(
                ProposalType.CLAIM_PROPOSAL, Operator.EVIDENCE_ATTACH,
                payload={"content": content, "relation": el.relation.value,
                         "review_status": getattr(el, "review_status", "unreviewed")},
                proposer="joni:refile", provenance=Provenance.from_operator(),
                target_objects=(new.id,)), actor="joni")
        self.supersede_claim(claim_id)
        return new.id

    def evidence_links(self) -> int:
        return len(self.core.all(l9.ObjectType.EVIDENCE_LINK))

    def hypothesize(self, text: str, topic: str, *, parents=(), origin: str = "joni") -> str:
        """Invent a conjecture - a CANDIDATE claim from existing claims. Never auto-activated
        or confirmed: a guess stays a guess until it earns support.

        ``origin="kevin"`` marks a creative model proposal: it carries MODEL provenance (so it is
        taint-flagged ``unverified_model_output`` and cannot reach authoritative status without an
        explicit human validation) - the hurdle is on adoption, not generation. ``origin="joni"`` is
        the deterministic-operator self-conjecture as before."""
        if origin == "kevin":
            proposer = "kevin"
            prov = Provenance.from_model(external=True, model_id="deepseek-v4-pro",
                                         provider="deepseek", served_model="deepseek-v4-pro")
        else:
            proposer, prov = "joni", Provenance.from_operator()
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": topic, "support": 0.4}, proposer=proposer,
            provenance=prov, target_objects=tuple(parents)),
            actor=proposer)
        return self._newest(l9.ObjectType.CLAIM).id

    def hypotheses(self) -> list:
        return [c for c in self.core.all(l9.ObjectType.CLAIM)
                if c.status is Status.CANDIDATE and c.derived_from]

    def activate_claim(self, claim_id: str):
        """Promote a candidate (e.g. a hypothesis that earned support) to ACTIVE - a
        working claim, NOT confirmed. Confirmation still needs an independent human."""
        return self._op(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
                        {"to_status": "active"}, targets=(claim_id,))

    def reject_claim(self, claim_id: str):
        """Give up on a claim/hypothesis - honestly. Shedding a guess that earned nothing
        is part of not degenerating; it is gate-recorded, never silent."""
        return self._op(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REJECT,
                        {}, targets=(claim_id,))

    def reject_method(self, method_id: str):
        """Shed a method candidate (e.g. an off-domain one harvested by mistake). Gate-recorded,
        never silent; Joni never *promotes* a method, but he may discard one he should not keep."""
        return self._op(ProposalType.METHOD_PROPOSAL, Operator.METHOD_REJECT,
                        {}, targets=(method_id,))

    def propose_method(self, *, name: str, summary: str, applicable_to=(),
                       origin: str = "joni") -> str:
        """Store a method Joni found, as a CANDIDATE in the shared Layer 9 core - for
        Kevin (or a human) to trial and promote later. Joni never promotes it himself."""
        self.core.submit(make_proposal(
            ProposalType.METHOD_PROPOSAL, Operator.METHOD_PROPOSE,
            payload={"name": name, "summary": summary, "steps": [],
                     "origin": origin, "applicable_to": list(applicable_to)},
            proposer="joni", provenance=Provenance.from_operator()), actor="joni")
        return self._newest(l9.ObjectType.METHOD).id

    def _newest(self, object_type):
        return max(self.core.all(object_type), key=lambda o: int(o.id.split("-")[-1]))

    def set_day(self, day: int) -> None:
        # The logical clock is MONOTONIC (the kernel forbids moving it backward). ``day`` is derived
        # from the runtime window, which can be reset/backdated below the current clock (e.g. an
        # unpark that starts a fresh window) — feeding that backward raised ValueError and crashed
        # every cycle. Only ever advance the clock, never regress it.
        self.core.set_clock(max(self.core.tick, 0, int(day)))

    # -- contradiction detection: open conflicts, never force-resolve -------- #
    def detect_and_open_conflicts(self) -> list[str]:
        live = sorted(self._live_claims(), key=lambda c: c.id)
        existing = {frozenset(x.claim_ids[:2])
                    for x in self.core.all(l9.ObjectType.CONFLICT) if len(x.claim_ids) >= 2}
        # Two structural speed-ups over the old all-pairs loop; NEITHER changes which conflicts
        # open (verified against the production state - identical opened set):
        #  1. Bucket by topic. The old loop compared all O(N^2) live pairs and discarded every
        #     cross-topic / empty-topic pair as its first step, so only same-topic pairs could
        #     ever open a conflict. Pairing within each topic bucket is the identical candidate set.
        #  2. Tokenise each claim ONCE, not per pair. The old loop re-ran _tokens/_content on both
        #     texts inside every pair; on the production state one topic ('forum') holds ~3.3k of
        #     ~3.9k live claims, so that single bucket is ~5.5M pairs and each claim's text was
        #     tokenised thousands of times. Precomputing per-claim token/content/polarity (the SAME
        #     conflict.py primitives, reused - no logic duplicated) cut this from ~82s to ~13s/cycle
        #     (measured, identical opened set). The residual ~13s is the 5.5M-pair loop itself in
        #     that one giant 'forum' bucket; shrinking it further needs an incremental
        #     (new-claims-only) pass, a separate semantics-sensitive change - not done here.
        # Buckets preserve id order (live is id-sorted), so within a bucket a.id < b.id as before.
        by_topic: dict[str, list] = {}
        for c in live:
            if c.topic:
                by_topic.setdefault(c.topic, []).append(c)
        toks = {c.id: _tokens(c.text) for cl in by_topic.values() for c in cl}
        cont = {c.id: _content(c.text) for cl in by_topic.values() for c in cl}
        pol = {cid: (-1 if (t & _NEGATIONS) else 1) for cid, t in toks.items()}   # == _polarity
        opened: list[str] = []
        for _topic, claims in by_topic.items():
            for i, a in enumerate(claims):
                ta, ca, pa = toks[a.id], cont[a.id], pol[a.id]
                for b in claims[i + 1:]:
                    pair = frozenset((a.id, b.id))
                    if pair in existing:
                        continue
                    tb, cb = toks[b.id], cont[b.id]
                    kind = None
                    # inline _antonym_clash / _overlap / _polarity on the precomputed sets - same
                    # result as calling them on the raw text, but without re-tokenising per pair.
                    if any((x in ta and y in tb) or (y in ta and x in tb) for x, y in _ANTONYMS):
                        kind = "stance_opposition"
                    elif (ca and cb and len(ca & cb) / len(ca | cb) >= 0.34 and pa != pol[b.id]):
                        kind = "negation"
                    if kind:
                        # Near-duplicate guard (review #4): detect a numeric-only paraphrase BEFORE
                        # opening a conflict. A pair that is identical except for a number (31 vs 34
                        # exchanges) is a minor discrepancy, not a contradiction - downgrade it
                        # from a big hard conflict (would trigger an Alexandria round) to a SOFT
                        # one. Real negations keep a 'not' after stripping numbers, so stay hard.
                        numeric_only = _numeric_only_difference(a.text, b.text)
                        from .qualify import qualify_conflict
                        contradictory = kind == "negation" and not numeric_only
                        severity = "hard" if contradictory else "soft"
                        ck = qualify_conflict(a.text, b.text, severity=severity,
                                              contradictory=contradictory)
                        cid = self.open_conflict((a.id, b.id), severity=severity, conflict_kind=ck)
                        opened.append(cid)
                        existing.add(pair)
        return opened

    # -- snapshot for the site ---------------------------------------------- #
    def supporter_families(self, claim_id: str) -> tuple[set[str], int]:
        """(independent source families, external evidence cards) backing a claim. A support that
        points at another claim contributes that claim's source family (so two claims from one
        paper/run/thread count once); a support not derived from a claim is an external card. This
        is the single source of truth for source-independence (used by promotion and the export)."""
        ev_by_id = {e.id: e for e in self.core.all(l9.ObjectType.EVIDENCE)}
        claim_by_id = {c.id: c for c in self.core.all(l9.ObjectType.CLAIM)}
        families: set[str] = set()
        external = 0
        for el in self.core.all(l9.ObjectType.EVIDENCE_LINK):
            if el.claim_id != claim_id or el.relation.value not in ("supports", "contextualizes"):
                continue
            ev = ev_by_id.get(el.evidence_id)
            m = _VIA.search(getattr(ev, "content", "") or "")
            supporter = claim_by_id.get(m.group(1)) if m else None
            if supporter is not None:
                # A supporter later rejected/superseded leaves its link behind (the kernel's
                # reject only flips status) - void support, must not count toward promotion.
                if supporter.status.value in ("rejected", "superseded"):
                    continue
                families.add(_source_family(supporter))
            else:
                external += 1
                sid = getattr(ev, "source_id", None)
                families.add(f"src:{sid}" if sid else f"ext:{el.id}")
        return families, external

    def independent_source_count(self, claim_id: str) -> int:
        fams, _ = self.supporter_families(claim_id)
        return len(fams)

    def supporter_families_map(self) -> dict[str, set[str]]:
        """Independent supporter families for ALL claims in one pass - the same semantics as
        ``supporter_families`` (dead supporters void, one family per paper/run/thread), but built
        once. The per-claim helper rebuilds the full evidence index per call, which turns any
        pass that asks about every claim (the export, the site) into O(claims x links)."""
        ev_by_id = {e.id: e for e in self.core.all(l9.ObjectType.EVIDENCE)}
        claim_by_id = {c.id: c for c in self.core.all(l9.ObjectType.CLAIM)}
        out: dict[str, set[str]] = {}
        for el in self.core.all(l9.ObjectType.EVIDENCE_LINK):
            if el.relation.value not in ("supports", "contextualizes"):
                continue
            ev = ev_by_id.get(el.evidence_id)
            m = _VIA.search(getattr(ev, "content", "") or "")
            supporter = claim_by_id.get(m.group(1)) if m else None
            fams = out.setdefault(el.claim_id, set())
            if supporter is not None:
                if supporter.status.value in ("rejected", "superseded"):
                    continue
                fams.add(_source_family(supporter))
            else:
                sid = getattr(ev, "source_id", None)
                fams.add(f"src:{sid}" if sid else f"ext:{el.id}")
        return out

    def accepted_call_ids(self) -> set[str]:
        """The set of model call_ids that produced at least one STILL-ACTIVE claim - so a true
        per-call yield (<=1) can be computed, instead of dividing a cumulative claim count by a
        cumulative call count (which conflates two ledgers and can read >1: metric theatre)."""
        ids: set[str] = set()
        for c in self._live_claims():
            for s in (getattr(c.provenance, "source_ids", ()) or ()):
                s = str(s)
                if s.startswith(("granite:", "deepseek:")) and ":" in s:
                    ids.add(s.split(":", 1)[1])
        return ids

    def proposal_accepted_count(self) -> int:
        """Live claims that originated from a semantic-model proposal (Granite/DeepSeek) and made
        it through the gate - the numerator for 'how many calls actually produced an accepted
        epistemic object' (review #9). Kevin's are candidate hypotheses, counted separately."""
        n = 0
        for c in self._live_claims():
            sids = getattr(c.provenance, "source_ids", ()) or ()
            if any(str(s).startswith(("granite:", "deepseek:")) for s in sids):
                n += 1
        return n

    def derivation_depth(self, claim, _seen: set | None = None) -> int:
        """How deep a claim's derivation chain runs (0 = a root, source-anchored claim). A deep
        chain with no fresh source is a warning sign of self-referential growth."""
        by_id = {c.id: c for c in self.core.all(l9.ObjectType.CLAIM)}
        seen = _seen or set()
        parents = [by_id[p] for p in (getattr(claim, "derived_from", ()) or ())
                   if p in by_id and p not in seen]
        if not parents:
            return 0
        seen = seen | {claim.id}
        return 1 + max(self.derivation_depth(p, seen) for p in parents)

    def epistemic_usability(self) -> dict:
        """The honest quality metric (review #10): a claim is *epistemically usable* only if it is
        correctly typed AND source-anchored AND non-duplicate AND topic-valid AND scope-valid AND
        provenance-complete. Far stricter than 'not insufficient-semantic-evidence', so it stops
        showing 100% while junk topics and unsupported ideas sit in the state."""
        from collections import Counter

        from . import quality
        active = self._live_claims()
        keys = ("correctly_typed", "source_anchored", "non_duplicate",
                "topic_valid", "scope_valid", "provenance_complete")
        flags = dict.fromkeys(keys, 0)
        if not active:
            return {"rate": 1.0, "n": 0, "flags": flags}

        def _norm(t: str) -> str:
            return " ".join((t or "").lower().split())
        dup_counts = Counter(_norm(c.text) for c in active)
        usable = 0
        for c in active:
            prov = getattr(c, "provenance", None)
            sids = tuple(getattr(prov, "source_ids", ()) or ()) if prov else ()
            origin = getattr(getattr(prov, "origin_type", None), "value", "") if prov else ""
            f = {
                "correctly_typed": bool((c.text or "").strip()) and bool((c.topic or "").strip()),
                "source_anchored": bool(sids) or bool(getattr(c, "derived_from", ()) or ()),
                "non_duplicate": dup_counts[_norm(c.text)] <= 1,
                "topic_valid": quality.is_good_topic(c.topic or ""),
                "scope_valid": bool(c.topic) and not quality.is_reserved_topic(c.topic or ""),
                "provenance_complete": bool(origin) and (bool(sids) or origin in
                                                         ("operator", "human")),
            }
            for k, v in f.items():
                flags[k] += int(v)
            usable += int(all(f.values()))
        return {"rate": round(usable / len(active), 3), "n": len(active), "flags": flags}

    def snapshot(self) -> dict:
        s = self.core
        ms = s.all(l9.ObjectType.METHOD)
        trials = sum(m.trial_count for m in ms)
        ready = sum(1 for m in ms if m.status is Status.PROVISIONAL
                    and m.trial_count >= 3 and m.success_count > m.failure_count)
        return {
            "tick": s.tick,
            "topics": self.topics(),
            "claims_total": len(s.all(l9.ObjectType.CLAIM)),
            "claims_active": len(self._live_claims()),
            "memory": len(s.all(l9.ObjectType.MEMORY_EPISODE)),
            "ledger": len(s.ledger),
            "open_conflicts": len(s.open_conflicts()),
            "methods": len(ms),
            "method_trials": trials,
            "methods_ready": ready,
            "preferences": len(s.all(l9.ObjectType.PREFERENCE)),
            "evidence_links": len(s.all(l9.ObjectType.EVIDENCE_LINK)),
            "self_model": len(s.all(l9.ObjectType.SELF_MODEL_CLAIM)),
            "hypotheses": len(self.hypotheses()),
            "research_topics": len(self.research_topics()),
            "epistemically_usable": self.epistemic_usability(),
        }

    # -- rich export for the human-facing Layer-9 map ----------------------- #
    def epistemic_export(self, *, ledger_tail: int = 200) -> dict:
        """A JSON-serialisable view of the whole epistemic state for the visualisation.

        It separates, per object, the things humans must see at a glance: epistemic
        *status* (truth), *salience* (how present/referenced it is - NOT truth), support,
        evidence strength, and taint. Plus the relations (evidence, conflicts, derivation),
        the utterances (narratives) with their basis, the status-change timeline, and the
        taint/authority summary with a flag if anything tainted reached high authority.
        """
        s = self.core
        objs = list(s.objects.values())
        ref_count = self._reference_counts(objs)

        def taint_flags(o) -> list[str]:
            d = o.taint.to_dict()
            return [k for k in _CONTAMINATION_FIELDS if d.get(k)]

        # The export is the site's living map, not a logfile: every LIVE claim is included, dead
        # ones (rejected/superseded) only as a recent tail - the full record stays in the journal
        # and the persona trail. This is also what keeps the rendered page from growing without
        # bound as housekeeping (reclassification, drains) retires thousands of claims.
        dead_tail = int(os.getenv("JONI_EXPORT_DEAD_TAIL", "400"))
        all_claims = list(s.all(l9.ObjectType.CLAIM))
        dead = [c for c in all_claims if c.status.value in ("rejected", "superseded")]
        dead_kept = set(
            c.id for c in sorted(dead, key=lambda c: int(c.id.split("-")[-1]))[-dead_tail:])
        included = [c for c in all_claims
                    if c.status.value not in ("rejected", "superseded") or c.id in dead_kept]
        # bulk indexes: the per-claim scans made this O(claims x links) every cycle
        links_by_claim: dict[str, list] = {}
        for el in s.all(l9.ObjectType.EVIDENCE_LINK):
            links_by_claim.setdefault(el.claim_id, []).append(el)
        fams_map = self.supporter_families_map()
        claims = []
        for c in included:
            links = links_by_claim.get(c.id, [])
            claims.append({
                "id": c.id, "text": c.text, "topic": c.topic,
                "status": c.status.value, "authority": c.authority.value,
                "support": round(c.confidence_or_support, 3),
                "salience": ref_count.get(c.id, 0),
                "evidence_strength": round(sum(el.strength for el in links), 3),
                "evidence_count": len(links),
                # review #5: count *independent* backing, not raw evidence_count (three claims
                # from one Moltbook thread are not three evidences), plus how deep the derivation
                # chain runs and the originating model family/provider where known.
                "independent_source_count": len(fams_map.get(c.id, ())),
                "derivation_depth": self.derivation_depth(c),
                "origin_family": _source_family(c),
                "model_family": getattr(c.provenance, "model_id", "") or "",
                "provider": getattr(c.provenance, "provider", "") or "",
                "taint": taint_flags(c), "derived_from": list(c.derived_from),
                "ledger_event": c.ledger_event, "tick": c.last_changed_tick,
            })
        included_ids = {c.id for c in included}

        def simple(o, **extra) -> dict:
            base = {"id": o.id, "status": o.status.value, "authority": o.authority.value,
                    "taint": taint_flags(o), "tick": o.last_changed_tick}
            base.update(extra)
            return base

        evidence_links = [
            {"id": el.id, "claim_id": el.claim_id, "evidence_id": el.evidence_id,
             "relation": el.relation.value, "strength": round(el.strength, 3),
             "review_status": el.review_status, "status": el.status.value}
            for el in s.all(l9.ObjectType.EVIDENCE_LINK)
            if el.claim_id in included_ids]              # links of omitted dead claims are noise
        conflicts = [
            simple(x, claim_ids=list(x.claim_ids), conflict_status=x.conflict_status.value,
                   kind=x.kind, conflict_kind=x.conflict_kind.value, severity=x.severity,
                   reason=x.resolution_reason or "")
            for x in s.all(l9.ObjectType.CONFLICT)]
        methods = [
            simple(m, name=m.name, summary=m.summary, origin=m.origin,
                   applicable_to=list(m.applicable_to), trial_count=m.trial_count,
                   success=m.success_count, failure=m.failure_count)
            for m in s.all(l9.ObjectType.METHOD)]
        self_model = [
            simple(sm, text=sm.text, evidence=list(sm.evidence),
                   counterevidence=list(sm.counterevidence))
            for sm in s.all(l9.ObjectType.SELF_MODEL_CLAIM)]
        narratives = [
            {"id": ns.id, "text": ns.text, "basis": list(ns.basis),
             "ledger_event": ns.ledger_event, "tick": ns.last_changed_tick}
            for ns in s.all(l9.ObjectType.NARRATIVE_SUMMARY)]
        semantic = [
            simple(sc, members=list(sc.members), decision=sc.decision.value,
                   semantic_state=sc.semantic_state.value,
                   lexical_trigger=round(sc.lexical_trigger, 3),
                   semantic_layer=sc.semantic_layer, rationale=sc.decision_rationale)
            for sc in s.all(l9.ObjectType.SEMANTIC_CLUSTER)]
        preferences = [
            simple(p, subject=p.subject, stance=p.stance, strength=round(p.strength, 3))
            for p in s.all(l9.ObjectType.PREFERENCE)]
        memory = [
            simple(m, summary=m.summary, kind=m.kind.value,
                   retrieval_weight=round(m.retrieval_weight, 3))
            for m in s.all(l9.ObjectType.MEMORY_EPISODE)]

        ledger = [
            {"id": e.id, "tick": e.tick, "operator": e.operator.value, "actor": e.actor,
             "decision": e.decision, "reason": e.reason[:160],
             "input_refs": list(e.input_refs), "output_refs": list(e.output_refs),
             "cost": e.cost, "event_hash": (e.event_hash or "")[:12]}
            for e in s.ledger[-ledger_tail:]]

        taint_summary = {f: sum(1 for o in objs if o.taint.to_dict().get(f))
                         for f in _CONTAMINATION_FIELDS}
        taint_summary["human_validated"] = sum(
            1 for o in objs if o.taint.human_validated)
        authority_summary: dict[str, int] = {}
        for o in objs:
            authority_summary[o.authority.value] = authority_summary.get(o.authority.value, 0) + 1
        # the red flag: anything contaminated that nonetheless reached high authority.
        high = {l9.Authority.AUTHORITATIVE.value, l9.Authority.CONTROL.value}
        tainted_authoritative = [
            o.id for o in objs
            if o.authority.value in high and o.taint.is_contaminated]

        return {
            "tick": s.tick,
            "claims": claims, "evidence_links": evidence_links, "conflicts": conflicts,
            "methods": methods, "self_model": self_model, "narratives": narratives,
            "semantic_clusters": semantic, "preferences": preferences, "memory": memory,
            "ledger": ledger, "counts": {
                "claims": len(claims), "evidence_links": len(evidence_links),
                "conflicts": len(conflicts), "methods": len(methods),
                "self_model": len(self_model), "memory": len(memory),
                "semantic_clusters": len(semantic), "preferences": len(preferences),
                "ledger": len(s.ledger),
                # honesty about the window: how many dead claims the map does NOT show (they
                # remain fully addressable in the journal and the persona trail).
                "claims_total": len(all_claims),
                "claims_omitted_dead": len(dead) - len(dead_kept),
            },
            "taint_summary": taint_summary, "authority_summary": authority_summary,
            "tainted_authoritative": tainted_authoritative,
        }

    @staticmethod
    def _reference_counts(objs) -> dict[str, int]:
        """How many other objects point at each object - a salience proxy (NOT truth)."""
        counts: dict[str, int] = {}

        def bump(ids):
            for i in ids:
                counts[i] = counts.get(i, 0) + 1

        for o in objs:
            bump(getattr(o, "derived_from", ()) or ())
            bump(getattr(o, "claim_ids", ()) or ())
            bump(getattr(o, "members", ()) or ())
            bump(getattr(o, "basis", ()) or ())
            bump(getattr(o, "evidence", ()) or ())
            cid = getattr(o, "claim_id", "")
            if cid:
                bump((cid,))
        return counts


def seed_core() -> l9.Layer9:
    """A fresh core with Joni's starting topics, created through the gate."""
    cs = CoreState(l9.Layer9())
    for topic in _SEED_TOPICS:
        cs.learn(f"{topic} is a topic I track", topic)
    return cs.core


def _use_sqlite() -> bool:
    """Persistence backend select. Default 'json' = the committed journal (unchanged behaviour).
    'sqlite' = the materialised runtime store (layer9_v2.runtime.desi_store): load is a SELECT, not
    a full journal replay. Reversible via the env var; no kernel change either way."""
    import os
    return os.getenv("JONI_PERSISTENCE", "json").lower() == "sqlite"


def load_or_migrate(paths: Paths) -> CoreState:
    """Resume the core; else migrate the legacy Joni state; else seed fresh.

    Self-heals a state written before per-entry ticks were journalled: if the strict load
    fails its hash check (a tick change made the recorded hash unreproducible), repair it
    in place and load again, rather than crashing the cycle.
    """
    if _use_sqlite():
        from ..layer9_v2.runtime import desi_store
        core = desi_store.load(paths.core_sqlite)            # warm: SELECT from the sqlite store
        if core is None:
            # cold start: restore the committed checkpoint (NO replay); only if it matches the
            # journal's recorded hash. This is the fix for the >100-min cold replay that parked
            # the loop — the journal stays the source of truth, the checkpoint is a verified cache.
            core = desi_store.load_via_checkpoint(paths.core, paths.checkpoint)
        if core is None and paths.core.exists():
            core = persistence.load(paths.core)    # last resort: full replay (checkpoint stale)
        if core is not None:
            return CoreState(core)
        # no sqlite store and no JSON core yet -> fall through to legacy migrate / seed
    else:
        try:
            core = persistence.load(paths.core)
        except ValueError:
            persistence.repair(paths.core)
            core = persistence.load(paths.core)
        if core is not None:
            return CoreState(core)
    legacy = _read_json(paths.state)           # old joni_state.json, if any
    if legacy:
        core, _report = migration.migrate(joni_state=legacy)
        return CoreState(core)
    return CoreState(seed_core())


def save(cs: CoreState, paths: Paths) -> None:
    if _use_sqlite():
        from ..layer9_v2.runtime import desi_store
        desi_store.save(cs.core, paths.core_sqlite)
        # keep the committed cold-start checkpoint fresh (cheap; state is in memory) so the NEXT
        # fresh CI job restores it instead of replaying. The journal is still written below.
        desi_store.write_checkpoint(cs.core, paths.checkpoint)
        persistence.save(cs.core, paths.core)     # journal stays the committed source of truth
    else:
        persistence.save(cs.core, paths.core)


def _read_json(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None
