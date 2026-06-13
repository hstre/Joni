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
├── creativity engine   local, or the sibling Kevin engine    (creativity.py)
├── router + budget  cheapest capable tier; API on demand     (router.py)
├── model client     local small / specialist / external API  (model_client.py)
├── persistence      the whole identity to/from JSON          (persistence.py)
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

### Persistence — it actually lives on

The whole of Layer 9 (claims with their status history, goals, preferences, projects,
memory, conflicts, the ledger, the id counters and the tick) serialises to one JSON
document and reloads verbatim. Because ids are sequential and there is no PRNG, a
reloaded identity is the *same self* — same memories, same rejected ideas, same goals
in progress — it simply continues.

```bash
python -m joni --ticks 8 --state joni.json "your take on privacy?"   # runs, saves
python -m joni --ticks 4 --state joni.json "and now?"                # resumes, continues
```

The server persists automatically (`JONI_STATE`, default `~/.joni/state.json`): it
resumes on startup and saves after every mutation.

### Creativity engine — Kevin plugs in

New projects are not invented by the renderer; a creativity engine proposes them from
current state, then an audited operator starts them. Two implementations behind one
protocol: a deterministic **local** engine (default), or the sibling **Kevin**
creativity-routing engine — it frames *"how do I make progress on `<topic>`?"* as a
problem and routes it through unexplored-space → wild variation → method transfer →
selection. Enable with `JONI_USE_KEVIN=1` (install Kevin first, e.g. `pip install -e
../Kevin`); projects it proposes are credited to the `kevin` engine in the ledger.
Both are deterministic, so Joni stays replay-stable either way.

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
the voice moves. (`DEEPSEEK_API_KEY2` is also accepted; the real voice retries
transient egress failures via `JONI_LLM_RETRIES` / `JONI_LLM_BACKOFF`.)

Two CI workflows: the default one runs offline (MockModel) on every push; a separate
`live-deepseek` workflow runs `scripts/live_smoke.py` against the real voice on pushes
to `main` and on manual dispatch, using the `DEEPSEEK_API_KEY` repository secret. The
Epistemic View is identical under both voices — only the phrasing changes — which is
the whole point.

## Off the leash — autonomous research & self-improvement

Joni can run unattended, under **one DESi rule**: *he may not change his protected core
without asking.* He may research and build **peripheral** improvements into himself; any
change that would touch the protected core (`models`, `state`, `operators`, `conflict`,
`router`, `persistence`, `loops`, `renderer`, `identity`, `model_client`, …) is **blocked
and turned into an ask** — a GitHub issue for a human — never self-applied.

One cycle (`python -m joni.autonomy run`):

1. **governance fail-safe** — verify the protected core matches `joni_core.lock`; stop if not.
2. **read** arXiv / Hacker News / Hugging Face for his current topics.
3. **judge & learn** (deterministic, free): relevant findings become claims; contradictions
   are resolved as audited opinion changes.
4. **improve** — peripheral improvements (track a new topic, note a capability) are built in
   autonomously; core-touching ones become asks.
5. **stay frugal** — deterministic and **€0 by default**; a model is used only when DESi
   *measures* the free answer inadequate, and only the cheapest tier within a **hard weekly
   budget** (default €20, paced per run). OpenRouter cheapest → DeepSeek fallback.
6. **route through real DESi** (opt-in, `JONI_USE_DESI=1`) — with the sibling
   `desi-governance` package installed, Joni uses DESi's own `EpistemicRouter` (its
   empirical routing table picks the Pareto-cheapest capable model + cost, logged with
   DESi's reason) and DESi's deterministic **tool registry** — not just arithmetic, also
   `date_math`, `unit_conversion`, `retrieval`. Free table lookups (Joni classifies tasks
   itself, so DESi's paid classifier is never invoked); falls back to Joni's own frugal
   layer when DESi is absent. Install: `pip install -e ".[desi]"` (or `-e ../DESi`).
7. **publish** — append the [append-only protocol](protocol/protocol.jsonl) and regenerate
   the static site under [`docs/`](docs/) (GitHub Pages).

```bash
python -m joni.autonomy lock      # (human) freeze the protected core
python -m joni.autonomy verify    # check core vs lock
JONI_ONLINE=1 python -m joni.autonomy run   # one live cycle
```

Two safety walls: a **core hash-lock** (any drift halts the run) and a **write allowlist**
(`state/`, `protocol/`, `docs/` only — logic is never auto-written).

### Running it for a week

`.github/workflows/autonomy.yml` fires **every 15 minutes** (`workflow_dispatch` too), runs one cycle
with `JONI_ONLINE=1` and the `DEEPSEEK_API_KEY` / `OPENROUTER_API_KEY` secrets, files any
asks as issues, and commits `state/ protocol/ docs/` back to `main`. It **retires itself
after 7 days** (the schedule then no-ops). Enable **GitHub Pages → Deploy from branch →
`main` / `docs`** to publish the dashboard.

## Status

v0.1 — a runnable demonstrator of the architecture, not a product and not a claim of
personhood. The deterministic core carries all the logic; the voice is pluggable.
