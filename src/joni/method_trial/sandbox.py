"""P0 of the method-sandbox (design-notes/METHOD_SANDBOX_AUFTRAG.md §4/§6): a safe, isolated
harness that runs an *untrusted* Python solver as pure computation and returns its answer — or a
clean failure — never letting it break the cycle or escape.

A solver is source that defines ``def solve(payload: dict) -> dict``. The harness runs it in a
**fresh child process** (never in-process ``exec``), reads the payload in / the answer out as JSON,
and contains it with layered defences:

* **Import allowlist** — the child's ``__import__`` only admits a small stdlib compute subset
  (``math``, ``statistics``, ``itertools``, ``re`` …). ``os``, ``sys``, ``socket``, ``subprocess``,
  ``ctypes``, ``io``, ``importlib`` … are unreachable, so net / file / fork / native code have no
  door. This is the primary containment.
* **Audit hook** (PEP 578) — a backstop that vetoes ``socket.*``, ``subprocess.*``, ``os.system``,
  ``open``, ``exec``/``compile``/``eval`` and non-allowlisted imports once the untrusted call is
  armed. An installed audit hook cannot be removed.
* **Curated builtins** — no ``open``/``exec``/``eval``/``compile``/``input``/``__import__``-raw.
* **Resource limits** (``resource.setrlimit``) — CPU seconds, address space, file size 0, core 0,
  open files. Plus a wall-clock ``timeout`` and a **process-group kill**, so an infinite loop, a
  memory hog, a fork bomb and a giant output all end as a bounded, clean fail.

**Threat model (honest).** This contains *pathological or buggy LLM-synthesised solver code* — the
P2 use case — with the ephemeral GitHub-Actions container as the outer trust boundary (Auftrag §4:
"Der GitHub-Actions-Job ist der äußere, ephemere Rahmen — die Sandbox ist der innere kontrollierte
Harness"). It is **not** a defence against a determined native-code exploit on a shared host; on a
stock runner without root we have no namespaces/seccomp, so the interpreter-level allowlist plus the
rlimits are the guarantee, and the disposable container is what makes that sufficient. Do not run
this outside such an ephemeral boundary and call it hardened.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass

# The compute-only stdlib subset a solver may import. Deliberately excludes anything with I/O,
# process, network, native-code or dynamic-import reach (os, sys, io, socket, subprocess, ctypes,
# importlib, pathlib, shutil, threading, multiprocessing, pickle, marshal, urllib, http, …).
_IMPORT_ALLOWLIST = frozenset({
    "math", "cmath", "statistics", "random", "itertools", "functools", "collections",
    "collections.abc", "re", "json", "string", "decimal", "fractions", "numbers",
    "datetime", "heapq", "bisect", "array", "textwrap", "unicodedata", "difflib", "operator",
    "copy", "enum", "dataclasses", "typing",
})

# Default limits. Generous enough for a real compute solver + interpreter start, tight enough that
# the adversarial cases trip quickly.
DEFAULT_CPU_SECONDS = 2
DEFAULT_WALL_SECONDS = 5.0
DEFAULT_MEM_MB = 512
DEFAULT_MAX_OUTPUT_BYTES = 256 * 1024

_OK_SENTINEL = "__JONI_SANDBOX_RESULT__"


@dataclass(frozen=True)
class SandboxResult:
    """The outcome of one solver run. ``ok`` means the solver returned a JSON dict within limits;
    on any failure ``answer`` is None and ``error`` carries a short, stable reason code
    (``timeout`` / ``memory`` / ``blocked:<what>`` / ``crash`` / ``bad_output`` / ``no_solve``)."""

    ok: bool
    answer: dict | None
    error: str
    wall_ms: int


# The child program. It runs under ``python -I -S`` (isolated, no site). Everything it needs is
# imported and captured BEFORE the untrusted solver is armed; after arming, the audit hook and the
# guarded __import__ are the only paths the untrusted code can take.
_CHILD = r'''
import sys, json, builtins, resource

def _set_limits(cpu, mem_bytes, nofile):
    def _lim(res, soft):
        try:
            resource.setrlimit(res, (soft, soft))
        except (ValueError, OSError):
            pass
    _lim(resource.RLIMIT_CPU, cpu)
    if mem_bytes:
        _lim(resource.RLIMIT_AS, mem_bytes)
    _lim(resource.RLIMIT_FSIZE, 0)      # no file writes at all
    _lim(resource.RLIMIT_CORE, 0)       # no core dumps
    _lim(resource.RLIMIT_NOFILE, nofile)
    try:
        # cap child/thread count as a fork-bomb backstop (best-effort; import allowlist is primary)
        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
        cur = soft if soft > 0 else 64
        resource.setrlimit(resource.RLIMIT_NPROC, (min(cur, 64), min(cur, 64)))
    except (ValueError, OSError, AttributeError):
        pass

_cfg = json.loads(sys.stdin.read())
_set_limits(int(_cfg["cpu"]), int(_cfg["mem_bytes"]), int(_cfg["nofile"]))

_ALLOW = set(_cfg["allow"])
_armed = [False]

def _guard_import(name, globals=None, locals=None, fromlist=(), level=0):
    if _armed[0] and name.split(".")[0] not in _ALLOW:
        raise ImportError("import blocked in sandbox: %r" % name)
    return _real_import(name, globals, locals, fromlist, level)

_real_import = builtins.__import__

# A curated builtins map: no open/exec/eval/compile/input/__import__-raw/help/breakpoint.
_BAD = {"open", "exec", "eval", "compile", "input", "help", "breakpoint",
        "__import__", "memoryview", "vars", "globals", "locals"}
_safe_builtins = {k: getattr(builtins, k) for k in dir(builtins) if k not in _BAD}
_safe_builtins["__import__"] = _guard_import

_BLOCK_PREFIX = ("socket.", "subprocess.", "os.", "ctypes.", "importlib.", "shutil.",
                 "webbrowser.", "urllib.", "http.", "ftplib.", "smtplib.", "pickle.",
                 "marshal.", "threading.", "multiprocessing.")
_BLOCK_EXACT = {"open", "os.system", "os.exec", "os.fork", "os.posix_spawn", "os.spawn",
                "exec", "compile", "eval", "code.__new__", "cpython.run_module"}

def _audit(event, args):
    if not _armed[0]:
        return
    if event in _BLOCK_EXACT or event.startswith(_BLOCK_PREFIX):
        raise PermissionError("blocked:%s" % event)
    if event == "import":
        mod = (args[0] or "").split(".")[0]
        if mod and mod not in _ALLOW:
            raise PermissionError("blocked:import:%s" % mod)

sys.addaudithook(_audit)

_src = _cfg["src"]
_payload = _cfg["payload"]
_ns = {"__builtins__": _safe_builtins, "__name__": "__solver__"}
_result = {"e": "crash:unknown"}
try:
    _code = compile(_src, "<solver>", "exec")   # compile while unarmed (trusted step)
    exec(_code, _ns)                              # defines solve(); does not run its body
    _solve = _ns.get("solve")
    if not callable(_solve):
        _result = {"e": "no_solve"}
    else:
        _armed[0] = True                         # arm: from here the untrusted body runs guarded
        _ans = _solve(_payload)
        _armed[0] = False
        if not isinstance(_ans, dict):
            _result = {"e": "bad_output"}
        else:
            try:
                json.dumps(_ans)                 # answer must be JSON-serialisable
                _result = {"a": _ans}
            except (TypeError, ValueError):
                _result = {"e": "bad_output"}
except PermissionError as _pe:
    _result = {"e": str(_pe)}
except MemoryError:
    _result = {"e": "memory"}
except BaseException as _exc:        # noqa: BLE001 - any solver failure is a clean, bounded fail
    _result = {"e": "crash:%s" % type(_exc).__name__}
_armed[0] = False                                # disarm before the trusted final write
try:
    _out = json.dumps(_result)
except (TypeError, ValueError):
    _out = json.dumps({"e": "bad_output"})
print("__JONI_SANDBOX_RESULT__" + _out)
'''


def run_solver(solver_src: str, payload: dict, *,
               cpu_seconds: int = DEFAULT_CPU_SECONDS,
               wall_seconds: float = DEFAULT_WALL_SECONDS,
               mem_mb: int = DEFAULT_MEM_MB,
               max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES) -> SandboxResult:
    """Run ``solver_src`` (defining ``solve(payload)->dict``) on ``payload`` in an isolated child.
    Always returns a :class:`SandboxResult`; never raises for a solver fault, a limit breach or a
    containment block. A timeout kills the whole process group."""
    import time
    cfg = json.dumps({
        "src": solver_src, "payload": payload, "cpu": int(cpu_seconds),
        "mem_bytes": int(mem_mb) * 1024 * 1024, "nofile": 64,
        "allow": sorted(_IMPORT_ALLOWLIST),
    })
    scratch = tempfile.mkdtemp(prefix="joni-sandbox-")
    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", _CHILD],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=scratch, start_new_session=True,      # own process group -> group-kill on timeout
            env={"PATH": "/usr/bin:/bin"},            # minimal, no inherited secrets
            text=True,
        )
    except OSError:
        _rmtree(scratch)
        return SandboxResult(False, None, "spawn_failed", int((time.monotonic() - start) * 1000))

    try:
        out, _ = proc.communicate(cfg, timeout=wall_seconds)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        with contextlib.suppress(subprocess.TimeoutExpired, ValueError):
            proc.communicate(timeout=2)
        _rmtree(scratch)
        return SandboxResult(False, None, "timeout", int((time.monotonic() - start) * 1000))
    finally:
        _rmtree(scratch)

    wall_ms = int((time.monotonic() - start) * 1000)
    if out is not None and len(out) > max_output_bytes:
        return SandboxResult(False, None, "output_too_large", wall_ms)

    line = _last_sentinel_line(out or "")
    if line is None:
        # No result line: the child was killed by a limit (CPU/memory via SIGKILL) or died hard.
        if proc.returncode and proc.returncode < 0:
            return SandboxResult(False, None, "killed", wall_ms)
        return SandboxResult(False, None, "no_result", wall_ms)
    try:
        obj = json.loads(line[len(_OK_SENTINEL):])
    except (ValueError, TypeError):
        return SandboxResult(False, None, "bad_output", wall_ms)
    if "a" in obj and isinstance(obj["a"], dict):
        return SandboxResult(True, obj["a"], "", wall_ms)
    return SandboxResult(False, None, str(obj.get("e", "crash")), wall_ms)


def _last_sentinel_line(out: str) -> str | None:
    for line in reversed(out.splitlines()):
        if line.startswith(_OK_SENTINEL):
            return line
    return None


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), 9)
    except (ProcessLookupError, PermissionError, OSError):
        with contextlib.suppress(OSError):
            proc.kill()


def _rmtree(path: str) -> None:
    import shutil
    with contextlib.suppress(OSError):
        shutil.rmtree(path, ignore_errors=True)


__all__ = ["SandboxResult", "run_solver", "DEFAULT_CPU_SECONDS", "DEFAULT_WALL_SECONDS",
           "DEFAULT_MEM_MB", "DEFAULT_MAX_OUTPUT_BYTES"]
