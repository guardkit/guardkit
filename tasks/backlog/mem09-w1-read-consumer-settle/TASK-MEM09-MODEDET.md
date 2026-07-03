---
id: TASK-MEM09-MODEDET
title: Remove the dead graphiti_client param from mode_detector.detect_mode
status: in_review
created: 2026-07-03T00:00:00Z
updated: 2026-07-03T00:00:00Z
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

- [x] **AC-1:** the `graphiti_client` parameter is removed from `detect_mode`'s signature, and the
      "Deprecated / ignored" lines are removed from its docstring. *(signature now `['project_id']`; unused
      `Any` import also dropped.)*
- [x] **AC-2:** all call-sites resolve — `system_plan.py:188` unchanged (already keyword-only `project_id`);
      `grep -rn "graphiti_client" guardkit/planning/` returns empty; no production `detect_mode(` site passes
      `graphiti_client` (the only remaining reference is the `pytest.raises(TypeError)` regression guard).
- [x] **AC-3:** `guardkit/planning/mode_detector.py` has **zero** graphiti references
      (`grep -in graphiti` empty).
- [x] **AC-4:** the two tests that passed `graphiti_client=` were replaced with a `test_graphiti_client_param_removed`
      regression guard + a `test_returns_setup_with_project_id`; `detect_mode()` callable without the kwarg returns
      `"setup"`. Full suite: **7 pre-existing fails, zero new** (12473 passed).

## Outcome (2026-07-03, via `/task-work`, MINIMAL intensity)

Done. `mode_detector.py` param + docstring + `Any` import removed; `test_mode_detector.py` updated (20 planning
tests pass). Ran in-session through `/task-work` (not `guardkit autobuild task`).

## Non-Goals

- Do NOT change `detect_mode`'s always-`"setup"` behavior — whether the function should still exist / do real
  mode detection post-cutover is a **separate** question, out of scope for this de-graphiti cleanup.
- Do NOT touch other planning modules.

## Notes

Good warm-up / first task in the wave (complexity 2, `mode: standard`, no memory seam).
