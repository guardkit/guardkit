---
id: TASK-REV-5610
title: Analyse vLLM Qwen3 DB feature autobuild run 2 failure on GB10
status: review_complete
task_type: review
review_mode: decision
review_depth: comprehensive
review_results:
  score: 88
  findings_count: 5
  recommendations_count: 5
  withdrawn_count: 2
  decision: implement
  revision: v2-deep-dive
  report_path: .claude/reviews/TASK-REV-5610-review-report.md
  completed_at: 2026-02-26T22:45:00Z
created: 2026-02-26T14:00:00Z
updated: 2026-02-26T14:00:00Z
priority: high
tags: [autobuild, vllm, qwen3, local-llm, debugging, gb10, run-2]
complexity: 6
decision_required: true
related_tasks: [TASK-REV-8A94]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse vLLM Qwen3 DB feature autobuild run 2 failure on GB10

## Description

Analyse the second attempt at the database feature (FEAT-947C - PostgreSQL Database Integration) autobuild using vLLM with Qwen3 Next Coder on the Dell GB10. This run includes the `--fresh` flag and benefits from the `timeout_multiplier=4.0x` fix, resulting in improved Wave 2 results compared to run 1 (TASK-REV-8A94). However, the run still fails at Wave 3 with new failure modes.

**Goal**: Identify remaining root causes after timeout fix, compare progress vs run 1 and the successful Anthropic run, and determine what further fixes are needed for full vLLM/Qwen3 autobuild success.

## Context

### Environment
- **Hardware**: Dell GB10 (local)
- **LLM Backend**: vLLM serving Qwen3 Next Coder
- **Endpoint**: `ANTHROPIC_BASE_URL=http://localhost:8000`
- **Feature**: FEAT-947C - PostgreSQL Database Integration (8 tasks, 4 waves)
- **Config**: `--max-turns 5`, `--fresh`, `stop_on_failure=True`, `timeout_multiplier=4.0x`
- **Task timeout**: 9600s (160 min) - 4x the base
- **SDK timeout**: 10800s (3h) - with 4.0x multiplier

### Failing Output
- Primary: `docs/reviews/gb10_local_autobuild/db_feature_2.md`

### Reference
- Run 1 analysis: `tasks/backlog/TASK-REV-8A94-analyse-vllm-qwen3-db-autobuild-failure.md`
- Successful Anthropic run: `docs/reviews/autobuild-fixes/db_finally_succeds.md`
- Fix history: `docs/reviews/autobuild-fixes/`

## Observed Results - Significant Improvement Over Run 1

### Wave 1: TASK-DB-001 - SUCCESS (2 turns)
- Turn 1: 8/10 criteria verified (80%) - Coach feedback on 2 incomplete
- Turn 2: 10/10 criteria verified (100%) - Coach approved
- Duration: ~1860s (31 min) across both turns
- **Note**: Needed 2 turns (run 1 succeeded in 1 turn for same task)

### Wave 2: ALL 3 TASKS PASSED (major improvement over run 1!)
- **TASK-DB-002**: SUCCESS, 1 turn, approved
- **TASK-DB-003**: SUCCESS, 1 turn, approved
- **TASK-DB-004**: SUCCESS, 1 turn, approved
- **Run 1 comparison**: Wave 2 had 2 failures (DB-002, DB-004 both TIMEOUT)

### Wave 3: FAILED (3 parallel tasks: DB-005, DB-006, DB-008)
This is where the new failure modes emerge:

#### TASK-DB-005 (Create initial migration)
- `WARNING: Task file not found for TASK-DB-005` on BOTH turns 1 and 2
- Routed to `direct Player path` (not task-work delegation)
- Lower complexity (2) with lower timeout (5760s)
- **Root cause**: Task file search failure - task was moved to `design_approved/` but direct path couldn't locate it

#### TASK-DB-006 (Implement CRUD operations) - PRIMARY FAILURE
- **Turn 1**: `SDK API error in stream: unknown` at ~5430s elapsed
  - State recovery attempted: 4 files changed detected
  - Coach validation 0/11 criteria verified
  - Coach gave feedback (rejection)
- **Turn 2**: Ran for 9210+ seconds (2h 33min), SDK completed with 93 turns
  - 8 files created, 39 modified, 1 test passing
  - Then CANCELLED (feature-level cancellation detected between Player and Coach)
- Total: 248 messages, 154 assistant, 92 tools in turn 2 alone

#### TASK-DB-008 (Integrate database health check)
- Running in parallel, likely also stalled/affected by the wave cancellation

## Key Failure Modes (New vs Run 1)

### 1. SDK API Error: Unknown (NEW)
- TASK-DB-006 turn 1: `ERROR:guardkit.orchestrator.agent_invoker:[TASK-DB-006] SDK API error in stream: unknown`
- This is a vLLM/Qwen3 backend streaming error, not seen in Anthropic runs
- Triggers state recovery path, but then Coach still rejects (0/11 criteria)

