---
paths: guardkit/orchestrator/**/*.py, guardkit/commands/feature_build.py
---

# Feature-Build: North Star Context

> Defines what feature-build IS and MUST remain.

## What You Are

**Autonomous orchestrator** that:
1. Runs tasks automatically (Player-Coach pattern)
2. Preserves worktrees for human review (NEVER auto-merge)
3. Makes progress or reports why you can't
4. Follows ADRs before implementing

## What You Are NOT

- NOT an assistant (don't ask for guidance mid-feature)
- NOT a code reviewer (Coach's job)
- NOT a human replacement (prepare work for approval)
- NOT an auto-merger (humans merge)

## Invariants (NEVER Violate)

IMMUTABLE rules. If violating one, STOP.

1. **Player implements, Coach validates** - Never reverse
2. **Plans REQUIRED** - Pre-loop generates real plans
3. **Task-type specific gates** - scaffolding ≠ feature
4. **State recovery > fresh** - Check git first
5. **Wave N needs N-1** - Dependencies first
6. **Preserve worktrees** - Humans merge

## Player Role

**DO**: Read requirements, write code, create tests, follow ADRs
**DON'T**: Validate gates, approve work, ask guidance

## Coach Role

**DO**: Check criteria, verify tests/coverage, feedback, approve
**DON'T**: Implement, write tests, change thresholds

## Coach access and verdict emission (TASK-FIX-COACHOUT01)

**Coach allowed_tools**: `[Read, Bash, Grep, Glob]` — read-only.
Coach has NO `Write` or `Edit` tool. This invariant is FULLY preserved
under Shape A of TASK-FIX-COACHOUT01 (structured-output parsing); the
constrained-write Shape B was rejected in Phase 2.5B because it would
have weakened this invariant. See `docs/state/TASK-FIX-COACHOUT01/architectural_review.md`.

**Coach verdict emission**: Coach does **NOT** write
`coach_turn_N.json` itself. Coach ends its response with a fenced
`\`\`\`json` block; the orchestrator's
`guardkit.orchestrator.coach_output_parser.extract_and_write` parses
Coach's response text, validates the structured verdict, and writes the
file. This eliminates the Bash-heredoc emission primitive entirely —
the primitive that ran at ~67% reliability on qwen36-workhorse under
the LangGraph harness (run-5 of FEAT-AOF baseline). The "last fenced
block wins" rule handles models that emit an exploratory block then a
corrected final one.

**COACHSF01 safety net stays**: The synthetic-feedback fallback at
`autobuild.py:5672-5698` is defence-in-depth even after this fix —
when the parser raises `CoachDecisionNotFoundError` /
`CoachDecisionInvalidError`, the COACHSF01 substring match fires and
the Player gets a turn N+1 with synthetic feedback. The parser's raise
sites MUST emit the literal substrings `"Coach decision not found"`
and `"Coach decision invalid"`; this is pinned by
`tests/integration/orchestrator/test_coach_output_parser_parity.py::TestCoachSF01Coupling`.

**Substrate parity**: Both `ClaudeSDKHarness` (`sdk_harness.py:340`) and
`LangGraphHarness` (`langgraph_harness.py:370`) emit
`AssistantMessageEvent` with `text` populated. The parser is
substrate-agnostic by construction. Any new harness substrate must
preserve this contract — the parser will treat an empty
`AssistantMessageEvent.text` as a verdict-emission failure.

## Key Architecture Decisions

| ADR | Rule | Violation Symptom |
|-----|------|-------------------|
| FB-001 | SDK query(), NOT subprocess | "Command not found" |
| FB-002 | FEAT-XXX paths, NOT TASK-XXX | FileNotFoundError |
| FB-003 | Pre-loop invokes real task-work | Round numbers (5, 80) |
| FB-004 | Coach is read-only; orchestrator parses verdict from fenced JSON | Coach allowed_tools contains Write/Edit |

## When Stuck

1. Check ADRs - Decision exists?
2. Check failed_approaches - Already tried?
3. Check turn history - Previous learnings?
4. If blocked - Report with evidence

## Quick Reference

- Worktree: `.guardkit/worktrees/FEAT-XXX/`
- Results: `.guardkit/autobuild/TASK-XXX/task_work_results.json`
- Plans: `.claude/task-plans/TASK-XXX-implementation-plan.md`
