---
id: TASK-INT-002
title: Add integration tests for combined TWD + SEC functionality
status: backlog
task_type: implementation
created: 2026-01-01T12:30:00Z
priority: medium
tags: [integration, testing, autobuild, coach]
complexity: 3
parent_review: TASK-REV-INT01
implementation_mode: task-work
conductor_workspace: feature-integration-wave1-2
dependencies:
  - TASK-INT-001  # Unified Coach Validation Flow
---

# TASK-INT-002: Integration Tests for Combined Features

## Description

Create comprehensive integration tests that exercise both TWD and SEC features together, ensuring they work correctly when deployed simultaneously.

**Source**: [TASK-REV-INT01 Integration Review](../../TASK-REV-INT01-feature-integration-review.md)

## Requirements

### Test Scenarios

#### 1. Security Issues + Honest Player

```python
def test_security_blocks_honest_player():
    """Security issues should block even when Player is honest."""
    # Given: Player report with accurate claims (tests pass)
    # And: Code contains critical security vulnerability (hardcoded secret)
    # When: Coach validates
    # Then: Feedback with security issue
    # And: Honesty verified = True (Player was honest)
    # And: Decision = feedback (security blocks)
```

#### 2. Dishonest Player + No Security Issues

```python
def test_honesty_blocks_secure_code():
    """Honesty discrepancy should block even when code is secure."""
    # Given: Player claims 10 tests pass
    # And: Actually only 7 tests pass
    # And: No security vulnerabilities
    # When: Coach validates
    # Then: Feedback with honesty discrepancy
    # And: Security check passed
    # And: Decision = feedback (honesty blocks)
```

#### 3. Security Issues + Dishonest Player

```python
def test_both_issues_reported_in_priority_order():
    """Both security and honesty issues should be reported."""
    # Given: Player claims tests pass (false)
    # And: Code has SQL injection vulnerability
    # When: Coach validates
    # Then: Feedback includes both issues
    # And: Security issue listed first (higher priority)
    # And: Honesty discrepancy listed second
```

#### 4. Full Approval Flow

```python
def test_full_approval_both_features():
    """Clean code with honest Player should be approved."""
    # Given: Player report with accurate claims
    # And: All tests actually pass
    # And: No security vulnerabilities
    # And: All acceptance criteria mapped with evidence
    # When: Coach validates
    # Then: Decision = approve
    # And: All validation sections populated
```

#### 5. Full Security Review Triggered

```python
def test_full_security_review_for_auth_task():
    """Auth-tagged tasks should trigger full security review."""
    # Given: Task with tag "authentication"
    # And: Security config level = standard
    # When: Coach validates
    # Then: Full security review invoked
    # And: Quick checks also run
```

#### 6. Security Skip Configuration

```python
def test_security_skip_bypasses_checks():
    """Security level = skip should bypass all security checks."""
    # Given: Task with security.level = skip
    # And: Code has security vulnerabilities
    # When: Coach validates
    # Then: Security checks NOT run
    # And: Validation continues with other checks
```

#### 7. Promise Verification Integration

```python
def test_promise_verification_after_security():
    """Promise verification should run after security passes."""
    # Given: Player with completion_promise
    # And: All security checks pass
    # And: Honesty verification passes
    # And: One criterion not verified by evidence
    # When: Coach validates
    # Then: Feedback with unverified criterion
    # And: Security and honesty sections show passed
```

### Edge Cases

#### 8. Check Timeout Handling

```python
def test_security_timeout_continues_validation():
    """Security check timeout should not block other checks."""
    # Given: Security-specialist times out (>5min)
    # When: Coach validates
    # Then: Security section shows "skipped" with reason
    # And: Other checks still execute
    # And: Approval possible if other checks pass
```

#### 9. Multiple Critical Findings

```python
def test_multiple_critical_findings_all_reported():
    """All critical findings should be reported, not just first."""
    # Given: 3 critical security findings
    # And: 2 honesty discrepancies
    # When: Coach validates
    # Then: All 5 issues in feedback
    # And: Grouped by category
```

## Acceptance Criteria

- [ ] All 9 test scenarios implemented
- [ ] Tests use mock fixtures (no real SDK calls)
- [ ] Tests verify decision JSON structure
- [ ] Tests verify priority ordering
- [ ] Tests verify all validation sections populated
- [ ] Tests pass in CI pipeline
- [ ] Test coverage report shows integration paths covered

## Files to Create/Modify

| File | Changes |
|------|---------|
| `tests/integration/test_coach_combined_validation.py` | New file with all tests |
| `tests/fixtures/coach_validation_fixtures.py` | Mock data for tests |

## Technical Notes

### Test Fixtures

Create reusable fixtures for:
- Player reports (honest and dishonest variants)
- Security findings (clean, quick findings, full review findings)
- Task configurations (various security levels and tags)
- Acceptance criteria (complete and incomplete mappings)

### Mocking Strategy

Mock the following components:
- `run_quick_security_checks()` - Return pre-defined findings
- `invoke_security_specialist()` - Return pre-defined findings (or simulate timeout)
- `run_tests_yourself()` - Return pre-defined test results
- `verify_player_claims()` - Use real implementation with mock inputs
- `verify_completion_promises()` - Use real implementation with mock inputs

### Assertions

Each test should assert:
1. Correct decision (approve/feedback)
2. Correct validation sections populated
3. Correct priority ordering of issues
4. Correct rationale text

## Out of Scope

- Unit tests for individual checks (covered by TWD and SEC feature tests)
- Performance testing
- End-to-end tests with real SDK

## Dependencies

This task depends on TASK-INT-001 (Unified Coach Validation Flow) being complete.
