"""Collapse-Resistance-Panel — a deterministic, READ-ONLY early-warning system over Joni's own
trajectory (operator spec 2026-07-05).

It measures, logs and warns. It NEVER repairs claims, resorts topics, or makes an authority
decision — any repair still flows through the existing gates. Strictly read-only with respect to
Layer 9: it reads the already-loaded core, the append-only protocol, and the run state; it writes
only its own two artefacts under the governance allowlist:

  * ``state/collapse_series.jsonl`` — one machine-readable row per CYCLE (the time series)
  * ``state/collapse_panel.md``     — a short human/site summary of the latest row

No LLM judge is ever consulted, and no self-diagnosis prose (the narrative summaries) is used as a
data source — only the graph, the protocol, the state and existing deterministic fields.

Terminology, kept strict (the spec asked for this):
  * **cycle**  — one ``one_cycle()`` iteration; the protocol's own counter, cumulative over the
    whole ``protocol.jsonl`` lifetime (never reset). One vitality + one note per cycle.
  * **run**    — the same iteration counted in ``window["runs"]``, which RESETS when the runtime
    window resets. "run 91" = the 91st iteration in the current window.
  * **self-review** — the periodic diary installment (every 10 runs / hourly), NOT per cycle.
Each series row records both ``cycle`` (cumulative) and ``run`` (window-scoped) so the two are
never conflated.
"""
from __future__ import annotations

import contextlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import desi_layer9 as l9

# Buckets that are semantic *sinks*, not real research directions — a claim landing here is
# undifferentiated. Netto entropy and the "real topics" views exclude them so the sink cannot
# fog the picture (the 84%-forum case: formally many topics, semantically one drain).
_SINK_BUCKETS = frozenset({"forum", "misc", "unknown", "unsorted", "gatemem", "assess"})

OK, WARN, ALARM = "ok", "warn", "alarm"
_RANK = {OK: 0, WARN: 1, ALARM: 2}


def _level(value: float, warn: float, alarm: float) -> str:
    """Higher value = worse. Returns ok/warn/alarm against the two thresholds."""
    if value >= alarm:
        return ALARM
    if value >= warn:
        return WARN
    return OK


def _entropy(counts) -> float:
    """Shannon entropy (bits) of a distribution over buckets, normalised to [0,1] by log2(k).
    1.0 = perfectly spread, →0 = collapsed onto one bucket. 0 buckets → 0.0, 1 bucket → 0.0."""
    total = sum(counts.values())
    if total <= 0 or len(counts) <= 1:
        return 0.0
    h = -sum((n / total) * math.log2(n / total) for n in counts.values() if n)
    return h / math.log2(len(counts))


# Authority is a first-class field on every Layer-9 object (untrusted < candidate < reviewed <
# authoritative < control). "Presented as reliable" means authority >= reviewed - NOT merely status
# 'active', which is only a working state (the operator's point: active != strongly supported).
_AUTHORITY_RANK = {"untrusted": 0, "candidate": 1, "reviewed": 2, "authoritative": 3, "control": 4}
_REVIEWED_RANK = _AUTHORITY_RANK["reviewed"]

# A source counts as an *independent external family* only if it is a real outside reference. A
# conversation / self-reference / body-less internal note is not - so synthetic self-support cannot
# masquerade as external grounding.
_EXTERNAL_SOURCE_KINDS = frozenset({"web", "paper", "dataset", "document", "observation"})

# Live (still-contested) conflict statuses - matches ``core.open_conflicts()``. TOLERATED is held
# open on PURPOSE (not an unresolved problem); RESOLVED/SUPERSEDED are closed. The panel used to
# count TOLERATED as "open", which is why its number sat above the dashboard's - now reconciled.
_LIVE_CONFLICT = frozenset({"open", "under_review"})
_CLOSED_CONFLICT_STATUS = frozenset({"resolved", "superseded"})


def _authority_rank(obj) -> int:
    a = getattr(getattr(obj, "authority", None), "value", None)
    if a is None:
        a = getattr(obj, "authority", "")
    return _AUTHORITY_RANK.get(str(a), 0)


