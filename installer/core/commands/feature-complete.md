# Feature Complete - Merge and Archive AutoBuild Results

Complete autonomous task implementation by merging approved worktree changes to main branch and archiving AutoBuild state. Use after reviewing and approving AutoBuild output from `/feature-build`.

Supports two modes:
- **Single Task Mode**: `/feature-complete TASK-XXX` - Merge one task
- **Feature Mode**: `/feature-complete FEAT-XXX` - Merge all tasks in a feature

## Command Syntax

```bash
# Single task mode
/feature-complete TASK-XXX [options]

# Feature mode
/feature-complete FEAT-XXX [options]
```

## Available Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--dry-run` | Preview changes without merging | false |
| `--force` | Skip confirmation prompts | false |
| `--no-cleanup` | Keep worktree after merge | false |
| `--no-archive` | Skip archiving before deletion (delete artifacts immediately) | false |
| `--verbose` | Show detailed merge output | false |
| `--verify` | Re-run tests after merge | false |

---

## CLI Reference

The `/feature-complete` slash command invokes the Python CLI. You can also use the CLI directly from shell.

### From Claude Code (Slash Command)

```bash
# Single task
/feature-complete TASK-AUTH-001

# With dry-run preview
/feature-complete TASK-AUTH-001 --dry-run

# Feature mode
/feature-complete FEAT-A1B2

# Force merge without prompts
/feature-complete FEAT-A1B2 --force
```

### From Shell (Python CLI)

```bash
# Equivalent single task command
guardkit autobuild complete TASK-AUTH-001

# With dry-run preview
guardkit autobuild complete TASK-AUTH-001 --dry-run

# Feature mode
guardkit autobuild complete FEAT-A1B2

# Force merge without confirmation
guardkit autobuild complete FEAT-A1B2 --force

# Verify tests after merge
guardkit autobuild complete FEAT-A1B2 --verify

# Preview changes without merging
guardkit autobuild complete FEAT-A1B2 --dry-run --verbose
```

### CLI Command Reference

| Command | Description |
|---------|-------------|
| `guardkit autobuild complete TASK-XXX` | Merge single task worktree to main |
| `guardkit autobuild complete FEAT-XXX` | Merge feature worktree to main |
| `guardkit autobuild status [ID]` | Check build/merge status |
| `guardkit worktree cleanup [ID]` | Remove worktree after merge |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUARDKIT_LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `GUARDKIT_VERIFY_AFTER_MERGE` | false | Automatically run tests after merge |

## Examples

### Basic Usage

```bash
# Review and merge single task
/feature-complete TASK-ABC123

# Equivalent CLI command
guardkit autobuild complete TASK-ABC123
```

### Preview Before Merging

```bash
# See what will be merged
/feature-complete TASK-ABC123 --dry-run

# Detailed preview with verbose output
/feature-complete TASK-ABC123 --dry-run --verbose
```

### Force Merge Without Confirmation

```bash
# Merge directly (skip confirmation)
/feature-complete TASK-ABC123 --force

# Useful for CI/CD automation
guardkit autobuild complete FEAT-A1B2 --force
```

### Complete Feature with Verification

```bash
# Merge all feature tasks and re-run tests
/feature-complete FEAT-A1B2 --verify

# Keep worktree for inspection after merge
/feature-complete FEAT-A1B2 --no-cleanup
```

## How It Works

The `/feature-complete` command operates in two modes depending on the input:

### Mode Detection

```
/feature-complete FEAT-A1B2    → Feature Mode (merges all tasks in feature)
/feature-complete TASK-ABC123  → Single Task Mode (merges one task)
```

---

## Single Task Mode

For individual tasks (`TASK-XXX`), the command merges worktree changes to main branch:

### Merge Process

