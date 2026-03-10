---
id: TASK-ABE-001
title: Integrate lint compliance into implementation task acceptance criteria
status: completed
created: 2026-03-10T12:00:00Z
updated: 2026-03-10T15:45:00Z
completed: 2026-03-10T15:45:00Z
completed_location: tasks/completed/TASK-ABE-001/
previous_state: in_review
state_transition_reason: "All acceptance criteria verified, 11/11 tests passing, quality gates met"
priority: high
tags: [autobuild, quality-gates, efficiency, feature-planning]
complexity: 4
task_type: feature
parent_review: TASK-REV-8D32
feature_id: FEAT-ABE
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Integrate lint compliance into implementation task acceptance criteria

## Description

Modify the feature planning pipeline to automatically include lint/format compliance in every implementation task's acceptance criteria. Simultaneously, instruct the research template to NOT generate standalone "verify quality gates" tasks that only run linting/type checking.

The youtube-transcript-mcp autobuild showed 4 standalone quality gate tasks (17% of all tasks) consuming 41% of total turns (15/37) while producing zero production code. FEAT-6CE9 (no standalone quality gate task) achieved the best efficiency: 1.25 turns/task.

## Acceptance Criteria

1. Research template prompts include instructions to add lint/format compliance to every implementation task's ACs
2. Research template prompts include explicit instruction to NOT create standalone quality gate verification tasks
3. The instruction is stack-agnostic — references "lint compliance" generically, not specific tools like ruff
4. Existing feature plan parsing (`spec_parser.py`) continues to work without modification
5. Quality gate generator (`quality_gate_generator.py`) continues to aggregate lint commands from individual task ACs
6. At least one integration test verifies that a generated feature plan includes lint compliance in task ACs and does not contain standalone quality gate tasks

## Implementation Notes

### Current State
- ACs are parsed from research template markdown by `spec_parser.py:_parse_task()` (L571-581)
- ACs are numbered list items beneath `**Acceptance Criteria:**` in each task block
- Quality gate verification tasks are written by the AI into the research template, not procedurally generated
- `quality_gate_generator.py` aggregates validation commands from `**Coach Validation:**` sections

### Approach
- Modify the research template prompt (in the feature planning pipeline) to include:
  - "Every implementation task MUST include 'All modified files pass lint checks with zero errors' as an acceptance criterion"
  - "Do NOT create standalone quality gate verification tasks. Lint and type-check compliance must be verified within each implementation task."
- This is a prompt-level change — no parser modifications needed
- The Coach will verify lint compliance as part of each implementation task's ACs rather than in a separate final task

### Key Files
- Feature planning prompts (research template generation)
- `guardkit/planning/spec_parser.py` — verify AC parsing still works
- `guardkit/planning/quality_gate_generator.py` — verify aggregation still works
- `installer/core/agents/autobuild-player.md` — may need lint compliance reminder
- `installer/core/agents/autobuild-coach.md` — may need lint verification guidance

## Coach Validation

- Verify research template prompt includes lint AC instruction
- Verify research template prompt prohibits standalone quality gate tasks
- Run `pytest tests/ -v --tb=short` — all tests pass
- Generate a test feature plan and confirm no standalone quality gate tasks appear