def _source_family(src) -> str | None:
    """A stable key for an *independent external* source family (the uri host, else its id/title),
    or None when the source is internal (a conversation / self-reference / no external uri)."""
    kind = str(getattr(src, "kind", "") or "")
    uri = str(getattr(src, "uri", "") or "")
    if kind not in _EXTERNAL_SOURCE_KINDS and "://" not in uri:
        return None
    m = re.search(r"://([^/]+)", uri)
    if m:
        host = m.group(1).lower()
        return host[4:] if host.startswith("www.") else host
    return uri or str(getattr(src, "id", "")) or None


def _normalise(text) -> str:
    """Lowercase + whitespace-collapse, digits KEPT - so a self-claim differing only in a count
    ('214 open' vs '215 open') stays DISTINCT (new info), not a false digit-stripped repeat."""
    return " ".join(str(text).lower().split())


# ---- individual metrics (each pure; each returns {value(s)..., "level": ...}) ---------------- #

def top_bucket_dominance(topics: Counter) -> dict:
    """[1] Share of active claims in the single largest topic bucket. Warn >65%, alarm >80%.
    The top bucket AND whether it is a sink are both reported — a sink dominating is the
    structural blind-maker, not a benign fact."""
    total = sum(topics.values())
    if not total:
        return {"top_bucket": None, "share": 0.0, "is_sink": False, "level": OK}
    bucket, n = topics.most_common(1)[0]
    share = n / total
    return {"top_bucket": bucket, "share": round(share, 4), "is_sink": bucket in _SINK_BUCKETS,
            "claims_total": total, "level": _level(share, 0.65, 0.80)}


def topic_entropy(topics: Counter) -> dict:
    """[2] Entropy brutto (all buckets) AND netto (sink buckets removed), normalised. A low netto
    entropy with a high brutto means the sink is doing the spreading, not real topics."""
    netto = Counter({t: n for t, n in topics.items() if t not in _SINK_BUCKETS})
    brutto_h = _entropy(topics)
    netto_h = _entropy(netto)
    # warn when the *net* structure (the real topics) is collapsing onto few buckets
    return {"entropy_brutto": round(brutto_h, 3), "entropy_netto": round(netto_h, 3),
            "real_topics": len(netto), "level": _level(1.0 - netto_h, 0.55, 0.75)}


def weak_claim_ratio(claims, support_of: dict) -> dict:
    """[3] Support quality on the RIGHT axes - status, authority and grounding are different things,
    and the old metric conflated 'active' (a working state) with 'strong' (well supported).

    ``support_of`` maps claim_id -> {'links': int, 'families': int (distinct external source
    families), 'reviewed': int (reviewed evidence links)}. Three readings:

      * per-status weak-by-links share (continuity with the old number, still informative);
      * ``presented_strong`` - claims put forward as reliable: status ``confirmed`` OR authority
        >= ``reviewed``. A merely ``active`` claim is NOT counted as strong;
      * the ``hollow`` share of those: no independent EXTERNAL source family behind them (only
        internal / derived / synthetic support). The ALARM rides on the hollow share, so a pile of
        working-state claims can't trip it and a synthetic claim propped only by other synthetic
        claims never reads as strong (the operator's synthetic-circularity concern, points 1+6).
    """
    by_status: dict[str, list[int]] = defaultdict(lambda: [0, 0])   # status -> [weak_links, total]
    presented = hollow = reviewed_backed = single_family = 0
    for c in claims:
        sup = support_of.get(c.id, {})
        links = int(sup.get("links", 0))
        families = int(sup.get("families", 0))
        reviewed = int(sup.get("reviewed", 0))
        by_status[c.status.value][1] += 1
        if links <= 1:
            by_status[c.status.value][0] += 1
        if c.status.value == "confirmed" or _authority_rank(c) >= _REVIEWED_RANK:
            presented += 1
            if families == 0:
                hollow += 1
            if families <= 1:
                single_family += 1
            if reviewed > 0:
                reviewed_backed += 1
    ratios = {st: round(w / t, 3) for st, (w, t) in by_status.items() if t}
    hollow_ratio = round(hollow / presented, 3) if presented else 0.0
    return {"by_status": ratios,
            "presented_strong": presented,
            "hollow_count": hollow, "hollow_ratio": hollow_ratio,
            "single_family_count": single_family, "reviewed_backed": reviewed_backed,
            # kept keys, honestly redefined: 'strong' = presented-as-reliable, 'weak' = hollow
            "strong_claims": presented, "strong_weak_ratio": hollow_ratio,
            "level": _level(hollow_ratio, 0.70, 0.90) if presented else OK}


