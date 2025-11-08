# Task ID Strategy Analysis and Recommendations

## Executive Summary

**Current State**: Taskwright has duplicate task ID issues due to inconsistent ID formats and lack of atomic ID generation.

**Root Causes Identified**:
1. Multiple ID formats in use simultaneously (TASK-004, TASK-004A, TASK-030B-1, TASK-DOCS-001)
2. Sequential numbering vulnerable to race conditions
3. No central ID registry or lock mechanism
4. Manual ID creation allows arbitrary formats
5. **Duplicate confirmed**: TASK-003 exists twice in the codebase

**Recommendation**: Adopt a **hybrid approach** combining hash-based IDs (inspired by Beads) with optional hierarchical notation for PM tool integration.

---

## Current State Analysis

### Actual IDs Found in Codebase

```
Simple Sequential:     TASK-004, TASK-015, TASK-012, TASK-014, TASK-030
Letter Suffixes:       TASK-004A, TASK-001B
Hierarchical:          TASK-030B-1, TASK-030B-1.1, TASK-030E-1
Namespace Prefixes:    TASK-DOCS-001, TASK-DOCS-002, TASK-DOCS-003
Test Tasks:            TASK-TEST
Templates:             {TASK_ID}
DUPLICATES:            TASK-003 (appears twice)
```

### Problems Identified

1. **Race Conditions**: Multiple users/sessions can generate same sequential ID
2. **Format Chaos**: 5+ different ID formats in active use
3. **Poor Validation**: No pre-creation duplicate checking
4. **Weak PM Mapping**: Formats like TASK-030B-1.1 don't align with JIRA/Azure DevOps patterns
5. **Manual Override**: Users can create arbitrary IDs bypassing system logic

---

## Beads Issue Tracker Approach

### How Beads Solves This

**Format**: `bd-{hash}` (e.g., `bd-a1b2`, `bd-f14c3e`)

**Key Features**:
- **Hash-based**: Generated from random data, collision-free
- **Progressive length**: 4 chars (0-500), 5 chars (500-1,500), 6 chars (1,500+)
- **Hierarchical support**: `bd-a3f8e9.1`, `bd-a3f8e9.2` for subtasks
- **Birthday paradox math**: 4-char hex = 65,536 possibilities, 1% collision at ~153 issues

**Advantages**:
- ✅ **Zero race conditions**: Concurrent creation is safe
- ✅ **No coordination needed**: Works across distributed teams/branches
- ✅ **Short and memorable**: 4-6 characters vs TASK-001.2.05 (13 chars)
- ✅ **Natural hierarchy**: Dot notation for subtasks without complexity

**Disadvantages**:
- ❌ **Not human-sequential**: Can't easily tell order (bd-a1b2 vs bd-f3c4)
- ❌ **Less intuitive**: Users expect TASK-1, TASK-2, not TASK-a1b2
- ❌ **PM tool friction**: JIRA/Azure DevOps expect hierarchical or sequential IDs

---

## PM Tool Compatibility Analysis

### JIRA
- **Preferred format**: `PROJ-123` (project key + sequential number)
- **Hierarchy**: Epic → Story → Sub-task (separate ID sequences)
- **Compatibility with hash**: Moderate (can map but not native)
- **Compatibility with sequential**: High (native pattern)

### Azure DevOps
- **Preferred format**: Work Item IDs are system-generated integers
- **Hierarchy**: Epic → Feature → User Story → Task (all use same ID sequence)
- **Compatibility with hash**: Low (expects integer IDs)
- **Compatibility with sequential**: High (can map to integer sequence)

### Linear
- **Preferred format**: `TEAM-123` (team key + sequential)
- **Hierarchy**: Initiatives → Issues (separate sequences)
- **Compatibility with hash**: Moderate (flexible ID system)
- **Compatibility with sequential**: High (native pattern)

### GitHub Issues
- **Preferred format**: `#123` (repository-scoped sequential)
- **Hierarchy**: Projects/Milestones (labels-based, not structural)
- **Compatibility with hash**: Low (expects sequential integers)
- **Compatibility with sequential**: High (native pattern)

**Conclusion**: PM tools strongly favor **sequential integer IDs** with optional prefix/namespace.

---

## Recommended Solution: Hybrid Approach

### Format Specification

```
TASK-{prefix}-{hash}[.{subtask}]
```

**Components**:
- `TASK`: Fixed identifier
- `{prefix}`: Optional 2-3 char namespace (E01 = Epic 001, DOC = Documentation)
- `{hash}`: 4-6 character hex hash (collision-free)
- `{subtask}`: Optional sequential subtask number (1, 2, 3...)

