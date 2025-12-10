---
id: TASK-DEBUG-A21C
title: Investigate task-complete not moving files in Conductor workspaces
status: completed
task_type: review
created: 2025-11-27T03:00:00Z
updated: 2025-11-27T08:20:00Z
completed_at: 2025-11-27T08:20:00Z
priority: high
tags: [debugging, conductor, task-complete, git-worktrees]
complexity: 5
decision_required: true
review_results:
  mode: debugging
  depth: standard
  finding: false_alarm
  root_cause: "Tasks never completed, not a technical issue"
  tasks_initially_completed: 3
  tasks_completed_during_investigation: 2
  total_tasks_completed: 5
  report_path: .claude/task-plans/TASK-DEBUG-A21C-investigation-report.md
  recommendation: accept
  decision: accept
  confidence: high_95_percent
  outcome: validated_conductor_works_correctly
---

# Task: Investigate task-complete Not Moving Files in Conductor Workspaces

## Context

When using Conductor.build workspaces (Git worktrees) to work on documentation tasks from TASK-DOC-F3BA-IMPLEMENTATION-GUIDE.md, the `/task-complete` command was run on completed tasks before merging the worktrees back to main. However, the task files are still showing up in `tasks/backlog/documentation/` instead of being moved to `tasks/completed/`.

**Affected Tasks** (from TASK-DOC-F3BA implementation):
- TASK-DOC-0801 (Update CLAUDE.md)
- TASK-DOC-443B (Review task detection)
- TASK-DOC-9FFC (Agent-format relationship)
- TASK-DOC-EDB0 (Task-work integration)
- TASK-DOC-83F0 (Create missing guides)

**Historical Context**:
- This issue occurred early on when first using Conductor app
- Was previously resolved
- May have regressed due to recent changes to `.claude/` directory in repo

## Objective

Conduct a systematic review to:
1. **Verify task-complete behavior** in Conductor worktree vs main branch
2. **Identify root cause** of file not being moved
3. **Check .claude directory symlinks** for potential issues
4. **Validate state synchronization** across worktrees
5. **Generate fix recommendations** or document workaround

## Scope

### Investigation Areas

1. **Task File Status**:
   - Check if tasks have `status: completed` in frontmatter
   - Verify file locations (still in backlog vs moved to completed)
   - Compare timestamps (when completed vs when merged)

2. **Conductor/Git Worktree Behavior**:
   - How `.claude/state` symlinks work across worktrees
   - Whether task-complete operates on worktree or main repo
   - State persistence mechanism

3. **.claude Directory Structure**:
   - Verify symlinks: `.claude/commands`, `.claude/agents`, `.claude/state`
   - Check if recent changes broke symlink architecture
   - Validate state directory permissions and accessibility

4. **task-complete Command Behavior**:
   - Read task-complete command specification
   - Understand expected file movement logic
   - Check if command respects worktree context

5. **Git Merge Impact**:
   - Does merging worktree preserve task status changes?
   - Are file moves (backlog → completed) captured in git?
   - Potential conflict resolution that reverted changes?

## Review Methodology

### Phase 1: Current State Assessment (15 min)

Check current status of affected tasks:

```bash
# List all TASK-DOC-* files in backlog
ls -la tasks/backlog/documentation/TASK-DOC-*.md

# Check their frontmatter status
for task in tasks/backlog/documentation/TASK-DOC-0801*.md \
            tasks/backlog/documentation/TASK-DOC-443B*.md \
            tasks/backlog/documentation/TASK-DOC-9FFC*.md \
            tasks/backlog/documentation/TASK-DOC-EDB0*.md \
            tasks/backlog/documentation/TASK-DOC-83F0*.md; do
  echo "=== $task ==="
  head -20 "$task" | grep "status:"
done

# Check if they exist in completed folder
ls -la tasks/completed/TASK-DOC-*.md 2>/dev/null || echo "None in completed/"
```

### Phase 2: .claude Directory Validation (10 min)

Verify symlink architecture:

```bash
# Check main .claude directory
ls -la .claude/

# Check symlinks
readlink .claude/commands
readlink .claude/agents
readlink .claude/state

# Verify state directory
ls -la .claude/state/

# Check permissions
ls -ld ~/.agentecflow/state/
```

### Phase 3: Git History Analysis (15 min)

Check what happened during merge:

```bash
# Find recent merges related to documentation tasks
git log --oneline --grep="TASK-DOC" -10

# Check if task files were moved in commits
git log --follow --oneline tasks/backlog/documentation/TASK-DOC-0801*.md

# Check for potential reverts or conflicts
git log --all --full-history -- "tasks/completed/TASK-DOC-*"
```

### Phase 4: task-complete Command Review (20 min)

Understand expected behavior:

```bash
# Find task-complete command spec
ls -la installer/core/commands/task-complete.md

# If it's a Python script, check implementation
find . -name "*task-complete*" -type f
```

Read command specification to understand:
- How it determines source and destination paths
- Whether it uses `.claude/state` for tracking
- If it respects worktree context vs main repo context

### Phase 5: Reproduce Issue (20 min)

Try to reproduce the issue in controlled environment:

```bash
# Create test worktree
conductor create-worktree test-task-complete main

# Create dummy task in worktree
cd test-task-complete
echo "---
id: TASK-TEST-0001
status: backlog
---
# Test Task" > tasks/backlog/TASK-TEST-0001-test.md

# Try completing it in worktree
# [Attempt /task-complete TASK-TEST-0001]

# Check if file moved
ls tasks/backlog/TASK-TEST-0001*.md
ls tasks/completed/TASK-TEST-0001*.md

# Return to main and check
cd ..
git merge test-task-complete
ls tasks/backlog/TASK-TEST-0001*.md
ls tasks/completed/TASK-TEST-0001*.md
```

