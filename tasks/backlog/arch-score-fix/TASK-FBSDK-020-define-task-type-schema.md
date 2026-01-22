---
id: TASK-FBSDK-020
title: Define task type schema and quality gate profiles
status: backlog
created: 2025-01-21T16:30:00Z
updated: 2025-01-21T16:30:00Z
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

- [ ] TaskType enum defined with 4 types: scaffolding, feature, infrastructure, documentation
- [ ] QualityGateProfile dataclass with configurable gates per type
- [ ] Default profiles defined matching the decision matrix
- [ ] Schema supports custom profiles via configuration
- [ ] Unit tests verify profile application
- [ ] Documentation updated with task type descriptions

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

## Notes

This is a foundational task that defines the schema. TASK-FBSDK-021 and TASK-FBSDK-022 depend on this schema being complete before they can implement the consumers.
