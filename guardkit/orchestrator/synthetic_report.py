"""Shared synthetic report builder for autobuild and direct mode.

This module provides two public functions that unify the divergent synthetic
report implementations in autobuild.py and agent_invoker.py (TASK-FIX-D1A3).

Public API
----------
build_synthetic_report : Build a synthetic Player report dict.
generate_file_existence_promises : Extract file promises from acceptance criteria.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("guardkit.orchestrator.synthetic_report")


def build_synthetic_report(
    task_id: str,
    turn: int,
    files_modified: List[str],
    files_created: List[str],
    tests_written: List[str],
    tests_passed: bool,
    test_count: int,
    implementation_notes: str,
    concerns: List[str],
    acceptance_criteria: Optional[List[str]] = None,
    task_type: Optional[str] = None,
    recovery_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a synthetic Player report from detected work state.

    This function constructs a report dict conforming to PLAYER_REPORT_SCHEMA
    and handles file-existence promise generation for scaffolding tasks.
    Git-analysis promise generation is intentionally NOT handled here -- it
    lives in autobuild.py to preserve the TASK-ACR-004 separation.

    Parameters
    ----------
    task_id : str
        Task identifier (e.g., "TASK-FIX-D1A3"). Caller sets this; callers
        that fill it later may pass "".
    turn : int
        Turn number (1-based).
    files_modified : List[str]
        Files modified by the player.
    files_created : List[str]
        Files created by the player.
    tests_written : List[str]
        Test files written by the player.
    tests_passed : bool
        Whether tests are passing.
    test_count : int
        Number of tests executed.
    implementation_notes : str
        Human-readable summary of what was done.
    concerns : List[str]
        Any concerns to flag for the Coach.
    acceptance_criteria : Optional[List[str]]
        Acceptance criteria text from the task frontmatter. Required for
        file-existence promise generation.
    task_type : Optional[str]
        Task type from frontmatter (e.g., "scaffolding", "feature"). When
        ``"scaffolding"`` and ``acceptance_criteria`` is provided, file-existence
        promises are generated.
    recovery_metadata : Optional[Dict[str, Any]]
        Optional recovery metadata to include in the report. Provided by the
        autobuild recovery path; omitted by direct mode.

    Returns
    -------
    Dict[str, Any]
        Synthetic Player report conforming to PLAYER_REPORT_SCHEMA.
    """
    has_criteria = bool(acceptance_criteria)
    should_generate_file_promises = task_type == "scaffolding" and has_criteria

    report: Dict[str, Any] = {
        "task_id": task_id,
        "turn": turn,
        "files_modified": files_modified,
        "files_created": files_created,
        "tests_written": tests_written,
        "tests_run": test_count > 0,
        "tests_passed": tests_passed,
        "test_output_summary": "",
        "implementation_notes": implementation_notes,
        "concerns": concerns,
        "requirements_addressed": [],
        "requirements_remaining": [],
        "_synthetic": True,
    }

    if recovery_metadata is not None:
        report["_recovery_metadata"] = recovery_metadata

    # Generate file-existence promises for scaffolding tasks only.
    # Non-scaffolding git-analysis promises are handled by autobuild.py.
    if should_generate_file_promises:
        promises = generate_file_existence_promises(
            files_created=files_created,
            files_modified=files_modified,
            acceptance_criteria=acceptance_criteria,
        )
        if promises:
            report["completion_promises"] = promises
            logger.info(
                "Generated %d file-existence promises "
                "for scaffolding task synthetic report",
                len(promises),
            )

    return report


