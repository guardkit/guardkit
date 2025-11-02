---
id: TASK-018
title: "Support epic:EPIC-XXX Parameter in /task-create Command"
status: backlog
created: 2025-11-02T15:30:00Z
updated: 2025-11-02T15:30:00Z
priority: high
complexity: 4
epic: null
feature: null
requirements: []
related_tasks: []
external_ids:
  jira: null
  linear: null
tags: [epic-hierarchy, task-creation, optional-features]
estimated_hours: 3
---

# TASK-018: Support epic:EPIC-XXX Parameter in /task-create

## Context

**Source**: Product Owner request for optional feature layer in epic hierarchy.

**Current Limitation**: `/task-create` requires `feature:FEAT-XXX` parameter, forcing users to create features even for small epics (3-5 tasks).

**Desired Flexibility**:
```
Epic → Task (simple epics)
Epic → Feature → Task (complex epics)
```

## Problem Statement

For small epics (bug fixes, tech debt, research), creating an intermediate feature layer adds unnecessary overhead:

```bash
# Current (forced ceremony)
/epic-create "Fix Auth Bugs"
/feature-create "Bug Fixes" epic:EPIC-002  # Artificial feature
/task-create "Debug timeout" feature:FEAT-001

# Desired (direct link)
/epic-create "Fix Auth Bugs"
/task-create "Debug timeout" epic:EPIC-002  # Skip feature layer
```

## Objective

Enhance `/task-create` command to accept **either** `epic:EPIC-XXX` **or** `feature:FEAT-XXX` parameter, enabling direct epic-to-task linking for simple epics.

## Implementation Requirements

### 1. Command Parameter Enhancement

**Update command signature**:
```bash
# Option 1: Link to feature (existing)
/task-create "Title" feature:FEAT-XXX

# Option 2: Link to epic directly (NEW)
/task-create "Title" epic:EPIC-XXX

# Validation: Must provide EITHER epic OR feature (not both)
```

### 2. Validation Rules

**XOR Validation**:
- ✅ Must specify EITHER `epic:EPIC-XXX` OR `feature:FEAT-XXX`
- ❌ Cannot specify both epic and feature
- ❌ Cannot specify neither (one is required)

**Epic Validation** (when epic specified):
- ✅ Epic must exist in `docs/epics/`
- ✅ Epic must have status: `active`, `planning`, or `in_progress`
- ❌ Cannot link to completed/cancelled epics

**Feature Validation** (existing behavior):
- ✅ Feature must exist in `docs/features/`
- ✅ Feature must be active
- ✅ Task inherits epic from feature automatically

### 3. Task Metadata Schema

**Add new fields**:
```yaml
---
id: TASK-XXX
title: "Debug session timeout"
epic: EPIC-002        # NEW: Direct epic link (if no feature)
feature: null         # Null if linked to epic directly
parent_type: epic     # NEW: "epic" or "feature"
parent_id: EPIC-002   # NEW: Normalized parent reference
requirements: []      # Can link requirements directly
---
```

### 4. Epic Metadata Updates

**Track direct tasks**:
```yaml
---
id: EPIC-002
title: "Fix Auth Bugs"
features: []                            # Empty if no features
direct_tasks: [TASK-004, TASK-005]     # NEW: Direct task IDs
has_features: false                     # NEW: Hierarchy indicator
organization_pattern: "direct"          # NEW: "direct", "features", "mixed"
task_count: 3
feature_count: 0
---
```

## File Changes

### 1. Command File
**File**: `installer/global/commands/task-create.md`

**Changes**:
- Add `epic:EPIC-XXX` parameter option
- Update examples to show both patterns
- Add validation rules section
- Update output format for epic-linked tasks

### 2. Command Implementation
**File**: `.claude/commands/task-create.md` (if different)

**Changes**:
- Parse `epic:` parameter
- Validate epic OR feature (XOR logic)
- Create task with appropriate metadata
- Update epic's `direct_tasks` array

### 3. Task Template
**File**: Task metadata template

**Changes**:
- Add `parent_type` field
- Add `parent_id` field
- Make `feature` nullable
- Make `epic` nullable (but one required)

## Validation Logic

### Pseudo-code
```python
def validate_task_parameters(epic_id, feature_id):
    # XOR validation
    if epic_id and feature_id:
        raise ValidationError("Cannot specify both epic and feature")

    if not epic_id and not feature_id:
        raise ValidationError("Must specify either epic or feature")

    # Epic validation
    if epic_id:
        epic = load_epic(epic_id)
        if not epic:
            raise ValidationError(f"Epic {epic_id} not found")
        if epic.status not in ['active', 'planning', 'in_progress']:
            raise ValidationError(f"Cannot link to {epic.status} epic")
        return 'epic', epic_id

    # Feature validation (existing)
    if feature_id:
        feature = load_feature(feature_id)
        if not feature:
            raise ValidationError(f"Feature {feature_id} not found")
        return 'feature', feature_id

def create_task(title, epic_id=None, feature_id=None):
    parent_type, parent_id = validate_task_parameters(epic_id, feature_id)

    # Create task metadata
    task = {
        'id': generate_task_id(),
        'title': title,
        'epic': epic_id if parent_type == 'epic' else get_epic_from_feature(feature_id),
        'feature': feature_id if parent_type == 'feature' else None,
        'parent_type': parent_type,
        'parent_id': parent_id,
        'status': 'backlog'
    }

    # Update parent
    if parent_type == 'epic':
        update_epic_direct_tasks(epic_id, task['id'])
    else:
        update_feature_tasks(feature_id, task['id'])

    return task
```

