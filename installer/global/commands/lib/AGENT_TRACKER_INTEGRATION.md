# Agent Invocation Tracker Integration Guide

**Task Reference:** TASK-ENF2
**Purpose:** Add agent invocation tracking and logging to task-work execution

## Overview

This guide explains how to integrate the `AgentInvocationTracker` into the task-work command to provide real-time visibility into which agents are being invoked, their sources, and execution status.

## Quick Start

### 1. Import Required Modules

```python
from installer.global.commands.lib import (
    AgentInvocationTracker,
    add_pending_phases,
    discover_agent_with_source
)
```

### 2. Initialize Tracker (Before Phase 2)

```python
# Initialize tracker at the start of task-work execution
tracker = AgentInvocationTracker()

# Add pending phases for visual clarity
add_pending_phases(tracker, workflow_mode="standard")  # or "micro"
```

### 3. Discover Agent with Source

Replace existing agent discovery calls with source-aware version:

```python
# OLD WAY (without source tracking):
agent_name = discover_agents(phase='implementation', stack=['python'])[0]['name']

# NEW WAY (with source tracking):
agent_name, agent_source = discover_agent_with_source(
    phase='implementation',
    stack=['python'],
    keywords=['fastapi', 'async', 'pydantic']
)
```

### 4. Record Invocation (Before Task Tool)

Before invoking each agent with the Task tool:

```python
tracker.record_invocation(
    phase="3",                          # Phase identifier
    agent_name=agent_name,              # Agent name from discovery
    phase_description="Implementation", # Human-readable description
    agent_source=agent_source           # Source from discovery
)
```

### 5. Mark Complete (After Agent Returns)

After each agent completes:

```python
tracker.mark_complete(
    phase="3",
    duration_seconds=120,  # Optional: calculated duration
    files_modified=[]      # Optional: list of modified files
)
```

### 6. Mark Skipped (For Blocked Phases)

If a phase is skipped or blocked:

```python
tracker.mark_skipped(
    phase="3",
    reason="Compilation failed"
)
```

## Integration Points in task-work.md

### Phase 2: Implementation Planning

```markdown
#### Phase 2: Implementation Planning

**INITIALIZE TRACKER** (first phase only):
```python
tracker = AgentInvocationTracker()
add_pending_phases(tracker, workflow_mode="standard")
```

**DISCOVER AGENT WITH SOURCE**:
```python
agent_name, agent_source = discover_agent_with_source(
    phase="implementation",
    stack=task.stack,
    keywords=extract_keywords(task.description)
)
```

**RECORD INVOCATION**:
```python
tracker.record_invocation("2", agent_name, "Planning", agent_source)
```

**INVOKE** Task tool with discovered agent.

**MARK COMPLETE**:
```python
tracker.mark_complete("2", duration_seconds=calculate_duration())
```
```

### Phase 2.5B: Architectural Review

```markdown
#### Phase 2.5B: Architectural Review

**DISCOVER AGENT**:
```python
agent_name, agent_source = discover_agent_with_source(
    phase="review",
    stack=["cross-stack"],
    keywords=["architecture", "solid", "patterns"]
)
```

**RECORD INVOCATION**:
```python
tracker.record_invocation("2.5B", agent_name, "Arch Review", agent_source)
```

**INVOKE** architectural-reviewer agent.

**MARK COMPLETE**:
```python
tracker.mark_complete("2.5B", duration_seconds=calculate_duration())
```
```

### Phase 3: Implementation

```markdown
#### Phase 3: Implementation

**DISCOVER AGENT WITH SOURCE**:
```python
agent_name, agent_source = discover_agent_with_source(
    phase="implementation",
    stack=task.stack,
    keywords=extract_keywords(task.description)
)
```

**RECORD INVOCATION**:
```python
tracker.record_invocation("3", agent_name, "Implementation", agent_source)
```

**INVOKE** Task tool with discovered agent.

**MARK COMPLETE** (if successful):
```python
tracker.mark_complete("3", duration_seconds=calculate_duration())
```

**MARK SKIPPED** (if failed):
```python
tracker.mark_skipped("3", "Compilation failed")
```
```

### Phase 4: Testing

```markdown
#### Phase 4: Testing

**DISCOVER AGENT WITH SOURCE**:
```python
agent_name, agent_source = discover_agent_with_source(
    phase="testing",
    stack=task.stack,
    keywords=["testing", "pytest", "coverage"]
)
```

**RECORD INVOCATION**:
```python
tracker.record_invocation("4", agent_name, "Testing", agent_source)
```

**INVOKE** testing agent.

**MARK COMPLETE** (if successful):
```python
tracker.mark_complete("4", duration_seconds=calculate_duration())
```

**MARK SKIPPED** (if blocked):
```python
tracker.mark_skipped("4", "Phase 3 blocked")
```
```

### Phase 5: Code Review

