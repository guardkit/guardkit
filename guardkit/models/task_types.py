"""Task type definitions and quality gate profiles.

Provides task type classification and associated quality gate configurations
for different task categories (scaffolding, feature, infrastructure, documentation).

This module defines:
- TaskType: Enum for task classification
- QualityGateProfile: Dataclass for quality gate configuration per task type
- DEFAULT_PROFILES: Registry of default profiles for each task type
- get_profile(): Function for profile registry lookup

The quality gate profiles determine which validation checks are required
for each task type during the task workflow execution.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional


class TaskType(Enum):
    """Task type classification for quality gate profiles.

    Different task types require different validation approaches:
    - SCAFFOLDING: Configuration and boilerplate tasks (no architecture review needed)
    - FEATURE: Primary implementation tasks (full quality gates)
    - INFRASTRUCTURE: DevOps and deployment tasks (tests required, no architecture review)
    - DOCUMENTATION: Documentation and guides (minimal validation)
    - TESTING: Test creation, test refactoring, coverage improvements (minimal validation)
    - REFACTOR: Code improvements, performance optimization, pattern implementation

    Attributes:
        SCAFFOLDING: Configuration files, project setup, templates
        FEATURE: Feature implementation, bug fixes, enhancements
        INFRASTRUCTURE: Docker, deployment, CI/CD, terraform, ansible
        DOCUMENTATION: Guides, API docs, tutorials, README files
        TESTING: Test files, test utilities, coverage improvements
        REFACTOR: Code cleanup, performance optimization, pattern refactoring
    """

    SCAFFOLDING = "scaffolding"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTOR = "refactor"


@dataclass
class QualityGateProfile:
    """Quality gate configuration for a task type.

    Defines which quality gates are enforced and their thresholds for a specific
    task type. This allows different validation rules for different task categories.

    Attributes:
        arch_review_required: Whether architectural review (Phase 2.5) is required.
            Recommended for: FEATURE tasks
            Skipped for: SCAFFOLDING, INFRASTRUCTURE, DOCUMENTATION
        arch_review_threshold: Minimum architectural review score (0-100).
            Default for features: 60
            Ignored if arch_review_required is False
        coverage_required: Whether code coverage validation is required.
            Recommended for: FEATURE tasks with testable code
            Skipped for: SCAFFOLDING, INFRASTRUCTURE, DOCUMENTATION
        coverage_threshold: Minimum line coverage percentage (0-100).
            Default for features: 80
            Ignored if coverage_required is False
        tests_required: Whether test execution is required.
            Required for: FEATURE, INFRASTRUCTURE
            Optional for: SCAFFOLDING (e.g., validation scripts)
            Skipped for: DOCUMENTATION
        plan_audit_required: Whether plan audit (Phase 5.5) is required.
            Scope creep detection and implementation completeness check.
            Required for: FEATURE, INFRASTRUCTURE, SCAFFOLDING
            Skipped for: DOCUMENTATION
        zero_test_blocking: Whether zero-test anomaly blocks approval (default: False).
            When True and tests_required is True, a zero-test anomaly returns
            an error that blocks Coach approval instead of a warning.
            Enabled for: FEATURE, REFACTOR
            Disabled for: SCAFFOLDING, INFRASTRUCTURE, DOCUMENTATION, TESTING

    Example:
        Feature task profile (maximum validation):
        >>> feature_profile = QualityGateProfile(
        ...     arch_review_required=True,
        ...     arch_review_threshold=60,
        ...     coverage_required=True,
        ...     coverage_threshold=80,
        ...     tests_required=True,
        ...     plan_audit_required=True,
        ... )

        Documentation task profile (minimal validation):
        >>> doc_profile = QualityGateProfile(
        ...     arch_review_required=False,
        ...     arch_review_threshold=0,
        ...     coverage_required=False,
        ...     coverage_threshold=0,
        ...     tests_required=False,
        ...     plan_audit_required=False,
        ... )
    """

    arch_review_required: bool
    arch_review_threshold: int
    coverage_required: bool
    coverage_threshold: float
    tests_required: bool
    plan_audit_required: bool
    zero_test_blocking: bool = False

    def __post_init__(self) -> None:
        """Validate quality gate profile configuration.

        Ensures that thresholds are valid and required constraints are met.

        Raises:
            ValueError: If arch_review_threshold is outside 0-100 range or
                       if coverage_threshold is outside 0-100 range, or
                       if thresholds are set when corresponding gate is not required.
        """
        # Validate arch_review_threshold
        if not (0 <= self.arch_review_threshold <= 100):
            raise ValueError(
                f"arch_review_threshold must be 0-100, got {self.arch_review_threshold}"
            )

        if not self.arch_review_required and self.arch_review_threshold > 0:
            raise ValueError(
                "arch_review_threshold should be 0 when arch_review_required is False"
            )

        # Validate coverage_threshold
        if not (0 <= self.coverage_threshold <= 100):
            raise ValueError(
                f"coverage_threshold must be 0-100, got {self.coverage_threshold}"
            )

        if not self.coverage_required and self.coverage_threshold > 0:
            raise ValueError(
                "coverage_threshold should be 0 when coverage_required is False"
            )

    @classmethod
    def for_type(cls, task_type: TaskType) -> "QualityGateProfile":
        """Get the default profile for a task type.

        Convenience method to retrieve the default quality gate profile
        from the DEFAULT_PROFILES registry for a given task type.

        Args:
            task_type: The TaskType to get the profile for.

        Returns:
            QualityGateProfile: The default profile for the given task type.

        Raises:
            KeyError: If task_type is not in DEFAULT_PROFILES (should not occur
                     if DEFAULT_PROFILES contains all TaskType values).

        Example:
            >>> feature_profile = QualityGateProfile.for_type(TaskType.FEATURE)
            >>> feature_profile.arch_review_required
            True
            >>> doc_profile = QualityGateProfile.for_type(TaskType.DOCUMENTATION)
            >>> doc_profile.tests_required
            False
        """
        return DEFAULT_PROFILES[task_type]


# Default profiles per task type
DEFAULT_PROFILES: Dict[TaskType, QualityGateProfile] = {
    TaskType.SCAFFOLDING: QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0.0,
        tests_required=False,  # Optional - may include validation scripts
        plan_audit_required=True,  # Ensure configuration is complete
    ),
    TaskType.FEATURE: QualityGateProfile(
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=80.0,
        tests_required=True,
        plan_audit_required=True,
        zero_test_blocking=True,
    ),
    TaskType.INFRASTRUCTURE: QualityGateProfile(
        arch_review_required=False,  # Infrastructure design is different paradigm
        arch_review_threshold=0,
        coverage_required=False,  # Infrastructure code coverage less meaningful
        coverage_threshold=0.0,
        tests_required=True,  # Deployment must be tested
        plan_audit_required=True,  # Ensure deployment is complete
    ),
    TaskType.DOCUMENTATION: QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0.0,
        tests_required=False,
        plan_audit_required=False,
    ),
    TaskType.TESTING: QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0.0,
        tests_required=False,
        plan_audit_required=True,
    ),
    TaskType.REFACTOR: QualityGateProfile(
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=80.0,
        tests_required=True,
        plan_audit_required=True,
        zero_test_blocking=True,
    ),
}


def get_profile(
    task_type: Optional[TaskType] = None,
) -> QualityGateProfile:
    """Get quality gate profile for a task type, with backward compatibility.

    Convenience function for profile registry lookup. Provides backward compatibility
    by defaulting to FEATURE profile when task_type is None or not provided, ensuring
    existing tasks without an explicit task_type field continue to use the original
    strict quality gates.

    Args:
        task_type: The TaskType to get the profile for, or None for default.
                  If None, returns the FEATURE profile (default behavior).

    Returns:
        QualityGateProfile: The quality gate profile for the task type.
                          If task_type is None, returns the FEATURE profile.

    Raises:
        KeyError: If task_type is provided but not in DEFAULT_PROFILES (should not
                 occur if DEFAULT_PROFILES contains all TaskType values).

    Example:
        Backward compatible usage (task_type not specified):
        >>> profile = get_profile()  # Returns FEATURE profile
        >>> profile.arch_review_required
        True

        Explicit task type:
        >>> scaffolding_profile = get_profile(TaskType.SCAFFOLDING)
        >>> scaffolding_profile.arch_review_required
        False

        None explicitly passed (same as default):
        >>> profile = get_profile(None)  # Returns FEATURE profile
    """
    if task_type is None:
        # Default to FEATURE profile for backward compatibility
        return DEFAULT_PROFILES[TaskType.FEATURE]
    return DEFAULT_PROFILES[task_type]