1. **Load task file** from `tasks/` directory
2. **Verify worktree exists** at `.guardkit/worktrees/TASK-XXX/`
3. **Check branch** is `autobuild/TASK-XXX`
4. **Preview changes** (unless `--dry-run` only or `--force`)
5. **Merge to main** using fast-forward or merge commit
6. **Update task status** from IN_PROGRESS to COMPLETED
7. **Archive AutoBuild state** to `.guardkit/archive/` (unless `--no-archive`)
8. **Delete `.guardkit/autobuild/TASK-XXX/`** (autobuild artifacts)
9. **Move task file** to `tasks/completed/`
10. **Cleanup worktree** (unless `--no-cleanup`)
11. **Run tests** (if `--verify`)

### Example Merge Output

```
══════════════════════════════════════════════════════════════
FEATURE COMPLETE: TASK-ABC123
══════════════════════════════════════════════════════════════

Task: Implement OAuth2 authentication
Status: Ready to merge
Worktree: .guardkit/worktrees/TASK-ABC123
Branch: autobuild/TASK-ABC123

Changes to merge:
  src/auth/oauth.py          | 120 ++++++++
  src/auth/models.py         |  45 ++++
  tests/test_oauth.py        |  80 ++++++
  3 files changed, 245 insertions(+)

Merge strategy: fast-forward
Target branch: main

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Proceed with merge? [Y/n]:
```

---

## Feature Mode

For features (`FEAT-XXX`), the command merges all tasks in sequence:

### Feature Mode Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     FEATURE MERGE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📁 Load Feature File                                           │
│     .guardkit/features/FEAT-XXX.yaml                            │
│                                                                 │
│  📋 Get Completed Tasks                                         │
│     ├── TASK-001 (status: completed)                            │
│     ├── TASK-002 (status: completed)                            │
│     ├── TASK-003 (status: completed)                            │
│     └── TASK-004 (status: completed)                            │
│                                                                 │
│  🔀 Merge Each Task                                             │
│     TASK-001: git merge autobuild/TASK-001                      │
│     TASK-002: git merge autobuild/TASK-002                      │
│     ... (in dependency order)                                   │
│                                                                 │
│  📊 Update Feature Status                                       │
│     .guardkit/features/FEAT-XXX.yaml → merged                   │
│                                                                 │
│  🗃️  Archive State                                              │
│     .guardkit/archive/FEAT-XXX/                                 │
│                                                                 │
│  🧹 Cleanup Worktrees                                           │
│     .guardkit/worktrees/FEAT-XXX/                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Feature Mode Phases

#### Phase 1: Load Feature
1. Load feature file from `.guardkit/features/FEAT-XXX.yaml`
2. Parse task list and completion status
3. Verify all worktrees exist

#### Phase 2: Merge Tasks
For each completed task in dependency order:
1. Preview changes for task
2. Merge worktree to main
3. Update task status in feature file
4. Continue to next task (or stop on failure)

#### Phase 3: Finalize
- Update feature status: `merged`
- Archive feature state to `.guardkit/archive/`
- Cleanup all worktrees
- Display final summary

### Feature Mode Example

```bash
# Merge entire feature
/feature-complete FEAT-A1B2

# Output:
# ══════════════════════════════════════════════════════════════
# FEATURE COMPLETE: FEAT-A1B2
# ══════════════════════════════════════════════════════════════
#
# Feature: User Authentication
# Status: Ready to merge
# Tasks: 4 completed
# Worktree: .guardkit/worktrees/FEAT-A1B2
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 1/4: TASK-001 - Create auth service interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Changes:
#   src/auth/interface.py      |  35 ++
#   tests/test_interface.py    |  20 +
#   2 files changed, 55 insertions(+)
#
# ✓ Merged to main
#
# ... (tasks 2-4 similar)
#
# ══════════════════════════════════════════════════════════════
# FEATURE RESULT: SUCCESS
# ══════════════════════════════════════════════════════════════
#
# Feature: User Authentication
# Status: MERGED
# Tasks: 4/4 merged
# Total changes: 245 insertions(+), 12 deletions(-)
#
# Next Steps:
#   1. Verify: git log --oneline -10
#   2. Deploy: Follow deployment process
#   3. Cleanup: Already completed
```

---

## When to Use /feature-complete

### Good Candidates
- AutoBuild completed successfully (Coach approved)
- Human reviewed changes and approved
- Ready to merge to main branch
- Want to archive build state
- Ready for deployment or further testing

