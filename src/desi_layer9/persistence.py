"""Persistence and replay.

The authoritative state is a deterministic function of the recorded operations:
``state = replay(journal)``. So persistence stores the **journal** (plus the seed tick
and schema version); loading replays it to reconstruct the identical objects, ledger and
hash chain. A snapshot may accelerate startup but never replaces the journal.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import snapshot
from .core import JournalEntry, Layer9, make_proposal
from .hashing import snapshot_hash, verify_chain
from .provenance import Provenance

SCHEMA_VERSION = 1


def replay(journal: list[JournalEntry], *, tick: int = 0) -> Layer9:
    """Reconstruct state from a journal. Deterministic - no PRNG anywhere.

    Each entry restores the core tick it ran at (legacy entries default to 0), so a journal
    that spans a tick change reproduces the exact historical ``created_tick`` values - and
    therefore its own snapshot hash.
    """
    core = Layer9(_tick=tick)
    for entry in journal:
        core._tick = entry.tick                       # internal write path (kernel-only replay)
        proposal = make_proposal(
            entry.proposal_type, entry.operator, payload=dict(entry.payload),
            proposer=entry.proposer, provenance=Provenance.from_dict(entry.provenance),
            reason=entry.reason, target_objects=entry.target_objects,
        )
        core.submit(proposal, actor=entry.actor, governance_approved=entry.governance_approved)
    if journal:
        core._tick = journal[-1].tick
    return core


def _fast_load_enabled() -> bool:
    """The snapshot fast-load is OPT-IN (``JONI_FAST_LOAD=1``). Default OFF preserves the exact
    current behaviour: state is always re-derived by replaying the journal (the source of truth, and
    the gate re-enforcement that goes with it). Enabling it TRUSTS the bot-written snapshot as a
    verified cache - a deliberate speed/integrity trade-off the deployment opts into."""
    return os.getenv("JONI_FAST_LOAD", "0") == "1"


def _sidecar_path(path: Path) -> Path:
    """The fast-load snapshot lives in a SIDECAR next to the committed file (e.g.
    ``layer9.json`` -> ``layer9.snapshot.json``), never inside it. The committed file stays
    journal-only (small, no multi-MB snapshot in git); the sidecar is git-ignored, so it survives a
    ``git reset --hard`` as an untracked file and speeds every cycle after the first of a job."""
    return path.with_name(path.stem + ".snapshot.json")


# ---- chunked journal on disk ------------------------------------------------------------------ #
# The journal is append-only, but storing it as ONE ever-growing file made every commit re-store
# a multi-MB blob (git's delta chains cap out and periodically store near-full copies): the state
# file alone accounted for the bulk of the repository's growth. On disk the journal is therefore
# split into SEALED chunks (a full chunk never changes again -> git stores it exactly once) plus
# one small active tail chunk. The in-memory contract is unchanged: ``to_doc``/``from_doc`` still
# speak a single journal list, and load verifies the reassembled journal against the recorded
# ``snapshot_hash`` and the ledger chain - a missing, truncated or tampered chunk cannot load.

def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` crash-safely: write a sibling temp file, flush+fsync it, then
    ``os.replace`` (atomic on POSIX). A kill at any point leaves either the old file intact or the
    new file complete - never a half-written/truncated file. Used for every state file so an
    interrupted ``save`` can never corrupt the head or a chunk in place."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _chunk_size() -> int:
    """Entries per chunk. ``JONI_JOURNAL_CHUNK=0`` disables chunking (legacy inline journal)."""
    return max(0, int(os.getenv("JONI_JOURNAL_CHUNK", "2000")))


def _chunk_dir(path: Path) -> Path:
    return path.with_name(path.stem + ".journal")


def _write_chunks(entries: list[dict], path: Path) -> list[dict]:
    """Write the journal as chunk files next to ``path``; return the head's file manifest.
    A sealed (full) chunk whose recorded entry count matches the previous head is NOT rewritten -
    append-only means its content cannot have changed; only the active tail chunk churns."""
    n = _chunk_size()
    cdir = _chunk_dir(path)
    cdir.mkdir(parents=True, exist_ok=True)
    prior: dict[str, int] = {}
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            for f in (old.get("journal_chunks") or {}).get("files", []):
                prior[str(f.get("name"))] = int(f.get("entries", -1))
        except Exception:  # noqa: BLE001 - an unreadable old head just means we rewrite everything
            prior = {}
    files: list[dict] = []
    for idx in range(max(1, -(-len(entries) // n))):
        chunk = entries[idx * n:(idx + 1) * n]
        name = f"chunk-{idx + 1:06d}.jsonl"
        sealed = len(chunk) == n
        fp = cdir / name
        if not (sealed and prior.get(name) == n and fp.exists()):
            _atomic_write(fp, "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in chunk))
        files.append({"name": name, "entries": len(chunk)})
    keep = {f["name"] for f in files}
    for fp in cdir.glob("chunk-*.jsonl"):
        if fp.name not in keep:                       # a compaction shrank the journal: drop stale
            fp.unlink()
    return files


def _read_doc(path: Path) -> dict | None:
    """Read a state doc in either on-disk format: legacy (inline ``journal``) or chunked
    (``journal_chunks`` manifest + JSONL chunk files). Returns the doc with ``journal`` inlined.
    A chunk whose entry count disagrees with the head manifest refuses to load - the snapshot-hash
    and chain verification downstream would catch content tampering; this catches truncation with
    a message that names the file."""
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    jc = doc.get("journal_chunks")
    if jc and "journal" not in doc:
        cdir = _chunk_dir(path)
        entries: list[dict] = []
        files = jc.get("files", [])
        for i, f in enumerate(files):
            fp = cdir / str(f.get("name"))
            recorded = int(f.get("entries", -1))
            lines = [line for line in fp.read_text(encoding="utf-8").splitlines() if line.strip()]
            is_tail = i == len(files) - 1
            # A sealed (non-tail) chunk is immutable, so its count must match EXACTLY - any
            # mismatch is truncation or tampering and hard-stops (the snapshot-hash/chain check
            # downstream catches modified content; this names a size mismatch). The TAIL chunk may
            # legitimately hold MORE than the head records: ``save`` writes the tail then the head
            # atomically, so a crash in between leaves extra, uncommitted entries in the tail. Those
            # are not part of the committed state (the head is the commit point), so we read exactly
            # the recorded prefix and drop the excess - recovering the last committed state instead
            # of refusing to load. FEWER than recorded is still corruption and hard-stops.
            if len(lines) < recorded or (len(lines) != recorded and not is_tail):
                raise ValueError(f"journal chunk {fp.name}: {len(lines)} entries on disk, head "
                                 f"records {recorded} - refusing to load")
            entries.extend(json.loads(line) for line in lines[:recorded])
        doc["journal"] = entries
    return doc


def to_doc(state: Layer9) -> dict:
    # Journal-only, ALWAYS. The snapshot never goes in here - it is written to the sidecar by
    # ``save``. This keeps the committed state file small regardless of fast-load.
    return {
        "schema_version": SCHEMA_VERSION,
        "tick": state.tick,
        "snapshot_hash": snapshot_hash(state),
        "journal": [e.to_dict() for e in state.journal],
    }


def from_doc(doc: dict, *, verify: bool = True, sidecar: dict | None = None) -> Layer9:
    journal = [JournalEntry.from_dict(e) for e in doc.get("journal", [])]
    recorded = doc.get("snapshot_hash")
    # FAST PATH (opt-in, verify=True, sidecar present): restore the sidecar snapshot and accept it
    # ONLY if it reproduces the committed file's ``snapshot_hash`` AND verify_chain passes. Any
    # problem -> replay instead. So it only ever skips work, never changes the result.
    snap = (sidecar or {}).get("state_snapshot")
    if _fast_load_enabled() and verify and snap is not None:
        try:
            state = snapshot.restore(snap, journal, tick=int(doc.get("tick", 0)))
            ok_chain, _ = verify_chain(state)
            if ok_chain and recorded and snapshot_hash(state) == recorded:
                return state
        except Exception:  # noqa: BLE001 - a malformed/old sidecar is never fatal; replay instead
            pass
    # SLOW PATH: full replay - the journal is the source of truth.
    state = replay(journal, tick=int(doc.get("tick", 0)))
    if verify:
        # Integrity: the reconstructed state must match the recorded snapshot.
        if recorded and snapshot_hash(state) != recorded:
            raise ValueError("replay snapshot hash mismatch - journal or snapshot corrupted")
        ok, problems = verify_chain(state)
        if not ok:
            raise ValueError("ledger chain broken on load: " + "; ".join(problems))
    return state


def save(state: Layer9, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = to_doc(state)
    if _chunk_size():
        # Chunked on-disk format: sealed immutable chunk files + a small head. The head carries
        # the same tick/snapshot_hash contract; only WHERE the journal lives changes.
        doc["journal_chunks"] = {"files": _write_chunks(doc.pop("journal"), path)}
    # The head is written LAST and atomically: it is the commit point that names each chunk and its
    # entry count, so it must land whole and only after every chunk it references is on disk.
    _atomic_write(path, json.dumps(doc, ensure_ascii=False, indent=2))
    sidecar = _sidecar_path(path)
    if _fast_load_enabled():
        # Write the verified fast-load cache alongside (git-ignored). It carries the same hash the
        # committed file records, so ``load`` can confirm the sidecar matches this exact journal.
        _atomic_write(sidecar, json.dumps(
            {"snapshot_hash": snapshot_hash(state), "tick": state.tick,
             "state_snapshot": snapshot.capture(state)}, ensure_ascii=False))
    elif sidecar.exists():
        sidecar.unlink()                              # fast-load off: never leave a stale sidecar
    return path


def load(path: str | Path, *, verify: bool = True) -> Layer9 | None:
    path = Path(path)
    doc = _read_doc(path)
    if doc is None:
        return None
    sidecar = None
    sc_path = _sidecar_path(path)
    if _fast_load_enabled() and sc_path.exists():
        try:
            sidecar = json.loads(sc_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a garbled sidecar just means we replay
            sidecar = None
    return from_doc(doc, verify=verify, sidecar=sidecar)


# Journal payload fields that are DERIVED detail - stored for audit but never read by any state
# logic - and that grew without bound (the semantic per-pair log is O(members²) and reached tens of
# MB across the run). Compaction drops them: the decision/state/rationale already carry the verdict,
# so the reconstructed claim graph is unchanged; only the dead weight goes.
_COMPACTABLE_MEASUREMENT_KEYS = ("pairs",)


def compact(path: str | Path, *, out: str | Path | None = None) -> dict:
    """One-time maintenance: slim the journal by dropping dead, derived measurement blobs, then
    re-derive the state and RE-SEAL it (fresh snapshot_hash + ledger chain).

    The append-only journal had bloated to tens of MB (90% of it the O(n²) ``measurement.pairs``
    log written by the semantic adapter - stored but never read), so a fresh job's full replay no
    longer finished inside a cycle. Stripping that field changes no decision (no logic consults it),
    so the rebuilt claim graph is identical bar the removed dead detail; the result is a small,
    fully-replayable, chain-valid file. The audit history (every entry, its decision and members)
    is preserved. Returns a small summary; raises if the slimmed journal does not load cleanly."""
    path = Path(path)
    doc = _read_doc(path)
    before_entries = len(doc.get("journal", []))
    stripped = 0
    for e in doc.get("journal", []):
        m = (e.get("payload") or {}).get("measurement")
        if isinstance(m, dict):
            for k in _COMPACTABLE_MEASUREMENT_KEYS:
                if k in m:
                    m.pop(k, None)
                    stripped += 1
    journal = [JournalEntry.from_dict(e) for e in doc.get("journal", [])]
    state = replay(journal, tick=int(doc.get("tick", 0)))     # rebuild from the slimmed journal
    out_path = Path(out) if out else path
    save(state, out_path)                                     # journal-only doc + fresh hash
    reloaded = load(out_path, verify=True)                    # must load + verify_chain cleanly
    if reloaded is None or snapshot_hash(reloaded) != snapshot_hash(state):
        raise ValueError("compaction produced a file that does not reload to the same state")
    return {"entries": before_entries, "fields_stripped": stripped,
            "snapshot_hash": snapshot_hash(state)}


def repair(path: str | Path) -> bool:
    """Re-seal a state whose recorded SNAPSHOT hash drifted while the ledger chain is still intact.

    The only legitimate case is a snapshot-hash mismatch with an unbroken chain (e.g. a state
    written before per-entry ticks were journalled, after a midnight tick rollover). A BROKEN CHAIN
    means possible tampering and must hard-stop, never be silently re-blessed: a blanket
    ``except ValueError: re-save`` would launder a corrupted journal into a self-consistent file.
    Returns True if a repair was needed; raises if the state is not safely repairable.
    """
    path = Path(path)
    if not path.exists():
        return False
    doc = _read_doc(path)
    try:
        from_doc(doc, verify=True)
        return False                                  # already loads cleanly - nothing to do
    except ValueError:
        pass
    state = from_doc(doc, verify=False)               # replay-only; deterministic
    ok, problems = verify_chain(state)
    if not ok:                                        # tampering, not drift - refuse to re-bless
        raise ValueError("ledger chain broken - refusing to repair (possible tampering): "
                         + "; ".join(problems))
    recorded = doc.get("snapshot_hash")
    if not (recorded and snapshot_hash(state) != recorded):
        # chain intact AND snapshot already matches: the load failed for some other reason we do
        # not understand - do not paper over it.
        raise ValueError("repair: verify failed but chain intact and snapshot matches - refusing")
    save(state, path)                                 # the one safe case: re-seal the snapshot hash
    from_doc(_read_doc(path), verify=True)            # must load cleanly now
    return True
