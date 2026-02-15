# Review Report: TASK-REV-F133

## Executive Summary

**Root Cause: CONFIRMED H1** -- The task-work delegation path (`_invoke_task_work_implement`) does not produce `completion_promises` or `requirements_met` in `task_work_results.json`. The `TaskWorkStreamParser` parses stream output for test counts, coverage, and file operations, but has **zero capability** to extract completion promises from the task-work SDK session. This leaves both fields empty, causing Coach's `validate_requirements()` to fall through to text matching against an empty list, yielding 0/10 criteria verified on every turn.

**Impact**: Any task using `implementation_mode: task-work` that has non-trivial acceptance criteria will hit the same UNRECOVERABLE_STALL. This is a **systemic bug**, not specific to scaffolding tasks.

**Severity**: High -- blocks all task-work delegated tasks in AutoBuild feature runs.

## Review Details

- **Mode**: Debugging / Root Cause Analysis
- **Depth**: Deep
- **Duration**: Deep code analysis across 4 source files + run log
- **Reviewer**: Manual code trace + log correlation

## Root Cause Analysis

### The Two Player Execution Paths

AutoBuild has two Player execution paths based on `implementation_mode`:

| Path | Mode | Method | Completion Promises | Result |
|------|------|--------|-------------------|--------|
| **Direct** | `direct` | `_invoke_player_direct()` | Player SDK returns JSON with `completion_promises` field | Propagated to `task_work_results.json` via `_write_direct_mode_results()` |
| **Task-work** | `task-work` | `_invoke_task_work_implement()` | `TaskWorkStreamParser` parses streamed text output | **Never extracted** -- parser has no pattern for promises |

### Evidence Chain

#### TASK-SFT-002 (documentation, `direct` mode) -- SUCCEEDED