```markdown
#### Phase 5: Code Review

**DISCOVER AGENT WITH SOURCE**:
```python
agent_name, agent_source = discover_agent_with_source(
    phase="review",
    stack=["cross-stack"],
    keywords=["code-quality", "review"]
)
```

**RECORD INVOCATION**:
```python
tracker.record_invocation("5", agent_name, "Review", agent_source)
```

**INVOKE** code-reviewer agent.

**MARK COMPLETE**:
```python
tracker.mark_complete("5", duration_seconds=calculate_duration())
```
```

## Visual Output Examples

### During Execution

```
=======================================================
AGENT INVOCATIONS LOG
=======================================================
✅ Phase 2 (Planning): python-api-specialist 📁 (source: local, completed in 45s)
✅ Phase 2.5B (Arch Review): architectural-reviewer 🌐 (source: global, completed in 30s)
⏳ Phase 3 (Implementation): python-api-specialist 📁 (source: local, IN PROGRESS)
⏸️ Phase 4 (Testing): Pending
⏸️ Phase 5 (Review): Pending
=======================================================
```

### After All Phases

```
=======================================================
AGENT INVOCATIONS LOG
=======================================================
✅ Phase 2 (Planning): python-api-specialist 📁 (source: local, completed in 45s)
✅ Phase 2.5B (Arch Review): architectural-reviewer 🌐 (source: global, completed in 30s)
✅ Phase 3 (Implementation): python-api-specialist 📁 (source: local, completed in 120s)
✅ Phase 4 (Testing): test-orchestrator 🌐 (source: global, completed in 60s)
✅ Phase 5 (Review): code-reviewer 🌐 (source: global, completed in 25s)
=======================================================
```

### Blocked Task

```
=======================================================
AGENT INVOCATIONS LOG
=======================================================
✅ Phase 2 (Planning): python-api-specialist 📁 (source: local, completed in 45s)
✅ Phase 2.5B (Arch Review): architectural-reviewer 🌐 (source: global, completed in 30s)
❌ Phase 3 (Implementation): SKIPPED (Compilation failed)
❌ Phase 4 (Testing): SKIPPED (Phase 3 blocked)
❌ Phase 5 (Review): SKIPPED (Phase 3 blocked)
=======================================================
```

## Source Icons Reference

| Source | Icon | Priority | Description |
|--------|------|----------|-------------|
| local | 📁 | 1 (highest) | Agent from `.claude/agents/` |
| user | 👤 | 2 | Agent from `~/.agentecflow/agents/` |
| global | 🌐 | 3 | Agent from `installer/global/agents/` |
| template | 📦 | 4 (lowest) | Agent from `installer/global/templates/*/agents/` |

## Status Icons Reference

| Status | Icon | Description |
|--------|------|-------------|
| completed | ✅ | Phase completed successfully |
| in_progress | ⏳ | Phase currently executing |
| pending | ⏸️ | Phase not yet started |
| skipped | ❌ | Phase skipped or blocked |

## Workflow Modes

### Standard Workflow (5 phases)

```python
add_pending_phases(tracker, workflow_mode="standard")
```

Phases: 2, 2.5B, 3, 4, 5

### Micro Workflow (3 phases)

```python
add_pending_phases(tracker, workflow_mode="micro")
```

Phases: 3, 4, 5

## Validation Support

The tracker provides data for TASK-ENF1 (pre-report validation):

```python
# Get count of completed agents
completed_count = tracker.get_completed_count()

# Get all completed invocations
completed = tracker.get_invocations_by_status("completed")

# Get all skipped phases
skipped = tracker.get_invocations_by_status("skipped")

# Validate all required phases were invoked
assert completed_count >= 3, "Not all required agents invoked"
```

## Testing

Run the demo to see the tracker in action:

```bash
python3 installer/global/commands/lib/demo_agent_tracker_integration.py
```

Run unit tests:

```bash
python3 installer/global/commands/lib/test_agent_invocation_tracker.py
```

## Benefits

1. **Visibility:** Users see exactly which agents are being used
2. **Source Tracking:** Know if local template agents are being used vs global
3. **Debugging:** Easily identify which agent is selected and why
4. **Validation:** Foundation for enforcement mechanisms (TASK-ENF1)
5. **Transparency:** Clear progress indication during execution

## Next Steps

1. Complete this task (TASK-ENF2)
2. Implement TASK-ENF1 (pre-report validation using tracker data)
3. Implement TASK-ENF3 (prominent invocation messages)
4. Implement TASK-ENF5-v2 (dynamic discovery enhancements)

## Related Tasks

- **TASK-ENF-P0-1:** Fix agent discovery to scan `.claude/agents/` (dependency)
- **TASK-ENF1:** Add pre-report validation (depends on this task)
- **TASK-ENF3:** Add prominent invocation messages (enhances this task)
- **TASK-ENF5-v2:** Dynamic discovery (complementary feature)
- **TASK-8D3F:** Review task that identified tracking gap
- **TASK-REV-9A4E:** Architectural review that identified source tracking gap
