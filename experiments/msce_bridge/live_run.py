"""Der echte End-to-End-Lauf: MSCEs eigene Prompts, wörtlich, auf echten Agenten-Traces.

Bis hierher war der Korpus Test-Fixtures. Das war die grösste Einschränkung des Experiments, und
sie fällt hier: die L2- und L3-Prompts werden **verbatim aus MSCEs Quelltext extrahiert** (nicht
paraphrasiert), auf **echte L1-Traces** angewandt und von einem echten LLM ausgeführt. Was
herauskommt, ist genuine MSCE-Ausgabe - und die wird dann von DESi beurteilt.

Datenquelle: Jonis eigenes Protokoll (``protocol/*.jsonl``) - reale Langzeit-Agenten-Erfahrung mit
Zustand, Handlung und Ausgang über hunderte Zyklen. Das ist genau die Domäne, auf die MSCE zielt
(long-horizon LLM agents), und es ist echte Historie, keine erfundene.

Kette:
    Protokoll-Events → Signatur-Buckets (nach ``kind``) → MSCEs L2-Prompt → echte L2-Policies
                     → Kohorte → MSCEs L3-Prompt → echte L3-Weltmodelle → DESi-Urteil

Aufruf::

    source .../secrets/ds.env
    DESI_ROOT=<desi> PYTHONPATH=src:<desi>/src python experiments/msce_bridge/live_run.py

Der Schlüssel wird ausschliesslich aus der Umgebung gelesen und nie geschrieben. Die Ausgabe landet
in ``live_l2.json`` / ``live_l3.json`` neben diesem Skript, damit das Urteil reproduzierbar bleibt.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_HERE))

MEMOS = Path(os.getenv("MEMOS_ROOT", _ROOT.parent / "memos"))
PROMPTS = MEMOS / "apps/memos-local-plugin/core/llm/prompts"
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"


def extract_system_prompt(ts_file: Path) -> str:
    """Pull the ``system:`` template literal out of MSCE's prompt module, verbatim.

    Deliberately not paraphrased - the whole point is to run THEIR prompt, so any finding is about
    MSCE's pipeline and not about my rewording of it.
    """
    src = ts_file.read_text(encoding="utf-8")
    m = re.search(r"system:\s*`(.*?)`,\s*\n\};", src, re.S)
    if not m:
        m = re.search(r"system:\s*`(.*?)`", src, re.S)
    if not m:
        raise SystemExit(f"kein system-Prompt in {ts_file}")
    return m.group(1)


def call_llm(system: str, user: str, *, temperature: float = 0.15) -> dict:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY fehlt - erst die env-Datei sourcen")
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:      # noqa: S310 - fixed https endpoint
        payload = json.loads(r.read())
    return json.loads(payload["choices"][0]["message"]["content"])


def load_traces(limit_per_bucket: int = 6) -> dict[str, list[dict]]:
    """Real L1 traces from Joni's protocol, shaped into MSCE's input record.

    MSCE's L2 prompt expects ``{state_summary, action, outcome, utility}`` records sharing a state
    signature. The protocol's ``kind`` IS a state signature (what situation the loop was in), so it
    is used as the bucket key - no invented clustering.
    """
    buckets: dict[str, list[dict]] = defaultdict(list)
    for path in sorted((_ROOT / "protocol").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = str(ev.get("kind", ""))
            summary = str(ev.get("summary", ""))
            if not kind or not summary:
                continue
            buckets[kind].append({
                "trace_id": f"tr_{kind}_{ev.get('cycle', 0)}",
                "state_summary": f"cycle {ev.get('cycle')}, phase '{kind}'",
                "action": summary[:300],
                "outcome": str(ev.get("refs", ""))[:200],
                "utility": 0.0 if ev.get("cost_eur", 0) == 0 else 1.0,
            })
    return {k: v[-limit_per_bucket:] for k, v in buckets.items() if len(v) >= 4}


def main() -> int:
    l2_system = extract_system_prompt(PROMPTS / "l2-induction.ts")
    l3_system = extract_system_prompt(PROMPTS / "l3-abstraction.ts")
    print(f"MSCE-Prompts verbatim extrahiert: L2 {len(l2_system)} Zeichen · "
          f"L3 {len(l3_system)} Zeichen")

    buckets = load_traces()
    picked = sorted(buckets, key=lambda k: -len(buckets[k]))[:int(os.getenv("N_BUCKETS", "5"))]
    print(f"Echte Trace-Buckets: {len(buckets)} gefunden, {len(picked)} verwendet -> {picked}\n")

    policies = []
    for i, kind in enumerate(picked):
        user = ("TRACES (same state signature):\n"
                + json.dumps(buckets[kind], ensure_ascii=False, indent=1))
        try:
            pol = call_llm(l2_system, user)
        except Exception as exc:  # noqa: BLE001 - a failed call is data, not a crash
            print(f"  L2 [{kind}] FEHLER: {type(exc).__name__}: {exc}")
            continue
        pol["id"] = f"po_{i + 1}"
        pol["_bucket"] = kind
        pol["_trace_ids"] = [t["trace_id"] for t in buckets[kind]]
        policies.append(pol)
        print(f"  L2 [{kind}] -> {str(pol.get('trigger', pol.get('title', '?')))[:80]}")

    (_HERE / "live_l2.json").write_text(
        json.dumps(policies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(policies)} echte L2-Policies -> live_l2.json")

    if not policies:
        return 1
    user3 = ("POLICIES (compatible domain cohort):\n"
             + json.dumps(policies, ensure_ascii=False, indent=1))
    world = call_llm(l3_system, user3)
    world["id"] = "world_live_1"
    world["policyIds"] = [p["id"] for p in policies]
    world["sourceEpisodeIds"] = sorted({t for p in policies for t in p["_trace_ids"]})
    world["structure"] = {k: world.get(k, []) for k in
                          ("environment", "inference", "constraints")}
    (_HERE / "live_l3.json").write_text(
        json.dumps([world], ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(len(world["structure"][k]) for k in world["structure"])
    print(f"1 echtes L3-Weltmodell mit {n} Einträgen -> live_l3.json")
    print(f"   Titel: {world.get('title', '')}")
    print(f"   confidence (selbst gemeldet): {world.get('confidence')}")

    import adjudicate
    res = adjudicate.adjudicate(world)
    print("\n" + adjudicate.render(res))
    by: dict[str, int] = {}
    for e in res["entries"]:
        by[e["state"]] = by.get(e["state"], 0) + 1
    print(f"\n=== DESi-Urteil über ECHTE MSCE-Ausgabe: {by} ===")
    anchored = sum(1 for e in res["entries"]
                   if all(c["pass"] for c in e["checks"] if c["check"].startswith("C1")))
    print(f"=== verankert: {anchored}/{len(res['entries'])} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
