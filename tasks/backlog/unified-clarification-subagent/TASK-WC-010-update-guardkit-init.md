---
id: TASK-WC-010
title: Update guardkit init to include agent
status: backlog
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-13T22:45:00Z
priority: medium
tags: [clarification, guardkit-init, infrastructure, wave-3]
complexity: 2
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 3
implementation_mode: direct
conductor_workspace: unified-clarification-wave3-2
dependencies:
  - TASK-WC-005
  - TASK-WC-009
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update guardkit init to Include Agent

## Description

Ensure the `guardkit init` command makes the `clarification-questioner` agent discoverable in initialized projects.

## Investigation Required

First, determine how agents are currently loaded:

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

- [ ] Clarification-questioner agent discoverable after guardkit init
- [ ] Works with all template types (react-typescript, fastapi-python, etc.)
- [ ] Agent works in fresh project initialization
- [ ] Behavior documented in appropriate files

## Testing

1. Run `guardkit init react-typescript` in fresh directory
2. Verify clarification-questioner agent is discoverable
3. Run `/task-work TASK-XXX` → verify Phase 1.6 can invoke agent
4. Test with each template type

## Documentation

If this is a no-op (Scenario A), update documentation to explain:
- Agents are loaded globally
- No per-project agent setup needed
- How to add custom agents if desired
