---
id: TASK-ENF-P0-1
title: Fix agent discovery to scan .claude/agents/ directory
status: completed
created: 2025-11-27T16:35:00Z
updated: 2025-11-27T18:00:00Z
completed: 2025-11-27T18:00:00Z
priority: critical
tags: [agent-discovery, foundation, phase-0, blocking]
task_type: implementation
epic: agent-invocation-enforcement
feature: null
requirements: []
dependencies: []
blocks: [TASK-ENF1, TASK-ENF2, TASK-ENF4, TASK-ENF5]
complexity: 6
effort_estimate: 2-3 hours
related_to: TASK-REV-9A4E
---

# TASK-ENF-P0-1: Fix Agent Discovery - Local Agent Scanning

## Context

**Critical Issue Identified**: TASK-REV-9A4E architectural review revealed that the agent discovery system does NOT scan `.claude/agents/` - the directory where `taskwright init` copies template agents during initialization.

**Impact**:
- Template-generated agents are invisible to discovery
- Enforcement mechanisms (ENF1, ENF4) will generate false positives
- Users will experience task blocking errors with valid template agents
- **ALL enforcement tasks (ENF1, ENF2, ENF4, ENF5) are blocked until this is fixed**

**Discovery**: TASK-REV-9A4E (Architectural Review)
**Review Report**: .claude/reviews/TASK-REV-9A4E-review-report.md

---

## Problem Statement

### Current Behavior (BROKEN)

Agent discovery scans:
1. `installer/core/agents/*.md` (global agents)
2. `installer/core/templates/*/agents/*.md` (template sources, before init)
3. `~/.agentecflow/agents/*.md` (user agents)

**Missing**: `.claude/agents/*.md` (where template-init copies local agents)

### Expected Behavior (FIXED)

Agent discovery should scan in this order with explicit precedence:
1. **`.claude/agents/*.md`** (LOCAL - highest priority) ← **NEW**
2. `~/.agentecflow/agents/*.md` (USER)
3. `installer/core/agents/*.md` (GLOBAL)
4. `installer/core/templates/*/agents/*.md` (TEMPLATE - lowest priority)

**Precedence Rule**: Local > User > Global > Template

When multiple agents exist with the same name, keep only the highest priority source.

---

## Objective

Fix the agent discovery system to:
1. Scan `.claude/agents/` directory as highest priority source
2. Implement explicit precedence rules for duplicate agents
3. Remove duplicates keeping highest priority source
4. Log selected agent source for debugging
5. Ensure template-initialized agents are immediately discoverable

---

## Scope

### In Scope

**Files to Modify**:
- `installer/core/commands/lib/agent_discovery.py` (primary implementation)
- Unit tests: `tests/test_agent_discovery.py`
- Integration tests: Template initialization → discovery verification

**Functionality**:
- Add `.claude/agents/` scanning as Phase 1 (highest priority)
- Implement precedence-based duplicate removal
- Add source path logging
- Handle missing `.claude/agents/` directory gracefully

### Out of Scope

- Modifying template-init command (separate task: TASK-ENF-P0-3)
- Updating documentation (separate task: TASK-ENF-P0-2)
- Modifying agent-enhance command (separate task: TASK-ENF-P0-4)
- Implementing enforcement mechanisms (blocked until this completes)

---

## Requirements

### FR1: Scan Local Agents Directory

**Priority**: P0 (Critical)

**Requirement**: Discovery system MUST scan `.claude/agents/` directory

**Implementation**:
```python
# Phase 1: Scan local agents (HIGHEST PRIORITY)
local_agent_dir = os.path.join(os.getcwd(), ".claude", "agents")
if os.path.exists(local_agent_dir):
    local_agents = glob(os.path.join(local_agent_dir, "*.md"))
    for agent_file in local_agents:
        agent = parse_agent(agent_file)
        if agent.name not in agent_sources:
            agent_sources[agent.name] = (agent, "local", PRIORITY_LOCAL)
```