### Use /task-work Instead
- Need to make changes before merging
- Want to run tests again
- Changes need rework
- Want to keep worktree for debugging

## Workflow Integration

### Single Task Workflow

```bash
# 1. Create task
/task-create "Implement OAuth2 authentication"
# Created: TASK-AUTH-001

# 2. Autonomous implementation
/feature-build TASK-AUTH-001
# → Creates worktree, runs Player-Coach loop
# → Preserves output for human review

# 3. Review worktree output
cd .guardkit/worktrees/TASK-AUTH-001
git diff main
# ... review changes ...

# 4. If approved, merge
/feature-complete TASK-AUTH-001

# 5. Complete task
/task-complete TASK-AUTH-001
```

### Feature Workflow

```bash
# 1. Plan feature
/feature-plan "Implement OAuth2 authentication"
# → Creates .guardkit/features/FEAT-A1B2.yaml
# → Creates tasks/backlog/oauth2/TASK-001.md ... TASK-004.md

# 2. Autonomous implementation of entire feature
/feature-build FEAT-A1B2
# → Executes tasks in wave order
# → Creates feature worktree

# 3. Review feature worktree
cd .guardkit/worktrees/FEAT-A1B2
git diff main
# ... review all changes ...

# 4. If approved, merge all tasks
/feature-complete FEAT-A1B2

# 5. Verify and complete tasks
/task-complete TASK-001 TASK-002 TASK-003 TASK-004

# 6. Verify deployment
git log --oneline -10
```

## State Management

### What Gets Saved

After successful merge:

```
.guardkit/
├── archive/                          # Gitignored, local-only
│   ├── TASK-ABC123/
│   │   ├── autobuild_state.json
│   │   ├── player_turn_1.json
│   │   ├── coach_turn_1.json
│   │   └── merge_summary.json
│   │
│   └── FEAT-A1B2/
│       ├── feature_state.yaml        # Archived from features/ before deletion
│       ├── task_results.json
│       └── merge_log.txt
│
├── autobuild/
│   └── [TASK-*/FEAT-* dirs removed]  # Deleted after merge
│
├── features/
│   └── [FEAT-A1B2.yaml removed]      # Archived then deleted
│
└── worktrees/
    └── [removed after cleanup]

tasks/
├── completed/
│   └── TASK-ABC123.md                # Moved from backlog/
└── backlog/
    └── [task files moved out]
```

### Archive Contents

**Task Archive** (TASK-XXX):
- `autobuild_state.json` - Final AI state
- `player_turn_N.json` - Player implementation reports
- `coach_turn_N.json` - Coach validation reports
- `merge_summary.json` - Merge details and changes

**Feature Archive** (FEAT-XXX):
- `feature_state.yaml` - Final feature state
- `task_results.json` - All task results
- `merge_log.txt` - Full merge transcript

## Troubleshooting

### "Worktree not found"

```bash
# Ensure worktree exists
ls .guardkit/worktrees/TASK-XXX/

# If missing, recreate from stashed state
/feature-build TASK-XXX --resume
```

### "Merge conflicts detected"

```bash
# Manual conflict resolution required
cd .guardkit/worktrees/TASK-XXX
git merge main
# ... resolve conflicts ...
git add -A
git commit -m "Resolve merge conflicts"

# Then complete merge
/feature-complete TASK-XXX
```

### "Task already completed"

```bash
# Task was already merged
# Check task status
grep status tasks/completed/TASK-XXX.md

# If already in main, verify:
git log --oneline | grep "TASK-XXX"

# If confirmed, just archive
/feature-complete TASK-XXX --no-cleanup
```

### "Feature not found"

```bash
# Ensure feature file exists
ls .guardkit/features/FEAT-XXX.yaml

# If missing, feature may have been deleted
# Complete tasks individually instead
/feature-complete TASK-001
/feature-complete TASK-002
```

## Dry-Run Preview

Preview changes without merging:

