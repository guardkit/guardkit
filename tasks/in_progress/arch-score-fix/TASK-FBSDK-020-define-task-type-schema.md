---
id: TASK-FBSDK-020
title: Define task type schema and quality gate profiles
status: in_progress
created: 2025-01-21T16:30:00Z
updated: 2025-01-22T18:45:00Z
priority: high
tags: [autobuild, quality-gates, task-types, schema]
parent_review: TASK-REV-FB19
feature_id: FEAT-ARCH-SCORE-FIX
implementation_mode: task-work
wave: 2
conductor_workspace: arch-score-fix-wave2-1
complexity: 4
depends_on: [TASK-FBSDK-018, TASK-FBSDK-019]
---

# Task: Define task type schema and quality gate profiles

## Description

Create a formal schema for task types and their associated quality gate profiles. Different task types (scaffolding, feature, infrastructure, documentation) require different validation approaches.

## Problem

Currently all tasks are treated uniformly with the same quality gates:
- Architectural review (≥60)
- Coverage (≥80%)
- All tests passing
- Plan audit (0 violations)

This is inappropriate for scaffolding tasks that produce configuration files (no code to review architecturally) or documentation tasks (no tests expected).

## Acceptance Criteria

- [x] TaskType enum defined with 4 types: scaffolding, feature, infrastructure, documentation
- [x] QualityGateProfile dataclass with configurable gates per type
- [x] Default profiles defined matching the decision matrix
- [x] Schema supports custom profiles via configuration (get_profile() function)
- [x] Unit tests verify profile application (46 tests, 100% coverage)
- [x] Documentation updated with task type descriptions (comprehensive docstrings)

## Implementation Notes

### New File: `guardkit/models/task_types.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TaskType(Enum):
    """Task type classification for quality gate profiles."""
    SCAFFOLDING = "scaffolding"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"

@dataclass
class QualityGateProfile:
    """Quality gate configuration for a task type."""
    arch_review_required: bool
    arch_review_threshold: int
    coverage_required: bool
    coverage_threshold: float
    tests_required: bool
    plan_audit_required: bool

    @classmethod
    def for_type(cls, task_type: TaskType) -> "QualityGateProfile":
        """Get the default profile for a task type."""
        return DEFAULT_PROFILES[task_type]

# Default profiles per task type
DEFAULT_PROFILES = {
    TaskType.SCAFFOLDING: QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0,
        tests_required=False,  # Optional
        plan_audit_required=True,
    ),
    TaskType.FEATURE: QualityGateProfile(
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=80,
        tests_required=True,
        plan_audit_required=True,
    ),
    TaskType.INFRASTRUCTURE: QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0,
        tests_required=True,
        plan_audit_required=True,
    ),
    TaskType.DOCUMENTATION: QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0,
        tests_required=False,
        plan_audit_required=False,
    ),
}
```

### Task Frontmatter Extension

```yaml
---
id: TASK-XXX
title: Setup project structure
task_type: scaffolding  # NEW FIELD
# ...
---
```

### Quality Gate Profile Matrix

| Task Type | Arch Review | Coverage | Tests | Plan Audit |
|-----------|-------------|----------|-------|------------|
| scaffolding | Skip | Skip | Optional | Required |
| feature (default) | ≥60 | ≥80% | Required | Required |
| infrastructure | Skip | Skip | Required | Required |
| documentation | Skip | Skip | Skip | Skip |

## Related Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` (will use profiles in TASK-FBSDK-021)
- `installer/core/commands/feature-plan.md` (will auto-detect in TASK-FBSDK-022)
- Task file frontmatter schema

## Implementation Summary

Successfully implemented task type schema and quality gate profiles:

### Files Created
- `guardkit/models/__init__.py` - Package init with clean exports
- `guardkit/models/task_types.py` - Core implementation (189 lines, well-documented)
- `tests/unit/test_task_types.py` - Comprehensive test suite (46 tests, 100% coverage)

### Key Components

1. **TaskType Enum** (4 values)
   - SCAFFOLDING: Configuration and boilerplate
   - FEATURE: Primary implementation tasks
   - INFRASTRUCTURE: DevOps and deployment
   - DOCUMENTATION: Guides and API docs

2. **QualityGateProfile Dataclass**
   - Configurable gates per task type
   - Built-in validation via __post_init__
   - Ensures threshold consistency
   - for_type() class method for registry lookup

3. **DEFAULT_PROFILES Registry**
   - Four profiles matching decision matrix
   - All fields initialized explicitly
   - Enforces quality standards per task type

4. **get_profile() Function**
   - Profile lookup with backward compatibility
   - Returns FEATURE profile by default
   - Handles None gracefully for missing task_type field

### Quality Metrics
- Test Count: 46 tests
- Line Coverage: 100%
- Branch Coverage: 100%
- All acceptance criteria met

### Architecture Alignment
- Uses dataclass (not Pydantic) per architectural review
- Maintains simplicity (YAGNI principle)
- Error handling via validation in __post_init__
- Production-ready code quality

## Notes

This is a foundational task that defines the schema. TASK-FBSDK-021 and TASK-FBSDK-022 depend on this schema being complete before they can implement the consumers.

Implementation complete and ready for:
- TASK-FBSDK-021: Integrate profiles into coach_validator.py
- TASK-FBSDK-022: Auto-detect task types in /feature-plan command
