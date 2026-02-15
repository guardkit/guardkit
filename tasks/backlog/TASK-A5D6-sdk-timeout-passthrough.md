---
id: TASK-A5D6
title: "Investigate SDK timeout parameter not passing through correctly"
status: review_complete
created: 2026-02-15T12:00:00Z
updated: 2026-02-15T14:00:00Z
priority: high
tags: [autobuild, sdk-timeout, bug-investigation]
task_type: review
complexity: 4
review_results:
  mode: decision
  depth: standard
  score: 85
  findings_count: 5
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-A5D6-review-report.md
  completed_at: 2026-02-15T14:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Investigate SDK timeout parameter not passing through correctly

## Description

The `--sdk-timeout` CLI parameter is not being correctly propagated when running `guardkit autobuild feature`. Running with `--sdk-timeout 3600` still results in the SDK timing out at 1800s, indicating the value is either being overridden, capped, or lost somewhere in the parameter chain.

**Reproduction command:**
```bash
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-AC1A --max-turns 30 --sdk-timeout 3600
```

**Expected:** `sdk_timeout=3600s` in AutoBuildOrchestrator logs
**Actual:** `sdk_timeout=1800s` observed in orchestrator initialization

## Evidence

- Run log: `docs/reviews/autobuild-fixes/run_1.md`
- Analysis: `docs/reviews/autobuild-fixes/run_1_analysis.md`
- Log line 75 shows: `sdk_timeout=1800s` despite user intending 3600
- Log line 1 shows command was `--sdk-timeout 1800` (the value that was actually used in the logged run)

## Investigation Areas

### Parameter Flow Chain
1. **CLI entry** (`guardkit/cli/autobuild.py`): `--sdk-timeout` option defined with `default=None`, validated 60-3600
2. **Feature orchestrator** (`guardkit/orchestrator/feature_orchestrator.py`): Receives `sdk_timeout` and passes to per-task AutoBuildOrchestrator. Resolution: CLI > task frontmatter > default (1200)
3. **AutoBuild orchestrator** (`guardkit/orchestrator/autobuild.py`): Constructor default is 1200, stores as `self.sdk_timeout`
4. **Agent invoker** (`guardkit/orchestrator/agent_invoker.py`): `DEFAULT_SDK_TIMEOUT=1200`, has dynamic calculation via `_calculate_sdk_timeout()` that checks if value differs from default

### Potential Issues to Investigate

1. **CLI `feature` subcommand vs `task` subcommand**: The `--sdk-timeout` may be defined on the `task` subcommand but not correctly passed through the `feature` subcommand path
2. **Feature orchestrator sdk_timeout resolution**: Check if `self.sdk_timeout` is being overridden by task frontmatter values or defaults during per-task execution
3. **AgentInvoker dynamic timeout calculation**: The `_calculate_sdk_timeout()` method has override detection logic comparing against `DEFAULT_SDK_TIMEOUT` - verify this works correctly for feature-level orchestration
4. **Default value inconsistency**: Tests expect default of 900, code defaults to 1200, and observed behavior shows 1800 - multiple default values in play
5. **Task-level `autobuild.sdk_timeout` frontmatter**: Check if FEAT-AC1A task files have frontmatter that overrides the CLI value

## Acceptance Criteria

- [ ] AC-001: Trace exact code path where `--sdk-timeout 3600` gets reduced to 1800
- [ ] AC-002: Identify whether the issue is in CLI parsing, feature orchestrator, or autobuild orchestrator
- [ ] AC-003: Verify the `feature` subcommand correctly passes `sdk_timeout` to `FeatureOrchestrator.__init__()`
- [ ] AC-004: Check task frontmatter in FEAT-AC1A tasks for overriding `autobuild.sdk_timeout` values
- [ ] AC-005: Document the fix with clear before/after behavior
- [ ] AC-006: Ensure tests cover the sdk_timeout passthrough for the feature orchestration path

## Key Files

- `guardkit/cli/autobuild.py` - CLI argument definition and subcommand handlers
- `guardkit/orchestrator/feature_orchestrator.py` - Feature-level orchestration
- `guardkit/orchestrator/autobuild.py` - Per-task orchestration
- `guardkit/orchestrator/agent_invoker.py` - SDK invocation with timeout
- `docs/reviews/autobuild-fixes/run_1.md` - Failure evidence
- `docs/reviews/autobuild-fixes/run_1_analysis.md` - Failure analysis (F1: SDK Timeout)

## Implementation Notes

This is a review/investigation task. The fix should be implemented in a follow-up task after the root cause is identified.
