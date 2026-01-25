# Feature: Architectural Score Gate Fix

## Overview

Fix the architectural score gate issue discovered during feature-build testing of FEAT-1D98 (FastAPI Health App). The system workflow is functioning correctly, but quality gates fail consistently because:

1. **Bug**: The `code_review.score` field is not being written to `task_work_results.json`, causing CoachValidator to default to score=0
2. **Design Gap**: Architectural review (SOLID/DRY/YAGNI) is inappropriate for scaffolding tasks that produce configuration files, not code

## Problem Statement

When running `guardkit autobuild feature FEAT-1D98`, the first task (TASK-HLTH-61B6 "Setup project structure and pyproject.toml") failed after 5 turns with consistent feedback: "Architectural review score below 60".

**Root Cause**: The `_write_task_work_results()` method in `agent_invoker.py` does not include the `code_review` field that CoachValidator expects. When CoachValidator reads `code_review.score`, it defaults to 0, which always fails the ≥60 threshold.

**Secondary Issue**: Even with the bug fixed, scaffolding tasks have no code architecture to evaluate, making SOLID/DRY/YAGNI scoring meaningless.

## Solution Approach

Implement a hybrid solution:

1. **Wave 1 (Bug Fix)**: Fix the persistence bug so architectural scores are properly written
2. **Wave 2 (Task Types)**: Introduce task type classification with appropriate quality gate profiles
3. **Wave 3 (Polish)**: Add override mechanisms and additional test coverage

## Subtasks

| Task ID | Title | Mode | Wave | Complexity |
|---------|-------|------|------|------------|
| TASK-FBSDK-018 | Write code_review.score to task_work_results.json | task-work | 1 | 3 |
| TASK-FBSDK-019 | Persist Phase 2.5B results for implement-only mode | task-work | 1 | 4 |
| TASK-FBSDK-020 | Define task type schema and quality gate profiles | task-work | 2 | 4 |
| TASK-FBSDK-021 | Modify CoachValidator to apply task type profiles | task-work | 2 | 5 |
| TASK-FBSDK-022 | Update feature-plan to auto-detect task types | task-work | 2 | 4 |
| TASK-FBSDK-023 | Add skip_arch_review CLI and frontmatter flags | task-work | 3 | 3 |
| TASK-FBSDK-024 | Create feature-code test case for quality gates | task-work | 3 | 3 |

## Dependencies

- Wave 2 depends on Wave 1 completion
- Wave 3 depends on Wave 2 completion

## Acceptance Criteria

- [ ] Feature-build completes successfully for scaffolding tasks
- [ ] Architectural review scores correctly persisted and evaluated
- [ ] Task types properly classified (scaffolding, feature, infrastructure, documentation)
- [ ] Quality gates applied contextually based on task type
- [ ] Override mechanisms available for edge cases
- [ ] Test coverage validates quality gate behavior

## Source Review

- Review Task: TASK-REV-FB19
- Review Report: `.claude/reviews/TASK-REV-FB19-review-report.md`
- Test Log: `docs/reviews/feature-build/after_FBSDK-015_016_017.md`