```bash
# Single task
/feature-complete TASK-ABC123 --dry-run

# Output shows exactly what would be merged:
# ── Changes in autobuild/TASK-ABC123 (not yet merged)
# src/auth/oauth.py          | 120 +++++
# src/auth/models.py         |  45 ++++
# tests/test_oauth.py        |  80 +++
# 3 files changed, 245 insertions(+)

# Feature
/feature-complete FEAT-A1B2 --dry-run --verbose

# Shows all tasks that would be merged in order
```

## Best Practices

1. **Always Review First**: Use `--dry-run` to preview changes
2. **Test After Merge**: Use `--verify` for critical tasks
3. **Keep History**: Archives are stored for audit trail
4. **Cleanup Worktrees**: Use `--no-cleanup` only for debugging
5. **Verify Main Branch**: Always check `git log` after merge
6. **Deploy Carefully**: Use gradual rollout strategies

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

### What This Command Does

This command operates in **two modes** based on the input ID:

1. **Single Task Mode** (`TASK-XXX`): Merge one task worktree to main
2. **Feature Mode** (`FEAT-XXX`): Merge all task worktrees in a feature to main

### Mode Detection

```python
def detect_mode(id_arg: str) -> str:
    if id_arg.startswith("FEAT-"):
        return "feature"
    elif id_arg.startswith("TASK-"):
        return "single_task"
    else:
        raise ValueError(f"Invalid ID format: {id_arg}. Use TASK-XXX or FEAT-XXX")
```

---

### Single Task Mode Execution

When the user invokes `/feature-complete TASK-XXX`:

1. **Load the task file** from `tasks/in_progress/` or `tasks/completed/`
2. **Verify worktree exists** at `.guardkit/worktrees/TASK-XXX/`
3. **Check branch** is `autobuild/TASK-XXX`
4. **Preview changes** (unless `--force` flag provided)
5. **Get user confirmation** (unless `--force` or `--dry-run` only)
6. **Execute merge via CLI** to main branch
7. **Update task status** to COMPLETED
8. **Archive state** to `.guardkit/archive/TASK-XXX/` (unless `--no-archive`)
9. **Delete `.guardkit/autobuild/TASK-XXX/`** artifacts
10. **Move task file** to `tasks/completed/`
11. **Cleanup worktree** (unless `--no-cleanup`)
12. **Display cleanup summary** (files deleted, bytes freed)
13. **Show final results** with merge details

#### Step 1: Verify Worktree Exists

```bash
# Check if worktree exists
if [ ! -d ".guardkit/worktrees/TASK-XXX" ]; then
    echo "Worktree not found for TASK-XXX"
    echo "Did you run /feature-build TASK-XXX yet?"
    exit 1
fi
```

#### Step 2: Preview Changes (if not --force)

```bash
# Show what will be merged
cd .guardkit/worktrees/TASK-XXX
git diff main --stat

# Example output:
# src/auth/oauth.py       | 120 +++++++++++
# src/auth/models.py      |  45 ++++
# tests/test_oauth.py     |  80 ++++++
# 3 files changed, 245 insertions(+)
```

#### Step 3: Get Confirmation (if not --dry-run or --force)

```bash
# Prompt user unless --force
if not args.force:
    echo "Proceed with merge? [Y/n]: "
    # Wait for input
    if not confirmed:
        exit 0  # User declined
```

#### Step 4: Execute Merge via CLI

```bash
# Execute actual merge
guardkit autobuild complete TASK-XXX [--dry-run] [--verify]
```

---

### Feature Mode Execution

When the user invokes `/feature-complete FEAT-XXX`:

1. **Load the feature file** from `.guardkit/features/FEAT-XXX.yaml`
2. **Parse task list** and completion status
3. **Verify all worktrees exist** for completed tasks
4. **Preview total changes** (unless `--force`)
5. **Get user confirmation** (unless `--force` or `--dry-run` only)
6. **Execute merges via CLI** in dependency order
7. **Update feature status** to MERGED
8. **Archive and cleanup artifacts** (Step 5 — archive, delete autobuild state, move tasks, display summary)
9. **Cleanup all worktrees** (unless `--no-cleanup`)
10. **Show final results** with summary

#### Step 1: Load Feature File

