---
id: TASK-FIX-AOFBUDG
title: Raise FEAT-AOF task_timeout so a turn-1-reject → turn-2-accept run fits the budget
status: completed
task_type: chore
created: 2026-06-07T13:00:00Z
updated: 2026-06-07T14:45:00Z
completed: 2026-06-07T14:45:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "AC-1 satisfied — per-task task_timeout=4800 committed to FEAT-AOF subtasks (AC-2 verified by next run)"
priority: high
complexity: 2
effort_hours: 1
deadline: 2026-06-15
parent_review: TASK-REV-AOF-RUN9
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: direct
intensity: standard
blocker: true
surfaced_in: ../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md
falsifier: "After landing, the next FEAT-AOF run that legitimately needs a turn 2 (Player+specialists ~921s + Coach ~946s on top of a ~1998s turn 1 ≈ 3864s wall-clock) completes inside the configured task_timeout with margin, rather than being cancelled by a feature-level timeout mid-turn-2-Coach."
---

# Task: Raise FEAT-AOF task_timeout to survive a 2-turn run (anomaly A / R1)

## Why this task exists

Run-9 was killed by the **3000s feature `task_timeout`** firing mid-turn-2-Coach.
The run-9 readiness review (`TASK-REV-AOF-RUN9` §3) measured per-turn substrate
cost and showed 3000s only covers a **turn-1-accept** run:

| Scenario | Wall-clock | Fits 3000s? | Fits 4800s? |
|---|---|---|---|
| Turn-1 ACCEPT (B fixed, clean) | ~1998s | ✅ (~1000s margin) | ✅ |
| Turn-1 REJECT → Turn-2 ACCEPT | ~3864s | ❌ **timeout** | ✅ (~936s margin) |

The review concluded a turn-1 accept is **possible but not reliable** (AC-006
unverified; Coach independent-test failures; interpreter mismatch — Finding N), so
the run must be able to survive a legitimate turn 2. The usual counter-argument
("more time just lets a retry storm run longer") **does not apply once the
reasoning fix (`TASK-FIX-COACHBUDG01-LG`) has landed** — turn 1 then yields a real
verdict, so a turn 2 is genuine revision, not a synthetic-feedback storm. Raising
the budget also relieves the per-invocation `budget_cap` squeeze (run-9 turn-2
Player was throttled to 1001s).

## What to do

- Set FEAT-AOF `task_timeout` to **≥4800s (80 min)** in
  `.guardkit/features/FEAT-AOF.yaml`, **or** launch with `--timeout-multiplier 1.6`.
- Prefer the multiplier if this is a one-off validation; prefer the yaml value if
  4800s should be the standing budget for this substrate.

## Acceptance criteria

- [x] **AC-1:** Next FEAT-AOF validation launched with task_timeout ≥ 4800s
  (or `--timeout-multiplier 1.6`). — Satisfied via committed per-task frontmatter
  override `autobuild.task_timeout: 4800` on all three FEAT-AOF subtasks
  (IA03 / GD02 / TP05). Resolves to ≥4800s for any `timeout_multiplier ≥ 1.0`
  (verified: 1.0 → 4800s, 1.6 → 7680s).
- [ ] **AC-2:** A 2-turn run completes without a feature-level timeout cancel.
  — Downstream verification (the falsifier); confirmed by the next FEAT-AOF run.

## Implementation note (mechanism correction)

The task originally proposed setting `task_timeout` in
`.guardkit/features/FEAT-AOF.yaml`. That path is a **no-op**: the feature YAML
schema has no `task_timeout` slot and `FeatureOrchestrator` never reads one from
it (it consumes only `id/name/description/tasks/orchestration/execution`). The
feature-level budget comes from the `--task-timeout` CLI flag (default 2400,
floored to 3000 via `GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR`, then × multiplier),
and run-9's `3000s` cancel was that floor × multiplier 1.0.

The only **file-committed, durable** mechanism is the per-task frontmatter
override `autobuild.task_timeout`, read by
`FeatureOrchestrator._resolve_task_timeout`. That is what was applied — it
matches the author's "standing budget for this substrate" intent and survives
regardless of how the next run is launched.

Equivalent one-off launch flag (no commit needed) remains available:
`guardkit autobuild feature FEAT-AOF --timeout-multiplier 1.6` (3000 × 1.6 =
4800s) or `--task-timeout 4800`.

**Files changed:**
- `tasks/backlog/autobuild-observability-fixes/TASK-FIX-IA03-…md` (+`autobuild.task_timeout: 4800`)
- `tasks/backlog/autobuild-observability-fixes/TASK-FIX-GD02-…md` (+`autobuild.task_timeout: 4800`)
- `tasks/backlog/autobuild-observability-fixes/TASK-FIX-TP05-…md` (+`autobuild.task_timeout: 4800`)

## Dependency

Pairs with the AC-006 probe (`TASK-FIX-AC006SMOKE-LG`, guardkitfactory) — run the
probe first, then launch with the raised budget.

## References

- Review (§3 budget, R1): `../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md`
- Run-9 log L12, L68, L353, L469-471
