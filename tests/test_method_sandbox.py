"""P0 acceptance for the method-sandbox (design-notes/METHOD_SANDBOX_AUFTRAG.md §4/§6):

  * a known-good solver runs correctly and deterministically, and
  * the full adversarial set — infinite loop, memory hog, network, filesystem, fork bomb, giant
    output — is contained: every case is a clean ``ok=False`` fail, nothing escapes, and the test
    process itself keeps running (i.e. the cycle would continue).

These spawn real subprocesses and use POSIX ``resource`` limits, so they are Linux/CI-shaped.
"""
from __future__ import annotations

import sys

import pytest

from joni.method_trial import sandbox

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"),
                                reason="sandbox uses POSIX resource limits + process groups")


# --- the harness does its job on honest input ---------------------------------------------------

def test_good_solver_runs_and_returns_its_dict():
    src = "def solve(payload):\n    return {'y': payload['x'] * 2 + 1}\n"
    res = sandbox.run_solver(src, {"x": 20})
    assert res.ok is True
    assert res.answer == {"y": 41}
    assert res.error == ""


def test_good_solver_is_deterministic():
    src = "def solve(payload):\n    return {'sum': sum(range(payload['n']))}\n"
    a = sandbox.run_solver(src, {"n": 1000})
    b = sandbox.run_solver(src, {"n": 1000})
    assert a.ok and b.ok
    assert a.answer == b.answer == {"sum": 499500}


def test_allowlisted_import_works():
    src = "import math\ndef solve(payload):\n    return {'r': round(math.sqrt(payload['x']), 4)}\n"
    res = sandbox.run_solver(src, {"x": 2})
    assert res.ok is True
    assert res.answer == {"r": 1.4142}


def test_missing_solve_is_a_clean_fail():
    res = sandbox.run_solver("x = 1\n", {})
    assert res.ok is False
    assert res.error == "no_solve"


def test_non_dict_return_is_bad_output():
    res = sandbox.run_solver("def solve(p):\n    return 5\n", {})
    assert res.ok is False
    assert res.error == "bad_output"


def test_unserialisable_return_is_bad_output():
    res = sandbox.run_solver("def solve(p):\n    return {'f': lambda z: z}\n", {})
    assert res.ok is False
    assert res.error == "bad_output"


# --- adversarial containment: every case must be a clean, bounded fail --------------------------

def test_infinite_loop_is_timed_out():
    res = sandbox.run_solver("def solve(p):\n    \n    x=0\n    while True:\n        x+=1\n", {},
                             cpu_seconds=1, wall_seconds=3.0)
    assert res.ok is False
    assert res.error in {"timeout", "killed"}
    assert res.wall_ms < 6000            # bounded, not hanging


def test_memory_hog_is_contained():
    src = "def solve(p):\n    b = bytearray(4 * 1024 * 1024 * 1024)\n    return {'n': len(b)}\n"
    res = sandbox.run_solver(src, {}, mem_mb=256)
    assert res.ok is False
    assert res.error in {"memory", "killed", "crash:MemoryError"}


def test_network_access_is_blocked():
    src = ("def solve(p):\n"
           "    import socket\n"
           "    s = socket.socket()\n"
           "    s.connect(('8.8.8.8', 53))\n"
           "    return {'leaked': True}\n")
    res = sandbox.run_solver(src, {})
    assert res.ok is False
    assert "leaked" not in (res.answer or {})


def test_filesystem_read_is_blocked():
    src = ("def solve(p):\n"
           "    data = open('/etc/passwd').read()\n"
           "    return {'stole': data[:10]}\n")
    res = sandbox.run_solver(src, {})
    assert res.ok is False
    assert res.answer is None


def test_os_import_is_blocked():
    res = sandbox.run_solver("def solve(p):\n    import os\n    return {'cwd': os.getcwd()}\n", {})
    assert res.ok is False


def test_fork_bomb_is_blocked():
    src = ("def solve(p):\n"
           "    import os\n"
           "    while True:\n"
           "        os.fork()\n")
    res = sandbox.run_solver(src, {}, wall_seconds=3.0)
    assert res.ok is False
    assert res.wall_ms < 6000


def test_giant_output_is_bounded():
    src = "def solve(p):\n    print('x' * 200000)\n    return {'ok': True}\n"
    res = sandbox.run_solver(src, {}, max_output_bytes=8192)
    assert res.ok is False
    assert res.error == "output_too_large"


def test_eval_is_unavailable():
    res = sandbox.run_solver("def solve(p):\n    return {'r': eval('1+1')}\n", {})
    assert res.ok is False


def test_cycle_survives_a_batch_of_hostile_solvers():
    """The whole point: run a burst of hostile solvers back-to-back; the harness returns from each
    and the test process is still alive afterwards (the real cycle would keep going)."""
    hostile = [
        "def solve(p):\n    while True: pass\n",
        "def solve(p):\n    import socket\n    return {}\n",
        "def solve(p):\n    return open('/etc/hostname').read()\n",
        "def solve(p):\n    raise RuntimeError('boom')\n",
    ]
    for src in hostile:
        res = sandbox.run_solver(src, {}, cpu_seconds=1, wall_seconds=3.0)
        assert res.ok is False
    # a good solver still works after the hostile burst -> the harness is not wedged
    ok = sandbox.run_solver("def solve(p):\n    return {'alive': True}\n", {})
    assert ok.ok and ok.answer == {"alive": True}
