---
id: TASK-COND-FE76
title: Investigate /task-complete inconsistent behavior in Conductor workspaces
status: completed
created: 2025-11-27 18:10:00+00:00
updated: '2025-11-27T20:38:20.170718Z'
priority: critical
tags:
- conductor
- task-complete
- bug
- phase-0
- investigation
- path-resolution
- plan-archival
task_type: implementation
epic: null
feature: null
requirements: []
dependencies: []
complexity: 5
effort_estimate: 2-3 hours
related_to: TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-4, TASK-ENF2, TASK-ENF3
notes: 'ROOT CAUSE IDENTIFIED (2025-11-27T19:05:00Z):

  - Full paths work consistently (TASK-ENF2, TASK-ENF3, TASK-ENF-P0-3)

  - Relative paths fail silently (TASK-ENF-P0-1, P0-2, P0-4)

  - Task lookup uses os.getcwd() which returns worktree path in Conductor

  - Fix: Resolve paths relative to main repo, not worktree


  SCOPE EXPANDED (2025-11-27T19:10:00Z):

  - Added FR2.5: Archive implementation plans on task completion

  - Prevents .claude/task-plans/ clutter

  - Plans archived alongside completed tasks for traceability

  - Complexity increased back to 5 (additional feature)

  - Effort remains 2-3 hours (straightforward addition)


  SCOPE EXPANDED AGAIN (2025-11-27T19:20:00Z):

  - Extended FR2.5: Archive implementation summaries from root directory

  - Prevents root directory clutter (TASK-XXX-IMPLEMENTATION-SUMMARY.md files)

  - Archives COMPLETION-REPORT.md files as well

  - All task documents archived together for complete traceability

  - Test cases increased from 6 to 9

  - Complexity remains 5 (similar implementation pattern)

  - Effort remains 2-3 hours (additional patterns to check)

  '
completed: '2025-11-27T20:38:20.168553Z'
---


# TASK-COND-FE76: Investigate /task-complete Inconsistent Behavior in Conductor Workspaces

## Context

During the completion of Phase 0 foundation tasks (TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-4) in a Conductor workspace, only TASK-ENF-P0-3 was automatically marked as completed and moved to `tasks/completed/2025-11/`. The other three tasks remained in `tasks/backlog/agent-invocation-enforcement/` despite being completed in the same workspace.

**Evidence**:
- Workspace output shows all tasks were worked on and completed
- Git commits show implementation was merged (b3e7500, 6ab2a8e, 301eb68)
- Only TASK-ENF-P0-3 moved to completed folder
- TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-4 remained in backlog with `status: backlog`

**User Report #1 (Initial)**:
> "I've implemented these tasks and completed them in a single Conductor workspace but they are still showing in the task/backlog"

**User Report #2 (Additional Evidence - 2025-11-27)**:
> "So I just implemented TASK-ENF2 and TASK-ENF3 in separate conductor worktrees and the /task-complete worked and they are taken out of the backlog, this time I passed the fullpath as I did for the task-work as I have found in the past that the task isn't found straight away without that and this looks related"

**Key Finding**: When using **full paths** for `/task-complete`, tasks are successfully moved and marked as completed. Without full paths, task completion may fail silently.

**Examples**:
- ❌ **Fails**: `/task-complete TASK-ENF-P0-1` (relative/short reference)
- ✅ **Works**: `/task-complete /Users/richardwoollcott/Projects/appmilla_github/taskwright/tasks/backlog/agent-invocation-enforcement/TASK-ENF-P0-1-fix-agent-discovery-local-scanning.md` (full path)

**Working Cases (with full paths)**:
- TASK-ENF2: Successfully completed in Conductor worktree (c316bd9)
- TASK-ENF3: Successfully completed in Conductor worktree (be6d12d)
- TASK-ENF-P0-3: Successfully completed (6ab2a8e)

**Failing Cases (without full paths?)**:
- TASK-ENF-P0-1: Remained in backlog
- TASK-ENF-P0-2: Remained in backlog
- TASK-ENF-P0-4: Remained in backlog

