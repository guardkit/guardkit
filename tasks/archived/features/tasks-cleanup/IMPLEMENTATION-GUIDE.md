# Implementation Guide: Tasks Directory Cleanup

**Feature**: FEAT-CLEANUP
**Parent Review**: TASK-REV-BL01
**Created**: 2026-01-26

## Execution Strategy

### Wave 1 (Parallel - No Dependencies)

Execute these tasks in parallel using Conductor workspaces:

| Task | Description | Workspace Name |
|------|-------------|----------------|
| TASK-CL-001 | Fix status/directory mismatches | tasks-cleanup-wave1-1 |
| TASK-CL-002 | Archive empty feature directories | tasks-cleanup-wave1-2 |

### Wave 2 (Sequential - Depends on Wave 1)

Execute after Wave 1 completes:

| Task | Description | Dependencies |
|------|-------------|--------------|
| TASK-CL-003 | Consolidate FB review tasks | TASK-CL-001 |
| TASK-CL-004 | Move blocked to obsolete | None (Wave 2 timing) |
| TASK-CL-005 | Remove duplicate files | TASK-CL-001 |

## Execution Commands

### Wave 1

```bash
# Task CL-001: Fix status/directory mismatches
cd /path/to/guardkit

# Move backlog-status tasks to backlog/
git mv tasks/in_review/TASK-DOC-267D*.md tasks/backlog/
git mv tasks/in_review/TASK-REV-AGENT-GEN*.md tasks/backlog/
git mv tasks/in_review/TASK-TC-DESC*.md tasks/backlog/
git mv tasks/in_progress/TASK-D3A1*.md tasks/backlog/
git mv tasks/in_progress/TASK-FIX-A7D3*.md tasks/backlog/

# Move review_complete-status tasks to review_complete/
git mv tasks/in_review/TASK-5E55*.md tasks/review_complete/
git mv tasks/in_review/TASK-895A*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-3666*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-9AC5*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-B601*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-C4D0*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-D4A7*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-DF4A*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FB-regression*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FB05*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FB20*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-FMT*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-PD02*.md tasks/review_complete/
git mv tasks/in_review/TASK-REV-TI01*.md tasks/review_complete/
git mv tasks/in_review/TASK-TMPL-2258*.md tasks/review_complete/
git mv tasks/in_progress/TASK-2E9E*.md tasks/review_complete/
git mv tasks/in_progress/TASK-REV-2658*.md tasks/review_complete/
git mv tasks/in_progress/TASK-REV-426C*.md tasks/review_complete/
git mv tasks/in_progress/TASK-REV-FB19*.md tasks/review_complete/

# Task CL-002: Archive empty feature directories
mkdir -p tasks/archived/features/
git mv tasks/backlog/autobuild-task-work-delegation/ tasks/archived/features/
git mv tasks/backlog/direct-mode-race-fix/ tasks/archived/features/
git mv tasks/backlog/feature-build-cli-native/ tasks/archived/features/
git mv tasks/backlog/feature-build-design-phase-fix/ tasks/archived/features/
git mv tasks/backlog/feature-build-fixes/ tasks/archived/features/
git mv tasks/backlog/feature-build-performance/ tasks/archived/features/
git mv tasks/backlog/feature-build-regression-fix/ tasks/archived/features/
git mv tasks/backlog/feature-plan-schema-fix/ tasks/archived/features/
git mv tasks/backlog/file-tracking-fix/ tasks/archived/features/
git mv tasks/backlog/nested-directory-support/ tasks/archived/features/
git mv tasks/backlog/player-report-harmonization/ tasks/archived/features/
git mv tasks/backlog/preloop-documentation/ tasks/archived/features/
git mv tasks/backlog/quality-gates-integration/ tasks/archived/features/
git mv tasks/backlog/sdk-delegation-fix/ tasks/archived/features/
git mv tasks/backlog/sdk-error-handling/ tasks/archived/features/
git mv tasks/backlog/task-type-expansion/ tasks/archived/features/
git mv tasks/backlog/task-work-performance/ tasks/archived/features/
```

### Wave 2

```bash
# Task CL-003: Consolidate feature-build reviews
mkdir -p tasks/archived/feature-build-reviews/
git mv tasks/backlog/TASK-REV-FB*.md tasks/archived/feature-build-reviews/

# Task CL-004: Move blocked to obsolete
git mv tasks/blocked/TASK-DOC-18F9*.md tasks/obsolete/
git mv tasks/blocked/TASK-EXT-C7C1*.md tasks/obsolete/

# Task CL-005: Remove duplicates
rm tasks/in_progress/TASK-FBP-003-integration-tests.md
rm tasks/backlog/TASK-REV-FMT-feature-build-analysis.md
```

## Verification

After all tasks complete:

```bash
# Should return 0 (no backlog status in in_review)
grep -l "^status: backlog" tasks/in_review/*.md 2>/dev/null | wc -l

# Should return 0 (no review_complete status in in_review)
grep -l "^status: review_complete" tasks/in_review/*.md 2>/dev/null | wc -l

# Should return 0 (no review_complete status in in_progress)
grep -l "^status: review_complete" tasks/in_progress/*.md 2>/dev/null | wc -l

# Should return 0 (blocked directory empty)
ls tasks/blocked/*.md 2>/dev/null | wc -l

# Should return 1 each (no duplicates)
find tasks/ -name "TASK-FBP-003*.md" | wc -l
find tasks/ -name "TASK-REV-FMT*.md" | wc -l
```

## Commit Message

```
chore: cleanup tasks directory structure

- Fix 24 status/directory mismatches
- Archive 17 empty feature directories
- Consolidate 20 obsolete FB review tasks
- Move 2 permanently blocked tasks to obsolete
- Remove 2 duplicate task files

Review: TASK-REV-BL01
Feature: FEAT-CLEANUP
```
