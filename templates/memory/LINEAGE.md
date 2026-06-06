# Lineage log — session continuity

> The first thing each new session reads after BRAIN. You are part of a continuity, not an isolated instance. The most recent entry below is your handoff — your entry point.

## How to use

1. Read the most recent session entry below — it's the handoff from the last session.
2. At the end of your session, append your own entry (newest at the top of the list).
3. Keep the handoff to what the **next** session must know — not a full dump.
4. When the file holds more than a few sessions, roll the older ones into `archive/`
   verbatim (one file per session) so this file stays short but nothing is lost.

Durable lessons belong in `feedback/` or `knowledge/` files, not only here.

---

## SESSION N — <short name>

**Date:** YYYY-MM-DD
**Summary:** <one or two sentences: what this session was about>

### What happened
1. <key thing done>
2. <key thing done>

### Key decisions
- <decision + the reason, so the next session doesn't relitigate it>

### Learned
- <anything surprising worth carrying forward; also write it to a feedback/knowledge file>

### Handoff (what the next session must know)
- <open item / half-finished work / what NOT to touch / where things were left>