def degeneracy(vitality_record: dict, undecidable: int, clusters_total: int) -> dict:
    """[4] Real counts, not the 0-3 composite alone: degeneration score, unsupported hypotheses,
    undecidable clusters, decidable %. Any non-zero degeneration is at least a warning; the
    persistence check (over runs) is applied by the caller via the series."""
    decidable_pct = round(100 * (1 - undecidable / clusters_total), 1) if clusters_total else 100.0
    degen = int(vitality_record.get("degeneration", 0))
    unsupported = int(vitality_record.get("unsupported_hypotheses", 0))
    lvl = WARN if degen >= 1 else OK
    return {"degeneration_score": degen, "unsupported_hypotheses": unsupported,
            "undecidable_clusters": undecidable, "clusters_total": clusters_total,
            "decidable_percent": decidable_pct, "level": lvl}


def conflict_depth(conflicts, topic_of: dict | None = None) -> dict:
    """[5] Not just the count — the *shape*. Build the contradiction graph from each conflict's
    claim_ids and report component count, the largest tangle, whether any component is cyclic
    (more edges than a tree), open/unresolved conflicts, and the worst topic. A flat 246 is far
    less critical than a few deep, cyclic tangles.

    A ``Conflict`` carries no ``topic`` of its own, so the worst topic is derived from the topics of
    its claims via ``topic_of`` (claim_id -> topic); without the map it stays ``None``."""
    topic_of = topic_of or {}
    adj: dict[str, set] = defaultdict(set)
    edges = 0
    per_topic: Counter = Counter()
    by_status: Counter = Counter()
    open_conf = 0
    total = 0
    for cf in conflicts:
        total += 1
        status = getattr(getattr(cf, "conflict_status", None), "value", "") or ""
        by_status[status or "open"] += 1
        # live = open + under_review (matches core.open_conflicts). TOLERATED is deliberately held,
        # not an unresolved problem; RESOLVED/SUPERSEDED are closed - both excluded from the shape.
        if status and status not in _LIVE_CONFLICT:
            continue
        open_conf += 1
        ids = [str(x) for x in (getattr(cf, "claim_ids", None) or [])]
        for cid in ids:                          # the conflict's topic(s) = its claims' topics
            t = topic_of.get(cid)
            if t:
                per_topic[t] += 1
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if ids[j] not in adj[ids[i]]:
                    adj[ids[i]].add(ids[j])
                    adj[ids[j]].add(ids[i])
                    edges += 1
    seen: set = set()
    comps = []          # (n_nodes, n_edges) per component
    for start in list(adj):
        if start in seen:
            continue
        stack, nodes = [start], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            nodes.add(x)
            stack.extend(adj[x] - seen)
        e = sum(len(adj[n] & nodes) for n in nodes) // 2
        comps.append((len(nodes), e))
    comps.sort(reverse=True)
    max_comp = comps[0][0] if comps else 0
    cyclic = sum(1 for n, e in comps if e >= n)      # a tree has e = n-1; e >= n ⇒ a cycle exists
    worst_topic = per_topic.most_common(1)[0] if per_topic else (None, 0)
    return {"open_conflicts": open_conf,               # live = open + under_review
            "total_conflicts": total,
            "tolerated": by_status.get("tolerated", 0),
            "closed": sum(by_status.get(s, 0) for s in _CLOSED_CONFLICT_STATUS),
            "by_status": dict(by_status),
            "components": len(comps), "max_component": max_comp,
            "cyclic_components": cyclic, "worst_topic": worst_topic[0],
            "worst_topic_conflicts": worst_topic[1],
            "level": max(_level(max_comp, 10, 25), WARN if cyclic else OK, key=_RANK.get)}


def novelty(new_counts: list[int]) -> dict:
    """[6] Input-starvation, not collapse — but a stagnation signal. 7-run and 30-run moving means
    of genuinely-new items, plus the zero-new share. Oldest→newest; last entry is current."""
    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else 0.0
    last7, last30 = new_counts[-7:], new_counts[-30:]
    zero_share = round(sum(1 for n in last30 if n == 0) / len(last30), 3) if last30 else 0.0
    # dry = both the fast and slow window near zero, or over half the recent cycles bringing nothing
    lvl = ALARM if (mean(last7) == 0 and last7) else (
        WARN if (mean(last30) < 1.0 or zero_share > 0.5) else OK)
    return {"new_mean_7": mean(last7), "new_mean_30": mean(last30),
            "zero_new_share_30": zero_share, "samples": len(new_counts), "level": lvl}