**Acceptance Criteria**:
- [ ] Discovery scans `.claude/agents/*.md`
- [ ] Handles missing directory gracefully (no error if doesn't exist)
- [ ] Parses agent metadata from local files

---

### FR2: Implement Precedence Rules

**Priority**: P0 (Critical)

**Requirement**: When duplicate agent names exist, keep highest priority source

**Precedence Order**:
1. **Local** (`.claude/agents/`) - Priority: 1 (highest)
2. **User** (`~/.agentecflow/agents/`) - Priority: 2
3. **Global** (`installer/core/agents/`) - Priority: 3
4. **Template** (`installer/core/templates/*/agents/`) - Priority: 4 (lowest)

**Implementation**:
```python
# Priority constants
PRIORITY_LOCAL = 1    # Highest
PRIORITY_USER = 2
PRIORITY_GLOBAL = 3
PRIORITY_TEMPLATE = 4  # Lowest

# Store agents with precedence
agent_sources = {}  # name -> (agent_data, source, priority)

# When adding agent, only add if not already found (higher priority exists)
if agent.name not in agent_sources:
    agent_sources[agent.name] = (agent, source, priority)
```

**Acceptance Criteria**:
- [ ] Local agents override user/global/template agents with same name
- [ ] User agents override global/template agents
- [ ] Global agents override template agents
- [ ] First-found wins (highest priority source)

---

### FR3: Log Selected Agent Source

**Priority**: P1 (High)

**Requirement**: Log which agent source was selected for debugging

**Implementation**:
```python
if ranked:
    best_match = ranked[0]
    source = next(s for n, (a, s, p) in agent_sources.items() if a == best_match)
    logger.info(f"Agent selected: {best_match.name} (source: {source})")
    return best_match
else:
    logger.info("No matching agent found, using task-manager (fallback)")
    return "task-manager"
```

**Acceptance Criteria**:
- [ ] Log message includes agent name and source
- [ ] Log level: INFO (visible by default)
- [ ] Format: "Agent selected: {name} (source: {source})"

---

### FR4: Handle Missing Directory Gracefully

**Priority**: P1 (High)

**Requirement**: If `.claude/agents/` doesn't exist, continue discovery without error

**Implementation**:
```python
# Check if directory exists before scanning
local_agent_dir = os.path.join(os.getcwd(), ".claude", "agents")
if os.path.exists(local_agent_dir):
    # Scan local agents
    ...
else:
    logger.debug(".claude/agents/ not found, skipping local agent scan")
```

**Acceptance Criteria**:
- [ ] No error if `.claude/agents/` doesn't exist
- [ ] Debug log message if directory missing
- [ ] Discovery continues with remaining sources

---

### FR5: Maintain Backward Compatibility

**Priority**: P1 (High)

**Requirement**: Existing discovery behavior preserved when `.claude/agents/` empty

**Acceptance Criteria**:
- [ ] Projects without local agents work unchanged
- [ ] Discovery still finds global/user agents
- [ ] Fallback to task-manager still works

---

## Implementation Plan

### Phase 1: Update Discovery Function (1-1.5 hours)

**File**: `installer/core/commands/lib/agent_discovery.py`

**Changes**:
1. Add priority constants
2. Change agent storage from list to dict (name → (agent, source, priority))
3. Add Phase 1: Scan `.claude/agents/` with PRIORITY_LOCAL
4. Update Phases 2-4 to check for duplicates before adding
5. Add source logging when agent selected

**Example Structure**:
```python
def discover_agents(phase: str, stack: str, keywords: list) -> Agent:
    """Discover agents with local > user > global > template precedence"""

    agent_sources = {}  # name -> (agent_data, source, priority)

    # Priority levels
    PRIORITY_LOCAL = 1
    PRIORITY_USER = 2
    PRIORITY_GLOBAL = 3
    PRIORITY_TEMPLATE = 4

    # Phase 1: Scan local agents (.claude/agents/)
    local_dir = os.path.join(os.getcwd(), ".claude", "agents")
    if os.path.exists(local_dir):
        for agent_file in glob(os.path.join(local_dir, "*.md")):
            agent = parse_agent(agent_file)
            if agent.name not in agent_sources:
                agent_sources[agent.name] = (agent, "local", PRIORITY_LOCAL)

    # Phase 2: Scan user agents (~/.agentecflow/agents/)
    # ... (only add if not already found)

    # Phase 3: Scan global agents
    # ... (only add if not already found)

    # Phase 4: Scan template agents
    # ... (only add if not already found)

    # Extract unique agents
    all_agents = [data for data, source, priority in agent_sources.values()]

    # Filter and rank
    matched = filter_by_criteria(all_agents, phase, stack, keywords)
    ranked = rank_by_relevance(matched)

    # Return best match with source logging
    if ranked:
        best_match = ranked[0]
        source = next(s for n, (a, s, p) in agent_sources.items() if a == best_match)
        logger.info(f"Agent selected: {best_match.name} (source: {source})")
        return best_match
    else:
        logger.info("No match found, using task-manager (fallback)")
        return "task-manager"
```

---

### Phase 2: Add Unit Tests (0.5-1 hour)

**File**: `tests/test_agent_discovery.py`

**Test Cases**:

1. **Test Local Agent Discovery**
   ```python
   def test_discover_local_agents():
       # Given: .claude/agents/test-specialist.md exists
       # When: discover_agents() called
       # Then: test-specialist found from local source
   ```

2. **Test Local Overrides Global**
   ```python
   def test_local_agent_overrides_global():
       # Given: Both local and global have "react-state-specialist"
       # When: discover_agents(stack="react")
       # Then: Local agent selected, not global
   ```

3. **Test Precedence Chain**
   ```python
   def test_precedence_local_user_global_template():
       # Given: Agent exists in all 4 sources
       # When: discover_agents()
       # Then: Local agent selected (highest priority)
   ```

4. **Test Missing Local Directory**
   ```python
   def test_missing_local_directory_graceful():
       # Given: .claude/agents/ doesn't exist
       # When: discover_agents()
       # Then: No error, continues with user/global agents
   ```

5. **Test Source Logging**
   ```python
   def test_agent_source_logged():
       # Given: Local agent exists
       # When: discover_agents()
       # Then: Log contains "Agent selected: X (source: local)"
   ```

---

### Phase 3: Integration Testing (0.5 hour)

**Scenario 1: Template Initialization**
```bash
# 1. Initialize react-typescript template
taskwright init react-typescript

# 2. Verify agents copied to .claude/agents/
ls .claude/agents/react-state-specialist.md  # Should exist

# 3. Create React task
/task-create "Test local agent discovery" stack:react

# 4. Run task
/task-work TASK-XXX

# 5. Verify local agent selected (check logs)
# Expected: "Agent selected: react-state-specialist (source: local)"
```

**Scenario 2: Local Agent Precedence**
```bash
# 1. Initialize template (creates local agent)
taskwright init python

# 2. Modify local agent (add custom capability)
echo "# Custom modification" >> .claude/agents/python-api-specialist.md

# 3. Run task
/task-work TASK-XXX

# 4. Verify local agent used, not global
# Expected: Custom modification reflected in agent behavior
```

---

## Acceptance Criteria

### Functional Requirements

- [ ] Discovery scans `.claude/agents/` as Phase 1 (highest priority)
- [ ] Precedence rules implemented: Local > User > Global > Template
- [ ] Duplicate agents removed, keeping highest priority source
- [ ] Agent source logged on selection
- [ ] Missing `.claude/agents/` handled gracefully (no error)
- [ ] Backward compatibility maintained (existing projects work)

### Testing Requirements

- [ ] All unit tests pass (5 new tests)
- [ ] Integration test: Template init → discovery verification
- [ ] Integration test: Local agent precedence over global
- [ ] No regressions in existing discovery behavior

### Code Quality

- [ ] Code follows existing discovery patterns
- [ ] Logging clear and actionable
- [ ] Error handling for edge cases
- [ ] Comments explain precedence logic

---

## Testing Strategy

### Unit Tests
```bash
pytest tests/test_agent_discovery.py -v
```

**Coverage Target**: 100% of new code

### Integration Tests
```bash
# Test 1: Template initialization
./tests/integration/test_template_agent_discovery.sh

# Test 2: Local agent precedence
./tests/integration/test_local_agent_precedence.sh
```

### Manual Testing
```bash
# Real-world scenario: Initialize template and run task
taskwright init react-typescript
/task-create "Test feature" stack:react
/task-work TASK-XXX
# Verify local agent selected in logs
```

---

## Success Metrics

**Primary Metric**: Template agents discoverable immediately after initialization
- Target: 100% of template-initialized agents found by discovery

**Secondary Metrics**:
- Local agent precedence: 100% correct (local always wins)
- No false negatives: 0% missing agents that should be found
- Backward compatibility: 100% of existing projects work unchanged

---

## Dependencies

### Blocked By
- None (this is the foundation task)

### Blocks
- TASK-ENF1 (Pre-Report Validation) - Depends on discovery finding local agents
- TASK-ENF2 (Agent Invocation Tracking) - Enhanced tracking needs source paths
- TASK-ENF4 (Phase Gate Checkpoints) - Gates validate discovered agents
- TASK-ENF5-v2 (Dynamic Discovery) - Table redesign assumes discovery works

---

## Risks & Mitigation

### Risk 1: Breaking Existing Discovery

**Probability**: Low
**Impact**: High
**Mitigation**:
- Extensive unit tests
- Integration tests with existing projects
- Backward compatibility verification

### Risk 2: Performance Impact

**Probability**: Low
**Impact**: Low
**Mitigation**:
- Scanning `.claude/agents/` is fast (typically <10 files)
- Caching can be added later if needed

### Risk 3: Edge Cases (Symlinks, Permissions)

**Probability**: Medium
**Impact**: Low
**Mitigation**:
- Handle file access errors gracefully
- Log warnings for inaccessible agents
- Continue discovery with available agents

---

## Rollout Plan

### Stage 1: Implementation & Testing (2-3 hours)
- Implement discovery changes
- Add unit tests
- Run integration tests

### Stage 2: Validation (1 hour)
- Test with all 5 templates (react-typescript, fastapi-python, etc.)
- Verify local agents discovered correctly
- Check precedence rules work

### Stage 3: Deployment (15 min)
- Merge to main
- No user-facing changes (internal fix)
- Unblocks enforcement tasks

---

## Follow-Up Tasks

After this task completes:

1. **TASK-ENF-P0-2**: Update agent-discovery-guide.md with local agent scanning
2. **TASK-ENF-P0-3**: Update template-init to verify agents discoverable
3. **TASK-ENF-P0-4**: Update agent-enhance to validate discovery metadata
4. **TASK-ENF1**: Implement pre-report validation (now unblocked)
5. **TASK-ENF2**: Enhance tracking with source paths (now unblocked)
6. **TASK-ENF4**: Implement phase gate checkpoints (now unblocked)
7. **TASK-ENF5-v2**: Redesign agent table with dynamic discovery (now unblocked)

---

## References

- **Review Report**: .claude/reviews/TASK-REV-9A4E-review-report.md
- **Review Task**: tasks/backlog/TASK-REV-9A4E-review-enforcement-tasks-regression-analysis.md
- **Agent Discovery Guide**: docs/guides/agent-discovery-guide.md
- **Original Discovery Issue**: TASK-8D3F (Subagent invocation issues)

---

## Notes

- **Critical Path**: This task is on the critical path for ALL enforcement tasks
- **Priority**: CRITICAL - Must be completed before any enforcement implementation
- **Effort**: 2-3 hours (relatively quick, high impact)
- **Risk**: Low - Additive change, doesn't break existing behavior

---

**Created**: 2025-11-27
**Priority**: CRITICAL
**Effort**: 2-3 hours
**Blocks**: TASK-ENF1, TASK-ENF2, TASK-ENF4, TASK-ENF5-v2
