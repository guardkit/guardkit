# TASK-FIX-7A07 AC-9 — Jarvis FEAT-J002 replay fixture

Minimised, anonymised fixture reconstructed from the jarvis FEAT-J002
MacBook-Pro run on 2026-04-24 (see `docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md`).

**Source (not referenced at runtime — documented for traceability only):**
`.guardkit/autobuild/TASK-J002-008/`
- `task_work_results.json` → `agent_invocations_validation.status == "violation"`,
  `missing_phases == ["4", "5"]`, `expected_phases == 3`, `actual_invocations == 1`.
- `coach_turn_5.json` / `coach_turn_6.json` — Coach feedback entries carrying
  `issues[0].category == "agent_invocations_violation"`.

The fixture files here carry only the shape-critical fields and do not copy
Player or Coach prose from the original run.
