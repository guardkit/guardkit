"""
Security Review Module for AutoBuild Phase 2.5C.

This module provides security review capabilities that execute during pre-loop
(Phase 2.5C) and can be verified by Coach in read-only mode.

Architecture:
    Pre-loop (Player): Executes security review via SecurityReviewer
    -> Persists results to .guardkit/autobuild/{task_id}/security_review.json
    -> Coach reads persisted results (does NOT re-run checks)

Security Review Flow:
    1. TaskWorkInterface.execute_security_review() is called during Phase 2.5C
    2. SecurityReviewer.run() executes security checks via SecurityChecker
    3. Results are categorized by severity and blocking decision is made
    4. Results are persisted via save_security_review()
    5. Coach reads results via load_security_review() for verification

Example:
    >>> from guardkit.orchestrator.quality_gates.security_review import (
    ...     SecurityReviewer,
    ...     SecurityReviewResult,
    ...     save_security_review,
    ...     load_security_review,
    ... )
    >>> from guardkit.orchestrator.security_config import SecurityConfig
    >>>
    >>> config = SecurityConfig()
    >>> reviewer = SecurityReviewer("/path/to/worktree", config)
    >>> result = reviewer.run("TASK-001")
    >>>
    >>> # Persist result
    >>> save_security_review(result, Path("/path/to/worktree"))
    >>>
    >>> # Coach reads result (read-only)
    >>> loaded = load_security_review("TASK-001", Path("/path/to/worktree"))
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from guardkit.orchestrator.quality_gates.security_checker import (
    SecurityChecker,
    SecurityFinding,
)
from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class SecurityReviewResult:
    """
    Result from security review execution.

    This dataclass contains all outputs from a security review, including
    findings categorized by severity and the blocking decision.

    Attributes
    ----------
    task_id : str
        Task identifier (e.g., "TASK-001")
    worktree_path : str
        Path to the worktree that was reviewed
    findings : List[SecurityFinding]
        List of security findings from the review
    critical_count : int
        Number of critical severity findings
    high_count : int
        Number of high severity findings
    medium_count : int
        Number of medium severity findings
    low_count : int
        Number of low severity findings
    blocked : bool
        Whether the task should be blocked based on findings
    execution_time_seconds : float
        Time taken to execute the security review
    timestamp : str
        ISO format timestamp of when the review was executed

    Example
    -------
    >>> result = SecurityReviewResult(
    ...     task_id="TASK-001",
    ...     worktree_path="/path/to/worktree",
    ...     findings=[],
    ...     critical_count=0,
    ...     high_count=0,
    ...     medium_count=0,
    ...     low_count=0,
    ...     blocked=False,
    ...     execution_time_seconds=1.5,
    ...     timestamp="2025-01-25T12:00:00Z",
    ... )
    """

    task_id: str
    worktree_path: str
    findings: List[SecurityFinding]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    blocked: bool
    execution_time_seconds: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for JSON serialization.

        Returns
        -------
        Dict[str, Any]
            Dictionary representation suitable for JSON serialization

        Example
        -------
        >>> result_dict = result.to_dict()
        >>> json.dumps(result_dict)  # Can be serialized to JSON
        """
        return {
            "task_id": self.task_id,
            "worktree_path": self.worktree_path,
            "findings": [
                {
                    "check_id": f.check_id,
                    "severity": f.severity,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "matched_text": f.matched_text,
                    "recommendation": f.recommendation,
                }
                for f in self.findings
            ],
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "blocked": self.blocked,
            "execution_time_seconds": self.execution_time_seconds,
            "timestamp": self.timestamp,
        }


# ============================================================================
# SecurityReviewer Class
# ============================================================================


