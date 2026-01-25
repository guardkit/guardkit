# Task Type Schema and Quality Gate Profiles

## Overview

The task type schema provides a formalized way to classify tasks and apply task-specific quality gate profiles. Different task types have different validation requirements:

- **SCAFFOLDING**: Configuration files, project setup, templates
  - Minimal validation (no architecture review, no coverage)
  - Plan audit required to ensure completeness

- **FEATURE**: Primary implementation tasks (default)
  - Full quality gates (architecture review ≥60, coverage ≥80%, tests required)
  - Complete validation pipeline

- **INFRASTRUCTURE**: DevOps, deployment, CI/CD
  - Tests required but no architecture review
  - Focus on deployment reliability

- **DOCUMENTATION**: Guides, API docs, tutorials
  - Minimal validation (no gates required)
  - Focus on content completeness

## Usage

### Getting a Profile

```python
from guardkit.models import TaskType, get_profile

# Get default profile (FEATURE - backward compatible)
profile = get_profile()

# Get specific profile by task type
scaffolding_profile = get_profile(TaskType.SCAFFOLDING)
infrastructure_profile = get_profile(TaskType.INFRASTRUCTURE)
```

### Using ProfileClasses

```python
from guardkit.models import QualityGateProfile, TaskType

# Get profile via class method
feature_profile = QualityGateProfile.for_type(TaskType.FEATURE)

# Access individual gates
if feature_profile.arch_review_required:
    # Enforce architectural review (≥60 score)
    pass

if feature_profile.coverage_required:
    # Enforce coverage threshold (≥80%)
    pass
```

### Task Frontmatter

Add `task_type` field to task file frontmatter:

```yaml
---
id: TASK-FBSDK-020
title: Define task type schema
task_type: scaffolding  # NEW FIELD (optional, defaults to feature)
---
```

## Quality Gate Profiles

### Profile Matrix

| Gate | Scaffolding | Feature | Infrastructure | Documentation |
|------|-------------|---------|-----------------|---------------|
| Architectural Review | Skip | ≥60 | Skip | Skip |
| Code Coverage | Skip | ≥80% | Skip | Skip |
| Tests Required | Optional | Yes | Yes | No |
| Plan Audit | Yes | Yes | Yes | No |

### Default Profiles

#### FEATURE Profile (Default)
```python
QualityGateProfile(
    arch_review_required=True,      # Phase 2.5 enforced
    arch_review_threshold=60,       # Minimum score
    coverage_required=True,         # Coverage check required
    coverage_threshold=80.0,        # Line coverage minimum
    tests_required=True,            # All tests must pass
    plan_audit_required=True,       # Scope creep detection
)
```

#### SCAFFOLDING Profile
```python
QualityGateProfile(
    arch_review_required=False,     # Skip architectural review
    arch_review_threshold=0,        # Not applicable
    coverage_required=False,        # Skip coverage check
    coverage_threshold=0.0,         # Not applicable
    tests_required=False,           # Optional (e.g., validation scripts)
    plan_audit_required=True,       # Ensure configuration completeness
)
```

#### INFRASTRUCTURE Profile
```python
QualityGateProfile(
    arch_review_required=False,     # Different paradigm for infra
    arch_review_threshold=0,        # Not applicable
    coverage_required=False,        # Meaningful for code, not infra
    coverage_threshold=0.0,         # Not applicable
    tests_required=True,            # Deployment must be tested
    plan_audit_required=True,       # Ensure deployment is complete
)
```

#### DOCUMENTATION Profile
```python
QualityGateProfile(
    arch_review_required=False,     # Not applicable to docs
    arch_review_threshold=0,        # Not applicable
    coverage_required=False,        # Not applicable to docs
    coverage_threshold=0.0,         # Not applicable
    tests_required=False,           # Not applicable to docs
    plan_audit_required=False,      # Minimal validation for docs
)
```

## API Reference

### TaskType Enum

