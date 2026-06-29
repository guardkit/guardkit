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

See: `docs/internals/commands-lib/graphiti-preamble.md` for availability check tiers.

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

### Step 2: Check Fleet Memory Availability and Write

**Tier 0 — MCP Tools (Preferred)**:

Check whether `mcp__fleet_memory__memory_write_payload` is available in the current session's tool list.

**IMPORTANT — Deferred tools**: In Claude Code sessions, MCP tools are often listed
in the system reminder as "deferred" (loadable via `ToolSearch`) rather than appearing
directly in the immediate tool list. Treat deferred tools as **available**.

If `mcp__fleet_memory__memory_write_payload` is **not** in the immediate tool list, scan the
session's deferred-tool list (system reminder block) for `mcp__fleet_memory__memory_write_payload`.
If present, load it via:

```
ToolSearch(query: "select:mcp__fleet_memory__memory_write_payload")
```

Only fall through to Tier 1/2 if the tool is absent from BOTH the immediate tool
list AND the deferred-tool list (i.e., the fleet_memory MCP server is not configured
for this session at all).

**IF** MCP tool is available (either immediately or after ToolSearch load):

**Write 1 — Task Outcome** (always):
```
mcp__fleet_memory__memory_write_payload(
  payload: {
    "project": "guardkit",
    "payload_type": "task_outcome",
    "domain_tags": ["task_outcomes"],
    "name": "Task Completion: {task_id}",
    "content": "{task_id}: {title}. Complexity: {complexity}/10. Approach: {approach}. Result: {outcome}. Lessons: {lessons}.",
    "source_type": "text",
    "source_description": "GuardKit task completion"
  }
)
```

**Write 2 — Architectural Decisions** (only if task content contains architectural decisions):
```
mcp__fleet_memory__memory_write_payload(
  payload: {
    "project": "guardkit",
    "payload_type": "project_decision",
    "domain_tags": ["project_decisions"],
    "name": "Decision: {task_id} - {decision_summary}",
    "content": "{decision_description}. Context: {task_id} ({title}). Rationale: {rationale}.",
    "source_type": "text",
    "source_description": "GuardKit task architectural decision"
  }
)
```

**IF** MCP writes succeed:
```
DISPLAY: "[Fleet Memory] Task outcome captured to knowledge graph"
```

**IF** MCP writes fail (error from tool call):
```
DISPLAY: "[Fleet Memory] Warning: Could not capture task outcome ({error})"
         "  (Non-critical — task completion continues)"
```

**DO NOT** block or fail task completion. Continue to git state commit.

---

### Step 2a: Detect group_id Override and Fall Back to CLI (DEPRECATED for fleet_memory)

> **Status (TASK-MEM08-009, 2026-06-29):** This step was specific to the
> legacy Graphiti HTTP MCP server's group_id override behavior (TASK-FIX-B1F7).
> The fleet_memory stdio MCP server uses payload-based routing and does not
> have this issue. **This step is skipped when using `mcp__fleet_memory__*` tools.**
>
> For rollback scenarios where `.mcp.json` is reverted to graphiti, this
> fallback logic remains available but is not invoked under normal fleet_memory
> operation.

> **Historical context (TASK-INF-5053, 2026-05-02):** the override that motivated
> this step was investigated against the graphiti server and **could not
> be reproduced** — the source correctly honours client-supplied `group_id`.
> See `docs/state/TASK-INF-5053/audit.md` for the audit trail.

**This step only applies when using the legacy `mcp__graphiti__add_memory` tools.**

The Graphiti MCP HTTP server reports the actual group used in the
response message: `Episode '...' queued for processing in group
'<actual>'`. If `<actual>` ever differs from the requested `group_id`,
project-specific knowledge (task outcomes, project decisions) would
leak into a shared namespace and be lost to future scoped searches.
Step 2a parses the message and falls back to the CLI on divergence.

After **Write 1** completes, parse the response message and check for
override using the parser at
`installer/core/commands/lib/graphiti_response_parser.py`:

```python
from installer.core.commands.lib.graphiti_response_parser import detect_group_override

result = detect_group_override(
    requested_group_id="guardkit__task_outcomes",
    response_message=write_1_response.message,
)
```

**IF** `result.overridden` is True:

```
DISPLAY (yellow): "[Graphiti] {result.warning}"
```

Then re-issue the same task-outcome write via the CLI (which uses the
Python `GraphitiClient` directly and respects `group_id`):

