---
id: TASK-F5C3
title: "Update CLAUDE.md with agent discovery system documentation"
status: backlog
created: 2025-11-26T09:50:00Z
updated: 2025-11-26T09:50:00Z
priority: medium
tags: [documentation, agent-discovery, claude-md]
complexity: 2
estimated_hours: 1
task_type: implementation
related_tasks: [TASK-E4B2]
dependencies: [TASK-E4B2]
---

# Task: Update CLAUDE.md with Agent Discovery System Documentation

## Problem Statement

The `.claude/CLAUDE.md` file needs to be updated to document the agent discovery system that's now used throughout Taskwright. Currently, it may not explain how discovery metadata works or how agents are selected during task execution.

## Context

After TASK-E4B2 adds discovery metadata to all agents, CLAUDE.md should document:
1. How agent discovery works (based on stack/phase/capabilities/keywords)
2. What discovery metadata means
3. How to add discovery metadata to new agents
4. Examples of agent routing during `/task-work`

## Requirements

### 1. Add Agent Discovery System Section

Add or update the section explaining agent discovery (likely in "Core AI Agents" section):

```markdown
### Agent Discovery System

Taskwright uses AI-powered agent discovery to automatically match tasks to appropriate specialists based on metadata (stack, phase, capabilities, keywords). No hardcoded mappings - discovery is intelligent and extensible.

**How It Works:**
1. **Phase 3**: System analyzes task context (file extensions, keywords, project structure)
2. **Discovery**: Scans all agents for metadata match (stack + phase + keywords)
3. **Selection**: Uses specialist if found, falls back to task-manager if not
4. **Feedback**: Shows which agent selected and why

**Discovery Metadata** (frontmatter in agent files):
- `stack`: [python, react, dotnet, typescript, cross-stack, etc.]
- `phase`: implementation | review | testing | orchestration | debugging
- `capabilities`: List of specific skills
- `keywords`: Searchable terms for matching

**Graceful Degradation**: Agents without metadata are skipped (no errors). System works during migration.
```

### 2. Update Core AI Agents Section

Ensure the agent list shows their roles and discovery metadata:

```markdown
## Core AI Agents

**Orchestration Agents** (cross-stack):
- **task-manager**: Unified workflow management (phase: orchestration)

**Review Agents** (cross-stack):
- **architectural-reviewer**: SOLID/DRY/YAGNI compliance review (phase: review)
- **code-reviewer**: Code quality enforcement (phase: review)
- **software-architect**: System design decisions (phase: review)

**Testing Agents** (cross-stack):
- **test-orchestrator**: Test execution and quality gates (phase: testing)
- **test-verifier**: Test result verification (phase: testing)
- **qa-tester**: QA and testing workflows (phase: testing)

**Debugging Agents** (cross-stack):
- **debugging-specialist**: Systematic debugging and root cause analysis (phase: debugging)
```

### 3. Add Example of Agent Selection

Show how discovery works in practice:

```markdown
**Example: Agent Selection During `/task-work`**

```bash
/task-work TASK-042  # Task involves Python API implementation

# System analyzes:
# - Files: *.py (Python detected)
# - Keywords: "API endpoint", "FastAPI"
# - Phase: Implementation (Phase 3)

# Discovery matches:
# - Stack: python ✓
# - Phase: implementation ✓
# - Capabilities: api, async-patterns, pydantic ✓

# Selected: python-api-specialist (from template or global)
# Fallback: task-manager (if no specialist found)
```
```

## Implementation Approach

**Phase 1: Review Current CLAUDE.md** (15 min)
- Read `.claude/CLAUDE.md` to understand current structure
- Identify where agent discovery section should go
- Check if any outdated agent information exists

**Phase 2: Update Agent Discovery Section** (30 min)
- Add or update "Agent Discovery System" section
- Update "Core AI Agents" list with discovery metadata
- Add example of agent selection during `/task-work`

**Phase 3: Verify Links and References** (15 min)
- Ensure links to agent files are correct
- Update any references to agent routing/selection
- Check that all 7 agents are documented

## Files to Modify

1. `.claude/CLAUDE.md` - Main project instructions file

## Acceptance Criteria

- [ ] CLAUDE.md documents agent discovery system
- [ ] Explanation of discovery metadata (stack, phase, capabilities, keywords)
- [ ] All 7 agents listed with their phases
- [ ] Example of agent selection during `/task-work` provided
- [ ] Clear documentation of graceful degradation (fallback to task-manager)
- [ ] Links to agent files are correct
- [ ] Section placement is logical and easy to find

## References

- **Agent Discovery Guide**: docs/guides/agent-discovery-guide.md
- **Current Agents**: .claude/agents/*.md
- **Related Task**: TASK-E4B2 (adds discovery metadata to agents)

## Success Metrics

When complete:
- ✅ CLAUDE.md accurately documents how agent discovery works
- ✅ Users understand what discovery metadata means
- ✅ Clear guidance on adding discovery metadata to new agents
- ✅ Agent discovery system is well-documented for Taskwright development