def repetition(dev_summaries: list[str], selfmodel_claims: list) -> dict:
    """[7] Repetition / dedup-loop, two independent signals:

      * the share of 'developed' operations that were duplicates (no new link), from the protocol;
      * self-model re-minting: the share of recent ``SELF_MODEL_CLAIM`` **objects** whose normalised
        text (digits KEPT) repeats an earlier one.

    Measuring real self-model objects - not digit-stripped protocol self-review text - fixes the
    old artefact: standardised traits that differ only in a count ('214 open' vs '215 open') used to
    collapse to one after digit-stripping and read as ~97% repetition. Keeping the digits, those are
    distinct self-claims (new information); only a genuinely identical trait text is a real re-mint.
    ``selfmodel_claims`` is a list of objects with a ``.text`` (a bare string is also accepted)."""
    dev_total = len(dev_summaries)
    dup = sum(1 for s in dev_summaries if "duplicate" in s.lower())
    dup_share = round(dup / dev_total, 3) if dev_total else 0.0
    texts = [_normalise(o if isinstance(o, str) else getattr(o, "text", ""))
             for o in selfmodel_claims]
    texts = [t for t in texts if t]
    sm_repeat = round(1 - len(set(texts)) / len(texts), 3) if texts else 0.0
    lvl = max(_level(dup_share, 0.85, 0.97), _level(sm_repeat, 0.5, 0.8), key=_RANK.get)
    return {"dev_total": dev_total, "duplicate_dev_share": dup_share,
            "selfmodel_count": len(texts), "selfmodel_repeat_ratio": sm_repeat, "level": lvl}


def guard_liveness() -> dict:
    """Which quality guards actually MEASURE in this deployment - and which silently fail open.

    A guard that cannot run is worse than none while nothing shows it: every downstream pass
    believes the check happened. The embedding domain gate (``quality.on_domain``) is fail-open
    by design - correct per decision, but as a standing condition it means three passes
    (retire_offdomain, emerge's domain gate, the method harvest's text gate) wave everything
    through. The Granite gates (topic/method) and the semantic layer say whether the LLM-judged
    checks are configured at all. Levels: OK = the embedding gate measures; WARN = it is dark
    but the Granite gates still judge; ALARM = lexical filters are the only line left."""
    from . import embeddings, method_review, projection, topic_review
    emb = embeddings.available()
    guards = {
        "embedding_domain_gate": "live" if emb else "fail-open",
        "granite_topic_gate": "live" if topic_review.enabled() else "off",
        "granite_method_gate": "live" if method_review.enabled() else "off",
        "semantic_layer": "live" if projection.enabled() else "off",
    }
    dark = sorted(k for k, v in guards.items() if v != "live")
    level = OK if emb else (WARN if projection.enabled() else ALARM)
    return {"level": level, "guards": guards, "dark": dark, "dark_count": len(dark)}


def cold_replay(load_seconds: float | None) -> dict:
    """[8] Not a semantic collapse — a *system* collapse early indicator. The kernel cold-load time
    (the O(n²)-replay incident's root). Baseline ~17s; warn >45s, alarm >180s. None = not measured
    this cycle (fast-load/warm path), reported as level ok."""
    if load_seconds is None:
        return {"load_seconds": None, "level": OK}
    return {"load_seconds": round(load_seconds, 1), "level": _level(load_seconds, 45, 180)}


# ---- orchestration -------------------------------------------------------------------------- #

def _read_protocol_tail(path: Path, kinds: frozenset, limit: int) -> list[dict]:
    """Read up to the last ``limit`` protocol events of the given kinds. Read-only, tolerant."""
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-6000:]:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("kind") in kinds:
            out.append(e)
    return out[-limit:]


