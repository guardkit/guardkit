---
id: TASK-ENF-P0-4
title: Update agent-enhance to validate discovery metadata
status: backlog
created: 2025-11-27T16:50:00Z
updated: 2025-11-27T16:50:00Z
priority: medium
tags: [agent-enhance, agent-discovery, phase-0]
task_type: implementation
epic: agent-invocation-enforcement
feature: null
requirements: []
dependencies: [TASK-ENF-P0-1]
complexity: 5
effort_estimate: 2-3 hours
related_to: TASK-REV-9A4E
---

# TASK-ENF-P0-4: Update Agent-Enhance Discovery Metadata Validation

## Context

TASK-REV-9A4E identified that `/agent-enhance` adds boundary sections but doesn't explicitly validate or add discovery metadata (stack, phase, capabilities, keywords). With TASK-ENF-P0-1 fixing discovery, agent-enhance should ensure enhanced agents are discoverable.

**Discovery**: TASK-REV-9A4E (Architectural Review - Finding #5)
**Implementation**: TASK-ENF-P0-1 (Agent Discovery Fix)

---

## Objective

Enhance `/agent-enhance` to:
1. Validate discovery metadata exists (stack, phase, capabilities, keywords)
2. Add missing metadata with user prompts or AI inference
3. Verify agent is discoverable after enhancement
4. Update enhancement checklist with discovery requirements

---

## Scope

### Files to Modify

**Primary**:
- `installer/global/commands/agent-enhance` (Python script)
- `installer/global/commands/agent-enhance.md` (documentation)

**Related**:
- `installer/global/agents/agent-content-enhancer.md` (agent instructions)

---

## Requirements

### FR1: Validate Discovery Metadata

**Requirement**: Check if agent has required discovery metadata

**Required Fields**:
| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `stack` | array | ✅ Yes | Technology stack(s) |
| `phase` | string | ✅ Yes | Workflow phase (implementation, review, testing, etc.) |
| `capabilities` | array | ✅ Yes | Specific skills/domains |
| `keywords` | array | ✅ Yes | Searchable terms for matching |
| `model` | string | ⚠️ Optional | Claude model (haiku, sonnet, opus) |

**Implementation**:
```python
def validate_discovery_metadata(agent):
    """Validate agent has required discovery metadata"""
    required_fields = ["stack", "phase", "capabilities", "keywords"]
    missing = []

    for field in required_fields:
        if field not in agent.frontmatter:
            missing.append(field)

    return missing  # Return list of missing fields
```

**Acceptance Criteria**:
- [ ] Check for all 4 required fields
- [ ] Return list of missing fields
- [ ] Optional fields (model) don't trigger validation errors

---

### FR2: Add Missing Metadata Interactively

**Requirement**: If metadata missing, prompt user or use AI inference

**Implementation Options**:

**Option 1: User Prompts** (simpler, explicit)
```python
def add_missing_metadata(agent, missing_fields):
    """Prompt user for missing metadata"""
    for field in missing_fields:
        if field == "stack":
            value = prompt_user("Enter stack (e.g., python, react, typescript): ")
            agent.frontmatter["stack"] = [v.strip() for v in value.split(",")]

        elif field == "phase":
            value = prompt_user("Enter phase (implementation/review/testing/orchestration/debugging): ")
            agent.frontmatter["phase"] = value.strip()

        elif field == "capabilities":
            value = prompt_user("Enter capabilities (comma-separated): ")
            agent.frontmatter["capabilities"] = [v.strip() for v in value.split(",")]

        elif field == "keywords":
            value = prompt_user("Enter keywords (comma-separated): ")
            agent.frontmatter["keywords"] = [v.strip() for v in value.split(",")]
```

**Option 2: AI Inference** (smarter, automatic)
```python
def infer_missing_metadata(agent, missing_fields):
    """Use AI to infer missing metadata from agent content"""
    prompt = f"""
    Analyze this agent's content and extract:
    {missing_fields}

    Agent name: {agent.name}
    Agent content:
    {agent.content}

    Return structured metadata.
    """

    inferred = ai_infer_metadata(prompt)
    agent.frontmatter.update(inferred)
```

**Recommendation**: Start with Option 1 (user prompts), add Option 2 later

**Acceptance Criteria**:
- [ ] Missing metadata added to frontmatter
- [ ] User prompts clear and helpful
- [ ] Validation passes after metadata added

---

### FR3: Verify Agent Discoverability

**Requirement**: After enhancement, verify agent is discoverable

**Implementation**:
```python
def verify_discoverability(agent_path):
    """Test if enhanced agent is discoverable"""
    agent = parse_agent(agent_path)

    # Extract stack and phase from agent
    stack = agent.frontmatter.get("stack", [])[0] if agent.frontmatter.get("stack") else None
    phase = agent.frontmatter.get("phase", "implementation")

    if not stack:
        logger.warning(f"⚠️  Agent {agent.name} has no stack, may not be discoverable")
        return False

    # Test discovery
    try:
        discovered = discover_agents(phase=phase, stack=stack, keywords=[])

        if discovered.name == agent.name:
            logger.info(f"✅ Agent {agent.name} is discoverable")
            return True
        else:
            logger.warning(f"⚠️  Agent {agent.name} may not be discoverable (different agent selected)")
            return False
    except Exception as e:
        logger.error(f"❌ Discovery test failed: {e}")
        return False
```

**Acceptance Criteria**:
- [ ] Test discovery after enhancement
- [ ] Log success/warning/error
- [ ] Warn if agent not discoverable

---

### FR4: Update Enhancement Checklist

**Requirement**: Add discovery metadata validation to enhancement checklist

**Current Checklist** (in agent-enhance.md):
```markdown
## Enhancement Checklist

1. [ ] Agent name follows convention (<domain>-specialist.md)
2. [ ] Frontmatter complete (name, description)
3. [ ] ALWAYS/NEVER/ASK boundary sections present
4. [ ] Capabilities section clear and actionable
5. [ ] Quick Start section with examples
```

**Updated Checklist**:
```markdown
## Enhancement Checklist

1. [ ] Agent name follows convention (<domain>-specialist.md)
2. [ ] Frontmatter complete (name, description)
3. [ ] **Discovery metadata present (stack, phase, capabilities, keywords)** ← NEW
4. [ ] ALWAYS/NEVER/ASK boundary sections present
5. [ ] Capabilities section clear and actionable
6. [ ] Quick Start section with examples
7. [ ] **Agent is discoverable (verified via test)** ← NEW
```

---

## Implementation Plan

### Step 1: Add Metadata Validation (1 hour)

**File**: `installer/global/commands/agent-enhance`

**Add Function**:
```python
def validate_and_fix_discovery_metadata(agent_path):
    """Validate and fix discovery metadata"""
    agent = parse_agent(agent_path)

    # Validate
    missing = validate_discovery_metadata(agent)

    if missing:
        print(f"\n⚠️  Missing discovery metadata: {', '.join(missing)}")
        print("Adding metadata for agent discovery...\n")

        # Add missing metadata
        add_missing_metadata(agent, missing)

        # Save updated agent
        save_agent(agent, agent_path)

    # Verify discoverability
    verify_discoverability(agent_path)
```

**Call After Boundary Section Enhancement**:
```python
# Existing enhancement steps
enhance_boundary_sections(agent_path)

# NEW: Validate discovery metadata
validate_and_fix_discovery_metadata(agent_path)

# Existing final steps
print("✅ Agent enhancement complete!")
```

---

### Step 2: Implement User Prompts (0.5 hour)

**Add Interactive Prompts**:
```python
def prompt_user(message):
    """Prompt user for input"""
    return input(message)

def add_missing_metadata(agent, missing_fields):
    # ... (implementation from FR2)
```

---

### Step 3: Add Discoverability Test (0.5 hour)

**Add Test Function**:
```python
def verify_discoverability(agent_path):
    # ... (implementation from FR3)
```

---

### Step 4: Update Documentation (1 hour)

**File**: `installer/global/commands/agent-enhance.md`

**Add Section**: "Discovery Metadata Validation"

**Content**:
```markdown
## Discovery Metadata Validation

`/agent-enhance` validates and adds discovery metadata required for agent discovery.

### Required Metadata

| Field | Type | Example | Purpose |
|-------|------|---------|---------|
| `stack` | array | `[python, fastapi]` | Technology stack(s) |
| `phase` | string | `implementation` | Workflow phase |
| `capabilities` | array | `[api, async-patterns, pydantic]` | Specific skills |
| `keywords` | array | `[endpoint, route, schema]` | Search terms |

### Interactive Prompts

If metadata is missing, you'll be prompted:

```
⚠️  Missing discovery metadata: stack, phase

Adding metadata for agent discovery...

Enter stack (e.g., python, react, typescript): python, fastapi
Enter phase (implementation/review/testing/orchestration/debugging): implementation
```

### Discoverability Verification

After enhancement, the system verifies your agent is discoverable:

```
✅ Agent python-api-specialist is discoverable
```

If not discoverable, check:
- Stack matches your project technology
- Phase is valid (implementation, review, testing, orchestration, debugging)
- Capabilities and keywords are relevant
```

---

## Acceptance Criteria

- [ ] Discovery metadata validated during enhancement
- [ ] Missing metadata prompted from user
- [ ] Discoverability verified after enhancement
- [ ] Enhancement checklist updated with discovery requirements
- [ ] Documentation updated with discovery metadata section

---

## Testing Strategy

### Unit Tests
```bash
# Test metadata validation
pytest tests/test_agent_enhance.py::test_validate_discovery_metadata

# Test missing metadata prompts
pytest tests/test_agent_enhance.py::test_add_missing_metadata

# Test discoverability verification
pytest tests/test_agent_enhance.py::test_verify_discoverability
```

### Integration Tests
```bash
# Enhance agent without metadata
cat > /tmp/test-agent.md <<EOF
# Test Agent
This is a test agent.
EOF

/agent-enhance /tmp/test-agent.md

# Expected:
# - Prompts for stack, phase, capabilities, keywords
# - Adds metadata to frontmatter
# - Verifies discoverability
# - Saves enhanced agent

# Verify metadata added
cat /tmp/test-agent.md
# Expected: Frontmatter includes stack, phase, capabilities, keywords
```

---

## Dependencies

**Depends On**:
- TASK-ENF-P0-1 (Agent Discovery Fix) - Discovery must work for verification

**Enables**:
- Enhanced agents are immediately discoverable
- Template agents can be enhanced with discovery metadata
- Consistent agent structure across all agents

---

## Rollout Considerations

### Existing Agents

**Question**: Should we bulk-update existing agents to add discovery metadata?

**Options**:
1. **Lazy Update**: Update agents as they're enhanced (recommended)
2. **Bulk Update**: Run `/agent-enhance` on all agents in installer/global/agents/
3. **Manual Update**: Update high-priority agents only

**Recommendation**: Lazy update (Option 1)
- Less disruptive
- Focuses on agents being actively used
- Can bulk-update later if needed

### Template Agents

**When templates are created** (`/template-create`):
- Template agents should have discovery metadata by default
- agent-content-enhancer should add metadata during enhancement

**When templates are initialized** (`taskwright init`):
- Copied agents inherit metadata from template
- TASK-ENF-P0-3 verifies metadata after copy

---

## References

- Review Report: .claude/reviews/TASK-REV-9A4E-review-report.md (Finding #5)
- Agent Discovery Fix: TASK-ENF-P0-1
- Current Command: installer/global/commands/agent-enhance
- Agent Content Enhancer: installer/global/agents/agent-content-enhancer.md

---

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Depends On**: TASK-ENF-P0-1
