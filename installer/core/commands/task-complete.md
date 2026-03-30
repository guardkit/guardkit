# Task Complete - Finalize Task with Feature/Epic Progress Rollup

Complete tasks with comprehensive validation, automatic progress rollup to features and epics, and external PM tool synchronization.

## Usage
```bash
/task-complete TASK-XXX [options]
```

## Examples
```bash
# Complete task with full validation
/task-complete TASK-045

# Complete with custom completion criteria
/task-complete TASK-045 --criteria-override

# Complete and force sync to PM tools
/task-complete TASK-045 --force-sync

# Complete without triggering rollup (for batch operations)
/task-complete TASK-045 --no-rollup

# Complete with deployment preparation
/task-complete TASK-045 --prepare-deployment

# Interactive completion with validation
/task-complete TASK-045 --interactive
```

## Completion Validation Process

### Pre-Completion Checks
Before marking a task as complete, the system validates:

1. **Acceptance Criteria**: All criteria must be satisfied
2. **Implementation Steps**: All steps marked as complete
3. **Quality Gates**: All gates must pass (tests, coverage, security)
4. **Code Review**: Implementation reviewed and approved
5. **Documentation**: Required documentation completed
6. **External Dependencies**: No blocking dependencies remain

### File Organization on Completion

When completing a task, the system automatically organizes all task-related files into a dedicated subfolder:

```bash
# Completion process creates organized structure:
tasks/completed/
└── TASK-045/
    ├── TASK-045.md                    # Main task file
    ├── implementation-summary.md       # Any related implementation docs
    ├── completion-report.md           # Completion details
    └── coverage-report.json           # Coverage data (if exists)
```

**File Discovery and Organization Logic:**

1. **Create Task Subfolder**
   ```bash
   # Create dedicated directory for task
   mkdir -p "tasks/completed/${TASK_ID}"
   ```

2. **Move Main Task File**
   ```bash
   # Move task file from in_progress to completed subfolder
   mv "tasks/in_progress/${TASK_ID}.md" "tasks/completed/${TASK_ID}/"
   ```

3. **Discover and Move Related Files**
   ```bash
   # Find all files in project root matching TASK-XXX-*.md pattern
   # Examples: TASK-045-IMPLEMENTATION-SUMMARY.md, TASK-045-COMPLETION-REPORT.md
   find . -maxdepth 1 -name "${TASK_ID}-*.md" -type f

   # Move each related file to the task subfolder
   for file in $(find . -maxdepth 1 -name "${TASK_ID}-*.md"); do
     # Extract suffix and create clean filename
     # TASK-045-IMPLEMENTATION-SUMMARY.md → implementation-summary.md
     suffix=$(echo "$file" | sed "s/.*${TASK_ID}-//")
     mv "$file" "tasks/completed/${TASK_ID}/${suffix}"
   done
   ```

4. **Discover and Move Coverage Files (if exists)**
   ```bash
   # Find coverage files matching task pattern
   find . -maxdepth 1 -name "coverage*${TASK_ID}*.json" -type f
   find . -maxdepth 1 -name "coverage-task${TASK_ID#TASK-}*.json" -type f

   # Move to task subfolder
   for file in $(find . -maxdepth 1 -name "*${TASK_ID}*.json"); do
     mv "$file" "tasks/completed/${TASK_ID}/"
   done
   ```

5. **Update Task File Metadata**
   ```yaml
   ---
   status: completed
   completed: 2024-01-20T16:30:00Z
   completed_location: tasks/completed/TASK-045/
   organized_files: [
     "TASK-045.md",
     "implementation-summary.md",
     "completion-report.md",
     "coverage-report.json"
   ]
   ---
   ```

**Benefits of Subfolder Organization:**
- **No Root Pollution**: Keeps project root clean and organized
- **Easy Discovery**: All task-related files in one place
- **Better Traceability**: Clear association between task and its artifacts
- **Scalable**: Structure works for projects with hundreds of tasks
- **Idempotent**: Safe if subfolder already exists

**Error Handling:**
- If subfolder already exists: Skip creation (idempotent)
- If related files not found: Log info message, continue with completion
- If move fails: Log warning, but don't block completion
- Preserve git history: Use `git mv` if files are tracked

