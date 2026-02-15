---
id: TASK-FIX-PIPELINE-DATA-LOSS
title: Fix AutoBuild Player→Coach Data Pipeline
task_type: feature
status: completed
created: 2026-02-15T21:00:00Z
updated: 2026-02-15T22:30:00Z
completed: 2026-02-15T22:30:00Z
completed_location: tasks/completed/TASK-FIX-PIPELINE-DATA-LOSS/
priority: critical
tags: [autobuild, agent-invoker, coach-validator, pipeline-fix, data-loss]
complexity: 4
parent_review: TASK-REV-F133
related_tasks: [TASK-SFT-001, TASK-ACR-001]
related_feature: FEAT-AC1A
implementation_mode: task-work
---

# TASK-FIX-PIPELINE-DATA-LOSS: Fix AutoBuild Player→Coach Data Pipeline

## Problem Statement

AutoBuild stalls with UNRECOVERABLE_STALL because Coach criteria verification returns 0/N every turn. The Player SDK agent creates real files and does real work, but the data pipeline between Player output and Coach input loses all meaningful data — file lists, completion_promises, and requirements_addressed are empty by the time Coach reads them.

## Forensic Evidence (from FEAT-AC1A / TASK-SFT-001 run_2)

### task_work_results.json (what Coach reads)
```json
{
  "files_modified": [],
  "files_created": [".../player_turn_3.json"],
  "tests_written": [],
  "quality_gates": { "tests_passed": 0, "all_passed": true },
  "completion_promises": /* FIELD ABSENT */
}
```

### player_turn_1.json (enriched by _create_player_report_from_task_work)
```json
{
  "files_modified": ["**", "/Users/.../pyproject.toml", ...],
  "files_created": ["**", "/Users/.../tests/seam/__init__.py", ...],
  "requirements_addressed": [],
  "completion_promises": /* FIELD ABSENT */,
  "implementation_notes": "Implementation via task-work delegation"
}
```

### Run logs confirm Player DID work
- Turn 1: 5 files created, 4 modified, 19 tool calls, 20 SDK turns
- Git detection found the files (absolute paths + spurious `"**"` entries)
- But Coach sees empty arrays → 0/10 → identical feedback → stall after 3 turns

## Root Cause Analysis

Three bugs form a cascading failure in the data pipeline:

### Bug 1: ToolUseBlock file tracking fails silently

**Location**: `agent_invoker.py`, `_invoke_task_work_implement()` stream loop and `TaskWorkStreamParser._track_tool_call()`

**Problem**: The stream loop processes `ToolUseBlock` instances and calls `parser._track_tool_call(block.name, block.input)`. But `_track_tool_call` expects `tool_args["file_path"]` as the key. The Claude Code SDK's Write/Edit tools may use a different key name (e.g., `path`, `file`, or a nested structure). There is zero diagnostic logging on what `block.input` actually contains, so the mismatch is invisible.

**Evidence**: `task_work_results.json` shows `files_modified: []` and `files_created: [only_the_player_report]` despite 19 tool calls including Write/Edit operations.

**Impact**: `_write_task_work_results()` receives empty file lists from the parser, writes empty arrays to `task_work_results.json`.

### Bug 2: Agent-written player report is overwritten, losing completion_promises

**Location**: `agent_invoker.py`, `_create_player_report_from_task_work()`

**Problem**: The execution protocol (`autobuild_execution_protocol.md`) instructs the SDK agent to write `player_turn_{turn}.json` with full `completion_promises`. The agent may successfully write this file. However, `_create_player_report_from_task_work()` unconditionally overwrites it with data from `task_work_results.json` (which has empty arrays due to Bug 1). Any `completion_promises` the agent wrote are destroyed.

**Evidence**: All `player_turn_N.json` files contain `"implementation_notes": "Implementation via task-work delegation"` — proving they were written by `_create_player_report_from_task_work`, not by the agent. No `completion_promises` field exists.

