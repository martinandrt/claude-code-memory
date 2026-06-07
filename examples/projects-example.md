---
name: example-checkout-rebuild
description: A worked example of a projects/ file — the live state of one ongoing piece of work, written so any future session can resume it without re-discovering context.
type: project
status: active
last_edited: 2026-01-15
---

> This is an illustrative example, not a real project. It shows the *shape* of a `projects/`
> file: the current state of ongoing work, kept current, so the session that picks it up
> next week knows where things stand without re-reading the whole history.

# Checkout rebuild — migrating the payment flow to the new provider

**Status:** in progress — new provider wired in test mode, not yet switched in production.

**Where it lives:** `apps/web/src/checkout/` · staging at `checkout-staging.example.com`.

## What's done
- New provider SDK integrated behind a feature flag (`USE_NEW_CHECKOUT`, default off).
- Happy-path purchase works end-to-end in test mode.

## Open items
- Refund flow not implemented yet — old provider still handles refunds.
- Webhook signature verification is stubbed; must be real before production (`webhooks/verify.ts`).
- No load test run against the new provider yet.

## Key decisions
- Keep both providers live behind the flag until a full billing cycle passes clean — no
  hard cutover. **Why:** a payment flow is the worst place to discover an edge case in
  production with no fallback.

## Do not break
- The flag defaults **off**. Real customers are still on the old provider — don't flip the
  default to ship "progress."

---

**Why a file like this exists:** the live state of work is the thing a stateless agent loses
hardest between sessions. Without it, every session re-reads the diff and guesses what's
intentional. The handoff in `LINEAGE.md` is the *event* ("worked on checkout today"); this
file is the *state* ("here is exactly where checkout stands now"). Update it as the work
moves; when the project ships, archive or delete it.
