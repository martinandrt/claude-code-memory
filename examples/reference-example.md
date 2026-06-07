---
name: example-team-directory
description: A worked example of a reference/ file — a stable lookup table (people, IDs, links) the agent consults to get a fact right, not a lesson or a procedure.
type: reference
status: active
last_edited: 2026-01-15
---

> This is an illustrative example, not a real directory. It shows the *shape* of a
> `reference/` file: stable facts the agent looks up — who's who, which ID is which, where a
> resource lives. No `why`, no anti-pattern; reference holds *facts*, not *rules*.

# Team directory

Who's who, so the agent addresses the right person and uses the right handle.

| Name | Role | Chat handle | Notes |
|------|------|-------------|-------|
| Alex Rivera | Eng lead | `@alex` | Owns deploys; ping before a production change |
| Sam Chen | Design | `@sam.chen` | Final say on UI copy |
| Jordan Lee | PM | `@jlee` | Routes anything customer-facing |

## Resource IDs

| Thing | ID / location |
|-------|---------------|
| Staging project | `proj_staging_4821` |
| Analytics dashboard | `dash-main` at analytics.example.com |
| Shared design file | figma.com/file/EXAMPLE123 |

---

**Why a reference file is its own type:** these are facts that are *looked up*, not reasoned
about — and they go stale in a specific way (a person changes role, an ID is retired). Keeping
them in one terse table means the agent gets the name or ID right without hunting, and the
staleness check can flag the whole file for a re-check on a slower cadence than a live project.
Update the row when a fact changes; this is the one place where being a plain lookup is the
entire point.