class SecurityReviewer:
    """
    Orchestrates security checks for AutoBuild Phase 2.5C.

    This class wraps SecurityChecker to provide a high-level security review
    interface that categorizes findings by severity and makes blocking decisions
    based on SecurityConfig settings.

    Blocking Logic:
        - STRICT level: Block on any finding
        - STANDARD level: Block on critical findings (if block_on_critical=True)
        - MINIMAL level: Never block (warnings only)
        - SKIP level: Skip all checks, never block

    Attributes
    ----------
    worktree_path : Path
        Path to the worktree to review
    config : SecurityConfig
        Security configuration controlling behavior

    Example
    -------
    >>> from guardkit.orchestrator.security_config import SecurityConfig
    >>> config = SecurityConfig()
    >>> reviewer = SecurityReviewer("/path/to/worktree", config)
    >>> result = reviewer.run("TASK-001")
    >>> print(f"Critical: {result.critical_count}, Blocked: {result.blocked}")
    """

    def __init__(
        self,
        worktree_path: Union[str, Path],
        config: SecurityConfig,
    ):
        """
        Initialize SecurityReviewer.

        Parameters
        ----------
        worktree_path : Union[str, Path]
            Path to the worktree to review
        config : SecurityConfig
            Security configuration controlling behavior
        """
        self.worktree_path = Path(worktree_path)
        self.config = config
        logger.debug(
            f"SecurityReviewer initialized for: {worktree_path}, "
            f"level: {config.level.value}"
        )

    def run(self, task_id: str) -> SecurityReviewResult:
        """
        Execute security review and return categorized results.

        Runs SecurityChecker on the worktree, categorizes findings by severity,
        and determines whether the task should be blocked based on config.

        Parameters
        ----------
        task_id : str
            Task identifier for this review

        Returns
        -------
        SecurityReviewResult
            Complete result with findings and blocking decision

        Example
        -------
        >>> result = reviewer.run("TASK-001")
        >>> if result.blocked:
        ...     print(f"Task blocked: {result.critical_count} critical findings")
        """
        logger.info(f"Starting security review for {task_id}")
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Handle SKIP level - no checks, no blocking
        if self.config.level == SecurityLevel.SKIP:
            logger.info(f"Security review skipped for {task_id} (level=SKIP)")
            return SecurityReviewResult(
                task_id=task_id,
                worktree_path=str(self.worktree_path),
                findings=[],
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                blocked=False,
                execution_time_seconds=time.time() - start_time,
                timestamp=timestamp,
            )

        # Run security checks
        findings: List[SecurityFinding] = []
        if self.worktree_path.exists():
            try:
                checker = SecurityChecker(self.worktree_path)
                findings = checker.run_quick_checks()
            except Exception as e:
                logger.error(f"Security check failed: {e}")
                # Return empty result on error
                findings = []

        # Categorize findings by severity
        critical_count = sum(1 for f in findings if f.severity == "critical")
        high_count = sum(1 for f in findings if f.severity == "high")
        medium_count = sum(1 for f in findings if f.severity == "medium")
        low_count = sum(1 for f in findings if f.severity == "low")

        # Determine blocking status based on config
        blocked = self._should_block(
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
        )

        execution_time = time.time() - start_time

        logger.info(
            f"Security review complete for {task_id}: "
            f"critical={critical_count}, high={high_count}, "
            f"blocked={blocked}, time={execution_time:.2f}s"
        )

        return SecurityReviewResult(
            task_id=task_id,
            worktree_path=str(self.worktree_path),
            findings=findings,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            blocked=blocked,
            execution_time_seconds=execution_time,
            timestamp=timestamp,
        )

    def _should_block(
        self,
        critical_count: int,
        high_count: int,
        medium_count: int,
        low_count: int,
    ) -> bool:
        """
        Determine if task should be blocked based on findings and config.

        Blocking Logic:
            - STRICT: Block on any finding (critical, high, medium, or low)
            - STANDARD: Block on critical if block_on_critical=True
            - MINIMAL: Never block
            - SKIP: Never block (handled before this method)

        Parameters
        ----------
        critical_count : int
            Number of critical findings
        high_count : int
            Number of high findings
        medium_count : int
            Number of medium findings
        low_count : int
            Number of low findings

        Returns
        -------
        bool
            True if task should be blocked
        """
        # MINIMAL level never blocks
        if self.config.level == SecurityLevel.MINIMAL:
            return False

        # STRICT level blocks on any finding
        if self.config.level == SecurityLevel.STRICT:
            total = critical_count + high_count + medium_count + low_count
            return total > 0

        # STANDARD level: block on critical if configured
        if self.config.level == SecurityLevel.STANDARD:
            if self.config.block_on_critical and critical_count > 0:
                return True
            return False

        # Default: don't block
        return False


# ============================================================================
# Persistence Functions
# ============================================================================


def save_security_review(
    result: SecurityReviewResult,
    worktree_path: Union[str, Path],
) -> Path:
    """
    Save security review result to JSON file.

    Saves to: .guardkit/autobuild/{task_id}/security_review.json

    Parameters
    ----------
    result : SecurityReviewResult
        The security review result to save
    worktree_path : Union[str, Path]
        Path to the worktree root

    Returns
    -------
    Path
        Path to the saved JSON file

    Example
    -------
    >>> path = save_security_review(result, Path("/path/to/worktree"))
    >>> print(f"Saved to: {path}")
    """
    from guardkit.orchestrator.paths import TaskArtifactPaths

    worktree = Path(worktree_path)

    # Ensure directory exists
    TaskArtifactPaths.ensure_autobuild_dir(result.task_id, worktree)

    # Get the path for security review file
    review_path = TaskArtifactPaths.security_review_path(result.task_id, worktree)

    # Write JSON
    with open(review_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Saved security review to {review_path}")
    return review_path


def load_security_review(
    task_id: str,
    worktree_path: Union[str, Path],
) -> Optional[SecurityReviewResult]:
    """
    Load security review result from JSON file.

    Loads from: .guardkit/autobuild/{task_id}/security_review.json

    Parameters
    ----------
    task_id : str
        Task identifier
    worktree_path : Union[str, Path]
        Path to the worktree root

    Returns
    -------
    Optional[SecurityReviewResult]
        Loaded result, or None if file not found or corrupted

    Example
    -------
    >>> result = load_security_review("TASK-001", Path("/path/to/worktree"))
    >>> if result:
    ...     print(f"Critical: {result.critical_count}")
    """
    from guardkit.orchestrator.paths import TaskArtifactPaths

    worktree = Path(worktree_path)
    review_path = TaskArtifactPaths.security_review_path(task_id, worktree)

    if not review_path.exists():
        logger.debug(f"Security review file not found: {review_path}")
        return None

    try:
        with open(review_path) as f:
            data = json.load(f)

        # Reconstruct SecurityFinding objects
        findings = [
            SecurityFinding(
                check_id=f["check_id"],
                severity=f["severity"],
                description=f["description"],
                file_path=f["file_path"],
                line_number=f["line_number"],
                matched_text=f["matched_text"],
                recommendation=f["recommendation"],
            )
            for f in data.get("findings", [])
        ]

        return SecurityReviewResult(
            task_id=data["task_id"],
            worktree_path=data["worktree_path"],
            findings=findings,
            critical_count=data["critical_count"],
            high_count=data["high_count"],
            medium_count=data["medium_count"],
            low_count=data["low_count"],
            blocked=data["blocked"],
            execution_time_seconds=data["execution_time_seconds"],
            timestamp=data["timestamp"],
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse security review JSON: {e}")
        return None
    except KeyError as e:
        logger.error(f"Missing key in security review JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load security review: {e}")
        return None


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "SecurityReviewResult",
    "SecurityReviewer",
    "save_security_review",
    "load_security_review",
]
