# Feature: CancelledError Exception Handling Fix

**Parent Review**: TASK-REV-C3F8
**Feature ID**: FEAT-CEF1
**Source**: [Review Report](../../../.claude/reviews/TASK-REV-C3F8-review-report.md) | [C4 Diagrams](../../../docs/reviews/vllm-profiling/c4-sequence-diagrams.md)

## Problem Statement

AutoBuild feature orchestration crashes with `AttributeError: 'CancelledError' object has no attribute 'success'` when a parallel wave task raises `CancelledError`. On Python 3.9+, `CancelledError` inherits from `BaseException` (not `Exception`), causing it to escape through 5 consecutive `except Exception` handlers and crash the result processing code.

## Solution Approach

1. Add `CancelledError` and `BaseException` isinstance checks in result processing (crash fix)
2. Add `CancelledError` handling at all 5 guard points in the invocation chain
3. Add PYTHONPATH env to Coach SDK options (fixes independent test failures)
4. Add cancellation diagnostics logging

## Subtask Summary

| Task | Description | Wave | Mode |
|------|-------------|------|------|
| TASK-CEF-001 | Fix result processing isinstance checks | 1 | task-work |
| TASK-CEF-002 | Add CancelledError handling at 5 guard points | 1 | task-work |
| TASK-CEF-003 | Add PYTHONPATH to Coach SDK options | 1 | direct |
| TASK-CEF-004 | Add cancellation diagnostics logging | 2 | direct |
