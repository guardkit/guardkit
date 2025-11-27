---
id: TASK-ENF-P0-3
title: Update template-init to verify agent discovery registration
status: backlog
created: 2025-11-27T16:45:00Z
updated: 2025-11-27T16:45:00Z
priority: medium
tags: [template-init, agent-discovery, phase-0]
task_type: implementation
epic: agent-invocation-enforcement
feature: null
requirements: []
dependencies: [TASK-ENF-P0-1]
complexity: 4
effort_estimate: 1-2 hours
related_to: TASK-REV-9A4E
---

# TASK-ENF-P0-3: Update Template-Init Agent Registration

## Context

TASK-REV-9A4E identified that `/template-init` copies agents to `.claude/agents/` but doesn't verify they're discoverable. With TASK-ENF-P0-1 fixing discovery to scan `.claude/agents/`, template-init should now verify agents are registered correctly.

**Discovery**: TASK-REV-9A4E (Architectural Review - Finding #4)
**Implementation**: TASK-ENF-P0-1 (Agent Discovery Fix)

---

## Objective

Enhance `/template-init` to:
1. Verify agents have discovery metadata after copying
2. Test discovery after initialization
3. Report registered agents to user
4. Handle missing metadata gracefully

---

## Scope

### Files to Modify

**Primary**:
- `installer/global/commands/template-init` (bash script)
- OR `installer/global/commands/lib/template_init.py` (if Python implementation)

**Related**:
- `installer/global/commands/template-init.md` (documentation)

---

## Requirements

### FR1: Verify Agent Metadata After Copy

**Requirement**: After copying agents, verify they have required discovery metadata

**Implementation**:
```python
def verify_agent_metadata(agent_path):
    """Verify agent has required discovery metadata"""
    required_fields = ["stack", "phase", "capabilities", "keywords"]

    agent = parse_agent(agent_path)
    missing_fields = [f for f in required_fields if f not in agent.frontmatter]

    if missing_fields:
        logger.warning(f"Agent {agent.name} missing metadata: {missing_fields}")
        return False
    return True
```

**Acceptance Criteria**:
- [ ] After copy, check each agent's frontmatter
- [ ] Warn if required metadata missing
- [ ] Continue initialization (don't block)

---

### FR2: Test Discovery After Initialization

**Requirement**: Verify copied agents are discoverable by running test discovery

**Implementation**:
```python
def test_agent_discovery_after_init(template_stack):
    """Test that template agents are discoverable"""
    try:
        # Run discovery for template stack
        discovered = discover_agents(phase="implementation", stack=template_stack)

        # Check if local agents found
        if discovered and discovered != "task-manager":
            logger.info(f"✅ Agent discovery successful: {discovered.name}")
            return True
        else:
            logger.warning("⚠️  No specialist agent discovered (will use task-manager)")
            return False
    except Exception as e:
        logger.error(f"❌ Agent discovery test failed: {e}")
        return False
```

**Acceptance Criteria**:
- [ ] Test discovery after agent copy
- [ ] Log success/warning/error
- [ ] Don't block initialization on failure

---

### FR3: Report Registered Agents

**Requirement**: Show user which agents were registered

**Implementation**:
```python
def report_registered_agents(agents_copied):
    """Report registered agents to user"""
    print("\n" + "="*60)
    print("✅ Registered Agents:")
    print("="*60)

    for agent in agents_copied:
        stack = agent.frontmatter.get("stack", "unknown")
        phase = agent.frontmatter.get("phase", "unknown")
        print(f"  • {agent.name}")
        print(f"    Stack: {stack}, Phase: {phase}")

    print("="*60 + "\n")
```

**Acceptance Criteria**:
- [ ] Display registered agents after initialization
- [ ] Show agent name, stack, and phase
- [ ] Clear, user-friendly format

---

### FR4: Handle Missing Metadata Gracefully

**Requirement**: If metadata missing, log warning but don't block initialization

**Acceptance Criteria**:
- [ ] Warn user about missing metadata
- [ ] Suggest running `/agent-enhance` to fix
- [ ] Continue initialization successfully

---

## Implementation Plan

### Step 1: Add Metadata Verification (0.5 hour)

**After agent copy**:
```python
agents_copied = copy_agents_from_template(template, ".claude/agents/")

# NEW: Verify metadata
for agent in agents_copied:
    if not verify_agent_metadata(agent):
        print(f"⚠️  Warning: {agent.name} missing discovery metadata")
        print(f"    Run: /agent-enhance .claude/agents/{agent.name}.md")
```

### Step 2: Add Discovery Test (0.5 hour)

**After agent copy and verification**:
```python
# NEW: Test discovery
test_agent_discovery_after_init(template.stack)
```

### Step 3: Add Agent Registration Report (0.5 hour)

**Before final success message**:
```python
# NEW: Report registered agents
report_registered_agents(agents_copied)

print("✅ Template initialization complete!")
```

### Step 4: Update Documentation (0.5 hour)

**File**: `installer/global/commands/template-init.md`

**Add Section**: "Agent Registration"

**Content**:
```markdown
## Agent Registration

After copying agents from the template, `template-init`:
1. Verifies agents have discovery metadata (stack, phase, capabilities, keywords)
2. Tests agent discovery to ensure agents are findable
3. Reports registered agents to the user

**Expected Output**:
```
======================================================================
✅ Registered Agents:
======================================================================
  • react-state-specialist
    Stack: [react, typescript], Phase: implementation
  • react-testing-specialist
    Stack: [react, typescript], Phase: testing
======================================================================
```

If agents are missing metadata, you'll see:
```
⚠️  Warning: custom-specialist missing discovery metadata
    Run: /agent-enhance .claude/agents/custom-specialist.md
```
```

---

## Acceptance Criteria

- [ ] Agent metadata verified after copy
- [ ] Discovery tested after initialization
- [ ] Registered agents reported to user
- [ ] Missing metadata handled gracefully (warning, not error)
- [ ] Documentation updated with registration section

---

## Testing Strategy

### Unit Tests
```bash
# Test metadata verification
pytest tests/test_template_init.py::test_verify_agent_metadata

# Test discovery test
pytest tests/test_template_init.py::test_discovery_after_init
```

### Integration Tests
```bash
# Initialize template and verify agents registered
taskwright init react-typescript

# Expected output:
# ✅ Registered Agents:
#   • react-state-specialist (stack: react, phase: implementation)

# Verify discovery works
/task-create "Test agent discovery" stack:react
/task-work TASK-XXX
# Expected: react-state-specialist invoked (not task-manager)
```

---

## Dependencies

**Depends On**:
- TASK-ENF-P0-1 (Agent Discovery Fix) - Discovery must scan `.claude/agents/`

**Enables**:
- User confidence that template agents are properly registered
- Early warning if agents have metadata issues
- Better troubleshooting when agents not found

---

## References

- Review Report: .claude/reviews/TASK-REV-9A4E-review-report.md (Finding #4)
- Agent Discovery Fix: TASK-ENF-P0-1
- Current Command: installer/global/commands/template-init

---

**Priority**: MEDIUM
**Effort**: 1-2 hours
**Depends On**: TASK-ENF-P0-1
