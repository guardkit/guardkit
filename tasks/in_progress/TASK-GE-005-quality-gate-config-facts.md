---
complexity: 5
conductor_workspace: graphiti-enhancements-wave2-3
created_at: 2026-01-29 00:00:00+00:00
dependencies: []
estimated_minutes: 120
feature_id: FEAT-GE
id: TASK-GE-005
implementation_mode: task-work
parent_review: TASK-REV-7549
priority: 2
status: design_approved
tags:
- graphiti
- facts
- quality-gates
- configuration
task_type: feature
title: Quality Gate Configuration Facts
wave: 2
---

# TASK-GE-005: Quality Gate Configuration Facts

## Overview

**Priority**: High (Enables configurable thresholds)
**Dependencies**: None (uses existing Graphiti infrastructure)

## Problem Statement

From TASK-REV-7549 analysis: "Quality Gate Threshold Drift" was a recurring problem:
- Fixed arch_review_threshold=60 for ALL feature tasks regardless of complexity
- Simple tasks (complexity 2-3) held to same standards as complex tasks
- Thresholds changed unpredictably across turns
- No versioning or audit trail for threshold changes

Quality gate thresholds are hardcoded, not queryable, and not task-type sensitive.

## Goals

1. Create QualityGateConfigFact for versioned, queryable thresholds
2. Define configurations for different task types and complexity levels
3. Integrate with CoachValidator to use configured thresholds
4. Enable threshold queries ("What threshold applies to this task?")

## Technical Approach

### Fact Definition

```python
# guardkit/knowledge/facts/quality_gate_config.py

from dataclasses import dataclass, field
from typing import Tuple, Optional
from datetime import datetime

@dataclass
class QualityGateConfigFact:
    """Versioned quality gate thresholds."""

    # Identity
    id: str  # QG-{task_type}-{complexity_range}
    name: str  # Human-readable name

    # Applicability
    task_type: str  # "scaffolding" | "feature" | "testing" | "refactoring" | "docs"
    complexity_range: Tuple[int, int]  # (min, max) complexity inclusive

    # Thresholds
    arch_review_required: bool
    arch_review_threshold: Optional[int]  # None if not required
    test_pass_required: bool
    coverage_required: bool
    coverage_threshold: Optional[float]  # None if not required
    lint_required: bool

    # Rationale
    rationale: str  # Why these thresholds for this profile

    # Versioning
    version: str = "1.0.0"
    effective_from: datetime = field(default_factory=datetime.now)
    supersedes: Optional[str] = None  # Previous version ID

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body."""
        return {
            "entity_type": "quality_gate_config",
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "complexity_range": self.complexity_range,
            "arch_review_required": self.arch_review_required,
            "arch_review_threshold": self.arch_review_threshold,
            "test_pass_required": self.test_pass_required,
            "coverage_required": self.coverage_required,
            "coverage_threshold": self.coverage_threshold,
            "lint_required": self.lint_required,
            "rationale": self.rationale,
            "version": self.version,
            "effective_from": self.effective_from.isoformat(),
            "supersedes": self.supersedes
        }
```

### Quality Gate Configurations

