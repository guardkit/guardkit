---
id: TASK-FIX-COACHSF01
title: Wire synthetic-feedback safety net for "Coach decision not found" verdict-emission failures
status: backlog
task_type: bug
created: 2026-06-05T17:30:00Z
updated: 2026-06-05T17:30:00Z
priority: critical
complexity: 3
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 1.5
blocks:
  - TASK-HMIG-010
falsifier: "After landing, run 5 of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` under GUARDKIT_HARNESS=langgraph: if Coach LLM completes its invocation but does NOT write coach_turn_N.json (qwen36-workhorse F2-at-Coach-level substrate behaviour), `_invoke_coach_primary` MUST emit a synthetic feedback decision (writes coach_turn_N.json with rationale naming the failure mode) and return success=True. The Player gets to retry on turn 2 with Coach's feedback. Regression test exercises invoke_coach returning success=False with `Coach decision not found` error → assert synthetic feedback fires."
tags:
  - autobuild
  - langgraph-migration
  - bugfix
  - coach
  - substrate-mitigation
---

# Task: Wire synthetic-feedback safety net for Coach decision-not-found failures

## Description

Surfaced by TASK-HMIG-010 run 4 (2026-06-05T16:05, see [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md)). Investigation in this session's analysis identified the root cause:

**F17 — qwen36-workhorse Coach can't reliably emit the structured Bash-heredoc verdict.**

Coach's contract:
- Prompt instructs Coach to write a JSON verdict file via Bash heredoc ([`agent_invoker.py:2393-2394`](../../../guardkit/orchestrator/agent_invoker.py))
- Allowed tools: `["Read", "Bash", "Grep", "Glob"]` — no `Write` tool ([`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py))
- Coach must construct a multi-line Bash heredoc with valid JSON to persist its verdict

Under qwen36-workhorse + LangGraph, this multi-step structured emission is unreliable. In run 4, Coach LLM ran for 140s with 12 successful HTTP responses but never emitted the Bash tool call to write `coach_turn_1.json`. This is **canary F2** (model discusses tool calls in prose without emitting actual tool_use blocks) manifesting at Coach level.

The substantive Player work was correct ([`phase_4_summary.json`](../../../.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/phase_4_summary.json) shows 14/14 doc-level exclusion tests passing). Only the verdict-emission failed.

## The orchestrator already has the fix mechanism — it isn't wired for this case

`_invoke_coach_primary` ([`autobuild.py:5508-5675`](../../../guardkit/orchestrator/autobuild.py)) has the right safety net:

```python
except Exception as sdk_error:
    logger.error("Coach invocation failed in primary path: %s. Emitting synthetic feedback decision.", sdk_error, exc_info=True)
    return self._emit_synthetic_coach_feedback(...)
```

But the safety net only fires on raised exceptions. `invoke_coach` catches `CoachDecisionNotFoundError` internally at [`agent_invoker.py:1987-1997`](../../../guardkit/orchestrator/agent_invoker.py):

```python
except (CoachDecisionNotFoundError, CoachDecisionInvalidError) as e:
    return AgentInvocationResult(
        task_id=task_id, turn=turn, agent_type="coach",
        success=False, report={}, error=str(e),
    )
```

So the file-not-found case returns `success=False` instead of propagating an exception. The synthetic-feedback safety net never fires. The orchestrator's downstream consumer sees `coach_decision="error"`, Wave 1 FAILS, AC-008 verdict computation is blocked.

## Acceptance Criteria

- [ ] AC-001: Locate the call site in `_invoke_coach_primary` where `asyncio.run(self._agent_invoker.invoke_coach(...))` returns ([`autobuild.py:5625`](../../../guardkit/orchestrator/autobuild.py)).
- [ ] AC-002: After the return, check `result.success`. If `False` AND `"Coach decision not found"` (or `"Coach decision invalid"`) appears in `result.error`: emit `self._emit_synthetic_coach_feedback(rationale=f"Coach verdict-emission failed: {result.error}. Likely substrate limitation (qwen36-workhorse F2 at Coach level). Player should retry on turn 2 with this feedback.")` and return that result.
- [ ] AC-003: Other `success=False` outcomes (`SDKTimeoutError`, generic `Unexpected error`) continue to return as-is — only the verdict-emission failure converts to synthetic feedback.
- [ ] AC-004: Regression test exercises invoke_coach returning `success=False` with `"Coach decision not found"` error → assert `_invoke_coach_primary` emits synthetic feedback (writes coach_turn_N.json, returns `success=True`).
- [ ] AC-005: Live smoke (HMIG-010 run 5): when Coach fails to write coach_turn_1.json, the orchestrator emits a synthetic feedback verdict instead of hard-failing the turn. Player gets a turn 2 to retry. (Bonus: run 5 may produce an actual approval on turn 2, since qwen36-workhorse sometimes succeeds at simpler verdicts.)

## Implementation Notes

- This is fix-shape (a) from the run-4 investigation. The simpler "let invoke_coach raise" (fix b) was rejected because it would change the invoke_coach contract for other callers (`GUARDKIT_COACH_LEGACY=1`, tests, etc.) — narrower fix is safer.
- The synthetic feedback rationale should specifically name "Coach verdict-emission failed" so future runs can distinguish this failure class from other Coach-side errors. Future telemetry / Graphiti capture can then track F17 recurrence rate as a substrate-quality metric.
- After landing, F17 effectively becomes a soft-fail with a tracked rationale. The substrate-quality finding remains — qwen36-workhorse Coach is unreliable at structured verdict emission — but the orchestrator no longer hard-blocks on it.

## Out of scope (filed separately)

- **F2-at-Coach-level fundamental fix**: would require either Coach prompt simplification (smaller verdict format), Coach output mode change (orchestrator parses text response into JSON), or upgrading the Coach model. Each is a bigger architectural decision. This task only wires the soft-fail safety net; the substrate-quality finding is recorded for AC-008 evidence.
- **Pip-cache ghost-path filter** (F18): the orchestrator's ghost-path filter at [`agent_invoker.py:180`](../../../guardkit/orchestrator/agent_invoker.py) caught 4 known paths in run 4 but didn't filter the 40+ `Library/Caches/pip/http-v2/...` entries that the env bootstrap leaves in git detection. Cosmetic; recorded as I-008 in feature-run-incidents.md.

## References

- Run-4 failure log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-4.md)
- Canary F2: [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) §3.F2
- Coach prompt: [`agent_invoker.py:2384-2415`](../../../guardkit/orchestrator/agent_invoker.py)
- Coach allowed-tools: [`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py)
- Coach safety-net (synthetic feedback): [`autobuild.py:5677-5732`](../../../guardkit/orchestrator/autobuild.py) (`_emit_synthetic_coach_feedback`)
- Blocked task: [TASK-HMIG-010](../../in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)

## Notes

After this lands, the AC-008 falsifier evaluation can proceed:
- Player produces real work (F2 mostly closed for Player per run 3/4 evidence)
- Coach soft-fails on verdict-emission, Player retries with feedback
- Eventually Coach either succeeds (substrate variance) or the orchestrator exhausts retries and produces a clean "feedback after N turns" verdict

Either outcome is a usable AC-008 data point.
