# /session-end — close the session

Turn what just happened into something the next session can act on. Write only what has value — an empty session writes nothing.

## 1. Gate on substance

Did anything worth remembering happen?

| Question | If yes | If no |
|----------|--------|-------|
| Was something substantive worked on? | → write LINEAGE | → skip it |
| Did you learn a new procedure / gotcha? | → write `knowledge/` | → skip |
| Did the user correct or confirm an approach? | → write `feedback/` | → skip |
| Did a project's state change? | → update `projects/` | → skip |

**If none of these — say "nothing to write" and stop. No commit.** A greeting or a dead-end question earns no entry. This gate is most of the discipline.

## 2. Write the LINEAGE handoff (only if it earned one)

Append a new entry, newest on top: **what was done · key decisions · what's left open · what the next session must not break.**

Keep it to *state the next agent can act on*:
- open technical items (file path + what's left)
- deploy / test status, known bugs
- data to hand over (URLs, mock credentials, IDs)

**Not** advice to your future self ("consider…", "recommend…", "for next session…") — that's agenda, not state, and the next session can't act on it. (`scripts/handover-lint.py`, wired as a pre-commit hook, rejects exactly these hedge-words in the `### Handoff` block.)

## 3. Capture the lessons

- new procedure / tool gotcha → `knowledge/`
- a correction from the user → `feedback/` (rule + **why** + how to apply)
- changed project state → `projects/`

Update an existing file if one covers the topic. A new file means new frontmatter + (after step 4) a line in the index.

## 4. Regenerate the index, then check structure

```bash
python3 scripts/memory-index.py            # MEMORY.md picks up any new file
python3 scripts/memory-check.py --invariants   # gate: required frontmatter, valid types, no broken refs
```

If the check fails, **fix it — don't commit around it.**

**Optional, if you've adopted the extras:** keep the semantic index fresh with `python3 scripts/recall/embed.py --incremental` (cheap — only re-embeds changed files), and run `python3 scripts/drift-check.py` *periodically* (not every session — it's one model call) to catch files that have started to contradict each other.

## 5. Commit

Plain Git. Stage what this session touched, commit with a one-line summary of the session, push.

## Summary (a few lines)

- session name/number (or "no write")
- what was captured (or "nothing new")
- the handoff for the next session
