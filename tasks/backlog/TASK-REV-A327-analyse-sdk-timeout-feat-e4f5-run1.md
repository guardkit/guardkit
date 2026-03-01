---
id: TASK-REV-A327
title: Analyse SDK timeout error in FEAT-E4F5 run 1
status: review_complete
task_type: review
review_mode: debugging
review_depth: comprehensive
created: 2026-03-01T00:00:00Z
updated: 2026-03-01T00:00:00Z
priority: high
tags: [timeout, autobuild, sdk, debugging, investigation]
complexity: 0
review_results:
  findings_count: 6
  recommendations_count: 7
  root_causes:
    - "BUG #1 (SEAM 1): Missing break after ResultMessage in _invoke_task_work_implement() causes stream hang"
    - "BUG #2 (SEAM 3): State recovery ignores player report test_count, falls back to 0 on CoachVerifier timeout"
    - "BUG #3 (SEAM 2): macOS subprocess cleanup disabled — _kill_child_claude_processes() is Linux-only"
  report_path: .claude/reviews/TASK-REV-A327-review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse SDK timeout error in FEAT-E4F5 run 1

## Description

Analyse the timeout error that occurred during the first AutoBuild feature orchestration run of FEAT-E4F5 (System Architecture & Design Commands). TASK-SAD-002 (Update ArchitectureDecision dataclass) timed out with an SDK timeout after 2340s, causing the entire feature run to fail with stop_on_failure=True, leaving 7/10 tasks unexecuted.

## Source Log

`docs/reviews/system-arch-design-commands/run_1.md`

## Observed Behaviour

### Timeline
- **17:38:40Z** — Wave 1 started: TASK-SAD-001, TASK-SAD-002, TASK-SAD-003 (parallel: 3)
- **18:24:04Z** — TASK-SAD-002 hit SDK timeout after 2340s (39 min)
- **18:25:04Z** — TASK-SAD-002 hit task-level timeout after 2400s (40 min)
- **18:35:24Z** — Wave 1 completed: 2 passed (SAD-001, SAD-003), 1 failed (SAD-002)
- Feature orchestration stopped due to `stop_on_failure=True`

### Key Facts
- **SDK timeout**: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
- **Messages processed before timeout**: 85
- **Last output**: Task appeared to be completing successfully — 66 tests passed, 99.0% coverage, architectural score 95/100, quality gates PASSED
- **State recovery**: Detected 3 files changed, but test detection found 0 tests (failed)
- **Coach verification**: Test execution timed out after 120s
- **TASK-SAD-001**: Succeeded in 1 turn (27 SDK turns, complexity=4)
- **TASK-SAD-003**: Succeeded in 1 turn (34 SDK turns, complexity=5)

### Paradox
TASK-SAD-002 (complexity=3, the simplest task) timed out, while TASK-SAD-001 (complexity=4) and TASK-SAD-003 (complexity=5) completed successfully. The last output from TASK-SAD-002 suggests it had actually completed all work and passed all quality gates before the timeout was triggered.

## Analysis Areas

1. **Root cause**: Why did the lowest-complexity task timeout when higher-complexity tasks succeeded?
2. **Timing analysis**: 85 messages in 2340s — was the agent stuck, slow, or did it complete but not exit cleanly?
3. **SDK timeout formula**: Is `base x mode_multiplier x complexity_multiplier` appropriate? For complexity=3, the timeout was 2340s — but the task may have needed more time despite low complexity rating.
4. **State recovery behaviour**: After timeout, state recovery found 3 files changed but 0 tests — yet the last output claimed 66 tests passed. Why the discrepancy?
5. **Coach verification timeout**: Test execution timed out at 120s during state recovery — is this related?
6. **dotnet restore failure**: The bootstrap had a partial failure (11/12) due to MAUI workload issues. Could this have affected TASK-SAD-002?
7. **Stop-on-failure impact**: The feature run stopped after Wave 1, leaving Waves 2-5 (7 tasks) unexecuted. Should the timeout handling be more nuanced?
8. **Worktree contention**: All 3 Wave 1 tasks shared the same worktree. Could parallel execution on a shared worktree cause contention that slowed TASK-SAD-002?

## Acceptance Criteria

- [ ] Root cause of the TASK-SAD-002 timeout identified
- [ ] Determine if TASK-SAD-002 actually completed work successfully before timeout
- [ ] Assess whether the SDK timeout formula needs adjustment
- [ ] Evaluate if the state recovery correctly captured the task's actual state
- [ ] Recommend configuration changes to prevent this class of timeout
- [ ] Assess impact of shared worktree on parallel task execution

## Recommendations

1. **[P0] Add `break` after ResultMessage in ALL 3 invocation paths** — `agent_invoker.py:3975` (task-work), `:1753` (direct), `:~3050` (player direct). Eliminates stream hang class.
2. **[P0] Fall back to player report test data in state recovery** — `state_tracker.py:376-380`. Both branches yield `test_count=0`; fix to read `player_report.get("test_count", 0)` as fallback.
3. **[P1] Implement macOS subprocess cleanup** — `agent_invoker.py:799-815`. Current `/proc`-based approach is Linux-only. Use `psutil` or tracked PID for cross-platform cleanup.
4. **[P2] Increase coach verification test timeout** from 120s to 300s for state recovery contexts — `coach_verification.py:269`.
5. **[P2] Scope state recovery tests to task-specific files** from player report `tests_written` field.
6. **[P3] Add `task_id` to SDK completion log** — `agent_invoker.py:3975` — eliminates log attribution ambiguity.
7. **No change to timeout formula** — correctly designed, issue was stream lifecycle.

Full report (revised with C4 diagrams): `.claude/reviews/TASK-REV-A327-review-report.md`

## Implementation Notes

_Space for implementation details if review leads to code changes_

## Test Execution Log

_Automatically populated by /task-work_
