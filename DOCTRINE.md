# Doctrine: write memory for the AI reader

The single idea that makes this whole system work:

> **The memory files are not documentation. They are the agent's execution manual.**
> The human almost never re-reads them. The only reader that matters is the *next agent session* — and it doesn't read to understand, it reads to **act**.

So you don't write "clear prose for a person." You write so that when the user says *"send that to the client"* or *"track this"* or *"build the demo,"* the agent does the right thing **on the first try, without being corrected.**

That is the only metric. Not "is this well-written." The metric is: **did the agent hit the user's intent without a correction.**

## The writing checklist

Every memory file should pass all six. They're cheap to apply and they're the difference between a note that gets followed and one that gets misread.

### 1. Trigger → action, at the top
Start with *what to do*, not the history of how the lesson came to be. Ideally lead with the user's real phrasing mapped to the exact procedure. People speak naturally, not in commands — capture the loose phrasing (*"can you sort out the invoice"*), not just a canonical verb.

### 2. A `why` on every rule
This is the one most people skip. The human won't be there to re-explain when the agent faces a slightly different situation. If the file says *what* but not *why*, the agent either fails on the new phrasing or applies the rule too narrowly or too broadly. The `why` is what lets the agent generalize correctly from the rule to the case in front of it.

### 3. State the anti-pattern explicitly
Write down what **not** to do. Models have a strong bias toward compliance and toward "doing something extra to be helpful." Without an explicit prohibition in the text, the agent will drift into the failure mode. The guardrail has to live in the file, not in your head.

### 4. Freshness
The agent can't tell that a playbook points at a file, ID, or flag that no longer exists — it'll confidently use the dead reference. Defend against it two ways: a `last_verified` date in the frontmatter, and a hard rule that the agent **verifies a reference still exists before acting on it.** A staleness check (`memory-check.py`) turns the date into an actual warning.

### 5. A greppable slug
The file is found by exact-match search, so its name and keywords must use *the user's vocabulary*, not the term that's technically tidy. Name it so you'd find it by `grep`-ing the words you'd actually say, not the words an architect would file it under.

### 6. Conclusion up, detail down
The agent reads top-down and often stops early. Put the executable core in the first lines; push the backstory to the bottom. If the first three lines don't tell the agent what to do, restructure.

## Two layers, two voices

Explicitness costs tokens, and the boot layer pays that cost every session. So the doctrine splits by layer:

- **Boot layer** (`BRAIN.md`, `LINEAGE.md`, `MEMORY.md`) → terse. Pointers only. The verbose reasoning does **not** belong in a file that loads every session.
- **On-demand layer** (everything else) → explicit, verbose, full `why`. This file is only read when it's needed, so it can afford to be complete.

Put the long-form reasoning in the file you open occasionally, never in the file that loads every time.

## Where reliability actually comes from

The center of gravity is **not** the rules — it's the **trigger→action mappings**: the table of "when the user says X, do Y." A pile of well-written principles is worth less than a precise map from the things the user actually says to the exact procedure. When you have to choose where to invest, **grow the intent mappings before you write another rule.** Rules tell the agent how to think; the mappings tell it what to *do* when this specific person says this specific thing.

## The habit that makes it compound

The doctrine is worth nothing without one behavior, which belongs in the boot layer as a standing rule:

> Whenever the user corrects you (*"no, not like that"*) **or** confirms a non-obvious call (*"yes, exactly"*), write it down **immediately** — as a new mapping, playbook, or feedback file. Don't wait for the end of the session. Don't wait to be asked.

The goal of each write is concrete: **that correction never has to happen again.** Every correction captured this way is one fewer in every session that follows. That's the loop: the longer you work with it, the fewer surprises.

## Anti-patterns

- **Writing for a human.** If it reads like nice documentation but doesn't open with an action, it'll be skimmed and skipped.
- **What without why.** Survives the exact situation it was born in; fails the next variation.
- **Verbose boot files.** Inflates the cost you pay every single session. Move it on-demand.
- **Tidy names over spoken names.** A perfectly-organized file nobody greps is invisible.
- **Saving the trivial.** A typo correction isn't a lesson. Capture the *generalizable* reason, or don't capture it.
- **Waiting for a "save memory" moment.** The correction is freshest the instant it happens. Write it then.
