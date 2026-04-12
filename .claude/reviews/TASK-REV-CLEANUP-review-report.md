# Review Report: TASK-REV-CLEANUP

## Executive Summary

AutoBuild artifacts accumulate unboundedly on the main branch after feature completion. The `feature-complete` command spec defines archive and worktree cleanup but has **no step to remove `.guardkit/autobuild/` artifacts**. Currently 241 TASK directories (6.7MB) and 27 feature YAML files are committed to git. The `.guardkit/archive/` directory specified in the spec was never actually created — the archive step is not functioning.

**Recommendation**: Extend `feature-complete` Step 5 to own the full lifecycle: commit → merge → artifact cleanup → branch delete. Add `.guardkit/autobuild/` to `.gitignore`. Treat feature YAML files as ephemeral orchestration state, not source.

---

## Review Details

- **Mode**: Architectural Review (cleanup strategy)
- **Depth**: Standard
- **Reviewer**: architectural analysis + codebase evidence

---

## Findings

### Finding 1: `.guardkit/autobuild/` is committed to git but should not be

**Severity**: High  
**Evidence**: 241 TASK directories, 6.7MB of JSON artifacts (player turns, coach turns, checkpoints, review summaries) are tracked in git. These are ephemeral build logs — equivalent to CI artifacts. They have zero value in the git history and inflate the repo.

**Current `.gitignore`**: Only `.guardkit/worktrees/` and `graphiti-query-log.jsonl` are ignored. `.guardkit/autobuild/` is completely unignored.

### Finding 2: Archive step in `feature-complete` is non-functional

**Severity**: Medium  
**Evidence**: The spec (Step 5, line 640-656 of `feature-complete.md`) defines:
```
archive_path = ".guardkit/archive/FEAT-XXX"
copy_file(".guardkit/features/FEAT-XXX.yaml", f"{archive_path}/feature_state.yaml")
```
But `.guardkit/archive/` does not exist on disk and has zero tracked files. The archive step is specified but never executes in practice.

### Finding 3: Feature YAML files accumulate without pruning

**Severity**: Medium  
**Evidence**: 27 `FEAT-*.yaml` files in `.guardkit/features/`, all committed. These track orchestration state (task lists, status, complexity). Once a feature is merged, the YAML has no ongoing purpose. The spec says to update status to "merged" but never removes the file.

### Finding 4: `feature-complete` does not own the worktree merge lifecycle

**Severity**: Medium  
**Evidence**: Per the task description, the commit → merge → branch delete flow is currently done manually via Claude Code after autobuild completes. The `feature-complete` command handles worktree cleanup but requires manual orchestration for the git operations preceding it. This creates friction and inconsistency.

### Finding 5: Task markdown files updated during builds are left modified

**Severity**: Low  
**Evidence**: Task files under `tasks/backlog/feat-*/TASK-*.md` get progress updates written during autobuild (checkpoint status, test results). After feature completion, these modifications remain as unstaged changes. They should either be committed as part of the merge or reverted.

---

## Artifact Classification

| Artifact | Category | After Merge Action | Rationale |
|----------|----------|-------------------|-----------|
| `.guardkit/autobuild/TASK-*/` | Ephemeral build log | **Delete** | CI-equivalent artifacts, no long-term value |
| `.guardkit/autobuild/FEAT-*/` | Ephemeral orchestration | **Delete** | Feature-level build state, ephemeral |
| `.guardkit/features/FEAT-*.yaml` | Orchestration state | **Delete** (after merge) | Purpose served once feature merged |
| `.guardkit/archive/FEAT-*/` | Historical archive | **Keep (gitignored)** | Useful for post-mortem, not for git |
| `tasks/backlog/feat-*/TASK-*.md` | Task tracking | **Commit** (in merge) | Part of task history, belongs in git |
| `tasks/completed/TASK-*.md` | Completed tasks | **Commit** (move) | Standard workflow state transition |

---

## Recommendations

### Recommendation 1: Add `.guardkit/autobuild/` to `.gitignore` ★

