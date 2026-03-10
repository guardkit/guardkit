---
id: TASK-ABE-003
title: Generate structured review summaries from autobuild logs
status: completed
created: 2026-03-10T12:00:00Z
updated: 2026-03-10T16:30:00Z
completed: 2026-03-10T16:30:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria satisfied"
completed_location: tasks/completed/TASK-ABE-003/
priority: medium
tags: [autobuild, review-quality, documentation]
complexity: 5
task_type: feature
parent_review: TASK-REV-8D32
feature_id: FEAT-ABE
wave: 2
implementation_mode: task-work
dependencies: [TASK-ABE-001, TASK-ABE-002]
---

# Task: Generate structured review summaries from autobuild logs

## Description

Add a post-processing step to the feature orchestrator that generates a structured, human-readable review summary from raw autobuild execution data. The current autobuild output (scored 45/100 for review document quality) consists of raw terminal logs with DEBUG/INFO lines, progress bars, and turn metadata that require manual parsing.

## Acceptance Criteria

1. A `ReviewSummaryGenerator` class (or equivalent) exists that processes autobuild execution data
2. The summary includes:
   - Feature-level metrics (total turns, duration, first-attempt pass rate)
   - Per-task outcome table (task ID, turns, implementation mode, outcome, rejection reasons if multi-turn)
   - Aggregated quality metrics (test coverage, lint status, architectural review score)
   - Turn efficiency analysis (single-turn vs multi-turn breakdown)
   - Key findings section (auto-generated from turn data)
3. The summary is written as a structured markdown file alongside the raw log
4. The summary generator runs automatically after `feature_orchestrator.orchestrate()` completes
5. The summary format is stack-agnostic — works for any technology
6. Unit tests verify summary generation from sample autobuild data

## Implementation Notes

### Data Sources

The feature orchestrator already collects:
- `TaskExecutionResult` per task (success, total_turns, duration)
- Turn records with Player/Coach decisions
- Quality gate status per task
- Wave execution data

### Output Format

```markdown
# Autobuild Review Summary: FEAT-XXX

## Metrics
| Metric | Value |
|--------|-------|
| Total tasks | N |
| Total turns | N |
| Avg turns/task | N.NN |
| Duration | Xm Ys |
| First-attempt pass rate | NN% |

## Per-Task Outcomes
| Task | Turns | Mode | Outcome | Notes |
|------|-------|------|---------|-------|
| ... | ... | ... | ... | ... |

## Quality Metrics
- Test coverage: NN%
- Lint errors: N remaining
- Architectural review: NN/100

## Key Findings
- [Auto-generated from turn data]
```

### Key Files

- `guardkit/orchestrator/feature_orchestrator.py` — integration point after `orchestrate()`
- New: `guardkit/orchestrator/review_summary.py` — summary generator
- `guardkit/orchestrator/autobuild.py` — turn data access

## Coach Validation

- `pytest tests/ -v --tb=short` — all tests pass
- Verify summary markdown is well-formed
- Verify summary is generated for a sample autobuild execution
- Verify summary includes all required sections
