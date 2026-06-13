"""Joni autonomy - research, learn, and self-improve under the DESi rule.

Off the leash, on the record:
  * reads arXiv / Hacker News / Hugging Face for its current topics;
  * learns what fits and changes its mind on contradictions (audited);
  * builds *peripheral* improvements into itself, but never the protected core -
    core changes become asks for a human;
  * is frugal: deterministic and free by default, cheapest model only when measured
    necessary, under a hard weekly budget;
  * logs everything to an append-only protocol and a static public website.
"""

from __future__ import annotations

from . import governance
from .run import one_cycle

__all__ = ["one_cycle", "governance"]