```python
QUALITY_GATE_CONFIGS = [
    # Scaffolding tasks (complexity 1-3)
    QualityGateConfigFact(
        id="QG-SCAFFOLDING-LOW",
        name="Scaffolding (Low Complexity)",
        task_type="scaffolding",
        complexity_range=(1, 3),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=True,
        coverage_required=False,
        coverage_threshold=None,
        lint_required=True,
        rationale="Scaffolding tasks create boilerplate with minimal logic. "
                  "No arch review needed; tests verify correctness; lint ensures consistency."
    ),

    # Simple feature tasks (complexity 1-3)
    QualityGateConfigFact(
        id="QG-FEATURE-LOW",
        name="Feature (Low Complexity)",
        task_type="feature",
        complexity_range=(1, 3),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=True,
        coverage_required=True,
        coverage_threshold=60.0,
        lint_required=True,
        rationale="Simple features (config, utilities) need basic coverage but "
                  "don't warrant arch review. 60% coverage ensures basics are tested."
    ),

    # Medium feature tasks (complexity 4-6)
    QualityGateConfigFact(
        id="QG-FEATURE-MED",
        name="Feature (Medium Complexity)",
        task_type="feature",
        complexity_range=(4, 6),
        arch_review_required=True,
        arch_review_threshold=50,
        test_pass_required=True,
        coverage_required=True,
        coverage_threshold=75.0,
        lint_required=True,
        rationale="Medium features need light arch review (50) to catch obvious issues. "
                  "75% coverage balances thoroughness with practicality."
    ),

    # Complex feature tasks (complexity 7-10)
    QualityGateConfigFact(
        id="QG-FEATURE-HIGH",
        name="Feature (High Complexity)",
        task_type="feature",
        complexity_range=(7, 10),
        arch_review_required=True,
        arch_review_threshold=70,
        test_pass_required=True,
        coverage_required=True,
        coverage_threshold=80.0,
        lint_required=True,
        rationale="Complex features need rigorous arch review (70) to maintain system integrity. "
                  "80% coverage ensures critical paths are tested."
    ),

    # Testing tasks (any complexity)
    QualityGateConfigFact(
        id="QG-TESTING",
        name="Testing Task",
        task_type="testing",
        complexity_range=(1, 10),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=True,
        coverage_required=False,  # Tests themselves don't need coverage
        coverage_threshold=None,
        lint_required=True,
        rationale="Test tasks add or improve tests. They must pass but don't need coverage metrics. "
                  "No arch review as tests follow existing patterns."
    ),

    # Documentation tasks (any complexity)
    QualityGateConfigFact(
        id="QG-DOCS",
        name="Documentation Task",
        task_type="docs",
        complexity_range=(1, 10),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=False,
        coverage_required=False,
        coverage_threshold=None,
        lint_required=False,
        rationale="Documentation tasks don't involve code. No quality gates except manual review."
    )
]
```

### Query Function

```python
async def get_quality_gate_config(
    task_type: str,
    complexity: int
) -> Optional[QualityGateConfigFact]:
    """Get quality gate configuration for task type and complexity."""

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return None

    results = await graphiti.search(
        query=f"quality_gate_config {task_type} complexity {complexity}",
        group_ids=["quality_gate_configs"],
        num_results=5
    )

    # Find matching config
    for result in results:
        body = result.get('body', {})
        min_c, max_c = body.get('complexity_range', (0, 10))
        if body.get('task_type') == task_type and min_c <= complexity <= max_c:
            return QualityGateConfigFact(**body)

    return None
```

### Integration with CoachValidator

```python
# In guardkit/orchestrator/coach_validator.py

async def _get_thresholds(self, task_type: str, complexity: int) -> dict:
    """Get thresholds from Graphiti config or fall back to defaults."""

    config = await get_quality_gate_config(task_type, complexity)

    if config:
        return {
            "arch_review_required": config.arch_review_required,
            "arch_review_threshold": config.arch_review_threshold,
            "coverage_required": config.coverage_required,
            "coverage_threshold": config.coverage_threshold,
            "test_pass_required": config.test_pass_required
        }

    # Default fallback (conservative)
    return {
        "arch_review_required": True,
        "arch_review_threshold": 60,
        "coverage_required": True,
        "coverage_threshold": 80.0,
        "test_pass_required": True
    }
```

## Acceptance Criteria

- [ ] QualityGateConfigFact dataclass created with all fields
- [ ] 6 configurations seeded (scaffolding, feature low/med/high, testing, docs)
- [ ] Query function retrieves config by task type and complexity
- [ ] CoachValidator uses configured thresholds
- [ ] Thresholds logged in Coach decisions for audit trail
- [ ] Unit tests for fact and query functions
- [ ] Integration test confirms correct config applied

## Files to Create/Modify

### New Files
- `guardkit/knowledge/facts/quality_gate_config.py`
- `guardkit/knowledge/seed_quality_gate_configs.py`
- `guardkit/knowledge/quality_gate_queries.py`
- `tests/knowledge/test_quality_gate_configs.py`

### Modified Files
- `guardkit/orchestrator/coach_validator.py` (use Graphiti thresholds)
- `guardkit/knowledge/seed_system_context.py` (call seed_quality_gate_configs)

## Testing Strategy

1. **Unit tests**: Test fact, seeding, and query functions
2. **Integration tests**: Seed configs, verify correct one returned for inputs
3. **E2E test**: Run task-work, verify Coach uses correct thresholds for task type