---
id: TASK-INFR-24DB
title: Infrastructure-aware conditional approval fallback
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
completed: 2026-02-17T00:00:00Z
priority: medium
tags: [autobuild, coach-validator, infrastructure, conditional-approval]
task_type: feature
complexity: 4
parent_review: TASK-REV-BA4B
feature_id: FEAT-INFRA
wave: 2
implementation_mode: task-work
dependencies: [TASK-INFR-6D4F, TASK-INFR-1670]
test_results:
  status: passed
  tests_total: 42
  tests_passed: 42
  tests_failed: 0
  last_run: 2026-02-17T00:00:00Z
---

# Task: Infrastructure-aware conditional approval fallback

## Description

When Docker is unavailable (TASK-INFR-5922's primary path fails), the Coach needs a fallback that prevents the infinite stall loop. This task implements the conditional approval path: when infrastructure tests fail, the task declares `requires_infrastructure`, the classification is high-confidence infrastructure, and all other quality gates pass, the Coach approves with a warning flag rather than returning feedback.

This is the **fallback** for environments without Docker. The primary path (TASK-INFR-5922) should be preferred when Docker is available.

## Acceptance Criteria

- [x] `CoachValidationResult` dataclass has new field: `approved_without_independent_tests: bool = False`
- [x] When independent tests fail with `classification=("infrastructure", "high")` AND `requires_infrastructure` is declared AND all other gates pass AND Docker was unavailable → Coach returns `approve` with `approved_without_independent_tests=True`
- [x] When classification is `("infrastructure", "ambiguous")` → existing feedback behavior (no conditional approval)
- [x] When `requires_infrastructure` is NOT declared → existing feedback behavior (no conditional approval)
- [x] AutoBuild summary displays conditional approval distinctly: "APPROVED (infra-dependent, independent tests skipped)"
- [x] `coach_turn_N.json` output includes `approved_without_independent_tests` flag for audit trail
- [x] Conditional approval is logged at WARNING level for visibility
- [x] Unit tests for:
  - High-confidence infra + declared deps + Docker unavailable → conditional approve
  - High-confidence infra + no declared deps → feedback (not approve)
  - Ambiguous infra + declared deps → feedback (not approve)
  - High-confidence infra + declared deps + Docker available → should not reach this path (Docker handles it)
  - All gates fail except tests → feedback (not approve, other gates must pass)

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` - Validate method decision path (line 575-616)
- `guardkit/orchestrator/autobuild.py` - Summary display, result handling
- `guardkit/orchestrator/schemas.py` - If CoachValidationResult is defined here

## Implementation Notes

### Decision path in coach_validator.py:575-616

Current:
```python
if not test_result.tests_passed:
    failure_class = self._classify_test_failure(test_result.raw_output)
    if failure_class == "infrastructure":
        # Always returns feedback
        return self._feedback_result(...)
```

Proposed:
```python
if not test_result.tests_passed:
    classification, confidence = self._classify_test_failure(test_result.raw_output)
    requires_infra = task.get("requires_infrastructure", [])
    docker_available = task.get("_docker_available", True)  # Set by TASK-INFR-5922

    if (classification == "infrastructure"
        and confidence == "high"
        and requires_infra
        and not docker_available
        and gates_status.all_gates_passed):
        logger.warning(
            f"Conditional approval for {task_id}: infrastructure failure "
            f"with declared deps {requires_infra}, Docker unavailable"
        )
        return self._approve_result(
            ...,
            approved_without_independent_tests=True,
        )

    # Existing feedback paths
    if classification == "infrastructure":
        return self._feedback_result(...)  # remediation suggestions
    else:
        return self._feedback_result(...)  # standard failure
```

### Dual-signal safety

Conditional approval requires BOTH signals to agree:
1. **Declared**: Task frontmatter says `requires_infrastructure: [postgresql]` (human intent)
2. **Detected**: Runtime classification says infrastructure failure with high confidence (runtime evidence)

This makes false positives extremely unlikely -- a code bug would need to both be pre-declared as infrastructure AND produce a ConnectionRefusedError.
