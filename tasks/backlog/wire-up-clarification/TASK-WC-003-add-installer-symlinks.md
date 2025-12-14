---
id: TASK-WC-003
title: Add orchestrator symlinks to installer
status: deleted
created: 2025-12-13T21:00:00Z
updated: 2025-12-13T22:45:00Z
priority: high
tags: [clarification, installer, symlinks, direct, deleted]
complexity: 2
implementation_mode: direct
conductor_workspace: wire-up-clarification-wave1-3
parent_feature: wire-up-clarification
related_review: TASK-REV-CLQ2
deleted_reason: "TASK-REV-CLQ3 decided to use unified subagent pattern - no symlinks needed for clarification"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add orchestrator symlinks to installer

## Description

Update the installation script to create symlinks for the clarification orchestrators (`feature-plan-orchestrator` and `task-review-orchestrator`) in `~/.agentecflow/bin/`. This enables the Python orchestrators to be invoked by slash commands.

## Background

Other commands like `/agent-enhance` and `/template-validate` work because the installer creates symlinks:
```bash
ln -sf "$GUARDKIT_PATH/installer/core/commands/lib/agent_enhance_orchestrator.py" "$HOME/.agentecflow/bin/agent-enhance"
```

The clarification orchestrators exist but don't have symlinks, so they can't be invoked from slash commands.

## Changes Required

### 1. Update install.sh

**File**: `installer/scripts/install.sh`

**Location**: Find the section that creates symlinks for bin/ scripts (around where agent-enhance is symlinked)

**Add**:
```bash
# =============================================================================
# Clarification Orchestrator Symlinks
# =============================================================================

echo "Creating clarification orchestrator symlinks..."

# Feature plan orchestrator
ln -sf "$GUARDKIT_PATH/installer/core/commands/lib/feature_plan_orchestrator.py" "$HOME/.agentecflow/bin/feature-plan-orchestrator"
chmod +x "$HOME/.agentecflow/bin/feature-plan-orchestrator"

# Task review orchestrator
ln -sf "$GUARDKIT_PATH/installer/core/commands/lib/task_review_orchestrator.py" "$HOME/.agentecflow/bin/task-review-orchestrator"
chmod +x "$HOME/.agentecflow/bin/task-review-orchestrator"

echo "  Created: ~/.agentecflow/bin/feature-plan-orchestrator"
echo "  Created: ~/.agentecflow/bin/task-review-orchestrator"
```

### 2. Verify Python Shebang Lines

Ensure both orchestrator files have proper shebang lines:

**File**: `installer/core/commands/lib/feature_plan_orchestrator.py`

**Verify line 1**:
```python
#!/usr/bin/env python3
```

If missing, add it at the very top of the file.

**File**: `installer/core/commands/lib/task_review_orchestrator.py`

**Verify line 1**:
```python
#!/usr/bin/env python3
```

If missing, add it at the very top of the file.

### 3. Update guardkit doctor (Optional)

**File**: `installer/scripts/guardkit` (or wherever `guardkit doctor` is implemented)

**Add checks for new symlinks**:
```bash
# Check clarification orchestrators
check_symlink "$HOME/.agentecflow/bin/feature-plan-orchestrator" "feature-plan-orchestrator"
check_symlink "$HOME/.agentecflow/bin/task-review-orchestrator" "task-review-orchestrator"
```

## Acceptance Criteria

- [ ] install.sh creates symlinks for both orchestrators
- [ ] Symlinks are executable (chmod +x)
- [ ] Both Python files have proper shebang lines
- [ ] Running `ls -la ~/.agentecflow/bin/*orchestrator*` shows both symlinks
- [ ] Running `python3 ~/.agentecflow/bin/feature-plan-orchestrator --help` works
- [ ] Running `python3 ~/.agentecflow/bin/task-review-orchestrator --help` works

## Testing

1. **Fresh Install Test**:
   ```bash
   # Remove existing symlinks
   rm -f ~/.agentecflow/bin/feature-plan-orchestrator
   rm -f ~/.agentecflow/bin/task-review-orchestrator

   # Re-run installer
   ./installer/scripts/install.sh

   # Verify symlinks created
   ls -la ~/.agentecflow/bin/*orchestrator*
   ```

2. **Execution Test**:
   ```bash
   # Test feature-plan orchestrator help
   python3 ~/.agentecflow/bin/feature-plan-orchestrator --help

   # Test task-review orchestrator help
   python3 ~/.agentecflow/bin/task-review-orchestrator --help
   ```

3. **Permission Test**:
   ```bash
   # Should be executable
   ~/.agentecflow/bin/feature-plan-orchestrator --help
   ~/.agentecflow/bin/task-review-orchestrator --help
   ```

## Implementation Notes

- This is a **direct** change to the installer script
- Pattern follows existing symlink creation (e.g., agent-enhance)
- No changes to Python code logic needed
- Test on fresh install and upgrade scenarios