def generate_file_existence_promises(
    files_created: List[str],
    files_modified: List[str],
    acceptance_criteria: List[str],
    worktree_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Generate file-existence promises by matching criteria against known files.

    Extracts file path patterns from acceptance criteria text and matches them
    against the provided lists of created/modified files. An optional disk
    check is performed when ``worktree_path`` is provided.

    This function unifies the two divergent implementations that previously
    existed in autobuild.py and agent_invoker.py:

    - autobuild.py used ``r'[\\w./\\-]+\\.\\w{1,5}'`` (primary pattern)
    - agent_invoker.py used backtick-quoted paths as a secondary pattern
    - agent_invoker.py also checked backtick-quoted directory references

    The shared implementation uses the autobuild regex as the primary pass,
    the backtick regex as a secondary pass, and a directory-reference check
    when ``worktree_path`` is provided to cover all styles.

    Parameters
    ----------
    files_created : List[str]
        Files created by the player.
    files_modified : List[str]
        Files modified by the player.
    acceptance_criteria : List[str]
        Acceptance criteria text strings to inspect.
    worktree_path : Optional[Path]
        Optional path to the worktree for disk-based existence checks.
        When provided, files found on disk (but not in created/modified
        lists) yield status ``"partial"`` rather than ``"incomplete"``.
        Directory references (backtick-quoted paths ending with ``/``)
        are also checked on disk.

    Returns
    -------
    List[Dict[str, Any]]
        One promise dict per acceptance criterion with keys:

        - ``criterion_id`` ("AC-NNN")
        - ``criterion_text`` (original criterion string)
        - ``status`` ("complete" | "partial" | "incomplete")
        - ``evidence`` (human-readable explanation)
        - ``evidence_type`` ("file_existence")
    """
    all_files_list = files_created + files_modified
    created_set = set(files_created)
    modified_set = set(files_modified)
    all_files_set = created_set | modified_set

    promises: List[Dict[str, Any]] = []

    for i, criterion_text in enumerate(acceptance_criteria):
        criterion_id = f"AC-{i + 1:03d}"

        # Primary pass: autobuild-style broad regex (matches path/to/file.ext)
        primary_patterns = re.findall(r'[\w./\-]+\.\w{1,5}', criterion_text)

        # Secondary pass: backtick-quoted paths from agent_invoker style
        secondary_patterns = re.findall(r'`([^`]+\.[a-zA-Z]+)`', criterion_text)

        # Deduplicate while preserving order
        all_patterns: List[str] = []
        seen: set = set()
        for p in primary_patterns + secondary_patterns:
            if p not in seen:
                all_patterns.append(p)
                seen.add(p)

        # Match patterns against known file lists
        matched_in_lists: List[str] = []
        for pattern in all_patterns:
            for known_file in all_files_list:
                if known_file.endswith(pattern) or pattern in known_file:
                    if known_file not in matched_in_lists:
                        matched_in_lists.append(known_file)

        if matched_in_lists:
            # Files found in created/modified lists -- status: complete
            file_status_parts = []
            for f in matched_in_lists:
                action = "created" if f in created_set else "modified"
                file_status_parts.append(f"{f} ({action})")
            evidence = "File-existence verified: " + ", ".join(file_status_parts)
            status = "complete"
            promises.append({
                "criterion_id": criterion_id,
                "criterion_text": criterion_text,
                "status": status,
                "evidence": evidence,
                "evidence_type": "file_existence",
            })
            continue

        # Disk check for file patterns when worktree_path is provided
        if worktree_path is not None:
            disk_found: List[str] = []
            for pattern in all_patterns:
                candidate = worktree_path / pattern
                if candidate.exists():
                    disk_found.append(pattern)

            if disk_found:
                evidence = "File existence verified: " + ", ".join(disk_found)
                promises.append({
                    "criterion_id": criterion_id,
                    "criterion_text": criterion_text,
                    "status": "partial",
                    "evidence": evidence,
                    "evidence_type": "file_existence",
                })
                continue

        # Directory reference check: backtick-quoted paths ending with /
        # e.g. `tests/seam/` -- only meaningful when worktree_path is available
        if worktree_path is not None:
            dir_refs = re.findall(r'`([^`]+/)`', criterion_text)
            if dir_refs:
                found_dirs = [
                    ref for ref in dir_refs
                    if (worktree_path / ref).is_dir()
                ]
                if found_dirs:
                    evidence = (
                        "File existence verified: " + ", ".join(found_dirs)
                    )
                    promises.append({
                        "criterion_id": criterion_id,
                        "criterion_text": criterion_text,
                        "status": "partial",
                        "evidence": evidence,
                        "evidence_type": "file_existence",
                    })
                    continue

        # No match anywhere
        promises.append({
            "criterion_id": criterion_id,
            "criterion_text": criterion_text,
            "status": "incomplete",
            "evidence": "No file-existence evidence for this criterion",
            "evidence_type": "file_existence",
        })

    return promises
