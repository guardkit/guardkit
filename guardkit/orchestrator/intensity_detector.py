"""Intensity level auto-detection for task-work command.

This module provides pure functions for automatically determining the appropriate
intensity level (MINIMAL, LIGHT, STANDARD, STRICT) for a task based on:

- Provenance (parent_review, feature_id)
- Complexity score (1-10 scale)
- High-risk keywords (security, breaking, API, schema, etc.)

The detection algorithm implements a tiered approach:
1. High-risk keywords always force STRICT mode
2. Provenance-based detection (tasks from reviews/features get lighter intensity)
3. Complexity-based detection for fresh tasks
4. Optional user override via --intensity flag

Architecture:
    - Pure stateless functions (no side effects)
    - Dict-based input (no Pydantic coupling)
    - Enum-based type safety
    - Module-level constants for easy maintenance

Example:
    >>> from guardkit.orchestrator.intensity_detector import determine_intensity
    >>>
    >>> task_data = {
    ...     "task_id": "TASK-001",
    ...     "description": "Add user authentication",
    ...     "complexity": 5,
    ...     "parent_review": None,
    ...     "feature_id": None,
    ... }
    >>> intensity = determine_intensity(task_data)
    >>> print(intensity)  # IntensityLevel.LIGHT
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# High-risk keywords that force STRICT mode (module-level constant)
HIGH_RISK_KEYWORDS = [
    "security",
    "auth",
    "authentication",
    "authorization",
    "breaking",
    "breaking change",
    "schema",
    "migration",
    "database",
    "api",
    "endpoint",
    "financial",
    "payment",
    "billing",
    "encryption",
    "crypto",
    "cryptographic",
    "oauth",
    "saml",
    "jwt",
    "session",
    "privilege",
    "permission",
    "access control",
    "injection",
    "xss",
    "csrf",
]


class IntensityLevel(Enum):
    """Intensity levels for task-work execution.

    Attributes:
        MINIMAL: Fastest execution, minimal phases (~3-5 min)
        LIGHT: Fast execution with brief planning (~10-15 min)
        STANDARD: Full workflow with smart decisions (~15-30 min)
        STRICT: Maximum rigor, all phases with blocking checkpoints (~30-60+ min)
    """

    MINIMAL = "minimal"
    LIGHT = "light"
    STANDARD = "standard"
    STRICT = "strict"


def determine_intensity(
    task_data: Dict[str, Any],
    override: Optional[str] = None,
) -> IntensityLevel:
    """Determine intensity level for a task based on provenance and complexity.

    Detection algorithm (in priority order):
    1. User override (if provided via --intensity flag)
    2. High-risk keywords → STRICT
    3. Provenance (parent_review) → MINIMAL/LIGHT based on complexity
    4. Provenance (feature_id) → MINIMAL/LIGHT/STANDARD based on complexity
    5. Fresh task → complexity-based detection

    Args:
        task_data: Task dictionary with keys:
            - description (str): Task description text
            - complexity (int): Complexity score (1-10)
            - parent_review (Optional[str]): Parent review task ID if from review
            - feature_id (Optional[str]): Feature ID if part of feature
        override: Optional intensity override from --intensity flag

    Returns:
        IntensityLevel enum value

    Raises:
        No exceptions - handles missing/invalid data gracefully with defaults

    Example:
        >>> # High-risk keyword forces STRICT
        >>> task = {"description": "Add OAuth authentication", "complexity": 4}
        >>> determine_intensity(task)
        IntensityLevel.STRICT

        >>> # Task from review gets lighter intensity
        >>> task = {"description": "Fix typo", "complexity": 3, "parent_review": "TASK-042"}
        >>> determine_intensity(task)
        IntensityLevel.MINIMAL

        >>> # User override takes precedence
        >>> task = {"description": "Add feature", "complexity": 5}
        >>> determine_intensity(task, override="strict")
        IntensityLevel.STRICT
    """
    # 1. User override takes precedence
    if override:
        try:
            return IntensityLevel(override.lower())
        except ValueError:
            logger.warning(
                f"Invalid intensity override '{override}', falling back to auto-detection"
            )

    # Extract fields with safe defaults
    description = task_data.get("description", "")
    complexity = task_data.get("complexity", 5)  # Default to medium complexity
    parent_review = task_data.get("parent_review")
    feature_id = task_data.get("feature_id")

    # 2. High-risk keywords always force STRICT
    if _has_high_risk_keywords(description):
        logger.info(
            f"High-risk keywords detected in description, forcing STRICT intensity"
        )
        return IntensityLevel.STRICT

    # 3. Check provenance (parent_review)
    if parent_review:
        intensity = _detect_from_parent_review(complexity)
        logger.info(
            f"Task from review (parent_review={parent_review}), "
            f"complexity={complexity} → {intensity.value}"
        )
        return intensity

    # 4. Check provenance (feature_id)
    if feature_id:
        intensity = _detect_from_feature(complexity)
        logger.info(
            f"Task from feature (feature_id={feature_id}), "
            f"complexity={complexity} → {intensity.value}"
        )
        return intensity

    # 5. Fresh task - complexity-based detection
    intensity = _detect_from_complexity(complexity)
    logger.info(
        f"Fresh task with complexity={complexity} → {intensity.value}"
    )
    return intensity


def _has_high_risk_keywords(description: str) -> bool:
    """Check if description contains high-risk keywords.

    Args:
        description: Task description text

    Returns:
        True if any high-risk keyword found (case-insensitive)

    Example:
        >>> _has_high_risk_keywords("Add OAuth authentication")
        True
        >>> _has_high_risk_keywords("Fix typo in README")
        False
    """
    description_lower = description.lower()
    return any(keyword in description_lower for keyword in HIGH_RISK_KEYWORDS)


def _detect_from_parent_review(complexity: int) -> IntensityLevel:
    """Detect intensity for tasks created from review recommendations.

    Tasks from reviews are typically well-scoped and can use lighter intensity.

    Args:
        complexity: Complexity score (1-10)

    Returns:
        MINIMAL for complexity ≤4, LIGHT for complexity >4

    Example:
        >>> _detect_from_parent_review(3)
        IntensityLevel.MINIMAL
        >>> _detect_from_parent_review(6)
        IntensityLevel.LIGHT
    """
    if complexity <= 4:
        return IntensityLevel.MINIMAL
    else:
        return IntensityLevel.LIGHT


def _detect_from_feature(complexity: int) -> IntensityLevel:
    """Detect intensity for tasks that are part of a feature.

    Feature subtasks benefit from feature-level planning and can use lighter intensity.

    Args:
        complexity: Complexity score (1-10)

    Returns:
        MINIMAL for complexity ≤3, LIGHT for ≤5, STANDARD for >5

    Example:
        >>> _detect_from_feature(2)
        IntensityLevel.MINIMAL
        >>> _detect_from_feature(5)
        IntensityLevel.LIGHT
        >>> _detect_from_feature(7)
        IntensityLevel.STANDARD
    """
    if complexity <= 3:
        return IntensityLevel.MINIMAL
    elif complexity <= 5:
        return IntensityLevel.LIGHT
    else:
        return IntensityLevel.STANDARD


def _detect_from_complexity(complexity: int) -> IntensityLevel:
    """Detect intensity for fresh tasks based on complexity alone.

    Fresh tasks need more rigor than provenance-based tasks.

    Args:
        complexity: Complexity score (1-10)

    Returns:
        MINIMAL for ≤3, LIGHT for ≤5, STANDARD for ≤6, STRICT for >6

    Example:
        >>> _detect_from_complexity(2)
        IntensityLevel.MINIMAL
        >>> _detect_from_complexity(5)
        IntensityLevel.LIGHT
        >>> _detect_from_complexity(6)
        IntensityLevel.STANDARD
        >>> _detect_from_complexity(8)
        IntensityLevel.STRICT
    """
    if complexity <= 3:
        return IntensityLevel.MINIMAL
    elif complexity <= 5:
        return IntensityLevel.LIGHT
    elif complexity <= 6:
        return IntensityLevel.STANDARD
    else:
        return IntensityLevel.STRICT


__all__ = [
    "IntensityLevel",
    "determine_intensity",
    "HIGH_RISK_KEYWORDS",
]
