---
id: TASK-INT-001
title: Implement unified Coach validation flow integrating security and honesty checks
status: backlog
task_type: implementation
created: 2026-01-01T12:30:00Z
priority: high
tags: [integration, autobuild, coach, security, validation]
complexity: 4
parent_review: TASK-REV-INT01
implementation_mode: task-work
conductor_workspace: feature-integration-wave1-1
dependencies:
  - TASK-TWD-008  # Honesty Verification
  - TASK-TWD-009  # Promise-Based Completion
  - TASK-SEC-001  # Quick Security Checks
  - TASK-SEC-003  # Security-Specialist Invocation
---

# TASK-INT-001: Unified Coach Validation Flow

## Description

Integrate security checks, honesty verification, and promise verification into a single coherent Coach validation flow. This task ensures both features work together correctly when both are deployed.

**Source**: [TASK-REV-INT01 Integration Review](../../TASK-REV-INT01-feature-integration-review.md)

## Requirements

### 1. Validation Order

Implement the following check order in `coach_validator.py`:

```python
def validate(task_id, turn, task):
    # 1. Read task-work results (existing)
    results = read_quality_gate_results(task_id)

    # 2. Verify quality gates passed (existing)
    if not results["test_results"]["all_passed"]:
        return feedback(...)

    # 3. Quick Security Checks (SEC-001, ~30s, always run)
    security_config = load_security_config(task)
    if security_config.level != "skip":
        quick_findings = run_quick_security_checks()
        critical = [f for f in quick_findings if f.severity == "critical"]
        if critical:
            return feedback("Critical security issues", findings=critical)

    # 4. Full Security Review (SEC-003, conditional)
    if should_run_full_review(task, security_config):
        full_findings = invoke_security_specialist(task)
        blocking = [f for f in full_findings if f.severity in ["critical", "high"]]
        if blocking:
            return feedback("Security review issues", findings=blocking)

    # 5. Run tests independently (existing - trust but verify)
    test_result = run_tests_yourself()

    # 6. Honesty Verification (TWD-008)
    honesty_check = verify_player_claims(player_report, test_result)
    if honesty_check.discrepancies:
        critical_discrepancies = [d for d in honesty_check.discrepancies
                                  if d.severity == "critical"]
        if critical_discrepancies:
            return feedback("Honesty verification failed", discrepancies=critical_discrepancies)

    # 7. Validate requirements (existing)
    if not all_criteria_met(...):
        return feedback(...)

    # 8. Promise Verification (TWD-009)
    if "completion_promise" in player_report:
        criteria_verification = verify_completion_promises(player_report, task)
        unverified = [c for c in criteria_verification if not c.coach_verified]
        if unverified:
            return feedback("Not all criteria verified", unverified=unverified)

    # 9. Approve (existing)
    return approve()
```

### 2. Priority Ordering for Multiple Issues

When multiple checks fail, report in priority order:

| Priority | Check Type | Rationale |
|----------|------------|-----------|
| 1 | Quality gates (tests, coverage) | Fundamental functionality |
| 2 | Critical security findings | Objective, high impact |
| 3 | Full security review blocking | Auth/sensitive code issues |
| 4 | Honesty discrepancies | Player claim verification |
| 5 | Requirements not met | Functional completeness |
| 6 | Promise verification failed | Criterion-level granularity |

### 3. Decision Format Integration

Unified decision JSON should include all relevant sections:

```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "feedback",
  "validation_results": {
    "quality_gates": { ... },
    "security": {
      "quick_checks_run": true,
      "quick_findings": [],
      "full_review_run": false,
      "full_findings": []
    },
    "honesty": {
      "verified": true,
      "discrepancies": []
    },
    "requirements": { ... },
    "promises": {
      "verified": true,
      "criteria": []
    }
  },
  "issues": [ ... ],
  "rationale": "..."
}
```

## Acceptance Criteria

- [ ] Security checks run before honesty verification
- [ ] Quick security checks always run (unless `skip` level)
- [ ] Full security review runs only when conditions met
- [ ] Honesty verification uses test results from independent run
- [ ] Promise verification runs after all other checks
- [ ] Priority ordering applied when multiple issues found
- [ ] Decision JSON includes all validation sections
- [ ] Existing tests still pass
- [ ] New integration tests added (see INT-002)

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Integrate validation order |
| `.claude/agents/autobuild-coach.md` | Update validation documentation |

## Technical Notes

### Check Independence

Each check should be independent and not affect others:
- Security findings don't modify test results
- Honesty discrepancies don't affect security checks
- Each check writes to separate decision sections

### Performance Considerations

- Quick security checks: ~30s timeout
- Full security review: ~2-5min timeout (conditional)
- Honesty verification: Re-uses test results, no additional test run
- Promise verification: Lightweight comparison

### Error Handling

If any check fails to execute (timeout, error):
- Log the error
- Mark that check as "skipped" in decision
- Continue with remaining checks
- Don't block approval for check execution failures (only findings block)

## Out of Scope

- Modifying individual check implementations (TWD-008, TWD-009, SEC-001, SEC-003)
- Adding new check types
- Changing configuration schemas

## Testing

See TASK-INT-002 for integration test requirements.
