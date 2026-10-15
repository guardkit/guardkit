---
id: TASK-FIX-COACHMISREAD01
title: The coach no longer rejects a turn over a test run the record says was skipped on purpose
status: completed
task_type: bugfix
created: 2026-09-04
completed: 2026-09-05
completed_location: tasks/completed/2026-09/
record_filed: 2026-10-15
record_provenance: reconstructed-after-the-fact
implementing_commits:
  - 9c86919f706f0eba28cf7b39b95440d9f33ad846
  - fd3e6816b3e34142e31b5b4f0e6cea5d397390ec
tags: [autobuild, coach, independent-tests, filed-after-the-fact]
---

> **Filed after the fact, on 2026-10-15.** The work shipped on 2026-09-04 and
> 2026-09-05 in the two commits listed above. Comments, log lines and the
> persisted coach-decision tag in `guardkit/orchestrator/agent_invoker.py` name
> it `TASK-FIX-COACHMISREAD01`, but no task record was ever written, so the lint
> `tests/rules/test_no_dead_task_id_references.py` failed. This record is
> written from those commits and the code; it is not a plan written in advance.

# The coach no longer rejects a turn over a skipped-on-purpose test run

## What went wrong

On 4 September 2026 build build-FEAT-44A8 ran a documentation task. Documentation
tasks do not need tests, so the separate ("independent") test run was skipped on
purpose, and the coach's own evidence record said so (`signal_absent=false`,
`test_command="skipped"`, `tests_required=false`). The coach rejected the turn
anyway, three times, claiming the test signal was absent: the opposite of its
own record. Nothing in the code caught that direction of misreading.

## What changed

- `AgentInvoker._reconcile_contradicted_absent_test_claim` (commit `9c86919f`)
  removes a coach finding that claims the independent-test signal was absent
  when the record shows a deliberate, profile-allowed skip. It acts only when
  evidence gathering completed, the signal is present and not absent, the test
  command reads "skipped" and the task type does not require tests. The verdict
  becomes an approval only if no other finding is left. A genuinely absent
  signal still fails closed. The corrected decision is written back to
  `coach_turn_N.json`.
- Findings that can never reject a turn (non-critical honesty warnings) no
  longer keep the turn rejected after the false objection is removed; they stay
  attached to the approval as warnings (commit `fd3e6816`, measured on the
  build-FEAT-99E2 turn-3 records).

## Where the tests are

`tests/orchestrator/test_coach_contradicted_absent_test_claim_guard.py` and
`tests/orchestrator/test_coach_contradicted_absent_claim_advisory_promotion.py`,
graded against copies of the real records in
`tests/fixtures/coach-misread-2026-09-04/`.
