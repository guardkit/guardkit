# Review Report: TASK-REV-F4A1

## Executive Summary

The feature autobuild command fails because:
1. **Incorrect usage**: User passed task ID `TASK-GR3-001` instead of feature ID `FEAT-0F4A`
2. **Missing feature file**: `FEAT-0F4A.yaml` does not exist in `.guardkit/features/`

**Root Cause Confirmed**: The graphiti-refinement-phase2 feature was planned manually without generating the required feature YAML file.

**Recommendation**: Create `FEAT-0F4A.yaml` to register all 41 tasks with proper wave orchestration.

---

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~15 minutes
- **Reviewer**: Claude AI (task-review workflow)

---

## Findings

### Finding 1: Incorrect Command Usage (Confirmed)

**Evidence**:
- User ran: `guardkit autobuild feature TASK-GR3-001`
- Expected: `guardkit autobuild feature FEAT-0F4A`

**Technical Details** (from `feature_loader.py:389-434`):
- Feature loader searches `.guardkit/features/{feature_id}.yaml` or `.yml`
- Task IDs (`TASK-*`) will never match feature file naming convention (`FEAT-*`)
- Error message correctly suggests using `/feature-plan`

**Severity**: User Error (not a bug)

### Finding 2: Missing Feature YAML File (Root Cause)

**Evidence**:
```
Existing features in .guardkit/features/:
├── FEAT-4048.yaml
├── FEAT-4C15.yaml
├── FEAT-FC-001.yaml
├── FEAT-FMT.yaml
├── FEAT-GE.yaml
├── FEAT-GI-DOC.yaml
├── FEAT-GI.yaml
├── FEAT-GR-MVP.yaml  ← Previous phase exists
└── FEAT-SEC.yaml

Missing: FEAT-0F4A.yaml
```

**Cause**: The graphiti-refinement-phase2 feature planning created task files but skipped the feature YAML generation step.

**Severity**: Critical (blocks feature-level autobuild)

### Finding 3: Task Structure is Complete

**Evidence**:
- 41 task files exist in `tasks/backlog/graphiti-refinement-phase2/`
- Tasks have correct metadata:
  - `feature_id: FEAT-0F4A` (present in frontmatter)
  - `sub_feature: GR-003/GR-004/GR-005/GR-006`
  - `wave: 1/2/3`
  - `parallel_group: wave1-gr003, wave1-gr004, etc.`
  - `implementation_mode: task-work/direct`
  - `dependencies: [...]`
- README.md and IMPLEMENTATION-GUIDE.md are comprehensive

**Severity**: No issue (task structure is valid)

### Finding 4: Reference Template Available

**Evidence**:
- `FEAT-GR-MVP.yaml` provides correct feature YAML structure
- Schema documented in `feature_loader.py:46-59`:
  ```yaml
  id: str (required)        # e.g., "FEAT-A1B2"
  name: str (required)      # Human-readable name
  description: str          # Feature description
  tasks: list               # List of task objects
  orchestration: dict       # Parallel execution configuration
  ```

**Benefit**: Can use MVP as template for Phase 2 feature file

---

## Option Analysis

### Option A: Create Feature YAML File (Recommended)

**Description**: Create `FEAT-0F4A.yaml` in `.guardkit/features/` with all 41 tasks registered.

**Effort**: ~30 minutes (scripted generation)

**Pros**:
- Enables feature-level orchestration with wave parallelism
- Preserves existing task structure unchanged
- Matches existing workflow with FEAT-GR-MVP
- Supports Conductor parallel execution (3 recommended workspaces)

**Cons**:
- Requires careful dependency mapping (already documented in IMPLEMENTATION-GUIDE.md)

**Implementation**:
1. Use `FEAT-GR-MVP.yaml` as template
2. Map 41 tasks from `tasks/backlog/graphiti-refinement-phase2/`
3. Configure orchestration parallel_groups matching IMPLEMENTATION-GUIDE.md waves
4. Validate with `guardkit autobuild feature FEAT-0F4A --dry-run`

### Option B: Use Task-Level AutoBuild