**Impact**: Coach's `_load_completion_promises()` reads the overwritten file, finds no promises, falls through to text matching against empty `requirements_met` → 0/N.

### Bug 3: task_work_results.json is never updated after enrichment

**Location**: `agent_invoker.py`, `_create_player_report_from_task_work()` and `invoke_player()`

**Problem**: `_create_player_report_from_task_work()` enriches the player report with git-detected files. But the enriched data (file lists, any recovered promises) is only written to `player_turn_N.json`. `task_work_results.json` — which Coach reads first via `read_quality_gate_results()` — is never updated with the enriched data.

**Evidence**: `player_turn_1.json` has git-detected files (albeit with spurious `"**"` entries). `task_work_results.json` has `files_modified: []`.

**Impact**: Even if Bug 2 is fixed, Coach reads stale `task_work_results.json` with empty file lists, affecting test detection (`_detect_tests_from_results`) and quality gate evaluation.

## Required Changes

### Fix 1: Diagnostic logging + flexible key matching for ToolUseBlock

**File**: `guardkit/orchestrator/agent_invoker.py`

**Method**: `_invoke_task_work_implement()` — the stream processing loop

**Change**: Add WARNING-level logging when a ToolUseBlock for Write/Edit is received, dumping the actual `block.input` type and keys. This is critical for diagnosing the key mismatch.

```python
# In the stream loop, where ToolUseBlock is processed:
elif isinstance(block, ToolUseBlock):
    tool_count += 1
    logger.debug(f"Tool invoked: {block.name}")
    if block.name in ("Write", "Edit"):
        tool_input = getattr(block, "input", {})
        # DIAGNOSTIC: Log actual structure
        if isinstance(tool_input, dict):
            logger.info(
                f"[{task_id}] ToolUseBlock {block.name} input keys: "
                f"{list(tool_input.keys())}"
            )
            parser._track_tool_call(block.name, tool_input)
        else:
            logger.warning(
                f"[{task_id}] ToolUseBlock {block.name} input is "
                f"{type(tool_input).__name__}, not dict: {str(tool_input)[:200]}"
            )
```

**Method**: `TaskWorkStreamParser._track_tool_call()`

**Change**: Try multiple key names for the file path. The Claude Code SDK tools may use `file_path`, `path`, `file`, or `command` (for Bash). Add fallback key resolution.

```python
def _track_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> None:
    # Try multiple key names for file path
    file_path = (
        tool_args.get("file_path")
        or tool_args.get("path")
        or tool_args.get("file")
        or tool_args.get("filePath")
    )
    if not file_path or not isinstance(file_path, str):
        # Log what keys we DID get for debugging
        logger.debug(
            f"Tool {tool_name} call has no recognizable file path key. "
            f"Available keys: {list(tool_args.keys())}"
        )
        return
    # ... rest of existing tracking logic
```

### Fix 2: Preserve agent-written completion_promises before overwriting

**File**: `guardkit/orchestrator/agent_invoker.py`

**Method**: `_create_player_report_from_task_work()`

**Change**: Before overwriting `player_turn_N.json`, check if the agent already wrote it with `completion_promises`. If so, preserve them in the new report. Also preserve `requirements_addressed` if the agent populated it.

Insert this block BEFORE the final `json.dump(report, f)` call, after the git enrichment and `task_work_result.output` override sections:

