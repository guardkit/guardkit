#!/usr/bin/env python3
"""feature_plan_bdd_link.py — /feature-plan Step 11 producer script (TASK-FIX-RWOP1.1).

Purpose
-------
Provide an imperative command-line entry point for /feature-plan Step 11
(BDD scenario linking / ``@task:`` tagging), so the step is reachable from
the slash-command's execution trace via ``Execute:`` rather than depending
on Claude-as-runtime to compose a Python matcher callback.

This is the Path B remediation chosen by TASK-FIX-RWOP1.1 to close the
runner-without-producer orphan documented in TASK-REV-RWOP1 Finding #1.
The shape mirrors TASK-FIX-3C9D's R1 fix: a thin CLI shim around the
existing deterministic library, invoked from feature-plan.md as
``Execute: python3 ~/.agentecflow/bin/feature-plan-bdd-link ...``.

Architecture
------------

The script splits Step 11 across two subcommands so the matcher (the
``bdd-linker`` subagent) can run between them as a Claude-runtime
``INVOKE Task(...)`` invocation:

1. ``prepare`` — discover the ``.feature`` file, parse it, read the
   feature YAML for the task list, extract acceptance criteria from each
   task's markdown file, build a :class:`MatchingRequest`, and write it as
   JSON to ``--output``. Emits a status JSON to stdout so the caller
   knows whether to proceed (status=ready), skip silently (status=skipped
   with one of ``no_feature_file``, ``no_scenarios``, ``all_tagged``), or
   re-run after fixing input (status=error).

2. ``apply`` — read the matcher's response (a list of ``TaskMatch`` JSON
   objects from the ``bdd-linker`` subagent), validate it via
   :func:`bdd_linking_phase.parse_matcher_response`, and call
   :func:`bdd_linker.apply_mapping` to atomically rewrite the ``.feature``
   file with ``@task:<TASK-ID>`` tags. Emits the one-line ``[Step 11]``
   summary to stdout.

The mechanical building blocks (``discover_feature_file``,
``parse_feature_file``, ``build_matching_request``, ``apply_mapping``,
``parse_matcher_response``) are reused from the existing
``installer/core/commands/lib/bdd_linker.py`` and
``installer/core/commands/lib/bdd_linking_phase.py`` libraries —
``run_linking_phase`` is the in-process reference implementation but is
not invoked from production code (see that module's docstring).

Usage
-----

    # Step 11.1 — prepare matching request
    python3 ~/.agentecflow/bin/feature-plan-bdd-link prepare \\
        --project-root . \\
        --feature-slug dark-mode \\
        --feature-yaml .guardkit/features/FEAT-XXXX.yaml \\
        --output /tmp/bdd-link-request.json

    # Step 11.2 (Claude-runtime): INVOKE Task(bdd-linker, prompt=<contents
    # of /tmp/bdd-link-request.json>) → write response to
    # /tmp/bdd-link-response.json

    # Step 11.3 — apply matches
    python3 ~/.agentecflow/bin/feature-plan-bdd-link apply \\
        --project-root . \\
        --feature-slug dark-mode \\
        --task-matches-file /tmp/bdd-link-response.json

Exit codes
----------

Both subcommands use these conventions so feature-plan.md prose can
branch deterministically:

* ``0`` — success (including the silent-skip paths from ``prepare``).
* ``1`` — input error (missing file, malformed YAML, etc.).
* ``2`` — matcher response error (``apply`` only). Surface the message
  to the user and offer a retry; do NOT swallow silently — that would
  recreate the runner-without-producer silent-failure mode this script
  is closing.

See also
--------

* ``installer/core/commands/feature-plan.md`` Step 11 — the prose
  contract that invokes this script.
* ``installer/core/agents/bdd-linker.md`` — the matching subagent.
* ``installer/core/commands/lib/bdd_linker.py`` — parsing + atomic
  rewrite primitives.
* ``installer/core/commands/lib/bdd_linking_phase.py`` — reference
  in-process orchestrator (kept for tests; ``run_linking_phase`` is
  intentionally not called from production).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Library reuse — these are the deterministic primitives this script
# composes. Importing from the existing modules (rather than re-implementing)
# preserves the parsing/atomicity/idempotency guarantees from TASK-FP-LINK.
from installer.core.commands.lib.bdd_linker import (  # noqa: E402
    DEFAULT_CONFIDENCE_THRESHOLD,
    MatchingRequest,
    TaskInfo,
    apply_mapping,
    build_matching_request,
    existing_task_tags,
    parse_feature_file,
)
from installer.core.commands.lib.bdd_linking_phase import (  # noqa: E402
    MatcherResponseError,
    discover_feature_file,
    parse_matcher_response,
)


# ---------------------------------------------------------------------------
# Status payloads emitted to stdout by `prepare`
# ---------------------------------------------------------------------------

# Silent-skip reasons map 1:1 to PhaseResult.status values from
# bdd_linking_phase.run_linking_phase, so feature-plan.md prose can react
# to either entry-point with the same vocabulary.
_SKIP_NO_FEATURE_FILE = "no_feature_file"
_SKIP_NO_SCENARIOS = "no_scenarios"
_SKIP_ALL_TAGGED = "all_tagged"


# ---------------------------------------------------------------------------
# Acceptance-criteria extraction
# ---------------------------------------------------------------------------


_AC_HEADING_RE = re.compile(r"^#{1,6}\s+Acceptance\s+Criteria\s*$", re.IGNORECASE)
_AC_BULLET_RE = re.compile(r"^\s*[-*]\s+(?:\[[\sxX]\]\s+)?(.*\S)\s*$")


def extract_acceptance_criteria(body: str) -> List[str]:
    """Pull bulleted acceptance criteria out of a task markdown body.

    Looks for a heading line matching ``## Acceptance Criteria`` (any
    heading depth, case-insensitive) and collects subsequent ``-`` /
    ``*`` bullet lines (with optional ``[ ]`` / ``[x]`` checkbox prefix)
    until the next heading or blank-line-then-heading boundary.

    Returns an empty list when the section is absent or contains no
    bullet lines — the matcher subagent treats missing ACs as "use task
    title/description only", which is the right fallback.
    """
    lines = body.splitlines()
    acs: List[str] = []
    in_section = False

    for line in lines:
        if _AC_HEADING_RE.match(line):
            in_section = True
            continue
        if in_section and re.match(r"^#{1,6}\s+", line):
            # Next heading ends the section.
            break
        if not in_section:
            continue
        bullet = _AC_BULLET_RE.match(line)
        if bullet:
            acs.append(bullet.group(1).strip())

    return acs


# ---------------------------------------------------------------------------
# Feature YAML loading
# ---------------------------------------------------------------------------


def load_feature_yaml(path: Path) -> Dict[str, Any]:
    """Load and parse a feature YAML file.

    Falls back to JSON if PyYAML is unavailable AND the file ends in
    ``.json`` (mirroring ``generate_feature_yaml.py``'s fallback shape).

    Raises:
        FileNotFoundError: If ``path`` doesn't exist.
        ValueError: If the file can't be parsed as YAML/JSON.
    """
    if not path.is_file():
        raise FileNotFoundError(f"feature YAML not found: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        # PyYAML not installed — accept JSON-shaped files only.
        if path.suffix == ".json":
            return json.loads(text)
        raise ValueError(
            f"PyYAML is required to read {path}; install pyyaml or use a .json feature file"
        )

    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"failed to parse {path}: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path}: expected a YAML mapping at top level, got {type(loaded).__name__}"
        )
    return loaded


def collect_task_infos(
    feature_yaml: Dict[str, Any],
    project_root: Path,
) -> List[TaskInfo]:
    """Convert a feature YAML's ``tasks`` list into :class:`TaskInfo` values.

    For each task, reads its markdown file (resolved relative to
    ``project_root``) and extracts acceptance criteria from the
    ``## Acceptance Criteria`` section. Tasks with missing markdown
    files are kept (with empty ACs) rather than silently dropped — the
    matcher will use title/description alone, and the user sees the
    task in the request payload.
    """
    raw_tasks = feature_yaml.get("tasks") or []
    if not isinstance(raw_tasks, list):
        raise ValueError(
            f"feature YAML 'tasks' must be a list (got {type(raw_tasks).__name__})"
        )

    infos: List[TaskInfo] = []
    for entry in raw_tasks:
        if not isinstance(entry, dict):
            continue  # Be lenient — skip malformed entries rather than crash.

        task_id = str(entry.get("id") or entry.get("task_id") or "").strip()
        if not task_id:
            continue

        title = str(entry.get("name") or entry.get("title") or "").strip()
        description = str(entry.get("description") or "").strip()
        file_path_str = str(entry.get("file_path") or "").strip()

        acs: List[str] = []
        if file_path_str:
            md_path = (project_root / file_path_str).resolve()
            try:
                body_text = md_path.read_text(encoding="utf-8")
            except (FileNotFoundError, IsADirectoryError, PermissionError):
                body_text = ""
            if body_text:
                # Strip frontmatter if present so the AC section regex
                # doesn't accidentally match inside it.
                body = _strip_frontmatter(body_text)
                acs = extract_acceptance_criteria(body)

        infos.append(
            TaskInfo(
                task_id=task_id,
                title=title,
                description=description,
                acceptance_criteria=acs,
            )
        )

    return infos


def _strip_frontmatter(text: str) -> str:
    """Drop a leading ``---``-delimited YAML frontmatter block, if any."""
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2]


# ---------------------------------------------------------------------------
# `prepare` subcommand
# ---------------------------------------------------------------------------


def cmd_prepare(args: argparse.Namespace) -> int:
    """Run the ``prepare`` subcommand.

    Discovers the ``.feature`` file, parses it, loads the feature YAML
    for tasks (with ACs), builds a :class:`MatchingRequest`, writes the
    JSON to ``args.output`` (or stdout if absent), and emits a status
    JSON to stdout so the caller can branch on silent-skip vs ready.
    """
    project_root = Path(args.project_root).resolve()
    feature_slug = args.feature_slug

    feature_path = discover_feature_file(project_root, feature_slug)
    if feature_path is None:
        _emit_status({"status": "skipped", "reason": _SKIP_NO_FEATURE_FILE})
        return 0

    doc = parse_feature_file(feature_path)
    if not doc.scenarios:
        _emit_status(
            {
                "status": "skipped",
                "reason": _SKIP_NO_SCENARIOS,
                "feature_path": str(feature_path),
            }
        )
        return 0

    # Idempotency short-circuit: if every scenario is already tagged we
    # don't need to invoke the matcher at all (matches run_linking_phase
    # behaviour).
    already = existing_task_tags(doc)
    if len(already) == len(doc.scenarios):
        _emit_status(
            {
                "status": "skipped",
                "reason": _SKIP_ALL_TAGGED,
                "feature_path": str(feature_path),
            }
        )
        return 0

    feature_yaml_path = Path(args.feature_yaml)
    try:
        feature_yaml = load_feature_yaml(feature_yaml_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"feature-plan-bdd-link prepare: {exc}", file=sys.stderr)
        return 1

    tasks = collect_task_infos(feature_yaml, project_root)
    if not tasks:
        # No tasks to match against — silent skip rather than a noisy
        # "everything untagged" report.
        _emit_status(
            {
                "status": "skipped",
                "reason": "no_tasks",
                "feature_path": str(feature_path),
            }
        )
        return 0

    request = build_matching_request(
        doc,
        tasks,
        confidence_threshold=args.confidence_threshold,
        skip_already_tagged=True,
    )

    # Defensive: build_matching_request returns scenarios=[] when every
    # scenario was already tagged. We caught this above with the len()
    # check, but re-check here in case someone passes a doc with weird
    # tag layout that fooled existing_task_tags.
    if not request.scenarios:
        _emit_status(
            {
                "status": "skipped",
                "reason": _SKIP_ALL_TAGGED,
                "feature_path": str(feature_path),
            }
        )
        return 0

    payload_json = request.to_json(indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload_json, encoding="utf-8")
        request_path: Optional[str] = str(output_path)
    else:
        # Without --output, emit the payload JSON on stdout under a key
        # so the status envelope still parses cleanly.
        request_path = None

    status_payload: Dict[str, Any] = {
        "status": "ready",
        "feature_path": str(feature_path),
        "scenarios_to_match": len(request.scenarios),
        "task_count": len(request.tasks),
        "confidence_threshold": request.confidence_threshold,
        "already_tagged_count": len(already),
    }
    if request_path is not None:
        status_payload["request_path"] = request_path
    else:
        # Caller asked to receive the payload inline.
        status_payload["request"] = json.loads(payload_json)

    _emit_status(status_payload)
    return 0


# ---------------------------------------------------------------------------
# `apply` subcommand
# ---------------------------------------------------------------------------


def cmd_apply(args: argparse.Namespace) -> int:
    """Run the ``apply`` subcommand.

    Reads the matcher's response, parses it via
    :func:`parse_matcher_response`, and calls :func:`apply_mapping` to
    rewrite the ``.feature`` file. Emits the one-line summary to stdout
    in the same shape as :func:`run_linking_phase`.
    """
    project_root = Path(args.project_root).resolve()
    feature_slug = args.feature_slug

    feature_path = discover_feature_file(project_root, feature_slug)
    if feature_path is None:
        # Apply called without a feature file — treat as skip (caller
        # should have noticed at prepare time, but we don't crash).
        _emit_status({"status": "skipped", "reason": _SKIP_NO_FEATURE_FILE})
        return 0

    raw_matches: Any
    if args.task_matches_file:
        matches_path = Path(args.task_matches_file)
        try:
            raw_matches = matches_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(
                f"feature-plan-bdd-link apply: matches file not found: {matches_path}",
                file=sys.stderr,
            )
            return 1
    elif not sys.stdin.isatty():
        raw_matches = sys.stdin.read()
    else:
        print(
            "feature-plan-bdd-link apply: provide --task-matches-file or pipe matches on stdin",
            file=sys.stderr,
        )
        return 1

    try:
        matches = parse_matcher_response(raw_matches)
    except MatcherResponseError as exc:
        # Exit code 2 lets feature-plan.md branch on "matcher returned
        # garbage" specifically, so the user gets a retry hint rather
        # than a silent miss.
        print(
            f"feature-plan-bdd-link apply: matcher response error: {exc}",
            file=sys.stderr,
        )
        return 2

    result = apply_mapping(
        feature_path,
        matches,
        confidence_threshold=args.confidence_threshold,
        dry_run=args.dry_run,
    )

    # Print the human-readable summary in the same form bdd_linking_phase
    # uses, so transcripts look identical regardless of which entry-point
    # /feature-plan went through.
    print(f"[Step 11] {result.summary}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _emit_status(payload: Dict[str, Any]) -> None:
    """Write a status JSON object to stdout, one object per line."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with prepare/apply subcommands."""
    parser = argparse.ArgumentParser(
        prog="feature-plan-bdd-link",
        description=(
            "/feature-plan Step 11 producer script — split BDD scenario "
            "linking across prepare/apply so the bdd-linker subagent can "
            "run between the two via INVOKE Task(...). See feature-plan.md "
            "Step 11 for the full prose contract."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # prepare
    prep = sub.add_parser(
        "prepare",
        help="Discover the .feature file, build the MatchingRequest, write JSON for the bdd-linker subagent.",
    )
    prep.add_argument(
        "--project-root",
        default=".",
        help="Project root (where features/ lives). Default: current directory.",
    )
    prep.add_argument(
        "--feature-slug",
        required=True,
        help="Slug of the feature /feature-plan just created (e.g. 'dark-mode').",
    )
    prep.add_argument(
        "--feature-yaml",
        required=True,
        help="Path to the feature YAML (e.g. '.guardkit/features/FEAT-XXXX.yaml') for task list + ACs.",
    )
    prep.add_argument(
        "--output",
        help="Path to write the MatchingRequest JSON. If omitted, the payload is embedded in the stdout status envelope under 'request'.",
    )
    prep.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help=f"Confidence threshold for the matcher (default: {DEFAULT_CONFIDENCE_THRESHOLD}).",
    )
    prep.set_defaults(func=cmd_prepare)

    # apply
    appl = sub.add_parser(
        "apply",
        help="Read TaskMatch[] JSON from --task-matches-file (or stdin) and rewrite the .feature file.",
    )
    appl.add_argument(
        "--project-root",
        default=".",
        help="Project root (where features/ lives). Default: current directory.",
    )
    appl.add_argument(
        "--feature-slug",
        required=True,
        help="Slug of the feature being linked.",
    )
    appl.add_argument(
        "--task-matches-file",
        help="Path to the bdd-linker subagent's TaskMatch[] JSON response. If omitted, reads from stdin.",
    )
    appl.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help=f"Confidence threshold (default: {DEFAULT_CONFIDENCE_THRESHOLD}).",
    )
    appl.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the result but don't write to the .feature file.",
    )
    appl.set_defaults(func=cmd_apply)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
