---
id: TASK-053
title: Update documentation for hash-based IDs
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: medium
tags: [documentation, hash-ids]
complexity: 4
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update documentation for hash-based IDs

## Description

Update all documentation to reflect the new hash-based task ID system. This includes command specifications, workflow guides, examples, and the main CLAUDE.md file. Ensure users understand the new format and benefits.

## Acceptance Criteria

- [ ] Update CLAUDE.md with hash ID format and benefits
- [ ] Update task-create.md with new ID examples
- [ ] Update all workflow guides with hash ID examples
- [ ] Update quick reference with new ID format
- [ ] Add FAQ section addressing common questions
- [ ] Update all code examples and screenshots
- [ ] Add prefix usage guide (E01, DOC, FIX, etc.)
- [ ] Document PM tool mapping system
- [ ] **Add implementation strategy guide (wave-based development)**
- [ ] **Link to research documents from main documentation**
- [ ] **Document Conductor.build parallel development workflow**
- [ ] **Add troubleshooting guide for parallel development**

## Test Requirements

- [ ] Validate all markdown files render correctly
- [ ] Verify all internal links work
- [ ] Check all code examples are accurate
- [ ] Review for consistency across all docs
- [ ] Spell check and grammar review

## Implementation Notes

### Files to Update

**Primary Documentation**:
1. `CLAUDE.md` - Main project documentation
2. `installer/global/commands/task-create.md` - Command specification
3. `docs/guides/guardkit-workflow.md` - Workflow guide
4. `docs/guides/quick-reference.md` - Quick reference

**Secondary Documentation**:
5. `README.md` - Project README
6. `docs/workflows/*.md` - All workflow documents
7. `docs/guides/*.md` - All guide documents
8. Template files that show task examples

**Implementation & Research Documentation**:
9. `docs/research/implementation-tasks-summary.md` - Link from main docs
10. `docs/research/task-id-strategy-analysis.md` - Reference for technical details
11. `docs/research/task-id-decision-guide.md` - Reference for decision rationale
12. Create: `docs/guides/hash-id-parallel-development.md` - Conductor.build workflow guide

### New Sections to Add

**1. Hash-Based ID Overview** (CLAUDE.md)
```markdown
## Task ID Format

GuardKit uses hash-based task IDs to prevent duplicates and support concurrent creation:

### Format
- Simple: `TASK-{hash}` (e.g., TASK-a3f8)
- With prefix: `TASK-{prefix}-{hash}` (e.g., TASK-E01-b2c4)
- With subtask: `TASK-{prefix}-{hash}.{number}` (e.g., TASK-E01-b2c4.1)

### Benefits
- ✅ Zero duplicates (mathematically guaranteed)
- ✅ Concurrent creation safe
- ✅ Conductor.build compatible
- ✅ PM tool integration via mapping

### Common Prefixes
- `E{number}`: Epic-related tasks (E01, E02)
- `DOC`: Documentation tasks
- `FIX`: Bug fixes
- `TEST`: Test-related tasks
- Custom prefixes: Any 2-4 uppercase alphanumeric
```

**2. PM Tool Mapping** (new guide)
```markdown
## PM Tool Integration

GuardKit maps internal hash IDs to external sequential IDs automatically:

Internal ID: TASK-E01-b2c4
External IDs:
  JIRA: PROJ-456
  Azure DevOps: 1234
  Linear: TEAM-789
  GitHub: #234

This mapping is:
- Automatic when tasks are exported
- Bidirectional (internal ↔ external)
- Persistent across sessions
- Transparent to users
```

**3. Migration Note** (FAQ entry only, no separate guide)
```markdown
## Migrating Existing Tasks

**Q: What about my existing tasks with old IDs?**

A: Run the personal migration script (documented in the script itself):

```bash
# Preview changes
python3 scripts/migrate-my-tasks.py --dry-run

# Execute migration
python3 scripts/migrate-my-tasks.py --execute

# If something goes wrong
bash .claude/state/rollback-migration.sh
```

Old IDs are preserved in `legacy_id` field. See script source for details.
```

**4. FAQ Section**
```markdown
## Hash-Based IDs FAQ

**Q: Why hash-based instead of sequential?**
A: Prevents duplicates in concurrent and distributed workflows. Critical for Conductor.build support.

**Q: Will users hate typing TASK-a3f8?**
A: Users rarely type IDs manually. Shell completion, copy/paste, and IDE integration handle this.

**Q: How do PM tools handle hash IDs?**
A: They don't see them! GuardKit maps internal hash IDs to external sequential IDs automatically.

**Q: Can I still use sequential IDs?**
A: No. Hash-based IDs are mandatory to prevent duplicates.

**Q: What about existing tasks?**
A: Run `python3 scripts/migrate-my-tasks.py` (see script for usage). Old IDs are preserved in legacy_id field.

**Q: How long are the IDs?**
A: 4-6 characters for the hash, plus optional 2-4 char prefix. Total: 9-15 characters.
```

