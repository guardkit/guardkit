---
id: TASK-CL-001
title: Fix status/directory mismatches
status: completed
created: 2026-01-26T14:45:00Z
updated: 2026-01-28T18:30:00Z
completed: 2026-01-28T18:30:00Z
priority: high
tags: [cleanup, housekeeping]
task_type: implementation
complexity: 2
parent_review: TASK-REV-BL01
feature_id: FEAT-CLEANUP
implementation_mode: direct
parallel_group: wave-1
---

# Task: Fix status/directory mismatches

## Description

Move 24 tasks to directories matching their frontmatter status.

## Actions Required

### Move backlog-status tasks to backlog/ (5 tasks)

```bash
git mv tasks/in_review/TASK-DOC-267D-add-agent-response-format-reference-to-claude-md-templates.md tasks/backlog/
git mv tasks/in_review/TASK-REV-AGENT-GEN-ai-agent-generation-heuristic-fallback-investigation.md tasks/backlog/
git mv tasks/in_review/TASK-TC-DESC-description-based-task-create.md tasks/backlog/
git mv tasks/in_progress/TASK-D3A1-review-template-init-architecture.md tasks/backlog/
git mv tasks/in_progress/TASK-FIX-A7D3-fix-python-scoping-issue-with-json-import-in-enhancer-py.md tasks/backlog/
```

### Move review_complete-status tasks from in_review/ to review_complete/ (15 tasks)

```bash
git mv tasks/in_review/TASK-5E55-review-greenfield-initialization-workflow.md tasks/review_complete/
git mv tasks/in_review/TASK-895A-review-model-selection-opus-4-5.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-3666-template-create-output-analysis.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-9AC5-feature-build-output-analysis.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-B601-feature-build-quality-gates-integration.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-C4D0-investigate-template-create-regressions.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-D4A7-progressive-disclosure-output-review.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-DF4A-review-feature-build-adversarial-loop-validation.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FB-regression-analysis.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FB05-comprehensive-feature-build-debugging.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FB20-post-arch-score-fix-validation.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FMT-feature-build-analysis.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-PD02-agent-enhance-output-review.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-TI01-analyze-template-init-updates.md tasks/review_complete/
git mv tasks/in_review/TASK-TMPL-2258-template-create-pivot-review.md tasks/review_complete/
```

### Move review_complete-status tasks from in_progress/ to review_complete/ (4 tasks)

```bash
git mv tasks/in_progress/TASK-2E9E-review-bdd-restoration-plan-requirekit-integration.md tasks/review_complete/
git mv tasks/in_progress/TASK-REV-2658-explore-agent-for-task-review.md tasks/review_complete/
git mv tasks/in_progress/TASK-REV-426C-review-progressive-disclosure-refactor.md tasks/review_complete/
git mv tasks/in_progress/TASK-REV-FB19-post-fbsdk015-017-arch-score-analysis.md tasks/review_complete/
```

## Acceptance Criteria

- [x] All 5 backlog-status tasks moved to tasks/backlog/
- [x] All 15 review_complete-status tasks moved from in_review/ to tasks/review_complete/
- [x] All 4 review_complete-status tasks moved from in_progress/ to tasks/review_complete/
- [x] Git history preserved via `git mv`

## Notes

- Use `git mv` to preserve history
- Run verification after: `grep -l "^status: backlog" tasks/in_review/*.md` should return empty
