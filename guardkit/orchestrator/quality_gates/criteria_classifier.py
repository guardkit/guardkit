"""Acceptance criteria classifier for Coach verification routing.

Classifies each acceptance criterion as file_content, command_execution,
or manual, enabling the Coach validator to route verification through
the appropriate path:

- file_content: Verify via file existence/content analysis (synthetic report)
- command_execution: Verify by running the command and checking exit code
- manual: Cannot be auto-verified, skip or require human review

This addresses the FEAT-2AAA failure where command_execution criteria
(``pip install``, ``python -c``) were unverifiable via the synthetic
report path, causing UNRECOVERABLE_STALL.

See: .claude/reviews/TASK-REV-3F40-review-report.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class CriterionType(Enum):
    """Classification of an acceptance criterion."""

    FILE_CONTENT = "file_content"
    COMMAND_EXECUTION = "command_execution"
    MANUAL = "manual"


@dataclass
class ClassifiedCriterion:
    """An acceptance criterion with its classification and metadata."""

    text: str
    criterion_type: CriterionType
    confidence: float  # 0.0 - 1.0
    extracted_command: Optional[str] = None
    target_file: Optional[str] = None
    reason: str = ""


@dataclass
class ClassificationResult:
    """Result of classifying all acceptance criteria for a task."""

    criteria: List[ClassifiedCriterion] = field(default_factory=list)

    @property
    def file_content_criteria(self) -> List[ClassifiedCriterion]:
        return [c for c in self.criteria if c.criterion_type == CriterionType.FILE_CONTENT]

    @property
    def command_criteria(self) -> List[ClassifiedCriterion]:
        return [c for c in self.criteria if c.criterion_type == CriterionType.COMMAND_EXECUTION]

    @property
    def manual_criteria(self) -> List[ClassifiedCriterion]:
        return [c for c in self.criteria if c.criterion_type == CriterionType.MANUAL]

    @property
    def verifiable_count(self) -> int:
        return len(self.file_content_criteria) + len(self.command_criteria)

    @property
    def total_count(self) -> int:
        return len(self.criteria)


# --- Pattern Matchers ---

# Command execution indicators: backtick-wrapped commands, "runs successfully",
# "succeeds", "exits with", "returns exit code"
_COMMAND_PATTERNS = [
    # Backtick-wrapped shell commands
    re.compile(r"`([^`]+)`\s+(?:runs?\s+)?successfully", re.IGNORECASE),
    re.compile(r"`([^`]+)`\s+succeeds", re.IGNORECASE),
    re.compile(r"`([^`]+)`\s+(?:returns?|exits?\s+with)\s+(?:exit\s+)?(?:code\s+)?0", re.IGNORECASE),
    re.compile(r"`([^`]+)`\s+(?:completes?|passes?)\s+without\s+errors?", re.IGNORECASE),
    # Explicit command patterns
    re.compile(r"(?:run|execute|invoke)\s+`([^`]+)`", re.IGNORECASE),
    # Common command prefixes in backticks
    re.compile(r"`((?:pip|npm|yarn|pnpm|cargo|go|dotnet|gradle|mvn|pytest|python|node)\s+[^`]+)`", re.IGNORECASE),
    # curl/wget patterns
    re.compile(r"`((?:curl|wget|http)\s+[^`]+)`", re.IGNORECASE),
]

# File content indicators: "exists in", "contains", "added to", "appears in",
# "present in", "defined in", file extensions
_FILE_CONTENT_PATTERNS = [
    re.compile(r"`([^`]+)`\s+(?:added|appears?|present|defined|exists?|included|set)\s+(?:to|in)\s+`([^`]+)`", re.IGNORECASE),
    re.compile(r"`([^`]+)`\s+(?:contains?|includes?|has)\s+`([^`]+)`", re.IGNORECASE),
    re.compile(r"(?:file|module|class|function|method|variable|constant)\s+`([^`]+)`\s+(?:exists?|created|defined)", re.IGNORECASE),
    re.compile(r"`([^`]+\.(?:py|ts|js|toml|json|yaml|yml|md|rs|go|java|cs|rb|sh))`\s+(?:exists?|created|contains?)", re.IGNORECASE),
    re.compile(r"(?:no\s+)?syntax\s+errors?\s+in\s+`([^`]+)`", re.IGNORECASE),
    re.compile(r"valid\s+(?:TOML|JSON|YAML|XML)\s+(?:in\s+)?`?([^`\s]+)`?", re.IGNORECASE),
]

# Manual verification indicators
_MANUAL_PATTERNS = [
    re.compile(r"(?:visually|manually)\s+(?:verify|confirm|check|inspect)", re.IGNORECASE),
    re.compile(r"(?:looks?|appears?)\s+correct", re.IGNORECASE),
    re.compile(r"user\s+(?:can|should)\s+(?:see|observe|notice)", re.IGNORECASE),
    re.compile(r"(?:performance|latency|response\s+time)\s+(?:is|stays?|remains?)\s+(?:under|below|within)", re.IGNORECASE),
    re.compile(r"(?:ui|ux|design|layout)\s+(?:matches?|follows?|conforms?)", re.IGNORECASE),
]


def classify_criterion(text: str) -> ClassifiedCriterion:
    """Classify a single acceptance criterion.

    Uses pattern matching to determine whether the criterion is verifiable
    via file content analysis, command execution, or requires manual review.

    Parameters
    ----------
    text : str
        The acceptance criterion text (e.g., from task markdown).

    Returns
    -------
    ClassifiedCriterion
        The classified criterion with type, confidence, and extracted metadata.
    """
    # Strip markdown checkbox prefix if present
    cleaned = re.sub(r"^\s*-?\s*\[[ x]?\]\s*", "", text).strip()

    # Check command execution patterns first (higher priority)
    for pattern in _COMMAND_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            command = match.group(1) if match.lastindex else None
            return ClassifiedCriterion(
                text=text,
                criterion_type=CriterionType.COMMAND_EXECUTION,
                confidence=0.9,
                extracted_command=command,
                reason=f"Matches command pattern: {pattern.pattern[:60]}",
            )

    # Check file content patterns
    for pattern in _FILE_CONTENT_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            target = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1)
            return ClassifiedCriterion(
                text=text,
                criterion_type=CriterionType.FILE_CONTENT,
                confidence=0.85,
                target_file=target,
                reason=f"Matches file content pattern: {pattern.pattern[:60]}",
            )

    # Check manual patterns
    for pattern in _MANUAL_PATTERNS:
        if pattern.search(cleaned):
            return ClassifiedCriterion(
                text=text,
                criterion_type=CriterionType.MANUAL,
                confidence=0.8,
                reason=f"Matches manual pattern: {pattern.pattern[:60]}",
            )

    # Fallback heuristics for unmatched criteria
    # Check for backtick content that looks like a file path
    file_path_match = re.search(r"`([^`]+\.(?:py|ts|js|toml|json|yaml|yml|md|rs|go))`", cleaned)
    if file_path_match:
        return ClassifiedCriterion(
            text=text,
            criterion_type=CriterionType.FILE_CONTENT,
            confidence=0.6,
            target_file=file_path_match.group(1),
            reason="Contains file path reference (fallback)",
        )

    # Check for backtick content that looks like a command
    cmd_match = re.search(r"`([^`]{10,})`", cleaned)
    if cmd_match:
        content = cmd_match.group(1)
        # Heuristic: commands tend to have spaces and start with known binaries
        if " " in content and any(
            content.lower().startswith(prefix)
            for prefix in ("pip ", "npm ", "python ", "node ", "cargo ", "go ", "dotnet ", "make ", "docker ")
        ):
            return ClassifiedCriterion(
                text=text,
                criterion_type=CriterionType.COMMAND_EXECUTION,
                confidence=0.5,
                extracted_command=content,
                reason="Contains command-like backtick content (fallback)",
            )

    # Default: file_content with low confidence
    return ClassifiedCriterion(
        text=text,
        criterion_type=CriterionType.FILE_CONTENT,
        confidence=0.3,
        reason="No strong pattern match, defaulting to file_content",
    )


def classify_acceptance_criteria(criteria: List[str]) -> ClassificationResult:
    """Classify all acceptance criteria for a task.

    Parameters
    ----------
    criteria : List[str]
        List of acceptance criterion text strings.

    Returns
    -------
    ClassificationResult
        Aggregated classification with per-type accessors.
    """
    result = ClassificationResult()
    for text in criteria:
        if text.strip():
            result.criteria.append(classify_criterion(text))
    return result
