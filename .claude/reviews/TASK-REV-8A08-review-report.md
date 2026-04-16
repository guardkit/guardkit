# Review Report: TASK-REV-8A08

## Executive Summary

The FEAT-486D AutoBuild stall was caused by a **partial/intermittent API outage** — not a complete outage and not a GuardKit bug. The upstream API was flapping: it served Turn 1 for 8 minutes before dropping the stream, then intermittently accepted lighter calls (Coach Turn 2 succeeded at 24.4s) while rejecting heavier Player invocations. This partial availability exposed two GuardKit weaknesses: (1) the stall detector cannot distinguish infrastructure failures from implementation failures, and (2) the Coach can succeed on synthetic reports while the Player remains blocked, creating a feedback loop that wastes turns.

## Review Details

- **Mode**: Decision Analysis (root cause + recommendations)
- **Depth**: Standard (revised for partial outage analysis)
- **Reviewer**: Manual analysis of failure log + GuardKit source

## Timeline Reconstruction

| Time (UTC) | Event | API Status |
|------------|-------|------------|
| 15:00:31 | Wave 1 starts (TASK-AD-001, direct mode) | Healthy |
| 15:07:48 | Wave 1 completes - SUCCESS (1 turn, 434s) | Healthy |
| 15:08:02 | Wave 2 starts (4 parallel tasks) | Healthy |
| 15:08:02 | **ConnectionResetError(54)** during vLLM embedding call | Embedding degraded |
| 15:08-15:23 | All 4 Wave 2 tasks succeed (1-2 turns each) | Healthy for SDK |
| 15:23:05 | Wave 3 starts (TASK-AD-004, task-work mode, complexity 6) | Healthy |
| 15:23-15:31 | Turn 1 Player runs 8 min: 1 Write + 7 Edit tool blocks | Degrading |
| 15:31:05 | Turn 1 at 480s: **SDK stream error "unknown"** | **Failing** |
| 15:31:35 | Turn 1 retry also fails → Cancelled via cancel scope | Failing |
| 15:32:00 | Turn 1 **Coach SDK FAILED** (8.4s, "unknown") | Failing |
| 15:32:10 | Turn 2 Player fails in **8 seconds** | Failing |
| 15:32:42 | Turn 2 **Coach SDK SUCCEEDED** (24.4s, with pre-flight warning) | **Partially up** |
| 15:33:07 | Turn 3 Player fails in **14 seconds** | Failing |
| 15:33:45 | Turn 3 Coach SDK FAILED (7.9s) | Failing |
| 15:33:53 | Turn 4 Player fails in **42 seconds** | Failing |
| 15:34:59 | Turn 4 Coach SDK FAILED (8.3s) | Failing |
| 15:35:07 | Turn 5 Player fails in **24 seconds** | Failing |
| 15:35:55 | Turn 5 Coach SDK FAILED (8.3s) | Failing |
| 15:35:55 | Stall detected: 3 identical feedback sigs, 0 criteria | |
| 15:36:03 | UNRECOVERABLE_STALL declared | |

## Findings

### Finding 1: Root Cause — Partial/Intermittent API Outage (REVISED)

**Evidence for partial (not complete) outage**:

| Turn | Player SDK | Coach SDK | Interpretation |
|------|-----------|-----------|----------------|
| T1 | Ran 8 min, failed at 480s | FAILED (8.4s) | Stream dropped mid-conversation |
| T2 | Failed in 8s | **SUCCEEDED** (24.4s, pre-flight slow) | API up for light calls, down for heavy |
| T3 | Failed in 14s | FAILED (7.9s) | Back down |
| T4 | Failed in 42s | FAILED (8.3s) | Down (Player lasted longer = partial retry?) |
| T5 | Failed in 24s | FAILED (8.3s) | Down |

**Key insight**: Turn 2's Coach SDK call succeeded in 24.4s (with a `[BashTool] Pre-flight check is taking longer than expected` warning). This proves the API was not completely down — it was flapping. Lighter requests (Coach running `pytest` via SDK) could get through intermittently, while heavier requests (Player task-work invocations with large prompts and multi-turn tool use) failed consistently.

