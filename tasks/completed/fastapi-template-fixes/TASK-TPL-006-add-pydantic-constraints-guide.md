---
id: TASK-TPL-006
title: Add pydantic-constraints.md pattern guide
status: completed
created: 2026-01-27T12:45:00Z
updated: 2026-01-27T14:35:00Z
completed: 2026-01-27T14:35:00Z
priority: low
tags: [template, fastapi-python, pydantic, patterns, documentation]
complexity: 2
parent_review: TASK-REV-A7F3
feature_id: FEAT-TPL-FIX
wave: 2
implementation_mode: direct
dependencies: []
conductor_workspace: fastapi-fixes-wave2-3
completed_location: tasks/completed/fastapi-template-fixes/
files_created:
  - installer/core/templates/fastapi-python/.claude/rules/patterns/pydantic-constraints.md
---

# Task: Add pydantic-constraints.md pattern guide

## Description

Add a pattern guide for Pydantic field constraints to prevent over-constraining schemas that can fail with valid third-party data. The health check schema issue (ge=0 failing for negative pool overflow) represents a common anti-pattern.

## Problem

Health check endpoint failed with:
```
overflow: Input should be greater than or equal to 0
```

SQLAlchemy connection pool can report negative overflow values (indicating available capacity), but the schema had `ge=0` constraint.

## Solution

Create `.claude/rules/patterns/pydantic-constraints.md`:

```markdown
---
paths: **/*.py, **/schemas/**
---

# Pydantic Field Constraint Patterns

## When to Use Strict Constraints

Use `ge=0`, `le=N`, `min_length`, etc. for:

- **User-provided input** (IDs, quantities, prices)
- **Application-level metrics** you control
- **Domain values** with known valid ranges

## When to Avoid Strict Constraints

Avoid strict constraints for:

- **Third-party library metrics** (database pools, cache stats)
- **System resource measurements** (memory, CPU, disk)
- **External API responses** (may have unexpected values)

## Database Pool Metrics Example

```python
# BAD - Can fail with valid SQLAlchemy pool metrics
class HealthResponse(BaseModel):
    pool_size: int = Field(ge=0)
    pool_overflow: int = Field(ge=0)  # Fails! Can be negative

# GOOD - Accepts valid range including overflow indicators
class HealthResponse(BaseModel):
    pool_size: int = Field(description="Current pool size")
    pool_overflow: int = Field(
        description="Overflow count (negative indicates available capacity)"
    )
```

## Constraint Decision Matrix

| Data Source | Strict Constraints? | Rationale |
|-------------|---------------------|-----------|
| User input | Yes | Validate early |
| Database IDs | Yes (ge=1) | IDs are positive |
| Quantities/Prices | Yes (ge=0) | Business rule |
| External APIs | No | Unpredictable |
| Library metrics | No | Implementation details |
| System stats | No | Can be negative/overflow |

## Default Behavior

When unsure, prefer **documentation over constraints**:

```python
# Prefer this
field: int = Field(description="Value from external system, may be negative")

# Over this
field: int = Field(ge=0, description="Must be positive")
```

## Validation Layers

Apply constraints at appropriate layers:

1. **API Input**: Strict validation (user-provided)
2. **Internal Processing**: Type hints only
3. **External Data**: Loose validation, handle errors

```python
# API input - strict
class UserCreate(BaseModel):
    age: int = Field(ge=0, le=150)

# Internal - no constraints
class InternalMetrics(BaseModel):
    pool_overflow: int  # No constraints

# External - handle gracefully
class ExternalAPIResponse(BaseModel):
    value: Optional[int] = None  # May be missing
```
```

## Acceptance Criteria

- [x] Create `.claude/rules/patterns/pydantic-constraints.md`
- [x] Include database pool metrics example
- [x] Add constraint decision matrix
- [x] Document validation layers approach
- [x] Add paths frontmatter for relevant files

## Files to Create

1. `installer/core/templates/fastapi-python/.claude/rules/patterns/pydantic-constraints.md` (new)

## Notes

- Pattern guidance, not template fix
- Prevents future issues with third-party data
- Follows existing `.claude/rules/patterns/` structure
