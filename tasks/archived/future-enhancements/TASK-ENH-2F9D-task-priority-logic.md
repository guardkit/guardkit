---
task_id: TASK-ENH-2F9D
title: Add dynamic task priority logic based on agent criticality
status: BACKLOG
priority: LOW
complexity: 2
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [enhancement, phase-8, task-management, prioritization]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-FIX-4B2E]
estimated_duration: 1 hour
technologies: [python, task-management]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Add Dynamic Task Priority Logic Based on Agent Criticality

## Problem Statement

All agent enhancement tasks are created with fixed priority "MEDIUM" regardless of agent importance. This doesn't reflect that some agents are more critical than others.

**Review Finding** (Section 2, Medium Priority Issue #6):
> **Location**: Line 969
> **Current**: Fixed priority "MEDIUM" for all tasks
> **Recommendation**: Priority based on agent criticality

## Current State

**Location**: `installer/core/commands/lib/template_create_orchestrator.py:969`

```python
priority: MEDIUM  # Fixed for all agents
```

**Problems**:
- No differentiation between critical and optional agents
- User can't prioritize enhancement work effectively
- Doesn't leverage agent priority metadata

## Acceptance Criteria

### 1. Dynamic Priority Assignment
- [ ] Task priority derived from agent priority field
- [ ] HIGH: agent.priority >= 9
- [ ] MEDIUM: agent.priority >= 7
- [ ] LOW: agent.priority < 7
- [ ] Falls back to MEDIUM if priority not available

### 2. Agent Priority Source
- [ ] Read priority from agent frontmatter
- [ ] Use architectural-reviewer's agent priority scoring
- [ ] Handle missing priority gracefully
- [ ] Validate priority is in valid range (0-10)

### 3. Configuration
- [ ] Priority thresholds configurable (optional)
- [ ] Can override priority in template vars
- [ ] Documented in code

### 4. User Experience
- [ ] Task list shows appropriate priorities
- [ ] User can prioritize enhancement work
- [ ] High priority agents stand out

## Technical Details

### Files to Modify

**1. `installer/core/commands/lib/template_create_orchestrator.py`**
- Add `_determine_task_priority` method
- Update task creation to use dynamic priority

### Recommended Implementation

```python
def _determine_task_priority(self, agent_file: Path) -> str:
    """Determine task priority based on agent criticality.

    Priority Thresholds:
    - HIGH: agent.priority >= 9 (critical agents)
    - MEDIUM: agent.priority >= 7 (important agents)
    - LOW: agent.priority < 7 (optional agents)

    Args:
        agent_file: Path to agent markdown file

    Returns:
        str: Priority level (HIGH, MEDIUM, or LOW)
    """
    try:
        import frontmatter
        agent_doc = frontmatter.loads(agent_file.read_text())
        agent_priority = agent_doc.metadata.get("priority", 7)  # Default to 7

        # Validate priority is numeric and in range
        if not isinstance(agent_priority, (int, float)):
            logger.warning(f"Invalid priority in {agent_file.name}: {agent_priority}")
            return "MEDIUM"

        agent_priority = max(0, min(10, agent_priority))  # Clamp to [0, 10]

        # Map agent priority to task priority
        if agent_priority >= 9:
            return "HIGH"
        elif agent_priority >= 7:
            return "MEDIUM"
        else:
            return "LOW"

    except Exception as e:
        logger.warning(f"Could not determine priority for {agent_file.name}: {e}")
        return "MEDIUM"  # Safe default
```

### Usage in Task Creation

```python
def _create_agent_enhancement_task(...):
    # Determine priority based on agent
    priority = self._determine_task_priority(agent_file)

    template_vars = {
        "task_id": task_id,
        "priority": priority,  # Dynamic instead of fixed
        # ... other vars
    }

    # Render template
    task_content = template.render(**template_vars)
    # ...
```

### Priority Thresholds Configuration (Optional)

```python
# Module-level constants for easy configuration
PRIORITY_THRESHOLDS = {
    "HIGH": 9,    # agent.priority >= 9 → HIGH
    "MEDIUM": 7,  # agent.priority >= 7 → MEDIUM
    # < 7 → LOW
}

def _determine_task_priority(self, agent_file: Path) -> str:
    """Determine task priority using configured thresholds."""
    try:
        import frontmatter
        agent_doc = frontmatter.loads(agent_file.read_text())
        agent_priority = agent_doc.metadata.get("priority", 7)

        # Use configured thresholds
        if agent_priority >= PRIORITY_THRESHOLDS["HIGH"]:
            return "HIGH"
        elif agent_priority >= PRIORITY_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        else:
            return "LOW"
    except Exception:
        return "MEDIUM"
```

## Success Metrics

### Functional Tests
- [ ] Critical agent (priority 9+) → HIGH task
- [ ] Important agent (priority 7-8) → MEDIUM task
- [ ] Optional agent (priority <7) → LOW task
- [ ] Missing priority → MEDIUM (fallback)
- [ ] Invalid priority → MEDIUM (fallback)

### Edge Cases
- [ ] Priority = 10 → HIGH
- [ ] Priority = 9 → HIGH
- [ ] Priority = 7 → MEDIUM
- [ ] Priority = 6.9 → LOW
- [ ] Priority = 0 → LOW
- [ ] Priority = "invalid" → MEDIUM
- [ ] Priority = -1 → LOW (clamped to 0)
- [ ] Priority = 100 → HIGH (clamped to 10)

### User Experience
- [ ] Task list sorted by priority shows critical agents first
- [ ] User can focus on high-priority enhancements
- [ ] Priority visible in task metadata

## Dependencies

**Related To**:
- TASK-FIX-4B2E (task creation workflow) - uses this priority logic
- TASK-PHASE-8-INCREMENTAL (main implementation)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 2**: Code Quality Review - Medium Priority Issue #6
- **Line 969**: Missing task priority logic

## Estimated Effort

**Duration**: 1 hour

**Breakdown**:
- Implementation (30 min): Add priority determination logic
- Testing (20 min): Test all priority levels
- Documentation (10 min): Document thresholds

## Test Plan

### Unit Tests

```python
def test_determine_priority_high(tmp_path):
    """Test high priority agent → HIGH task."""
    agent_file = tmp_path / "critical-agent.md"
    agent_file.write_text("""---
name: critical-agent
priority: 10
---
""")

    orchestrator = TemplateCreateOrchestrator()
    priority = orchestrator._determine_task_priority(agent_file)

    assert priority == "HIGH"

def test_determine_priority_medium(tmp_path):
    """Test medium priority agent → MEDIUM task."""
    agent_file = tmp_path / "important-agent.md"
    agent_file.write_text("""---
name: important-agent
priority: 7
---
""")

    orchestrator = TemplateCreateOrchestrator()
    priority = orchestrator._determine_task_priority(agent_file)

    assert priority == "MEDIUM"

def test_determine_priority_low(tmp_path):
    """Test low priority agent → LOW task."""
    agent_file = tmp_path / "optional-agent.md"
    agent_file.write_text("""---
name: optional-agent
priority: 5
---
""")

    orchestrator = TemplateCreateOrchestrator()
    priority = orchestrator._determine_task_priority(agent_file)

    assert priority == "LOW"

def test_determine_priority_missing(tmp_path):
    """Test missing priority → MEDIUM (default)."""
    agent_file = tmp_path / "agent.md"
    agent_file.write_text("""---
name: agent
---
""")

    orchestrator = TemplateCreateOrchestrator()
    priority = orchestrator._determine_task_priority(agent_file)

    assert priority == "MEDIUM"

def test_determine_priority_invalid(tmp_path):
    """Test invalid priority → MEDIUM (fallback)."""
    agent_file = tmp_path / "agent.md"
    agent_file.write_text("""---
name: agent
priority: "invalid"
---
""")

    orchestrator = TemplateCreateOrchestrator()
    priority = orchestrator._determine_task_priority(agent_file)

    assert priority == "MEDIUM"

def test_determine_priority_clamping(tmp_path):
    """Test priority clamping to [0, 10] range."""
    # Test upper bound
    agent_file = tmp_path / "agent.md"
    agent_file.write_text("""---
name: agent
priority: 100
---
""")

    orchestrator = TemplateCreateOrchestrator()
    priority = orchestrator._determine_task_priority(agent_file)

    assert priority == "HIGH"  # Clamped to 10

    # Test lower bound
    agent_file.write_text("""---
name: agent
priority: -10
---
""")

    priority = orchestrator._determine_task_priority(agent_file)

    assert priority == "LOW"  # Clamped to 0
```

### Integration Tests

```python
def test_task_creation_with_dynamic_priority(tmp_path):
    """Test task creation uses dynamic priority."""
    # Create agent with high priority
    agent_file = tmp_path / "agents" / "critical-agent.md"
    agent_file.parent.mkdir(parents=True)
    agent_file.write_text("""---
name: critical-agent
priority: 10
---
""")

    orchestrator = TemplateCreateOrchestrator()
    task_id = orchestrator._create_agent_enhancement_task(
        agent_name="critical-agent",
        agent_file=agent_file,
        template_dir=tmp_path,
        template_name="test-template"
    )

    # Read created task
    task_file = Path("tasks/backlog") / f"{task_id}.md"
    task_content = task_file.read_text()

    assert "priority: HIGH" in task_content
```

## Notes

- **Priority**: LOW - nice to have, not blocking
- **Risk**: LOW - purely additive logic
- **Impact**: Improves user prioritization of enhancement work
- **Effort**: 1 hour per review estimate

## Example Output

**Before** (all tasks same priority):
```
tasks/backlog/
├── TASK-CRITICAL-12345678.md     (priority: MEDIUM)
├── TASK-IMPORTANT-87654321.md    (priority: MEDIUM)
└── TASK-OPTIONAL-ABCDEF12.md     (priority: MEDIUM)
```

**After** (dynamic priority):
```
tasks/backlog/
├── TASK-CRITICAL-12345678.md     (priority: HIGH)    ← Stands out
├── TASK-IMPORTANT-87654321.md    (priority: MEDIUM)
└── TASK-OPTIONAL-ABCDEF12.md     (priority: LOW)     ← Deprioritized
```

## Future Enhancements

### Complexity-Based Priority
Could also consider agent complexity:
```python
if agent_priority >= 9 and agent_complexity >= 7:
    return "CRITICAL"  # New level
```

### User Override
Allow user to override priority via flag:
```bash
/template-create --agent-priority-override=all:HIGH
```

### Priority Distribution Report
Show priority distribution:
```
Created 10 agent enhancement tasks:
- HIGH: 2 tasks
- MEDIUM: 5 tasks
- LOW: 3 tasks
```
