"""Shared synthetic report builder for autobuild and direct mode.

This module provides public functions that unify the divergent synthetic
report implementations in autobuild.py and agent_invoker.py (TASK-FIX-D1A3).

Public API
----------
build_synthetic_report : Build a synthetic Player report dict.
generate_file_existence_promises : Extract file promises from acceptance criteria.
infer_requirements_from_files : Infer requirements_addressed from file contents.
"""

import fnmatch as _fnmatch
import logging
import re
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set

logger = logging.getLogger("guardkit.orchestrator.synthetic_report")

# Maximum file size (bytes) to read for content-based inference.
_MAX_FILE_SIZE = 100_000  # 100 KB

# Maximum total bytes to read across all files.
_MAX_TOTAL_BYTES = 1_000_000  # 1 MB

# Minimum keyword count in a criterion for inference to be attempted.
_MIN_KEYWORDS = 2

# Fraction of criterion keywords that must appear in file content.
_KEYWORD_THRESHOLD = 0.5  # 50%

# Stopwords filtered out of criterion text before keyword extraction.
_STOPWORDS: FrozenSet[str] = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "and", "but", "or",
    "nor", "not", "so", "yet", "for", "with", "from", "into", "onto",
    "upon", "about", "after", "before", "above", "below", "between",
    "through", "during", "without", "within", "along", "across",
    "that", "this", "these", "those", "each", "every", "all", "both",
    "few", "more", "most", "other", "some", "such", "only", "own",
    "same", "than", "too", "very", "just", "also", "then", "once",
    "here", "there", "when", "where", "why", "how", "what", "which",
    "who", "whom", "its", "of", "to", "in", "on", "at", "by", "as",
    "if", "no", "up",
    # Task-specific stopwords
    "create", "add", "update", "implement", "ensure", "verify",
    "should", "must", "file", "new",
})


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
    worktree_path: Optional[Path] = None,
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
    worktree_path : Optional[Path]
        Absolute path to the worktree root for content-based requirements
        inference (TASK-FIX-ASPF-006). When provided along with
        ``acceptance_criteria``, the builder will attempt to infer
        ``requirements_addressed`` by grepping file contents for criterion
        keywords. When ``None``, ``requirements_addressed`` remains ``[]``.

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

    # Infer requirements_addressed from file contents (TASK-FIX-ASPF-006).
    if acceptance_criteria and worktree_path is not None:
        inferred = infer_requirements_from_files(
            acceptance_criteria=acceptance_criteria,
            files_created=files_created,
            files_modified=files_modified,
            worktree_path=worktree_path,
        )
        if inferred:
            report["requirements_addressed"] = inferred
            logger.info(
                "Inferred %d requirements_addressed from file content "
                "analysis (TASK-FIX-ASPF-006)",
                len(inferred),
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
        - ``status`` ("complete" | "partial" | "incomplete") — callers **must**
          handle all three values; ``CriterionStatus.PARTIAL`` represents a
          file found on disk but absent from the git-change lists.
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

        # Tertiary pass: double-quoted file paths ("src/config.py")
        double_quoted_patterns = re.findall(r'"([^"]+\.[a-zA-Z]+)"', criterion_text)

        # Quaternary pass: single-quoted file paths ('src/config.py')
        single_quoted_patterns = re.findall(r"'([^']+\.[a-zA-Z]+)'", criterion_text)

        # Quinary pass: glob-like patterns in backticks (`alembic/versions/*.py`)
        glob_patterns = re.findall(r'`([^`]*\*[^`]*)`', criterion_text)

        # Deduplicate while preserving order
        all_patterns: List[str] = []
        seen: set = set()
        for p in (
            primary_patterns
            + secondary_patterns
            + double_quoted_patterns
            + single_quoted_patterns
            + glob_patterns
        ):
            if p not in seen:
                all_patterns.append(p)
                seen.add(p)

        # Match patterns against known file lists
        matched_in_lists: List[str] = []
        match_confidence = 1.0  # direct file name match

        for pattern in all_patterns:
            if "*" in pattern:
                # Glob pattern matching
                for known_file in all_files_list:
                    if _fnmatch.fnmatch(known_file, pattern):
                        if known_file not in matched_in_lists:
                            matched_in_lists.append(known_file)
                            match_confidence = min(match_confidence, 0.7)
            else:
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
                "confidence": match_confidence,
            })
            continue

        # Directory-structure matching: "Create X directory/folder"
        dir_creation_matches = re.findall(
            r'[Cc]reate\s+(?:the\s+)?(?:a\s+)?[`"\']?(\S+?)[`"\']?'
            r'\s+(?:directory|folder|dir)\b',
            criterion_text,
        )
        dir_structure_matches = re.findall(
            r'[`"\']?(\S+?)[`"\']?\s+directory\s+structure',
            criterion_text,
        )
        dir_names = dir_creation_matches + dir_structure_matches
        if dir_names:
            dir_matched: List[str] = []
            for dname in dir_names:
                dname = dname.strip("/")
                for known_file in all_files_list:
                    if known_file.startswith(dname + "/") or ("/" + dname + "/") in known_file:
                        if known_file not in dir_matched:
                            dir_matched.append(known_file)
            if dir_matched:
                file_status_parts = []
                for f in dir_matched:
                    action = "created" if f in created_set else "modified"
                    file_status_parts.append(f"{f} ({action})")
                evidence = (
                    "Directory-structure verified: "
                    + ", ".join(file_status_parts)
                )
                promises.append({
                    "criterion_id": criterion_id,
                    "criterion_text": criterion_text,
                    "status": "complete",
                    "evidence": evidence,
                    "evidence_type": "file_existence",
                    "confidence": 0.6,
                })
                continue

        # Disk check for file patterns when worktree_path is provided
        if worktree_path is not None:
            disk_found: List[str] = []
            for pattern in all_patterns:
                if "*" in pattern:
                    continue  # skip glob patterns for disk check
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
                    "confidence": 0.5,
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
                        "confidence": 0.5,
                    })
                    continue

        # No match anywhere
        promises.append({
            "criterion_id": criterion_id,
            "criterion_text": criterion_text,
            "status": "incomplete",
            "evidence": "No file-existence evidence for this criterion",
            "evidence_type": "file_existence",
            "confidence": 0.0,
        })

    return promises


