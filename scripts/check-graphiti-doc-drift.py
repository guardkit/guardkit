#!/usr/bin/env python3
"""Flag stale graphiti-related docs across GuardKit-using repos (TASK-INF-5053).

Scans `.claude/rules/graphiti-knowledge-graph.md`, `.claude/commands/task-complete.md`,
and `~/.agentecflow/commands/task-complete.md` for the pre-INF-5053 prose
(claims that the HTTP MCP server silently coerces `group_id`).

Read-only. Prints a report. Does NOT modify any files. The recommended
replacement prose lives in this GuardKit repo's
`.claude/rules/graphiti-knowledge-graph.md` (rules) and
`installer/core/commands/task-complete.md` (command); the user reviews each
flagged file and patches manually.

Usage:
  scripts/check-graphiti-doc-drift.py
  scripts/check-graphiti-doc-drift.py --roots ~/Projects ~/.agentecflow --max-depth 4
  scripts/check-graphiti-doc-drift.py --verbose
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

# Patterns indicating the old (pre-INF-5053) diagnosis. Any one of these in a
# graphiti-related doc means the file pre-dates 2026-05-02 and reflects the
# now-invalidated "server silently overrides group_id" claim.
STALE_PATTERNS = [
    re.compile(r"Known transport limitation"),
    re.compile(r"silently overrides .* group_id", re.IGNORECASE),
    re.compile(r"HTTP MCP coerces"),
    re.compile(r"MCP write .group_id. coercion", re.IGNORECASE),
    re.compile(r"server silently overrides"),
]

# Patterns indicating the file already carries the post-INF-5053 correction.
# At least one means the file has been updated.
CURRENT_PATTERNS = [
    re.compile(r"TASK-INF-5053"),
    re.compile(r"could not be reproduced"),
    re.compile(r"is honoured \(TASK-INF-5053\)"),
]

# Files to scan, relative to a repo root.
SCAN_TARGETS = [
    ".claude/rules/graphiti-knowledge-graph.md",
    ".claude/rules/graphiti-knowledge.md",
    ".claude/commands/task-complete.md",
    "commands/task-complete.md",  # ~/.agentecflow layout
    "installer/core/commands/task-complete.md",  # GuardKit source-of-truth
]

# Directories never worth descending into.
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
             ".mypy_cache", ".pytest_cache", "dist", "build", ".tox"}


@dataclass
class Finding:
    path: Path
    status: str  # "stale", "current", "neutral"
    stale_hits: list[tuple[int, str]]  # (lineno, line)
    current_hits: list[tuple[int, str]]


def scan_file(path: Path) -> Finding:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError) as e:
        return Finding(path, "neutral", [], [(0, f"<read error: {e}>")])

    stale: list[tuple[int, str]] = []
    current: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(p.search(line) for p in STALE_PATTERNS):
            stale.append((lineno, line.rstrip()))
        if any(p.search(line) for p in CURRENT_PATTERNS):
            current.append((lineno, line.rstrip()))

    if stale and not current:
        status = "stale"
    elif stale and current:
        # Mixed — file was edited but old prose lingers somewhere.
        status = "stale"
    elif current and not stale:
        status = "current"
    else:
        status = "neutral"
    return Finding(path, status, stale, current)


def discover_repo_roots(roots: list[Path], max_depth: int) -> list[Path]:
    """Yield directories that look like project roots (.git or .claude present)."""
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        root = root.expanduser().resolve()
        if not root.exists():
            continue
        # The root itself counts.
        if root not in seen:
            seen.add(root)
            out.append(root)
        # Walk to max_depth.
        root_parts = len(root.parts)
        for dirpath, dirnames, _ in os.walk(root):
            d = Path(dirpath)
            depth = len(d.parts) - root_parts
            if depth >= max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = [n for n in dirnames if n not in SKIP_DIRS]
            # A repo root has either .git or .claude as a child.
            if (d / ".git").exists() or (d / ".claude").exists():
                if d not in seen:
                    seen.add(d)
                    out.append(d)
                # Don't descend further; siblings inside a repo are not separate repos.
                dirnames[:] = []
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--roots",
        nargs="+",
        default=[
            str(Path.home() / ".agentecflow"),
            # Parent of the current repo, to catch sibling project repos.
            str(Path.cwd().parent),
        ],
        help="Search roots (default: ~/.agentecflow and parent of cwd)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=4,
        help="Max directory depth from each root (default: 4)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show every matched line, not just the first per file",
    )
    args = parser.parse_args()

    roots = [Path(r) for r in args.roots]
    repo_roots = discover_repo_roots(roots, args.max_depth)

    print("Graphiti doc-drift scan (TASK-INF-5053)")
    print("=" * 50)
    print()
    print("Scanned roots:")
    for r in roots:
        rp = r.expanduser().resolve()
        marker = "" if rp.exists() else "  (does not exist)"
        print(f"  - {rp}{marker}")
    print()
    print(f"Discovered {len(repo_roots)} candidate repo root(s).")
    print()

    findings: list[Finding] = []
    for repo in repo_roots:
        for target in SCAN_TARGETS:
            p = repo / target
            if p.is_file():
                findings.append(scan_file(p))

    counts = {"stale": 0, "current": 0, "neutral": 0}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1

    if not findings:
        print("No matching files found under the scanned roots.")
        return 0

    # Print stale findings first — they're the actionable ones.
    for status_label, header in [
        ("stale", "STALE (pre-TASK-INF-5053 prose detected)"),
        ("current", "CURRENT (already updated)"),
        ("neutral", "NEUTRAL (no graphiti-override prose either way)"),
    ]:
        group = [f for f in findings if f.status == status_label]
        if not group:
            continue
        print(f"== {header} — {len(group)} file(s) ==")
        for f in group:
            print(f"  {f.path}")
            if status_label == "stale":
                hits = f.stale_hits if args.verbose else f.stale_hits[:3]
                for lineno, line in hits:
                    snippet = line[:110] + ("..." if len(line) > 110 else "")
                    print(f"    L{lineno}: {snippet}")
                if not args.verbose and len(f.stale_hits) > 3:
                    print(f"    ... +{len(f.stale_hits) - 3} more (use --verbose)")
            elif status_label == "current" and args.verbose:
                for lineno, line in f.current_hits[:1]:
                    snippet = line[:110] + ("..." if len(line) > 110 else "")
                    print(f"    L{lineno}: {snippet}")
        print()

    print("Summary")
    print("-" * 7)
    for label in ("stale", "current", "neutral"):
        if counts.get(label):
            print(f"  {label:8s}: {counts[label]}")
    print(f"  {'total':8s}: {len(findings)}")
    print()

    if counts["stale"]:
        print("Action: review each STALE file and replace the old override prose with")
        print("the post-INF-5053 wording. The source-of-truth files are:")
        print("  - .claude/rules/graphiti-knowledge-graph.md  (per-repo rules)")
        print("  - installer/core/commands/task-complete.md   (distributed command)")
        print("Both live in the GuardKit repo. Audit trail: docs/state/TASK-INF-5053/audit.md")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
