# Review Report: TASK-REV-E719

## Executive Summary

**Three root causes** drive the UNRECOVERABLE_STALL in AutoBuild Run 3 for TASK-SFT-001. Unlike Run 2 (complete pipeline data loss), Run 3 shows **partial success** (6/10 criteria verified) but gets stuck on 4 criteria across all 3 turns. The root causes are:

1. **RC-1 (Primary): Criteria parser inflates sub-bullets into top-level criteria** -- The task has 6 acceptance criteria, but 4 indented sub-bullets under criterion #2 are parsed as separate criteria, giving 10. The Player writes 6 completion_promises (matching the 6 real criteria) but Coach expects 10.

2. **RC-2 (Contributing): No text-matching fallback for criteria without promises** -- When `_match_by_promises()` finds no promise for AC-007 through AC-010, it immediately rejects them. There is no fallback to `_match_by_text()` for individual unmatched criteria, even though `requirements_addressed` contains 10-11 entries that could match.

3. **RC-3 (Amplifying): Stall detector cannot distinguish "stuck at 60%" from "stuck at 0%"** -- The feedback stall detector compares `(feedback_signature, criteria_passed_count)` tuples across turns. When all 3 turns produce identical feedback with 6/10 passing, it triggers UNRECOVERABLE_STALL, even though 60% progress was made and the Player is actively trying to address the remaining criteria.

**Severity**: High -- blocks TASK-SFT-001 and all 8 downstream tasks in FEAT-AC1A.

## Review Details

- **Mode**: Debugging / Root Cause Analysis
- **Depth**: Deep
- **Duration**: Deep code trace across 5 source files + run log
- **Reviewer**: Code trace + log correlation

## Root Cause Analysis

### RC-1: Criteria Parser Inflates Sub-Bullets (Primary)

