---
id: TASK-MEM09-MODEDET
title: Remove the dead graphiti_client param from mode_detector.detect_mode
status: backlog
created: 2026-07-03T00:00:00Z
priority: low
feature_id: FEAT-MEM-09
wave: 1
task_type: refactor
complexity: 2
tags: [fleet-memory, degraphiti, cleanup, FEAT-MEM-09]
autobuild:
  enabled: true
  max_turns: 3
  base_branch: main
  mode: standard
---

# Task: Remove the dead graphiti_client param from mode_detector.detect_mode

> Trivial dead-code cleanup (guide §1 "drop only dead vestiges"). No memory read — **no live/boundary
> test needed**; this is the one W1 task with no fleet-memory seam.

## Description

`guardkit/planning/mode_detector.py::detect_mode` still accepts a `graphiti_client: Optional[Any] = None`
parameter ([`:35-36`](../../../guardkit/planning/mode_detector.py#L35)) that its docstring marks
"Deprecated / ignored (retained for compatibility)" ([`:46`](../../../guardkit/planning/mode_detector.py#L46))
and the body never uses (the function degrades to `return "setup"` at [`:62`](../../../guardkit/planning/mode_detector.py#L62)).
The only real caller — `system_plan.py:188` `await detect_mode(project_id=project_id)` — already does **not**
pass it. Remove the vestige.

## Acceptance Criteria

- [ ] **AC-1:** the `graphiti_client` parameter is removed from `detect_mode`'s signature, and the
      "Deprecated / ignored" lines are removed from its docstring.
- [ ] **AC-2:** all call-sites resolve — `system_plan.py:188` unchanged (already keyword-only `project_id`);
      `grep -rn "graphiti_client" guardkit/planning/` returns empty; `grep -rn "detect_mode(" guardkit/ tests/`
      shows no site passing `graphiti_client`.
- [ ] **AC-3:** `guardkit/planning/mode_detector.py` has **zero** graphiti references
      (`grep -in graphiti guardkit/planning/mode_detector.py` empty).
- [ ] **AC-4:** any existing `mode_detector` test that passed `graphiti_client=...` is updated; a test asserts
      `detect_mode` is callable without that kwarg and returns the expected mode. Full suite stays at the 7
      pre-existing fails, zero new.

## Non-Goals

- Do NOT change `detect_mode`'s always-`"setup"` behavior — whether the function should still exist / do real
  mode detection post-cutover is a **separate** question, out of scope for this de-graphiti cleanup.
- Do NOT touch other planning modules.

## Notes

Good warm-up / first task in the wave (complexity 2, `mode: standard`, no memory seam).
