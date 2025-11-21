---
task_id: TASK-FIX-9E1A
title: Fix task ID uniqueness and collision risk
status: BACKLOG
priority: HIGH
complexity: 2
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [bug, phase-8, production-blocker, task-management]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-FIX-4B2E]
estimated_duration: 30 minutes
technologies: [python, uuid]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Fix Task ID Uniqueness and Collision Risk

## Problem Statement

Task ID generation for agent enhancement tasks uses timestamp-based IDs that can collide when multiple agents have similar names. This creates duplicate task IDs and potential file overwrites.

**Review Finding** (Section 2, High Priority Issue #1):
> **Current**: `TASK-AGENT-{agent_name[:8]}-{timestamp}`
> **Problem**: Agents with similar names create duplicate IDs
> **Example**: `repository-pattern-specialist` and `repository-domain-specialist` both → `TASK-AGENT-REPOSITO-20251120-211953`

## Current State

**Location**: `installer/global/commands/lib/template_create_orchestrator.py:963`

```python
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
task_id = f"TASK-AGENT-{agent_name[:8].upper()}-{timestamp}"
```

**Problems**:
1. Agent name truncated to 8 chars (too short for uniqueness)
2. Timestamp has 1-second resolution (collisions in batch operations)
3. Two agents with same 8-char prefix → duplicate IDs
4. Could overwrite existing task files

## Acceptance Criteria

### 1. Uniqueness Guarantee
- [ ] Task IDs are guaranteed unique even for similar agent names
- [ ] IDs don't collide in rapid succession (< 1 second apart)
- [ ] IDs don't collide across multiple template creations
- [ ] Works correctly with batch agent processing

### 2. ID Format
- [ ] Follows Taskwright convention: `TASK-{prefix}-{hash}`
- [ ] Prefix indicates agent type or category
- [ ] Hash is short but collision-resistant (8 chars minimum)
- [ ] Human-readable and sortable

### 3. Backward Compatibility
- [ ] New format doesn't break existing task parsing
- [ ] No migration needed for existing tasks
- [ ] Compatible with task management commands

### 4. Implementation Quality
- [ ] Uses standard library (uuid module)
- [ ] No external dependencies
- [ ] Deterministic for testing (optional seed parameter)
- [ ] Well-documented in code

## Technical Details

### Files to Modify

**1. `installer/global/commands/lib/template_create_orchestrator.py`**
- Line 963: Task ID generation

### Recommended Implementation

#### Option A: UUID-Based (Recommended)
```python
import uuid

def _generate_task_id(self, agent_name: str) -> str:
    """Generate unique task ID for agent enhancement.

    Format: TASK-{agent-name-prefix}-{uuid}
    Example: TASK-REPO-PATTERN-A3F2B1C8

    Args:
        agent_name: Full agent name (e.g., 'repository-pattern-specialist')

    Returns:
        str: Unique task ID
    """
    # Use up to 12 chars of agent name for readability
    prefix = agent_name[:12].upper().replace('-', '-')

    # Use 8 chars of UUID for uniqueness (collision probability: ~1 in 4 billion)
    unique_id = uuid.uuid4().hex[:8].upper()

    return f"TASK-{prefix}-{unique_id}"
```

**Examples**:
- `repository-pattern-specialist` → `TASK-REPOSITORY-A3F2B1C8`
- `repository-domain-specialist` → `TASK-REPOSITORY-7B9E4D2A` (different!)
- `realm-thread-safety-specialist` → `TASK-REALM-THREA-F1C3E8B2`

**Pros**:
- Guaranteed uniqueness (128-bit UUID)
- Standard library (no dependencies)
- Fast generation
- Collision-resistant

**Cons**:
- Less human-readable (random string)
- Not sortable by creation time

#### Option B: Hash-Based
```python
import hashlib

def _generate_task_id(self, agent_name: str) -> str:
    """Generate unique task ID using hash of agent name + timestamp."""
    timestamp = datetime.datetime.now().isoformat()
    content = f"{agent_name}:{timestamp}"
    hash_value = hashlib.md5(content.encode()).hexdigest()[:8].upper()

    prefix = agent_name[:12].upper().replace('-', '-')

    return f"TASK-{prefix}-{hash_value}"
```

**Pros**:
- Deterministic for same input
- Short hash (8 chars)

**Cons**:
- Requires timestamp for uniqueness
- More complex than UUID

#### Option C: Counter-Based (NOT Recommended)
```python
_task_counter = 0

def _generate_task_id(self, agent_name: str) -> str:
    """Generate task ID with counter."""
    self._task_counter += 1
    prefix = agent_name[:12].upper()
    return f"TASK-{prefix}-{self._task_counter:04d}"
```

**Pros**:
- Sequential, sortable

**Cons**:
- Requires persistent counter storage
- Race conditions in parallel execution
- Complexity not worth benefits

### Decision: Option A (UUID-Based)

**Rationale**:
- Simplest implementation
- Guaranteed uniqueness
- Standard library
- No state management needed
- Works with parallel processing

## Success Metrics

### Functional Tests
- [ ] Different agents → different task IDs
- [ ] Similar agent names → different task IDs
- [ ] Rapid succession (10+ tasks/second) → all unique
- [ ] Same agent in different templates → different IDs

### Edge Cases
- [ ] Very long agent names (>12 chars) truncated correctly
- [ ] Agent names with special characters handled
- [ ] Unicode in agent names (if supported)

### Performance
- [ ] ID generation < 1ms per task
- [ ] No memory leaks with 1000+ IDs

## Dependencies

**Blocks**:
- TASK-FIX-4B2E (task creation workflow) - should use fixed ID generation

**Related**:
- TASK-PHASE-8-INCREMENTAL (main implementation)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 2**: Code Quality Review - High Priority Issue #1
- **Line 963**: Task ID collision risk
- **Section 6.1**: Immediate Priority #4 (15 minutes estimate)

## Estimated Effort

**Duration**: 30 minutes (1 hour with comprehensive testing)

**Breakdown**:
- Implementation (15 min): Replace timestamp with UUID
- Testing (30 min): Write unit tests for uniqueness
- Documentation (15 min): Update docstring

## Test Plan

### Unit Tests

```python
def test_task_id_uniqueness():
    """Test that task IDs are unique for different agents."""
    orchestrator = TemplateCreateOrchestrator()

    id1 = orchestrator._generate_task_id("repository-pattern-specialist")
    id2 = orchestrator._generate_task_id("repository-domain-specialist")

    assert id1 != id2
    assert id1.startswith("TASK-REPOSITORY-")
    assert id2.startswith("TASK-REPOSITORY-")

def test_task_id_rapid_generation():
    """Test uniqueness with rapid ID generation."""
    orchestrator = TemplateCreateOrchestrator()
    agent_name = "test-agent"

    ids = [orchestrator._generate_task_id(agent_name) for _ in range(1000)]

    assert len(ids) == len(set(ids))  # All unique

def test_task_id_format():
    """Test task ID follows expected format."""
    orchestrator = TemplateCreateOrchestrator()

    task_id = orchestrator._generate_task_id("my-test-agent-specialist")

    assert task_id.startswith("TASK-")
    assert len(task_id) == len("TASK-MY-TEST-AGEN-12345678")
    assert task_id.count("-") == 3  # TASK-PREFIX-UUID

def test_task_id_long_agent_name():
    """Test handling of very long agent names."""
    orchestrator = TemplateCreateOrchestrator()

    long_name = "very-long-agent-name-that-exceeds-twelve-characters"
    task_id = orchestrator._generate_task_id(long_name)

    # Should truncate to 12 chars between first and last dash
    parts = task_id.split("-")
    prefix_length = len("-".join(parts[1:-1]))
    assert prefix_length <= 12

def test_task_id_collision_probability():
    """Statistical test for collision resistance."""
    orchestrator = TemplateCreateOrchestrator()

    # Generate 10,000 IDs - should have zero collisions
    ids = {orchestrator._generate_task_id("agent") for _ in range(10000)}

    assert len(ids) == 10000  # All unique
```

## Implementation Steps

1. **Update _generate_task_id method** (or create if doesn't exist)
   - Import uuid at top of file
   - Implement UUID-based generation
   - Add comprehensive docstring

2. **Update task creation call**
   ```python
   # Old
   task_id = f"TASK-AGENT-{agent_name[:8].upper()}-{timestamp}"

   # New
   task_id = self._generate_task_id(agent_name)
   ```

3. **Write unit tests** (see test plan above)

4. **Update documentation**
   - Document new ID format in code comments
   - Update command spec if ID format is documented

## Notes

- **Priority**: HIGH - production blocker per review
- **Effort**: 15 minutes per review (very quick fix)
- **Impact**: Prevents data loss from file overwrites
- **Risk**: LOW - purely internal change, no user-facing impact

## Alternative Considered

**Content-Addressable IDs**:
```python
# Hash of agent file content + template name
content_hash = hashlib.sha256(f"{agent_content}:{template_name}".encode()).hexdigest()[:8]
```

**Rejected because**:
- Overkill for this use case
- Same agent in same template would get same ID (wanted or not?)
- UUID is simpler and sufficient
