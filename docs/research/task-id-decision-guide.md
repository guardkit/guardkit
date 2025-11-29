# Task ID Strategy - Quick Decision Guide

## TL;DR

**Current Problem**: Duplicate task IDs (TASK-003 exists twice) due to race conditions and inconsistent formats.

**Recommended Solution**: Hash-based IDs with PM tool mapping (inspired by Beads issue tracker).

**Decision Required**: Choose between 3 approaches below.

---

## Option Comparison

| Feature | Hash-Based (Recommended) | Sequential + Lock | Hybrid Sequential |
|---------|--------------------------|-------------------|-------------------|
| **Example ID** | `TASK-E01-b2c4` | `TASK-E01-042` | `TASK-042` |
| **Collision Risk** | Zero (mathematically) | Low (with proper locking) | High (current issue) |
| **Concurrent Creation** | ✅ Safe | ⚠️ Requires file locks | ❌ Race conditions |
| **Distributed Teams** | ✅ Works perfectly | ❌ Lock conflicts | ❌ Coordination needed |
| **Conductor.build Support** | ✅ Full support | ❌ Lock conflicts in worktrees | ❌ Broken |
| **PM Tool Mapping** | Via mapping table | Direct (native) | Direct (native) |
| **Human Readability** | ⚠️ Moderate (TASK-b2c4) | ✅ High (TASK-042) | ✅ High (TASK-042) |
| **Implementation Effort** | Medium | Medium | Low (but broken) |
| **Migration Complexity** | Moderate | Moderate | None (status quo) |

---

## Option 1: Hash-Based (Recommended)

### Format
```
TASK-{prefix}-{hash}[.{subtask}]

Examples:
TASK-a3f8              # Simple task
TASK-E01-b2c4          # Task in Epic 001
TASK-DOC-f1a3          # Documentation task
TASK-E01-b2c4.1        # Subtask 1
TASK-E01-b2c4.2        # Subtask 2
```

### How It Works
- **Hash generation**: SHA-256 of timestamp + random bytes → 4-6 char hex
- **Collision prevention**: Mathematical guarantee (65,536 possibilities with 4 chars)
- **PM tool mapping**: Internal hash → External sequential (stored in mapping table)
- **Scaling**: 4 chars (0-500 tasks), 5 chars (500-1,500), 6 chars (1,500+)

### Pros
- ✅ **Zero duplicate risk**: Hash collisions are mathematically near-impossible
- ✅ **Concurrent-safe**: Multiple users/sessions can create tasks simultaneously
- ✅ **Distributed teams**: Works across branches, worktrees, teams
- ✅ **Conductor.build compatible**: Parallel worktrees work perfectly
- ✅ **Scalable**: Grows naturally with task count

### Cons
- ⚠️ **Not sequential**: Can't tell task order from ID alone
- ⚠️ **Requires mapping**: PM tools need separate sequential IDs
- ⚠️ **Less familiar**: Users expect TASK-1, TASK-2, not TASK-a3f8
- ⚠️ **Migration needed**: All existing tasks need new IDs

### PM Tool Integration
```yaml
# Internal ID (collision-free)
id: TASK-E01-b2c4

# External IDs (sequential per tool)
external_ids:
  jira: PROJ-456
  azure_devops: 1234
  linear: TEAM-789
  github: 234
```

### When to Choose
- ✅ You use Conductor.build for parallel development
- ✅ You have distributed teams (multiple developers, branches)
- ✅ You need bulletproof collision prevention
- ✅ You're willing to map internal → external IDs for PM tools

---

## Option 2: Sequential + File Locking

### Format
```
TASK-{prefix}-{number}

Examples:
TASK-042               # Simple task
TASK-E01-005           # Task 5 in Epic 001
TASK-DOC-012           # Documentation task 12
```

### How It Works
- **Counter file**: `.claude/state/task_id_counter.txt`
- **Lock file**: `.claude/state/task_id.lock`
- **Atomic increment**: File lock → read → increment → write → unlock
- **Per-prefix counters**: Separate sequences for each prefix

### Pros
- ✅ **Familiar format**: Users expect sequential numbers
- ✅ **PM tool native**: Direct mapping to JIRA/Azure DevOps/Linear
- ✅ **Order visible**: Easy to see task creation order
- ✅ **Simple mapping**: No external ID table needed

