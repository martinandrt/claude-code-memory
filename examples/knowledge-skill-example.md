---
name: example-release-checklist
description: A worked example of a knowledge/skills file — a reusable playbook for a recurring multi-step task, so the agent runs the whole sequence the same way every time instead of improvising.
type: knowledge
status: active
last_edited: 2026-01-15
---

> This is an illustrative example, not a real skill. It shows the *shape* of a
> `knowledge/skills/` file: a repeatable procedure with a clear trigger, written as steps
> the next session can follow start-to-finish. A `tools/` file says how one integration
> *behaves*; a `skills/` file says how to *do a whole task* that spans several.

# Cutting a release

**Trigger:** the user says "cut a release", "ship it", "tag a new version", or asks to
publish the next version.

## Steps
1. **Confirm the branch is clean and green** — `git status` clean, CI passing on the
   latest commit. Don't release on top of a red build.
2. **Pick the version** — patch for fixes, minor for features, major for breaking changes.
   If unsure which, ask — don't guess a major.
3. **Update the changelog** — move everything under "Unreleased" into a dated section for
   the new version.
4. **Tag and push** — `git tag vX.Y.Z && git push --tags`. The tag is what the publish
   pipeline triggers on.
5. **Verify the publish landed** — check the package registry / release page actually shows
   the new version before telling the user it's out. (This is the [[verify-before-claiming-done]]
   rule applied to releases.)

## Anti-patterns
- Tagging before CI is green "to save time" — a broken release is far more expensive to
  unwind than waiting for the build.
- Reporting "released!" off the tag push alone. The tag triggering the pipeline is not the
  same as the pipeline succeeding — confirm the artifact is live.

**Why capture this as a skill:** a release is a sequence where skipping or reordering one
step (changelog after tag, publish unverified) causes real damage, and it happens rarely
enough that no one remembers the exact order. Writing it once means every release runs the
same safe way, regardless of which session does it.
