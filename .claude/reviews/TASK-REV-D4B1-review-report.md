# Review Report: TASK-REV-D4B1

## Executive Summary

TASK-CR-007 and TASK-CR-008 fail with MAX_TURNS_EXCEEDED because they are classified as `task_type: refactor`, which requires `tests_required=True` in the quality gate profile. These documentation-trimming tasks never produce test results, so the Coach repeatedly fails them with "Tests did not pass during task-work execution" on every turn. TASK-CR-009 succeeds because the Player creates a test file (`tests/test_task_cr_009_pathgated_trim.py`) on turn 2 that passes, satisfying the gate.

**Root Cause**: Task type misclassification. These are documentation content reduction tasks incorrectly typed as `refactor`. (The feature was manually created, bypassing the `/feature-plan` auto-detection which already has correct task type classification via `guardkit/lib/task_type_detector.py`.)

**Secondary Issue**: No unrecoverable stall detection. When `should_rollback()` fires but `find_last_passing_checkpoint()` returns `None` (no turn ever passed), the loop continues indefinitely until MAX_TURNS_EXCEEDED — burning 55 turns (~50 minutes) with zero progress.

---

## Review Details

- **Mode**: Architectural / Decision Analysis
- **Depth**: Standard
- **Reviewer**: Manual analysis of log, source code, and task definitions
- **Evidence Base**: 3,929-line error log, Coach validator source, task type profiles, task definitions
- **Revision**: R1 — Confirmed `/feature-plan` already has task type classification; added unrecoverable stall detection analysis

---

## Findings

### Finding 1: Task Type Misclassification (Root Cause)

**Severity**: Critical
**Evidence**:

All three Wave 3 tasks are defined with `task_type: refactor` in their frontmatter:

| Task | Description | task_type | Nature |
|------|-------------|-----------|--------|
| CR-007 | Trim orchestrators.md (~385→80 lines) | refactor | Documentation trimming |
| CR-008 | Trim dataclasses.md + pydantic-models.md | refactor | Documentation trimming |
| CR-009 | Trim 5 path-gated .md files | refactor | Documentation trimming |