**Description**: Run `guardkit autobuild task TASK-XXX` for each task individually.

**Effort**: Immediate (no setup)

**Pros**:
- Works without feature YAML
- Can start immediately

**Cons**:
- No wave-level parallelism
- Must manually track task order and dependencies
- 41 separate autobuild invocations
- Loses feature-level progress tracking

**Use Case**: Quick start on a single task while Option A is prepared

### Option C: Re-run /feature-plan

**Description**: Run `/feature-plan "Graphiti Refinement Phase 2"` to regenerate feature structure.

**Effort**: ~15 minutes

**Pros**:
- Would generate feature YAML automatically

**Cons**:
- May overwrite existing task files with different IDs
- Loses manual refinements to task descriptions
- IMPLEMENTATION-GUIDE.md would be regenerated (possibly losing detail)
- Existing task metadata would not match new generation

**Not Recommended**: Risk of losing existing planning work outweighs benefits

---

## Recommendation

**Implement Option A**: Create `FEAT-0F4A.yaml` manually using:
- `FEAT-GR-MVP.yaml` as template structure
- Task metadata from existing 41 task files
- Wave configuration from `IMPLEMENTATION-GUIDE.md`

**Feature YAML Structure Required**:
```yaml
id: FEAT-0F4A
name: "Graphiti Refinement Phase 2"
description: "..."
status: planned
complexity: 7
estimated_tasks: 41

tasks:
  - id: TASK-GR3-001
    name: "Implement FeatureDetector class"
    file_path: "tasks/backlog/graphiti-refinement-phase2/TASK-GR3-001-implement-feature-detector.md"
    complexity: 4
    dependencies: []
    status: pending
    implementation_mode: task-work
    estimated_minutes: 120
  # ... 40 more tasks

orchestration:
  parallel_groups:
    # Wave 1: GR-003 and GR-004 in parallel
    - - TASK-GR3-001
      - TASK-GR3-002
      - TASK-GR3-003
      # ... (8 tasks from GR-003)
    - - TASK-GR4-001
      - TASK-GR4-002
      # ... (9 tasks from GR-004)
    # Wave 2: GR-005 sequential
    - - TASK-GR5-001
      # ... (10 tasks)
    # Wave 3: GR-006 sequential
    - - TASK-GR6-001
      # ... (14 tasks)
  estimated_duration_minutes: 3840
  recommended_parallel: 3
```

---

## Next Steps

1. Create `FEAT-0F4A.yaml` using the structure above
2. Populate all 41 tasks with correct file_path references
3. Configure parallel_groups matching wave structure
4. Validate with: `guardkit autobuild feature FEAT-0F4A --dry-run`
5. Run: `guardkit autobuild feature FEAT-0F4A --verbose`

---

## Appendix

### Files Examined

- `tasks/backlog/TASK-REV-F4A1-analyze-feature-autobuild-error.md` (review task)
- `tasks/backlog/graphiti-refinement-phase2/README.md` (feature description)
- `tasks/backlog/graphiti-refinement-phase2/IMPLEMENTATION-GUIDE.md` (wave structure)
- `tasks/backlog/graphiti-refinement-phase2/TASK-GR3-001-*.md` (sample task)
- `.guardkit/features/FEAT-GR-MVP.yaml` (reference template)
- `guardkit/orchestrator/feature_loader.py` (feature loading logic)

### Task Count Verification

- GR-003: 8 tasks (TASK-GR3-001 to TASK-GR3-008)
- GR-004: 9 tasks (TASK-GR4-001 to TASK-GR4-009)
- GR-005: 10 tasks (TASK-GR5-001 to TASK-GR5-010)
- GR-006: 14 tasks (TASK-GR6-001 to TASK-GR6-014)
- **Total: 41 tasks** (confirmed)

### Key File Paths

- Feature YAML target: `.guardkit/features/FEAT-0F4A.yaml`
- Feature loader: `guardkit/orchestrator/feature_loader.py:389-434`
- Reference template: `.guardkit/features/FEAT-GR-MVP.yaml`
