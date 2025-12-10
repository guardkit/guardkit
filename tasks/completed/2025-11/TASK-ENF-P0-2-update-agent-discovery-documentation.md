---
id: TASK-ENF-P0-2
title: Update agent discovery documentation with local agent scanning
status: completed
created: 2025-11-27T16:40:00Z
updated: 2025-11-27T18:00:00Z
completed: 2025-11-27T18:00:00Z
priority: high
tags: [documentation, agent-discovery, phase-0]
task_type: implementation
epic: agent-invocation-enforcement
feature: null
requirements: []
dependencies: [TASK-ENF-P0-1]
complexity: 3
effort_estimate: 1-2 hours
related_to: TASK-REV-9A4E
---

# TASK-ENF-P0-2: Update Agent Discovery Documentation

## Context

TASK-ENF-P0-1 fixed agent discovery to scan `.claude/agents/` with explicit precedence rules (Local > User > Global > Template). The documentation must be updated to reflect this critical change.

**Discovery**: TASK-REV-9A4E (Architectural Review)
**Implementation**: TASK-ENF-P0-1 (Agent Discovery Fix)

---

## Objective

Update `docs/guides/agent-discovery-guide.md` to:
1. Document `.claude/agents/` scanning as highest priority source
2. Explain precedence rules with clear examples
3. Add troubleshooting guide for common discovery issues
4. Include discovery flow diagram showing all 4 sources

---

## Scope

### Files to Update

**Primary**:
- `docs/guides/agent-discovery-guide.md`

**Secondary** (if references need updating):
- `CLAUDE.md` (Agent Discovery System section)
- `installer/core/commands/task-work.md` (agent selection references)

---

## Requirements

### FR1: Document Local Agent Scanning

**Add Section**: "Agent Sources and Discovery Order"

**Content**:
```markdown
## Agent Sources and Discovery Order

The agent discovery system scans 4 sources in priority order:

1. **Local** (`.claude/agents/`) - **Highest Priority** ← NEW
   - Created by `taskwright init <template>`
   - Project-specific customizations
   - **Always takes precedence** over all other sources

2. **User** (`~/.agentecflow/agents/`)
   - User's personal agent library
   - Cross-project customizations
   - Overrides global agents

3. **Global** (`installer/core/agents/`)
   - Canonical agent definitions
   - System defaults
   - Fallback for missing local/user

4. **Template** (`installer/core/templates/*/agents/`)
   - Source definitions before initialization
   - Only used if agent not found elsewhere
   - Rarely invoked (templates copy to local on init)

### Precedence Rule

**When duplicate agent names exist**: Local > User > Global > Template

The first agent found (highest priority) is used, and duplicates from lower priority sources are ignored.
```

---

### FR2: Add Precedence Examples

**Add Section**: "Precedence Examples"

**Content** (5 examples from review report Appendix C):
1. Local agent overrides global
2. User agent overrides global
3. Local overrides both user and global
4. Fallback to global when local missing
5. Fallback to task-manager when no match

---

### FR3: Add Discovery Flow Diagram

**Add Section**: "Discovery Flow Diagram"

**Content**: Mermaid or ASCII diagram showing:
- 4-phase scanning process
- Precedence-based duplicate removal
- Ranking by relevance
- Fallback to task-manager

**Example** (from review report):
```
┌────────────────────────────────────────────────┐
│         Agent Discovery System                 │
├────────────────────────────────────────────────┤
│  1. Scan Local (.claude/agents/) ← HIGHEST     │
│  2. Scan User (~/.agentecflow/agents/)         │
│  3. Scan Global (installer/core/agents/)     │
│  4. Scan Template (templates/*/agents/)        │
│  5. Remove duplicates (keep highest priority)  │
│  6. Rank by relevance (stack + phase + keys)   │
│  7. Return best match or task-manager          │
└────────────────────────────────────────────────┘
```

---

### FR4: Add Troubleshooting Guide

**Add Section**: "Troubleshooting Discovery Issues"

**Common Issues**:

1. **Template agents not found**
   - Symptom: Agent not discovered after `taskwright init`
   - Cause: `.claude/agents/` directory missing or empty
   - Solution: Verify template initialization completed successfully

2. **Wrong agent selected**
   - Symptom: Global agent used instead of local customization
   - Cause: Local agent has different name or missing metadata
   - Solution: Check local agent frontmatter (stack, phase, capabilities, keywords)

3. **task-manager used instead of specialist**
   - Symptom: Fallback agent invoked when specialist expected
   - Cause: No agent matches stack/phase/keywords
   - Solution: Verify agent metadata matches task requirements

---

### FR5: Update Existing Discovery Pseudo-Code

**Current Code** (BROKEN):
```python
def discover_agents(phase, stack, keywords):
    # 1. Scan global agents
    global_agents = scan("installer/core/agents/*.md")

    # 2. Scan template agents (TEMPLATES, not initialized)
    template_agents = scan("installer/core/templates/*/agents/*.md")

    # 3. Scan user agents
    user_agents = scan("~/.agentecflow/agents/*.md")

    # ❌ MISSING: .claude/agents/ (where template-init copies local agents)