## Problem Statement

### Current Behavior (BROKEN)

When using `/task-work` in Conductor workspaces:
- Implementation completes successfully
- Git commits are created
- Changes are merged to main
- **BUT**: Task files are not always moved to completed folder
- **AND**: Task metadata is not always updated to `status: completed`

### Expected Behavior (FIXED)

When `/task-work` completes successfully:
1. Implementation code is written
2. Tests pass (100%)
3. Git commit is created
4. Task file is moved from `tasks/backlog/` to `tasks/completed/YYYY-MM/`
5. Task metadata is updated: `status: completed`, `completed: <timestamp>`
6. Changes are committed to git

**All 6 steps should happen consistently, regardless of Conductor workspace.**

## Objective

Investigate and fix the `/task-complete` command (or the completion logic in `/task-work`) to ensure:
1. Task files are consistently moved to completed folder
2. Task metadata is consistently updated
3. Behavior is identical in Conductor workspaces and main repo
4. State changes are persisted across Conductor worktree boundaries

## Scope

### In Scope

**Investigation**:
- Review `/task-complete` command implementation
- Review `/task-work` Phase 5.5 completion logic
- Analyze Conductor symlink architecture impact
- Check state persistence mechanisms
- Identify why TASK-ENF-P0-3 succeeded but others failed

**Files to Review**:
- `installer/global/commands/task-complete` (if exists as Python script)
- `installer/global/commands/task-complete.md` (command specification)
- `installer/global/commands/task-work` (Phase 5.5 completion logic)
- `installer/global/commands/lib/state_manager.py` (if exists)
- `.claude/state/` directory structure (symlink target)

**Root Cause Analysis**:
- **PATH RESOLUTION BUG** (PRIMARY SUSPECT): Task lookup fails with relative paths in Conductor workspaces
  - Without full path: Task file not found → silent failure → no move, no metadata update
  - With full path: Task file found → successful completion
  - Likely cause: `os.getcwd()` returns worktree path, but task search assumes main repo
- Timing issues (async completion?)
- File locking conflicts
- Symlink resolution failures
- Missing error handling
- Conductor-specific path resolution bugs

### Out of Scope

- Redesigning entire state management system (unless necessary)
- Changes to Conductor architecture
- Migration of existing tasks (separate cleanup task)

## Requirements

### FR1: Identify Root Cause

**Priority**: P0 (Critical)

**Requirement**: Determine why task completion is inconsistent in Conductor workspaces

**Investigation Steps**:
1. ✅ **CONFIRMED**: Path resolution is the root cause
   - Full paths work consistently (TASK-ENF2, TASK-ENF3, TASK-ENF-P0-3)
   - Relative/short paths fail silently (TASK-ENF-P0-1, P0-2, P0-4)
2. Review task lookup logic in `/task-complete` command
3. Check how `os.getcwd()` interacts with Conductor worktree paths
4. Identify where task file search happens and why it fails without full paths
5. Determine if error messages are suppressed (silent failure)
6. Test fix: Make task lookup Conductor-aware or always use absolute paths

**Acceptance Criteria**:
- [x] Root cause identified and documented ✅ (Path resolution bug confirmed)
- [ ] Reproducible test case created
- [x] Difference between working (full paths) and failing (relative paths) cases understood ✅

---

### FR1.5: Hypothesis and Proposed Fix (NEW)

**Priority**: P0 (Critical)

**Hypothesis**: Task lookup in `/task-complete` uses relative path resolution that breaks in Conductor worktrees

**Evidence**:
1. ✅ **Full paths work**: TASK-ENF2, TASK-ENF3, TASK-ENF-P0-3 all completed successfully
2. ❌ **Relative paths fail**: TASK-ENF-P0-1, P0-2, P0-4 remained in backlog
3. User explicitly states: "I have found in the past that the task isn't found straight away without that [full path]"

