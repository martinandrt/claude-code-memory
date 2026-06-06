# Frontmatter schema

Every on-demand memory file starts with a YAML frontmatter block. The index generator and
the checker both parse it, so the keys matter. The parser is intentionally dumb — flat
`key: value` lines only, no nested YAML — which keeps the scripts dependency-free.

```yaml
---
name: short-kebab-case-slug
description: One line. This is what shows up in the MEMORY.md index — the sentence the agent skims to decide whether to open the file. Make it greppable and specific.
type: feedback        # one of: rule | identity | user | knowledge | feedback | project | reference
status: active        # active | archived
last_edited: 2026-01-15
# last_verified: 2026-01-15   # optional; if present, used for staleness instead of last_edited
---
```

## The `type` values

| `type` | What it holds | Goes stale after |
|--------|---------------|------------------|
| `rule` | Hard operating rules | 180 days |
| `identity` | Who the agent / user is in this setup | 180 days |
| `user` | Profile, preferences, values | 180 days |
| `knowledge` | How a tool / skill / system works (under `knowledge/`) | 90 days |
| `feedback` | A lesson learned from a real mistake | never |
| `project` | Live state of ongoing work | 30 days |
| `reference` | Stable lookups (people, IDs, links) | 180 days |

Staleness thresholds live in `scripts/memory-check.py` — tune them to your cadence.
`feedback` never goes stale on purpose: a lesson about *why* something was wrong doesn't
expire just because time passed.

## The body

After the frontmatter, write for the AI reader (see [DOCTRINE.md](../DOCTRINE.md)). For a
`feedback` or `rule` file, the most reliable shape is:

```text
**Rule:** <trigger → what to do>

**Why:** <the reason it's right — this is what lets the agent generalize to a new phrasing>

**How to apply:**
- <concrete step>
- <the anti-pattern: what NOT to do, stated explicitly>
```

Link related files inline with `[[other-file-slug]]` so the memory forms a graph, not a
pile. A link to a slug that doesn't exist yet is fine — it marks something worth writing
later.

See [examples/](../examples/) for two worked files that follow this schema.