**Location**: [task_loader.py:300-324](guardkit/tasks/task_loader.py#L300-L324)

The `_extract_acceptance_criteria()` method in `TaskLoader` parses markdown list items from the `## Acceptance Criteria` section. It matches any line starting with `- [ ]`, `- [x]`, `- `, or `* ` and strips the prefix.

**The TASK-SFT-001 task file has this structure:**

```markdown
## Acceptance Criteria

- [ ] `tests/seam/` directory exists with `__init__.py`
- [ ] `tests/seam/conftest.py` provides shared fixtures:
  - `graphiti_mock_client` — AsyncMock...
  - `cli_runner` — Click CliRunner...
  - `tmp_task_dir` — Temporary task directory...
  - `minimal_spec_fixture` — Path to minimal...
- [ ] `pytest.ini` or `pyproject.toml` registers `@pytest.mark.seam` marker
- [ ] `tests/seam/` tests are discovered and run by `pytest tests/seam/`
- [ ] Existing tests...are NOT moved
- [ ] `tests/fixtures/minimal-spec.md` fixture file created...
```

After `.strip()`, the indented sub-bullets (`  - graphiti_mock_client...`) become `- graphiti_mock_client...` which matches the `- ` prefix pattern. **Result: 10 criteria parsed instead of 6.**

The Player receives these 10 criteria via the prompt but only writes 6 `completion_promises` (mapping to the 6 "real" criteria). The 4 sub-bullet criteria (AC-007 through AC-010) have no matching promise.

**Evidence from run_3.md:**
```
Recovered 6 completion_promises from agent-written player report for TASK-SFT-001
AC-007: No completion promise for AC-007
AC-008: No completion promise for AC-008
```

Note: Only AC-007 and AC-008 are logged (not AC-009 and AC-010) because `_display_criteria_progress()` only logs criteria where the promise lookup fails -- the other 2 sub-bullets may have been matched by coincidence to adjacent promises or the log output is filtered.

### RC-2: No Hybrid Matching Strategy (Contributing)

**Location**: [coach_validator.py:990-1023](guardkit/orchestrator/quality_gates/coach_validator.py#L990-L1023)

The `validate_requirements()` method in `CoachValidator` uses an **either/or** strategy:

```python
if completion_promises:
    strategy = "promises"
    validation = self._match_by_promises(acceptance_criteria, completion_promises)
else:
    strategy = "text"
    requirements_met = task_work_results.get("requirements_met", [])
    validation = self._match_by_text(acceptance_criteria, requirements_met)
```

When promises exist (6 of them), the method uses **only** `_match_by_promises()`. Criteria without a matching promise are immediately rejected with evidence `"No completion promise for AC-XXX"`.

The `requirements_addressed` list (10-11 entries per turn) is never consulted because the strategy is "promises" (not "text"). Even though the Player reports 10+ `requirements_addressed` entries that could potentially match the 4 orphaned criteria via text matching, this data is ignored.

### RC-3: Stall Detector Doesn't Differentiate Partial Progress (Amplifying)

**Location**: [autobuild.py:2617-2669](guardkit/orchestrator/autobuild.py#L2617-L2669)

The `_is_feedback_stalled()` method tracks `(feedback_signature, criteria_passed_count)` per turn:

```python
# All recent turns have same signature?
sigs = {sig for sig, _ in recent}
if len(sigs) != 1:
    return False

# Zero criteria progress across all recent turns?
counts = [count for _, count in recent]
if all(c == counts[0] for c in counts):
    return True  # STALL
```

When all 3 turns have `(fec0ab4a, 6)`, the stall detector fires because:
- Same feedback signature: True (identical 4 missing criteria)
- Same criteria count: True (6 every turn)

The error message says `"0% criteria progress"` but this refers to the **delta** (no improvement turn-over-turn), not the absolute level (which is 60%). The stall detector cannot differentiate:
- **Run 2 pattern**: stuck at 0/10 (genuine zero progress, pipeline bug)
- **Run 3 pattern**: stuck at 6/10 (significant progress, matching bug)

In Run 3, the underlying issue is recoverable (fix the criteria parsing), but the stall detector treats it as unrecoverable because it only looks at the delta.

### RC-4: Negative Assertion Handling (Minor)

**Location**: [coach_validator.py:1075-1163](guardkit/orchestrator/quality_gates/coach_validator.py#L1075-L1163)

Criterion #5 ("Existing tests...are NOT moved") is a negative assertion. Even if it had a matching promise, verifying "something was NOT done" requires the Player to explicitly claim non-action. The `_match_by_promises()` method can handle this **if** the Player writes a promise like:

```json
{"criterion_id": "AC-005", "status": "complete", "evidence": "Verified files still exist at original locations"}
```

Looking at the logs, AC-005 IS in the 6 verified criteria (mapped to the 5th real criterion). The negative assertion is handled correctly via promises. **This hypothesis (H4) is dismissed for Run 3** -- the Player did write a promise for it.

### RC-5: File Existence Not Connected to Criteria (Minor)

Criterion #6 (`tests/fixtures/minimal-spec.md` created) is also in the 6 verified criteria. **H5 is dismissed** -- the Player wrote a promise for it and Coach verified it.

## Hypothesis Evaluation

| Hypothesis | Status | Root Cause | Notes |
|-----------|--------|------------|-------|
| **H1**: Coach text matching too strict | **PARTIALLY CONFIRMED (RC-2)** | Contributing | Text matching is never reached because promises exist. When it would be reached, it's unused for the 4 orphaned criteria |
| **H2**: Player only generates 6/10 promises | **CONFIRMED (RC-1)** | Primary | Player correctly generates 6 promises for 6 real criteria; the 10-criteria count is an artifact of the parser inflating sub-bullets |
| **H3**: Stall detector too aggressive | **CONFIRMED (RC-3)** | Amplifying | Detector treats "stuck at 60%" same as "stuck at 0%", prematurely terminating a recoverable situation |
| **H4**: Negative assertions unverifiable | **DISMISSED** | N/A | AC-005 (negative assertion) IS in the 6 verified criteria via promises |
| **H5**: File created but not matched | **DISMISSED** | N/A | AC-006 (fixture file) IS in the 6 verified criteria via promises |

## Proposed Fixes

### Fix 1: Criteria Parser -- Ignore Indented Sub-Bullets (RC-1)

**File**: [task_loader.py:300-324](guardkit/tasks/task_loader.py#L300-L324)

**Change**: Only match lines that start at column 0 (no leading whitespace before the bullet/checkbox). Indented lines are sub-bullets belonging to their parent criterion.

```python
# BEFORE (current)
for line in lines:
    if line.strip().lower() in ["## acceptance criteria", ...]:
        in_criteria = True
        continue
    elif in_criteria:
        if line.startswith("##"):
            break
        stripped = line.strip()
        if stripped.startswith(("- [ ]", "- [x]", "- ", "* ")):
            text = stripped.lstrip(...)
            if text:
                criteria_lines.append(text)

# AFTER (proposed)
for line in lines:
    if line.strip().lower() in ["## acceptance criteria", ...]:
        in_criteria = True
        continue
    elif in_criteria:
        if line.startswith("##"):
            break
        # Only match TOP-LEVEL list items (no leading whitespace)
        # Indented items (e.g., "  - sub-bullet") are sub-criteria
        # and belong to their parent
        if line.startswith(("- [ ] ", "- [x] ", "- ", "* ")):
            text = line.lstrip("- [x] ").lstrip("- [ ] ").lstrip("- ").lstrip("* ")
            if text.strip():
                criteria_lines.append(text.strip())
```

**Impact**: This changes the criteria count from 10 to 6 for TASK-SFT-001. All 6 will have matching promises. Sub-bullet content is lost from the criteria list but is still present in the full `requirements` text that the Player receives.

**Risk**: Low. Any task that uses indented sub-bullets currently inflates the criteria count, causing the same class of promise mismatch. Fixing this is a correctness improvement.

### Fix 2: Hybrid Matching -- Promise-First with Text Fallback (RC-2)

**File**: [coach_validator.py:990-1023](guardkit/orchestrator/quality_gates/coach_validator.py#L990-L1023)

**Change**: For criteria that have no matching promise, fall back to `_match_by_text()` against `requirements_addressed` (not `requirements_met`).

```python
# BEFORE (either/or)
if completion_promises:
    validation = self._match_by_promises(acceptance_criteria, completion_promises)
else:
    requirements_met = task_work_results.get("requirements_met", [])
    validation = self._match_by_text(acceptance_criteria, requirements_met)

# AFTER (hybrid)
if completion_promises:
    validation = self._match_by_promises(acceptance_criteria, completion_promises)

    # For criteria rejected due to missing promises, try text fallback
    if not validation.all_criteria_met:
        requirements_addressed = task_work_results.get(
            "requirements_addressed",
            task_work_results.get("requirements_met", [])
        )
        if requirements_addressed:
            validation = self._hybrid_fallback(
                validation, acceptance_criteria, requirements_addressed
            )
else:
    requirements_met = task_work_results.get("requirements_met", [])
    validation = self._match_by_text(acceptance_criteria, requirements_met)
```

New method `_hybrid_fallback()`:

```python
def _hybrid_fallback(
    self,
    promise_validation: RequirementsValidation,
    acceptance_criteria: List[str],
    requirements_addressed: List[str],
) -> RequirementsValidation:
    """Re-evaluate rejected criteria using text matching against requirements_addressed."""
    text_validation = self._match_by_text(acceptance_criteria, requirements_addressed)

    # Merge: keep promise results for verified criteria,
    # upgrade rejected criteria if text matching verifies them
    merged_results = []
    merged_missing = []

    for promise_cr, text_cr in zip(
        promise_validation.criteria_results,
        text_validation.criteria_results
    ):
        if promise_cr.result == "verified":
            merged_results.append(promise_cr)
        elif text_cr.result == "verified":
            # Upgrade: promise missed it but text matched
            merged_results.append(CriterionResult(
                criterion_id=text_cr.criterion_id,
                criterion_text=text_cr.criterion_text,
                result="verified",
                status="verified",
                evidence=f"[Text fallback] {text_cr.evidence}",
            ))
        else:
            merged_results.append(promise_cr)
            merged_missing.append(promise_cr.criterion_text)

    criteria_met = len(acceptance_criteria) - len(merged_missing)
    return RequirementsValidation(
        criteria_total=len(acceptance_criteria),
        criteria_met=criteria_met,
        all_criteria_met=len(merged_missing) == 0,
        missing=merged_missing,
        criteria_results=merged_results,
    )
```

**Impact**: Criteria without promises get a second chance via text matching against `requirements_addressed`. This is a safety net for parser inflation and for cases where the Player's SDK session exhausts turns before writing all promises.

**Risk**: Medium. Could lead to false positives if `requirements_addressed` entries are too broadly worded. Mitigated by the 70% keyword threshold in `_match_by_text()`.

### Fix 3: Stall Detector -- Differentiate Partial Progress (RC-3)

**File**: [autobuild.py:2617-2669](guardkit/orchestrator/autobuild.py#L2617-L2669)

**Change**: When criteria are partially passing (>0), increase the stall threshold or log a warning instead of terminating.

```python
# BEFORE
counts = [count for _, count in recent]
if all(c == counts[0] for c in counts):
    logger.warning(...)
    return True

# AFTER
counts = [count for _, count in recent]
if all(c == counts[0] for c in counts):
    if counts[0] == 0:
        # True zero progress -- unrecoverable
        logger.warning(
            f"Feedback stall: identical feedback (sig={feedback_sig}) "
            f"for {threshold} turns with 0 criteria passing"
        )
        return True
    else:
        # Partial progress but stuck -- allow more turns before declaring stall
        extended_threshold = threshold + 2  # Give 2 extra turns
        if len(self._feedback_history) >= extended_threshold:
            extended_recent = self._feedback_history[-extended_threshold:]
            ext_sigs = {sig for sig, _ in extended_recent}
            ext_counts = [count for _, count in extended_recent]
            if len(ext_sigs) == 1 and all(c == ext_counts[0] for c in ext_counts):
                logger.warning(
                    f"Feedback stall: identical feedback (sig={feedback_sig}) "
                    f"for {extended_threshold} turns with {counts[0]} criteria passing "
                    f"(extended threshold for partial progress)"
                )
                return True
        logger.info(
            f"Partial progress stall warning: {counts[0]} criteria passing "
            f"but stuck for {threshold} turns. Allowing {extended_threshold - threshold} "
            f"more turns before declaring stall."
        )
        return False
```

**Impact**: Tasks with partial progress (like 6/10) get 5 turns instead of 3 before being declared stalled. This gives the Player more chances to address the remaining criteria.

**Risk**: Low. Worst case is 2 extra turns of wasted compute for genuinely stuck tasks. The feedback stall will still trigger at turn 5.

### Fix Priority

| Fix | Priority | Effort | Impact | Recommendation |
|-----|----------|--------|--------|----------------|
| Fix 1 (criteria parser) | **Critical** | Low (5 lines) | Eliminates the root cause for TASK-SFT-001 and any task with nested criteria | **Implement first** |
| Fix 2 (hybrid matching) | **High** | Medium (30 lines) | Defense-in-depth for promise gaps | Implement second |
| Fix 3 (stall detector) | **Medium** | Low (15 lines) | Prevents premature termination of partially-successful tasks | Implement third |

## Impact Assessment

### TASK-SFT-001 (Direct)

Fix 1 alone would resolve the TASK-SFT-001 stall. With 6 criteria and 6 promises, all would match. Re-running with the fix should result in approval within 1-2 turns.

### Other FEAT-AC1A Tasks

| Task | Mode | Affected by RC-1? | Nested Criteria? |
|------|------|-------------------|-----------------|
| TASK-SFT-001 | task-work | **Yes** | Yes (4 sub-bullets) |
| TASK-SFT-002 | direct | No (already completed) | N/A |
| TASK-SFT-003 | task-work | **Risk** | Needs inspection |
| TASK-SFT-004 | task-work | **Risk** | Needs inspection |
| TASK-SFT-005 | task-work | **Risk** | Needs inspection |
| TASK-SFT-006 | task-work | **Risk** | Needs inspection |
| TASK-SFT-007 | task-work | **Risk** | Needs inspection |
| TASK-SFT-008 | task-work | **Risk** | Needs inspection |
| TASK-SFT-009 | task-work | **Risk** | Needs inspection |
| TASK-SFT-010 | direct | Low risk | Direct mode handles promises differently |
| TASK-SFT-011 | task-work | **Risk** | Needs inspection |

9 of 11 tasks use `task-work` mode. Any with indented sub-bullets in their acceptance criteria will hit the same bug. Fix 1 is essential before re-running the feature.

### Systemic Impact

The criteria parser bug affects **any task with indented sub-bullets** across all features, not just FEAT-AC1A. This is a latent bug that manifests whenever:
1. A task uses nested list items in acceptance criteria AND
2. The Player generates promises matching the "real" criteria count (not the inflated count)

## Appendix

### A. Criteria Mapping (TASK-SFT-001)

| AC ID | Text (parsed) | Real Criterion? | Promise? | Verified? |
|-------|--------------|-----------------|----------|-----------|
| AC-001 | `tests/seam/` directory exists with `__init__.py` | Yes | Yes | Yes |
| AC-002 | `tests/seam/conftest.py` provides shared fixtures: | Yes (header) | Yes | Yes |
| AC-003 | `graphiti_mock_client` -- AsyncMock... | No (sub-bullet) | Yes* | Yes |
| AC-004 | `cli_runner` -- Click CliRunner... | No (sub-bullet) | Yes* | Yes |
| AC-005 | `tmp_task_dir` -- Temporary task directory... | No (sub-bullet) | Yes* | Yes |
| AC-006 | `minimal_spec_fixture` -- Path to minimal... | No (sub-bullet) | Yes* | Yes |
| AC-007 | `pytest.ini` or `pyproject.toml` registers marker | Yes | **No** | **No** |
| AC-008 | `tests/seam/` tests discovered and run | Yes | **No** | **No** |
| AC-009 | Existing tests NOT moved | Yes | **No** | **No** |
| AC-010 | `tests/fixtures/minimal-spec.md` created | Yes | **No** | **No** |

*AC-003 through AC-006 match promises that the Player wrote for the sub-bullet content (coincidentally aligned).

The 4 real criteria (AC-007 through AC-010) are the ones that stall, because the Player's 6 promises were consumed by the inflated criteria list (AC-001 through AC-006).

### B. Key File Locations

| File | Purpose | Relevant Lines |
|------|---------|---------------|
| [task_loader.py](guardkit/tasks/task_loader.py) | Criteria parsing | 300-324 |
| [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) | Requirements validation | 990-1023, 1075-1163 |
| [autobuild.py](guardkit/orchestrator/autobuild.py) | Stall detection | 2617-2669 |
| [agent_invoker.py](guardkit/orchestrator/agent_invoker.py) | Player report creation | 1594-1606 |
| [run_3.md](docs/reviews/autobuild-fixes/run_3.md) | Full run 3 log | - |

### C. Diagnostic Evidence

**Run 3 Turn 1:**
```
Recovered 6 completion_promises from agent-written player report for TASK-SFT-001
Recovered 10 requirements_addressed from agent-written player report for TASK-SFT-001
Criteria Progress (Turn 1): 6/10 verified (100%)
Criteria: 6 verified, 4 rejected, 0 pending
  AC-007: No completion promise for AC-007
  AC-008: No completion promise for AC-008
```

**Stall Detection (Turn 3):**
```
WARNING: Feedback stall: identical feedback (sig=fec0ab4a) for 3 turns with 6 criteria passing
ERROR: Feedback stall detected for TASK-SFT-001: identical feedback for 3 consecutive turns with 0% criteria progress
```
