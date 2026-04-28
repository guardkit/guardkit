---
id: TASK-REV-COSE
title: Diagnose Coach SDK-test-execution opaque-stderr fallback in coach_validator
status: backlog
task_type: review
review_mode: diagnostic
review_depth: standard
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: low
tags: [autobuild, coach-validator, sdk-test-execution, observability, R7]
related_reviews:
  - TASK-REV-9D13  # Origin review (filed this as sidequest)
related_features: []
complexity: 3
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-REV-COSE — Diagnose Coach SDK-test-execution opaque-stderr fallback

## Context

Filed as a sidequest from [TASK-REV-9D13 v2 §4 R7](../../.claude/reviews/TASK-REV-9D13-report.md#r7--coach-sdk-test-execution-opaque-stderr-sidequest-separate-review). Originating evidence at jarvis run-2 history lines 2989-2995:

```
ERROR:claude_agent_sdk._internal.query:Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution failed (error_class=Exception): Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
WARNING:guardkit.orchestrator.quality_gates.coach_validator:SDK test execution failed (error_class=Exception), falling back to subprocess.
INFO:guardkit.orchestrator.quality_gates.coach_validator:Independent tests passed in 3.3s
```

The Coach's SDK-mediated test-execution path raised `Command failed with exit code 1` whose `Error output:` was literally `"Check stderr output for details"` — uninformative. The subprocess fallback worked correctly (3.3 s, 18 tests passed). **The defect is the diagnostic surface, not the orchestration outcome.** Operators investigating the failure need to know *why* the SDK path failed.

## Goal

Produce a diagnostic report identifying:

1. Where the SDK-mediated test-execution path constructs and reads stderr in `guardkit/orchestrator/quality_gates/coach_validator.py`
2. Why the actual stderr is being lost between `claude_agent_sdk._internal.query` and the catch block in `coach_validator`
3. Whether the issue is upstream in `claude_agent_sdk` (transport/subprocess layer) or in GuardKit's exception-translation
4. A targeted fix proposal that surfaces the actual stderr without changing the fallback semantics (subprocess fallback should remain in place; only the diagnostic surface needs improvement)

## Investigation Scope

- `guardkit/orchestrator/quality_gates/coach_validator.py` — locate the `_run_independent_tests_via_sdk` (or equivalently named) method
- `claude_agent_sdk._internal.query` and `claude_agent_sdk._internal.transport.subprocess_cli` for the stderr capture pattern
- Whether the bundled `claude` CLI (`claude_agent_sdk/_bundled/claude`) writes to a different fd than the SDK reads
- Cross-reference with any existing related Graphiti facts (search `claude_agent_sdk MessageParseError SDK timeout subprocess` in `guardkit__project_decisions` and `guardkit__task_outcomes`)

## Acceptance Criteria

- [ ] Root cause of the opaque stderr identified with file:line evidence
- [ ] Determination: is this a GuardKit defect, an upstream `claude_agent_sdk` defect, or a `claude` CLI bundling issue?
- [ ] Targeted fix proposal (with file:line and ~5-10 line code sketch)
- [ ] Regression risk analysis (the subprocess fallback must continue to work; this is purely improving diagnostics)
- [ ] Report saved to `.claude/reviews/TASK-REV-COSE-report.md` per `/task-review` convention

## Out of Scope

- Removing the subprocess fallback (load-bearing for the case where SDK path fails for any reason)
- Refactoring the Coach validator beyond the stderr-capture path
- Investigating why the SDK-path was failing in the first place — that is a deeper rabbit hole; this review focuses on the **diagnostic surface**

## Suggested Workflow

```bash
/task-review TASK-REV-COSE --mode=diagnostic --depth=standard
```

Read `coach_validator.py` first; then trace through `claude_agent_sdk._internal.query` to understand how the `Fatal error in message reader` is constructed. Cross-check against the bundled `claude` CLI's output convention (does it write structured JSON to stdout and free-form errors to stderr, or interleave?).