### 2. Task File Not Found (NEW)
- TASK-DB-005: `WARNING: Task file not found for TASK-DB-005` on both turns
- The task file was moved from `backlog/` to `design_approved/` by state_bridge
- But the `direct Player path` (used for low-complexity tasks) can't locate it
- This may be a state_bridge/file search bug exposed by Qwen3's different task handling

### 3. Excessive SDK Turns (WORSE than run 1)
- TASK-DB-006 turn 2: 93 SDK turns, 248 messages, 9210+ seconds
- Qwen3 appears to enter a loop or generate excessive tool calls
- Contrast: Anthropic tasks typically complete in 15-30 SDK turns

### 4. Coach Criteria Verification Still 0/11 (PERSISTENT from run 1)
- TASK-DB-006 turn 1: 0/11 criteria verified despite error recovery capturing work
- Same `matching_strategy: text` issue seen in run 1 for different tasks
- Player `requirements_met: []` when Qwen3 encounters errors

### 5. Parallel Wave Resource Contention (POSSIBLE)
- Wave 3 runs 3 tasks in parallel on local vLLM
- Each task making API calls to same local endpoint
- May cause resource exhaustion on GB10 hardware

## Comparison: Run 1 vs Run 2 vs Anthropic

| Metric | Run 1 | Run 2 | Anthropic |
|--------|-------|-------|-----------|
| Config | `--max-turns 5` | `--max-turns 5 --fresh` | `--max-turns 10 --fresh` |
| Timeout multiplier | 1.0x (2400s) | 4.0x (9600s) | N/A (~2400s) |
| Wave 1 | PASS (1 turn) | PASS (2 turns) | PASS (1 turn) |
| Wave 2 | FAIL (1/3 pass) | PASS (3/3 pass) | PASS (3/3 pass) |
| Wave 3 | Not reached | FAIL (SDK errors) | PASS |
| Wave 4 | Not reached | Not reached | PASS |
| Tasks completed | 2/8 | 4/8 | 5/5 |
| Duration | 72m 47s | >160 min | ~60 min |

## Key Questions for Review

1. **What causes the `SDK API error in stream: unknown` for vLLM?**
   - Is this a vLLM timeout, OOM, or stream disconnect?
   - Does it correlate with parallel task load on the GPU?

2. **Why can't direct Player path find TASK-DB-005's task file?**
   - Is the file search not checking `design_approved/` directory?
   - Is this a regression in state_bridge when tasks move between directories?

3. **Why does TASK-DB-006 take 93 SDK turns on turn 2?**
   - Is Qwen3 in a loop? Generating excessive tool calls?
   - Is it re-doing all work from turn 1 instead of incrementally fixing?
   - Should there be an SDK turn budget limit for local models?

4. **Should Wave 3 parallelism be reduced for local vLLM?**
   - 3 parallel tasks all making vLLM requests may exceed GB10 capacity
   - Would sequential or 2-at-a-time execution improve reliability?

5. **What remaining fixes from TASK-REV-8A94 apply here?**
   - Timeout multiplier is working (Wave 2 fixed)
   - Text matching still failing for some tasks
   - What about the semantic matching recommendation?

## Acceptance Criteria

- [ ] Root cause of `SDK API error in stream: unknown` identified
- [ ] Root cause of `Task file not found for TASK-DB-005` identified
- [ ] Analysis of why TASK-DB-006 takes 93 SDK turns (loop detection)
- [ ] Comparison of run 2 improvements vs run 1 documented
- [ ] Recommendations for Wave 3 parallelism on local hardware
- [ ] Assessment of whether Coach text matching still blocks (post-error recovery)
- [ ] Prioritised fix list for next autobuild attempt

## Review Approach

1. **Deep-dive TASK-DB-006 failure**: SDK error → state recovery → Coach rejection → massive retry
2. **Investigate TASK-DB-005 file location bug**: State bridge directory handling
3. **Analyse vLLM streaming error**: Correlate with GPU load/memory during parallel wave
4. **Compare SDK turn counts**: Qwen3 (93 turns) vs Anthropic typical (15-30 turns)
5. **Cross-reference with TASK-REV-8A94 findings**: Which fixes worked, which remain

## Implementation Notes

This review should produce:
- A delta findings report vs TASK-REV-8A94
- Specific fixes for the 3 new failure modes (SDK error, file-not-found, excessive turns)
- Parallelism configuration recommendations for local hardware
- Updated vLLM autobuild playbook

## References

| Resource | Location |
|----------|----------|
| Run 2 Failing Output | `docs/reviews/gb10_local_autobuild/db_feature_2.md` |
| Run 1 Failing Output | `docs/reviews/gb10_local_autobuild/db_feature_1.md` |
| Run 1 Review Task | `tasks/backlog/TASK-REV-8A94-analyse-vllm-qwen3-db-autobuild-failure.md` |
| Successful Anthropic Run | `docs/reviews/autobuild-fixes/db_finally_succeds.md` |
| Coach Validator | `guardkit/orchestrator/quality_gates/coach_validator.py` |
| Agent Invoker | `guardkit/orchestrator/agent_invoker.py` |
| State Bridge | `guardkit/tasks/state_bridge.py` |

## Test Execution Log

[Automatically populated by /task-review]
