#!/usr/bin/env python3
"""
handover-lint.py — keep the LINEAGE handoff honest: state, not agenda.

The handoff a session leaves is for the *next* session to act on — open items,
deploy/test status, IDs to hand over. It is not a place for advice to a future
self ("consider doing X", "recommend Y", "for next session…"). That kind of
hedge-word agenda is exactly what the doctrine says to keep out, and the rule
erodes the moment it lives only in your head. This puts mechanical teeth on it.

Scans ONLY the `### Handoff` section of the most recent `## SESSION N — …` block.
Nothing else in the commit is read.

Usage:
  python3 scripts/handover-lint.py            # pre-commit mode: acts only if
                                              # memory/LINEAGE.md is staged
  python3 scripts/handover-lint.py --file P   # lint the handoff in file P directly
                                              # (for testing / manual checks)

Wire it as a pre-commit hook (.git/hooks/pre-commit) to block a commit whose
handoff drifts into agenda. Exit 1 = blocked.
Override (deliberate, from a terminal): HANDOVER_OVERRIDE=1 git commit …

Zero dependencies (stdlib only).
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINEAGE = ROOT / "memory" / "LINEAGE.md"

# Phrases that signal agenda / advice / self-direction rather than state.
# These target *intent*, not a literal translation: past tense and adjective
# forms ("considered", "recommended", "worth carrying forward") are allowed —
# only the forward-looking, steering forms are rejected.
BLACKLIST = [
    (r"\bconsider(?:ing)?\b", "agenda"),
    (r"\brecommend(?:s|ing|ation|ations)?\b", "advice"),
    (r"should\s+probably", "agenda"),
    (r"might\s+want\s+to", "agenda"),
    (r"\bworth\s+(?:doing|considering|a\s+look|exploring|trying|adding|checking|fixing)\b", "agenda"),
    (r"for\s+(?:the\s+)?next\s+session", "agenda for the next session"),
    (r"next\s+session\s+should", "agenda for the next session"),
    (r"it(?:'d|\s+would)\s+be\s+(?:good|worth|nice|better)\s+to", "agenda"),
    (r"\bproactively\b", "self-direction"),
    (r"\bmaybe\b", "agenda"),
]


def extract_last_handover(content: str) -> str | None:
    """Return the text of the `### Handoff` section in the LAST `## SESSION` block,
    or None if there's no session or no handoff section yet (work in progress)."""
    session_matches = list(re.finditer(r"^## SESSION\s+\d+[a-z]*\s+[—-]", content, re.MULTILINE))
    if not session_matches:
        return None
    last_session_text = content[session_matches[-1].start():]

    handoff_match = re.search(r"^###\s+Handoff", last_session_text, re.MULTILINE)
    if not handoff_match:
        return None

    rest = last_session_text[handoff_match.end():]
    next_section = re.search(r"^###\s+|\n---\n", rest, re.MULTILINE)
    end = handoff_match.end() + (next_section.start() if next_section else len(rest))
    return last_session_text[handoff_match.start():end]


def find_violations(handover_text: str) -> list[tuple[int, str, str]]:
    """Return [(line_number_in_handoff, matched_text, rule), …]."""
    violations = []
    for i, line in enumerate(handover_text.split("\n"), start=1):
        for pattern, rule in BLACKLIST:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                violations.append((i, m.group().strip(), rule))
    return violations


def lint_text(content: str, source: str) -> int:
    handover = extract_last_handover(content)
    if handover is None:
        return 0  # no handoff section yet → nothing to block
    violations = find_violations(handover)
    if not violations:
        return 0

    print("", file=sys.stderr)
    print("🛑 HANDOFF VERBOSITY — commit blocked", file=sys.stderr)
    print(f"   The latest 'Handoff' section in {source} has {len(violations)} violation(s):", file=sys.stderr)
    for line, text, rule in violations:
        print(f"   ~line {line}: '{text}' [{rule}]", file=sys.stderr)
    print("", file=sys.stderr)
    print("   Handoff = open technical items + deploy/test status + data to hand over.", file=sys.stderr)
    print("   No agenda for the next session, no self-diagnosis, no meta-advice.", file=sys.stderr)
    print("", file=sys.stderr)
    print("   Override (deliberate): HANDOVER_OVERRIDE=1 git commit …", file=sys.stderr)
    print("", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint the LINEAGE handoff for agenda/hedge-words.")
    parser.add_argument("--file", type=Path, help="Lint this file's handoff directly (bypass the git-staged check).")
    args = parser.parse_args()

    if args.file is not None:
        if not args.file.exists():
            print(f"handover-lint: {args.file} does not exist", file=sys.stderr)
            return 2
        return lint_text(args.file.read_text(), str(args.file))

    if os.environ.get("HANDOVER_OVERRIDE") == "1":
        print("⚠️  handover-lint: HANDOVER_OVERRIDE=1 → skipping check (deliberate).", file=sys.stderr)
        return 0

    try:
        staged = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True
        ).splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        staged = []
    if "memory/LINEAGE.md" not in staged:
        return 0
    if not LINEAGE.exists():
        return 0

    return lint_text(LINEAGE.read_text(), str(LINEAGE.relative_to(ROOT)))


if __name__ == "__main__":
    sys.exit(main())