**Likely Bug Location**:
```python
# Hypothetical broken code in task-complete
def find_task_file(task_id_or_path):
    """Find task file by ID or path"""
    if os.path.isabs(task_id_or_path):
        # Full path: works in Conductor
        return task_id_or_path if os.path.exists(task_id_or_path) else None
    else:
        # Relative path: BREAKS in Conductor
        # os.getcwd() returns worktree path, not main repo
        task_dirs = ['tasks/backlog', 'tasks/in_progress', ...]
        for task_dir in task_dirs:
            # BUG: This searches in worktree, not main repo!
            pattern = os.path.join(task_dir, f"{task_id_or_path}*.md")
            matches = glob(pattern)
            if matches:
                return matches[0]
        return None  # Silent failure - no error message!
```

**Proposed Fix**:
```python
def find_task_file(task_id_or_path):
    """Find task file by ID or path (Conductor-aware)"""
    # Get main repo path (resolve symlinks for Conductor)
    main_repo = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../../'))

    if os.path.isabs(task_id_or_path):
        # Full path: already works
        return task_id_or_path if os.path.exists(task_id_or_path) else None
    else:
        # Relative path: search in main repo, not worktree
        task_dirs = ['tasks/backlog', 'tasks/in_progress', ...]
        for task_dir in task_dirs:
            # FIX: Search in main repo
            pattern = os.path.join(main_repo, task_dir, f"{task_id_or_path}*.md")
            matches = glob(pattern)
            if matches:
                return matches[0]

        # IMPROVEMENT: Fail loudly instead of silently
        raise FileNotFoundError(
            f"Task not found: {task_id_or_path}\n"
            f"Searched in: {main_repo}/tasks/\n"
            f"Tip: Use full path or ensure task exists"
        )
```

**Acceptance Criteria**:
- [ ] Task lookup resolves paths relative to main repo, not worktree
- [ ] Error messages are clear when task not found (no silent failures)
- [ ] Both relative and absolute paths work in Conductor workspaces
- [ ] Backward compatibility maintained for non-Conductor usage

---

### FR2: Fix Task Completion Logic

**Priority**: P0 (Critical)

**Requirement**: Ensure task files are moved and metadata is updated consistently

**Implementation**:
- Fix file move operation to handle Conductor symlinks
- Add error handling with clear logging
- Ensure metadata updates are atomic
- Verify git commits include task file moves
- **Archive implementation plans to prevent clutter**

**Acceptance Criteria**:
- [ ] Task files always moved to `tasks/completed/YYYY-MM/`
- [ ] Metadata always updated: `status: completed`, `completed: <timestamp>`
- [ ] Works identically in Conductor workspaces and main repo
- [ ] Error messages are clear and actionable
- [ ] Implementation plans archived to `tasks/completed/YYYY-MM/` alongside task files

---

### FR2.5: Archive Implementation Plans and Summaries (NEW)

**Priority**: P1 (High)

**Requirement**: Automatically archive implementation plans AND summary documents when tasks are completed to prevent clutter in `.claude/task-plans/` and root directory

**Rationale**:
- Implementation plans and summaries are valuable historical records
- Keeping them in `.claude/task-plans/` and root directory clutters the workspace
- Archiving alongside completed tasks maintains traceability
- All task-related documents should be in same location as completed tasks

**Current Behavior (BROKEN)**:
```
# .claude/task-plans/ clutter
.claude/task-plans/
├── TASK-001-implementation-plan.md  # Completed weeks ago ❌
├── TASK-042-implementation-plan.md  # Completed yesterday ❌
├── TASK-123-implementation-plan.md  # Active task ✅
└── TASK-456-implementation-plan.md  # Active task ✅

# Root directory clutter (worse!)
/
├── TASK-ENF2-IMPLEMENTATION-SUMMARY.md  # Completed task ❌
├── TASK-003-COMPLETION-REPORT.md        # Completed task ❌
├── TASK-045-IMPLEMENTATION-SUMMARY.md   # Completed task ❌
├── src/
├── tests/
└── ...
```
- Mix of active and completed plans
- **Implementation summaries clutter root directory**
- No clear indication which files are still relevant
- Directories grow indefinitely