**Revised conclusion**: This was a **partial API outage** — degraded service that could handle some requests but not sustained streaming sessions. The inconsistency between Player (always fails) and Coach (sometimes succeeds) made it harder for GuardKit to classify the situation.

### Finding 2: Asymmetric Player/Coach Failure Hid the Infrastructure Issue

**Evidence**:
- Turn 1 Coach: FAILED → feedback = "SDK API error: unknown"
- Turn 2 Coach: **SUCCEEDED** → feedback = "Not all acceptance criteria met" (different message!)
- Turns 3-5 Coach: FAILED → feedback = "SDK API error: unknown"

**Impact**: Because Turn 2's Coach succeeded, it produced a *different* feedback signature from the other turns. The stall detector uses identical feedback hashing to detect stalls. The signature sequence was:

| Turn | Feedback Signature | Content |
|------|-------------------|---------|
| T1 | sig-A | "SDK API error: unknown" |
| T2 | sig-B (different!) | "Not all acceptance criteria met..." |
| T3 | sig-C (= sig-A) | "SDK API error: unknown" |
| T4 | sig-C | "SDK API error: unknown" |
| T5 | sig-C | "SDK API error: unknown" — **3rd repeat → stall triggered** |

The stall detector requires 3 identical consecutive signatures. Turn 2's successful (but different) Coach feedback **reset the counter**, delaying stall detection by one turn. In a complete outage all 5 signatures would match and detection would trigger at Turn 3 instead of Turn 5.

**Assessment**: The partial outage created a **feedback signature oscillation** that delayed stall detection. This is a design gap — the stall detector should also recognise "SDK error + non-SDK error + SDK error" as a pattern worth short-circuiting on.

### Finding 3: Turn 2 Coach Success Created a False Progress Signal

**Evidence**:
- Turn 2 Coach SDK succeeded, so it ran its full validation pipeline
- But it was validating a **synthetic report** (because the Player had failed)
- The synthetic report had no `completion_promises`, so all 10 criteria were marked unmet
- Coach feedback: "Not all acceptance criteria met: [10 criteria listed]"
- This is technically correct feedback but completely unhelpful — the criteria weren't met because the Player never ran, not because of bad implementation

**Impact**: GuardKit treated Turn 2 as a "normal feedback turn" rather than an infrastructure failure. The Coach produced actionable-looking feedback that made the situation appear like an implementation problem rather than an API problem.

**Assessment**: When the Player fails with an SDK error and the Coach subsequently succeeds on a synthetic report, the Coach's criteria feedback is meaningless noise. GuardKit should flag this scenario explicitly.

### Finding 4: Wave 2 ConnectionResetError — Possibly Related

**Evidence**:
- At 15:08:02, `ConnectionResetError(54, 'Connection reset by peer')` during embedding calls to `promaxgb10-41b1:8001`
- The embedding server and Claude API are both served from the same physical machine (`promaxgb10-41b1`)
- The ConnectionReset occurred at the exact moment Wave 2 started its 4 parallel tasks

**Revised assessment**: **Possibly related**. While the embedding server (port 8001) and Claude API (likely different port) are different services, they share the same host. Network instability or resource contention on `promaxgb10-41b1` could affect both. The 4 parallel Wave 2 tasks may have contributed to resource pressure on the server, leading to the degradation that fully manifested during Wave 3.

### Finding 5: task-work Mode Amplified the Impact (Revised)

**Evidence (revised)**:
- task-work mode sends larger prompts (19,660 bytes inline protocol) vs direct mode
- task-work mode uses `max_turns: 100` (heavier session) vs direct mode
- In a partial outage where lighter calls succeed but heavier ones fail, task-work's larger request size would be the first to be rejected

**Revised assessment**: **Contributing factor in a partial outage**. While task-work mode didn't *cause* the outage, its heavier payload made it more susceptible to partial degradation. If TASK-AD-004 had used `direct` mode (like Waves 1-2), it might have succeeded during the intermittent windows — though this is speculative.

### Finding 6: Stall Detection Effective But Slow for Infrastructure Failures

**Evidence**:
- Stall detector correctly identified the pattern and halted execution
- But it required 5 turns / ~13 minutes because:
  1. Turn 2's different Coach feedback broke the consecutive signature streak
  2. The detector only counts identical feedback, not "SDK error pattern" generically
  3. No distinction between "Player can't run code" vs "Player ran bad code"

