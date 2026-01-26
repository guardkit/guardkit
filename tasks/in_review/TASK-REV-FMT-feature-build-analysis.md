---
id: TASK-REV-FMT
title: Analyze MCP Template Feature-Build Attempts (FEAT-FMT & FEAT-4048)
status: review_complete
created: 2026-01-25T12:00:00Z
updated: 2026-01-26T14:30:00Z
priority: high
task_type: review
tags: [feature-build, autobuild, analysis, post-mortem, fastmcp, typescript-mcp]
complexity: 5
decision_required: true
related_features: [FEAT-FMT, FEAT-4048]
review_mode: technical-debt
review_depth: standard
review_results:
  mode: technical-debt
  depth: standard
  findings_count: 3
  recommendations_count: 3
  report_path: .claude/reviews/TASK-REV-FMT-review-report.md
  completed_at: 2026-01-26T14:30:00Z
---

# Task: Analyze MCP Template Feature-Build Attempts

## Description

Analyze the `/feature-build` execution attempts for both MCP template features:
1. **FEAT-FMT** - FastMCP Python Template (documented in `/docs/reviews/feature-build/fastapi-python-mcp.md`)
2. **FEAT-4048** - TypeScript MCP Template (likely has same `task_type` validation issue)

Both features are expected to fail due to the same root cause: `task_type: implementation` in task frontmatter not accepted by CoachValidator. This review should identify:

1. Root cause analysis of the failure (shared across both features)
2. What work was actually accomplished despite the failure
3. Recommendations for fixing the immediate issue across all affected tasks
4. Systemic improvements to prevent similar failures

## Context

### Features Being Built

#### FEAT-FMT - FastMCP Python Template
- **Feature ID**: FEAT-FMT
- **Feature Name**: FastMCP Python Template
- **Tasks**: 8 total across 4 waves
- **Wave Structure**:
  - Wave 1: TASK-FMT-001, TASK-FMT-002 (Foundation)
  - Wave 2: TASK-FMT-003, TASK-FMT-004, TASK-FMT-005, TASK-FMT-006 (Core Content)
  - Wave 3: TASK-FMT-007 (Integration)
  - Wave 4: TASK-FMT-008 (Validation)
- **Build Status**: FAILED after ~15 minutes

#### FEAT-4048 - TypeScript MCP Template
- **Feature ID**: FEAT-4048
- **Feature Name**: TypeScript MCP Template
- **Tasks**: TBD (to be verified during review)
- **Build Status**: Not yet attempted (expected same failure)

### Failure Summary (FEAT-FMT - applies to both)
- **Result**: FAILED after ~15 minutes
- **Tasks Completed**: 0/8
- **Root Cause**: `task_type: implementation` in task frontmatter not accepted by CoachValidator
- **Valid Values**: scaffolding, feature, infrastructure, documentation, testing, refactor
- **Worktree Location**: `.guardkit/worktrees/FEAT-FMT`

### What Was Accomplished (FEAT-FMT)
Despite the failure, the Player agent made progress:
- TASK-FMT-001: 5 turns, created 5-8 files, modified 3-4 files
- TASK-FMT-002: 5 turns, created 1-2 files, modified 4-5 files

## Acceptance Criteria

- [ ] Root cause of the task_type validation failure is documented
- [ ] Verify FEAT-4048 tasks have the same `task_type: implementation` issue
- [ ] Gap analysis: Where should `implementation` have been mapped or where was it introduced incorrectly?
- [ ] Assessment of work done in FEAT-FMT worktree (what can be salvaged)
- [ ] Recommendation: Fix task files vs. update CoachValidator (pros/cons)
- [ ] Batch fix strategy for all affected tasks across both features
- [ ] Preventive measures documented (how to avoid this in future)
- [ ] Decision checkpoint provided with clear options

## Review Questions

1. **Source of Mismatch**: Where did `task_type: implementation` originate? Was it from:
   - Task creation template?
   - Manual editing?
   - Feature-plan auto-generation?

2. **Validator Design**: Should `implementation` be a valid task_type, or is there a semantic reason it's excluded?

3. **Cross-Feature Impact**: Do all tasks in FEAT-4048 have the same issue? How many total tasks need fixing?

4. **Worktree Assessment**: Is the work in `.guardkit/worktrees/FEAT-FMT` usable? What's the quality?

5. **Resume Strategy**: Can builds be resumed after fixing task_type values, or do they need fresh starts?

## Files to Review

### FEAT-FMT (FastMCP Python Template)
- `/docs/reviews/feature-build/fastapi-python-mcp.md` - Build output log
- `.guardkit/features/FEAT-FMT.yaml` - Feature definition
- `tasks/backlog/fastmcp-python-template/TASK-FMT-*.md` - All 8 task files
- `.guardkit/worktrees/FEAT-FMT/` - Worktree with partial implementation

### FEAT-4048 (TypeScript MCP Template)
- `.guardkit/features/FEAT-4048.yaml` - Feature definition (if exists)
- `tasks/backlog/*/TASK-*-4048-*.md` or similar - Task files (pattern TBD)

### System Files
- `guardkit/orchestrator/coach_validator.py` - CoachValidator allowed values
- Task creation templates - Source of task_type values

## Implementation Notes

### Review Findings Summary

**Root Cause**: All 8 FEAT-FMT tasks use `task_type: implementation` which is NOT a valid `TaskType` enum value. Valid values are: `scaffolding`, `feature`, `infrastructure`, `documentation`, `testing`, `refactor`.

**Key Findings**:
1. FEAT-FMT: 8/8 tasks affected - all use invalid `task_type: implementation`
2. FEAT-4048: 0/11 tasks affected - all use correct task_type values
3. Worktree has salvageable work: `manifest.json` and `settings.json` are complete

**Recommended Fix**: Update all 8 FEAT-FMT task files with correct task_type values:
- TASK-FMT-001, 002, 005: `scaffolding`
- TASK-FMT-003, 004, 006, 007: `documentation`
- TASK-FMT-008: `testing`

**Full Report**: [.claude/reviews/TASK-REV-FMT-review-report.md](.claude/reviews/TASK-REV-FMT-review-report.md)

## Test Execution Log

Review completed 2026-01-26. See full report for details.
