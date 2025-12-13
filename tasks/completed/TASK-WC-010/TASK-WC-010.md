---
id: TASK-WC-010
title: Update guardkit init to include agent
status: completed
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-13T21:26:51Z
completed: 2025-12-13T23:30:00Z
priority: medium
tags: [clarification, guardkit-init, infrastructure, wave-3, no-op]
complexity: 1
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 3
implementation_mode: direct
conductor_workspace: unified-clarification-wave3-2
dependencies:
  - TASK-WC-005
  - TASK-WC-009
test_results:
  status: not_applicable
  coverage: null
  last_run: null
implementation_note: "NO-OP - Existing infrastructure handles this automatically"
completed_location: tasks/completed/TASK-WC-010/
organized_files: ['TASK-WC-010.md', 'investigation-report.md']
---

# Task: Update guardkit init to Include Agent

## Status: ✅ COMPLETED (NO-OP)

**Finding**: No code changes required. The existing GuardKit installer and initialization infrastructure already handles agent distribution automatically.

## Description

Ensure the `clarification-questioner` agent discoverable in initialized projects.

## Investigation Results

**Scenario A confirmed**: Agents are loaded globally from `~/.agentecflow/agents/`.

### How It Works

**1. Installation Phase** (`installer/scripts/install.sh` line 516):
```bash
# Install core global agents first
if [ -d "$INSTALLER_DIR/core/agents" ] && [ "$(ls -A $INSTALLER_DIR/core/agents)" ]; then
    cp -r "$INSTALLER_DIR/core/agents/"* "$INSTALL_DIR/agents/" 2>/dev/null || true
    print_success "Installed core global agents"
fi
```
**Result**: `installer/core/agents/clarification-questioner.md` → `~/.agentecflow/agents/clarification-questioner.md`

**2. Project Initialization** (`installer/scripts/init-project.sh` lines 210-226):
```bash
# Copy global agents (skip if file exists from template)
for agent_file in "$AGENTECFLOW_HOME/agents"/*.md; do
    if [ -f "$agent_file" ]; then
        local agent_name=$(basename "$agent_file")
        if [ ! -f ".claude/agents/$agent_name" ]; then
            cp "$agent_file" ".claude/agents/$agent_name"
            ((global_agent_count++))
        fi
    fi
done
```
**Result**: `~/.agentecflow/agents/clarification-questioner.md` → `.claude/agents/clarification-questioner.md`

**3. Agent Discovery** (`installer/core/commands/lib/agent_discovery.py` lines 84-88):
```python
# 2. Global user agents (~/.agentecflow/agents/)
home = Path.home()
user_agents = home / ".agentecflow" / "agents"
if user_agents.exists():
    locations.append((user_agents, "user", PRIORITY_USER))
```

**Search Order** (priority 0 = highest):
1. Local (`.claude/agents/`) - Priority 0
2. User (`~/.agentecflow/agents/`) - Priority 2
3. Global (`installer/core/agents/`) - Priority 3
4. Template (`installer/core/templates/*/agents/`) - Priority 4

### Implementation Required

**None**. The existing infrastructure handles this automatically.

### Documentation Updated

Added to `CLAUDE.md` section "Agent Discovery System":
- How agents are installed globally
- How agents are copied during project initialization
- Agent discovery search order and precedence
- How to add custom agents (global, local, or template)

## Original Investigation Plan

~~First, determine how agents are currently loaded:~~

1. **Global agents** (`~/.agentecflow/agents/`):
   - If agents are loaded from here globally, this task may be a no-op
   - The installer (TASK-WC-009) already copies the agent here

2. **Template agents** (`installer/core/templates/*/agents/`):
   - If templates have their own agent directories, the agent may need to be added there

3. **Project agents** (`.claude/agents/`):
   - If projects have local agent directories, determine if this agent should be copied

## Files to Check

```bash
# Check how templates handle agents
ls installer/core/templates/*/agents/

# Check guardkit init script
cat installer/scripts/guardkit-init.sh  # or equivalent

# Check how Task tool discovers agents
grep -r "agentecflow/agents" installer/
```

## Likely Scenarios

### Scenario A: Global Agents (Most Likely)

If the Task tool loads agents from `~/.agentecflow/agents/` globally:

**Action**: This task is a no-op. Document this in CLAUDE.md.

```markdown
## Agent Discovery

Agents are loaded globally from `~/.agentecflow/agents/`.
The clarification-questioner agent is installed there by the installer.
No per-project setup required.
```

### Scenario B: Template Agents

If templates include agent directories that are copied during init:

**Action**: Add clarification-questioner to all templates.

```bash
# For each template
cp installer/core/agents/clarification-questioner.md \
   installer/core/templates/react-typescript/agents/
cp installer/core/agents/clarification-questioner.md \
   installer/core/templates/fastapi-python/agents/
# ... etc
```

### Scenario C: Project-Local Agents

If projects need local copies:

**Action**: Update guardkit init to copy the agent.

```bash
# In guardkit init script
cp ~/.agentecflow/agents/clarification-questioner.md \
   .claude/agents/
```

## Acceptance Criteria

- [x] ✅ Clarification-questioner agent discoverable after guardkit init (existing infrastructure)
- [x] ✅ Works with all template types (global agent copied to all projects)
- [x] ✅ Agent works in fresh project initialization (via init-project.sh lines 210-226)
- [x] ✅ Behavior documented in CLAUDE.md (added agent discovery documentation)
- [x] ✅ Investigation completed and findings documented

## Testing (Verification Steps)

To verify this works correctly:

### 1. Verify Agent Installation
```bash
# After running installer
ls -la ~/.agentecflow/agents/clarification-questioner.md
# Expected: File exists (28 total agents)
```

### 2. Verify Project Initialization
```bash
# Create test directory
mkdir -p /tmp/guardkit-test && cd /tmp/guardkit-test

# Initialize with any template
guardkit init react-typescript

# Verify agent copied
ls -la .claude/agents/clarification-questioner.md
# Expected: File exists
```

### 3. Verify Agent Discovery
```bash
# In initialized project
cd /tmp/guardkit-test

# Create task that triggers clarification
/task-create "Test clarification" complexity:5

# Work on task (should trigger Phase 1.6)
/task-work TASK-XXX --with-questions
# Expected: Clarification questions appear
# Expected: System uses clarification-questioner agent
```

## Documentation

✅ **Completed**: Added to `CLAUDE.md` section "Agent Discovery System":
- How agents are installed globally during installation
- How agents are copied during project initialization
- Agent discovery search order and precedence
- How to add custom agents (global, local, or template)

**See**: `TASK-WC-010-INVESTIGATION.md` for complete analysis
