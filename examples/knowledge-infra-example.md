---
name: example-nightly-backup-job
description: A worked example of a knowledge/infra file — how one piece of the running system actually works (a background job, an environment quirk), so a session understands the moving parts before it touches them.
type: knowledge
status: active
last_edited: 2026-01-15
---

> This is an illustrative example, not real infra. It shows the *shape* of a
> `knowledge/infra/` file: the system itself — background jobs, environment quirks, how the
> pieces wire together — so the agent isn't surprised by something that runs without anyone
> invoking it.

# Nightly backup job

**What it is:** a cron job on the app server that dumps the database to object storage every
night at 03:00 UTC and keeps the last 14 days.

**Where it's defined:** `ops/cron/backup.sh`, scheduled in `ops/crontab`. Logs to
`/var/log/backup.log`.

## What a session needs to know
- The job runs **unattended** — nothing in a session triggers it. If a backup is "missing",
  check the cron log, don't assume a session was supposed to make it.
- Restores are **manual** and not tested automatically. A backup existing is not proof it
  restores; that has to be checked by hand.
- The 14-day window means anything needed longer must be copied out before it rotates off.

## Anti-pattern
- Assuming data is safe because "there's a backup job." Confirm the *last successful run* in
  the log before relying on it — a silently failing cron is the classic trap.

**Why capture infra like this:** background machinery is invisible until it breaks, and a
session that doesn't know it exists will either duplicate it or misdiagnose a failure. This
file is the map of the moving parts that keep running whether or not anyone's in a session.