The `REFACTOR` quality gate profile ([task_types.py:209-216](guardkit/models/task_types.py#L209-L216)) requires:
```python
TaskType.REFACTOR: QualityGateProfile(
    arch_review_required=True,
    arch_review_threshold=60,
    coverage_required=True,
    coverage_threshold=80.0,
    tests_required=True,      # ← THIS IS THE PROBLEM
    plan_audit_required=True,
)
```

The `DOCUMENTATION` profile has `tests_required=False`, `coverage_required=False`, `arch_review_required=False`, and `plan_audit_required=False`.

These tasks are editing markdown documentation files — they are **not** refactoring code. They should use the `documentation` task type.

**Note**: The `/feature-plan` auto-detection already handles this correctly via [task_type_detector.py](guardkit/lib/task_type_detector.py). This feature was manually created, bypassing that logic. However, the detector has a priority ordering issue: REFACTOR keywords are checked before DOCUMENTATION, so task descriptions mentioning "migration" (as these Graphiti migration tasks do) would match REFACTOR first regardless. The word "trim" is not in any keyword list.

### Finding 2: Coach Validation Feedback Loop

**Severity**: High
**Evidence** (from [max_turns_exceeded.md](docs/reviews/graphiti_enhancement/max_turns_exceeded.md)):

The Coach validator at [coach_validator.py:723-735](guardkit/orchestrator/quality_gates/coach_validator.py#L723-L735) processes the `quality_gates` section of `task_work_results.json`. For CR-007 and CR-008:

1. Player runs `/task-work --implement-only` → edits markdown files → no tests created
2. `task_work_results.json` written with `quality_gates.all_passed = None` (no test results parsed)
3. Coach reads results: `tests=None (required=True)` → fails quality gate
4. Coach feedback: "Tests did not pass during task-work execution"
5. Player receives feedback, tries again → same result
6. Repeats until MAX_TURNS_EXCEEDED

Log evidence for CR-007 Turn 1 (line 758):
```
Quality gate evaluation complete: tests=None (required=True), coverage=True (required=True),
arch=True (required=False), audit=True (required=True), ALL_PASSED=False
```

This same pattern repeats identically on every turn (verified for turns 1-5 in first run, turns 1-25 in second run).

### Finding 3: Why CR-009 Succeeds

**Severity**: Informational
**Evidence** (from log lines 1274-1287):

CR-009 succeeds because the Player **creates a test file** (`tests/test_task_cr_009_pathgated_trim.py`) during implementation. On turn 2:

```
Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True),
arch=True (required=False), audit=True (required=True), ALL_PASSED=True
Task-specific tests detected for TASK-CR-009: 1 file(s)
Running independent tests: pytest tests/test_task_cr_009_pathgated_trim.py -v --tb=short
Independent tests passed in 1.8s
Coach approved TASK-CR-009 turn 2
```

The Player for CR-009 happened to create a test file (likely because `/task-work --mode=tdd` was used and the Player wrote tests for the markdown trimming). The Players for CR-007 and CR-008 did not create test files across any of their turns.

This is non-deterministic behaviour — whether the Player creates tests for a markdown-editing task depends on the LLM's interpretation of `--mode=tdd` for documentation changes. It should not be relied upon.

### Finding 4: Player Behaviour Across Turns (Looping Without Progress)

**Severity**: High
**Evidence**:

For CR-007 and CR-008, the criteria progress remains at **0% verified** across all turns:
- Turn 1: 0/5 verified (CR-007), 0/4 verified (CR-008)
- Turn 2: 0/5 verified, 0/4 verified
- ... through Turn 25: identical

The Player makes the same markdown edits repeatedly, receives the same "Tests did not pass" feedback, and has no actionable path to resolve the issue because:
1. The task is to trim markdown content — there's no meaningful test to write
2. The Coach feedback ("tests did not pass") is misleading for a documentation task
3. The Player cannot change the quality gate profile

This represents wasted compute (52 turns for Wave 3 alone, ~50 minutes).

### Finding 5: No Unrecoverable Stall Detection (Critical Gap)

**Severity**: High
**Evidence** ([autobuild.py:1014-1037](guardkit/orchestrator/autobuild.py#L1014-L1037), [worktree_checkpoints.py:505-523](guardkit/orchestrator/worktree_checkpoints.py#L505-L523)):

The existing context pollution detection has a critical gap:

```python
# autobuild.py lines 1014-1037
if self.rollback_on_pollution:
    if self._checkpoint_manager.should_rollback():
        target_turn = self._checkpoint_manager.find_last_passing_checkpoint()
        if target_turn:                           # ← What if None?
            # ... rollback and continue ...
        # ELSE: silently continues the loop!      # ← NO HANDLING
```

When `should_rollback()` returns `True` (2+ consecutive failures detected) but `find_last_passing_checkpoint()` returns `None` (no turn ever passed), the code **silently continues the loop**. This is exactly what happened for CR-007 and CR-008:

1. Turn 1: tests fail → checkpoint with `tests_passed=False`
2. Turn 2: tests fail → checkpoint with `tests_passed=False` → `should_rollback()=True` → `find_last_passing_checkpoint()=None` → **silently continues**
3. Turns 3-25: same pattern, 23 more wasted turns

The log confirms this:
```
WARNING: Context pollution detected: 2 consecutive test failures in turns [1, 2]
WARNING: No passing checkpoints found in history
```

The system correctly identifies the unrecoverable situation but takes no action. There is also:
- No detection of **identical Coach feedback** across consecutive turns
- No detection of **0% criteria progress** sustained over N turns
- No early exit when the situation is structurally unrecoverable

### Finding 6: Task Type Detector Priority Gap

**Severity**: Low
**Evidence** ([task_type_detector.py:251-261](guardkit/lib/task_type_detector.py#L251-L261)):

The auto-detector checks REFACTOR keywords (including "migrate", "migration") **before** DOCUMENTATION keywords. Since these are "Graphiti migration" tasks, even the auto-detector would classify them as REFACTOR. The word "trim" is absent from all keyword lists.

This is a minor issue since `/feature-plan` was not used here, but worth noting for future prevention.

---

## Root Cause Analysis

```
CR-007/CR-008 task_type = "refactor" (manually set, incorrect)
  → REFACTOR profile loaded (tests_required=True)
    → Player edits .md files, no tests created
      → task_work_results.json: quality_gates.all_passed = None
        → Coach: tests=None (required=True) → ALL_PASSED=False
          → Feedback: "Tests did not pass"
            → should_rollback()=True, find_last_passing_checkpoint()=None
              → NO EARLY EXIT — silently continues
                → Player retries with same approach
                  → Loop until MAX_TURNS_EXCEEDED (55 turns, ~50 min)
```

**Contributing Factors**:
1. **Primary**: Wrong `task_type` in task frontmatter (manually created feature)
2. **Secondary**: No early exit when stall detected (find_last_passing_checkpoint returns None)
3. **Tertiary**: Coach feedback doesn't suggest the actual issue or corrective action

---

## Why CR-009 Succeeds While CR-007/CR-008 Fail

| Factor | CR-009 | CR-007/CR-008 |
|--------|--------|---------------|
| task_type | refactor | refactor |
| Nature | Trim 5 .md files | Trim .md files |
| Player creates tests? | Yes (Turn 2) | No (any turn) |
| Coach: tests gate | PASS (Turn 2) | FAIL (all turns) |
| Result | APPROVED (2 turns) | MAX_TURNS_EXCEEDED |

The only difference is non-deterministic Player behaviour: CR-009's Player happened to create a pytest file that validates the trimming. This is fragile — the same task could fail on a different run.

---

## Recommendations

### Recommendation 1: Reclassify Task Types (Immediate Fix)

**Priority**: Critical
**Effort**: Trivial (2 YAML field changes)

Change the `task_type` field in CR-007 and CR-008 task definitions:

```yaml
# Before
task_type: refactor

# After
task_type: documentation
```

This switches to the DOCUMENTATION quality gate profile where `tests_required=False`, allowing the Coach to approve documentation-only changes without requiring tests.

### Recommendation 2: Add Unrecoverable Stall Detection to AutoBuild Loop

**Priority**: High
**Effort**: Low-Medium

When `should_rollback()` returns `True` but `find_last_passing_checkpoint()` returns `None`, the orchestrator should detect this as an **unrecoverable stall** and exit early instead of continuing to burn turns.

**Implementation**: In [autobuild.py](guardkit/orchestrator/autobuild.py) around line 1017:

```python
if self._checkpoint_manager.should_rollback():
    target_turn = self._checkpoint_manager.find_last_passing_checkpoint()
    if target_turn:
        # ... existing rollback logic ...
    else:
        # UNRECOVERABLE: No passing checkpoint ever existed
        logger.error(
            f"Unrecoverable stall detected for {task_id}: "
            f"context pollution detected but no passing checkpoint exists. "
            f"Exiting loop early to avoid wasting turns."
        )
        return turn_history, "unrecoverable_stall"
```

Additionally, add detection for **repeated identical feedback**:
- Track the last N Coach feedback messages
- If the same feedback repeats 3+ consecutive turns with 0% criteria progress, exit early

This would have saved 53 of the 55 wasted turns (~48 minutes).

### Recommendation 3: Add "trim" to Documentation Keywords in Task Type Detector

**Priority**: Low
**Effort**: Trivial

Add "trim" and "reduce" to the DOCUMENTATION keyword list in [task_type_detector.py:75-97](guardkit/lib/task_type_detector.py#L75-L97). This helps the auto-detector correctly classify content-reduction tasks when `/feature-plan` is used.

Also consider adding a file-extension-based heuristic: if a task description mentions only `.md` files, bias towards DOCUMENTATION regardless of other keywords.

### Recommendation 4: Coach Should Detect Documentation-Only Changes

**Priority**: Medium
**Effort**: Medium

Add a heuristic to the Coach validator: if all files modified/created have documentation extensions (`.md`, `.rst`, `.txt`, `.adoc`) and the task is typed as `refactor`, auto-relax the `tests_required` gate or warn that the task type may be incorrect.

This would be a safety net for misclassified tasks. Implementation location: [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py), in `verify_quality_gates()`.

### Recommendation 5: Improve Coach Feedback for Test-Less Tasks

**Priority**: Low
**Effort**: Low

When `tests_passed=None` and the task only modifies documentation files, the Coach feedback should say:
> "No tests found. If this is a documentation-only task, consider setting `task_type: documentation` in the task frontmatter."

Instead of the current generic "Tests did not pass during task-work execution" which doesn't help the Player understand the actual issue.

---

## Decision Matrix

| Fix | Impact | Effort | Risk | Recommendation |
|-----|--------|--------|------|----------------|
| Reclassify CR-007/CR-008 task types | High (immediate unblock) | Trivial | None | **Do immediately** |
| Unrecoverable stall detection | High (prevents future waste) | Low-Medium | Low | **Implement** |
| Add "trim" to doc keywords | Low (prevention) | Trivial | None | **Implement** |
| Coach doc-change detection | Medium (safety net) | Medium | Low | Consider |
| Improved Coach feedback | Low (developer UX) | Low | None | Consider |

---

## Appendix

### Files Analysed

- [tasks/backlog/context-reduction/TASK-CR-007-trim-orchestrators-md.md](tasks/backlog/context-reduction/TASK-CR-007-trim-orchestrators-md.md)
- [tasks/backlog/context-reduction/TASK-CR-008-trim-dataclass-pydantic-patterns.md](tasks/backlog/context-reduction/TASK-CR-008-trim-dataclass-pydantic-patterns.md)
- [tasks/backlog/context-reduction/TASK-CR-009-trim-remaining-pathgated-files.md](tasks/backlog/context-reduction/TASK-CR-009-trim-remaining-pathgated-files.md)
- [guardkit/models/task_types.py](guardkit/models/task_types.py) — Quality gate profiles and TaskType enum
- [guardkit/orchestrator/quality_gates/coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) — Coach validation logic
- [guardkit/orchestrator/agent_invoker.py](guardkit/orchestrator/agent_invoker.py) — Player invocation and results writing
- [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py) — AutoBuild loop and stall detection gap
- [guardkit/orchestrator/worktree_checkpoints.py](guardkit/orchestrator/worktree_checkpoints.py) — Checkpoint/rollback system
- [guardkit/lib/task_type_detector.py](guardkit/lib/task_type_detector.py) — Task type auto-detection
- [docs/reviews/graphiti_enhancement/max_turns_exceeded.md](docs/reviews/graphiti_enhancement/max_turns_exceeded.md) — Full error log (3,929 lines)

### Key Log Evidence

**CR-007 Turn 1** (line 758-761):
```
Using quality gate profile for task type: refactor
Quality gate evaluation complete: tests=None (required=True), coverage=True, arch=True, audit=True, ALL_PASSED=False
Quality gates failed for TASK-CR-007
Feedback: - Tests did not pass during task-work execution
```

**CR-007 Turn 2** — Context pollution detected but no action taken:
```
WARNING: Context pollution detected: 2 consecutive test failures in turns [1, 2]
WARNING: No passing checkpoints found in history
```

**CR-009 Turn 2** (line 1279-1283):
```
Using quality gate profile for task type: refactor
Quality gate evaluation complete: tests=True (required=True), coverage=True, arch=True, audit=True, ALL_PASSED=True
Task-specific tests detected for TASK-CR-009: 1 file(s)
Independent tests passed in 1.8s
Coach approved TASK-CR-009 turn 2
```

### Metrics

| Metric | Value |
|--------|-------|
| Total turns wasted (CR-007 + CR-008) | 55 (5 + 25 + 5 + 25) |
| Total execution time wasted | ~50 minutes |
| CR-009 turns to success | 2 |
| Wave 3 pass rate | 33% (1/3) |
| Turns saveable with stall detection | 53 (exit at turn 2 instead of 25+25+5+5) |
