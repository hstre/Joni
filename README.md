# Joni

**A DESi-based operative identity.** From the outside it reads like a person. Inside
there is no person — only controlled state and deterministic operators, every move an
append-only ledger event.

> We did not build a person and then mystify it. We built the *impression* of one —
> and we show, line by line, exactly how it is produced.

Joni is a member of the DESi / AleXiona / Kevin ecosystem and inherits its rule:
**LLM for language, rules for logic.** A model may give the identity a *voice*; it
never owns state. Memory, beliefs, goals, preferences, conflict resolution, routing
and budgeting are all deterministic and replay-stable.

---

## The two views

Joni always answers in **two views at once**:

- **Conversation View** — the seemingly autonomous figure.
- **Epistemic View** — the exact claim, goal, memory, operator, trigger, reviewer
  and ledger event that produced what it just said.

So nothing has to be taken on faith. When Joni says *"I've changed my mind about
that,"* the Epistemic View dissolves it into receipts:

```
"I used to think local-first models keep data fully private,
 but I have since rejected that."

  previous_claim : C-1        (the old belief)
  old_status     : active
  new_status     : rejected
  trigger        : contradictory_evidence
  operator       : conflict_resolution
  reviewed_by    : deepseek-chat
  ledger_event   : L9-14
```

The impression of personhood is real *as an impression*, and always one click from
being taken apart. That is the whole point — and the way the demonstrator draws
attention to the underlying DESi ideas: explicit epistemic state, controlled memory,
drift limitation, auditable self-change, budgeted model routing, and the separation
of content, method, role and validity.

---

## How the impression is produced

```
local DESi core
├── Layer 9          state, roles, goals, claims, conflicts   (state.py)
├── operators        the only ways to change, each audited    (operators.py)
├── conflict engine  deterministic contradiction detection    (conflict.py)
├── autobiographical memory   episodic, recalled by relevance (memory.py)
├── research harvester + improvement loop   evolution per tick (loops.py)
├── router + budget  cheapest capable tier; API on demand     (router.py)
├── model client     local small / specialist / external API  (model_client.py)
├── audit ledger     append-only receipts (L9-####)           (in state.py)
└── renderer         the two views, produced together         (renderer.py)
```

Each apparently personal trait maps to a mechanism:

| Looks like… | Is actually… |
|---|---|
| persistent memory | append-only episodic `MemoryEpisode`s |
| autobiographical continuity | the memory log, recalled by token overlap |
| recognisable preferences | `Preference`s formed from specific claims |
| own projects & topics | `Project`s + claim topics, started/abandoned by rule |
| reasoned changes of mind | `conflict_resolution` operators, each a ledger event |
| long-term goals | `Goal`s advanced deterministically each tick |
| using a strong model "when it matters" | the router escalating a *hard* turn to the external API, within budget |

### Living over time

A `tick` is one unit of lived time — deterministic and fully audited. It harvests a
finding, detects contradictions, **resolves them (the justified opinion changes)**,
advances a goal, and periodically forms a preference, starts or abandons a project.
Run many ticks and you get an identity that visibly evolves — drops ideas, picks up
new ones, makes progress — while every step stays a ledger event you can point at.

---

## Quickstart

```bash
make install        # pip install -e ".[dev]"  (no key, no network)
make test           # pytest
make lint           # ruff
make demo           # run 8 ticks, dump the ledger, ask about privacy in both views
make serve          # dual-pane UI at http://127.0.0.1:8000
```

CLI:

```bash
python -m joni --ticks 8 --ledger --auto "what's your take on privacy these days?"
```

Library:

```python
from joni import Joni

joni = Joni()
joni.live(ticks=8)                       # weeks, compressed: it evolves, audited
r = joni.respond("your take on privacy?")
print(r.conversation)                    # the apparent person
print(r.epistemic)                       # operator / trigger / reviewed_by / ledger_event
```

### Web UI / API

`make serve` opens a two-pane view: **Conversation** on the left (with controls to
advance time and ask), **Epistemic** on the right (the last utterance's full
derivation, plus tabs for live `state` and the append-only `ledger`, which highlights
the cited event).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/respond` | `{prompt}` → conversation + epistemic trace |
| `POST` | `/api/tick` / `/api/live` | advance one / many ticks |
| `GET`  | `/api/state` | claims, goals, projects, preferences, snapshot |
| `GET`  | `/api/ledger` | the append-only audit ledger |
| `POST` | `/api/reset` | reseed the identity |

---

## Design invariants (from DESi)

- **Closed enumerations** — statuses, triggers and operators are fixed sets.
- **Replay-stable, sequential ids** — `C-1`, `G-2`, `L9-14`, assigned by counters in
  a deterministic order. No PRNG: the same ticks always produce the same life.
- **Append-only audit** — the ledger records what happened; it is never rewritten.
- **No trait without a receipt** — every claim transition carries the ledger event id
  that recorded it. (There is a test for exactly this.)

## Language layer

Default is a deterministic `MockModel`: the renderer's brief is already grounded and
first-person, so offline output is faithful to Layer 9 with zero setup. To give Joni
a real voice (DeepSeek / GPT-4o — it only *rephrases* the brief, adds no facts):

```bash
pip install -e ".[llm]"
export DEEPSEEK_API_KEY=sk-...     # or DEEPSEEK_API_KEY2 / OPENAI_API_KEY
export JONI_USE_REAL_LLM=1
make demo
```

The engines, state, routing and ledger are byte-for-byte identical either way — only
the voice moves.

## Status

v0.1 — a runnable demonstrator of the architecture, not a product and not a claim of
personhood. The deterministic core carries all the logic; the voice is pluggable.