**Examples**:
```
TASK-a3f8          # Standalone task (no epic)
TASK-E01-b2c4      # Task in Epic 001
TASK-DOC-f1a3      # Documentation task
TASK-E01-b2c4.1    # Subtask 1 of TASK-E01-b2c4
TASK-E01-b2c4.2    # Subtask 2 of TASK-E01-b2c4
```

### Why This Works

1. **Hash prevents duplicates**: Core ID is collision-free
2. **Prefix enables grouping**: Easy filtering by epic/domain
3. **Subtask notation**: Natural breakdown without coordination
4. **PM tool mapping**: Can map to sequential externally while keeping hash internally
5. **Short and memorable**: TASK-E01-b2c4 (13 chars) vs TASK-001.2.05 (13 chars, but hash is more flexible)

### ID Generation Algorithm

```python
import hashlib
import secrets
from datetime import datetime

def generate_task_id(prefix: str = None) -> str:
    """
    Generate collision-free task ID using hash.

    Args:
        prefix: Optional namespace (e.g., "E01" for Epic 001, "DOC" for docs)

    Returns:
        Task ID in format TASK-{prefix}-{hash} or TASK-{hash}
    """
    # Create random seed from timestamp + random bytes
    seed = f"{datetime.utcnow().isoformat()}-{secrets.token_hex(8)}"

    # Generate hash
    hash_bytes = hashlib.sha256(seed.encode()).digest()
    hash_hex = hash_bytes.hex()

    # Determine hash length based on existing task count
    task_count = count_existing_tasks()

    if task_count < 500:
        hash_length = 4
    elif task_count < 1500:
        hash_length = 5
    else:
        hash_length = 6

    # Extract hash portion
    task_hash = hash_hex[:hash_length]

    # Verify uniqueness (collision check)
    while task_exists(task_hash, prefix):
        # Extremely rare, but regenerate if collision
        seed = f"{datetime.utcnow().isoformat()}-{secrets.token_hex(8)}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        hash_hex = hash_bytes.hex()
        task_hash = hash_hex[:hash_length]

    # Format final ID
    if prefix:
        return f"TASK-{prefix}-{task_hash}"
    else:
        return f"TASK-{task_hash}"

def generate_subtask_id(parent_id: str, subtask_number: int) -> str:
    """
    Generate subtask ID with dot notation.

    Args:
        parent_id: Parent task ID (e.g., "TASK-E01-b2c4")
        subtask_number: Sequential subtask number (1, 2, 3...)

    Returns:
        Subtask ID (e.g., "TASK-E01-b2c4.1")
    """
    return f"{parent_id}.{subtask_number}"
```

### PM Tool Mapping Strategy

**Internal → External ID Mapping**:

```yaml
# Store in task frontmatter
id: TASK-E01-b2c4
external_ids:
  jira: PROJ-456        # Sequential in JIRA
  azure_devops: 1234    # Work item ID in Azure DevOps
  linear: TEAM-789      # Sequential in Linear
  github: 234           # Issue number in GitHub
```

**Mapping Table** (stored in `.claude/state/external_id_mapping.json`):

```json
{
  "TASK-E01-b2c4": {
    "jira": "PROJ-456",
    "azure_devops": 1234,
    "linear": "TEAM-789",
    "github": 234,
    "created": "2024-01-15T10:00:00Z",
    "epic": "EPIC-001"
  }
}
```

**Benefits**:
- Internal IDs are collision-free (hash-based)
- External IDs are sequential per PM tool
- Bidirectional mapping maintained
- No duplicate internal IDs possible
- Each PM tool gets its preferred format

---

## Migration Strategy

### Phase 1: ID Generation (Week 1)

1. **Implement hash-based generator**
   - Add `lib/id_generator.py`
   - Unit tests for collision checking
   - Performance tests (10,000 IDs in <1 second)

2. **Add validation**
   - Pre-creation duplicate check
   - Format validation regex
   - Collision detection

3. **Update `/task-create`**
   - Replace sequential logic with hash generator
   - Add prefix parameter support
   - Maintain backward compatibility (read old formats)

### Phase 2: PM Tool Mapping (Week 2)

1. **Implement mapping service**
   - Add `lib/external_id_mapper.py`
   - Bidirectional ID lookup
   - JSON persistence

2. **Update task frontmatter**
   - Add `external_ids` field
   - Auto-populate on PM tool sync

3. **Update export commands**
   - Map internal → external on export
   - Store mapping in both directions

