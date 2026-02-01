---
id: TASK-REV-F4A1
title: Analyze feature autobuild error and fix FEAT-0F4A setup
status: review_complete
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 3
  decision: implement_option_a
  report_path: .claude/reviews/TASK-REV-F4A1-review-report.md
  completed_at: 2026-02-01T12:00:00Z
task_type: review
created: 2026-02-01T11:30:00Z
updated: 2026-02-01T11:30:00Z
priority: high
tags: [autobuild, feature-orchestration, graphiti-refinement]
complexity: 4
decision_required: true
---

# Task: Analyze Feature AutoBuild Error and Fix FEAT-0F4A Setup

## Problem Statement

When running:
```bash
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature TASK-GR3-001 --verbose --max-turns 15
```

The system returns:
```
Feature not found: Feature file not found: TASK-GR3-001
Searched in: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/features
Create feature with: /feature-plan "your feature description"
```

## Root Cause Analysis

### Issue 1: Task ID Used Instead of Feature ID
The command `guardkit autobuild feature TASK-GR3-001` passes a **task ID** to the feature orchestrator, but it expects a **feature ID** (e.g., `FEAT-0F4A`).

**Evidence:**
- `TASK-GR3-001` is a task file at: `tasks/backlog/graphiti-refinement-phase2/TASK-GR3-001-implement-feature-detector.md`
- The feature ID for this work is `FEAT-0F4A` (documented in `IMPLEMENTATION-GUIDE.md` line 3)

### Issue 2: Missing Feature YAML File
Even if the correct feature ID were used, `FEAT-0F4A.yaml` does **not exist** in `.guardkit/features/`.

**Existing feature files:**
- FEAT-4048.yaml
- FEAT-4C15.yaml
- FEAT-FC-001.yaml
- FEAT-FMT.yaml
- FEAT-GE.yaml
- FEAT-GI-DOC.yaml
- FEAT-GI.yaml
- FEAT-GR-MVP.yaml
- FEAT-SEC.yaml

**Missing:** `FEAT-0F4A.yaml`

### Issue 3: Feature File Not Created During Planning
The graphiti-refinement-phase2 feature was planned manually (via `/feature-plan` or direct creation), but the corresponding YAML feature file was never generated in `.guardkit/features/`.

## Required Actions

### Option A: Create Feature YAML File (Recommended)
Create `FEAT-0F4A.yaml` in `.guardkit/features/` with the proper structure to register the 44 tasks in the graphiti-refinement-phase2 backlog.

**Tasks to register:**
- Wave 1 (GR-003): TASK-GR3-001 through TASK-GR3-008 (8 tasks)
- Wave 1 (GR-004): TASK-GR4-001 through TASK-GR4-009 (9 tasks)
- Wave 2 (GR-005): TASK-GR5-001 through TASK-GR5-010 (10 tasks)
- Wave 3 (GR-006): TASK-GR6-001 through TASK-GR6-014 (14 tasks)
- **Total: 41 tasks**

### Option B: Use Task-Level AutoBuild
Instead of feature-level orchestration, run task-level autobuild:
```bash
guardkit autobuild task TASK-GR3-001 --verbose --max-turns 15
```

### Option C: Re-run /feature-plan
Re-run the feature planning process to generate proper feature YAML:
```bash
/feature-plan "Graphiti Refinement Phase 2"
```

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Feature YAML file created at `.guardkit/features/FEAT-0F4A.yaml`
- [ ] All 41 tasks properly registered in the feature file
- [ ] Wave dependencies captured (Wave 1 parallel, Wave 2 sequential, Wave 3 sequential)
- [ ] Command `guardkit autobuild feature FEAT-0F4A` runs without "Feature not found" error
- [ ] Documentation updated if needed

## Technical Context

### Feature Loader Logic (feature_loader.py)
- Line 389: `FEATURES_DIR = ".guardkit/features"`
- Lines 425-434: Searches for `{feature_id}.yaml` then `.yml`
- Raises `FeatureNotFoundError` if neither exists

### Feature Orchestrator (feature_orchestrator.py)
- Line 279: Sets features_dir to `.guardkit/features`
- Lines 425-429: Calls `FeatureLoader.load_feature(feature_id)`

### Correct Command Usage
```bash
# Feature-level (requires FEAT-*.yaml file)
guardkit autobuild feature FEAT-0F4A --verbose

# Task-level (works directly with task files)
guardkit autobuild task TASK-GR3-001 --verbose
```

## Files to Examine

- `tasks/backlog/graphiti-refinement-phase2/IMPLEMENTATION-GUIDE.md` - Feature structure
- `tasks/backlog/graphiti-refinement-phase2/README.md` - Feature description
- `.guardkit/features/FEAT-GR-MVP.yaml` - Reference for feature YAML structure
- `guardkit/orchestrator/feature_loader.py` - Feature loading logic
- `guardkit/orchestrator/feature_orchestrator.py` - Orchestration logic

## Recommendation

**Implement Option A**: Create the `FEAT-0F4A.yaml` file by:
1. Using `FEAT-GR-MVP.yaml` as a template
2. Registering all 41 tasks with proper wave groupings
3. Setting up parallel execution for Wave 1 tracks A and B
4. Configuring sequential execution for Waves 2 and 3

This preserves the existing task structure and enables feature-level orchestration.
