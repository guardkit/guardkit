---
id: TASK-002
title: "Remove Requirements Management Commands"
created: 2025-10-27
status: completed
completed_at: 2025-11-01
priority: high
complexity: 3
parent_task: none
subtasks: []
estimated_hours: 2
actual_hours: 0.5
completion_metrics:
  total_duration: "< 1 hour"
  implementation_time: "30 minutes"
  testing_time: "N/A (deletion task, no code testing required)"
  review_time: "< 5 minutes"
  files_removed: 14
  files_remaining: 9
  acceptance_criteria_met: 4/4
  broken_references_identified: 8
  follow_up_tasks_documented: 4
---

# TASK-002: Remove Requirements Management Commands

## Description

Remove all commands related to requirements management (EARS, BDD, Epic/Feature hierarchy) from guardkit repository, keeping only task-focused workflow commands.

## Context

GuardKit is the "lite" version (formerly Agentecflow Lite) focusing on task workflow with quality gates. Requirements management features (EARS, BDD, epics, features) are being removed to reduce complexity.

## Commands to Remove

### Requirements Management
```bash
❌ gather-requirements.md
❌ formalize-ears.md
❌ generate-bdd.md
```

### Epic/Feature Hierarchy
```bash
❌ epic-create.md
❌ epic-status.md
❌ epic-sync.md
❌ epic-generate-features.md
❌ feature-create.md
❌ feature-status.md
❌ feature-sync.md
❌ feature-generate-tasks.md
```

### PM Tool Integration & Visualization
```bash
❌ task-sync.md (PM tool synchronization)
❌ hierarchy-view.md
❌ portfolio-dashboard.md
```

## Commands to Keep

### Core Task Workflow
```bash
✅ task-create.md (needs modification)
✅ task-work.md (needs modification)
✅ task-complete.md
✅ task-status.md (needs modification)
✅ task-refine.md (needs simplification)
```

### Development Tools
```bash
✅ debug.md
✅ figma-to-react.md
✅ zeplin-to-maui.md
```

## Implementation Steps

### 1. Identify Command Files to Delete

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/kuwait

# Find all requirements-related commands
find installer/core/commands -name "*requirements*.md"
find installer/core/commands -name "*ears*.md"
find installer/core/commands -name "*bdd*.md"
find installer/core/commands -name "*epic*.md"
find installer/core/commands -name "*feature*.md"
find installer/core/commands -name "hierarchy*.md"
find installer/core/commands -name "portfolio*.md"
find installer/core/commands -name "*sync*.md"
```

### 2. Remove Command Files

```bash
# Remove requirements commands
rm -f installer/core/commands/gather-requirements.md
rm -f installer/core/commands/formalize-ears.md
rm -f installer/core/commands/generate-bdd.md

# Remove epic commands
rm -f installer/core/commands/epic-create.md
rm -f installer/core/commands/epic-status.md
rm -f installer/core/commands/epic-sync.md
rm -f installer/core/commands/epic-generate-features.md

# Remove feature commands
rm -f installer/core/commands/feature-create.md
rm -f installer/core/commands/feature-status.md
rm -f installer/core/commands/feature-sync.md
rm -f installer/core/commands/feature-generate-tasks.md

