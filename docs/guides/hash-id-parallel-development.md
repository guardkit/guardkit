# Hash-Based ID Parallel Development with Conductor.build

This guide explains how to leverage Conductor.build worktrees for parallel development of the hash-based ID implementation, and more generally for any parallel development workflow.

## Overview

Hash-based task IDs enable safe concurrent task creation across multiple worktrees with zero collision risk. This makes them ideal for parallel development workflows using [Conductor.build](https://conductor.build).

### Why Hash-Based IDs Enable Parallel Development

**Sequential IDs** (e.g., TASK-001, TASK-002):
- ❌ Require coordination to prevent duplicates
- ❌ Create merge conflicts when multiple developers create tasks
- ❌ Need lock files or other synchronization mechanisms

**Hash-Based IDs** (e.g., TASK-a3f8, TASK-b2c4):
- ✅ Mathematically guaranteed unique (collision-free)
- ✅ No coordination needed across worktrees
- ✅ Clean merges - no ID conflicts
- ✅ Perfect for Conductor.build parallel workflows

## Hash-Based ID Implementation Wave Strategy

The hash-based ID implementation itself is organized into 4 waves to demonstrate parallel development:

- **Wave 0**: Foundation (Days 1-3) - Sequential
- **Wave 1**: Parallel Development (Days 4-8) - 3 concurrent worktrees
- **Wave 2**: Migration (Days 9-12) - Sequential
- **Wave 3**: Validation (Days 13-15) - Sequential

## Wave 1: Parallel Development Example

### Setup Worktrees

```bash
# Create 3 worktrees for parallel development
conductor worktree create hash-id-integration    # Worktree A
conductor worktree create hash-id-pm-tools       # Worktree B
conductor worktree create hash-id-frontmatter    # Worktree C
```

### Worktree Assignments

**Worktree A (Integration Layer)**:
- TASK-C38F: Update /task-create to use hash-based IDs
- TASK-2BF7: Add prefix support and inference

**Worktree B (PM Tool Integration)**:
- TASK-223C: Implement external ID mapper
- TASK-4679: Add JSON persistence for mappings

**Worktree C (Schema Updates)**:
- TASK-7A96: Update task frontmatter schema

### Execution

```bash
# Terminal 1 (Worktree A)
cd hash-id-integration
/task-work TASK-C38F
/task-work TASK-2BF7

# Terminal 2 (Worktree B)
cd hash-id-pm-tools
/task-work TASK-223C
/task-work TASK-4679

# Terminal 3 (Worktree C)
cd hash-id-frontmatter
/task-work TASK-7A96
```

### Merge Strategy

Merge worktrees in dependency order:

1. **Worktree C (Schema)** - Merge first (smallest changes, foundation for others)
2. **Worktree B (PM Tools)** - Merge second (independent feature)
3. **Worktree A (Integration)** - Merge last (depends on schema)

```bash
# Merge order example
git checkout main
git merge hash-id-frontmatter     # Schema updates first
git merge hash-id-pm-tools        # PM tools second
git merge hash-id-integration     # Integration last
```

## Benefits of Hash-Based IDs for Parallel Development

### Time Savings

- **20-33% faster** completion with parallel development
- Multiple tasks can be worked on simultaneously without ID conflicts
- No waiting for sequential ID assignment

### Safety Guarantees

- **Zero ID collisions** across worktrees (mathematically guaranteed)
- **Safe merging** - no sequential counter conflicts
- **Independent testing** in each worktree
- **No coordination overhead** - developers work independently

### Workflow Improvements

- **No lock files** - no need for ID reservation mechanisms
- **Clean merges** - ID conflicts eliminated
- **Easy rollback** - worktrees are independent
- **Flexible scheduling** - work on tasks in any order

## General Parallel Development Workflow

### 1. Plan Task Dependencies

Before starting parallel development:

1. Identify independent tasks (can run in parallel)
2. Identify dependent tasks (must run sequentially)
3. Group independent tasks into worktrees
4. Plan merge order based on dependencies

### 2. Create Worktrees

```bash
# Create worktrees for independent task groups
conductor worktree create feature-a
conductor worktree create feature-b
conductor worktree create feature-c
```

### 3. Execute Tasks in Parallel

```bash
# Terminal 1
cd feature-a
/task-create "Implement feature A" prefix:FEA
# Created: TASK-FEA-h8j3
/task-work TASK-FEA-h8j3

# Terminal 2
cd feature-b
/task-create "Implement feature B" prefix:FEB
# Created: TASK-FEB-k2m9
/task-work TASK-FEB-k2m9

# Terminal 3
cd feature-c
/task-create "Implement feature C" prefix:FEC
# Created: TASK-FEC-n7p4
/task-work TASK-FEC-n7p4
```

**Note**: Each task gets a unique hash-based ID with no collisions!

### 4. Merge in Dependency Order

```bash
# Merge foundation tasks first, dependent tasks last
git checkout main
git merge feature-c  # Foundation (if C is a dependency)
git merge feature-b  # Independent feature
git merge feature-a  # Depends on C
```

## Timeline Comparisons

### Solo Developer (Sequential)
- **Wave 1 Duration**: 8-10 days
- **Total Project**: 15-18 days
- **Tasks per day**: 1-2 tasks

### Team (Parallel - 3 developers)
- **Wave 1 Duration**: 3-4 days (66% faster)
- **Total Project**: 10-12 days (33% faster)
- **Tasks per day**: 3-4 tasks (parallel)

### AI Swarm (Parallel - Conductor.build)
- **Wave 1 Duration**: 2-3 days (75% faster)
- **Total Project**: 8-10 days (44% faster)
- **Tasks per day**: 5+ tasks (parallel)

## Troubleshooting Parallel Development

### Problem: Merge Conflicts in Task Files

**Symptom**: Git merge conflicts in task frontmatter

**Solution**:
```bash
# Hash IDs prevent ID conflicts, but file paths may conflict
# Use different prefixes for each worktree to avoid path conflicts
conductor worktree create feature-a  # Use prefix FEA
conductor worktree create feature-b  # Use prefix FEB
```

### Problem: State File Conflicts

**Symptom**: Conflicts in `.claude/state/task_counter.json`

**Solution**:
```bash
# Hash-based IDs don't use task_counter.json
# If you see this, you're still using sequential IDs
# Ensure hash ID generator is properly configured
```

### Problem: Dependent Tasks Block Progress

**Symptom**: Worktree B can't proceed because it needs changes from Worktree A

**Solution**:
1. Merge Worktree A early (partial merge)
2. Rebase Worktree B on updated main
3. Continue work in Worktree B

```bash
# Partial merge strategy
git checkout main
git merge worktree-a        # Merge dependency
cd ../worktree-b
git rebase main             # Get updates
/task-work TASK-xxx         # Continue
```

### Problem: Conductor.build State Sync Issues

**Symptom**: Task state not syncing across worktrees

**Solution**:
```bash
# Taskwright uses symlinks for state persistence
# Verify symlinks are correct
ls -la .claude/state/

# Should show symlinks to main repo's .claude/state/
# If not, re-run installer
./installer/scripts/install.sh
```

## Best Practices

### 1. Use Prefixes for Organization

```bash
# Use meaningful prefixes to group related tasks
/task-create "Auth feature" prefix:AUTH
/task-create "UI component" prefix:UI
/task-create "API endpoint" prefix:API
```

### 2. Keep Worktrees Focused

- Each worktree should work on related tasks
- Avoid cross-cutting changes across all worktrees
- Limit to 3-5 tasks per worktree

### 3. Merge Frequently

- Don't let worktrees diverge too far from main
- Merge foundation tasks early
- Rebase worktrees on updated main regularly

### 4. Test in Each Worktree

```bash
# Each worktree should pass tests independently
cd worktree-a
/task-work TASK-xxx  # Includes Phase 4.5 test enforcement
# Only merge if tests pass
```

### 5. Document Dependencies

```markdown
# In task frontmatter or implementation notes
depends_on: [TASK-a3f8, TASK-b2c4]
blocks: [TASK-c5d7]
```

## See Also

- [Implementation Tasks Summary](../research/implementation-tasks-summary.md) - Wave-based execution plan
- [Task ID Strategy Analysis](../research/task-id-strategy-analysis.md) - Technical architecture
- [Task ID Decision Guide](../research/task-id-decision-guide.md) - Why hash-based IDs?
- [Conductor.build Documentation](https://conductor.build) - Parallel development workflows
- [External ID Mapping](hash-id-pm-tools.md) - PM tool integration with hash IDs

## Example: Full Parallel Workflow

Here's a complete example of parallel development with hash-based IDs:

```bash
# 1. Create feature branch and worktrees
git checkout -b feature/parallel-demo
conductor worktree create auth-system
conductor worktree create payment-system
conductor worktree create notification-system

# 2. Create tasks in parallel (different terminals)
# Terminal 1
cd auth-system
/task-create "User login" prefix:AUTH
# Created: TASK-AUTH-h8j3
/task-work TASK-AUTH-h8j3

# Terminal 2
cd payment-system
/task-create "Payment processing" prefix:PAY
# Created: TASK-PAY-k2m9
/task-work TASK-PAY-k2m9

# Terminal 3
cd notification-system
/task-create "Email notifications" prefix:NOTIF
# Created: TASK-NOTIF-n7p4
/task-work TASK-NOTIF-n7p4

# 3. All tasks create unique IDs - no conflicts!

# 4. Merge in order (after all pass tests)
git checkout feature/parallel-demo
git merge auth-system
git merge payment-system
git merge notification-system

# 5. Push feature branch
git push origin feature/parallel-demo
```

**Result**: 3 tasks completed in parallel with zero ID conflicts and clean merges!
