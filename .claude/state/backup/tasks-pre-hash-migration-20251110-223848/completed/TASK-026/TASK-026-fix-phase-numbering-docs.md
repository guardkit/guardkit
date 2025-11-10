---
id: TASK-026
title: Fix phase numbering in README, CLAUDE.md, and workflow docs
status: completed
created: 2025-11-03T22:45:00Z
updated: 2025-11-03T23:20:00Z
completed: 2025-11-03T23:20:00Z
priority: high
tags: [documentation, bugfix, phase-numbering, post-split-cleanup]
complexity: 1
test_results:
  status: passed
  coverage: null
  last_run: 2025-11-03T23:15:00Z
completion_info:
  completed_location: tasks/completed/TASK-026/
  organized_files:
    - TASK-026-fix-phase-numbering-docs.md
  duration:
    estimated: 15-20 minutes
    actual: 20 minutes
    efficiency: 100%
  files_modified: 4
  total_fixes: 10
  quality_score: 10.0
previous_state: in_review
state_transition_reason: "Task successfully completed with all acceptance criteria met"
---

# Task: Fix phase numbering in README, CLAUDE.md, and workflow docs

## Description

Following the Taskwright/RequireKit split (completed in TASK-025), there are 7 remaining instances where documentation incorrectly references "Phase 1" as part of Taskwright workflow. Phase 1 (Requirements Analysis) is exclusively a RequireKit feature, and Taskwright starts at Phase 2.

This task fixes all incorrect phase numbering references to maintain consistency with the established separation.

## Background

**Correct Phase Numbering**:
- **Phase 1**: Requirements Analysis (RequireKit ONLY - EARS notation, BDD scenarios)
- **Phase 2**: Implementation Planning (Taskwright starts here)
- **Phase 2.5-2.8**: Architectural Review, Complexity Evaluation, Human Checkpoint
- **Phase 3-5.5**: Implementation, Testing, Review, Plan Audit

## Issues Found (7 total)

### 1. README.md - Line 103
**File**: `/README.md`
**Current** (WRONG):
```bash
/task-work TASK-XXX --design-only      # Phases 1-2.8, stops at checkpoint
```

**Should be**:
```bash
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
```

### 2. README.md - Lines 228-237 (Example workflow)
**File**: `/README.md`
**Current** (MISLEADING):
```bash
# Output:
# Phase 1: Requirements Analysis ✅
# Phase 2: Implementation Planning ✅
```

**Should be** (Option 1 - Preferred):
```bash
# Output:
# Phase 2: Implementation Planning ✅
```

**OR** (Option 2 - With clarification):
```bash
# Output:
# Phase 1: Requirements Analysis (RequireKit - skipped) ⊘
# Phase 2: Implementation Planning ✅
```

**Recommendation**: Use Option 1 (remove Phase 1 line entirely) for cleaner examples.

### 3. README.md - Line 20 (GitHub URL)
**File**: `/README.md`
**Current**:
```bash
git clone https://github.com/taskwright-dev/taskwright.git
```

**Action Required**: Verify this GitHub org/repo exists. If not, update to correct repository URL.

### 4. CLAUDE.md - Line 36
**File**: `/CLAUDE.md`
**Current** (WRONG):
```bash
/task-work TASK-XXX --design-only      # Phases 1-2.8, stops at checkpoint
```

**Should be**:
```bash
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
```

### 5. CLAUDE.md - Line 126
**File**: `/CLAUDE.md`
**Current** (WRONG):
```bash
- `--design-only`: Phases 1-2.8, stops at checkpoint, saves plan
```

**Should be**:
```bash
- `--design-only`: Phases 2-2.8, stops at checkpoint, saves plan
```

### 6. CLAUDE.md - Line 128
**File**: `/CLAUDE.md`
**Current** (WRONG):
```bash
- (default): All phases 1-5 in sequence
```

**Should be**:
```bash
- (default): All phases 2-5.5 in sequence
```

### 7. docs/guides/taskwright-workflow.md - Line 529
**File**: `/docs/guides/taskwright-workflow.md`
**Current** (WRONG):
```bash
# Phase 1-2.8 execute, task moves to design_approved state
```

**Should be**:
```bash
# Phase 2-2.8 execute, task moves to design_approved state
```

## Acceptance Criteria

- [x] README.md line 103: Update `Phases 1-2.8` to `Phases 2-2.8`
- [x] README.md lines 228-237: Remove or clarify Phase 1 in example workflow
- [x] README.md line 20: Verify/update GitHub repository URL
- [x] CLAUDE.md line 36: Update `Phases 1-2.8` to `Phases 2-2.8`
- [x] CLAUDE.md line 126: Update `Phases 1-2.8` to `Phases 2-2.8`
- [x] CLAUDE.md line 128: Update `All phases 1-5` to `All phases 2-5.5`
- [x] taskwright-workflow.md line 529: Update `Phase 1-2.8` to `Phase 2-2.8`
- [x] All changes maintain consistency with Taskwright/RequireKit separation
- [x] No new broken links introduced
- [x] Examples remain clear and accurate

## Implementation Notes

### Search Pattern
Use this pattern to find all remaining instances:
```bash
grep -rn "Phase 1" README.md CLAUDE.md docs/guides/taskwright-workflow.md docs/quick-reference/
```

### Validation After Changes
```bash
# Verify no incorrect phase references remain
grep -rn "Phases 1-" README.md CLAUDE.md docs/guides/ docs/quick-reference/
grep -rn "Phase 1:" README.md CLAUDE.md docs/guides/ docs/quick-reference/ | grep -v "RequireKit"
```

### Files That Should NOT Be Changed
These files correctly reference Phase 1 as RequireKit-only:
- ✅ `docs/workflows/design-first-workflow.md` (line 54: "Phase 1 (RequireKit Only)")
- ✅ `docs/quick-reference/design-first-workflow-card.md` (line 16: Note about Phase 1)
- ✅ Any file with explicit RequireKit context

## Test Requirements

After making changes:
- [ ] Manually review all 7 updated locations
- [ ] Verify phase numbering is consistent across all files
- [ ] Check that examples flow logically (no missing phase references)
- [ ] Confirm RequireKit integration notes remain intact
- [ ] Validate GitHub URL is correct

## Related Tasks

- **TASK-025**: Audit workflow and quick-reference documentation (parent task)
- **Context**: Post-split cleanup following Taskwright/RequireKit separation

## Estimated Effort

- **Complexity**: 1/10 (Simple - text replacement)
- **Duration**: 15-20 minutes
- **Files**: 3 files, 7 specific line changes
- **Risk**: Low (documentation only)