### Cons
- ⚠️ **Lock dependency**: Requires `fcntl` (doesn't work on all filesystems)
- ❌ **Conductor.build issues**: Lock conflicts in parallel worktrees
- ❌ **Distributed teams**: Requires central coordination
- ⚠️ **Lock contention**: Performance issues with high concurrency
- ⚠️ **Single point of failure**: Lock file corruption breaks creation

### When to Choose
- ✅ Single developer or small co-located team
- ✅ Single repository (no Conductor.build)
- ✅ PM tool integration is highest priority
- ✅ Users strongly prefer sequential numbering

---

## Option 3: Keep Current (Not Recommended)

### Why Not
- ❌ **Already has duplicates**: TASK-003 appears twice
- ❌ **Inconsistent formats**: 5+ formats in use (TASK-004, TASK-004A, TASK-030B-1)
- ❌ **No validation**: Users can create arbitrary IDs
- ❌ **Race conditions**: Multiple sessions create same ID

### Only Choose If
- You're willing to manually deduplicate IDs
- You don't use Conductor.build
- Your team is very small (1-2 people)
- You rarely create tasks concurrently

---

## Recommended Decision: Hash-Based

### Why This is Best for Taskwright

1. **Conductor.build is Core Feature**
   - Taskwright explicitly supports parallel worktrees
   - File locks don't work across worktrees
   - Hash-based IDs work perfectly in parallel

2. **Distributed Collaboration**
   - Multiple developers can create tasks simultaneously
   - No coordination or central authority needed
   - Works across branches, forks, remotes

3. **Future-Proof**
   - Scales to thousands of tasks
   - No format changes needed as project grows
   - Mathematical collision prevention

4. **PM Tool Flexibility**
   - Can map to ANY external format
   - Each tool gets its preferred ID format
   - Bidirectional mapping maintained

### Implementation Plan (3 Weeks)

**Week 1: Core ID Generation**
- Implement hash generator (`lib/id_generator.py`)
- Add collision checking
- Unit tests (1,000+ ID generation, zero collisions)
- Update `/task-create` command

**Week 2: PM Tool Mapping**
- Implement mapper (`lib/external_id_mapper.py`)
- JSON persistence for mappings
- Bidirectional lookup
- Update task frontmatter schema

**Week 3: Migration**
- Generate hash IDs for all existing tasks
- Preserve old IDs in `legacy_id` field
- Update cross-references
- Documentation updates

---

## Quick Start: Try It Now

```bash
# Run the proof-of-concept
python3 docs/research/task-id-poc.py

# Generates:
# - 5 sample task IDs (with prefixes)
# - 3 subtask IDs (dot notation)
# - PM tool mappings (JIRA, Azure DevOps, Linear, GitHub)
# - 1,000 collision-free IDs (validation)
```

---

## Questions to Answer

### Q: Will users hate hash-based IDs?

**A**: Users rarely type task IDs manually. Most workflows:
- `/task-work` autocomplete (shell completion)
- Copy/paste from `/task-status` output
- Click links in markdown files
- IDE integration (future feature)

Hash length is same as sequential: `TASK-E01-b2c4` (13 chars) vs `TASK-E01-042` (12 chars)

### Q: What about existing JIRA/Azure DevOps integration?

**A**: Mapping table handles this:
- Taskwright uses hash internally
- JIRA sees sequential `PROJ-456`
- Azure DevOps sees integer `1234`
- Mapping is automatic and transparent

### Q: Can we switch later if it doesn't work?

**A**: Yes, but costly:
- Mapping table enables future format changes
- Store current ID in `legacy_id` field
- Can migrate to sequential later if needed
- Better to get it right now

### Q: How do we handle the migration?

**A**: Automated script:
```bash
# Generate hash IDs for all tasks
./scripts/migrate-task-ids.sh

# Preserves:
# - Old ID in legacy_id field
# - All cross-references updated
# - Git history maintained
# - Rollback script provided
```

---

## Final Recommendation

**Choose Hash-Based (Option 1)** if:
- ✅ You use or plan to use Conductor.build
- ✅ You have multiple developers
- ✅ You need bulletproof collision prevention
- ✅ You're willing to invest 3 weeks in implementation

**Choose Sequential + Lock (Option 2)** if:
- ✅ Single developer or very small team
- ✅ No Conductor.build usage
- ✅ PM tool native IDs are critical
- ✅ Users strongly prefer sequential numbers

**Choose Status Quo (Option 3)** if:
- ❌ You like manually fixing duplicate IDs
- ❌ You don't mind inconsistent formats
- ❌ Race conditions are acceptable

---

## Next Steps

1. **Review this guide**: Understand trade-offs
2. **Run POC**: `python3 docs/research/task-id-poc.py`
3. **Decide**: Hash-based vs Sequential + Lock
4. **Confirm**: Reply with chosen approach
5. **Implement**: Create task with `/task-create` for chosen approach

---

## References

- [Full Analysis](./task-id-strategy-analysis.md) - Detailed technical analysis
- [Proof of Concept](./task-id-poc.py) - Working demonstration
- [Beads Issue Tracker](https://github.com/steveyegge/beads#bd---beads-issue-tracker-) - Original inspiration