### Completion Execution
```bash
/task-complete TASK-045

🏁 Completing Task: TASK-045

📁 Organizing Task Files
Creating: tasks/completed/TASK-045/
Moving: tasks/in_progress/TASK-045.md → tasks/completed/TASK-045/
Found related files:
  ✅ TASK-045-IMPLEMENTATION-SUMMARY.md → implementation-summary.md
  ✅ TASK-045-COMPLETION-REPORT.md → completion-report.md
  ✅ coverage-task045.json → coverage-report.json
Organized 4 files into tasks/completed/TASK-045/

🔄 Task State Transition
Status: IN_PROGRESS → COMPLETED
Completion Date: 2024-01-20T16:30:00Z
Duration: 2.5 days (estimated: 2 days)
Location: tasks/completed/TASK-045/

📊 Progress Rollup Calculation
Feature FEAT-003: 65% → 85% (+20%)
Epic EPIC-001: 57% → 63% (+6%)
Portfolio: 46% → 48% (+2%)

🔄 External Tool Updates
✅ Jira Sub-task PROJ-129: Status → "Done"
✅ Linear Issue PROJECT-461: Status → "Completed"
✅ GitHub Issue #253: Closed

🎉 Task Completion Summary
✅ TASK-045 successfully completed
✅ Feature FEAT-003 at 85% completion
✅ Epic EPIC-001 progressed to 63%
✅ All task files organized in tasks/completed/TASK-045/
✅ All downstream dependencies cleared
```

## Quality Assurance Integration

### Completion Quality Gates
Quality gates must pass before completion:
- Code Coverage: ≥80% ✅
- Test Pass Rate: 100% ✅
- Security Scan: No critical issues ✅
- Code Review: Approved ✅

## Agentecflow Stage Integration

### Stage 3 → Stage 4 Transition Support
```bash
/task-complete TASK-045 --stage-transition

🔄 Stage 3 → Stage 4 Transition: TASK-045
Implementation: 100% complete ✅
Quality Gates: 4/4 passed ✅
Ready for deployment: ✅
```

This command ensures high-quality task completion while maintaining accurate progress tracking across the **Epic → Feature → Task hierarchy**.

## Graphiti Knowledge Capture (Write Path)

**Purpose**: Capture task outcome to the Graphiti knowledge graph so future tasks benefit from lessons learned. This is the learning flywheel — every completed task enriches the context available to `/task-work`, `/task-review`, and `/feature-plan` read paths.

**Trigger**: Always execute after file organization and state updates, before git commit. Fast no-op if Graphiti unavailable.

**Non-blocking**: Task completion MUST succeed even if Graphiti write fails. All errors are logged as warnings.

See: `lib/graphiti-preamble.md` for availability check tiers.

### Step 1: Extract Task Outcome Data

From the task file frontmatter and content sections, extract:

```
task_id:     {from frontmatter: id}
title:       {from frontmatter: title}
complexity:  {from frontmatter: complexity}
approach:    {from Implementation Notes section, or commit messages, or "standard implementation"}
outcome:     {from acceptance criteria pass/fail status and quality gate results}
lessons:     {from Notes section if present, or "No specific lessons recorded"}
decisions:   {any architectural decisions noted in task content}
```

Format the task outcome as a narrative episode:

```
episode_name = "Task Completion: {task_id}"

episode_body = "{task_id}: {title}. Complexity: {complexity}/10. Approach: {approach}. Result: {outcome}. Lessons: {lessons}."
```

**Example**:
```
episode_name = "Task Completion: TASK-042"

episode_body = "TASK-042: Implement user authentication API. Complexity: 7/10. Approach: Used JWT with bcrypt password hashing, FastAPI dependency injection for auth middleware. Result: All acceptance criteria met, 92% test coverage, architectural review 85/100. Lessons: Redis session storage required careful connection pooling configuration for test isolation."
```

### Step 2: Check Graphiti Availability and Write

**Tier 0 — MCP Tools (Preferred)**:

Check whether `mcp__graphiti__add_memory` is available in the current session's tool list.

**IF** MCP tool is available:

**Write 1 — Task Outcome** (always):
```
mcp__graphiti__add_memory(
  name: "Task Completion: {task_id}",
  episode_body: "{task_id}: {title}. Complexity: {complexity}/10. Approach: {approach}. Result: {outcome}. Lessons: {lessons}.",
  group_id: "guardkit__task_outcomes",
  source: "text",
  source_description: "GuardKit task completion"
)
```

**Write 2 — Architectural Decisions** (only if task content contains architectural decisions):
```
mcp__graphiti__add_memory(
  name: "Decision: {task_id} - {decision_summary}",
  episode_body: "{decision_description}. Context: {task_id} ({title}). Rationale: {rationale}.",
  group_id: "guardkit__project_decisions",
  source: "text",
  source_description: "GuardKit task architectural decision"
)
```