def compute(cs, extensions: dict, *, proto_path: Path, load_seconds: float | None,
            cycle: int, run: int) -> dict:
    """Compute the full panel record from the graph + protocol + state. Pure read; no writes."""
    core = cs.core
    claims = cs.active_claims()
    topics = Counter(c.topic for c in claims if c.topic)

    # Per-claim support quality (not just a link count): distinct independent EXTERNAL source
    # families and reviewed links, via EvidenceLink -> Evidence -> Source. Only SUPPORTS count.
    evidence_by_id = {e.id: e for e in core.all(l9.ObjectType.EVIDENCE)}
    source_by_id = {s.id: s for s in core.all(l9.ObjectType.SOURCE)}
    _support: dict[str, dict] = {}
    for el in core.all(l9.ObjectType.EVIDENCE_LINK):
        cid = getattr(el, "claim_id", None)
        if not cid:
            continue
        rel = getattr(getattr(el, "relation", None), "value", getattr(el, "relation", ""))
        if str(rel) not in ("supports", ""):
            continue
        rec = _support.setdefault(cid, {"links": 0, "reviewed": 0, "families": set()})
        rec["links"] += 1
        if str(getattr(el, "review_status", "")) == "reviewed":
            rec["reviewed"] += 1
        ev = evidence_by_id.get(getattr(el, "evidence_id", None))
        src = source_by_id.get(getattr(ev, "source_id", None)) if ev is not None else None
        fam = _source_family(src) if src is not None else None
        if fam:
            rec["families"].add(fam)
    support_of = {cid: {"links": r["links"], "reviewed": r["reviewed"],
                        "families": len(r["families"])} for cid, r in _support.items()}
    # recent self-model OBJECTS (not digit-stripped protocol text) for the repetition sensor
    selfmodel = sorted(core.all(l9.ObjectType.SELF_MODEL_CLAIM),
                       key=lambda o: getattr(o, "created_tick", 0))[-30:]

    clusters = list(core.all(l9.ObjectType.SEMANTIC_CLUSTER))
    decidable_states = {"synthesis-eligible", "synthesis-rejected", "semantic-measured"}
    undecidable = sum(1 for o in clusters
                      if getattr(o, "semantic_state", None) not in decidable_states)
    vit = extensions.get("vitality", {})
    conflicts = list(core.all(l9.ObjectType.CONFLICT))
    # a claim_id -> topic map so conflict_depth can name its worst topic (a Conflict has no topic)
    topic_of = {c.id: c.topic for c in core.all(l9.ObjectType.CLAIM) if getattr(c, "topic", None)}

    # novelty from the protocol note counts; dev-duplicate share from the develop ops
    notes = _read_protocol_tail(proto_path, frozenset({"note"}), 60)
    new_counts = [int(m.group(1)) for e in notes
                  if (m := re.search(r"· (\d+) new", e.get("summary", "")))]
    devs = [e.get("summary", "") for e in
            _read_protocol_tail(proto_path, frozenset({"developed"}), 200)]

    metrics = {
        "top_bucket_dominance": top_bucket_dominance(topics),
        "topic_entropy": topic_entropy(topics),
        "weak_claim_ratio": weak_claim_ratio(claims, support_of),
        "degeneracy": degeneracy(vit, undecidable, len(clusters)),
        "conflict_depth": conflict_depth(conflicts, topic_of),
        "novelty": novelty(new_counts),
        "repetition": repetition(devs, selfmodel),
        "cold_replay": cold_replay(load_seconds),
        "guard_liveness": guard_liveness(),
    }
    overall = max((m["level"] for m in metrics.values()), key=_RANK.get, default=OK)
    return {"cycle": cycle, "run": run, "active_claims": len(claims),
            "overall": overall, "metrics": metrics}


