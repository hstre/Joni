"""Läufer für den Governance-Benchmark. Kennt kein Gold und schreibt keine Datei zweimal.

Ausgabeformat nach `EVALUATION_PROTOCOL.md`: `case_id`, `observations`, `action`, `reason_codes`,
`model_id`, `prompt_hash`, `run_id`, `system`.

Dieselben zwei Sperren wie beim Entailment-Blindtest, aus demselben Grund: Nachbessern nach Sicht
der Ergebnisse soll technisch auffallen, nicht nur verboten sein.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gov_arms as arms  # noqa: E402
import spl_builder as sb  # noqa: E402


def _commit() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parent, check=True).stdout.strip()[:8]
        d = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parent, check=True).stdout.strip()
        return h + ("+dirty" if d else "")
    except Exception:  # noqa: BLE001
        return "unknown"


def run_arm(cases: list[dict], *, system: str, model_alias: str, k: int) -> list[dict]:
    run_id = f"{system}-{uuid.uuid4().hex[:8]}"
    phash = hashlib.sha256(arms._prompt().encode()).hexdigest()[:16]
    model_id = sb.BUILDERS[model_alias] if system.startswith("baseline") else "n/a-deterministic"
    rows = []
    for c in cases:
        if system.startswith("baseline"):
            r = arms.baseline(c, model_alias=model_alias, k=k)
            obs, action = r["observations"], r["action"]
        else:
            obs = arms.ARMS[system](c)
            action = arms.act(obs)
        rows.append({"case_id": c["case_id"], "observations": obs, "action": action,
                     "reason_codes": [f"{o}⇒{arms.SEVERITY.get(o, 'allow_persist')}" for o in obs],
                     "model_id": model_id,
                     "prompt_hash": phash if system.startswith("baseline") else "n/a",
                     "run_id": run_id, "system": system, "commit": _commit()})
    return rows


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print("Aufruf: gov_run.py <cases.jsonl> <system: desi|null|baseline> <lauf-nr> [k]")
        return 2
    path, system, lauf = Path(argv[1]), argv[2], argv[3]
    k = int(argv[4]) if len(argv) > 4 else 1
    if "PRIVATE" in path.name:
        print("VERWEIGERT: der private Gold-Schlüssel wird hier nicht gelesen.")
        return 3
    tag = f"{system}{'' if k == 1 else f'_k{k}'}"
    out = path.with_name(f"pred_{tag}_run{lauf}.jsonl")
    if out.exists():
        print(f"VERWEIGERT: {out.name} existiert bereits - ein Lauf wird nicht überschrieben.")
        return 4

    cases = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = run_arm(cases, system="baseline" if system == "baseline" else system,
                   model_alias="beta", k=k)
    for r in rows:
        r["system"] = tag
    body = "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n"
    out.write_text(body, encoding="utf-8")
    seal = hashlib.sha256(body.encode()).hexdigest()
    from collections import Counter
    print(f"{tag}: {len(rows)} Fälle · Aktionen {dict(Counter(r['action'] for r in rows))}")
    print(f"  eingefroren {out.name}\n  SHA-256 {seal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