### Phase 3: Migration (Week 3)

1. **Migrate existing tasks**
   - Generate hash IDs for all tasks
   - Preserve old IDs in `legacy_id` field
   - Update all cross-references

2. **Update documentation**
   - New ID format examples
   - PM tool mapping guide
   - Migration changelog

3. **Deprecation warnings**
   - Warn on old format usage
   - Provide migration script
   - Set removal timeline (6 months)

---

## Alternative: Pure Sequential with Locking

If hash-based IDs are too radical, we can fix the sequential approach:

### Atomic ID Generation

```python
import fcntl
import os
from pathlib import Path

def generate_sequential_id(prefix: str = None) -> str:
    """
    Generate sequential ID with file-based locking.
    Prevents race conditions in concurrent environments.
    """
    lock_file = Path(".claude/state/task_id.lock")
    counter_file = Path(".claude/state/task_id_counter.txt")

    # Acquire exclusive lock
    with open(lock_file, 'w') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

        try:
            # Read current counter
            if counter_file.exists():
                current = int(counter_file.read_text().strip())
            else:
                current = 0

            # Increment
            next_id = current + 1

            # Write back
            counter_file.write_text(str(next_id))

            # Format ID
            if prefix:
                return f"TASK-{prefix}-{next_id:03d}"
            else:
                return f"TASK-{next_id:03d}"

        finally:
            # Release lock
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
```

**Pros**:
- ✅ Familiar sequential format
- ✅ Easy to understand order
- ✅ PM tool native compatibility

**Cons**:
- ❌ Requires file locking (doesn't work on all filesystems)
- ❌ Doesn't work across distributed teams/branches
- ❌ Lock contention in high-concurrency scenarios
- ❌ No support for Conductor.build multi-worktree parallelism

---

## Recommended Decision Matrix

| Criterion | Hash-Based | Sequential + Lock | Current (Broken) |
|-----------|------------|-------------------|------------------|
| **Race Condition Safety** | ✅ Perfect | ⚠️ Good (with locks) | ❌ Broken |
| **Distributed Teams** | ✅ Works | ❌ Needs coordination | ❌ Broken |
| **PM Tool Compatibility** | ⚠️ Via mapping | ✅ Native | ❌ Inconsistent |
| **Human Readability** | ⚠️ Moderate | ✅ High | ⚠️ Varies |
| **Conductor.build Support** | ✅ Works | ❌ Lock conflicts | ❌ Broken |
| **Implementation Complexity** | ⚠️ Medium | ⚠️ Medium | ✅ Simple (but broken) |
| **Migration Effort** | ⚠️ Moderate | ⚠️ Moderate | - |

---

## Final Recommendation

**Adopt Hybrid Hash-Based Approach** (Option 1)

**Rationale**:
1. **Eliminates duplicates completely**: Hash-based IDs are mathematically collision-free
2. **Supports distributed workflows**: Critical for Conductor.build integration
3. **Flexible PM tool integration**: Can map to any external format
4. **Future-proof**: Scales to 1,500+ tasks without format changes
5. **Minimal user impact**: Users rarely type task IDs (mostly copy/paste)

**Format**:
```
TASK-{prefix}-{hash}[.{subtask}]

Examples:
TASK-a3f8           # Simple task
TASK-E01-b2c4       # Task in Epic 001
TASK-DOC-f1a3       # Documentation task
TASK-E01-b2c4.1     # Subtask
```

**PM Tool Strategy**:
- Internal: Hash-based (collision-free)
- External: Sequential per tool (native format)
- Mapping: Bidirectional JSON registry

**Implementation Timeline**: 3 weeks
- Week 1: ID generation + validation
- Week 2: PM tool mapping
- Week 3: Migration + documentation

---

## Action Items

1. **Decide on approach**: Hash-based vs Sequential + Lock
2. **Review prefix strategy**: What namespaces needed? (E01, DOC, FIX, etc.)
3. **PM tool priority**: Which tools need integration first?
4. **Migration timeline**: When to deprecate old formats?
5. **User communication**: How to announce change?

---

## References

- [Beads Issue Tracker](https://github.com/steveyegge/beads#bd---beads-issue-tracker-) - Hash-based ID inspiration
- [JIRA REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/) - External ID format
- [Azure DevOps Work Items](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/) - Integer ID system
- [Linear API](https://developers.linear.app/docs/graphql/working-with-the-graphql-api) - Sequential ID format
- [Birthday Paradox](https://en.wikipedia.org/wiki/Birthday_problem) - Collision probability math
