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

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task type classification for quality gate profiles.

    Different task types require different validation approaches:
    - SCAFFOLDING: Configuration and boilerplate tasks (no architecture review needed)
    - FEATURE: Primary implementation tasks (full quality gates)
    - INFRASTRUCTURE: DevOps and deployment tasks (tests required, no architecture review)
    - INTEGRATION: Wiring and integration tasks (tests desirable but not blocking)
    - DOCUMENTATION: Documentation and guides (minimal validation)
    - TESTING: Test creation, test refactoring, coverage improvements (minimal validation)
    - REFACTOR: Code improvements, performance optimization, pattern implementation
    - GLUE / WIRING: Hand-written glue that binds factory-generated components at
        declared seams (composition-root registration, DI wiring, route/handler
        binding, BDD step definitions, adapter shims). The highest-risk task class
        (DF-016 clause 5): strictest evidence posture, no gate relaxation.
    - OPERATOR_HANDOFF: Tasks that hand off to a human operator (every gate disabled)

    Attributes:
        SCAFFOLDING: Configuration files, project setup, templates
        FEATURE: Feature implementation, bug fixes, enhancements
        INFRASTRUCTURE: Docker, deployment, CI/CD, terraform, ansible
        INTEGRATION: Wiring endpoints, connecting services, hooking up middleware
        DOCUMENTATION: Guides, API docs, tutorials, README files
        TESTING: Test files, test utilities, coverage improvements
        REFACTOR: Code cleanup, performance optimization, pattern refactoring
        DECLARATIVE: Pydantic models, DTOs, Settings classes, constants, app init
        GLUE: Hand-written glue at a declared seam — the DF-016 §6(a) glue-authoring
            class. Distinct from INTEGRATION: where INTEGRATION relaxes gates
            (that relaxation is what let glue escapes through — POC-006, SMP-002),
            GLUE is the *strictest* posture so the Coach treats glue adversarially
            as production code. The value the /feature-plan emitter assigns
            (DF-016 clause 5 keys the Coach posture mechanically off this class).
        WIRING: Co-equal spelling of the GLUE class named in DF-016 §6(a)
            ("a `glue`/`wiring` task class"); carries the identical strict profile.
        OPERATOR_HANDOFF: Tasks the orchestrator must skip and route to a human
            operator (e.g. external configuration, registry edits, manual
            credential rotation). Every quality gate is disabled so the
            orchestrator has a deterministic signal to skip the task entirely
            rather than try to autonomously implement it.
    """

    SCAFFOLDING = "scaffolding"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    INTEGRATION = "integration"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTOR = "refactor"
    DECLARATIVE = "declarative"
    # DF-016 §6(a): explicit glue-authoring class so the clause-5 Coach posture
    # keys mechanically, never inferred. GLUE is the /feature-plan emitter's
    # cutover target (FEAT-DF12 DFEM-013); WIRING is the co-equal DF-016 spelling.
    GLUE = "glue"
    WIRING = "wiring"
    OPERATOR_HANDOFF = "operator_handoff"


@dataclass
class QualityGateProfile:
    """What a task type asks of the build.

    Attributes:
        tests_required: Whether the project's tests are run for this task type
            and a run that fails sends the turn back. False for SCAFFOLDING,
            DOCUMENTATION and OPERATOR_HANDOFF.

    (27 October 2026: the architecture-review, coverage, plan-audit,
    zero-test and seam-test settings went with the checks they configured.)
    """

    tests_required: bool

    @classmethod
    def for_type(cls, task_type: TaskType) -> "QualityGateProfile":
        """The default profile for a task type."""
        return DEFAULT_PROFILES[task_type]


# Default profiles per task type
DEFAULT_PROFILES: Dict[TaskType, QualityGateProfile] = {
    TaskType.SCAFFOLDING: QualityGateProfile(tests_required=False),
    TaskType.FEATURE: QualityGateProfile(tests_required=True),
    TaskType.INFRASTRUCTURE: QualityGateProfile(tests_required=True),
    TaskType.INTEGRATION: QualityGateProfile(tests_required=True),
    TaskType.DOCUMENTATION: QualityGateProfile(tests_required=False),
    # TASK-ABFIX-012: a TESTING task's deliverable IS passing tests.
    TaskType.TESTING: QualityGateProfile(tests_required=True),
    TaskType.REFACTOR: QualityGateProfile(tests_required=True),
    TaskType.DECLARATIVE: QualityGateProfile(tests_required=True),
    TaskType.GLUE: QualityGateProfile(tests_required=True),
    TaskType.WIRING: QualityGateProfile(tests_required=True),
    # The orchestrator skips the task entirely.
    TaskType.OPERATOR_HANDOFF: QualityGateProfile(tests_required=False),
}


# Canonical alias table for legacy task_type values.
# Canonical location: guardkit/models/task_types.py
# Also referenced from coach_validator for backward compatibility.
TASK_TYPE_ALIASES: Dict[str, TaskType] = {
    "implementation": TaskType.FEATURE,
    "bug-fix": TaskType.FEATURE,
    "bug_fix": TaskType.FEATURE,
    "benchmark": TaskType.TESTING,
    "research": TaskType.DOCUMENTATION,
    "enhancement": TaskType.FEATURE,
    "config": TaskType.DECLARATIVE,
    "dto": TaskType.DECLARATIVE,
}

# Combined set of all valid task_type strings (enum values + aliases)
VALID_TASK_TYPES: Set[str] = {t.value for t in TaskType} | set(TASK_TYPE_ALIASES.keys())


def normalise_task_type(raw_type: str) -> str:
    """Normalise a task_type string to its canonical enum value.

    Resolves aliases (e.g. 'enhancement' -> 'feature') and falls back
    to 'feature' with a warning for unknown values.

    Args:
        raw_type: Raw task type string, possibly an alias or unknown value.

    Returns:
        Canonical task type string from TaskType enum values.
    """
    # Already canonical?
    try:
        return TaskType(raw_type).value
    except ValueError:
        pass
    # Known alias?
    if raw_type in TASK_TYPE_ALIASES:
        logger.info("Normalised task_type '%s' -> '%s'", raw_type, TASK_TYPE_ALIASES[raw_type].value)
        return TASK_TYPE_ALIASES[raw_type].value
    # Unknown - default to feature with warning
    logger.warning("Unknown task_type '%s', defaulting to 'feature'", raw_type)
    return TaskType.FEATURE.value


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
        >>> profile.tests_required
        True

        Explicit task type:
        >>> scaffolding_profile = get_profile(TaskType.SCAFFOLDING)
        >>> scaffolding_profile.tests_required
        False

        None explicitly passed (same as default):
        >>> profile = get_profile(None)  # Returns FEATURE profile
    """
    if task_type is None:
        # Default to FEATURE profile for backward compatibility
        return DEFAULT_PROFILES[TaskType.FEATURE]
    return DEFAULT_PROFILES[task_type]
