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

## Fleet-Memory Knowledge Capture (Write Path)

**Purpose**: Capture task outcome to fleet-memory so future tasks benefit from lessons learned. This is the learning flywheel — every completed task enriches the context available to `/task-work`, `/task-review`, and `/feature-plan` read paths.

**Trigger**: Always execute after file organization and state updates, before git commit. Fast no-op if fleet-memory is unavailable.

**Non-blocking**: Task completion MUST succeed even if the fleet-memory write fails. All errors are logged as warnings.

See: `docs/internals/commands-lib/memory-preamble.md` for availability check tiers and the write-payload contract.

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

These fields map to the typed `build_outcome` payload that the `guardkit memory capture-outcome` CLI constructs when it parses the task file (Step 2) — you do **not** hand-build a payload or a narrative episode:

| Extracted field | `build_outcome` payload field |
|---|---|
| `task_id` | `task_id` (also derives the natural key `build_outcome:guardkit:{task_id}`) |
| `outcome` (acceptance-criteria pass/fail) | `status` — `"success"` or `"failure"` |
| `approach` | `approach` (embedded for retrieval) |
| `lessons` | `lessons` (embedded for retrieval) |
| `title` / summary | embedded for retrieval |

Any architectural `decisions` are captured separately as `adr` payloads in Step 2a.

### Step 2: Write the Task Outcome (CLI-first)

The **task outcome** is a `build_outcome` payload written by the dedicated
`guardkit memory capture-outcome` CLI (the only fleet-memory write CLI). It parses
the just-moved task file directly — no temp files, no manual payload construction —
so it is the preferred path for the outcome write whether or not the MCP tools are
in-session.

**Check fleet-memory availability** (see `docs/internals/commands-lib/memory-preamble.md`
Tier 0 → Tier 1): check for the `mcp__fleet_memory__*` tools; else `guardkit memory status`.
Set `memory_available` accordingly. If neither is reachable, set `memory_available = false`,
display the unavailability warning (see `docs/internals/commands-lib/memory-preamble.md` —
Warning Message Template) and continue — **do not block completion**.

**IF** `memory_available` is true, write the outcome:

```bash
# Frontmatter-driven (preferred): pulls task_id, title, requirements,
# summary, lessons, related ADRs from the task file's frontmatter +
# `## Implementation Summary` / `## Implementation Notes` / `## Notes`
# sections. CLI flags override anything that's parsed.
# Writes a build_outcome payload (payload_type "build_outcome") to fleet-memory.
guardkit memory capture-outcome \
  --from-task-file tasks/completed/{YYYY-MM}/{task_id}-{slug}.md \
  --success \
  --timeout 300
```

The `--timeout 300` sizes the per-write timeout for the embedding step
(60-300 s typical on local embedders). Pass `--failure` instead of `--success`
if the task completed but did not meet its acceptance criteria.

**IF** the task file lacks an `## Implementation Summary` section, fall
back to the explicit-flag form:

```bash
guardkit memory capture-outcome \
  --task-id {task_id} \
  --task-title "{title}" \
  --summary "{one-paragraph outcome summary}" \
  --approach "{approach used}" \
  --lessons "{lesson 1}" --lessons "{lesson 2}" \
  --success \
  --timeout 300
```

**IF** the CLI write succeeds, it prints:
```
✅ Outcome captured: OUT-XXXXXXXX
   Payload: build_outcome:guardkit:{task_id}
```
A non-zero natural-key confirms the payload was persisted (content-hash upsert,
so re-running is idempotent).

**IF** fleet-memory is unavailable or disabled (default non-blocking behaviour):
```
DISPLAY (yellow): "Fleet-memory unavailable or disabled — outcome NOT captured"
                   "  (use --strict to exit non-zero in this case)"
```
Task completion proceeds. To make this case fail-fast (e.g. in CI), pass
`--strict` to the subcommand.

---

### Step 2a: Capture Architectural Decisions (MCP write, if any)

If the task content records **architectural decisions**, capture each as an `adr`
payload via the MCP write tool. There is no `guardkit memory` write CLI for
arbitrary knowledge — only `capture-outcome` — so decision writes require the
fleet-memory MCP tools to be connected.

**Check for the MCP write tool** (see `docs/internals/commands-lib/memory-preamble.md`
Tier 0): check whether `mcp__fleet_memory__memory_write_payload` is available in the
current session's tool list.

**IMPORTANT — Deferred tools**: In Claude Code sessions, MCP tools are often listed
in the system reminder as "deferred" (loadable via `ToolSearch`) rather than appearing
directly in the immediate tool list. Treat deferred tools as **available**.

If `mcp__fleet_memory__memory_write_payload` is **not** in the immediate tool list, scan the
session's deferred-tool list (system reminder block) for `mcp__fleet_memory__memory_write_payload`.
If present, load it via:

```
ToolSearch(query: "select:mcp__fleet_memory__memory_write_payload")
```

**IF** the MCP write tool is available (either immediately or after ToolSearch load) AND
the task recorded architectural decisions — for each decision write an `adr` payload
(`identifier` sanitised to underscores only, e.g. `DECISION_045`):

```
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "adr",
  "project": "guardkit",
  "identifier": "DECISION_{NNN}",
  "decision": "{decision_description}. Context: {task_id} ({title}). Rationale: {rationale}.",
  "status": "accepted",
  "domain_tags": ["project"],
  "source_ref": "tasks/completed/{YYYY-MM}/{task_id}-{slug}.md"
})
```

**IF** the write succeeds:
```
DISPLAY: "[Fleet-Memory] Architectural decision captured (adr:guardkit:DECISION_{NNN})"
```

**IF** the write fails (error from the tool call):
```
DISPLAY (yellow): "[Fleet-Memory] Warning: could not capture decision ({error})"
                  "  (Non-critical — task completion continues)"
```

**IF** the MCP write tool is absent from BOTH the immediate and deferred tool lists,
skip decision capture (the CLI cannot write arbitrary payloads):
```
DISPLAY (yellow): "[Fleet-Memory] MCP write tool not connected — architectural"
                  "  decisions NOT captured. Connect the fleet_memory MCP server"
                  "  (see .mcp.json) to persist decisions."
```

**Step 2a is non-blocking** — any failure (missing tool, write error) emits a
warning and continues. Task completion is not affected.

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

📝 Fleet-Memory Knowledge Capture
✅ Outcome captured: OUT-XXXXXXXX
   Payload: build_outcome:guardkit:TASK-042

✅ Task state committed to git

🎉 Task Completion Summary
✅ TASK-042 successfully completed
```

**Example Flow (unavailable)**:
```
📝 Fleet-Memory Knowledge Capture
[Fleet-Memory] Knowledge capture skipped (not configured)

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