# Claude Code Memory

A file-based memory architecture that gives [Claude Code](https://claude.com/claude-code) **persistent memory across sessions** and lets it **improve from its own mistakes** — without a database, a vector store, or an API key.

> This is the skeleton and the doctrine extracted from a personal Claude Code setup I've run daily across **200+ sessions**. It's shaped by what actually went wrong over that time. It ships the structure, the writing doctrine, and the scripts — **not** the private memory itself.

It is not a framework you install. It is a **shape you copy and adapt** — a handful of Markdown files, a frontmatter convention, and about 500 lines of dependency-free Python.

---

## The problem

Every Claude Code session starts from zero. The model is brilliant inside one session and amnesiac between them. The common answer — a growing `CLAUDE.md` — breaks down fast:

- **It doesn't scale.** Everything you want remembered loads into every session. Context fills with things irrelevant to today's task, and you pay for all of it on every request.
- **It doesn't learn.** When the agent makes the same mistake twice, nothing captured *why* the first fix was right. The correction evaporates when the session ends.
- **It has no continuity.** Session 50 has no idea what session 49 decided, what's half-finished, or what it must not touch.

This repo is a working answer to all three.

## The shape

Three layers, by how often they're needed:

```text
memory/
  BRAIN.md       operating manual + decision rules        ← boot layer:
  LINEAGE.md     continuity handoff from last session         loaded every
  MEMORY.md      auto-generated lookup index (don't edit)     session, terse
  feedback/      lessons from mistakes                     ← on-demand layer:
  knowledge/     how tools / skills / systems work             opened only
  projects/      live state of ongoing work                    when relevant
  reference/     stable lookups (people, IDs, links)

scripts/
  memory-index.py    regenerate the MEMORY.md lookup index from frontmatter
  memory-check.py    staleness + structural invariants (CI-able)
```

The split is what matters: the **boot layer stays small** (it's the cost you pay every session), and **detail lives on-demand** in files the agent only opens when the task calls for it. Token cost stays flat as the memory grows from 10 files to 200.

## How it learns

The engine isn't the files — it's a habit, encoded as a rule the agent reads at boot:

> Whenever the user corrects you, or confirms a non-obvious approach, **write it down immediately** as a memory file — trigger, the reason it's right, and the anti-pattern to avoid. Don't wait for the end of the session.

Each correction becomes a file the *next* session reads before it acts, so the same mistakes stop recurring. Over many sessions the agent ends up knowing your tools, your style, and the things to avoid.

See **[DOCTRINE.md](DOCTRINE.md)** for *how* to write these files so a future agent acts on them correctly, and **[PRINCIPLES.md](PRINCIPLES.md)** for the operating principles the agent runs on.

## The loop

The files are a skeleton; a loop the agent runs every session is what makes them live. **Boot reads the boot layer. The session works. End writes the handoff, captures the lessons, and regenerates the index.**

```text
   /boot  reads ──►  BRAIN · LINEAGE · MEMORY  ──►  the work  ──┐
   (terse status,    + recent activity                         │
    then waits)                                                │
        ▲                                                      ▼
        └──────  /session-end  writes  ◄────────────────────────┘
                 LINEAGE handoff · lessons · regenerated index
```

Boot is cheap and runs always; end is selective and writes only when the session earned it — an empty session writes nothing. Skip the loop and you have well-organized empty folders. See **[LIFECYCLE.md](LIFECYCLE.md)** for what each routine does and why, plus copy-ready `/boot` and `/session-end` templates.

## What's inside

| File | What it is |
|------|------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The layered memory model and why each part is shaped the way it is |
| [LIFECYCLE.md](LIFECYCLE.md) | The session loop — what `/boot` and `/session-end` do and why, with copy-ready templates |
| [DOCTRINE.md](DOCTRINE.md) | How to write memory *for an AI reader* — the writing checklist that makes recall reliable |
| [PRINCIPLES.md](PRINCIPLES.md) | The operating principles the agent runs on — all specific to this setup |
| [templates/](templates/) | Empty boot files, the frontmatter schema, and `/boot` + `/session-end` command templates, ready to copy |
| [examples/](examples/) | Two worked memory files — a feedback lesson and a tool gotcha |
| [scripts/](scripts/) | `memory-index.py`, `memory-check.py` — stdlib only, no dependencies |

## Quick start

```bash
# 0. Clone this repo — you'll copy two folders out of it.
git clone https://github.com/martinandrt/claude-code-memory
cd claude-code-memory

# 1. Copy the template memory tree + the scripts into YOUR project.
#    Point your-project at your real project dir (mkdir it first if it's new).
mkdir -p your-project
cp -r templates/memory   your-project/memory
cp -r scripts            your-project/scripts

# 2. Point Claude Code at the boot files — add to your project's CLAUDE.md:
#    "At the start of every session, read memory/BRAIN.md, then memory/LINEAGE.md."

# 3. From inside your project, regenerate the lookup index whenever you
#    add a file under memory/feedback/ or memory/knowledge/:
cd your-project
python3 scripts/memory-index.py

# 4. (optional) Run scripts/memory-index.py from a Claude Code Stop hook so the
#    index updates itself at the end of every session. See ARCHITECTURE.md → Automation.
```

You don't need all of it. The smallest useful version is `feedback/` + `scripts/memory-index.py` + the learning habit. Add continuity (LINEAGE) and checks (`scripts/memory-check.py`) when the memory grows enough to need them.

## What this is *not*

- **Not the actual brain.** The private memory — profile, clients, project specifics — is not here and never will be. This is the empty skeleton plus the method.
- **Not a magic prompt.** It's a discipline. It works because something writes files honestly and something reads them before acting. If you skip the habit, you have empty folders.
- **Not the only way.** Memory MCP servers and vector stores solve a different shape of this. This one is deliberately boring: plain files, `grep`, no infra, fully inspectable, and it survives tool churn.

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, take what's useful.

Built by [@martinandrt](https://github.com/martinandrt). If you build something better on top of it, I'd like to see it.
