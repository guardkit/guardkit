# TASK-FMDR-001 — provenance record

**Status:** completed (fleet task; tracking file not originally committed to this repo)

This is a provenance record for a fleet task whose *code* landed in this
repository but whose task-tracking file was never committed here. It exists so
the orchestrator's hardcoded reference to `TASK-FMDR-001` resolves under the
`tests/rules/test_no_dead_task_id_references.py` linter (the reference is real
provenance, not a dead/typo'd ID).

## What it was

The originating defect for **FEAT-FMDR**: an autobuild run where
`TASK-FMDR-001` was killed as `unrecoverable_stall` on a green codebase because
a timed-out (absent) test signal was coerced to an explicit `False` false-red.

## Where it is referenced

- [`guardkit/orchestrator/agent_invoker.py:9546`](../../guardkit/orchestrator/agent_invoker.py#L9546)
  — the `False`-here-is-the-false-red comment guarding the absent-signal path.

## Cross-references

- Design rule: [`.claude/rules/absence-must-survive-every-reconciliation-layer.md`](../../.claude/rules/absence-must-survive-every-reconciliation-layer.md)
  (seeded by the follow-up fix TASK-ABFIX-010, commit `069086a0`).
- Retro: [`docs/retro/session-handoff-2026-07-04-reliability-batch-landed-design-first-next.md`](../retro/session-handoff-2026-07-04-reliability-batch-landed-design-first-next.md).
