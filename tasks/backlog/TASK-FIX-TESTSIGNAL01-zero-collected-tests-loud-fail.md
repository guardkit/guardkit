---
id: TASK-FIX-TESTSIGNAL01
title: Phase-4 tests_run=0 must abort as verifier-infrastructure failure
status: backlog
task_type: bugfix
priority: high
created: 2026-07-05
tags: [autobuild, quality-gates, verifier-infrastructure]
---

# tests_run=0 is never a quality verdict

A Phase-4 deterministic pytest record with zero collected tests can only mean
verifier infrastructure is broken (venv, paths, collection error) — it can
never mean "Player code is bad". Today it feeds the stall heuristic: FEAT-ABL-005
run 4 recorded `tests_run=0` on every turn while the loop concluded
`unrecoverable_stall` (`docs/retro/abl005-autobuild-infra-chain-2026-07-04.md`,
lesson 1).

Fix: when the Phase-4 specialist record shows `tests_run == 0`, abort the turn
with an explicit verifier-infrastructure verdict (distinct from Player
rejection), surface the collection error, and do not count the turn against
the Player.

Acceptance: unit test simulating a 0-collection Phase-4 record produces the
infrastructure verdict and halts the task rather than iterating turns.
