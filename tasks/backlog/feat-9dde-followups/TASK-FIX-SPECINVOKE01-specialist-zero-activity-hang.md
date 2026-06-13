---
id: TASK-FIX-SPECINVOKE01
title: Root-cause the deterministic test-orchestrator specialist zero-activity hang under the LangGraph harness
status: backlog
task_type: fix
created: 2026-06-13T12:40:00Z
updated: 2026-06-13T12:40:00Z
priority: medium
complexity: 6
related: [TASK-FIX-SPECHANG, TASK-FIX-SPECVIOL01, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, harness, specialist, test-orchestrator, hang, langgraph]
---

# Task: Root-cause the test-orchestrator specialist zero-activity hang

## Why this task exists

FEAT-9DDE run 3 (2026-06-13) confirmed the specialist-invocation hang is
**deterministic, not intermittent, and independent of the Player model**: the
stronger qwen3-coder-30b Player still saw `run_specialist(test-orchestrator)`
hang on **both** turns of TASK-TSJ-001 with **zero model activity**:

```
[TASK-TSJ-001] test-orchestrator sdk_timeout capped 3299s -> 600s (TASK-FIX-SPECHANG)
[TASK-TSJ-001] specialist:test-orchestrator invocation in progress... (30s..150s elapsed)
run_specialist(test-orchestrator): hang detected (no model activity for 150s)
  — terminating before the 600s duration cap
```

The improved hang detector (terminate at 150s of no activity, vs run-2's 700s+)
works correctly and the build still converged — so this is a **cleanup /
efficiency** item, not a build blocker — but every turn wastes ~150s and injects
a `validation=violation` specialist record. The detector treats the symptom; this
task is to find why the `test-orchestrator` specialist sub-invocation produces
**no model activity at all** under the LangGraph harness (no HTTP request reaches
`:9000`), and fix the invocation path so the specialist actually runs (or is
cleanly skipped when not applicable) instead of hanging.

## Acceptance Criteria

- [ ] Root cause identified: why `run_specialist(test-orchestrator)` issues zero
      LLM calls under `GUARDKIT_HARNESS=langgraph` (e.g. tool/sub-agent wiring,
      model threading into the specialist sub-invocation, or a deadlock before
      the first request).
- [ ] The specialist either (a) runs and produces real activity, or (b) is
      cleanly and quickly skipped with an explicit "specialist unavailable on
      this substrate" signal — NOT a 150s no-activity hang + `validation=violation`.
- [ ] If the specialist is genuinely redundant with the Coach's own independent
      test run (which is what actually verified TSJ-001 in run 3), document that
      and gate it off cheaply rather than invoking-then-hanging.
- [ ] Regression test exercising the no-activity branch (no Player model calls →
      fast clean skip / surfaced absent-signal, not a duration-cap grind).
- [ ] The SPECVIOL01 invariant continues to hold (a specialist
      `validation=violation` must not become a Player honesty `must_fix`).

## Evidence
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md` §"Finding 3".
- Run log: `.guardkit/autobuild/FEAT-9DDE-run3-stdout.log` (specialist hang lines, both turns).
- Specialist records: `.guardkit/worktrees/FEAT-9DDE/.guardkit/autobuild/TASK-TSJ-001/specialist_results.json`.
</content>
