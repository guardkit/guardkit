---
id: TASK-018
title: Audit and Reorganize Global vs Template-Specific Agents
status: completed
created: 2025-11-02T00:00:00Z
completed: 2025-11-02T16:11:00Z
priority: high
complexity: 2
estimated_hours: 1
actual_hours: 0.5
tags: [agents, templates, cleanup, bug-fix]
epic: null
feature: installation
dependencies: []
blocks: [TASK-019]
---

# TASK-018: Audit and Reorganize Global vs Template-Specific Agents

## Objective

Audit all agents in `installer/global/agents/` and move stack-specific agents to their respective template directories. This fixes the bug where Python-specific agents are being copied to .NET projects.

## Problem Statement

**Current Issue**:
- `python-mcp-specialist.md` is in `/installer/global/agents/`
- This agent gets copied to ALL projects (including dotnet-microservice)
- Users get irrelevant Python agents in their .NET projects

**Root Cause**:
The installer copies all global agents to every project type, regardless of stack.

## Expected Organization

### Global Agents (Cross-Stack)
These should stay in `installer/global/agents/`:
- `architectural-reviewer.md` - Works across all stacks
- `code-reviewer.md` - Works across all stacks
- `task-manager.md` - Works across all stacks
- `test-orchestrator.md` - Works across all stacks
- `test-verifier.md` - Works across all stacks
- `devops-specialist.md` - Infrastructure (cross-stack)
- `database-specialist.md` - Database design (cross-stack)
- `security-specialist.md` - Security (cross-stack)
- `debugging-specialist.md` - Debugging (cross-stack)
- `build-validator.md` - Build validation (cross-stack)
- `pattern-advisor.md` - Design patterns (cross-stack)
- `complexity-evaluator.md` - Complexity scoring (cross-stack)
- `figma-react-orchestrator.md` - UX design (React-specific but orchestrator)
- `zeplin-maui-orchestrator.md` - UX design (MAUI-specific but orchestrator)

### Template-Specific Agents
These should move to template directories:

**Python Template** (`installer/global/templates/python/agents/`):
- `python-mcp-specialist.md` ← **MOVE THIS**
- `python-api-specialist.md` (already there)
- `python-testing-specialist.md` (already there)
- `python-langchain-specialist.md` (already there)

**React Template** (`installer/global/templates/react/agents/`):
- Already has stack-specific agents ✓

**TypeScript API Template** (`installer/global/templates/typescript-api/agents/`):
- Already has stack-specific agents ✓

**.NET Templates** (maui-*, dotnet-microservice):
- Already have stack-specific agents ✓

## Acceptance Criteria

- [ ] Audit all 15 global agents and categorize (cross-stack vs stack-specific)
- [ ] Move `python-mcp-specialist.md` from global to python template
- [ ] Verify no other stack-specific agents in global directory
- [ ] Test: dotnet-microservice init should NOT include python-mcp-specialist
- [ ] Test: python template init SHOULD include python-mcp-specialist
- [ ] Update documentation if needed

## Implementation Steps

### 1. Audit Current Global Agents

```bash
# List all global agents
ls -1 installer/global/agents/*.md

# Expected to find:
# - python-mcp-specialist.md (NEEDS TO MOVE)
# - All other agents (should be cross-stack)
```

### 2. Move Python MCP Specialist

```bash
# Move the agent
mv installer/global/agents/python-mcp-specialist.md \
   installer/global/templates/python/agents/

# Verify
ls installer/global/templates/python/agents/python-mcp-specialist.md
```

### 3. Verify Template Structure

```bash
# Check python template has all its agents
ls -1 installer/global/templates/python/agents/

# Expected:
# - python-api-specialist.md
# - python-testing-specialist.md
# - python-langchain-specialist.md
# - python-mcp-specialist.md (newly moved)
# - architectural-reviewer.md (template copy)
```

### 4. Test Installation

```bash
# Test dotnet-microservice init
cd /tmp/test-dotnet
taskwright init dotnet-microservice

# Verify NO python-mcp-specialist in agents
ls .claude/agents/ | grep python-mcp
# Should return empty

# Test python init
cd /tmp/test-python
taskwright init python

# Verify python-mcp-specialist IS present
ls .claude/agents/python-mcp-specialist.md
# Should exist
```

## Files to Modify

1. **Move Agent File**:
   - From: `installer/global/agents/python-mcp-specialist.md`
   - To: `installer/global/templates/python/agents/python-mcp-specialist.md`

2. **No Code Changes Required**:
   - The installer already handles template-specific agents correctly
   - See `install.sh:350-358` and `init-project.sh:212-221`

## Testing Strategy

### Unit Test
- Verify file exists in correct location
- Verify file removed from old location

### Integration Test
```bash
# Test 1: .NET project should NOT have python-mcp-specialist
./installer/scripts/install.sh
cd /tmp/test-dotnet
mkdir test-project && cd test-project
~/.agentecflow/scripts/init-project.sh dotnet-microservice

# Verify
if grep -q "python-mcp-specialist" .claude/agents/python-mcp-specialist.md 2>/dev/null; then
    echo "FAIL: Python agent in .NET project"
else
    echo "PASS: No Python agent in .NET project"
fi

# Test 2: Python project SHOULD have python-mcp-specialist
cd /tmp/test-python
mkdir test-project && cd test-project
~/.agentecflow/scripts/init-project.sh python

# Verify
if [ -f .claude/agents/python-mcp-specialist.md ]; then
    echo "PASS: Python agent in Python project"
else
    echo "FAIL: Missing Python agent in Python project"
fi
```

## Definition of Done

- [ ] `python-mcp-specialist.md` moved to python template
- [ ] No other stack-specific agents found in global directory
- [ ] .NET projects do NOT get Python agents
- [ ] Python projects DO get Python agents
- [ ] Documentation updated if needed
- [ ] Tests pass

## Notes

- **Low Risk**: Simple file move operation
- **Quick Fix**: ~30 minutes total
- **High Impact**: Fixes immediate user-facing bug
- **No Breaking Changes**: Existing logic already handles this correctly

## Related Issues

- User reported: "python mcp specialist agent in dotnet-microservice project"
- This is part of the larger cleanup from splitting agentecflow → taskwright + require-kit

---

**Status**: Ready for implementation
**Priority**: HIGH (user-facing bug)
**Estimated Time**: 1 hour
