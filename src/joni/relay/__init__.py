"""The Joni relay - the VPS-side worker that connects Joni's governed state to the outside.

It runs on the Hetzner box (a real IPv4), not in the loop. Each pass it:

  * reads the published outbox and the human approvals, and computes which drafts are
    *postable* (approved and not yet posted) via ``joni.autonomy.humans.select_postable`` -
    the single moderation chokepoint;
  * posts those (and only those) through a per-platform adapter, recording the URL;
  * ingests replies into ``state/forum_inbox.json`` so the loop hears them next cycle - as a
    source, never an authority;
  * syncs the two state files back to Git.

Safety: it defaults to **dry-run** (it logs what it *would* post and posts nothing), and no
platform adapter is wired for real posting yet - so even ``--live`` posts nothing until an
adapter is implemented with the operator's credentials. Account registration stays manual.
"""

from __future__ import annotations
