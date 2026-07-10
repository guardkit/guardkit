#!/usr/bin/env python3
"""Generate (or verify) the GuardKit command-distribution MANIFEST.

PB-3 (DIM3-F3): every copy generation of the installer command markdowns has,
until now, carried no provenance — the ~/.agentecflow drift sat undetected ~7
weeks. This manifest is the single provenance source, designed ONCE to serve
three consumers:

  * install.sh   — reads the tombstone list to PRUNE retired command names from
                   an already-installed ~/.agentecflow/commands (additive-copy
                   left them forever); reads the version to stamp the marker.
  * guardkit doctor — compares an installed commands dir against the per-file
                   sha256 to report current/modified/stale/retired (report-only).
  * packaging    — documents the canonical command include set (the wheel ships
                   the same files under guardkit/_installer_core via DF-011).

The manifest is HASH-OF-CONTENT ONLY — it never stores file content, only the
sha256 of each command markdown. `source_commit` is best-effort provenance (the
last commit that touched the file); `version` is derived from the single source
guardkit/__init__.py — killing the 3-4 unrelated hardcoded version stamps.

Usage:
    python scripts/generate_command_manifest.py           # write the manifest
    python scripts/generate_command_manifest.py --check    # CI: fail on drift

`--check` compares content hashes + version + tombstone set + command name set
(the load-bearing fields). It deliberately IGNORES `source_commit` drift, which
depends on git history depth and commit ordering (a shallow CI clone, or a same
-commit edit-and-regenerate, would otherwise produce spurious mismatches).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMMANDS_DIR = _REPO_ROOT / "installer" / "core" / "commands"
_MANIFEST_PATH = _COMMANDS_DIR / "MANIFEST.json"
_INIT_PY = _REPO_ROOT / "guardkit" / "__init__.py"

SCHEMA_VERSION = 1

# Retired command markdowns: deleted from installer/core/commands but historically
# copied into ~/.agentecflow/commands (and project .claude/) by the additive-copy
# installer with no prune path. install.sh removes these names on the next run;
# `guardkit doctor` reports any that are still present. Curated (the files are
# gone, so they cannot be auto-derived); each carries its retirement commit.
TOMBSTONES = [
    {
        "name": "impact-analysis.md",
        "retired_in": "ce914f7c",
        "reason": (
            "Imports the physically-removed guardkit.knowledge.graphiti_client "
            "(FEAT-MEM-09 WS-2c); an attended invocation loads a spec whose "
            "implementation stack is deleted."
        ),
    },
    {
        "name": "system-overview.md",
        "retired_in": "71becc51",
        "reason": "Retired from installer/core/commands; superseded workflow.",
    },
    {
        "name": "task-refine.md",
        "retired_in": "f20e0b68",
        "reason": (
            "Retired per DEC-task-refine-retirement (ADR-C consolidation, "
            "2026-07-09): zero inbound command references; claimed module "
            "refinement_handler.py never existed; role absorbed by re-running "
            "/task-work and /task-review's [I]mplement flow."
        ),
    },
    {
        "name": "figma-to-react.md",
        "retired_in": "PENDING",
        "reason": (
            "Retired per DEC-design-tool-trio-retirement (DF-018 §2.4 "
            "Option A, ACCEPTED Rich 2026-07-09): revives+executes "
            "TASK-UX-2DAB. Stack-specific Figma->React design-to-code, "
            "superseded by the unified design_url path "
            "(guardkit/orchestrator/mcp_design_extractor.py); no live "
            "guardkit/installer consumer; lapsed removal_planned 2026-06-01."
        ),
    },
    {
        "name": "zeplin-to-maui.md",
        "retired_in": "PENDING",
        "reason": (
            "Retired per DEC-design-tool-trio-retirement (DF-018 §2.4 "
            "Option A, ACCEPTED Rich 2026-07-09): revives+executes "
            "TASK-UX-2DAB. Stack-specific Zeplin->.NET MAUI design-to-code, "
            "superseded by the unified design_url path; no live consumer."
        ),
    },
    {
        "name": "mcp-zeplin.md",
        "retired_in": "PENDING",
        "reason": (
            "Retired per DEC-design-tool-trio-retirement (DF-018 §2.4 "
            "Option A, ACCEPTED Rich 2026-07-09): documents a Zeplin MCP "
            "integration the orchestrator does not implement; extended into "
            "the TASK-UX-2DAB retirement per DF-018 §2.4."
        ),
    },
]


def _read_version() -> str:
    """Read __version__ from guardkit/__init__.py — the single version source."""
    text = _INIT_PY.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit(f"could not read __version__ from {_INIT_PY}")
    return match.group(1)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_commit(path: Path) -> str:
    """Last commit that touched ``path`` (best-effort provenance)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "log", "-1", "--format=%h", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        commit = out.stdout.strip()
        return commit or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def build_manifest() -> dict:
    """Build the manifest dict from the current repo state."""
    commands: dict[str, dict[str, str]] = {}
    for md in sorted(_COMMANDS_DIR.glob("*.md")):
        commands[md.name] = {
            "sha256": _sha256(md.read_bytes()),
            "source_commit": _source_commit(md),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "guardkit-command-distribution-manifest",
        "package": "guardkit-py",
        "version": _read_version(),
        "note": (
            "CI-generated by scripts/generate_command_manifest.py. "
            "Hash-of-content only — never a second content source. "
            "Regenerate: python scripts/generate_command_manifest.py"
        ),
        "commands": commands,
        "tombstones": TOMBSTONES,
    }


def _serialise(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=False) + "\n"


def _comparable(manifest: dict) -> dict:
    """Project a manifest onto its load-bearing (checked) fields.

    Drops `source_commit` and `note` — provenance/informational fields that
    depend on git-history depth and are not part of the content contract.
    """
    return {
        "schema_version": manifest.get("schema_version"),
        "package": manifest.get("package"),
        "version": manifest.get("version"),
        "commands": {
            name: entry.get("sha256")
            for name, entry in manifest.get("commands", {}).items()
        },
        "tombstones": [t.get("name") for t in manifest.get("tombstones", [])],
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed manifest matches the repo (CI); do not write.",
    )
    args = parser.parse_args(argv)

    fresh = build_manifest()

    if args.check:
        if not _MANIFEST_PATH.is_file():
            print(f"MANIFEST missing: {_MANIFEST_PATH}", file=sys.stderr)
            print("Run: python scripts/generate_command_manifest.py", file=sys.stderr)
            return 1
        committed = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        if _comparable(committed) != _comparable(fresh):
            print(
                "Command MANIFEST is STALE (content hashes / version / tombstones "
                "/ command set drifted). Regenerate:\n"
                "  python scripts/generate_command_manifest.py",
                file=sys.stderr,
            )
            return 1
        print("Command MANIFEST is up to date.")
        return 0

    _MANIFEST_PATH.write_text(_serialise(fresh), encoding="utf-8")
    print(f"Wrote {_MANIFEST_PATH} ({len(fresh['commands'])} commands, "
          f"version {fresh['version']}, {len(fresh['tombstones'])} tombstones).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
