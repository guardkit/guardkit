---
id: TASK-REV-GB10
title: Analyse vLLM local autobuild failures on GB10 ProMax
status: review_complete
task_type: review
review_mode: debugging
review_depth: deep
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:00:00Z
priority: high
tags: [autobuild, vllm, local-inference, gb10, sdk-error, bug]
complexity: 5
source_file: docs/reviews/gb10_local_autobuild/api_feature_1.md
review_results:
  mode: debugging
  depth: deep
  findings_count: 5
  bugs_confirmed: 2
  decision: implement
  report_path: .claude/reviews/TASK-REV-GB10-review-report.md
  implementation_tasks: [TASK-FIX-d999, TASK-FIX-e78d]
  vllm_fix_applied: scripts/vllm-serve.sh max_model_len 65536→131072
  completed_at: 2026-02-23T00:00:00Z
---

# Task: Analyse vLLM local autobuild failures on GB10 ProMax

## Description

Analyse the failures and errors from a `guardkit autobuild feature` run against the local vLLM
inference server on the Dell ProMax GB10 (`ANTHROPIC_BASE_URL=http://localhost:8000`). The run
attempted to build FEAT-EC3C (FastAPI app with health endpoint, 3 tasks / 3 waves).

Wave 1 (TASK-70ED) eventually passed after 2 turns via state recovery, but Wave 2 (TASK-C086)
crashed with a hard GuardKit exception, halting the entire feature build.

Source log: `docs/reviews/gb10_local_autobuild/api_feature_1.md`

## Identified Issues

### Issue 1 — Recurring `SDK agent error: unknown` (Critical)

**Every** Player invocation fails with:
```
ERROR:guardkit.orchestrator.agent_invoker:[TASK-XXX] SDK API error in stream: unknown
✗ Player failed: SDK agent error: unknown
```

This happens after a working period (270–480 s of tool activity visible in the logs), then the
SDK stream terminates with an opaque `unknown` error. The pattern is consistent across all 3
Player turns in the log. This is almost certainly the vLLM backend dropping the connection /
truncating the stream — either due to context-length exhaustion, a generation-length cap, or a
server-side timeout.

**Related**: A concurrent `RuntimeError: Attempted to exit cancel scope in a different task than
it was entered in` appears in the anyio cancel scope during SDK teardown (lines 155–174 of the
log), suggesting the SDK's async cleanup is failing when the stream is abruptly closed.

### Issue 2 — `ValueError: 'partial' is not a valid CriterionStatus` (GuardKit Bug)

The autobuild orchestrator crashes hard on TASK-C086 Turn 1 Coach validation:

```
ValueError: 'partial' is not a valid CriterionStatus
  File "guardkit/orchestrator/autobuild.py", line 3083, in _display_criteria_progress
    promises = [CompletionPromise.from_dict(p) for p in promises_data]
  File "guardkit/orchestrator/schemas.py", line 149, in from_dict
    status=CriterionStatus(data.get("status", "incomplete")),
```

`CriterionStatus` enum does not include a `"partial"` value, but the Coach (or synthetic report
generator) is producing promise objects with `status: "partial"`. This is a hard crash that
stops the feature build immediately — it does not fall through to recovery.

**This is a GuardKit code bug independent of the vLLM backend.**

### Issue 3 — `python` not found in PATH (Environment)

```
WARNING: pytest not found, trying python -m pytest
ERROR: Failed to run tests: [Errno 2] No such file or directory: 'python'
```

The test detection code calls `python` (not `python3`) which is absent on the GB10. Tests
therefore cannot be detected or run. This results in `0 tests, failed` being reported for
TASK-70ED Turn 1 even though the scaffold task genuinely has no tests.

### Issue 4 — `task_work_results.json` not written after SDK error (Consequence of Issue 1)

Because the Player SDK process terminates with an error, it never writes
`.guardkit/autobuild/TASK-XXX/task_work_results.json`. The Coach validator then warns:

```
WARNING: task_work_results.json not found for TASK-XXX
```

This causes the Coach to fall back to text-matching on a synthetic report, which cannot reliably
verify acceptance criteria — leading to false-positive approvals (TASK-70ED was approved with
0/8 criteria verified on turn 1, then 8/8 on turn 2 from a synthetic report alone).

### Issue 5 — Graphiti not available

```
INFO: Graphiti factory not available or disabled, disabling context loading
⚠ Graphiti not available — context loading disabled for this run
```

Graphiti knowledge context is disabled. This is informational but means the autobuild runs
without prior knowledge context loaded.

## Root Cause Hypothesis

The primary root cause is **the vLLM model truncating the response stream mid-generation**,
manifesting as `SDK agent error: unknown`. The inline `task-work` protocol is ~19 KB and the
Player is asked to use up to 50 turns, which may result in very long context windows that exceed
the local model's context limit or a vLLM server-side generation cap.

The secondary root cause is **a GuardKit enum bug** where `CriterionStatus` does not handle
`"partial"` as a valid status value, causing a hard crash instead of graceful degradation.

## Acceptance Criteria

- [ ] Identify what vLLM configuration or context-length limit is causing `SDK agent error: unknown`
- [ ] Confirm whether the `unknown` SDK error maps to a specific HTTP error from the vLLM server (context overflow, timeout, etc.)
- [ ] Identify the source of `"partial"` status values in CompletionPromise / CriterionStatus (Coach output or synthetic report generator)
- [ ] Propose fix for `CriterionStatus` enum to handle `"partial"` without crashing (add value or sanitise on deserialisation)
- [ ] Confirm whether `python` vs `python3` test detection affects real test runs or only the detection fallback path
- [ ] Assess whether state recovery via synthetic report produces false positives (TASK-70ED approved with 0 real tests)
- [ ] Recommend configuration changes for running autobuild against a local vLLM endpoint

## Investigation Areas

1. `guardkit/orchestrator/schemas.py:149` — `CriterionStatus` enum definition
2. `guardkit/orchestrator/autobuild.py:3083` — `_display_criteria_progress` deserialisation
3. `guardkit/orchestrator/synthetic_report.py` — what `status` values it can produce
4. `guardkit/orchestrator/coach_verification.py` — `python` vs `python3` command selection
5. `guardkit/orchestrator/agent_invoker.py` — SDK error classification (`unknown`)
6. vLLM server logs on GB10 (if accessible) for corresponding errors at the 270–480 s mark

## Related Tasks

- `TASK-REV-AB3D` — review-vllm-model-name-mismatch-autobuild (related vLLM issue)

## Next Steps

When ready: `/task-review TASK-REV-GB10 --mode=debugging --depth=deep`
