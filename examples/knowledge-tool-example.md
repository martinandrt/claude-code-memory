---
name: example-deploy-cli-gotcha
description: A worked example of a knowledge/tools file — capturing one non-obvious gotcha about an integration so the next session doesn't rediscover it the hard way.
type: knowledge
status: active
last_edited: 2026-01-15
---

> This is an illustrative example, not a real tool. It shows the *shape* of a `knowledge/tools/`
> file: the specific, hard-won behavior that a tool's own docs won't tell you, written so the
> next session avoids the trap on the first try.

# Example deploy CLI — env vars apply only after a redeploy

**Gotcha:** Setting an environment variable via the CLI does **not** affect the currently
running deployment. The value is stored, but it only takes effect on the **next** deploy.

**Why it bites:** You set the var, you re-run the app, it still uses the old value, and you
waste twenty minutes assuming the set command failed. It didn't — the timing is the trap.

**How to apply:**
- After changing any env var, trigger a fresh deploy before testing — don't test against the
  live one and conclude the change didn't take.
- To confirm a value is actually stored (separate from being live), list the vars explicitly
  rather than inferring from app behavior.
- **Anti-pattern:** "I set the var but it's not working, the CLI must be broken." Check the
  deploy timing first.

**Verified:** 2026-01-15 (re-verify if the CLI major version changes — flagged by the
staleness check after 90 days).
