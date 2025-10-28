---
id: TASK-007
title: "Remove Requirements Library Modules"
created: 2025-10-27
status: backlog
priority: medium
complexity: 3
parent_task: none
subtasks: []
estimated_hours: 1.5
---

# TASK-007: Remove Requirements Library Modules

## Description

Remove Python library modules related to requirements management (feature_generator.py and any EARS/BDD/Epic/Feature modules) from installer/global/commands/lib/, keeping all quality gate implementation.

## Modules to Remove

### Requirements Features
```python
❌ feature_generator.py              # Feature generation from epics
❌ test_feature_generator.py         # Tests for feature generator
❌ epic_*.*                          # Any epic-related modules
❌ requirement_*.*                   # Any requirements-related modules
❌ ears_*.*                          # Any EARS notation modules
❌ bdd_*.*                           # Any BDD-related modules
```

## Modules to Keep

### Quality Gate Implementation
```python
✅ checkpoint_display.py             # Phase 2.6 - Human checkpoints
✅ plan_persistence.py               # Design-first workflow
✅ plan_modifier.py                  # Phase 2.7 - Plan modifications
✅ review_modes.py                   # Quick/full review routing
✅ user_interaction.py               # Checkpoint interactions
✅ upfront_complexity_adapter.py     # Phase 2.7 - Complexity evaluation
✅ plan_markdown_parser.py           # Plan parsing
✅ plan_audit.py                     # Phase 5.5 - Plan validation
```

### Task Management
```python
✅ git_state_helper.py               # Task state management
✅ agent_utils.py                    # Agent coordination
✅ micro_task_workflow.py            # --micro flag implementation
✅ version_manager.py                # Compatibility management
✅ error_messages.py                 # User feedback
✅ visualization.py                  # Progress display
✅ spec_drift_detector.py            # Quality monitoring
```

### Metrics
```python
✅ metrics/__init__.py
✅ metrics/plan_audit_metrics.py
```

## Implementation Steps

### 1. Identify Files to Remove

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait

# Find requirements-related modules
find installer/global/commands/lib -name "*feature*.py"
find installer/global/commands/lib -name "*epic*.py"
find installer/global/commands/lib -name "*requirement*.py"
find installer/global/commands/lib -name "*ears*.py"
find installer/global/commands/lib -name "*bdd*.py"
```

### 2. Check for Import Dependencies

```bash
# Find imports of modules to be removed
grep -r "from.*feature_generator\|import.*feature_generator" \
  installer/global/commands/lib/

# If any found, update those files to remove imports
```

### 3. Remove Files

```bash
cd installer/global/commands/lib

# Remove feature generator
rm -f feature_generator.py
rm -f test_feature_generator.py

# Remove any other requirements modules found in step 1
# (Only if they exist)
```

### 4. Verify No Broken Imports

```bash
# Test Python imports still work
cd installer/global/commands/lib

python3 -c "
import sys
sys.path.insert(0, '.')
from checkpoint_display import *
from plan_persistence import *
from review_modes import *
from git_state_helper import *
from plan_audit import *
from upfront_complexity_adapter import *
print('✅ All imports successful')
"
```

### 5. Update __init__.py

If `__init__.py` exports removed modules, update it:
```python
# Remove lines like:
from .feature_generator import *  # DELETE

# Keep all quality gate exports
from .checkpoint_display import *
from .plan_persistence import *
# etc.
```

## Validation Checklist

### Files Removed
- [ ] feature_generator.py removed (if exists)
- [ ] test_feature_generator.py removed (if exists)
- [ ] All epic/requirement/ears/bdd modules removed (if any)

### Quality Gate Modules Intact
- [ ] checkpoint_display.py present
- [ ] plan_persistence.py present
- [ ] review_modes.py present
- [ ] plan_audit.py present
- [ ] upfront_complexity_adapter.py present
- [ ] All task management modules present

### No Broken Imports
- [ ] Python import test passes
- [ ] No imports of removed modules in remaining files
- [ ] __init__.py updated (if needed)

## Acceptance Criteria

- [ ] All requirements-related modules removed
- [ ] Quality gate modules retained
- [ ] Task management modules retained
- [ ] No broken imports
- [ ] Python import test passes
- [ ] No references to removed modules

## Testing

```bash
# Run import test
cd installer/global/commands/lib
python3 -c "import sys; sys.path.insert(0, '.'); from checkpoint_display import *; print('OK')"

# Search for orphaned references
grep -r "feature_generator" . --include="*.py"
# Should return empty
```

## Related Tasks

- TASK-002: Remove requirements management commands
- TASK-003: Remove requirements-related agents
- TASK-005: Modify task-work.md (agent orchestration)

## Estimated Time

1.5 hours

## Notes

- Check if feature_generator.py actually exists first
- May be fewer files to remove than expected
- Focus on ensuring no broken imports after removal
- Document what was removed in comments or ADR
