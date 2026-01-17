# Feature: Provenance-Aware Intensity System

## Problem Statement

Currently, `/task-work` applies the same heavyweight ceremony (planning, architectural review, complexity evaluation) regardless of whether that work was already done upstream by `/task-review` or `/feature-plan`. This causes:

- **65+ minute execution** for tasks that should take 10-20 minutes
- **Redundant architectural reviews** when parent review already scored 85/100
- **Wasted tokens** regenerating plans that already exist
- **User frustration** having to manually specify `--micro` to skip redundant phases

## Evidence

Real-world validation from MyDrive project (TASK-REV-G001):
- 6 subtasks (TASK-GS-011a through 011f) created from comprehensive architectural review
- Per current rules: "❌ Not eligible for --micro" (complexity 2-3, multi-file)
- User applied `--micro` anyway
- Result: **10-20 minutes per task with quality maintained**

The ceremony was front-loaded in `/task-review`. The subtasks didn't need it repeated.

## Solution

Implement **provenance-aware intensity detection**:

1. Track where tasks originate (`parent_review`, `feature_id` fields)
2. Auto-detect appropriate intensity based on provenance
3. Provide `--intensity` flag for manual override
4. Skip redundant phases when upstream command already did the work

## Intensity Levels

| Level | Duration | When Applied |
|-------|----------|--------------|
| `minimal` | 3-10 min | Task from `/task-review`, or complexity ≤3 |
| `light` | 10-20 min | Task from `/feature-plan`, or complexity 4-5 |
| `standard` | 20-40 min | Fresh task, complexity 5-6 |
| `strict` | 45-90 min | Fresh task, complexity 7+, or security keywords |

## Subtasks

| Task ID | Title | Wave | Mode | Est. Time |
|---------|-------|------|------|-----------|
| TASK-INT-a1b2 | Add provenance fields to task frontmatter | 1 | task-work | 1-2 hours |
| TASK-INT-c3d4 | Implement --intensity flag with 4 levels | 1 | task-work | 2-3 hours |
| TASK-INT-e5f6 | Add provenance-aware auto-detection logic | 2 | task-work | 2-3 hours |
| TASK-INT-g7h8 | Update task-work command to use intensity | 2 | task-work | 2-3 hours |
| TASK-INT-i9j0 | Add integration tests for intensity system | 3 | task-work | 1-2 hours |

## Dependencies

- **Depends on**: TASK-TWP Wave 1 (documentation constraints, micro threshold)
- **Enhances**: `/task-work`, `/task-review`, `/feature-plan` commands

## Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Reviewed subtask duration | 65+ min | 10-20 min | 70-85% faster |
| Feature-plan subtask duration | 65+ min | 15-25 min | 60-75% faster |
| Fresh simple task duration | 65+ min | 10-15 min | 80% faster |
| Token consumption | 85k+ | 10-25k | 70-88% reduction |

## Related

- [TASK-REV-FB16 Review Report](/.claude/reviews/TASK-REV-FB16-review-report.md) - Decision analysis
- [TASK-REV-FB15 Review Report](/.claude/reviews/TASK-REV-FB15-review-report.md) - Root cause analysis
- [Adversarial Intensity Research](/docs/research/guardkit-agent/Adversarial_Intensity_and_Adaptive_Ceremony_Research.md)
- [TASK-TWP Performance Tasks](/tasks/backlog/task-work-performance/) - Prerequisite tasks
