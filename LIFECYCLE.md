# The session loop: read on boot, write on end

The files in [ARCHITECTURE.md](ARCHITECTURE.md) are a skeleton. What makes them a *living* system is a loop the agent runs every session:

> **Boot reads the boot layer. The session works. End writes the handoff, captures the lessons, and regenerates the index.**

Skip the loop and you have well-organized empty folders. The boot layer is only worth its token cost if something keeps filling it; the continuity handoff only exists because something writes it at the end. The loop is the metabolism — how the memory ingests a session and consolidates it into the next one.

Two routines close it. Most setups wire them to a command each — here we call them **`/boot`** and **`/session-end`** — but the names don't matter; the two halves do.

```text
        ┌──────────────────────────────────────────────┐
        │                                              │
   /boot  reads ──►  BRAIN · LINEAGE · MEMORY      the work
   (every session,   + recent activity                 │
    terse status)         ▲                            │
        ▲                 │                            ▼
        │                 └──── /session-end  writes ──┘
        │                       LINEAGE handoff
        └───────────────────────+ lessons (feedback/knowledge/projects)
                                 + regenerate MEMORY index
```

The asymmetry is the point: **boot is cheap and happens always; end is selective and happens only when the session earned a write.**

---

## `/boot` — read, internalize, don't recite

The first thing a new session does. Its only job is to load the boot layer into the agent's head and get oriented, fast.

**What it does**

1. **Reads the boot layer in parallel** — `BRAIN.md` (operating manual + decision rules), `LINEAGE.md` (the last session's handoff), `MEMORY.md` (the lookup index), and the tail of an activity log if you keep one.
2. **Internalizes** — understands the last session: what it was, what's half-finished, what must not be touched. Maps the open items.
3. **Outputs a short status** — a few lines: which session this is, what it continues, anything notable since last time, and "what are we doing?" Then it stops and waits.

**Why each part**

- **Read in frequency order, not all at once.** The boot layer is small *by design* (see the two-tier split in ARCHITECTURE). Boot loads exactly that layer and nothing from the on-demand folders — those get opened later, only when a task calls for them. Loading everything at boot would defeat the whole architecture.
- **Internalize, don't recite.** *This is the most-skipped part.* The anti-pattern is the agent dumping the contents of the files back at you — you wrote them, you can see them in your editor, and the recitation burns tokens and your attention for zero value. The metric for boot is not "did it summarize the files" but "is it oriented enough to act correctly on the next request." A five-line status that proves orientation beats a page that parrots the map.
- **End by asking, not by doing.** Boot orients; it doesn't start work. It hands control back so you set the direction.

## `/session-end` — decide, write, consolidate

The last thing a session does. It turns the session that just happened into something the *next* session can read before it acts.

**What it does**

1. **Gates on substance.** First question: did anything worth remembering happen? A session that was just a greeting or a dead-end question gets **no write at all** — say so and stop. Most of the discipline lives in this gate.
2. **Writes the LINEAGE handoff** — if the session earned it: what was done, key decisions, what's left open, what the next session must not break. Newest entry on top; older ones roll over into the archive (see ARCHITECTURE → *Continuity & rollover*).
3. **Captures the lessons** — a correction goes to `feedback/`, a new tool gotcha or playbook to `knowledge/`, a changed project state to `projects/`. Update an existing file if one already covers the topic; only make a new file when none does.
4. **Regenerates the index and checks structure** — run `memory-index.py` so `MEMORY.md` reflects any new file, then `memory-check.py --invariants` as a gate before committing. If the check fails, fix it before the commit, don't commit around it.
5. **Commits.** Plain Git. The memory's whole history becomes inspectable and `git blame`-able.

**Why each part**

- **The gate is the point.** Without it, every session feels obligated to "produce something," and the memory fills with restatements of nothing. An empty session honestly producing nothing is the system working, not failing — it's the same honesty principle as [PRINCIPLES.md](PRINCIPLES.md) §1: don't pad. The handoff has to stay worth reading, which means most of its value comes from what you *refuse* to write.
- **Write the handoff for the next agent, not for yourself.** The reader is the next session — it reads to *act*, not to admire. So the handoff is concrete: open technical items with file paths, deploy/test state, IDs and URLs to hand over. It is **not** a place for advice to your future self ("consider doing X", "it would be good to Y") — that's agenda, not state, and the next session can't act on it. (We enforce this with a commit-time lint; see the appendix.)
- **Capture lessons here as a backstop, not as the only time.** The primary learning habit is "write the file the *moment* the correction happens" (README → *How it learns*). Session-end is the safety net that catches anything that slipped through, plus the bookkeeping — index regen and structural checks — that you don't want to depend on a human remembering.
- **Regenerate, never hand-edit the index.** `MEMORY.md` is derived from every file's frontmatter. The moment it's edited by hand it can drift out of sync with reality; keeping it generated means it's never wrong.

---

## Make it a property of the system, not a thing you remember

The loop should not depend on you typing two commands. Wire as much of it as you can to run on its own:

- A **`Stop` hook** that appends one line to an activity log every time a session ends (timestamp + topic) gives `/boot` its "what happened since last time" for free.
- Running **`memory-index.py` from that same hook** keeps the index current without anyone invoking `/session-end` at all.
- Running **`memory-check.py --invariants` in CI** turns the structural gates into something a bad commit can't slip past.

Continuity becomes a property of the system, not a discipline you have to sustain by hand. The two routines are still where judgment lives — *what's worth a handoff, which lesson to capture* — but the bookkeeping around them runs itself.

---

## Appendix: what daily use added

You do **not** need any of this on day one. These are the calluses a real setup grows after hundreds of sessions, recorded here so you know what the routines turn into under load — not as a starting point.

- **Concurrency-safe session numbering.** If you ever run more than one session against the same memory at once (multiple agents, multiple terminals), they all boot with the same "last session number" and will collide on it at end — silently merging or overwriting each other's handoff. The fix: don't assign the session's number at boot; assign it at *end*, after syncing, from the live state. Until you run sessions in parallel, you'll never hit this.
- **A handoff lint.** The "write state, not agenda" rule erodes the moment it's only in your head. A small commit-time check that rejects hedge-words ("consider", "recommend", "for next session") in the handoff section keeps it honest mechanically. The agent can't override its own gate; only a human at the terminal can.
- **Rollover thresholds and staging.** As LINEAGE grows and sessions overlap, you'll want the rollover threshold tuned and a scratch area for in-progress writes so parallel sessions don't stage into each other. All of it is downstream of the same two-tier principle — keep the always-loaded part small — applied to the lifecycle instead of the file tree.

Every one of these is a generalization of a specific thing that went wrong. That's the pattern the whole repo is built on: the rule exists because the absence of it cost something once.
