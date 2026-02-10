---
complexity: 5
complexity_score: 5
dependencies:
- TASK-FP002-001
- TASK-FP002-002
domain_tags:
- task-metadata
- graphiti-integration
- turn-budget
- domain-tags
feature_id: FEAT-FP-002
files_not_to_touch:
- guardkit/orchestrator/
- guardkit/knowledge/
files_to_create:
- guardkit/planning/task_metadata.py
- tests/unit/test_task_metadata.py
files_to_modify: []
graphiti_context_budget: 4000
id: TASK-FP002-005
implementation_mode: task-work
parent_review: TASK-REV-FP002
relevant_decisions:
- D5
- D10
status: design_approved
task_type: feature
title: Task Metadata Enricher
turn_budget:
  expected: 3
  max: 5
type: implementation
wave: 2
---

# TASK-FP002-005: Task Metadata Enricher

## Description

Create `guardkit/planning/task_metadata.py` that takes `TaskDefinition` (from SpecParser) and `TargetConfig` (from TargetMode), and produces enriched task markdown with YAML frontmatter, structured Coach validation blocks, and Player constraint sections. The output format is what gets written to individual task `.md` files.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `guardkit/planning/task_metadata.py`
- [ ] File exists: `tests/unit/test_task_metadata.py`
- [ ] Function `enrich_task(task, target_config, feature_id) -> EnrichedTask` exists
- [ ] Function `render_task_markdown(enriched_task) -> str` produces valid markdown with YAML frontmatter
- [ ] YAML frontmatter includes: task_id, feature_id, complexity, complexity_score, type, domain_tags, files_to_create, files_to_modify, files_not_to_touch, dependencies, relevant_decisions, turn_budget, graphiti_context_budget
- [ ] Turn budget follows rules: low → {expected:1, max:3}, medium → {expected:2, max:5}, high → {expected:3, max:5}
- [ ] Graphiti context budget follows rules: low → 2000, medium → 4000, high → 6000
- [ ] `local-model` target adds explicit import paths and type hints to implementation notes
- [ ] Rendered markdown contains sections: Description, Acceptance Criteria, Coach Validation Commands, Player Constraints, Implementation Notes
- [ ] Tests pass: `pytest tests/unit/test_task_metadata.py -v`
- [ ] Lint passes: `ruff check guardkit/planning/task_metadata.py`

## Coach Validation Commands

```bash
pytest tests/unit/test_task_metadata.py -v
ruff check guardkit/planning/task_metadata.py
python -c "from guardkit.planning.task_metadata import enrich_task, render_task_markdown; print('OK')"
```

## Player Constraints

- Create files ONLY in `guardkit/planning/` and `tests/unit/`
- Do NOT import from `guardkit/orchestrator/` or `guardkit/knowledge/`
- Import `TaskDefinition` from `guardkit.planning.spec_parser`
- Import `TargetConfig` from `guardkit.planning.target_mode`

## Implementation Notes (Prescriptive)

```python
from dataclasses import dataclass, field
from guardkit.planning.spec_parser import TaskDefinition
from guardkit.planning.target_mode import TargetConfig, TargetMode

TURN_BUDGETS = {
    "low": {"expected": 1, "max": 3},
    "medium": {"expected": 2, "max": 5},
    "high": {"expected": 3, "max": 5},
}

CONTEXT_BUDGETS = {
    "low": 2000,
    "medium": 4000,
    "high": 6000,
}

@dataclass
class EnrichedTask:
    task_definition: TaskDefinition
    feature_id: str
    turn_budget: dict[str, int]
    graphiti_context_budget: int
    target_config: TargetConfig
    enriched_notes: str = ""

def enrich_task(task: TaskDefinition, target_config: TargetConfig, feature_id: str) -> EnrichedTask:
    """Add metadata enrichments based on target mode and complexity."""

def render_task_markdown(enriched_task: EnrichedTask) -> str:
    """Render enriched task as markdown with YAML frontmatter."""
```

When `target_config.mode == LOCAL_MODEL`:
- Add explicit import statements to implementation notes
- Add full type signatures where type hints are mentioned
- Format Coach blocks as structured YAML instead of bash code blocks