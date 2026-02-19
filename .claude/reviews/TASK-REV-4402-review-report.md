# Review Report: TASK-REV-4402

## Executive Summary

Analysis of the successful FEAT-BA28 (PostgreSQL Database Integration) autobuild run confirms that **all 5 anomalies are explainable and none represent correctness bugs**. However, 3 of 5 anomalies indicate configuration/design issues worth addressing to reduce noise and improve quality gate accuracy.

**Overall Assessment: 82/100** — System is working correctly; improvements are quality-of-life, not safety-critical.

## Review Details

- **Mode**: Architectural Review (code-level analysis)
- **Depth**: Standard
- **Task**: TASK-REV-4402 — Analyse successful FEAT-BA28 autobuild run
- **Evidence File**: `docs/reviews/autobuild-fixes/db_finally_succeds.md`

---

## Finding 1 — Documentation Level Constraint: Misconfiguration (Severity: Medium)

### Root Cause

The `documentation_level` parameter defaults to `"minimal"` for all AutoBuild tasks, hardcoded at the `invoke_player()` call site:

```python
# agent_invoker.py:620
documentation_level: str = "minimal",
```

The `DOCUMENTATION_LEVEL_MAX_FILES` mapping sets:
```python
DOCUMENTATION_LEVEL_MAX_FILES = {
    "minimal": 2,
    "standard": 2,      # ← same as minimal
    "comprehensive": None,  # No limit
}
```

The constraint at `_validate_file_count_constraint()` (line 4228) is **warning-only** — it logs but does not block.

### Analysis

- **All 5 tasks violated the constraint** because any task creating source files + test files will exceed 2 files.
- The `files_created` list tracks **all files the agent writes** (source, config, test files) — it does NOT filter out autobuild artifacts. This is correct behaviour since `files_created` is populated from `ToolUseBlock.Write` tracking.
- The `"minimal": 2` limit is appropriate for true scaffolding tasks (e.g., create a config file), but **not for TDD-mode tasks** that by definition create implementation files + test files.
- `"standard"` also has a limit of 2, which is identical to `"minimal"` — making the distinction meaningless.

### Verdict

**Misconfiguration, not a bug.** The constraint is always violated for TDD/feature tasks and provides no signal. Two options:

1. **Option A (Recommended)**: Make `documentation_level` configurable per-task in the feature YAML, defaulting to `"standard"` for feature/infrastructure tasks and `"minimal"` for scaffolding. Raise `"standard"` limit to something reasonable (e.g., 10-15 files).
2. **Option B**: Remove the constraint entirely — it's currently all noise, no signal.

**Risk if unfixed**: Zero — constraint is non-blocking. But noisy warnings reduce log readability.

---

## Finding 2 — `tests_required=False` Classification: Correct but Questionable for TASK-DB-005

### Root Cause

The `tests_required` flag comes from the `QualityGateProfile` for each `TaskType`:

| Task | task_type | tests_required | Correct? |
|------|-----------|----------------|----------|
| TASK-DB-001 | scaffolding | False | Yes — infrastructure setup |
| TASK-DB-002 | scaffolding | False | Yes — Alembic migration config |
| TASK-DB-003 | feature | True | Yes — application logic |
| TASK-DB-004 | feature | True | Yes — API endpoints |
| TASK-DB-005 | testing | False | **Questionable** |

The `TaskType.TESTING` profile (in `guardkit/models/task_types.py:227-234`):
```python
TaskType.TESTING: QualityGateProfile(
    tests_required=False,
    ...
)
```

### Analysis

The rationale for `tests_required=False` on TESTING tasks is documented in the profile comments: testing tasks create test files, and running "independent test verification" on a task whose entire purpose is creating tests is somewhat circular — the Coach already validates quality gates from the Player's own test execution.

However, **TASK-DB-005 specifically adds database integration tests** — these tests exercise real application code and infrastructure. Independent verification that these tests pass would provide genuine confidence.

### Verdict

**Classification is defensible but suboptimal for TASK-DB-005.** The `testing` profile was designed for tasks like "add unit test stubs" or "improve coverage", where the tests themselves are the deliverable. For integration-test tasks that exercise real infrastructure, independent verification has higher value.

**Recommendation**: No code change needed now. If this pattern recurs, consider adding a `task_type: integration_testing` or a per-task `tests_required` override in task frontmatter.

---

## Finding 3 — SDK Turn Count Exceeds `max_turns=50`: Expected SDK Behaviour

### Root Cause

The code passes `max_turns=50` via `TASK_WORK_SDK_MAX_TURNS`:

```python
# agent_invoker.py:112
TASK_WORK_SDK_MAX_TURNS = 50
```

This is passed to the Claude Agent SDK as `--max-turns 50`. However, the SDK reported actual turn counts of:

| Task | SDK `num_turns` | SDK `max_turns` |
|------|----------------|-----------------|
| TASK-DB-001 | 63 | 50 |
| TASK-DB-002 | 61 | 50 |
| TASK-DB-003 | 54 | 50 |
| TASK-DB-004 | 66 | 50 |
| TASK-DB-005 | 42 | 50 |

### Analysis

The key insight is that the SDK's `ResultMessage.num_turns` and the `--max-turns` CLI flag **count different things**:

- **`--max-turns`**: Limits the number of **agentic turns** (API round-trips where the model calls tools and gets results). This is the hard limit.
- **`num_turns`**: Reports the total number of **conversation messages** processed, including system messages, user messages, assistant messages, and tool results. This is an informational metric, not bounded by `--max-turns`.