```bash
guardkit graphiti capture-outcome \
  --from-task-file tasks/completed/{YYYY-MM}/{task_id}-{slug}.md \
  --timeout 300
```

```
DISPLAY: "[Graphiti] MCP group overridden → re-sent via CLI to correct group"
```

**IF** the CLI re-issue itself fails:
```
DISPLAY (yellow): "[Graphiti] CLI fallback also failed ({error})"
                  "  (Non-critical — task completion continues)"
```

**IF** `result.overridden` is False (or `result.actual` is None — the
response did not match the expected pattern, treated as a safe no-op):
proceed normally.

**Same check for Write 2** (architectural decisions →
`guardkit__project_decisions`):

```python
result = detect_group_override(
    requested_group_id="guardkit__project_decisions",
    response_message=write_2_response.message,
)
```

**IF** `result.overridden` is True for Write 2:

```
DISPLAY (yellow): "[Graphiti] {result.warning}"
                  "  (No CLI equivalent for inline architectural-decision writes —"
                  "   decision episode is misfiled in '{result.actual}'. Manual"
                  "   re-capture required if this decision must be queryable in"
                  "   '{result.requested}'.)"
```

There is no `guardkit graphiti capture-decision` subcommand today, so
Write 2 cannot auto-fall-back. The warning is the surface for the user
to decide whether to file a follow-up.

**Step 2a is non-blocking** — any failure (parse error, CLI failure,
override-with-no-fallback) emits a warning and continues. Task
completion is not affected.

**See also**: `.claude/rules/graphiti-knowledge-graph.md` "HTTP MCP
transport: `group_id` is honoured (TASK-INF-5053)",
TASK-FIX-B1F7 (original mitigation), and TASK-INF-5053
(`docs/state/TASK-INF-5053/audit.md`, scope revision).

---

**Tier 1/2 — CLI Fallback** (when MCP not available):

**IF** `mcp__fleet_memory__memory_write_payload` is NOT available:

Check memory backend availability via Read tool (Tier 1):
Read `.guardkit/graphiti.yaml` — if file exists and `enabled: true`, proceed to CLI write.
The CLI uses the configured `backend` flag (graphiti/fleet_memory/dual) from `graphiti.yaml`.

**IF** memory backend is enabled:

Use the dedicated `capture-outcome` subcommand which wraps the
`capture_task_outcome` Python API and writes to the configured backend
(fleet_memory/graphiti/dual) with structured fields (TASK-FIX-CLI7, TASK-MEM08-009).
The subcommand parses the just-moved task file directly — no temp files needed:

```bash
# Frontmatter-driven (preferred): pulls task_id, title, requirements,
# summary, lessons, related ADRs from the task file's frontmatter +
# `## Implementation Summary` / `## Implementation Notes` / `## Notes`
# sections. CLI flags override anything that's parsed.
guardkit memory capture-outcome \
  --from-task-file tasks/completed/{YYYY-MM}/{task_id}-{slug}.md \
  --timeout 300
```

**Note**: `guardkit graphiti capture-outcome` is deprecated but remains as an
alias for backward compatibility. Use `guardkit memory capture-outcome`.

The `--timeout 300` sizes the per-episode timeout for local-LLM entity
extraction (60-300 s typical on local LLMs).

**IF** the task file lacks an `## Implementation Summary` section, fall
back to the explicit-flag form:

```bash
guardkit memory capture-outcome \
  --task-id {task_id} \
  --task-title "{title}" \
  --summary "{one-paragraph outcome summary}" \
  --approach "{approach used}" \
  --lessons "{lesson 1}" --lessons "{lesson 2}" \
  --related-adr {parent_review_or_adr_id} \
  --timeout 300
```

**IF** CLI write succeeds:
The subcommand prints:
```
✅ Outcome captured: OUT-XXXXXXXX
   Group: task_outcomes
```
plus the inner client's `Episode profile [...]: nodes=N, edges=M,
invalidated=K` log line. A non-zero `nodes`/`edges` count confirms the
LLM extraction actually ran (not just a queued raw episode).

**IF** memory backend is unavailable or disabled (default non-blocking
behaviour):
```
DISPLAY (yellow): "Memory backend unavailable or disabled — outcome NOT captured"
                   "  (use --strict to exit non-zero in this case)"
```
Task completion proceeds. To make this case fail-fast (e.g. in CI), pass
`--strict` to the subcommand.

**IF** memory backend is not enabled (config missing or `enabled: false`):
The subcommand reaches the same "unavailable or disabled" branch above
and emits the same warning. Task completion proceeds.

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