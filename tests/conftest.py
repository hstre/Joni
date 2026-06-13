"""Test isolation.

Point the persisted-state file at a throwaway temp path *before* any test module
imports ``joni.api`` (which builds its shared identity at import time). Keeps tests
from reading or writing the real ``~/.joni/state.json``.
"""

import os
import tempfile
from pathlib import Path

os.environ["JONI_STATE"] = str(Path(tempfile.mkdtemp(prefix="joni-test-")) / "state.json")
# Default tests use the deterministic local engines, not Kevin or DESi.
os.environ.pop("JONI_USE_KEVIN", None)
os.environ.pop("JONI_USE_DESI", None)
