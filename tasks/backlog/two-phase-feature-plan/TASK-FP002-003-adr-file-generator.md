---
id: TASK-FP002-003
title: ADR File Generator
task_type: feature
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 2
implementation_mode: task-work
complexity: 4
complexity_score: 4
type: implementation
domain_tags:
- adr-generation
- documentation
- graphiti-seeding
files_to_create:
- guardkit/planning/adr_generator.py
- tests/unit/test_adr_generator.py
files_to_modify: []
files_not_to_touch:
- docs/adr/
dependencies:
- TASK-FP002-001
relevant_decisions:
- D3
turn_budget:
  expected: 2
  max: 4
graphiti_context_budget: 4000
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FP-002
  base_branch: main
  started_at: '2026-02-10T17:50:11.817900'
  last_updated: '2026-02-10T17:57:35.119784'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-10T17:50:11.817900'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# TASK-FP002-003: ADR File Generator

## Description

Create `guardkit/planning/adr_generator.py` that generates Architecture Decision Record markdown files from the `Decision` dataclass produced by the Spec Parser (TASK-FP002-001). Each decision in the spec's Decision Log becomes a separate ADR file suitable for Graphiti seeding.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `guardkit/planning/adr_generator.py`
- [ ] File exists: `tests/unit/test_adr_generator.py`
- [ ] Function `generate_adrs(decisions, feature_id, output_dir)` returns `list[Path]`
- [ ] Generated ADR files follow naming: `ADR-FP-{feature_number}-{slug}.md`
- [ ] ADR content includes sections: Status, Date, Context, Decision, Rationale, Alternatives Rejected, Consequences
- [ ] Duplicate detection: skips if ADR with same title already exists in output_dir (when `check_duplicates=True`)
- [ ] Handles empty decisions list gracefully (returns empty list)
- [ ] Slug generation converts titles to lowercase-hyphenated format
- [ ] Tests pass: `pytest tests/unit/test_adr_generator.py -v`
- [ ] Lint passes: `ruff check guardkit/planning/adr_generator.py`

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