```

**Updated Code** (FIXED):
```python
def discover_agents(phase, stack, keywords):
    agent_sources = {}  # name -> (agent_data, source, priority)

    # 1. Scan local agents (HIGHEST PRIORITY) ← NEW
    local_agents = scan(".claude/agents/*.md")
    for agent in local_agents:
        agent_sources[agent.name] = (agent, "local", PRIORITY_LOCAL)

    # 2. Scan user agents
    user_agents = scan("~/.agentecflow/agents/*.md")
    for agent in user_agents:
        if agent.name not in agent_sources:  # Only add if not already found
            agent_sources[agent.name] = (agent, "user", PRIORITY_USER)

    # 3. Scan global agents
    global_agents = scan("installer/core/agents/*.md")
    for agent in global_agents:
        if agent.name not in agent_sources:
            agent_sources[agent.name] = (agent, "global", PRIORITY_GLOBAL)

    # 4. Scan template agents (lowest priority)
    template_agents = scan("installer/core/templates/*/agents/*.md")
    for agent in template_agents:
        if agent.name not in agent_sources:
            agent_sources[agent.name] = (agent, "template", PRIORITY_TEMPLATE)

    # Extract unique agents (duplicates already removed)
    all_agents = [data for data, source, priority in agent_sources.values()]

    # Rank by relevance and return best match
    return rank_and_select(all_agents, phase, stack, keywords)
```

---

## Acceptance Criteria

- [ ] Local agent scanning documented as Phase 1 (highest priority)
- [ ] Precedence rules explained clearly with 5 examples
- [ ] Discovery flow diagram added (Mermaid or ASCII)
- [ ] Troubleshooting section added with common issues
- [ ] Pseudo-code updated to reflect new discovery logic
- [ ] All references to "discovery scans X sources" updated to include local
- [ ] CLAUDE.md updated if it references discovery

---

## Implementation Plan

### Step 1: Update Agent Discovery Guide (1 hour)

**File**: `docs/guides/agent-discovery-guide.md`

**Sections to Add/Update**:
1. Agent Sources and Discovery Order (new)
2. Precedence Examples (new)
3. Discovery Flow Diagram (new)
4. Troubleshooting Guide (new)
5. Discovery pseudo-code (update existing)

### Step 2: Update CLAUDE.md (0.5 hour)

**File**: `CLAUDE.md`

**Section**: "Agent Discovery System"

**Update**: Add note about `.claude/agents/` scanning and precedence

### Step 3: Review for Consistency (0.5 hour)

**Check**:
- All references to discovery consistent
- Examples accurate
- Troubleshooting covers common scenarios
- Diagrams render correctly

---

## Testing Strategy

### Documentation Review
- [ ] Read through updated guide end-to-end
- [ ] Verify all examples are accurate
- [ ] Check that diagrams render correctly
- [ ] Ensure troubleshooting steps work

### User Validation
- [ ] Follow guide as if new user
- [ ] Verify precedence examples match actual behavior
- [ ] Test troubleshooting steps resolve issues

---

## Dependencies

**Depends On**:
- TASK-ENF-P0-1 (Agent Discovery Fix) - Must be implemented first

**Enables**:
- Users understand how discovery works
- Troubleshooting is self-service
- Template workflows are clear

---

## References

- Review Report: .claude/reviews/TASK-REV-9A4E-review-report.md
- Agent Discovery Fix: TASK-ENF-P0-1
- Current Guide: docs/guides/agent-discovery-guide.md

---

**Priority**: HIGH
**Effort**: 1-2 hours
**Depends On**: TASK-ENF-P0-1
