---
id: TASK-REV-FB26
title: Diagnose independent test verification failure loop in feature-build
status: completed
created: 2026-01-23T10:30:00Z
updated: 2026-01-23T11:35:00Z
completed: 2026-01-23T11:35:00Z
priority: high
task_type: review
tags: [feature-build, autobuild, coach-validator, independent-tests, debugging]
complexity: 6
review_mode: decision
review_depth: standard
review_results:
  mode: decision
  depth: standard
  findings_count: 3
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-FB26-review-report.md
  completed_at: 2026-01-23T11:15:00Z
implementation_tasks_created:
  - TASK-FIX-INDFB
  - TASK-FIX-FBMSG
  - TASK-FIX-TESTS
---

# Task: Diagnose independent test verification failure loop in feature-build

## Description

Feature build is failing on FEAT-A96D (FastAPI App with Health Endpoint) with tasks entering a failure loop where the Coach repeatedly reports "Independent test verification failed:" but the Player cannot fix the issue. The log output shows:

**Observed Behavior:**
1. TASK-FHA-001 (scaffolding): SUCCESS (1 turn) - tests_required=False, so no independent test verification
2. TASK-FHA-002 (feature): FAILED after 5 turns - repeated "Independent test verification failed:"
3. TASK-FHA-003 (feature): FAILED after 5 turns - repeated "Independent test verification failed:"

**Key Observations from Logs:**
- Player reports "0 files created, 0 modified, 0 tests (passing)" but Coach still fails it
- Feedback message is truncated: "- Independent test verification failed:" with no details after the colon
- Independent tests run in ~0.2s and fail immediately
- Quality gates report ALL_PASSED=True before independent test verification
- The Player appears unaware of what's actually failing

## Review Context

**Source File:** `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/feature-build/after_TASK-REV-FB25_fixes.md`

**Relevant Code Areas:**
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Independent test verification
- `guardkit/orchestrator/autobuild.py` - Feedback loop handling
- `guardkit/orchestrator/agent_invoker.py` - Player invocation and feedback passing

## Questions to Answer

1. **Why are independent tests failing?**
   - What tests are being run?
   - What's the actual pytest output?
   - Are tests failing because code doesn't exist yet or because of actual bugs?

2. **Why is feedback incomplete?**
   - Why does "Independent test verification failed:" have no details after the colon?
   - Is the test output being captured and passed to the Player?

3. **Why can't the Player fix the issue?**
   - Is the Player receiving the failure information?
   - Is the failure actionable given the information provided?

4. **Is there a test environment issue?**
   - Are tests running in the worktree with correct PYTHONPATH?
   - Are dependencies installed in the worktree?

## Acceptance Criteria

- [ ] Identify root cause of independent test failures
- [ ] Determine why feedback is truncated/incomplete
- [ ] Propose fix for feedback communication
- [ ] Validate fix addresses the failure loop

## Files to Examine

1. `guardkit/orchestrator/quality_gates/coach_validator.py` - Line ~220-280 (independent test logic)
2. `guardkit/orchestrator/autobuild.py` - Feedback handling
3. `.guardkit/autobuild/TASK-FHA-002/coach_turn_*.json` - Coach decision files
4. `.guardkit/autobuild/TASK-FHA-002/player_turn_*.json` - Player reports

## Related Tasks

- TASK-REV-FB25: Previous review that led to this testing
- TASK-FIX-INDTEST: Independent test skip for scaffolding
- TASK-FIX-SCAF: Scaffolding quality gate profile

## Review Output

Review findings should identify:
1. The root cause of the failure loop
2. Whether this is a code bug, configuration issue, or design gap
3. Specific fix recommendations with code locations
