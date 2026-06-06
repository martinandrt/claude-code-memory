#!/usr/bin/env python3
"""
Memory index auto-generator.

Reads the frontmatter of every memory file and regenerates the index sections
in MEMORY.md, between the <!-- AUTO:START --> and <!-- AUTO:END --> markers.

Zero dependencies (stdlib only).

Usage:
  python3 memory-index.py                       # rewrite MEMORY.md in place
  python3 memory-index.py --dry-run             # print to stdout, change nothing
  python3 memory-index.py --check               # show diff vs current state
  python3 memory-index.py --memory-dir PATH     # point at your memory/ dir

The index is generated, never hand-edited. Each file contributes one line:
its name, path, and the `description` field from its frontmatter. That line is
what the agent skims to decide whether to open the file.
"""

import argparse
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "memory"

# Boot-layer files are loaded every session directly; they don't belong in the
# on-demand index. Add your own private/never-index files here.
SKIP_FILES = {"MEMORY.md", "LINEAGE.md", "BRAIN.md"}

# Output section order + headings. `type:` in frontmatter maps a file to a section;
# files under knowledge/ are sub-split by their subfolder (tools/skills/infra).
SECTION_ORDER = [
    ("rule", "### Rules"),
    ("identity", "### Identity"),
    ("user", "### User — profile, preferences"),
    ("knowledge-tools", "### Knowledge — tools (integrations)"),
    ("knowledge-skills", "### Knowledge — skills (how-to playbooks)"),
    ("knowledge-infra", "### Knowledge — infra (system, environment)"),
    ("feedback", "### Feedback"),
    ("project", "### Projects"),
    ("reference", "### Reference"),
]


def parse_frontmatter(path: Path) -> dict:
    """Read the YAML frontmatter between the --- markers (flat key: value only)."""
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


def classify_file(rel_path: Path, file_type: str) -> str:
    """Map a file to an output section by its type and path."""
    parts = rel_path.parts

    if file_type == "knowledge" or (len(parts) > 1 and parts[0] == "knowledge"):
        if len(parts) > 1 and parts[1] == "tools":
            return "knowledge-tools"
        elif len(parts) > 1 and parts[1] == "skills":
            return "knowledge-skills"
        elif len(parts) > 1 and parts[1] == "infra":
            return "knowledge-infra"
        # Loose knowledge/ files (no tools|skills|infra subfolder) default to the
        # infra/catch-all bucket. Convention (ARCHITECTURE.md) is to use a subfolder.
        return "knowledge-infra"

    return file_type


def scan_memory(memory_dir: Path) -> dict:
    """Walk the memory tree, return {section: [{path, name, description}]}."""
    sections = {key: [] for key, _ in SECTION_ORDER}

    for path in sorted(memory_dir.rglob("*.md")):
        if path.name in SKIP_FILES:
            continue
        rel = path.relative_to(memory_dir)
        if rel.parts[0] == "archive":
            continue

        fm = parse_frontmatter(path)
        if not fm:
            continue

        file_type = fm.get("type", "unknown")
        name = fm.get("name", rel.stem)
        description = fm.get("description", "")

        section = classify_file(rel, file_type)
        if section not in sections:
            # Unknown `type:` → the file would be silently dropped from the index.
            # Warn so the omission is visible (memory-check.py --invariants fails on it).
            print(f"WARN: skipping {rel}: unrecognized type '{file_type}'", file=sys.stderr)
            continue

        sections[section].append({
            "path": str(rel),
            "name": rel.name.replace(".md", ""),
            "description": description,
            "full_name": name,
        })

    return sections


def generate_sections(sections: dict) -> str:
    """Render the markdown for the auto-generated index sections."""
    lines = []

    for key, heading in SECTION_ORDER:
        files = sections.get(key, [])
        if not files:
            continue

        lines.append(heading)
        lines.append("")
        for f in sorted(files, key=lambda x: x["name"]):
            lines.append(f"- [{f['name']}.md]({f['path']}) — {f['description']}")
        lines.append("")

    return "\n".join(lines)


def update_memory_md(memory_dir: Path, dry_run: bool, check: bool):
    """Read MEMORY.md and replace the content between the AUTO markers."""
    memory_md = memory_dir / "MEMORY.md"
    if not memory_md.exists():
        print(
            f"ERROR: no MEMORY.md found at {memory_md} — run this from your "
            f"project root, or pass --memory-dir PATH.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = memory_md.read_text(encoding="utf-8")

    start_marker = "<!-- AUTO:START -->"
    end_marker = "<!-- AUTO:END -->"

    if start_marker not in content or end_marker not in content:
        print("ERROR: AUTO:START / AUTO:END markers not found in MEMORY.md", file=sys.stderr)
        sys.exit(1)

    sections = scan_memory(memory_dir)
    generated = generate_sections(sections)

    before = content.split(start_marker)[0]
    after = content.split(end_marker)[1]
    new_content = f"{before}{start_marker}\n\n{generated}\n{end_marker}{after}"

    if check:
        if content == new_content:
            print("OK: MEMORY.md is up to date.")
        else:
            old_auto = content.split(start_marker)[1].split(end_marker)[0].strip()
            old_lines = set(old_auto.splitlines())
            new_lines = set(generated.strip().splitlines())
            for line in sorted(new_lines - old_lines):
                if line.strip() and not line.startswith("###"):
                    print(f"  + {line.strip()}")
            for line in sorted(old_lines - new_lines):
                if line.strip() and not line.startswith("###"):
                    print(f"  - {line.strip()}")
        return

    if dry_run:
        print(generated)
        return

    memory_md.write_text(new_content, encoding="utf-8")
    file_count = sum(len(v) for v in sections.values())
    print(f"OK: MEMORY.md updated ({file_count} files indexed).")


def main():
    parser = argparse.ArgumentParser(description="Memory index auto-generator")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout, change nothing")
    parser.add_argument("--check", action="store_true", help="Compare with current state")
    parser.add_argument("--memory-dir", type=Path, default=MEMORY_DIR)
    args = parser.parse_args()

    update_memory_md(args.memory_dir, args.dry_run, args.check)


if __name__ == "__main__":
    main()
