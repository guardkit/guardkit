---
id: TASK-FIX-d5e6
title: Improve SDK API error classification and stall termination message
status: completed
task_type: implementation
created: 2026-02-23T00:00:00Z
updated: 2026-02-24T00:00:00Z
completed: 2026-02-24T00:00:00Z
priority: medium
tags: [autobuild, coach, failure-classification, stall-detection, gb10]
complexity: 2
parent_review: TASK-REV-ED10
feature_id: FEAT-7a2e
wave: 2
implementation_mode: task-work
dependencies: [TASK-FIX-f1a2]
test_results:
  status: passed
  tests_added: 7
  tests_total: 254
  coverage: null
---

# Task: Improve SDK API error classification and stall termination message

## Problem Statement

When the Coach Validator encounters `"SDK API error: invalid_request"`, the failure classifier
(`_classify_test_failure`) returns `failure_class=code, confidence=n/a` because the "SDK API error"
pattern does not match any known infrastructure failure pattern. This is a misclassification — the
failure is an SDK/API infrastructure problem, not a code defect in the Player's implementation.

Additionally, when the stall detector fires with a feedback pattern dominated by SDK API errors,
the stall termination message says "Review task_type classification and acceptance criteria", which
is misleading — the Player code is not the problem.

These two issues compound to make it hard to diagnose the real root cause from the autobuild
output alone.

## Acceptance Criteria

- [x] `_classify_test_failure()` in `coach_validator.py` recognises "SDK API error" and
      "invalid_request" patterns as `failure_class=sdk_api_error` (or existing `infrastructure`
      class with appropriate sub-type)
- [x] When the stall feedback for all N turns contains "SDK API error", the stall termination
      message in `autobuild.py` shows a targeted message such as:
      `"Stall caused by SDK API errors — check ANTHROPIC_BASE_URL configuration and SDK model
      name compatibility"` instead of the generic "Review task_type classification" message
- [x] Existing unit tests in `tests/unit/` pass
- [x] New test covers SDK API error pattern matching in `_classify_test_failure()`

## Implementation Summary

### coach_validator.py — `_classify_test_failure()`

Added `_SDK_API_ERROR_PATTERNS` class-level list with patterns:
- `"SDK API error"`, `"invalid_request"`, `"invalid_request_error"`, `"AssistantMessage.error"`

Check is inserted before `_INFRA_HIGH_CONFIDENCE` patterns. Returns `("sdk_api_error", "high")`.

### autobuild.py — `_build_summary_details()`

In the `unrecoverable_stall` branch, inspects the last 3 feedback entries from turn history.
If all contain `"SDK API error"`, shows targeted message mentioning ANTHROPIC_BASE_URL and
SERVED_MODEL_NAME. Otherwise falls back to the generic message.

### Tests Added (7 total)

**test_coach_validator.py — TestClassifyTestFailureSdkApiError (4 tests)**:
- `test_sdk_api_error_classified_correctly` — "SDK API error: invalid_request" → `("sdk_api_error", "high")`
- `test_invalid_request_error_classified` — "invalid_request_error" → `("sdk_api_error", "high")`
- `test_assistant_message_error_classified` — "AssistantMessage.error" → `("sdk_api_error", "high")`
- `test_unrelated_error_not_classified_as_sdk` — assertion error → `("code", "n/a")`

**test_autobuild_stall_detection.py — TestStallHintSdkApiError (3 tests)**:
- `test_sdk_api_error_stall_shows_targeted_hint` — all SDK feedback → targeted message
- `test_non_sdk_stall_shows_generic_hint` — non-SDK feedback → generic message
- `test_mixed_feedback_shows_generic_hint` — mixed feedback → generic message

## Files Modified

- `guardkit/orchestrator/quality_gates/coach_validator.py` — added `_SDK_API_ERROR_PATTERNS` and check
- `guardkit/orchestrator/autobuild.py` — conditional stall hint in `_build_summary_details()`
- `tests/unit/test_coach_validator.py` — added `TestClassifyTestFailureSdkApiError` (4 tests)
- `tests/unit/test_autobuild_stall_detection.py` — added `TestStallHintSdkApiError` (3 tests)