1. **Player invoked via direct SDK** ([agent_invoker.py:2209](guardkit/orchestrator/agent_invoker.py#L2209))
2. Player returns structured JSON including `completion_promises: [{criterion_id: "AC-001", status: "complete", ...}, ...]`
3. `_write_direct_mode_results()` propagates `completion_promises` into `task_work_results.json` ([agent_invoker.py:2441-2444](guardkit/orchestrator/agent_invoker.py#L2441-L2444))
4. Coach's `_load_completion_promises()` finds promises in `task_work_results.json`
5. Coach uses `_match_by_promises()` strategy -- **6/11 verified on Turn 1, 11/11 on Turn 2**

Log evidence:
```
INFO: Criteria Progress (Turn 1): 6/11 verified (60%)
INFO:   AC-005: No completion promise for AC-005
INFO: Coach approved TASK-SFT-002 turn 2
INFO: Criteria Progress (Turn 2): 11/11 verified (100%)
```

#### TASK-SFT-001 (scaffolding, `task-work` mode) -- FAILED

1. **Player invoked via task-work delegation** ([agent_invoker.py:697](guardkit/orchestrator/agent_invoker.py#L697))
2. Task-work SDK session runs Claude Code's `/task-work --implement-only` command
3. Output is streamed through `TaskWorkStreamParser` which extracts: phases, test counts, coverage, file lists, arch scores ([agent_invoker.py:153-493](guardkit/orchestrator/agent_invoker.py#L153-L493))
4. `TaskWorkStreamParser.to_result()` returns dict **without** `completion_promises` or `requirements_met` keys
5. `_write_task_work_results()` writes `task_work_results.json` **without** these fields ([agent_invoker.py:3684-3712](guardkit/orchestrator/agent_invoker.py#L3684-L3712))
6. `_create_player_report_from_task_work()` checks for `completion_promises` in task_work_data but finds none ([agent_invoker.py:1492-1495](guardkit/orchestrator/agent_invoker.py#L1492-L1495))
7. Coach's `_load_completion_promises()` finds empty list in both `task_work_results.json` and `player_turn_N.json`
8. Coach falls to `_match_by_text()` with `requirements_met: []` -- **0/10 criteria on all 3 turns**

Log evidence (identical on all 3 turns):
```
WARNING: Criteria verification 0/10 - diagnostic dump:
WARNING:   requirements_met: []
WARNING:   completion_promises: (not used)
WARNING:   matching_strategy: text
WARNING:   _synthetic: False
```

### Why `TaskWorkStreamParser` Cannot Extract Promises

The `TaskWorkStreamParser` ([agent_invoker.py:153](guardkit/orchestrator/agent_invoker.py#L153)) uses regex patterns to parse streaming text output. It can detect:
- Phase markers (`Phase 2: Implementation Planning...`)
- Test results (`12 tests passed, 0 failed`)
- Coverage (`Coverage: 85.5%`)
- File operations (Write/Edit tool calls)
- Architectural review scores

It **cannot** detect completion promises because:
1. Task-work output is unstructured streaming text, not JSON
2. The Claude Code `/task-work` command doesn't output completion promises in its stream
3. Even if it did, there's no regex pattern registered to capture them

### Why Text Matching Also Fails

The `_match_by_text()` fallback ([coach_validator.py:1247](guardkit/orchestrator/quality_gates/coach_validator.py#L1247)) compares acceptance criteria text against `requirements_met` entries. Since `requirements_met` is always empty for task-work delegated tasks (not populated by `TaskWorkStreamParser` or `_write_task_work_results`), every criterion results in `"Not found in Player requirements_met"`.

## Hypothesis Evaluation

| Hypothesis | Status | Notes |
|-----------|--------|-------|
| **H1**: Player task-work delegation doesn't populate `requirements_met` | **CONFIRMED (Primary)** | `TaskWorkStreamParser` has no capability to extract promises or requirements from stream |
| **H2**: Coach text matching too strict for nested criteria | **Not reached** | Text matching never executes with any input -- the input list is empty |
| **H3**: Quality gate profile misconfigured for scaffolding | **DISMISSED** | Profile correctly sets `tests_required=False`, quality gates pass. The failure is in requirements validation, not quality gates |
| **H4**: FalkorDB errors degraded context | **DISMISSED (Contributor, not root cause)** | Graphiti context was disabled early, but this doesn't affect promise generation. TASK-SFT-002 also ran without Graphiti context and succeeded |

## Impact Assessment

### Affected Tasks

**All tasks with `implementation_mode: task-work`** are affected. In FEAT-AC1A:

| Task | Mode | Affected? |
|------|------|-----------|
| TASK-SFT-001 (scaffolding) | task-work | YES -- stalled |
| TASK-SFT-002 (documentation) | direct | No |
| TASK-SFT-003 through TASK-SFT-008 | task-work | YES -- would stall if reached |
| TASK-SFT-009 through TASK-SFT-011 | unknown | Depends on mode |

**7 of 11 tasks** in this feature are likely affected.

### Systemic Scope

Any future `feature-build` run with `implementation_mode: task-work` tasks will hit this bug. The task-work delegation path is used for complex implementation tasks (feature, refactor, infrastructure), making this a **critical path issue** for AutoBuild.

## Recommendations

### Fix 1: Add file-existence verification for task-work path (Recommended)

**Location**: [agent_invoker.py:3684-3736](guardkit/orchestrator/agent_invoker.py#L3684-L3736) (`_write_task_work_results`)

After `_write_task_work_results` writes the results, generate `completion_promises` by cross-referencing acceptance criteria against `files_created` and `files_modified`. This is the same approach used for synthetic reports (TASK-ASF-006) but applied to the task-work path.

```python
# In _write_task_work_results(), after building results dict:

# Generate completion_promises from file-existence verification
# when no promises are present (task-work delegation path)
if not results.get("completion_promises"):
    promises = self._generate_file_existence_promises(
        task_id, results, acceptance_criteria
    )
    if promises:
        results["completion_promises"] = promises
```

**Pros**: Quick to implement, uses existing file detection infrastructure
**Cons**: Only verifies file existence, not content quality

### Fix 2: Inject completion_promises into task-work protocol prompt

**Location**: [agent_invoker.py:~1000](guardkit/orchestrator/agent_invoker.py#L1000) (inline implement protocol)

The Player prompt already requests `completion_promises` in its JSON output format for direct mode. For task-work delegation, add an equivalent instruction to the inline implement protocol that tells Claude Code to output a completion promises summary at the end.

**Pros**: Gets real AI-verified promises from the implementation session
**Cons**: Relies on Claude Code outputting structured data that `TaskWorkStreamParser` must parse

### Fix 3: Read task-work's own quality gate artifacts

**Location**: [coach_validator.py:907](guardkit/orchestrator/quality_gates/coach_validator.py#L907) (`validate_requirements`)

When `requirements_met` is empty and `completion_promises` is empty, have Coach fall back to reading the task-work session's own quality gate outputs (Phase 4.5 results, Phase 5 review) from the worktree's `.claude/` artifacts.

**Pros**: Uses task-work's native quality gate assessment
**Cons**: Requires understanding task-work's internal artifact format

### Recommended Approach: Fix 1 + Fix 2 (Layered)

1. **Immediate** (Fix 1): File-existence verification as a safety net -- ensures no empty-promises stall
2. **Follow-up** (Fix 2): AI-generated promises for richer verification

## Implementation Decision

**Approach chosen**: Merged review Fix 1 (file-existence verification) into the existing spec [TASK-FIX-PIPELINE-DATA-LOSS](../../tasks/backlog/TASK-FIX-PIPELINE-DATA-LOSS.md) as **Fix 5**. The spec now contains 5 complementary fixes:

| Fix | What | Why |
|-----|------|-----|
| Fix 1 | Diagnostic logging + flexible ToolUseBlock key matching | Upstream data was being dropped silently |
| Fix 2 | Preserve agent-written completion_promises | Player report was being overwritten |
| Fix 3 | Update task_work_results.json after enrichment | Coach was reading stale data |
| Fix 4 | Filter spurious git entries (`"**"`, `"*"`) | Garbage in file lists |
| Fix 5 | File-existence verification fallback | Safety net when agent doesn't output promises at all |

Fixes 1-4 fix the plumbing so real data flows through. Fix 5 is a defensive layer for when the agent genuinely doesn't produce promises (short tasks, SDK turn exhaustion).

**Single task**: All 5 fixes target `agent_invoker.py`, same method chain. No need to split into subtasks.

## Appendix

### Key File Locations

| File | Role |
|------|------|
| [guardkit/orchestrator/agent_invoker.py](guardkit/orchestrator/agent_invoker.py) | Player invocation, `TaskWorkStreamParser`, results writing |
| [guardkit/orchestrator/quality_gates/coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) | Coach validation, `_match_by_text`, `_match_by_promises` |
| [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py) | Stall detection, criteria progress tracking |
| [guardkit/models/task_types.py](guardkit/models/task_types.py) | Quality gate profiles per task type |

### Diagnostic Data Points

- TASK-SFT-001 Turn 1: Player created 5 files, modified 4 -- Coach saw 0/10 criteria
- TASK-SFT-001 stall signature: `sig=bbaba24c` repeated 3x with identical feedback
- TASK-SFT-002 Turn 1: 6/11 criteria verified via `completion_promises` strategy
- TASK-SFT-002 Turn 2: 11/11 criteria verified via `completion_promises` strategy -- approved
- Graphiti disabled for entire run (FalkorDB event loop errors) -- did not affect TASK-SFT-002 success