## Output Format

### Epic-Linked Task
```bash
/task-create "Debug session timeout" epic:EPIC-002

# Output:
✅ Task Created: TASK-018

📋 Task Details
Title: Debug session timeout
Epic: EPIC-002 (Fix Auth Bugs)
Feature: None (direct epic link)
Parent Type: epic
Status: backlog

📁 File Location
tasks/backlog/TASK-018-debug-session-timeout.md

🔗 Hierarchy
EPIC-002: Fix Auth Bugs
  └── TASK-018: Debug session timeout [backlog]

Next Steps:
1. Start work: /task-work TASK-018
2. View epic: /epic-status EPIC-002
```

### Feature-Linked Task (Existing)
```bash
/task-create "Implement login" feature:FEAT-001

# Output:
✅ Task Created: TASK-008

📋 Task Details
Title: Implement login
Epic: EPIC-001 (User Management)
Feature: FEAT-001 (Authentication)
Parent Type: feature
Status: backlog

📁 File Location
tasks/backlog/TASK-008-implement-login.md

🔗 Hierarchy
EPIC-001: User Management
  └── FEAT-001: Authentication
        └── TASK-008: Implement login [backlog]
```

## Error Cases

### Both Epic and Feature
```bash
/task-create "Bad task" epic:EPIC-001 feature:FEAT-001

# Error:
❌ Validation Error
Cannot specify both epic and feature parameters.

Usage:
  /task-create "Title" epic:EPIC-XXX
  /task-create "Title" feature:FEAT-XXX

Choose one hierarchy pattern per epic.
```

### Neither Epic nor Feature
```bash
/task-create "Bad task"

# Error:
❌ Validation Error
Must specify either epic or feature parameter.

Usage:
  /task-create "Title" epic:EPIC-XXX  (for simple epics)
  /task-create "Title" feature:FEAT-XXX  (for complex epics)
```

### Invalid Epic
```bash
/task-create "Debug timeout" epic:EPIC-999

# Error:
❌ Validation Error
Epic EPIC-999 not found.

Available epics:
  EPIC-001: User Management (active)
  EPIC-002: Fix Auth Bugs (active)

Use: /epic-create "Title" to create a new epic
```

## Testing Scenarios

### Test 1: Create Epic-Linked Task
```bash
/epic-create "Fix Auth Bugs"
/task-create "Debug timeout" epic:EPIC-002
# Expected: Task created with parent_type=epic
```

### Test 2: Create Feature-Linked Task
```bash
/epic-create "User Management"
/feature-create "Authentication" epic:EPIC-001
/task-create "Implement login" feature:FEAT-001
# Expected: Task created with parent_type=feature
```

### Test 3: Invalid Both Parameters
```bash
/task-create "Bad task" epic:EPIC-001 feature:FEAT-001
# Expected: Error - cannot specify both
```

### Test 4: Invalid Neither Parameter
```bash
/task-create "Bad task"
# Expected: Error - must specify one
```

### Test 5: Invalid Epic ID
```bash
/task-create "Debug timeout" epic:EPIC-999
# Expected: Error - epic not found
```

### Test 6: Completed Epic Rejection
```bash
# Assuming EPIC-003 is completed
/task-create "New task" epic:EPIC-003
# Expected: Error - cannot link to completed epic
```

## Acceptance Criteria

- [ ] `/task-create` accepts `epic:EPIC-XXX` parameter
- [ ] Validation enforces epic XOR feature (not both, not neither)
- [ ] Task metadata includes `parent_type` and `parent_id` fields
- [ ] Epic metadata tracks `direct_tasks` array
- [ ] Error messages are clear and helpful
- [ ] Task files created with correct hierarchy metadata
- [ ] Epic status shows direct tasks when features absent
- [ ] All test scenarios pass
- [ ] Documentation updated with examples
- [ ] Backward compatible with existing feature-based tasks

## Related Work

**require-kit repo**:
- REQ-004: Optional feature layer (parent task)
- Analysis: `docs/research/optional-feature-layer-analysis.md`

**taskwright repo**:
- This task (TASK-018): Command implementation
- Future: `/epic-status` updates to show direct tasks
- Future: `/hierarchy-view` updates for mixed display

## Timeline Estimate

- Command parameter parsing: 0.5 hours
- Validation logic (XOR, epic checks): 1 hour
- Task metadata schema updates: 0.5 hours
- Epic metadata updates: 0.5 hours
- Testing & validation: 0.5 hours

**Total**: ~3 hours

## Notes

- This is the **core command enhancement** for the optional feature layer
- Focus only on `/task-create` command in this task
- Other commands (`/epic-status`, `/hierarchy-view`) will be updated in separate tasks
- Maintains full backward compatibility with existing feature-based workflow
- Enables both simple (epic → task) and complex (epic → feature → task) patterns

## Definition of Done

- [ ] Command accepts `epic:EPIC-XXX` parameter
- [ ] Validation prevents both epic and feature
- [ ] Task metadata includes new fields
- [ ] Epic tracks direct tasks
- [ ] Error messages tested
- [ ] All acceptance criteria met
- [ ] Documentation examples added
- [ ] No breaking changes to existing functionality
