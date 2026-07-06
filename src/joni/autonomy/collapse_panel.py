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
from collections import Counter, defaultdict
from pathlib import Path

import desi_layer9 as l9
from desi_layer9 import Status

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


def weak_claim_ratio(claims, evidence_of: dict) -> dict:
    """[3] Fraction of claims with ≤1 evidence link, SPLIT by status. A weak *candidate* is fine;
    a weak *active/confirmed* ('strong') claim is the concern, so the level rides on that group."""
    by_status: dict[str, list[int]] = defaultdict(lambda: [0, 0])   # status -> [weak, total]
    for c in claims:
        st = c.status.value
        by_status[st][1] += 1
        if evidence_of.get(c.id, 0) <= 1:
            by_status[st][0] += 1
    ratios = {st: round(w / t, 3) for st, (w, t) in by_status.items() if t}
    strong = ["active", "confirmed"]
    sw = sum(by_status[s][0] for s in strong)
    st_ = sum(by_status[s][1] for s in strong)
    strong_weak = (sw / st_) if st_ else 0.0
    return {"by_status": ratios, "strong_weak_ratio": round(strong_weak, 3),
            "strong_claims": st_, "level": _level(strong_weak, 0.60, 0.85)}


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


def conflict_depth(conflicts) -> dict:
    """[5] Not just the count — the *shape*. Build the contradiction graph from each conflict's
    claim_ids and report component count, the largest tangle, whether any component is cyclic
    (more edges than a tree), open/unresolved conflicts, and the worst topic. A flat 246 is far
    less critical than a few deep, cyclic tangles."""
    adj: dict[str, set] = defaultdict(set)
    edges = 0
    per_topic: Counter = Counter()
    open_conf = 0
    for cf in conflicts:
        if getattr(cf, "status", None) in (Status.RESOLVED if hasattr(Status, "RESOLVED") else (),):
            continue
        open_conf += 1
        per_topic[getattr(cf, "topic", None) or "?"] += 1
        ids = [str(x) for x in (getattr(cf, "claim_ids", None) or [])]
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
    return {"open_conflicts": open_conf, "components": len(comps), "max_component": max_comp,
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


def repetition(dev_summaries: list[str], selfmodel_texts: list[str]) -> dict:
    """[7] Repetition / dedup-loop: the share of 'developed' operations that were duplicates
    (no new link), and whether the self-model is re-minting near-identical traits (the historical
    re-mint bug is the reference case: same trait text repeated). Read from the protocol only."""
    dev_total = len(dev_summaries)
    dup = sum(1 for s in dev_summaries if "duplicate" in s.lower())
    dup_share = round(dup / dev_total, 3) if dev_total else 0.0
    # self-model repetition: distinct vs total recent self-model trait texts (stripped of digits,
    # so a count-only difference — exactly the old bug — reads as a repeat).
    stripped = ["".join(ch for ch in t if not ch.isdigit()) for t in selfmodel_texts]
    sm_repeat = round(1 - len(set(stripped)) / len(stripped), 3) if stripped else 0.0
    lvl = max(_level(dup_share, 0.85, 0.97), _level(sm_repeat, 0.5, 0.8), key=_RANK.get)
    return {"dev_total": dev_total, "duplicate_dev_share": dup_share,
            "selfmodel_repeat_ratio": sm_repeat, "level": lvl}


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

    evidence_of: Counter = Counter()
    for el in core.all(l9.ObjectType.EVIDENCE_LINK):
        cid = getattr(el, "claim_id", None)
        if cid:
            evidence_of[cid] += 1

    clusters = list(core.all(l9.ObjectType.SEMANTIC_CLUSTER))
    decidable_states = {"synthesis-eligible", "synthesis-rejected", "semantic-measured"}
    undecidable = sum(1 for o in clusters
                      if getattr(o, "semantic_state", None) not in decidable_states)
    vit = extensions.get("vitality", {})
    conflicts = list(core.all(l9.ObjectType.CONFLICT))

    # novelty + repetition from the protocol (deterministic fields only)
    notes = _read_protocol_tail(proto_path, frozenset({"note"}), 60)
    import re
    new_counts = [int(m.group(1)) for e in notes
                  if (m := re.search(r"· (\d+) new", e.get("summary", "")))]
    devs = [e.get("summary", "") for e in
            _read_protocol_tail(proto_path, frozenset({"developed"}), 200)]
    sms = [e.get("summary", "") for e in
           _read_protocol_tail(proto_path, frozenset({"self_review"}), 30)]

    metrics = {
        "top_bucket_dominance": top_bucket_dominance(topics),
        "topic_entropy": topic_entropy(topics),
        "weak_claim_ratio": weak_claim_ratio(claims, evidence_of),
        "degeneracy": degeneracy(vit, undecidable, len(clusters)),
        "conflict_depth": conflict_depth(conflicts),
        "novelty": novelty(new_counts),
        "repetition": repetition(devs, sms),
        "cold_replay": cold_replay(load_seconds),
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
        f"| 3 Weak-Claim (strong) | {m['weak_claim_ratio']['strong_weak_ratio']:.0%} "
        f"von {m['weak_claim_ratio']['strong_claims']} | {icon[m['weak_claim_ratio']['level']]} |",
        f"| 4 Degen/undecidable | degen {m['degeneracy']['degeneration_score']}, "
        f"decidable {m['degeneracy']['decidable_percent']:.0f}%, "
        f"{m['degeneracy']['unsupported_hypotheses']} unsupp. "
        f"| {icon[m['degeneracy']['level']]} |",
        f"| 5 Conflict-Tiefe | {m['conflict_depth']['open_conflicts']} offen, "
        f"max Tangle {m['conflict_depth']['max_component']}, "
        f"{m['conflict_depth']['cyclic_components']} zyklisch "
        f"| {icon[m['conflict_depth']['level']]} |",
        f"| 6 Novelty (7/30) | {m['novelty']['new_mean_7']:.2f} / "
        f"{m['novelty']['new_mean_30']:.2f}, "
        f"{m['novelty']['zero_new_share_30']:.0%} leer | {icon[m['novelty']['level']]} |",
        f"| 7 Repetition | dup-dev {m['repetition']['duplicate_dev_share']:.0%}, "
        f"self-model {m['repetition']['selfmodel_repeat_ratio']:.0%} "
        f"| {icon[m['repetition']['level']]} |",
        f"| 8 Cold-Replay | {m['cold_replay']['load_seconds']}s "
        f"| {icon[m['cold_replay']['level']]} |",
        "",
    ]
    return "\n".join(lines) + "\n"


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
