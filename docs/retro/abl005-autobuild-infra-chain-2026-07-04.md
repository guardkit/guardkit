# ABL-005 autobuild: four infra defects before a single honest Coach verdict

**Dates:** 2026-07-03 → 04 · **Feature:** FEAT-ABL-005 (ablation fixture tooling, fleet-memory)
**Loop:** guardkit autobuild, gpt-oss-120b Player / gemma4-coach Coach via llama-swap on the GB10
**Status at writing:** run 5 in flight (designated final attempt; if it fails on
infra, the remaining work is hand-finished — operator policy 2026-07-04).
**Companion:** `abl001-natscore-stub-false-green-2026-07-03.md` (the concurrent
ABL-001 run; shares defects #3a/#3b).

## The chain

Every failed run had a *different* root cause, and none of them was the
models'. The Player's wave-1 code was substantially sound from run 3 turn 1;
the loop failed around it four distinct ways before the Coach ever saw an
honest test signal.

| # | Run | Symptom | Root cause | Fix |
|---|-----|---------|-----------|-----|
| 1 | run 1 | loop died at startup | `guardkitfactory` not importable — system-python wrapper instead of the guardkit venv | invoke `.venv/bin/guardkit-py` (June-16 recipe) |
| 2 | run 2 | loop died at first model call | default cloud model with no credentials | llama-swap env: `OPENAI_BASE_URL` → `:9000/v1`, dummy key, pinned local models |
| 3a | run 3 | `unrecoverable_stall / context_pollution_stall_no_checkpoint` after 3 turns | **concurrent autobuild loops** (this + FEAT-ABL-001) with different Player models on one llama-swap → multi-minute model swaps every alternating request | serialize: one loop per llama-swap; match model pairs across consecutive runs |
| 3b | run 3 (compounding) | Coach Phase-4 died all 3 turns | `/tmp/pytest-of-richardwoollcott` **basetemp race** with the other loop's pytest | serialization removes it; for future parallel loops: per-loop `--basetemp` |
| 4 | run 4 | `absent test signal (deterministic Phase 4): tests_run=0` all 8 turns | **guardkit `--resume` venv-resolution defect**: resume skips bootstrap; `_resolve_venv_python` probes `<worktree>/.guardkit/venv` but bootstrap creates `<worktree>/.venv` → silent fallback to `sys.executable` (no `fleet_memory` installed) → pytest collects 0 tests | worktree-only: `ln -s ../.venv .guardkit/venv` (+ `.git/info/exclude`); **guardkit fix candidate: make resume re-resolve the bootstrap venv location or fail loudly instead of falling back** |

Reproduction evidence for #4 (the subtle one): the run-4 log records
`resolved_interpreter=<guardkit>/.venv/bin/python3` (the orchestrator's own);
hand-running that interpreter against the worktree tests reproduces the
0-collection ImportError byte-identical to
`.guardkit/worktrees/FEAT-ABL-005/.guardkit/autobuild/TASK-ABL5-001/specialist_results.json`.
After the symlink fix, the exact Phase-4-shaped command collects 5 tests:
4 pass, 1 genuine Player bug (`TypeError`, `fixture/__init__.py:119`) — the
first honest quality signal the loop ever had for this feature.

## What this cost, and what masked it

- ~4.5 hours of wall-clock and five run attempts to get one honest Coach turn.
- Defect #4 is the nastiest class: the Coach *appeared* to be rejecting the
  Player on quality for 8 straight turns, when it was actually blind
  (`tests_run=0` was recorded in the specialist record all along — the signal
  existed, nothing surfaced it). A stall verdict built on an empty test run is
  indistinguishable, from the outside, from a hard task.
- Shepherding gaps compounded it: `tail -F`-style monitors never exit, so the
  supervising agents slept through both failures (see companion retro's
  operational lessons — monitors must terminate; run the loop itself as the
  background task).

## Lessons beyond the fixes

1. **`tests_run=0` must be a loud, first-class failure**, not an input to a
   stall heuristic. Any Phase-4 record with zero collected tests should abort
   the turn with a verifier-infrastructure verdict — it can never mean
   "Player code is bad".
2. **Resume paths need the same bootstrap guarantees as fresh runs.** Skipping
   bootstrap is an optimization; silently degrading the interpreter is not.
   File as a guardkit task: resume-path venv resolution (probe `<worktree>/.venv`
   too, or persist `venv_python` in the feature execution state).
3. **The eval-substrate contrast is the phase-ablation argument in miniature.**
   The same day, the Harbor/Docker/PyTest track (spike + 3 corpus tasks, all
   oracle-validated RED→GREEN) ran without a single infra failure. Deterministic
   verifiers in pinned containers vs. a live orchestration loop on a shared box:
   the reliability gap is exactly why the ablation grades with the former.

## Outcome

- Run 5 (final attempt) launched 2026-07-04 with the venv fix proven by hand
  first; in-loop confirmation checkpoint at the first Phase-4.
- *Update on conclusion:* result, merge SHA or hand-finish decision, and
  whether defect #4's guardkit fix task was filed.