def render_summary(rec: dict) -> str:
    """A short human/site summary of the latest row (Markdown). Descriptive only — it states the
    warning, it never claims a repair."""
    m = rec["metrics"]
    icon = {OK: "🟢", WARN: "🟡", ALARM: "🔴"}
    lines = [
        "# Joni — Collapse-Resistance-Panel",
        "",
        f"**Cycle {rec['cycle']} · Run {rec['run']} · {rec['active_claims']} aktive Claims**  ",
        f"**Gesamtstatus: {icon[rec['overall']]} {rec['overall'].upper()}**  ",
        "",
        "_Read-only Frühwarnung. Das Panel misst und warnt — es repariert nichts; "
        "Korrekturen laufen weiter über die bestehenden Gates._",
        "",
        "| Metrik | Wert | Status |",
        "|---|---|---|",
        f"| 1 Top-Bucket-Dominanz | {m['top_bucket_dominance']['top_bucket']} "
        f"{m['top_bucket_dominance']['share']:.0%}"
        f"{' (Sink!)' if m['top_bucket_dominance']['is_sink'] else ''} "
        f"| {icon[m['top_bucket_dominance']['level']]} |",
        f"| 2 Entropy brutto/netto | {m['topic_entropy']['entropy_brutto']:.2f} / "
        f"{m['topic_entropy']['entropy_netto']:.2f} ({m['topic_entropy']['real_topics']} echte) "
        f"| {icon[m['topic_entropy']['level']]} |",
        f"| 3 Weak-Claim (hohl) | {m['weak_claim_ratio']['strong_weak_ratio']:.0%} von "
        f"{m['weak_claim_ratio']['strong_claims']} präsentiert-stark, "
        f"{m['weak_claim_ratio'].get('reviewed_backed', 0)} reviewed-gestützt "
        f"| {icon[m['weak_claim_ratio']['level']]} |",
        f"| 4 Degen/undecidable | degen {m['degeneracy']['degeneration_score']}, "
        f"decidable {m['degeneracy']['decidable_percent']:.0f}%, "
        f"{m['degeneracy']['unsupported_hypotheses']} unsupp. "
        f"| {icon[m['degeneracy']['level']]} |",
        f"| 5 Conflict-Tiefe | {m['conflict_depth']['open_conflicts']} live "
        f"(open+review), {m['conflict_depth'].get('tolerated', 0)} toleriert, "
        f"{m['conflict_depth'].get('closed', 0)} closed; max Tangle "
        f"{m['conflict_depth']['max_component']}, "
        f"{m['conflict_depth']['cyclic_components']} zyklisch "
        f"| {icon[m['conflict_depth']['level']]} |",
        f"| 6 Novelty (7/30) | {m['novelty']['new_mean_7']:.2f} / "
        f"{m['novelty']['new_mean_30']:.2f}, "
        f"{m['novelty']['zero_new_share_30']:.0%} leer | {icon[m['novelty']['level']]} |",
        f"| 7 Repetition | dup-dev {m['repetition']['duplicate_dev_share']:.0%}, "
        f"self-model {m['repetition']['selfmodel_repeat_ratio']:.0%} "
        f"({m['repetition'].get('selfmodel_count', 0)} obj) "
        f"| {icon[m['repetition']['level']]} |",
        f"| 8 Cold-Replay | {m['cold_replay']['load_seconds']}s "
        f"| {icon[m['cold_replay']['level']]} |",
        f"| 9 Guard-Liveness | {_guards_cell(m['guard_liveness'])} "
        f"| {icon[m['guard_liveness']['level']]} |",
        "",
    ]
    return "\n".join(lines) + "\n"


def _guards_cell(g: dict) -> str:
    return ("alle Wächter messen" if not g["dark"]
            else "dunkel: " + ", ".join(g["dark"]))


def run_panel(cs, extensions: dict, proto, cycle: int, *, run: int, paths,
              load_seconds: float | None = None) -> dict:
    """Compute + persist the panel for this cycle. Fail-open: any error is swallowed so the panel
    can never break the loop. Writes ONLY its two state artefacts and one protocol line — never
    Layer 9. Returns the record (or an empty dict on failure)."""
    try:
        rec = compute(cs, extensions, proto_path=paths.protocol, load_seconds=load_seconds,
                      cycle=cycle, run=run)
        series = paths.collapse_series
        series.parent.mkdir(parents=True, exist_ok=True)
        with series.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        paths.collapse_panel.write_text(render_summary(rec), encoding="utf-8")
        d = rec["metrics"]
        proto.record(cycle, "collapse",
                     f"{rec['overall']} · top-bucket {d['top_bucket_dominance']['share']:.0%}"
                     f"{'(sink)' if d['top_bucket_dominance']['is_sink'] else ''} · "
                     f"novelty30 {d['novelty']['new_mean_30']:.2f} · "
                     f"conflict-max {d['conflict_depth']['max_component']} · "
                     f"decidable {d['degeneracy']['decidable_percent']:.0f}%")
        return rec
    except Exception as exc:  # noqa: BLE001 - a read-only monitor must never break the cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "collapse", f"[panel error, skipped] {type(exc).__name__}")
        return {}
