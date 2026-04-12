# Implementation Guide: AutoBuild Artifact Cleanup

## Wave 1: Gitignore + One-Time Cleanup (TASK-AC-001)

**Risk**: None — only removes build artifacts from tracking  
**Effort**: ~30 min

### Steps

1. Add to `.gitignore`:
   ```gitignore
   # AutoBuild artifacts (ephemeral build logs)
   .guardkit/autobuild/

   # Feature archives (local reference only)
   .guardkit/archive/
   ```

2. Untrack existing autobuild artifacts:
   ```bash
   git rm -r --cached .guardkit/autobuild/
   ```

3. Delete feature YAML files for completed/merged features:
   - Check each `.guardkit/features/FEAT-*.yaml` for `status: merged` or features with no active tasks
   - Remove completed ones from git tracking

4. Commit cleanup

### Verification
- `git status` shows no `.guardkit/autobuild/` files
- `.guardkit/autobuild/` directory still exists locally but is untracked
- No regression in `feature-complete` or `feature-build` commands

---

## Wave 2: Extend Step 5 + Archive (TASK-AC-002)

**Risk**: Low — modifying command spec  
**Effort**: ~2 hours

### Changes to `feature-complete.md`

Extend Step 5 (Archive and Cleanup) to add after existing worktree cleanup:

```
Step 5 additions:
  a. Delete .guardkit/autobuild/TASK-*/ for all tasks in the feature
  b. Delete .guardkit/autobuild/FEAT-*/ for the completed feature
  c. Archive .guardkit/features/FEAT-*.yaml to .guardkit/archive/ (gitignored)
  d. Delete .guardkit/features/FEAT-*.yaml from disk
  e. Move completed task files to tasks/completed/
```

### Archive Design
- Archive path: `.guardkit/archive/FEAT-XXX/` (gitignored — local reference only)
- Contents: feature YAML + merge summary
- Optional `--no-archive` flag to skip archiving
- No TTL pruning needed initially (YAGNI — user can `rm -rf .guardkit/archive/` manually)

### Verification
- Run `feature-complete` on a test feature
- Verify autobuild artifacts deleted
- Verify feature YAML archived then deleted
- Verify task files moved to completed

---

## Wave 3: Full Lifecycle Ownership (TASK-AC-003)

**Risk**: Low-Medium — adding git operations to command  
**Effort**: ~3 hours

### Changes to `feature-complete.md`

Add new steps before existing Step 1:

```
New Step 0: Worktree Merge Lifecycle
  a. Verify autobuild completion (coach approved, all tasks passed)
  b. Stage and commit remaining changes in worktree branch
  c. Merge worktree branch to main (fast-forward preferred, merge commit fallback)
  d. Delete worktree branch (git branch -d autobuild/TASK-XXX)
```

This replaces the current manual workflow where Claude Code orchestrates commit/merge/branch-delete before `feature-complete` is invoked.

### Key Design Decisions
- Fast-forward merge preferred (cleaner history)
- If merge conflict: stop and report, don't auto-resolve
- `--dry-run` should preview the merge without executing
- `--no-merge` flag for cases where merge was already done manually

### Verification
- Create a test worktree with changes
- Run `feature-complete` end-to-end
- Verify: changes merged, branch deleted, artifacts cleaned, task files moved
