---
id: TASK-WC-009
title: Update installer to copy new agent
status: completed
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-13T23:15:00Z
completed: 2025-12-13T23:15:00Z
priority: medium
tags: [clarification, installer, infrastructure, wave-3]
complexity: 2
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 3
implementation_mode: direct
conductor_workspace: unified-clarification-wave3-1
dependencies:
  - TASK-WC-005
supersedes:
  - TASK-WC-003
test_results:
  status: passed
  coverage: n/a
  last_run: 2025-12-13T23:15:00Z
---

# Task: Update Installer to Copy New Agent

## Description

Update the GuardKit installer to copy the `clarification-questioner` agent to the user's `~/.agentecflow/agents/` directory during installation.

## File to Modify

`installer/scripts/install.sh`

## Changes Required

### 1. Add Agent Copy Command

Add after the existing agent copy section:

```bash
# Copy clarification-questioner agent
if [ -f "$GUARDKIT_PATH/installer/core/agents/clarification-questioner.md" ]; then
    cp "$GUARDKIT_PATH/installer/core/agents/clarification-questioner.md" \
       "$HOME/.agentecflow/agents/"
    echo "✓ Installed clarification-questioner agent"
else
    echo "⚠ Warning: clarification-questioner.md not found"
fi
```

### 2. Verify Agent Directory Exists

Ensure the agents directory creation includes this agent:

```bash
# Create agents directory if needed
mkdir -p "$HOME/.agentecflow/agents"
```

### 3. Update Installation Summary

Add to the installation summary output:

```bash
echo ""
echo "Installed components:"
echo "  ✓ Core commands"
echo "  ✓ Agent files (including clarification-questioner)"
echo "  ✓ Python libraries"
echo ""
```

## Note on Symlinks

**This task supersedes TASK-WC-003** which proposed adding orchestrator symlinks. Since we're using the subagent pattern, no Python script symlinks are needed for clarification.

The agent file is a markdown file that the Task tool reads directly - no symlink required.

## Verification Steps

After running installer:

```bash
# Verify agent exists
ls -la ~/.agentecflow/agents/clarification-questioner.md

# Verify agent is readable
head -20 ~/.agentecflow/agents/clarification-questioner.md
```

## Acceptance Criteria

- [x] Agent copied during installation
- [x] Agent available at `~/.agentecflow/agents/clarification-questioner.md`
- [x] Installation script idempotent (can run multiple times safely)
- [x] Warning shown if source agent file missing
- [x] Installation summary includes agent

## Implementation Details

**Changes Made:**
1. Added explicit `mkdir -p "$INSTALL_DIR/agents"` to ensure directory exists
2. Added dedicated copy section for clarification-questioner agent with success/warning messages
3. Updated installation summary to mention "including clarification-questioner"
4. Maintained idempotent behavior (safe to run multiple times)

**Files Modified:**
- `installer/scripts/install.sh` (lines 514-530, 1264)

**Commits:**
- `0e5423e` - Implementation of installer changes
- `6dff66e` - Task completion and status update

## Testing

1. Run fresh installation → agent copied
2. Run installation again → no errors, agent still present
3. Delete agent, run installation → agent restored
4. Remove source agent, run installation → warning shown