# ---------------------------------------------------------------------------
# Requirements inference from file contents (TASK-FIX-ASPF-006)
# ---------------------------------------------------------------------------


def _extract_criterion_keywords(criterion_text: str) -> Set[str]:
    """Extract meaningful keywords from criterion text for content matching.

    Splits on non-alphanumeric characters, lowercases, filters stopwords
    and short words (<=3 chars).

    Parameters
    ----------
    criterion_text : str
        Raw acceptance criterion text.

    Returns
    -------
    Set[str]
        Set of lowercase keyword strings.
    """
    words = re.split(r'[^a-zA-Z0-9_]+', criterion_text.lower())
    return {
        w for w in words
        if len(w) > 3 and w not in _STOPWORDS
    }


def infer_requirements_from_files(
    acceptance_criteria: List[str],
    files_created: List[str],
    files_modified: List[str],
    worktree_path: Optional[Path] = None,
) -> List[str]:
    """Infer requirements_addressed by grepping file contents for criterion keywords.

    For each acceptance criterion, extracts meaningful keywords and searches
    the contents of created/modified files for matches.  A criterion is
    considered addressed when at least ``_KEYWORD_THRESHOLD`` (50%) of its
    keywords appear in the combined file contents.

    Parameters
    ----------
    acceptance_criteria : List[str]
        Acceptance criteria text strings to evaluate.
    files_created : List[str]
        Relative paths of files created by the Player.
    files_modified : List[str]
        Relative paths of files modified by the Player.
    worktree_path : Optional[Path]
        Absolute path to the worktree root.  Required for reading file
        contents.  When ``None``, returns ``[]``.

    Returns
    -------
    List[str]
        Criterion text strings for which content-based evidence was found.
        Suitable for populating ``requirements_addressed``.
    """
    if worktree_path is None:
        return []

    all_files = files_created + files_modified
    if not all_files:
        return []

    # Sort files alphabetically for deterministic reading order (TASK-VRF-005).
    # Without sorting, the 1MB total-byte cap causes different file subsets to
    # be read each turn (file order depends on git change order), producing
    # non-deterministic keyword matches and criteria oscillation.
    all_files = sorted(set(all_files))

    # Read file contents (with size guards)
    file_contents: Dict[str, str] = {}
    total_bytes = 0
    for rel_path in all_files:
        abs_path = worktree_path / rel_path
        try:
            size = abs_path.stat().st_size
            if size > _MAX_FILE_SIZE:
                logger.debug("Skipping %s (size %d > %d)", rel_path, size, _MAX_FILE_SIZE)
                continue
            if total_bytes + size > _MAX_TOTAL_BYTES:
                logger.debug(
                    "Total byte cap reached (%d), stopping file reads", total_bytes
                )
                break
            content = abs_path.read_text(encoding="utf-8")
            file_contents[rel_path] = content.lower()
            total_bytes += size
        except (OSError, UnicodeDecodeError):
            # Skip unreadable or binary files
            continue

    if not file_contents:
        return []

    # Combine all file contents for keyword searching
    combined_content = "\n".join(file_contents.values())

    addressed: List[str] = []
    for criterion_text in acceptance_criteria:
        keywords = _extract_criterion_keywords(criterion_text)
        if len(keywords) < _MIN_KEYWORDS:
            continue

        matched = sum(1 for kw in keywords if kw in combined_content)
        ratio = matched / len(keywords)

        if ratio >= _KEYWORD_THRESHOLD:
            addressed.append(criterion_text)
            logger.debug(
                "Criterion matched (%.0f%% keywords): %.80s",
                ratio * 100,
                criterion_text,
            )

    return addressed