**Expected Behavior (FIXED)**:
```
# Clean workspace
.claude/task-plans/
├── TASK-123-implementation-plan.md  # Active task only ✅
└── TASK-456-implementation-plan.md  # Active task only ✅

# Root directory clean (no task files) ✅
/
├── src/
├── tests/
└── ...

# All task documents archived together
tasks/completed/2025-11/
├── TASK-001-fix-auth-bug.md
├── TASK-001-implementation-plan.md           # Archived ✅
├── TASK-001-IMPLEMENTATION-SUMMARY.md        # Archived ✅
├── TASK-042-add-validation.md
├── TASK-042-implementation-plan.md           # Archived ✅
└── TASK-042-COMPLETION-REPORT.md             # Archived ✅
```
- Only active task plans in `.claude/task-plans/`
- **No task files in root directory**
- Completed plans and summaries archived with tasks
- Clear separation of active vs historical
- All task artifacts in one location

**Implementation**:
```python
def archive_task_documents(task_id, completed_dir):
    """Archive all task-related documents when task completes"""
    archived_count = 0

    # 1. Archive implementation plan from .claude/task-plans/
    plan_path = f".claude/task-plans/{task_id}-implementation-plan.md"
    if os.path.exists(plan_path):
        try:
            archive_path = os.path.join(completed_dir, f"{task_id}-implementation-plan.md")
            shutil.move(plan_path, archive_path)
            logger.info(f"✅ Archived implementation plan: {archive_path}")
            archived_count += 1
        except Exception as e:
            logger.warning(f"⚠️  Failed to archive implementation plan: {e}")

    # 2. Archive implementation summary from root directory
    # Pattern: TASK-XXX-IMPLEMENTATION-SUMMARY.md
    summary_patterns = [
        f"{task_id}-IMPLEMENTATION-SUMMARY.md",
        f"{task_id}-implementation-summary.md",
        f"{task_id}-COMPLETION-REPORT.md",
        f"{task_id}-completion-report.md",
    ]

    repo_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../../'))
    for pattern in summary_patterns:
        summary_path = os.path.join(repo_root, pattern)
        if os.path.exists(summary_path):
            try:
                archive_path = os.path.join(completed_dir, pattern)
                shutil.move(summary_path, archive_path)
                logger.info(f"✅ Archived summary document: {archive_path}")
                archived_count += 1
            except Exception as e:
                logger.warning(f"⚠️  Failed to archive summary {pattern}: {e}")

    if archived_count == 0:
        logger.debug(f"No task documents found for {task_id} to archive")
    else:
        logger.info(f"📦 Archived {archived_count} document(s) for {task_id}")

    # Don't fail task completion if archival fails
    return archived_count
```

**Integration into /task-complete**:
```python
def complete_task(task_id_or_path):
    """Complete task with document archival"""
    # 1. Find task file (with Conductor-aware path resolution)
    task_path = find_task_file(task_id_or_path)

    # 2. Extract task ID from path
    task_id = extract_task_id(task_path)

    # 3. Create completed directory (e.g., tasks/completed/2025-11/)
    completed_dir = create_completed_dir()

    # 4. Move task file
    new_task_path = move_task_to_completed(task_path, completed_dir)

    # 5. Update task metadata
    update_task_metadata(new_task_path, status="completed", completed=now())

    # 6. Archive all task documents (NEW - plans + summaries)
    archived_count = archive_task_documents(task_id, completed_dir)

    # 7. Commit changes to git (includes all archived files)
    git_commit_completion(task_id, archived_count)

    logger.info(f"✅ Task {task_id} completed successfully ({archived_count} documents archived)")
```

