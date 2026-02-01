---
complexity: 3
conductor_workspace: gr-mvp-wave6-schemas
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-003-D
feature_id: FEAT-GR-MVP
id: TASK-GR-001-E
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- project-seeding
- autobuild
- quality-gates
- mvp-phase-2
task_type: feature
title: Create QualityGateConfigEpisode and seed defaults
updated: 2026-02-01T09:30:00+00:00
wave: 6
---

# Task: Create QualityGateConfigEpisode and seed defaults

## Description

Create the QualityGateConfigEpisode dataclass and seed default task-type specific thresholds. This directly addresses the "quality gate threshold drift" problem identified in TASK-REV-7549.

## Acceptance Criteria

- [x] QualityGateConfigEpisode dataclass implemented (as `QualityGateConfigFact` in `guardkit/knowledge/facts/quality_gate_config.py`)
- [x] Default configs for: scaffolding, feature, testing, documentation (see `QUALITY_GATE_CONFIGS` list)
- [x] Configs seeded during project init (via `seed_quality_gate_configs()` in `guardkit/knowledge/seed_quality_gate_configs.py`)
- [x] Configs accessible during task-work/feature-build (via `get_quality_gate_config()` in `guardkit/knowledge/quality_gate_queries.py`)
- [x] Entity ID for upsert (allows customization) (uses `id` field, e.g., `QG-FEATURE-LOW`)

## Implementation Notes

### Schema Definition

```python
@dataclass
class QualityGateConfigEpisode:
    """Quality gate configuration per task type."""

    entity_type: str = "quality_gate_config"

    task_type: str = ""  # "scaffolding" | "feature" | "testing" | "documentation"
    complexity_range: Tuple[int, int] = (1, 10)

    # Architectural review
    arch_review_required: bool = True
    arch_review_threshold: int = 60

    # Test coverage
    coverage_required: bool = True
    coverage_threshold: float = 0.80

    # Test execution
    tests_required: bool = True

    # Effective date (for versioning)
    effective_from: str = ""

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti."""
        return f"""
        Task Type: {self.task_type}
        Complexity Range: {self.complexity_range[0]}-{self.complexity_range[1]}

        Quality Gates:
        - Architectural Review: {"Required" if self.arch_review_required else "Not Required"} (threshold: {self.arch_review_threshold}/100)
        - Test Coverage: {"Required" if self.coverage_required else "Not Required"} (threshold: {self.coverage_threshold*100}%)
        - Tests: {"Required" if self.tests_required else "Not Required"}

        Effective From: {self.effective_from}
        """

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert."""
        return f"quality_gate_config_{self.task_type}"
```

### Default Configs

```python
QUALITY_GATE_DEFAULTS = {
    "scaffolding": QualityGateConfigEpisode(
        task_type="scaffolding",
        complexity_range=(1, 4),
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0.0,
        tests_required=False,
    ),
    "feature": QualityGateConfigEpisode(
        task_type="feature",
        complexity_range=(1, 10),
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=0.80,
        tests_required=True,
    ),
    "testing": QualityGateConfigEpisode(
        task_type="testing",
        complexity_range=(1, 6),
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,  # Tests ARE the coverage
        coverage_threshold=0.0,
        tests_required=True,
    ),
    "documentation": QualityGateConfigEpisode(
        task_type="documentation",
        complexity_range=(1, 4),
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0.0,
        tests_required=False,
    ),
}
```

### Files to Create

- `src/guardkit/integrations/graphiti/episodes/quality_gate_config.py`

## Test Requirements

- [ ] Unit tests for schema
- [ ] Unit tests for default configs
- [ ] Integration test for seeding

## Notes

This directly addresses AutoBuild lesson learned - threshold drift caused unpredictable approvals.

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
- [TASK-REV-7549 AutoBuild Lessons](../../../../tasks/backlog/TASK-REV-7549-autobuild-lessons-learned-graphiti.md)