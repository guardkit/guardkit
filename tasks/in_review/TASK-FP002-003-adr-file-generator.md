---
complexity: 4
complexity_score: 4
dependencies:
- TASK-FP002-001
domain_tags:
- adr-generation
- documentation
- graphiti-seeding
feature_id: FEAT-FP-002
files_not_to_touch:
- docs/adr/
files_to_create:
- guardkit/planning/adr_generator.py
- tests/unit/test_adr_generator.py
files_to_modify: []
graphiti_context_budget: 4000
id: TASK-FP002-003
implementation_mode: task-work
parent_review: TASK-REV-FP002
relevant_decisions:
- D3
status: in_review
task_type: feature
title: ADR File Generator
turn_budget:
  expected: 2
  max: 4
type: implementation
wave: 2
---

# TASK-FP002-003: ADR File Generator

## Description

Create `guardkit/planning/adr_generator.py` that generates Architecture Decision Record markdown files from the `Decision` dataclass produced by the Spec Parser (TASK-FP002-001). Each decision in the spec's Decision Log becomes a separate ADR file suitable for Graphiti seeding.

## Acceptance Criteria (Machine-Verifiable)

- [x] File exists: `guardkit/planning/adr_generator.py`
- [x] File exists: `tests/unit/test_adr_generator.py`
- [x] Function `generate_adrs(decisions, feature_id, output_dir)` returns `list[Path]`
- [x] Generated ADR files follow naming: `ADR-FP-{feature_number}-{slug}.md`
- [x] ADR content includes sections: Status, Date, Context, Decision, Rationale, Alternatives Rejected, Consequences
- [x] Duplicate detection: skips if ADR with same title already exists in output_dir (when `check_duplicates=True`)
- [x] Handles empty decisions list gracefully (returns empty list)
- [x] Slug generation converts titles to lowercase-hyphenated format
- [x] Tests pass: `pytest tests/unit/test_adr_generator.py -v` (29/29 tests passing)
- [x] Lint passes: `ruff check guardkit/planning/adr_generator.py`

## Coach Validation Commands

```bash
pytest tests/unit/test_adr_generator.py -v
ruff check guardkit/planning/adr_generator.py
python -c "from guardkit.planning.adr_generator import generate_adrs; print('Import OK')"
```

## Player Constraints

- Create files ONLY in `guardkit/planning/` and `tests/unit/`
- Tests must use `tmp_path` fixture for output, never write to actual `docs/adr/`
- Import `Decision` dataclass from `guardkit.planning.spec_parser`

## Implementation Notes (Prescriptive)

```python
from pathlib import Path
from guardkit.planning.spec_parser import Decision

def generate_adrs(
    decisions: list[Decision],
    feature_id: str,
    output_dir: Path = Path("docs/adr"),
    check_duplicates: bool = True,
) -> list[Path]:
    """Generate ADR markdown files from Decision Log entries."""
```

ADR file content template:
```markdown
# ADR-FP-{feature_number}-{slug}: {title}

**Status:** {adr_status}
**Date:** {today's date}
**Feature:** {feature_id}
**Decision:** {number}

## Context

{rationale}

## Decision

{title}

## Rationale

{rationale}

## Alternatives Rejected

{alternatives_rejected}

## Consequences

Implementation must follow this decision. See feature spec for full context.
```

- Extract feature number from feature_id (e.g., "FEAT-FP-002" → "002")
- Slug generation: lowercase, replace spaces with hyphens, remove special chars, truncate to 50 chars