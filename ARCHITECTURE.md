# Architecture

The memory is plain Markdown files in a Git repo, organized into three layers by **how often the agent needs them**. Everything else follows from that one question: how often does the agent need this file?

```text
memory/
├── BRAIN.md               operating manual + decision rules     ← boot layer:
├── LINEAGE.md             continuity handoff from last session     loaded EVERY
├── MEMORY.md              auto-generated lookup index              session, terse
├── feedback/              lessons from real mistakes            ← on-demand layer:
├── knowledge/             how tools / skills / systems work        opened only
│   ├── tools/             how each integration actually behaves    when the task
│   ├── skills/            reusable how-to playbooks                needs it
│   └── infra/             system, environment, running jobs
├── projects/              live state of ongoing work
└── reference/             stable lookups (people, IDs, links)

scripts/                   dependency-free Python
├── memory-index.py        regenerate MEMORY.md from frontmatter
└── memory-check.py        staleness + structural invariants
```

## The core tension: every session pays for the boot layer

Claude Code re-reads its boot context on every session, and every token is sent to the model on every request. So the boot layer has a hard budget. If you let it grow, you pay forever.

The resolution is a deliberate **two-tier split**:

| | Boot layer | On-demand layer |
|---|---|---|
| Loaded | every session | only when the task calls for it |
| Style | terse, pointers | verbose, full reasoning |
| Job | "here's the map, and where to look" | "here's exactly how to do X" |
| Cost | paid every session | paid only when opened |

This is why `BRAIN.md` is a *map*, not an encyclopedia. It points to detail; it doesn't contain it. A memory that grows from 10 to 200 files keeps a flat boot cost, because the 190 new files live in the on-demand layer and only load when `grep` says they're relevant.

## The three layers

### 1. Boot layer — loaded every session

**`BRAIN.md`** — the operating manual. Who the agent is working with, what it can do, and the **decision rules**: a do / ask / never matrix that tells the agent when to act autonomously, when to stop and confirm, and what's always forbidden (e.g. never exfiltrate secrets, never run an irreversible external action without a green light). This is what lets the agent act on its own judgment instead of checking everything with you.

**`LINEAGE.md`** — continuity. At the end of each session the agent appends a short handoff: what was done, key decisions, what's left open, and what the *next* session must not break. The next session reads this first. Without it, every session re-discovers context from scratch. Old entries roll over into a greppable archive so the live file stays short (see *Continuity & rollover*).

**`MEMORY.md`** — the lookup index. One line per on-demand file: its name, path, and a one-sentence description pulled from the file's frontmatter. The agent skims this to know *what exists* and *what to open*, without loading any of it. **This file is generated** — never hand-edited — by `scripts/memory-index.py`.

### 2. On-demand layer — loaded only when relevant

Everything the agent might need but rarely all at once. Each file is **one fact, one job**, with a frontmatter header (see [DOCTRINE.md](DOCTRINE.md) for the schema):

- **`feedback/`** — the learning core. Each file captures one correction or confirmed approach: the trigger, *why* it's right, and the anti-pattern to avoid. This is where the agent's mistakes turn into never-again rules.
- **`knowledge/tools/`** — how a specific integration *actually* behaves, including the gotchas docs won't tell you.
- **`knowledge/skills/`** — reusable playbooks for recurring multi-step tasks.
- **`knowledge/infra/`** — the system itself: environment quirks, background jobs, how the pieces wire together.
- **`projects/`** — the live state of each ongoing piece of work, so any session can resume it.
- **`reference/`** — stable lookups: people and their roles, resource IDs, external links.

Files are found by `grep`, not by being pre-loaded. That's why naming and the one-line description matter so much (see DOCTRINE — *greppable slug*).

### 3. Automation — for the parts a machine can keep honest

The *bookkeeping* around the memory shouldn't depend on a human remembering it. A few small mechanisms remove that dependency — but be clear about the scope: they automate the **hygiene**, not the **learning**. Writing the files honestly is still discipline (README → *What this is not*); these just keep the structure around it from rotting.

- **`scripts/memory-index.py`** — scans every file's frontmatter and regenerates the `MEMORY.md` index. The index is never out of sync because it's never written by hand.
- **`scripts/memory-check.py`** — two jobs. *Staleness*: flags files whose `last_verified` date (or `last_edited`, if absent) is older than a per-type threshold (a `project` goes stale in 30 days; a `feedback` lesson never does). *Invariants*: structural gates you can run in CI — every file has required frontmatter keys, its `type` is a known one, no duplicate frontmatter keys, the markdown links in the boot files (BRAIN/MEMORY) resolve to real files, and the lookup index is current.
- **`scripts/handover-lint.py`** — a commit-time check that scans the latest `### Handoff` block and rejects hedge-word agenda ("consider", "recommend", "for next session"). Wire it as a pre-commit hook to hold the handoff to *state, not agenda* mechanically rather than by good intentions.
- **A `Stop` hook (you wire it yourself)** — Claude Code can run a command when a session ends; point it at a one-line append to an activity log and at `memory-index.py`, and that log and index maintain themselves. The repo doesn't ship the hook — it's a few lines specific to your shell and paths — but once wired, that bookkeeping stops being a thing you remember to do. The *learning* loop, though, is not on this list: nothing here makes the agent write a lesson. That stays discipline.

## Continuity & rollover

`LINEAGE.md` would grow without bound, so it has a rollover: once it holds more than N sessions, the older ones move verbatim into `archive/` (one file per session) and only the most recent stays in the live, boot-loaded file. Nothing is compressed or summarized away — every past session is recoverable by `grep` — but the boot cost stays constant. This is the same principle as the two-tier split, applied over time instead of across topics.

## Why plain files

A database or a vector store would also work, and for some shapes it's the better tool. This architecture deliberately chooses plain Markdown in Git because:

- **Inspectable.** You can read, diff, and `git blame` the agent's entire memory. Nothing is opaque.
- **No infra.** No server, no embeddings, no API key, nothing to keep running or pay for.
- **Survives tool churn.** Files outlive whatever MCP server or framework you're using now.
- **`grep` is enough.** At the scale of one person's working memory, exact-match search over good filenames beats semantic search, and it never returns something that isn't there.
- **The agent maintains it natively.** Claude Code already reads and writes files. The memory is built from the one primitive the agent is best at.

The tradeoff is real: there's no semantic recall, so retrieval leans entirely on naming and the lookup index. [DOCTRINE.md](DOCTRINE.md) is what makes that tradeoff work.
