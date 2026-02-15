---
id: TASK-ASF-006
title: Enrich synthetic recovery reports with file-existence promises (R4-full)
task_type: feature
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 3
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-ASF-005
priority: high
status: backlog
tags: [autobuild, stall-fix, R4-full, phase-3, synthetic-report]
---

# Task: Enrich synthetic recovery reports with file-existence promises (R4-full)

## Description

This is the **second phase** of the two-phase R4 fix. After R4-lite (TASK-ASF-004) added observability and R5 (TASK-ASF-005) scoped test detection, this task enriches synthetic recovery reports with `completion_promises` based on file-existence verification.

Currently, `_build_synthetic_report()` produces reports with empty `requirements_addressed` and no `completion_promises`, making Coach approval impossible regardless of actual work done. For scaffolding tasks, many acceptance criteria are file-existence checks that can be verified from git state.

**CRITICAL ORDERING**: This task depends on R5 (TASK-ASF-005) being complete. The diagnostic diagrams identified a false approval risk: if synthetic reports gain file-existence promises but test detection is still worktree-wide, scaffolding tasks could be approved via file-existence promises while their task-specific tests are failing.

## Root Cause Addressed

- **F2**: Synthetic recovery reports structurally cannot satisfy Coach criteria (`autobuild.py:2114-2136`)
- **New finding**: No fast-fail for synthetic reports — Coach runs full validation on reports that can never pass

## Implementation

### Phase 1: Fast-fail for synthetic reports

```python
# coach_validator.py — in validate_requirements()
def validate_requirements(self, acceptance_criteria, task_work_results, turn):
    is_synthetic = task_work_results.get("_synthetic", False)

    if is_synthetic:
        logger.info(f"Synthetic report detected — skipping promise matching, "
                    f"using file-existence verification")
        # Skip _match_by_promises() — guaranteed to fail for synthetic
        # Go directly to enriched verification
        return self._match_synthetic_report(
            acceptance_criteria, task_work_results
        )

    # Normal path: promises first, then text fallback
    completion_promises = self._load_completion_promises(task_work_results, turn)
    ...
```

### Phase 2: File-existence promise generation (scaffolding only)

```python
# autobuild.py — in _build_synthetic_report()
def _build_synthetic_report(self, work_state, task_id, turn):
    report = {
        "_synthetic": True,
        "files_created": work_state.files_created,
        "files_modified": work_state.files_modified,
        ...
    }

    # For scaffolding tasks, generate file-existence promises
    if self._task_type == "scaffolding" and self._acceptance_criteria:
        promises = self._generate_file_existence_promises(
            work_state, self._acceptance_criteria
        )
        if promises:
            report["completion_promises"] = promises
            logger.info(f"Generated {len(promises)} file-existence promises "
                       f"for synthetic report")

    return report
```

## Files to Modify

1. `guardkit/orchestrator/autobuild.py` — Enrich `_build_synthetic_report()` with file-existence promise generation (~line 2114)
2. `guardkit/orchestrator/quality_gates/coach_validator.py` — Add `_match_synthetic_report()` fast-fail path (~line 1040)
3. `guardkit/orchestrator/autobuild.py` — Add `_generate_file_existence_promises()` helper method

## Acceptance Criteria

- [ ] Synthetic reports for scaffolding tasks include `completion_promises` based on file existence
- [ ] Coach uses `_match_synthetic_report()` fast-fail when `_synthetic: True` flag detected
- [ ] File-existence promises only match criteria that are verifiable by file presence (not content)
- [ ] Non-scaffolding tasks are unaffected (no promises generated for non-scaffolding synthetic reports)
- [ ] Coach's test gate still runs after promise matching (promises alone don't bypass test verification)
- [ ] Task-scoped test detection (R5) is used when verifying synthetic report tests
- [ ] Tests cover: scaffolding task with files present, scaffolding task with files missing, non-scaffolding task

## Regression Risk

**Medium** — This changes the Coach's validation path for synthetic reports. Key risks:
1. **False approval**: File-existence promises could approve a task whose files exist but have wrong content. Mitigated by: promises only cover file-existence criteria, not content criteria.
2. **Coach validation change**: Adding `_match_synthetic_report()` changes the validation flow for recovered turns. Mitigated by: only activates when `_synthetic: True` flag is present (set by R4-lite).
3. **Task-type coupling**: `_build_synthetic_report()` gains awareness of task types. Mitigated by: gated behind `task_type == "scaffolding"` check.

## Interaction Notes

- **Depends on R5 (TASK-ASF-005)**: Test detection must be scoped before promises are generated. See Diagram 5 interaction risk.
- **Uses R4-lite flag (TASK-ASF-004)**: The `_synthetic: True` flag from R4-lite is used for fast-fail routing.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 2, Recommendation R4)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 4, Diagram 5)