```python
class TaskType(Enum):
    SCAFFOLDING = "scaffolding"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
```

### QualityGateProfile Dataclass

```python
@dataclass
class QualityGateProfile:
    arch_review_required: bool      # Phase 2.5 required?
    arch_review_threshold: int      # Min score (0-100)
    coverage_required: bool         # Coverage check required?
    coverage_threshold: float       # Min percentage (0-100)
    tests_required: bool            # Tests required?
    plan_audit_required: bool       # Phase 5.5 required?

    @classmethod
    def for_type(cls, task_type: TaskType) -> "QualityGateProfile":
        """Get default profile for task type."""

    def __post_init__(self) -> None:
        """Validate configuration."""
```

### Functions

#### get_profile()

```python
def get_profile(task_type: Optional[TaskType] = None) -> QualityGateProfile:
    """Get quality gate profile for task type.

    Args:
        task_type: TaskType to get profile for, or None for default.

    Returns:
        QualityGateProfile for the task type.
        Returns FEATURE profile if task_type is None (backward compatible).
    """
```

### DEFAULT_PROFILES Registry

```python
DEFAULT_PROFILES: Dict[TaskType, QualityGateProfile] = {
    TaskType.SCAFFOLDING: ...,
    TaskType.FEATURE: ...,
    TaskType.INFRASTRUCTURE: ...,
    TaskType.DOCUMENTATION: ...,
}
```

## Validation

The `QualityGateProfile.__post_init__()` method validates:

1. **arch_review_threshold** must be 0-100
   - If arch_review_required is False, must be 0

2. **coverage_threshold** must be 0-100
   - If coverage_required is False, must be 0

Raises `ValueError` if validation fails.

## Backward Compatibility

Tasks without a `task_type` field default to the FEATURE profile, maintaining
the original strict quality gates:

```python
# Old task (no task_type field) uses FEATURE profile
profile = get_profile(None)  # Returns FEATURE profile
# This ensures existing tasks continue to work unchanged
```

## Integration Points

This schema is used by:

1. **TASK-FBSDK-021**: Integrate profiles into `coach_validator.py`
   - Apply profile-specific quality gates during validation

2. **TASK-FBSDK-022**: Auto-detect task types in `/feature-plan`
   - Suggest appropriate task type based on feature description

## Testing

Comprehensive test suite with 46 tests:

- TaskType enum validation (6 tests)
- Profile creation and configuration (8 tests)
- Validation logic (10 tests)
- Registry and lookup functions (11 tests)
- Backward compatibility (2 tests)
- Integration workflows (3 tests)

Run tests:
```bash
pytest tests/unit/test_task_types.py -v --cov=guardkit.models
```

Coverage: 100% lines, 100% branches

## Examples

### Creating a Feature Task

```python
# Feature tasks use full quality gates
profile = get_profile(TaskType.FEATURE)

# Validate quality gates
if profile.arch_review_required:
    # Run Phase 2.5 - Architectural Review
    score = run_architecture_review(implementation)
    assert score >= profile.arch_review_threshold

if profile.coverage_required:
    # Check coverage meets threshold
    coverage = measure_coverage(test_results)
    assert coverage >= profile.coverage_threshold
```

### Creating a Scaffolding Task

```python
# Scaffolding tasks skip most gates
profile = get_profile(TaskType.SCAFFOLDING)

# Only plan audit is required
if profile.plan_audit_required:
    # Run Phase 5.5 - Plan Audit (scope creep detection)
    audit_results = run_plan_audit(implementation_plan)
    assert audit_results.no_scope_creep
```

### Creating a Documentation Task

```python
# Documentation tasks have minimal validation
profile = get_profile(TaskType.DOCUMENTATION)

# No quality gates required!
# Just ensure content is complete
```

## Related Files

- `guardkit/models/task_types.py` - Main implementation
- `tests/unit/test_task_types.py` - Test suite
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Consumer (TASK-FBSDK-021)
- Task file frontmatter schema documentation