```python
# TASK-FIX-PIPELINE: Recover agent-written completion_promises
# The execution protocol instructs the SDK agent to write player_turn_N.json
# directly. If the agent did so before this method runs, preserve the
# agent's completion_promises and requirements_addressed (which we would
# otherwise overwrite with empty arrays from task_work_results.json).
if not report.get("completion_promises") and player_report_path.exists():
    try:
        with open(player_report_path, "r") as f:
            agent_written = json.load(f)
        
        # Recover completion_promises from agent-written report
        agent_promises = agent_written.get("completion_promises", [])
        if agent_promises:
            report["completion_promises"] = agent_promises
            logger.info(
                f"Recovered {len(agent_promises)} completion_promises "
                f"from agent-written player report for {task_id}"
            )
        
        # Recover requirements_addressed if ours is empty
        if not report["requirements_addressed"]:
            agent_reqs = agent_written.get("requirements_addressed", [])
            if agent_reqs:
                report["requirements_addressed"] = agent_reqs
                logger.info(
                    f"Recovered {len(agent_reqs)} requirements_addressed "
                    f"from agent-written player report for {task_id}"
                )
        
        # Recover requirements_remaining if ours is empty
        if not report["requirements_remaining"]:
            agent_remaining = agent_written.get("requirements_remaining", [])
            if agent_remaining:
                report["requirements_remaining"] = agent_remaining
                
    except (json.JSONDecodeError, IOError) as e:
        logger.debug(f"No agent-written player report to recover from: {e}")
```

**Placement**: This must go AFTER the git enrichment block and AFTER the `task_work_result.output` override block, but BEFORE the final file write.

### Fix 3: Update task_work_results.json after enrichment

**File**: `guardkit/orchestrator/agent_invoker.py`

**Method**: `_create_player_report_from_task_work()`

**Change**: After enriching the player report with git data and recovered promises, write the enriched file lists and promises back to `task_work_results.json`. This ensures Coach sees the same data regardless of which file it reads first.

Add this block AFTER writing the player report (after the existing `json.dump(report, f)` and `logger.info`):

```python
# TASK-FIX-PIPELINE: Update task_work_results.json with enriched data
# Coach reads task_work_results.json for quality gate evaluation and test
# detection. It must reflect the enriched file lists and any recovered
# completion_promises. Without this, Coach sees stale empty arrays.
if task_work_results_path.exists():
    try:
        with open(task_work_results_path, "r") as f:
            task_work_data = json.load(f)
        
        updated = False
        
        # Update file lists if enriched data is richer
        if len(report.get("files_modified", [])) > len(task_work_data.get("files_modified", [])):
            task_work_data["files_modified"] = report["files_modified"]
            updated = True
        
        if len(report.get("files_created", [])) > len(task_work_data.get("files_created", [])):
            task_work_data["files_created"] = report["files_created"]
            updated = True
        
        # Propagate completion_promises if not already present
        if report.get("completion_promises") and not task_work_data.get("completion_promises"):
            task_work_data["completion_promises"] = report["completion_promises"]
            updated = True
        
        # Update tests_written from enriched report
        if len(report.get("tests_written", [])) > len(task_work_data.get("tests_written", [])):
            task_work_data["tests_written"] = report["tests_written"]
            updated = True
        
        if updated:
            with open(task_work_results_path, "w") as f:
                json.dump(task_work_data, f, indent=2)
            logger.info(
                f"Updated task_work_results.json with enriched data for {task_id}"
            )
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to update task_work_results.json: {e}")
```

### Fix 4: Filter spurious git entries

**File**: `guardkit/orchestrator/agent_invoker.py`

**Method**: `_create_player_report_from_task_work()` — git enrichment block

**Change**: Filter out invalid entries from git detection results. The current code produces entries like `"**"` in file lists (likely from glob pattern leakage). Add a filter after the set union.

In the git enrichment section, after the line `report["files_modified"] = sorted(list(original_modified | git_modified))`:

```python
# Filter invalid entries (glob patterns, empty strings, bare wildcards)
def _is_valid_path(p: str) -> bool:
    """Filter out invalid file path entries from git detection."""
    if not p or not p.strip():
        return False
    if p in ("*", "**", "***"):
        return False
    if p.startswith("*"):
        return False
    return True

report["files_modified"] = sorted([p for p in report["files_modified"] if _is_valid_path(p)])
report["files_created"] = sorted([p for p in report["files_created"] if _is_valid_path(p)])
```