**Assessment**: The stall detector works well for its designed purpose (implementation stalls). For infrastructure failures, a separate detection mechanism is needed — one that tracks SDK-level errors regardless of Coach feedback content.

### Finding 7: SDK "unknown" Error Remains Opaque

**Evidence**:
- Error surfaces as `"unknown"` consistently — no HTTP status, no error code, no connection details
- The `check_assistant_message_error()` function in `agent_invoker.py` extracts the error string from `AssistantMessage.content`, but the upstream SDK provides no structured error information
- Turn 4 Player lasted 42s (vs 8-24s for other turns) — suggesting the API was sometimes partially responsive, but the error is always the same `"unknown"` regardless of failure mode

**Assessment**: The SDK error classification is a significant gap. Even distinguishing "connection refused" vs "stream interrupted mid-response" vs "HTTP 500" would enable smarter retry and detection strategies.

## Recommendations

### R1: Add SDK Error Type Tracking to Adversarial Loop (High Impact, Medium Effort)

Track a new counter `consecutive_player_sdk_errors` in the adversarial loop. When the Player fails with an SDK-level error (not a code/test failure), increment the counter. When it succeeds or fails for non-SDK reasons, reset it.

**Short-circuit rule**: If `consecutive_player_sdk_errors >= 2`, exit immediately with a new `sdk_infrastructure_failure` decision type, regardless of Coach results.

**Why 2 not 3**: Unlike the feedback stall detector (which waits for 3 identical signatures because implementation feedback can legitimately repeat), SDK errors at the transport layer indicate a systemic problem. Two consecutive SDK failures without any successful Player execution is a strong signal.

**Implementation**: In `autobuild.py` around line 1990, before the existing feedback stall check:

```python
# Track SDK-level Player failures (infrastructure detection)
if turn_record.player_result and turn_record.player_result.get("sdk_error"):
    consecutive_sdk_errors += 1
    if consecutive_sdk_errors >= 2:
        logger.error(f"Infrastructure failure for {task_id}: "
                     f"{consecutive_sdk_errors} consecutive SDK errors")
        return turn_history, "sdk_infrastructure_failure"
else:
    consecutive_sdk_errors = 0
```

### R2: Skip Coach When Player Failed with SDK Error (High Impact, Low Effort)

When the Player fails with an SDK-level error, skip Coach validation entirely. Evidence from this incident shows the Coach either:
- Also fails with "unknown" (wasting ~8s per turn), OR
- Succeeds on a synthetic report and produces misleading "criteria not met" feedback

Neither outcome adds value. Skipping Coach saves time and prevents the feedback signature oscillation that delayed stall detection.

**Implementation**: In `autobuild.py`, after Player failure detection:

```python
if player_result.error_type == "sdk_error":
    logger.info(f"Skipping Coach validation — Player failed at SDK level")
    turn_record.decision = "feedback"
    turn_record.feedback = f"SDK infrastructure error: {player_result.error}"
    # Don't invoke Coach at all
```

### R3: Add API Health Check Between Waves (Medium Impact, Low Effort)

Before starting each wave, execute a lightweight SDK probe (minimal prompt, single-turn). If the probe fails after 2 retries with exponential backoff (30s, 60s), halt the feature build with `api_health_check_failed`.

This would have caught the issue before Wave 3 burned 5 turns — or at least before subsequent waves in future incidents.

**Implementation**: Add `_check_api_health()` to `FeatureOrchestrator`, called between waves.

### R4: Improve Error Extraction from SDK (Medium Impact, Medium Effort)

Investigate the `AssistantMessage` error format in the Claude Agent SDK to extract more structured error information. Even partial improvements would help:

| Current | Desired |
|---------|---------|
| `"unknown"` | `"stream_interrupted"` / `"connection_refused"` / `"http_500"` / `"timeout"` |

Check: `claude_agent_sdk._internal.transport` for where the "unknown" string originates. The SSE transport likely has access to the HTTP response status before it surfaces as "unknown".

### R5: Detect Feedback Signature Oscillation (Low Impact, Medium Effort)