**IF** MCP writes succeed:
```
DISPLAY: "[Graphiti] Task outcome captured to knowledge graph"
```

**IF** MCP writes fail (error from tool call):
```
DISPLAY: "[Graphiti] Warning: Could not capture task outcome ({error})"
         "  (Non-critical — task completion continues)"
```

**DO NOT** block or fail task completion. Continue to git state commit.

---

**Tier 1/2 — CLI Fallback** (when MCP not available):

**IF** `mcp__graphiti__add_memory` is NOT available:

Check Graphiti availability via Read tool (Tier 1 from `lib/graphiti-preamble.md`):
Read `.guardkit/graphiti.yaml` — if file exists and `enabled: true`, proceed to CLI write.

**IF** Graphiti is enabled:

Write a temporary file with the task outcome, then seed via CLI:

```bash
# Write outcome to temp file
cat > /tmp/guardkit-task-outcome-{task_id}.md << 'OUTCOME_EOF'
# Task Completion: {task_id}

{task_id}: {title}. Complexity: {complexity}/10. Approach: {approach}. Result: {outcome}. Lessons: {lessons}.
OUTCOME_EOF

# Seed to knowledge graph via CLI
guardkit graphiti add-context /tmp/guardkit-task-outcome-{task_id}.md \
  --group task_outcomes

# Clean up temp file
rm -f /tmp/guardkit-task-outcome-{task_id}.md
```

**IF** CLI write succeeds:
```
DISPLAY: "[Graphiti] Task outcome captured via CLI"
```

**IF** CLI write fails:
```
DISPLAY: "[Graphiti] Warning: Could not capture task outcome via CLI ({error})"
         "  (Non-critical — task completion continues)"
```

**IF** Graphiti is not enabled (config missing or `enabled: false`):
```
DISPLAY: "[Graphiti] Knowledge capture skipped (not configured)"
```

### Step 3: Summary

After the write attempt (regardless of success/failure), continue to the git state commit step. The knowledge capture is purely additive — it enriches future sessions but is never required for task completion.

**Example Flow (MCP path)**:
```
/task-complete TASK-042

🏁 Completing Task: TASK-042

📁 Organizing Task Files
...

🔄 Task State Transition
Status: IN_PROGRESS → COMPLETED
...

📊 Progress Rollup Calculation
...

📝 Graphiti Knowledge Capture
[Graphiti] Task outcome captured to knowledge graph

✅ Task state committed to git

🎉 Task Completion Summary
✅ TASK-042 successfully completed
```

**Example Flow (unavailable)**:
```
📝 Graphiti Knowledge Capture
[Graphiti] Knowledge capture skipped (not configured)

✅ Task state committed to git
```

## Git State Commit (REQUIRED for Conductor Support)

**CRITICAL**: After completing the task and moving files to the completed directory, commit all task-related state files to git. This ensures that state is preserved across git worktrees (used by Conductor.build for parallel development).

### Implementation

After completing all file organization and state updates, execute the following Python code:

```python
from installer.core.commands.lib.git_state_helper import commit_state_files

# Commit all state files for this completed task
# This includes:
# - docs/state/{task_id}/ directory (all state files)
# - Task completion metadata
# - Progress rollup updates

try:
    commit_state_files(
        task_id="{task_id}",
        message=f"Complete {task_id} and update state"
    )
    print("✅ Task state committed to git")
except Exception as e:
    # Don't fail completion if git commit fails
    # (may not be in a git repo, or git may not be available)
    print(f"⚠️  Warning: Could not commit task state: {e}")
    print("   (This is non-critical - task completion can continue)")
```

### Why This Is Needed

- **Conductor.build** uses git worktrees for parallel development
- Each worktree has its own working directory but shares the same git repository
- State files in `docs/state/` MUST be committed to be visible across all worktrees
- Without this step, completed task state is lost when switching between worktrees

### What Gets Committed

- All files in `docs/state/{task_id}/` directory
- Progress rollup updates (if stored in state files)
- Completion metadata and timestamps
- Does NOT commit the task file itself (that's in `tasks/completed/` and handled separately)
- Does NOT push to remote (that's a separate operation)

### Error Handling

- If git commit fails, log a warning but continue with task completion
- Common reasons for failure:
  - Not in a git repository
  - Git not available in environment
  - No state files to commit (silent success)
- Task completion should never fail due to git commit issues