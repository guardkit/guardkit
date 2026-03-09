# Implementation Guide: Run 3 Review Fixes (FEAT-RFX)

**Parent Review**: TASK-REV-A8C6
**Feature ID**: FEAT-RFX
**Total Tasks**: 9
**Total Complexity**: 36 points

## Problem Statement

AutoBuild Run 3 for youtube-transcript-mcp FEAT-2AAA succeeded (5/5 tasks, 27m 51s) but exposed four systemic issues:

1. **CancelledError** affects 40% of direct-mode Player invocations due to async generator GC finalization mismatch in claude_agent_sdk
2. **Cross-turn Graphiti learning** is 100% non-functional -- `add_episode` LLM pipeline exceeds the 30s timeout on every turn
3. **Coach criteria gap** -- failed command_execution criteria are silently invisible to the Coach (success injected, failures only logged)
4. **Stale task tracking** -- CRV task completion status is inconsistent between backlog copies and completed directory

## Wave Breakdown

### Wave 1: Housekeeping (3 tasks, 4 complexity points)

Quick wins with no code dependencies. All can run in parallel.

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-RFX-5E37 | Clean up stale CRV task files and update README | 1 | direct | none |
| TASK-RFX-BAD9 | Normalize pip to sys.executable -m pip | 2 | direct | none |
| TASK-RFX-C9D9 | Deprioritise TASK-CRV-B275 and TASK-CRV-7DBC | 1 | direct | none |

**Execution**: All 3 tasks are independent. Execute in parallel using Conductor workspaces or sequentially in a single session.

**Key files touched**:
- `tasks/backlog/coach-runtime-verification/` (5E37, C9D9)
- `guardkit/orchestrator/autobuild.py` ~line 2878 (BAD9)

---

### Wave 2: Critical Reliability Fixes (2 tasks, 10 complexity points)

Address the two highest-impact issues: CancelledError and non-functional cross-turn learning.

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-RFX-8332 | Fix CancelledError via explicit generator close | 5 | task-work | none |
| TASK-RFX-5FED | Replace Graphiti turn state capture with local file-based | 5 | task-work | none |

**Execution**: Both tasks are independent (different subsystems). Execute in parallel.

**Key files touched**:
- `guardkit/orchestrator/agent_invoker.py` ~lines 2008, 4426 (8332)
- `guardkit/orchestrator/autobuild.py` ~line 3517 (5FED)
- `guardkit/knowledge/autobuild_context_loader.py` (5FED)
- `guardkit/orchestrator/state_tracker.py` (5FED)

**Risk notes**:
- TASK-RFX-8332: Test with both direct-mode and task-work delegation to verify no regressions
- TASK-RFX-5FED: Maintain Graphiti fallback for backward compatibility

---

### Wave 3: Coach Criteria Soft Gate (2 tasks, 9 complexity points)

Build structured command execution results and failure classification. These are sequential -- Phase 1 provides the data structures Phase 2 needs.

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-RFX-528E | Coach criteria soft gate Phase 1: structured results | 3 | task-work | TASK-RFX-BAD9 |
| TASK-RFX-F7F5 | Coach criteria soft gate Phase 2: failure classifier + advisory | 6 | task-work | TASK-RFX-528E |

**Execution**: Sequential. 528E must complete before F7F5 starts.

**Key files touched**:
- `guardkit/orchestrator/autobuild.py` `_execute_command_criteria()` (528E)
- `guardkit/orchestrator/quality_gates/coach_validator.py` (F7F5)
- New: `guardkit/orchestrator/quality_gates/failure_classifier.py` (F7F5)

**Design decision**: Soft Gate (Option B) -- failure classifier + advisory injection without changing Coach approve/reject threshold. Coach still decides based on file_content criteria only; command execution failures are advisory context appended to feedback.

---

### Wave 4: Architectural Improvements (2 tasks, 13 complexity points)

Long-term architectural refactors. Each depends on earlier waves.

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-RFX-7C63 | Extended CoachValidator with runtime verification | 6 | task-work | TASK-RFX-F7F5 |
| TASK-RFX-B20B | SDK sessions for Player resumption after CancelledError | 7 | task-work | TASK-RFX-8332 |

**Execution**: Both tasks are independent of each other. Execute in parallel after their respective dependencies complete.

**Key files touched**:
- `guardkit/orchestrator/quality_gates/coach_validator.py` (7C63)
- `guardkit/orchestrator/autobuild.py` `_execute_command_criteria()` (7C63)
- `guardkit/orchestrator/agent_invoker.py` (B20B)

**Risk notes**:
- TASK-RFX-7C63: Backward compatibility required -- existing quality gate profiles must continue to work
- TASK-RFX-B20B: Complexity 7 triggers Phase 2.8 human checkpoint. Requires SDK session management understanding.

## Dependency Graph

```
Wave 1 (parallel):
  TASK-RFX-5E37 ─────────────────────────────────────────────┐
  TASK-RFX-C9D9 ─────────────────────────────────────────────┤ (no downstream deps)
  TASK-RFX-BAD9 ──────────────────────┐                      │
                                      │                      │
Wave 2 (parallel):                    │                      │
  TASK-RFX-8332 ──────────────────────┼──────────────────────┤
  TASK-RFX-5FED ──────────────────────┼──────────────────────┤ (no downstream deps)
                                      │                      │
Wave 3 (sequential):                  │                      │
  TASK-RFX-528E (depends on BAD9) ────┘                      │
       │                                                     │
  TASK-RFX-F7F5 (depends on 528E)                            │
       │                                                     │
Wave 4 (parallel):                                           │
  TASK-RFX-7C63 (depends on F7F5) ───────────────────────────┘
  TASK-RFX-B20B (depends on 8332) ───────────────────────────┘
```

## Conductor Workspace Names

For parallel execution using Conductor:

| Wave | Workspace Name | Task |
|------|---------------|------|
| 1 | `rfx-wave1-cleanup` | TASK-RFX-5E37 |
| 1 | `rfx-wave1-pip` | TASK-RFX-BAD9 |
| 1 | `rfx-wave1-deprioritise` | TASK-RFX-C9D9 |
| 2 | `rfx-wave2-cancelled-error` | TASK-RFX-8332 |
| 2 | `rfx-wave2-turn-state` | TASK-RFX-5FED |
| 3 | `rfx-wave3-structured-results` | TASK-RFX-528E |
| 3 | `rfx-wave3-failure-classifier` | TASK-RFX-F7F5 |
| 4 | `rfx-wave4-coach-validator` | TASK-RFX-7C63 |
| 4 | `rfx-wave4-sdk-sessions` | TASK-RFX-B20B |

## Execution Strategy

1. **Start with Wave 1** -- all 3 tasks can run in a single session or 3 parallel Conductor workspaces. Expected: <30 minutes.
2. **Wave 2 in parallel** -- CancelledError fix and turn state capture are independent. Use 2 Conductor workspaces. Expected: 2-4 hours each.
3. **Wave 3 sequentially** -- 528E first (structured results), then F7F5 (failure classifier). Cannot parallelize due to data structure dependency. Expected: 2-3 hours for 528E, 4-6 hours for F7F5.
4. **Wave 4 in parallel** -- once F7F5 and 8332 are done respectively. Use 2 Conductor workspaces. Expected: 4-6 hours for 7C63, 6-8 hours for B20B.

## Verification

After all waves complete, run a fresh autobuild of FEAT-2AAA to verify:
- Zero CancelledErrors (or graceful recovery)
- Cross-turn context loading from local files
- Command execution results visible in Coach decision JSON
- No regressions in embedding dimension handling