Enhance the stall detector to recognise oscillating patterns, not just consecutive identical signatures. In this incident, the pattern was:

```
SDK_ERROR → CRITERIA_NOT_MET → SDK_ERROR → SDK_ERROR → SDK_ERROR
```

A "majority SDK error" heuristic (e.g., 3+ of last 4 signatures are SDK errors) would catch this pattern one turn earlier.

### R6: Resume Assessment (Unchanged)

FEAT-486D is safely resumable with `--resume` once API health is verified. Turn 1 wrote partial code (5 files, +208/-142) with failing tests. The Player will detect this on resume via state recovery.

## Decision Matrix

| Option | Impact | Effort | Risk | Recommendation |
|--------|--------|--------|------|----------------|
| R1: SDK error counter + short-circuit | High | Medium | Low | **Implement** |
| R2: Skip Coach on SDK Player failure | High | Low | Low | **Implement** |
| R3: API health check between waves | Medium | Low | Low | **Implement** |
| R4: Improve SDK error extraction | Medium | Medium | Low | **Implement** |
| R5: Feedback oscillation detection | Low | Medium | Low | Consider |
| R6: Resume FEAT-486D | N/A | Low | Low | **Do it** |

## Revised Answers to Acceptance Criteria

| Criterion | Answer |
|-----------|--------|
| Root cause identified | **Partial/intermittent API outage** — degraded service, not complete downtime |
| "unknown" SDK error mapping | No structured error codes available; transport-level detail lost |
| Wave 2 parallel execution → rate limiting? | **Possibly contributing** — 4 parallel tasks on same host may have contributed to resource pressure |
| TASK-AD-004 complexity/mode contribution? | **Indirect** — task-work mode's heavier payload more susceptible to partial degradation |
| ConnectionResetError early warning? | **Possibly related** — same host (`promaxgb10-41b1`), occurred at start of parallel execution |
| GuardKit improvements needed? | **Yes** — R1-R4: SDK error tracking, Coach skip, health checks, error extraction |
| FEAT-486D resumable? | **Yes** — safe with `--resume` after verifying API health |
| Findings documented | This report (revised) |

## Appendix

### Key Evidence: Partial vs Complete Outage

The single strongest evidence for "partial outage" is Turn 2's Coach result:

```
Line 1122: SDK independent tests passed in 24.4s
Line 1121: [BashTool] Pre-flight check is taking longer than expected
```

The API accepted a lighter Coach SDK invocation (running `pytest` with ~5 tool turns) while rejecting the heavier Player SDK invocation (task-work with 100 max turns and 19KB prompt). The pre-flight warning indicates the API was responsive but degraded.

### Error Chain (Revised)

```
Partial API degradation on promaxgb10-41b1
  │
  ├── Player SDK (heavy: task-work, 19KB prompt, max_turns=100)
  │     → SSE stream interrupted ("unknown")
  │     → retry → also fails
  │     → Cancelled via cancel scope
  │     → state_recovery captures partial git state
  │     → synthetic report generated
  │
  └── Coach SDK (light: pytest, single Bash command)
        ├── Turn 1: FAILED ("unknown") → feedback = "SDK API error"
        ├── Turn 2: SUCCEEDED (24.4s, slow) → feedback = "criteria not met" ← DIFFERENT SIGNATURE
        ├── Turn 3: FAILED ("unknown") → feedback = "SDK API error"
        ├── Turn 4: FAILED ("unknown") → feedback = "SDK API error"
        └── Turn 5: FAILED ("unknown") → feedback = "SDK API error" ← 3rd repeat → STALL
```

### Key Files Analysed

- Failure log: `specialist-agent/docs/reviews/FEAT-486D-stall.md` (1469 lines)
- Review summary: `specialist-agent/.guardkit/autobuild/FEAT-486D/review-summary.md`
- SDK retry logic: `guardkit/orchestrator/agent_invoker.py:4595-4650`
- Stall detection: `guardkit/orchestrator/autobuild.py:1984-2002`
- Coach validator: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Retry constants: `guardkit/orchestrator/agent_invoker.py:204-209` (`MAX_SDK_STREAM_RETRIES=1`)