### Fix 5: File-existence verification fallback for promise generation

**File**: `guardkit/orchestrator/agent_invoker.py`

**Method**: `_create_player_report_from_task_work()` — after Fix 2 (promise recovery) and Fix 3 (task_work_results update)

**Problem**: Fixes 1-4 fix the plumbing so real data flows through. But there's a case where the agent genuinely doesn't output promises — shorter tasks, or when the SDK session exhausts turns before reaching the report-writing phase. In those cases, all upstream fixes produce nothing, and Coach still sees 0/N.

**Change**: When no `completion_promises` exist after Fix 2 recovery AND `task_work_results.json` has no promises, generate synthetic promises by cross-referencing the task's acceptance criteria against `files_created` and `files_modified`. This mirrors the approach used for synthetic reports (TASK-ASF-006) but applied defensively on the task-work path.

```python
# TASK-FIX-PIPELINE: File-existence verification fallback (Fix 5)
# If no completion_promises were recovered from the agent or task_work_results,
# generate synthetic promises by checking whether files mentioned in the
# acceptance criteria actually exist in the worktree. This covers the case
# where the agent ran out of SDK turns before writing its report.
if not report.get("completion_promises"):
    acceptance_criteria = task.get("acceptance_criteria", [])
    if acceptance_criteria:
        synthetic_promises = self._generate_file_existence_promises(
            task_id=task_id,
            files_created=report.get("files_created", []),
            files_modified=report.get("files_modified", []),
            acceptance_criteria=acceptance_criteria,
            worktree_path=self.worktree_path,
        )
        if synthetic_promises:
            report["completion_promises"] = synthetic_promises
            logger.info(
                f"Generated {len(synthetic_promises)} file-existence promises "
                f"for {task_id} (agent did not produce promises)"
            )
```

**New helper method** `_generate_file_existence_promises()`:

```python
def _generate_file_existence_promises(
    self,
    task_id: str,
    files_created: List[str],
    files_modified: List[str],
    acceptance_criteria: List[str],
    worktree_path: Path,
) -> List[Dict[str, Any]]:
    """Generate completion promises from file existence checks.

    For each acceptance criterion, check if files mentioned in the criterion
    text exist in the worktree (via files_created/files_modified lists or
    direct disk check). Generate a promise with status "complete" if the
    file exists, "incomplete" otherwise.

    Args:
        task_id: Task identifier
        files_created: Files created by Player
        files_modified: Files modified by Player
        acceptance_criteria: List of AC text strings
        worktree_path: Path to worktree for disk checks

    Returns:
        List of promise dicts with criterion_id, status, evidence, evidence_type
    """
    import re
    all_files = set(files_created) | set(files_modified)
    promises = []

    for i, criterion in enumerate(acceptance_criteria):
        criterion_id = f"AC-{i+1:03d}"

        # Extract file paths from criterion text (backtick-quoted paths)
        file_refs = re.findall(r'`([^`]+\.[a-zA-Z]+)`', criterion)
        # Also check for directory references like `tests/seam/`
        dir_refs = re.findall(r'`([^`]+/)`', criterion)

        found_files = []
        for ref in file_refs:
            # Check against known file lists
            if any(ref in f for f in all_files):
                found_files.append(ref)
            # Check disk as fallback
            elif (worktree_path / ref).exists():
                found_files.append(ref)

        found_dirs = []
        for ref in dir_refs:
            if (worktree_path / ref).is_dir():
                found_dirs.append(ref)

        if found_files or found_dirs:
            evidence_items = found_files + found_dirs
            promises.append({
                "criterion_id": criterion_id,
                "status": "partial",
                "evidence": f"File existence verified: {', '.join(evidence_items)}",
                "evidence_type": "file_existence",
            })
        else:
            promises.append({
                "criterion_id": criterion_id,
                "status": "incomplete",
                "evidence": "No file references found or verified",
                "evidence_type": "file_existence",
            })

    return promises
```

**Why `status: "partial"` instead of `"complete"`**: File existence proves the Player created the right files, but doesn't prove the content is correct. Coach's `_match_by_promises()` already treats `"partial"` as verified (TASK-ACR-004) with a lower-confidence annotation, which is the right signal.

## Testing Strategy

### Manual Verification

1. Run AutoBuild on FEAT-AC1A / TASK-SFT-001 after applying fixes
2. Check the logs for the new diagnostic output:
   - `ToolUseBlock Write input keys: [...]` — shows actual SDK key names
   - `Recovered N completion_promises from agent-written player report`
   - `Updated task_work_results.json with enriched data`
3. Inspect `task_work_results.json` — should now have populated file lists
4. Inspect `player_turn_1.json` — should have `completion_promises` if agent wrote them
5. Coach should now verify >0 criteria instead of 0/N

### Unit Tests

Add tests in `tests/unit/test_agent_invoker.py`:

1. **test_track_tool_call_multiple_key_names**: Verify `_track_tool_call` works with `file_path`, `path`, `file`, and `filePath` keys
2. **test_create_player_report_preserves_agent_promises**: Write a player report with promises to disk, call `_create_player_report_from_task_work`, verify promises are preserved
3. **test_create_player_report_updates_task_work_results**: After enrichment, verify `task_work_results.json` has the same file lists as the player report
4. **test_git_detection_filters_wildcards**: Verify `"**"` and `"*"` entries are filtered from file lists
5. **test_file_existence_promises_generated_when_no_agent_promises**: Verify `_generate_file_existence_promises` produces partial promises when files exist on disk
6. **test_file_existence_promises_skipped_when_agent_promises_exist**: Verify Fix 5 does not overwrite real agent promises
7. **test_file_existence_promises_extracts_backtick_paths**: Verify regex extraction of file paths from criterion text

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py` | Fix 1: ToolUseBlock diagnostic logging + flexible key matching |
| `guardkit/orchestrator/agent_invoker.py` | Fix 2: Preserve agent-written completion_promises |
| `guardkit/orchestrator/agent_invoker.py` | Fix 3: Update task_work_results.json after enrichment |
| `guardkit/orchestrator/agent_invoker.py` | Fix 4: Filter spurious git entries |
| `guardkit/orchestrator/agent_invoker.py` | Fix 5: File-existence verification fallback for promise generation |
| `tests/unit/test_agent_invoker.py` | New unit tests for all 5 fixes |

## Acceptance Criteria

- AC-001: ToolUseBlock processing logs actual `block.input` keys at INFO level for Write/Edit tools
- AC-002: `_track_tool_call` resolves file paths from any of: `file_path`, `path`, `file`, `filePath`
- AC-003: Agent-written `completion_promises` in `player_turn_N.json` are preserved when `_create_player_report_from_task_work` runs
- AC-004: `task_work_results.json` is updated with enriched file lists and promises after `_create_player_report_from_task_work` completes
- AC-005: Spurious entries (`"**"`, `"*"`, empty strings) are filtered from file lists
- AC-006: All existing tests continue to pass
- AC-007: New unit tests cover all 5 fixes
- AC-008: When no agent or recovered promises exist, file-existence verification generates `partial` promises for criteria referencing files that exist in the worktree
- AC-009: File-existence fallback does NOT overwrite real agent-written or recovered promises (Fix 2 takes priority)

## Complexity

4 — All changes are in a single file (`agent_invoker.py`) with one new helper method. No architectural changes, no new dependencies. The 5 fixes are targeted insertions at specific points in existing methods, plus one new `_generate_file_existence_promises()` helper.

## Implementation Mode

task-work

## Priority

CRITICAL — This is the root cause of all AutoBuild stalls. Without this fix, no AutoBuild run can complete successfully.