### Phase 6: Hypothesis Testing (30 min)

**Hypothesis 1**: task-complete operates on main repo, not worktree
- **Test**: Run task-complete in worktree, check where file is moved
- **Evidence**: File location after command

**Hypothesis 2**: State symlinks broken, command can't track completions
- **Test**: Verify symlink targets exist and are accessible from worktree
- **Evidence**: Symlink validation output

**Hypothesis 3**: Git merge reverts file moves
- **Test**: Check git merge commits for file movement records
- **Evidence**: Git log showing file renames

**Hypothesis 4**: Command requires git commit before file move persists
- **Test**: Complete task, commit, then merge
- **Evidence**: Whether committed moves survive merge

**Hypothesis 5**: Recent .claude changes broke state synchronization
- **Test**: Compare .claude setup before/after recent changes
- **Evidence**: Git diff of .claude directory structure

## Expected Deliverables

### 1. Investigation Report

Create: `.claude/task-plans/TASK-DEBUG-A21C-investigation-report.md`

**Structure**:
```markdown
# Task-Complete Conductor Issue Investigation

## Executive Summary
- Issue confirmed: [YES/NO]
- Root cause identified: [DESCRIPTION]
- Workaround available: [YES/NO]
- Fix required: [YES/NO]

## Findings by Phase

### Phase 1: Current State
[Status of 5 affected tasks]

### Phase 2: .claude Directory
[Symlink validation results]

### Phase 3: Git History
[Merge history analysis]

### Phase 4: Command Behavior
[task-complete specification review]

### Phase 5: Reproduction
[Test results]

### Phase 6: Hypothesis Testing
[Which hypothesis confirmed]

## Root Cause

[Detailed explanation of why task-complete doesn't work in worktrees]

## Impact Assessment

- Severity: [HIGH/MEDIUM/LOW]
- Affected workflows: [List]
- Workaround complexity: [HIGH/MEDIUM/LOW]
```

### 2. Fix Recommendations

**If root cause is identified**:
- Provide specific fix (code change, config change, workflow change)
- Estimate effort to implement fix
- List alternative workarounds

**If root cause is unclear**:
- Document known symptoms
- Suggest additional investigation steps
- Recommend interim workaround

### 3. Workaround Documentation

**Immediate workaround** (if available):
```bash
# Step-by-step instructions to manually move completed tasks
# in Conductor worktree environment
```

**Long-term solution**:
- Fix task-complete to work in worktrees, OR
- Document workflow: "complete tasks only in main branch", OR
- Automation script to sync completed tasks after merge

## Acceptance Criteria

- [ ] All 5 affected tasks status verified (backlog vs completed)
- [ ] .claude symlinks validated in main and worktree contexts
- [ ] Git merge history analyzed for file movements
- [ ] task-complete command behavior documented
- [ ] Issue reproduced in controlled test environment
- [ ] Root cause hypothesis tested and confirmed/rejected
- [ ] Investigation report created with findings
- [ ] Fix recommendation provided (or workaround documented)
- [ ] Impact assessment completed

## Success Criteria

**Minimum** (Understanding):
- Root cause identified with high confidence
- Workaround documented for immediate use
- Decision on fix vs accept-and-document

**Ideal** (Resolution):
- Fix implemented and tested
- Conductor workflow updated
- Documentation updated
- Test cases added to prevent regression

## Related Context

**Previous Resolution**:
- User mentioned: "We had this early on using the Conductor app and resolved it"
- **Action**: Search git history for previous fix
- **Command**: `git log --all --grep="conductor" --grep="worktree" --grep="task-complete" -i`

**Recent .claude Changes**:
- User mentioned: "Recent messing about with the .claude directory"
- **Action**: Review recent commits to .claude directory
- **Command**: `git log --oneline -- .claude/ | head -20`

**Installation Script**:
- Symlinks created by: `installer/scripts/install.sh`
- **Action**: Review install script for state symlink setup
- **File**: `installer/scripts/install.sh`

## Review Mode

**Recommended**: `debugging` (root cause analysis)

**Alternative**: `decision` (if root cause unclear, decide between fix vs workaround)

**Depth**: `standard` (1-2 hours)

## Next Steps

```bash
# Execute this review
/task-review TASK-DEBUG-A21C --mode=debugging --depth=standard

# After review, decision checkpoint:
# [A]ccept - Document findings, no fix needed
# [I]mplement - Create task to fix task-complete for worktrees
# [R]evise - Need deeper investigation
# [C]ancel - Issue not reproducible
```

## Notes

- This is a **debugging review** - focus on root cause analysis
- User expects this might be related to .claude directory changes
- Historical context: issue was previously fixed, may have regressed
- Affected workflow: Conductor parallel development (critical for productivity)
- Priority: High (blocks efficient parallel development)

## Files to Examine

**Task Files**:
- `tasks/backlog/documentation/TASK-DOC-0801-*.md`
- `tasks/backlog/documentation/TASK-DOC-443B-*.md`
- `tasks/backlog/documentation/TASK-DOC-9FFC-*.md`
- `tasks/backlog/documentation/TASK-DOC-EDB0-*.md`
- `tasks/backlog/documentation/TASK-DOC-83F0-*.md`

**Infrastructure**:
- `.claude/` directory structure
- `~/.agentecflow/state/` directory
- `installer/scripts/install.sh`
- `installer/core/commands/task-complete.md`

**Git History**:
- Recent commits to .claude/
- Merge commits for documentation worktrees
- Previous conductor-related fixes