# Remove visualization/sync commands
rm -f installer/core/commands/hierarchy-view.md
rm -f installer/core/commands/portfolio-dashboard.md
rm -f installer/core/commands/task-sync.md
```

### 3. Verify Removal

```bash
# List remaining commands
ls installer/core/commands/*.md

# Expected files:
# - task-create.md
# - task-work.md
# - task-complete.md
# - task-status.md
# - task-refine.md
# - debug.md
# - figma-to-react.md
# - zeplin-to-maui.md
```

## Acceptance Criteria

- [x] All 14 requirements-related command files removed (was 13, task-sync counted separately)
- [x] 9 core task workflow and development commands remain (including mcp-zeplin.md)
- [x] Broken references identified (to be fixed in TASK-004, 005, 006)
- [x] Git status shows all deletions

## Related Tasks

- TASK-003: Remove requirements-related agents
- TASK-004: Modify task-create.md (remove epic/feature frontmatter)
- TASK-005: Modify task-work.md (remove requirements loading)
- TASK-006: Modify task-status.md (remove epic/feature filters)

## Estimated Time

2 hours

## Notes

- This is a pure deletion task - no modifications to remaining files
- File modifications will be handled in separate tasks (TASK-004, 005, 006)
- Keep documentation about what was removed for reference

## Implementation Results

### Files Successfully Removed (14 total)

**Requirements Management (3 files):**
- gather-requirements.md
- formalize-ears.md
- generate-bdd.md

**Epic Management (4 files):**
- epic-create.md
- epic-status.md
- epic-sync.md
- epic-generate-features.md

**Feature Management (4 files):**
- feature-create.md
- feature-status.md
- feature-sync.md
- feature-generate-tasks.md

**PM Tool Integration & Visualization (3 files):**
- hierarchy-view.md
- portfolio-dashboard.md
- task-sync.md

### Files Remaining (9 total)

**Core Task Workflow (5 files):**
- task-create.md
- task-work.md
- task-complete.md
- task-status.md
- task-refine.md

**Development Tools (4 files):**
- debug.md
- figma-to-react.md
- zeplin-to-maui.md
- mcp-zeplin.md

### Broken References Found

The following files contain references to deleted commands (to be fixed in follow-up tasks):

**task-create.md:**
- References to /task-sync (lines 559, 674)
- References to /epic-create (line 694)
- References to /feature-create (line 697)
- References to /epic-status (line 706)

**task-refine.md:**
- Reference to /task-sync (line 499)

**task-status.md:**
- References to /feature-status (line 311)
- References to /epic-status (line 314)

These references will be removed/updated in:
- TASK-004: Modify task-create.md
- TASK-005: Modify task-work.md
- TASK-006: Modify task-status.md
- (task-refine.md will need updating too)

---

## Completion Report

### Summary
**Task**: Remove Requirements Management Commands
**Completed**: 2025-11-01
**Duration**: < 1 hour
**Final Status**: ✅ COMPLETED

### Deliverables
- **Files removed**: 14 command files
- **Files remaining**: 9 core task workflow and development commands
- **Broken references identified**: 8 references across 3 files
- **Follow-up tasks documented**: 4 related tasks (TASK-003, 004, 005, 006)

### Quality Metrics
- ✅ All acceptance criteria met (4/4)
- ✅ All 14 target files successfully removed
- ✅ Verified 9 core files remain intact
- ✅ Broken references documented for follow-up tasks
- ✅ Git status shows all deletions correctly
- ✅ Task state transitions tracked (backlog → in_progress → in_review → completed)

### Impact
This task successfully reduced the complexity of GuardKit by removing requirements management features (EARS, BDD, Epic/Feature hierarchy, PM tool integration) that were moving to the separate require-kit package. The repository now focuses purely on task workflow with quality gates.

**Complexity Reduction:**
- Command count: 23 → 9 (61% reduction)
- Removed features: Requirements management, Epic/Feature hierarchy, PM tool sync, Portfolio visualization

### Lessons Learned

**What went well:**
- Clear task specification made execution straightforward
- Systematic approach (categorize → remove → verify) worked efficiently
- Documentation of broken references helps follow-up tasks
- Actual time (0.5h) was significantly under estimate (2h)

**Challenges faced:**
- Task stated 13 files but actually 14 (task-sync counted separately)
- Task stated 8 remaining files but actually 9 (mcp-zeplin.md not mentioned)
- These minor discrepancies didn't affect execution but highlighted value of verification steps

**Improvements for next time:**
- Could automate broken reference detection with grep/ripgrep
- Could generate a "deletion manifest" showing before/after file counts
- For future similar tasks, consider creating a script to automate the verification

### Follow-up Actions
The following tasks are ready to proceed:
1. **TASK-003**: Remove requirements-related agents
2. **TASK-004**: Modify task-create.md (remove epic/feature frontmatter and references)
3. **TASK-005**: Modify task-work.md (remove requirements loading)
4. **TASK-006**: Modify task-status.md (remove epic/feature filters)

Additionally, task-refine.md will need updating to remove /task-sync reference (line 499).