**5. Wave-Based Implementation Strategy** (new guide: `docs/guides/hash-id-parallel-development.md`)
```markdown
# Hash-Based ID Parallel Development with Conductor.build

This guide explains how to leverage Conductor.build worktrees for parallel development
of the hash-based ID implementation.

## Overview

The hash-based ID implementation is organized into 4 waves:

- **Wave 0**: Foundation (Days 1-3) - Sequential
- **Wave 1**: Parallel Development (Days 4-8) - 3 concurrent worktrees
- **Wave 2**: Migration (Days 9-12) - Sequential
- **Wave 3**: Validation (Days 13-15) - Sequential

## Wave 1: Parallel Development

### Setup Worktrees

```bash
conductor worktree create hash-id-integration    # Worktree A
conductor worktree create hash-id-pm-tools       # Worktree B
conductor worktree create hash-id-frontmatter    # Worktree C
```

### Worktree Assignments

**Worktree A (Integration Layer)**:
- TASK-048: Update /task-create to use hash-based IDs
- TASK-054: Add prefix support and inference

**Worktree B (PM Tool Integration)**:
- TASK-049: Implement external ID mapper
- TASK-050: Add JSON persistence for mappings

**Worktree C (Schema Updates)**:
- TASK-051: Update task frontmatter schema

### Execution

```bash
# Terminal 1 (Worktree A)
cd hash-id-integration
/task-work TASK-048
/task-work TASK-054

# Terminal 2 (Worktree B)
cd hash-id-pm-tools
/task-work TASK-049
/task-work TASK-050

# Terminal 3 (Worktree C)
cd hash-id-frontmatter
/task-work TASK-051
```

### Merge Strategy

1. Worktree C (Schema) - smallest changes
2. Worktree B (PM Tools) - independent feature
3. Worktree A (Integration) - depends on schema

## Benefits

- **20-33% faster** completion with parallel development
- **Zero ID collisions** across worktrees (hash-based IDs)
- **Safe merging** - no sequential counter conflicts
- **Independent testing** in each worktree

## See Also

- [Implementation Tasks Summary](../research/implementation-tasks-summary.md)
- [Strategy Analysis](../research/task-id-strategy-analysis.md)
- [Conductor.build Documentation](https://conductor.build)
```

**6. Links from Main Documentation** (CLAUDE.md)
```markdown
## Hash-Based Task IDs

For detailed information about the hash-based ID system:

- **Implementation Guide**: [Wave-Based Parallel Development](docs/guides/hash-id-parallel-development.md)
- **Technical Analysis**: [Task ID Strategy Analysis](docs/research/task-id-strategy-analysis.md)
- **Decision Rationale**: [Task ID Decision Guide](docs/research/task-id-decision-guide.md)
- **Implementation Plan**: [Implementation Tasks Summary](docs/research/implementation-tasks-summary.md)
```

### Examples to Update

**Before (Sequential)**:
```bash
/task-create "Fix login bug"
# Created: TASK-042

/task-work TASK-042
```

**After (Hash-based)**:
```bash
/task-create "Fix login bug"
# Created: TASK-a3f8

/task-work TASK-a3f8

# With prefix
/task-create "Fix login bug" prefix:FIX
# Created: TASK-FIX-a3f8
```

### Update All Examples

Search for patterns and update:
- `TASK-\d{3}` → `TASK-{hash}` examples
- `TASK-042` → `TASK-a3f8` (use realistic hash)
- Add prefix examples where appropriate
- Show external ID mapping in PM tool sections

### Consistency Checks

- [ ] All examples use hash format
- [ ] No references to old sequential format
- [ ] Prefix usage is consistent
- [ ] External ID mapping is explained where relevant
- [ ] Migration guide is referenced for existing users
- [ ] Benefits are clearly stated
- [ ] **Wave-based implementation strategy documented**
- [ ] **Research documents linked from main documentation**
- [ ] **Conductor.build workflow explained**
- [ ] **Parallel development troubleshooting included**

### New Documentation Files to Create

**Create these new guides**:

1. **`docs/guides/hash-id-parallel-development.md`**
   - Conductor.build worktree setup
   - Wave 1 parallel execution strategy
   - Merge strategy and order
   - Troubleshooting parallel development
   - Timeline comparisons (solo vs team vs AI swarm)

2. **`docs/guides/hash-id-pm-tools.md`**
   - PM tool mapping concepts
   - JIRA integration examples
   - Azure DevOps integration examples
   - Linear integration examples
   - GitHub integration examples
   - Bidirectional lookup

**Note**: Migration documentation removed - TASK-052 is simplified for personal use only. Migration notes are in the script itself (`scripts/migrate-my-tasks.py`).

### Links to Add in Main Documentation

**In CLAUDE.md**, add new section:
```markdown
## Hash-Based Task IDs (New)

GuardKit uses collision-free hash-based task IDs:

### Format
- Simple: `TASK-a3f8`
- With prefix: `TASK-E01-b2c4`
- With subtask: `TASK-E01-b2c4.1`

### Documentation
- **Quick Start**: [Task ID Overview](#task-id-format)
- **Parallel Development**: [Conductor.build Workflow](docs/guides/hash-id-parallel-development.md)
- **PM Tools**: [External ID Mapping](docs/guides/hash-id-pm-tools.md)
- **Technical Details**: [Strategy Analysis](docs/research/task-id-strategy-analysis.md)
- **Implementation Plan**: [Tasks Summary](docs/research/implementation-tasks-summary.md)

### For Developers
If you're implementing the hash-based ID system:
- See [Implementation Tasks Summary](docs/research/implementation-tasks-summary.md) for wave-based execution plan
- Use Conductor.build for Wave 1 parallel development (20-33% faster)
- All tasks use `/task-work` for quality gates
```

**In README.md**, update features section:
```markdown
## Features

- **Hash-Based Task IDs**: Collision-free IDs support concurrent creation and Conductor.build parallel development
- **Quality Gates**: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)
- **PM Tool Integration**: Automatic mapping to JIRA, Azure DevOps, Linear, GitHub
- ...
```

## Dependencies

- TASK-052: Migration script (to reference in FAQ, but no separate guide needed)

## Related Tasks

- TASK-055: Integration testing (may reveal doc gaps)

## Test Execution Log

[Automatically populated by /task-work]