**Edge Cases**:
1. **No documents exist**: Log debug message, continue (archived_count = 0)
2. **Documents already archived**: Skip archival, continue
3. **Archive fails**: Log warning, continue (don't fail task completion)
4. **Multiple summaries**: Archive all matching patterns (IMPLEMENTATION-SUMMARY, COMPLETION-REPORT, etc.)
5. **Case sensitivity**: Check both uppercase and lowercase patterns
6. **Conductor workspace**: Resolve repo root via `os.path.realpath()` for correct path

**Document Patterns Archived**:
- `.claude/task-plans/{task_id}-implementation-plan.md`
- `{repo_root}/{task_id}-IMPLEMENTATION-SUMMARY.md`
- `{repo_root}/{task_id}-implementation-summary.md`
- `{repo_root}/{task_id}-COMPLETION-REPORT.md`
- `{repo_root}/{task_id}-completion-report.md`

**Acceptance Criteria**:
- [ ] Implementation plans moved to `tasks/completed/YYYY-MM/` on task completion
- [ ] **Implementation summaries moved from root directory to `tasks/completed/YYYY-MM/`** (NEW)
- [ ] **Completion reports archived alongside task files** (NEW)
- [ ] Plans archived alongside their task files
- [ ] `.claude/task-plans/` only contains plans for active tasks
- [ ] **Root directory clean (no task summary files)** (NEW)
- [ ] Archival failure doesn't block task completion (logs warning)
- [ ] Git commit includes all archived files (task + plan + summaries)
- [ ] Works in both Conductor workspaces and main repo
- [ ] Case-insensitive pattern matching handles all naming conventions

---

### FR3: Add State Persistence Validation

**Priority**: P1 (High)

**Requirement**: Verify state changes persist across Conductor worktree boundaries

**Implementation**:
```python
def validate_task_completion(task_id):
    """Verify task completion persisted correctly"""
    # Check file moved
    completed_path = find_task_in_completed(task_id)
    if not completed_path:
        raise ValueError(f"Task {task_id} not found in completed folder")

    # Check metadata updated
    task_data = parse_task(completed_path)
    if task_data['status'] != 'completed':
        raise ValueError(f"Task {task_id} status not updated to completed")

    if 'completed' not in task_data:
        raise ValueError(f"Task {task_id} missing completed timestamp")

    # Check git commit includes move
    git_log = subprocess.run(['git', 'log', '-1', '--name-status'], capture_output=True)
    if f'tasks/completed/' not in git_log.stdout.decode():
        logger.warning(f"Task {task_id} move not committed to git")

    return True
```

**Acceptance Criteria**:
- [ ] Validation runs after task completion
- [ ] Fails loudly if state not persisted
- [ ] Provides actionable error messages

---

### FR4: Add Integration Tests

**Priority**: P1 (High)

**Requirement**: Test task completion in Conductor workspace scenarios

**Test Cases**:

1. **Test Completion in Main Repo**
   ```python
   def test_task_completion_main_repo():
       # Given: Task in backlog
       task_id = create_test_task()

       # When: Task completed via /task-work
       run_command(f"/task-work {task_id}")

       # Then: Task moved and metadata updated
       assert task_in_completed(task_id)
       assert task_status(task_id) == "completed"
   ```

2. **Test Completion in Conductor Workspace**
   ```python
   def test_task_completion_conductor_workspace():
       # Given: Task in backlog, working in Conductor worktree
       task_id = create_test_task()
       worktree_path = create_conductor_worktree()

       # When: Task completed in worktree
       os.chdir(worktree_path)
       run_command(f"/task-work {task_id}")

       # Then: Task moved in main repo (via symlink)
       os.chdir(main_repo_path)
       assert task_in_completed(task_id)
       assert task_status(task_id) == "completed"
   ```

3. **Test Explicit /task-complete**
   ```python
   def test_explicit_task_complete():
       # Given: Task in IN_REVIEW state
       task_id = create_test_task(status="in_review")

       # When: /task-complete called
       run_command(f"/task-complete {task_id}")

       # Then: Task moved and metadata updated
       assert task_in_completed(task_id)
       assert task_metadata(task_id)['completed'] is not None
   ```

4. **Test Document Archival - Plan Only (NEW)**
   ```python
   def test_implementation_plan_archival():
       # Given: Task with implementation plan only
       task_id = create_test_task()
       create_implementation_plan(task_id)

       # When: Task completed
       run_command(f"/task-complete {task_id}")

       # Then: Plan archived with task
       assert not os.path.exists(f".claude/task-plans/{task_id}-implementation-plan.md")
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-implementation-plan.md")
   ```

5. **Test Document Archival - Summary Only (NEW)**
   ```python
   def test_implementation_summary_archival():
       # Given: Task with implementation summary in root directory
       task_id = create_test_task()
       create_implementation_summary(task_id)  # Creates in root: TASK-XXX-IMPLEMENTATION-SUMMARY.md

       # When: Task completed
       run_command(f"/task-complete {task_id}")

       # Then: Summary archived with task, root directory clean
       assert not os.path.exists(f"{task_id}-IMPLEMENTATION-SUMMARY.md")
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-IMPLEMENTATION-SUMMARY.md")
   ```

6. **Test Document Archival - Plan + Summary (NEW)**
   ```python
   def test_all_documents_archival():
       # Given: Task with plan AND summary
       task_id = create_test_task()
       create_implementation_plan(task_id)
       create_implementation_summary(task_id)
       create_completion_report(task_id)

       # When: Task completed
       run_command(f"/task-complete {task_id}")

       # Then: All documents archived together
       # Plans cleaned
       assert not os.path.exists(f".claude/task-plans/{task_id}-implementation-plan.md")
       # Root cleaned
       assert not os.path.exists(f"{task_id}-IMPLEMENTATION-SUMMARY.md")
       assert not os.path.exists(f"{task_id}-COMPLETION-REPORT.md")
       # All archived
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-implementation-plan.md")
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-IMPLEMENTATION-SUMMARY.md")
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-COMPLETION-REPORT.md")
   ```

7. **Test Archival Without Documents (Edge Case)**
   ```python
   def test_task_complete_without_documents():
       # Given: Task without any plans or summaries
       task_id = create_test_task()
       # No documents created

       # When: Task completed
       run_command(f"/task-complete {task_id}")

       # Then: Task completes successfully (archival skipped, archived_count = 0)
       assert task_in_completed(task_id)
       assert task_status(task_id) == "completed"
       # No error thrown for missing documents
   ```

8. **Test Document Archival in Conductor Workspace (NEW)**
   ```python
   def test_document_archival_conductor_workspace():
       # Given: Task with plan and summary, working in Conductor worktree
       task_id = create_test_task()
       create_implementation_plan(task_id)
       create_implementation_summary(task_id)
       worktree_path = create_conductor_worktree()

       # When: Task completed in worktree
       os.chdir(worktree_path)
       run_command(f"/task-complete {task_id}")

       # Then: All documents archived in main repo
       os.chdir(main_repo_path)
       # Plans cleaned
       assert not os.path.exists(f".claude/task-plans/{task_id}-implementation-plan.md")
       # Root cleaned
       assert not os.path.exists(f"{task_id}-IMPLEMENTATION-SUMMARY.md")
       # All archived
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-implementation-plan.md")
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-IMPLEMENTATION-SUMMARY.md")
   ```

9. **Test Case-Insensitive Summary Archival (NEW)**
   ```python
   def test_case_insensitive_summary_archival():
       # Given: Task with different case variations
       task_id = create_test_task()
       # Create files with different casing
       create_file(f"{task_id}-implementation-summary.md")  # lowercase
       create_file(f"{task_id}-COMPLETION-REPORT.md")        # uppercase

       # When: Task completed
       run_command(f"/task-complete {task_id}")

       # Then: Both archived regardless of case
       assert not os.path.exists(f"{task_id}-implementation-summary.md")
       assert not os.path.exists(f"{task_id}-COMPLETION-REPORT.md")
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-implementation-summary.md")
       assert os.path.exists(f"tasks/completed/2025-11/{task_id}-COMPLETION-REPORT.md")
   ```

**Acceptance Criteria**:
- [ ] All 9 test cases pass (was 6)
- [ ] Tests run in CI/CD pipeline
- [ ] Tests cover both implicit (Phase 5.5) and explicit (/task-complete) completion
- [ ] Tests verify plan archival in both main repo and Conductor workspaces
- [ ] **Tests verify summary archival from root directory** (NEW)
- [ ] **Tests verify all document types archived together** (NEW)
- [ ] **Tests verify root directory cleanup** (NEW)
- [ ] Tests verify graceful handling of missing documents
- [ ] Tests verify case-insensitive pattern matching

---

## Implementation Plan

### Phase 1: Investigation (1 hour)

**Step 1.1: Review Workspace Output**
- Analyze provided workspace log for completion attempts
- Check for error messages or warnings
- Identify which command was used (implicit vs explicit)

**Step 1.2: Reproduce Issue**
- Create test task in Conductor workspace
- Run `/task-work` to completion
- Verify if task file moves and metadata updates
- Document exact failure mode

**Step 1.3: Compare Working vs Failing Cases**
- Review TASK-ENF-P0-3 (worked) vs TASK-ENF-P0-1/2/4 (failed)
- Check git history for differences
- Analyze file structure and paths

**Step 1.4: Identify Root Cause**
- Review `/task-complete` implementation
- Check symlink resolution in Conductor
- Identify missing error handling

---

### Phase 2: Fix Implementation (1-1.5 hours)

**Step 2.1: Update Task Completion Logic**
- Fix file move operation (handle symlinks)
- Add atomic metadata updates
- Improve error handling and logging

**Step 2.2: Add Validation**
- Implement post-completion validation
- Verify state persistence
- Add git commit verification

**Step 2.3: Test in Conductor**
- Run fix in Conductor workspace
- Verify state propagates to main repo
- Ensure no regressions

---

### Phase 3: Testing (0.5-1 hour)

**Step 3.1: Create Integration Tests**
- Implement 3 test cases
- Run tests in both environments
- Verify all pass

**Step 3.2: Manual Testing**
- Complete real task in Conductor workspace
- Verify file moved
- Verify metadata updated
- Verify git commit includes changes

---

## Acceptance Criteria

### Functional Requirements

- [x] Root cause identified and documented ✅
- [ ] Task completion works consistently in Conductor workspaces
- [ ] Task files always moved to `tasks/completed/YYYY-MM/`
- [ ] Task metadata always updated (`status: completed`, `completed: <timestamp>`)
- [ ] Implementation plans archived to `tasks/completed/YYYY-MM/` (NEW)
- [ ] `.claude/task-plans/` only contains active task plans (NEW)
- [ ] State changes persist across worktree boundaries
- [ ] Error messages are clear and actionable

### Testing Requirements

- [ ] Integration tests pass (9 test cases - 3 original + 6 document archival)
- [ ] Manual testing in Conductor workspace succeeds
- [ ] Plan archival tested in both main repo and Conductor
- [ ] **Summary archival tested (root directory cleanup)** (NEW)
- [ ] **All document types archived together** (NEW)
- [ ] **Case-insensitive pattern matching tested** (NEW)
- [ ] No regressions in main repo completion
- [ ] All edge cases handled gracefully (including missing documents)

### Code Quality

- [ ] Clear error handling with logging
- [ ] Atomic operations (file move + metadata update + plan archival)
- [ ] Symlink-aware path resolution
- [ ] Git commit verification (includes plan moves)
- [ ] Graceful degradation (plan archival failures don't block completion)

---

## Testing Strategy

### Reproduction Test
```bash
# 1. Create Conductor worktree
cd ~/Projects/appmilla_github/taskwright
conductor create test-workspace

# 2. Create test task
cd test-workspace
/task-create "Test task completion" priority:high

# 3. Complete task
/task-work TASK-XXX

# 4. Verify completion (should succeed, currently may fail)
cd ~/Projects/appmilla_github/taskwright  # Main repo
ls tasks/completed/2025-11/TASK-XXX*.md  # Should exist

# 5. Check metadata
grep "^status:" tasks/completed/2025-11/TASK-XXX*.md  # Should show "completed"
```

### Unit Tests
```bash
pytest tests/test_task_completion.py -v
```

### Integration Tests
```bash
pytest tests/integration/test_conductor_task_completion.py -v
```

---

## Success Metrics

**Primary Metric**: Task completion success rate in Conductor workspaces
- Target: 100% (currently ~25% based on evidence: 1/4 tasks completed without full paths)
- With full paths: 100% (TASK-ENF2, TASK-ENF3, TASK-ENF-P0-3 all succeeded)
- **Goal**: Make relative paths work 100% of the time

**Secondary Metrics**:
- Task file move success: 100%
- Metadata update success: 100%
- **Implementation plan archival success: 100%** (NEW)
- **Active plan directory cleanliness: 100%** (NEW - only active tasks in `.claude/task-plans/`)
- State persistence across worktrees: 100%
- Error message clarity: Subjective, validated via manual testing

**Document Archival Metrics** (NEW):
- Implementation plans archived: 100%
- **Implementation summaries archived from root: 100%** (NEW)
- **Completion reports archived from root: 100%** (NEW)
- Documents archived to correct location: 100% (`tasks/completed/YYYY-MM/`)
- **Root directory cleanup: 100%** (NEW - no task files in root after completion)
- `.claude/task-plans/` cleanup: 100% (only active task plans remain)
- Git commits include all document moves: 100%
- Missing documents handled gracefully: 100% (no errors)
- **Multiple document types archived together: 100%** (NEW - plan + summary + report)

---

## Dependencies

### Blocked By
- None (can start immediately)

### Blocks
- Any task using `/task-complete` or `/task-work` in Conductor workspaces
- Phase 0 foundation tasks (ENF series) - waiting for reliable completion

---

## Risks & Mitigation

### Risk 1: Symlink Resolution Complexity

**Probability**: High
**Impact**: High
**Mitigation**:
- Use absolute paths resolved via `os.path.realpath()`
- Test with both symlinked and non-symlinked paths
- Add verbose logging for path resolution

### Risk 2: Race Conditions

**Probability**: Medium
**Impact**: Medium
**Mitigation**:
- Use atomic file operations
- Add file locking if necessary
- Implement retry logic with exponential backoff

### Risk 3: Breaking Existing Workflows

**Probability**: Low
**Impact**: High
**Mitigation**:
- Extensive testing in main repo before deploying
- Keep backward compatibility
- Add feature flag for new completion logic

---

## Rollout Plan

### Stage 1: Investigation & Fix (2 hours)
- Identify root cause
- Implement fix
- Test in Conductor workspace

### Stage 2: Validation (1 hour)
- Run integration tests
- Manual testing in real scenario
- Verify no regressions

### Stage 3: Deployment (15 min)
- Merge to main
- Update documentation if needed
- Notify users of fix

---

## Follow-Up Tasks

After this task completes:

1. **Document Conductor Best Practices**: Add Conductor-specific guidance to CLAUDE.md
2. **Audit Other Commands**: Check if other commands have similar Conductor issues
3. **Add Conductor CI/CD Tests**: Ensure all future changes test Conductor compatibility

---

## References

- **User Report**: This task description (context section)
- **Related Tasks**: TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-3, TASK-ENF-P0-4
- **Conductor Docs**: (if available in repo)
- **State Management**: `.claude/state/` directory

---

## Notes

- **Critical Path**: This blocks reliable use of Taskwright in Conductor workspaces
- **Priority**: HIGH - Affects developer workflow and productivity
- **Effort**: 2-3 hours (investigation + fix + testing)
- **Risk**: Medium - Fix should be straightforward once root cause identified

---

**Created**: 2025-11-27T18:10:00Z
**Priority**: HIGH
**Effort**: 2-3 hours
**Related To**: TASK-ENF-P0-1, TASK-ENF-P0-2, TASK-ENF-P0-3, TASK-ENF-P0-4
