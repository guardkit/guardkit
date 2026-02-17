---
id: TASK-PCTD-3182
title: "SDK Bash tool environment parity for Coach test execution (Option C)"
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: critical
tags: [autobuild, coach-validator, environment-parity, sdk, root-cause-fix]
task_type: feature
complexity: 7
parent_review: TASK-REV-D7B2
feature_id: FEAT-27F2
wave: 3
implementation_mode: task-work
dependencies: [TASK-PCTD-5208]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: SDK Bash tool environment parity for Coach test execution (Option C)

## Description

This is the **root cause fix** for the Player/Coach test divergence (Finding F1 in TASK-REV-D7B2). The Coach currently runs tests via `subprocess.run(shell=True)` which uses `/bin/sh` without sourcing user shell profiles, venv activation, or environment variables. The Player runs tests via the Claude Agent SDK's Bash tool which inherits the full user environment.

**Solution**: Use a minimal Claude Agent SDK invocation (1 turn, Haiku model, Bash-only) to run Coach tests, achieving 100% environment parity with the Player. Fall back to `subprocess.run()` only on explicit config or SDK errors.

The SDK is a **hard runtime requirement** for AutoBuild (enforced by `_require_sdk()` at both CLI entry points), so it is always available when CoachValidator executes.

## Acceptance Criteria

- [ ] `_run_tests_via_sdk()` async method added to `CoachValidator`
- [ ] Uses `ClaudeAgentOptions(model="claude-haiku-4-5-20251001", max_turns=1, allowed_tools=["Bash"], permission_mode="bypassPermissions")`
- [ ] Handles `UserMessage` with `ToolResultBlock` to capture Bash output (GAP-FIX #4)
- [ ] Handles `ToolResultBlock.content` as `str | list[dict] | None` (GAP-FIX #5)
- [ ] Uses `ToolResultBlock.is_error` for pass/fail determination, NOT text parsing (GAP-FIX #6/#7)
- [ ] Provides `duration_seconds` in all `IndependentTestResult` return paths (GAP-FIX #8)
- [ ] Uses `asyncio.get_event_loop()` with try/except safety pattern (GAP-FIX #9)
- [ ] `run_independent_tests()` modified to try SDK first, subprocess fallback on error
- [ ] `CoachValidator.__init__()` accepts `coach_test_execution: str = "sdk"` parameter
- [ ] `AutoBuildOrchestrator._load_coach_config()` reads from `.guardkit/config.yaml` under `autobuild.coach.test_execution`
- [ ] Config option: `"sdk"` (default) or `"subprocess"` (explicit opt-out)
- [ ] All 4 `IndependentTestResult` fields populated in every return path (data contract validation)
- [ ] 15 tests per test plan in review report (unit + integration)

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `__init__()`, `run_independent_tests()`, `_run_tests_via_sdk()` (new)
- `guardkit/orchestrator/autobuild.py` — `_invoke_coach_safely()` (CoachValidator instantiation), `_load_coach_config()` (new)

## Implementation Notes

**CRITICAL**: The review report contains a fully validated implementation with 9 GAP-FIX annotations. The implementation was validated against SDK v0.1.18 API surface. See `.claude/reviews/TASK-REV-D7B2-review-report.md` R5 section for:

- Complete `_run_tests_via_sdk()` code with all 9 GAP-FIX annotations
- Complete `run_independent_tests()` code with SDK-first + subprocess fallback
- `CoachValidator.__init__()` changes
- `AutoBuildOrchestrator._load_coach_config()` code
- C4 Level 3 component interaction diagram with gap-fix annotations
- C4 Level 2 event loop lifecycle diagram proving no nested `run_until_complete`
- Data contract validation tracing all 4 `IndependentTestResult` fields
- 15-item test plan

### Key Technology Seam Risks (All Pre-Mitigated)

| # | Seam | Risk | Mitigation |
|---|------|------|------------|
| 2 | SDK `--model` flag | CLI doesn't recognize shorthand | Full ID: `"claude-haiku-4-5-20251001"` |
| 4 | SDK message parser | Bash output in `UserMessage`, not `AssistantMessage` | Handle `UserMessage` with `ToolResultBlock` |
| 5 | `ToolResultBlock.content` type union | `str \| list[dict] \| None` | Type-check and extract properly |
| 6/7 | Pass/fail determination | `is_error` reflects exit code, not text parsing | Use `is_error` as primary signal |
| 9 | async/sync bridge | `RuntimeError: no current event loop` | Use exact `autobuild.py:3459-3463` pattern |

## Test Execution Log
[Automatically populated by /task-work]