```bash
# Read feature file
feature = load_yaml(".guardkit/features/FEAT-XXX.yaml")

# Extract task list with status
tasks = feature["tasks"]  # List of task dicts with id, status, etc.
parallel_groups = feature["orchestration"]["parallel_groups"]
```

#### Step 2: Verify Worktrees

```bash
# For each completed task, verify worktree exists
for task in tasks:
    if task["status"] == "completed":
        worktree_path = f".guardkit/worktrees/{task['id']}"
        if not exists(worktree_path):
            error(f"Worktree missing for {task['id']}")
            return
```

#### Step 3: Preview Total Changes

```bash
# Show combined changes from all task worktrees
total_insertions = 0
total_deletions = 0
total_files = 0

for task in completed_tasks:
    # Get stats from each worktree
    cd .guardkit/worktrees/{task_id}
    git diff main --stat | parse()
    add to totals

# Display summary
print(f"Total changes: {total_files} files, +{ins} -{del}")
```

#### Step 4: Execute Merges

```bash
# Merge each task in dependency order (from parallel_groups)
for wave in parallel_groups:
    for task_id in wave:
        task = find_task(tasks, task_id)
        if task["status"] != "completed":
            continue

        # Execute merge for this task
        guardkit autobuild complete {task_id} --force [--verify]

        # Update task status in feature YAML
        # Change task.status from "completed" to "merged"
        update_feature_yaml(feature, task_id, "merged")
```

#### Step 5: Archive, Artifact Cleanup, and Task Finalization

```bash
# --- 5a: Archive feature state (unless --no-archive) ---
cleanup_summary = { "files_deleted": 0, "bytes_freed": 0 }

if not args.no_archive:
    archive_path = ".guardkit/archive/FEAT-XXX"
    mkdir -p archive_path

    # Archive feature YAML before deletion
    copy_file(".guardkit/features/FEAT-XXX.yaml", f"{archive_path}/feature_state.yaml")
    save_merge_summary(archive_path)
    print(f"  ✓ Archived feature state to {archive_path}/")
else:
    print("  ⏭️  Skipping archive (--no-archive)")

# --- 5b: Cleanup worktrees (unless --no-cleanup) ---
if not args.no_cleanup:
    for task in tasks:
        worktree_path = f".guardkit/worktrees/{task['id']}"
        if exists(worktree_path):
            size = get_dir_size(worktree_path)
            rm -rf worktree_path
            cleanup_summary["files_deleted"] += count_files(worktree_path)
            cleanup_summary["bytes_freed"] += size
    git worktree prune
    print(f"  ✓ Cleaned up worktrees")

# --- 5c: Delete autobuild state for merged tasks ---
for task in tasks:
    autobuild_task_path = f".guardkit/autobuild/{task['id']}"
    if exists(autobuild_task_path):
        size = get_dir_size(autobuild_task_path)
        rm -rf autobuild_task_path
        cleanup_summary["files_deleted"] += count_files(autobuild_task_path)
        cleanup_summary["bytes_freed"] += size
        print(f"  ✓ Deleted autobuild state: {autobuild_task_path}/")

# Delete autobuild state for the feature itself
autobuild_feat_path = ".guardkit/autobuild/FEAT-XXX"
if exists(autobuild_feat_path):
    size = get_dir_size(autobuild_feat_path)
    rm -rf autobuild_feat_path
    cleanup_summary["files_deleted"] += count_files(autobuild_feat_path)
    cleanup_summary["bytes_freed"] += size
    print(f"  ✓ Deleted autobuild state: {autobuild_feat_path}/")

# --- 5d: Delete feature YAML (already archived in 5a) ---
feature_yaml_path = ".guardkit/features/FEAT-XXX.yaml"
if exists(feature_yaml_path):
    size = get_file_size(feature_yaml_path)
    rm feature_yaml_path
    cleanup_summary["files_deleted"] += 1
    cleanup_summary["bytes_freed"] += size
    print(f"  ✓ Deleted feature file: {feature_yaml_path}")

# --- 5e: Move completed task files to tasks/completed/ ---
mkdir -p "tasks/completed"
for task in tasks:
    # Search for task file in backlog (may be in subfolder)
    task_file = find_task_file(task["id"], search_dirs=["tasks/backlog", "tasks/in_progress", "tasks/in_review"])
    if task_file:
        dest = f"tasks/completed/{basename(task_file)}"
        move_file(task_file, dest)
        # Update frontmatter status
        update_frontmatter(dest, {"status": "completed", "updated": now_iso8601()})
        print(f"  ✓ Moved {basename(task_file)} → tasks/completed/")

# --- 5f: Display cleanup summary ---
print()
print(f"  🧹 Cleanup Summary:")
print(f"     Files deleted: {cleanup_summary['files_deleted']}")
print(f"     Space freed: {format_bytes(cleanup_summary['bytes_freed'])}")
if not args.no_archive:
    print(f"     Archive: .guardkit/archive/FEAT-XXX/")
print()
```

