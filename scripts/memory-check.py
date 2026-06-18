#!/usr/bin/env python3
"""
Memory staleness checker + structural invariants.

Zero dependencies (stdlib only).

Usage:
  python3 memory-check.py                 # staleness report (default)
  python3 memory-check.py --stale-only    # only files that are stale
  python3 memory-check.py --json          # machine-readable output
  python3 memory-check.py --invariants    # structural gates, exit 1 on failure
  python3 memory-check.py --memory-dir PATH

Run --invariants in CI to keep the memory structurally honest: every file has
the required frontmatter, its type is a known one, no file has duplicate keys,
the lookup index is current, the markdown links in the boot files (BRAIN/MEMORY)
resolve to real files, the session numbering in LINEAGE.md stays consistent, and
no script in scripts/ is left orphaned (referenced by no doc, command, or memory
file). The last two are anti-rot gates — they catch a kind of decay structure
alone doesn't: a mis-numbered handoff, or a script nobody points at anymore.
"""

import argparse
import json
import re
import sys
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "memory"

SKIP_FILES = {"MEMORY.md", "LINEAGE.md"}
SKIP_DIRS = {"archive"}
REQUIRED_FRONTMATTER_KEYS = {"name", "description", "type", "status", "last_edited"}
KNOWN_TYPES = {"rule", "identity", "user", "knowledge", "feedback", "project", "reference"}
FEEDBACK_SOFT_CAP = 25  # warning only — past this, consider consolidating
PLACEHOLDER_RE = re.compile(r"<[^>]+>")  # ignore <placeholder> tokens in cross-refs

# Days before a file of a given type is considered stale (None = never stale).
# A lesson learned from a mistake doesn't expire; a project's live state does.
STALENESS_DAYS = {
    "project": 30,
    "knowledge": 90,
    "identity": 180,
    "rule": 180,
    "user": 180,
    "reference": 180,
    "feedback": None,
}


def parse_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    m = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def _memory_files(memory_dir: Path):
    """Yield (path, rel) for every memory file, skipping index/archive files."""
    for path in sorted(memory_dir.rglob("*.md")):
        rel = path.relative_to(memory_dir)
        if path.name in SKIP_FILES or any(p in SKIP_DIRS for p in rel.parts):
            continue
        yield path, rel


# ---------------------------------------------------------------- staleness ---

def check_file(path: Path, today: date, memory_dir: Path) -> dict:
    rel = path.relative_to(memory_dir)
    fm = parse_frontmatter(path)

    file_type = fm.get("type", "unknown")
    # Either last_verified (re-checked) or last_edited counts as "fresh".
    last_ok = fm.get("last_verified", "") or fm.get("last_edited", "")
    threshold = STALENESS_DAYS.get(file_type)

    result = {
        "path": str(rel), "name": fm.get("name", rel.stem), "type": file_type,
        "last_ok": last_ok, "stale": False, "days": None, "reason": None,
    }

    if threshold is None:
        result["reason"] = "never stale"
        return result
    if not last_ok:
        result["stale"] = True
        result["reason"] = "missing last_verified/last_edited"
        return result
    try:
        when = datetime.strptime(last_ok, "%Y-%m-%d").date()
    except ValueError:
        result["stale"] = True
        result["reason"] = f"bad date format: {last_ok}"
        return result

    days = (today - when).days
    result["days"] = days
    if days > threshold:
        result["stale"] = True
        result["reason"] = f"{days}d > {threshold}d limit"
    else:
        result["reason"] = f"{days}d (limit {threshold})"
    return result


def check_all(memory_dir: Path) -> list:
    today = date.today()
    results = []
    for path in sorted(memory_dir.rglob("*.md")):
        if path.name in SKIP_FILES or any(p in SKIP_DIRS for p in path.relative_to(memory_dir).parts):
            continue
        results.append(check_file(path, today, memory_dir))
    return results


def print_table(results: list, stale_only: bool):
    filtered = [r for r in results if r["stale"]] if stale_only else results
    if not filtered:
        if stale_only:
            print("OK: no stale files.")
        return
    stale_count = sum(1 for r in results if r["stale"])
    for r in filtered:
        tag = "STALE" if r["stale"] else "  OK "
        days_str = f"{r['days']}d" if r["days"] is not None else "—"
        print(f"  {tag}  {r['path']:<45} {r['type']:<12} {days_str:<8} {r['reason']}")
    print(f"\n  {stale_count}/{len(results)} files need a review.")


