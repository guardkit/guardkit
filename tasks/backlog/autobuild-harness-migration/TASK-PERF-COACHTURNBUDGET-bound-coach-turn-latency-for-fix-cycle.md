---
id: TASK-PERF-COACHTURNBUDGET
title: Bound Coach-turn latency so the B-full catch→fix cycle fits in the task budget
status: backlog
task_type: feature
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
priority: high
complexity: 5
parent_task: TASK-HMIG-010
related: [TASK-PERF-COACHSYNTH, TASK-ARCH-COACHBFULL, TASK-OPS-COACH31B, TASK-FIX-MAXPARALLEL01]
implementation_mode: task-work
intensity: strict
---

# Task: Bound Coach-turn latency so the catch→fix cycle fits in budget

## Why this task exists

Run-23 is the run where the Coach **grew teeth** — TP05's B-full Coach caught a
real Player regression (`feedback`, AC-002/003/004 `rejected`, a **critical
`TypeError` in `specialist_invocations.py:924`**) instead of rubber-stamping.
That is the win the whole arc was chasing.

**But the loop could not act on it.** TP05's Coach turn took **41m43s** (the
synthesis hit the 16 384 `max_tokens` ceiling — a 60 KB response — on dense
gemma4:31b), which **exhausted the 80-min task budget before turn 2 could
apply the fix** → `TIMEOUT_BUDGET_EXHAUSTED`. So the Coach found the bug and
then the loop ran out of time to let the Player fix it. A reviewer that catches
bugs but starves the fix cycle is only half a loop.

TASK-PERF-COACHSYNTH bounded the **gather** (Lever A — done; F20-context
overflow). Its **synthesis-latency levers were deferred** (resident g31, bound
synthesis prompt, cap generation). Run-23 proves they are now load-bearing:
the 41-min turn is the synthesis, not the gather.

## The tension to respect (do NOT make the Coach lazy)

The 41 minutes bought something real — a **thorough investigation that caught a
TypeError**. The fix is **not** "cap `max_tokens` low" (that would truncate the
`criteria_verification` + `issues` that *are* the bug report). The latency is
mostly **(a)** g31 cold-loading ~50 GB every Coach turn and **(b)** dense-31B
generating ~16 K tokens of `reasoning_content` + verdict under `--reasoning
auto`. Cut the latency **without** cutting the verdict substance or the
investigation depth.

## Levers

- **Lever 1 — keep g31 resident (biggest fixed win).** Stop llama-swap evicting
  g31 between Coach turns (the `coach31` set is `qw & g31`; the Player only needs
  `qw`). Removes the per-turn ~50 GB reload. (= COACHSYNTH AC-3, unshipped.)
- **Lever 2 — tune synthesis generation.** Stop the synthesis grinding to the
  16 384 ceiling on a complex task: cap/curtail `reasoning_content` (e.g.
  `--reasoning` budget or a lower synthesis `max_tokens` that still fits a full
  verdict), so generation stops when the verdict is done, not at the token cap.
  Verify `criteria_verification` + `issues` survive intact (no truncation).
- **Lever 3 — give B-full turns enough budget for ≥2 turns.** A catch→fix cycle
  is *two* Coach turns. If a single B-full turn can be ~40 min, an 80-min
  `--task-timeout` cannot fit two. Either cut per-turn latency (Levers 1–2) until
  two turns fit, OR raise the B-full `--task-timeout` as an explicit interim
  (document the number and why). Real fix is latency; budget bump is a stopgap.

## Acceptance criteria

- [ ] **AC-1 (resident g31)**: g31 is not cold-loaded every Coach turn (llama-swap
  log shows no per-turn `evict=[gemma4-31b]` + reload). Report the per-turn
  latency saved.
- [ ] **AC-2 (turn fits the fix cycle)**: a B-full Coach turn (gather + synthesis)
  on a TP05-class task completes within a bound that leaves room for a **second**
  turn inside `--task-timeout` (target: one turn ≤ ~50% of the task budget).
- [ ] **AC-3 (substance preserved)**: the synthesis no longer grinds to
  `max_tokens` on a complex task, AND the verdict still carries a populated
  `criteria_verification` + `issues` (no truncation of the bug report) — verified
  against a run-23-TP05-shaped reproducer.
- [ ] **AC-4 (catch→fix falsifier — the real one)**: a re-run where the Coach
  catches a real Player bug (turn 1 `feedback`) **and turn 2 actually runs and
  applies a fix within budget** — the run-23 failure inverted. The loop completes
  the catch→fix cycle rather than timing out after the catch.
- [ ] **AC-5 (depth preserved)**: the Coach still catches the run-23-class
  `TypeError` (don't trade bug-detection for speed).

## Notes

- This is the **synthesis-latency half** of TASK-PERF-COACHSYNTH (gather bound =
  Lever A, completed; this = Levers B/C/D). Filed separately because COACHSYNTH is
  already `completed` and the gather bound is validated-ish.
- Evidence: run-23 (`docs/state/TASK-REV-HMIG/run-23-artifacts/`) — TP05 41m43s /
  60 KB synthesis → `TIMEOUT_BUDGET_EXHAUSTED` before turn 2.
- Coordinate Lever 1 with TASK-OPS-COACH31B (the `coach31` set + keepalive policy
  on the GB10).
- Pairs with TASK-FIX-MAXPARALLEL01 (keep Coach calls sequential → no F20) — that
  fixes *availability*; this fixes *throughput* (the fix cycle).