**Idempotency**: Each cleanup operation checks existence before acting. Running `/feature-complete` on an already-cleaned feature is a no-op — all checks return false and no errors are raised.

**The `--no-archive` flag**: Skips step 5a (archiving to `.guardkit/archive/`). Artifact deletion in steps 5c-5d still proceeds. Use when you don't need the local archive (e.g., CI/CD pipelines or when disk space is constrained).

---

### Error Handling

**Single Task Mode Errors:**

| Error | User Message | Recovery |
|-------|--------------|----------|
| Worktree not found | "Worktree not found for TASK-XXX. Did you run /feature-build?" | Create worktree or resume build |
| Wrong branch | "Worktree is on branch X, expected autobuild/TASK-XXX" | Checkout correct branch |
| Merge conflict | "Merge conflicts detected. Manual resolution required." | Resolve conflicts manually |
| Already merged | "Task already in main branch" | Verify with git log |
| User declined | "Merge cancelled by user" | Review changes again with --dry-run |

**Feature Mode Errors:**

| Error | User Message | Recovery |
|-------|--------------|----------|
| Feature not found | "Feature FEAT-XXX not found in .guardkit/features/" | Verify feature exists |
| Invalid YAML | "Failed to parse feature file" | Fix YAML syntax |
| Missing worktree | "Worktree missing for TASK-001" | Rebuild missing task |
| No completed tasks | "No completed tasks to merge" | Run /feature-build first |
| Merge conflict | "Merge conflict in TASK-001. Manual resolution required." | Resolve in worktree |

### What NOT To Do

1. **DO NOT** manually edit worktrees (they're auto-generated)
2. **DO NOT** checkout branches manually (let merge handle it)
3. **DO NOT** delete `.guardkit/features/` manually
4. **DO NOT** merge without using this command (state tracking needed)
5. **DO NOT** proceed with merge if conflicts exist (manual resolution required)

### Output Format

```
══════════════════════════════════════════════════════════════
FEATURE COMPLETE: TASK-ABC123
══════════════════════════════════════════════════════════════

Task: Implement OAuth2 authentication
Worktree: .guardkit/worktrees/TASK-ABC123
Branch: autobuild/TASK-ABC123

Changes to merge:
  src/auth/oauth.py          | 120 ++++++++
  src/auth/models.py         |  45 ++++
  tests/test_oauth.py        |  80 ++++++
  3 files changed, 245 insertions(+)

Merge strategy: fast-forward
Target branch: main

Proceed with merge? [Y/n]: Y

Merging...
  ✓ Merged autobuild/TASK-ABC123 to main
  ✓ Updated task status to COMPLETED
  ✓ Archived state to .guardkit/archive/
  ✓ Cleaned up worktree

══════════════════════════════════════════════════════════════
RESULT: SUCCESS
══════════════════════════════════════════════════════════════

Status: MERGED
Commit: abc123def (on main)
Changes: 3 files, 245 insertions(+), 0 deletions(-)
Archive: .guardkit/archive/TASK-ABC123/

Next Steps:
  1. Verify: git log --oneline -5
  2. Test: npm test (or equivalent)
  3. Deploy: Follow deployment process
```