# --------------------------------------------------------------- invariants ---

def _frontmatter_raw(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    m = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    return m.group(1) if m else None


def invariant_required_keys(memory_dir: Path) -> list[str]:
    """Every memory file has the required frontmatter keys."""
    failures = []
    for path, rel in _memory_files(memory_dir):
        raw = _frontmatter_raw(path)
        if raw is None:
            failures.append(f"{rel}: missing frontmatter")
            continue
        present = {l.partition(":")[0].strip() for l in raw.splitlines() if ":" in l}
        missing = REQUIRED_FRONTMATTER_KEYS - present
        if missing:
            failures.append(f"{rel}: missing keys {sorted(missing)}")
    return failures


def invariant_known_type(memory_dir: Path) -> list[str]:
    """Every memory file's `type` is one of the known section types.

    A typo'd type (e.g. `feeback`) would otherwise let a file pass every gate
    while being silently dropped from the generated index.
    """
    failures = []
    for path, rel in _memory_files(memory_dir):
        t = parse_frontmatter(path).get("type")
        if t is not None and t not in KNOWN_TYPES:
            failures.append(f"{rel}: unknown type '{t}' (expected one of {sorted(KNOWN_TYPES)})")
    return failures


def invariant_no_duplicate_keys(memory_dir: Path) -> list[str]:
    """No frontmatter key appears twice in the same file (a silent parse hazard)."""
    failures = []
    for path, rel in _memory_files(memory_dir):
        raw = _frontmatter_raw(path)
        if raw is None:
            continue
        seen = {}
        for line in raw.splitlines():
            if ":" not in line:
                continue
            key = line.partition(":")[0].strip()
            if not key or key.startswith("-"):
                continue
            seen[key] = seen.get(key, 0) + 1
        dups = [k for k, c in seen.items() if c > 1]
        if dups:
            failures.append(f"{rel}: duplicate keys {dups}")
    return failures


def invariant_cross_refs(memory_dir: Path) -> list[str]:
    """Markdown links in the boot files (BRAIN/MEMORY) resolve to real files."""
    failures = []
    mdlink_re = re.compile(r"\[[^\]]+\]\(([^)\s]+?\.(?:md|py|sh))\)")
    for doc in [memory_dir / "BRAIN.md", memory_dir / "MEMORY.md"]:
        if not doc.exists():
            continue
        for match in mdlink_re.finditer(doc.read_text()):
            rel = match.group(1)
            if rel.startswith(("http://", "https://", "mailto:", "#")) or PLACEHOLDER_RE.search(rel):
                continue
            if not (doc.parent / rel).resolve().exists():
                failures.append(f"{doc.name}: broken link `{rel}`")
    return failures


def invariant_index_current(memory_dir: Path) -> list[str]:
    """The auto-generated MEMORY.md index reflects what's on disk."""
    import importlib.util
    index_path = Path(__file__).parent / "memory-index.py"
    spec = importlib.util.spec_from_file_location("memory_index", index_path)
    if spec is None or spec.loader is None:
        return [f"cannot load {index_path.name}"]
    memory_index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(memory_index)

    memory_md = memory_dir / "MEMORY.md"
    if not memory_md.exists():
        return ["MEMORY.md does not exist"]
    content = memory_md.read_text()
    if "<!-- AUTO:START -->" not in content or "<!-- AUTO:END -->" not in content:
        return ["MEMORY.md is missing the <!-- AUTO:START/END --> markers"]
    generated = memory_index.generate_sections(memory_index.scan_memory(memory_dir)).strip()
    current = content.split("<!-- AUTO:START -->")[1].split("<!-- AUTO:END -->")[0].strip()
    if current != generated:
        return ["MEMORY.md index is out of date — run: python3 scripts/memory-index.py"]
    return []


def invariant_feedback_cap(memory_dir: Path) -> list[str]:
    """Soft cap on feedback files (warning) — past this, consolidate."""
    feedback_dir = memory_dir / "feedback"
    if not feedback_dir.is_dir():
        return []
    count = sum(1 for _ in feedback_dir.glob("*.md"))
    if count > FEEDBACK_SOFT_CAP:
        return [f"feedback/: {count} files > {FEEDBACK_SOFT_CAP} (warning) — consider consolidating"]
    return []


def invariant_lineage_sessions(memory_dir: Path) -> list[str]:
    """Session numbers in LINEAGE.md are unique and never increase going down the file.

    The handoff log is append-newest-on-top, so reading top→bottom the numbers should
    descend. A duplicate, or a number that's higher than the one above it, means a
    session was mis-numbered or retro-inserted — a quiet way for continuity to drift.
    No-op until LINEAGE.md actually has numbered `## SESSION N` headers (the template
    placeholder doesn't count).
    """
    lineage = memory_dir / "LINEAGE.md"
    if not lineage.exists():
        return []
    nums = [int(m) for m in re.findall(r"^## SESSION (\d+)", lineage.read_text(), re.MULTILINE)]
    if len(nums) < 2:
        return []
    failures = []
    seen = set()
    for n in nums:
        if n in seen:
            failures.append(f"LINEAGE.md: session number {n} appears more than once")
        seen.add(n)
    for i in range(1, len(nums)):
        if nums[i] > nums[i - 1]:
            failures.append(
                f"LINEAGE.md: session {nums[i]} sits below {nums[i - 1]} — out of order "
                f"(newest goes on top)"
            )
            break
    return failures


def invariant_no_orphan_scripts(memory_dir: Path) -> list[str]:
    """Every top-level script in scripts/ is referred to by name from some doc.

    A script that nothing — no README, no command, no memory file — names is either
    dead or undocumented, and both rot. Sub-directories are skipped on purpose, so an
    optional add-on like scripts/recall/ isn't policed by this gate.
    """
    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent
    blobs = []
    for md in repo_root.glob("*.md"):  # README, ARCHITECTURE, … at repo root
        blobs.append(md.read_text(encoding="utf-8", errors="ignore"))
    if memory_dir.is_dir():
        for md in memory_dir.rglob("*.md"):
            blobs.append(md.read_text(encoding="utf-8", errors="ignore"))
    blob = "\n".join(blobs)
    failures = []
    for script in sorted(list(scripts_dir.glob("*.py")) + list(scripts_dir.glob("*.sh"))):
        if script.name not in blob:
            failures.append(
                f"scripts/{script.name}: orphan — no doc, command, or memory file names it"
            )
    return failures


INVARIANTS = [
    ("Required frontmatter keys", invariant_required_keys, "error"),
    ("Known frontmatter type", invariant_known_type, "error"),
    ("No duplicate frontmatter keys", invariant_no_duplicate_keys, "error"),
    ("Cross-refs resolve (BRAIN/MEMORY)", invariant_cross_refs, "error"),
    ("Lookup index is current", invariant_index_current, "error"),
    ("LINEAGE session numbering", invariant_lineage_sessions, "error"),
    ("No orphan scripts", invariant_no_orphan_scripts, "error"),
    ("Feedback count cap", invariant_feedback_cap, "warning"),
]


def run_invariants(memory_dir: Path) -> int:
    had_error = False
    warnings = 0
    for label, fn, severity in INVARIANTS:
        failures = fn(memory_dir)
        if not failures:
            print(f"  ok   {label}")
            continue
        print(f"  {'FAIL' if severity == 'error' else 'warn'} {label}")
        for f in failures:
            print(f"        {f}")
        if severity == "error":
            had_error = True
        else:
            warnings += len(failures)
    print()
    if had_error:
        print("FAIL: at least one invariant violated.")
        return 1
    print(f"PASS{f' (with {warnings} warnings)' if warnings else ''}.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Memory staleness checker + invariants")
    parser.add_argument("--stale-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--invariants", action="store_true")
    parser.add_argument("--memory-dir", type=Path, default=MEMORY_DIR)
    args = parser.parse_args()

    if args.invariants:
        sys.exit(run_invariants(args.memory_dir))

    results = check_all(args.memory_dir)
    if args.json:
        filtered = [r for r in results if r["stale"]] if args.stale_only else results
        json.dump(filtered, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_table(results, args.stale_only)


if __name__ == "__main__":
    main()