**Priority**: High | **Effort**: Trivial  
**Rationale**: These are build artifacts equivalent to `node_modules/` or `__pycache__/`. They should never be in git. After adding to `.gitignore`, run `git rm -r --cached .guardkit/autobuild/` to untrack existing files.

**Proposed `.gitignore` additions**:
```gitignore
# AutoBuild artifacts (ephemeral build logs)
.guardkit/autobuild/

# Feature archives (local reference only)
.guardkit/archive/
```

### Recommendation 2: Extend `feature-complete` Step 5 with artifact cleanup

**Priority**: High | **Effort**: Medium  
**Rationale**: The command should own the full post-merge cleanup. Add these operations after the existing worktree cleanup:

```
Step 5 additions:
  a. Delete .guardkit/autobuild/TASK-*/ for all tasks in the feature
  b. Delete .guardkit/autobuild/FEAT-*/ for the completed feature
  c. Delete .guardkit/features/FEAT-*.yaml (after archiving if archive enabled)
  d. Move completed task files to tasks/completed/
```

### Recommendation 3: Make `feature-complete` own the full worktree lifecycle

**Priority**: Medium | **Effort**: Medium  
**Rationale**: Currently requires manual git operations. The command should handle:

```
Full lifecycle:
  1. Verify autobuild completion (coach approved)
  2. Stage and commit remaining changes in worktree
  3. Merge worktree branch to main (ff or merge commit)
  4. Delete worktree and branch
  5. Cleanup artifacts (Rec 2)
  6. Update task/feature status
```

This eliminates the manual "commit remaining → merge → delete branch" step that currently precedes `feature-complete`.

### Recommendation 4: Implement archive as local-only (gitignored)

**Priority**: Low | **Effort**: Low  
**Rationale**: The archive concept in the spec is sound for post-mortems but should be gitignored. Archive to `.guardkit/archive/FEAT-*/` with feature YAML + merge summary, but keep it out of git. Add optional `--archive` flag (default: true) and `--archive-ttl=30d` for auto-pruning stale archives.

### Recommendation 5: One-time cleanup of existing artifacts

**Priority**: High | **Effort**: Low  
**Rationale**: Before implementing the above, do a one-time cleanup:

```bash
# 1. Add to .gitignore
# 2. Untrack autobuild artifacts
git rm -r --cached .guardkit/autobuild/
# 3. Delete feature YAMLs for completed features
# 4. Commit cleanup
```

This removes 6.7MB of build artifacts from the tracked tree immediately.

---

## Decision Matrix

| Option | Impact | Effort | Risk | Recommendation |
|--------|--------|--------|------|----------------|
| 1. Gitignore autobuild | High | Trivial | None | **Do first** |
| 2. Extend Step 5 cleanup | High | Medium | Low | **Do second** |
| 3. Own full lifecycle | Medium | Medium | Low | **Do third** |
| 4. Archive as gitignored | Low | Low | None | **Do with 2** |
| 5. One-time cleanup | High | Low | None | **Do with 1** |

---

## Implementation Sequence

**Wave 1** (immediate, low risk):
- Rec 1 + Rec 5: Add `.gitignore` entries, untrack existing artifacts, delete completed feature YAMLs

**Wave 2** (feature-complete enhancement):
- Rec 2 + Rec 4: Extend Step 5 with artifact cleanup and gitignored archive

**Wave 3** (lifecycle ownership):
- Rec 3: Full worktree lifecycle in `feature-complete`

---

## Architecture Score

| Principle | Score | Notes |
|-----------|-------|-------|
| SRP (feature-complete scope) | 5/10 | Command should own full lifecycle but doesn't |
| DRY (cleanup logic) | 7/10 | Manual cleanup repeats same steps each time |
| YAGNI (archive) | 8/10 | Archive spec exists but isn't needed yet — gitignore sufficient |
| Separation of concerns | 6/10 | Build artifacts mixed with source in git |
| **Overall** | **65/100** | Functional but leaky — artifacts accumulate unboundedly |