Evidence: The log shows `[TASK-DB-001] Message summary: total=160, assistant=96, tools=62, results=1`. The 63 "turns" likely counts the 62 tool-use exchanges + 1 final result, or uses a slightly different counting methodology internal to the CLI.

**`max_turns` was NOT scaled.** The log explicitly shows `[TASK-DB-001] Max turns: 50` for every task. The tasks simply used 50 or fewer agentic turns, but the `num_turns` metric reports a higher number because it counts total messages.

### Verdict

**Not an anomaly — the `num_turns` metric is a message count, not a turn count.** The `max_turns=50` hard limit was respected. The previous regression concern (turn exhaustion causing missing `completion_promises`) is **not mitigated by scaling** — it was mitigated by the TASK-FIX-FFE2 and TASK-FIX-4AB4 fixes.

**Recommendation**: No code change needed. Consider renaming the log message from `SDK completed: turns=X` to `SDK completed: messages=X` to avoid future confusion.

---

## Finding 4 — Graphiti Project ID Warning: Missing Configuration

### Root Cause

The `guardkit-examples/fastapi/.guardkit/` directory contains only:
```
autobuild/
features/
worktrees/
```

No `graphiti.yaml` file exists. The Graphiti client auto-detects `project_id` from the current working directory name (`fastapi`), producing:
```
WARNING: No explicit project_id in config, auto-detected 'fastapi' from cwd.
```

### Verdict

**Confirmed: missing configuration file.** This warning appeared 5 times (once per task) and is pure noise.

**Recommendation**: Add a minimal `guardkit-examples/fastapi/.guardkit/graphiti.yaml`:
```yaml
project_id: fastapi-example
```

**Risk if unfixed**: Zero — Graphiti auto-detection works correctly. The warning is informational noise.

---

## Finding 5 — `completion_promises` Always Recovered: Structural Limitation Confirmed

### Root Cause

All 5 tasks used the Fix 2 recovery path:
```
INFO: Recovered 6 completion_promises from agent-written player report for TASK-DB-001
```

This confirms the structural gap identified in TASK-REV-9745 Finding 1: `TaskWorkStreamParser` has no regex pattern to extract `completion_promises` from the agent's streaming output. The agent writes promises to its player report (a markdown file), and the recovery mechanism scrapes them from there.

### Analysis

The system has **three lines of defence**:
1. **TaskWorkStreamParser** — parses structured output from agent stream → **no `completion_promises` pattern** (gap)
2. **Fix 2 (player report scraping)** — reads agent-written markdown report → **working correctly** (all 5 tasks recovered)
3. **Fix 5 (task file scraping via `_find_task_file`)** — reads task markdown for criteria → **now fixed by TASK-FIX-FFE2** (searches `design_approved` directory)

The TASK-FIX-4AB4 fix (completion_promises protocol mandate in execution protocol) strengthens the agent's prompt to always include promises, reducing reliance on recovery mechanisms.

### Verdict

**Expected behaviour — recovery mechanism working as designed.** The structural gap in `TaskWorkStreamParser` is known and accepted. The recovery path is robust: Fix 2 succeeded on 5/5 tasks in this run, and Fix 5 (via TASK-FIX-FFE2) provides a fallback if Fix 2 fails.

**Residual risk**: If the agent omits `completion_promises` from both its player report AND the task markdown (unlikely with TASK-FIX-4AB4), then all three recovery paths fail and criteria matching reverts to 0/6. This risk is now low — it would require the agent to completely ignore the explicit protocol mandate.

**Recommendation**: No further action needed. The current triple-fallback architecture is sufficient.

---

## Recommendations Summary

| # | Finding | Severity | Action | Priority |
|---|---------|----------|--------|----------|
| 1 | Documentation level `minimal` always violated | Medium | Raise limit or make configurable per task_type | Low |
| 2 | TASK-DB-005 `tests_required=False` | Low | Accept; revisit if integration-testing pattern recurs | None |
| 3 | SDK `num_turns` > `max_turns` confusion | Low | Rename log message for clarity | Low |
| 4 | Missing Graphiti config in fastapi example | Low | Add `graphiti.yaml` to example project | Low |
| 5 | `completion_promises` always recovered | Info | No action — working as designed | None |

---

## Residual Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| completion_promises triple-failure | Very Low | High (stall) | TASK-FIX-4AB4 protocol mandate + TASK-FIX-FFE2 fallback |
| Documentation constraint masking real violations | Low | Low | Constraint is non-blocking; real issues caught by quality gates |
| Turn exhaustion on larger tasks | Medium | Medium | `max_turns=50` is hard limit; timeout scaling provides additional safety |

**Overall residual risk: Low.** No blocking issues identified. All findings are quality-of-life improvements.

---

## Acceptance Criteria Status

- [x] Documentation level constraint: determined — `minimal` level is misconfigured for TDD/feature tasks; non-blocking warning provides no signal value
- [x] `tests_required=False` for TASK-DB-005: determined — classification is defensible via TESTING profile; no immediate change needed
- [x] `max_turns` scaling: confirmed — `max_turns` was NOT scaled (stayed at 50); SDK `num_turns` reports message count, not turn count
- [x] Graphiti warning: recommendation — add `graphiti.yaml` to fastapi example project
- [x] Residual risk assessment: Low — no safety-critical issues; triple-fallback for completion_promises is robust
