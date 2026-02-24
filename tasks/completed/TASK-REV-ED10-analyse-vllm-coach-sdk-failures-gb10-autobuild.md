---
id: TASK-REV-ED10
title: Analyse vLLM Coach SDK failures in GB10 autobuild feature run
status: completed
task_type: review
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:00:00Z
priority: high
tags: [autobuild, vllm, coach, sdk, review, gb10]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 7
  report_path: .claude/reviews/TASK-REV-ED10-review-report.md
  completed_at: 2026-02-23T00:00:00Z
  decision: implement
  implementation_feature: FEAT-7a2e
  implementation_tasks:
    - TASK-FIX-f1a2
    - TASK-FIX-b3c4
    - TASK-FIX-d5e6
    - TASK-FIX-g7h8
    - TASK-DOC-i1j2
    - TASK-FIX-k3l4
---

# Task: Analyse vLLM Coach SDK failures in GB10 autobuild feature run

## Description

Analyse the failures observed in the autobuild feature run `FEAT-EC3C` executed on the Dell GB10 machine against a local vLLM server (`ANTHROPIC_BASE_URL=http://localhost:8000`). The run log is at:

`docs/reviews/gb10_local_autobuild/api_feature_2.md`

The run failed at Wave 2 (TASK-C086) with `UNRECOVERABLE_STALL` after 3 turns. Two distinct failure categories were observed and require root cause analysis and recommended fixes.

## Observed Failures

### Failure 1: Environment Bootstrap — Externally-Managed Python (PEP 668)

After Wave 1 completed successfully, the environment bootstrap phase attempted to install Python packages using `/usr/bin/python3 -m pip install <package>` directly. All 6 install commands failed with:

```
error: externally-managed-environment
× This environment is externally managed
```

This is the Debian/Ubuntu PEP 668 protection against installing packages into the system Python. The bootstrap achieved `0/6` successes and logged:

```
⚠ Environment bootstrap partial: 0/6 succeeded
```

**Source**: `guardkit/orchestrator/environment_bootstrap.py`

### Failure 2: Coach Validator — SDK `invalid_request` on Test Execution

The Coach Validator attempted to run independent test verification via the Claude Agent SDK:

```
Running independent tests via SDK (environment parity): pytest tests/test_config.py -v --tb=short
SDK API error: invalid_request
SDK independent tests failed in 0.7-0.8s
```

This occurred identically on turns 1, 2, and 3 of TASK-C086. The stall detector correctly identified the pattern and terminated early:

```
Feedback stall: identical feedback (sig=9632f335) for 3 turns with 0 criteria passing
UNRECOVERABLE_STALL
```

The `invalid_request` error appears when the Coach Validator invokes the Claude Agent SDK with `ANTHROPIC_BASE_URL=http://localhost:8000` pointing to vLLM. The SDK fails immediately (~0.8s), suggesting vLLM rejects the request format used for the test execution sub-invocation.

### Secondary Observation: asyncio RuntimeError (non-fatal)

During Player SDK invocations, a recurring non-fatal error appeared:

```
ERROR:asyncio:Task exception was never retrieved
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

This originates from `anyio/_backends/_asyncio.py` when the async generator is closed (`GeneratorExit`). It appears on turns 2 and 3 of TASK-C086 but did NOT prevent Player turns from completing successfully.

## Acceptance Criteria

- [ ] Root cause identified for the `externally-managed-environment` pip failure in `environment_bootstrap.py`
- [ ] Root cause identified for `SDK API error: invalid_request` during Coach Validator test execution against vLLM
- [ ] Determine whether `invalid_request` is a vLLM compatibility issue (missing API feature) or a request format mismatch
- [ ] Assess whether the asyncio `RuntimeError` (cancel scope) is a real bug or benign noise when running against vLLM
- [ ] Provide specific, actionable fix recommendations for each failure category
- [ ] Determine if these failures are GB10/vLLM-specific or would also occur on other environments
- [ ] Identify whether the stall detection correctly terminated — or if it should have applied conditional approval instead

## Key Questions

1. What does the `invalid_request` vLLM error mean — is it an unsupported API endpoint, a missing model capability, or a malformed request?
2. Does `environment_bootstrap.py` have a virtualenv fallback, or does it only use system pip?
3. Why did the Coach conditional approval logic not trigger? (`failure_class=code, confidence=n/a, requires_infra=[], docker_available=True, all_gates_passed=True`)
4. Is there a way to configure the Coach to skip SDK-based test execution when running against vLLM, falling back to a direct subprocess test run?
5. Could the asyncio cancel scope error contribute to the `invalid_request` result on subsequent turns?

## Files to Review

- `docs/reviews/gb10_local_autobuild/api_feature_2.md` — Full run log
- `guardkit/orchestrator/environment_bootstrap.py` — Pip install logic
- `guardkit/orchestrator/quality_gates/coach_validator.py` — Coach SDK test execution and conditional approval
- `guardkit/orchestrator/agent_invoker.py` — SDK invocation and asyncio error handling
- `guardkit/orchestrator/autobuild.py` — Stall detection logic

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-ED10` to execute the analysis. No code changes should be made as part of this task — findings should inform separate fix tasks.

## Test Execution Log

_Automatically populated by /task-work_
