---
id: TASK-AB-WTISO01
title: Per-task worktree isolation for parallel waves (design-first)
status: backlog
created: 2026-07-04T09:40:00Z
priority: medium
tags: [autobuild, worktree, parallel-waves, isolation, checkpoints, evidence-boundary, design-first]
complexity: 9
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Per-task worktree isolation for parallel waves

> **CLOSED 2026-07-05: wontfix — serialize instead** (operator decision on
> handoff §2.3 question 1, delegated with "long-term correctness as the
> goal"; this file stays as the closure record and re-open mandate).
>
> Rationale: serialization is CORRECT — it produces right answers, just
> slower — while a per-task-worktree layer touches ~7 load-bearing
> invariants at once (evidence boundary, `git add -A` checkpoints,
> `reset --hard` rollback, the two-level fcntl/threading lock, wave-merge
> semantics, per-worktree venv bootstrap cost, and the wiring gate's
> wave-aggregate aperture). Local backends are capped at 1 by design
> (KV-cache), so parallelism only pays on cloud runs; the landed mitigation
> stack (overlap auto-serialise default-on + lowering-only YAML tier +
> interference stall subtype, TASK-AB-WAVECTL01/STALLTAX01) already forces
> serial execution exactly where interference would occur, leaving only
> non-overlapping tasks parallel — which are safe in a shared worktree.
> Building the isolation layer speculatively, without demonstrated demand,
> is where the correctness risk lives (YAGNI). Precedent: TASK-ABSR-WTKS
> filed this class 2026-04-28 and was deferred for the same reasons.
>
> **Re-open trigger:** cloud runs with genuinely parallel overlapping-file
> waves become routine AND overlap auto-serialisation is a measured
> throughput bottleneck. If re-opened, the original design-first mandate
> below stands unchanged: `/task-work --design-only` + Phase 2.5 review
> before any implementation task is cut.
>
> Original filing note (preserved): this is the real structural fix for R2,
> but it touches the evidence boundary, `git add -A` checkpoints,
> `reset --hard` rollback, cross-process locks and merge semantics. It MUST
> go through `/task-work --design-only` (design doc + Phase 2.5 review)
> before any implementation task is cut.

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 14 (R2 —
FEAT-SMP-001 parallel-wave shared-worktree pollution).

The genuine architectural property behind R2 (all VERIFIED):

- One shared worktree per feature (`feature_orchestrator.py:554`,
  `:1158-1162`); wave tasks run **concurrently against it**
  (`:2820-2837`).
- Checkpoints stage the **entire** shared tree (`git add -A`,
  `worktree_checkpoints.py:470-474`), so task A's checkpoint bakes in task
  B's half-written files.
- `rollback_to` is a shared `git reset --hard` (`:672`) with **no wave
  gating** — rolling back task A destroys task B's in-flight work.

With SMP-02 ∥ SMP-03 both retrying in lock-step, cross-task contamination
red-lined both tasks into `context_pollution_stall_no_checkpoint`. The A7B2
contention detection + ABFIX-005 amnesty assume the wave becomes effectively
single-tasked by the next turn (`coach_validator.py:2298-2301`) — an
assumption lock-step retries break.

Per-task worktree isolation (each wave task gets its own worktree, merged
back on approval) removes the contamination class structurally. But every
one of these subsystems currently assumes the shared tree and must be
re-designed together, not patched piecemeal:

1. **Evidence boundary** — post-turn `git diff` baselines, `files_modified`
   attribution, `evidence_repos` resolution, honesty path checks.
2. **Checkpoints** — `git add -A` staging scope, checkpoint identity,
   `find_last_passing_checkpoint` semantics per task.
3. **Rollback** — `reset --hard` blast radius becomes per-task.
4. **Locks** — the cross-process `fcntl` lock contention model changes.
5. **Merge semantics** — per-task worktree → feature worktree → main is a
   new merge hop with conflict handling; interaction with
   `/feature-complete`.
6. **A7B2/ABFIX-005** — decide explicitly what survives (see constraints).

## Acceptance Criteria

- [ ] AC-001 (design gate): a design document covering all six surfaces
      above, reviewed and approved (Phase 2.5 + human checkpoint —
      complexity ≥7), BEFORE any implementation tasks are filed.
- [ ] AC-002: the design specifies the evidence-boundary treatment: each
      task's oracle aperture covers exactly its own worktree plus declared
      `evidence_repos` — explicit roots, no implicit parent scanning.
- [ ] AC-003: the design specifies per-task checkpoint/rollback semantics
      (a task's rollback cannot destroy a sibling's work) and the fate of
      the shared-tree `git add -A` / `reset --hard` code paths.
- [ ] AC-004: the design specifies merge-back semantics on task approval,
      conflict handling, and the interaction with wave completion
      persistence (C1 mark-gating) and `/feature-complete`.
- [ ] AC-005: the design states explicitly which parts of A7B2 contention
      detection and the ABFIX-005 amnesty are retired vs retained, with
      rationale (hand-authored overlapping waves remain possible).
- [ ] AC-006: the design addresses resource cost (N worktrees + N venvs per
      wave) and the bootstrap implications (`environment_bootstrap` per
      task worktree vs shared).
- [ ] AC-007: implementation is decomposed into follow-up tasks only after
      AC-001; this task itself ships the approved design, not code.

## Implementation Notes

File:line anchors from the xref (§3 R2 item 1, §5 item 14):

- `guardkit/orchestrator/feature_orchestrator.py:554`, `:1158-1162` — one
  shared worktree per feature.
- `feature_orchestrator.py:2820-2837` — wave tasks dispatched concurrently
  against it.
- `guardkit/orchestrator/worktree_checkpoints.py:470-474` — checkpoint
  `git add -A` stages the entire shared tree.
- `worktree_checkpoints.py:672` — `rollback_to` shared `git reset --hard`,
  no wave gating.
- `guardkit/orchestrator/quality_gates/coach_validator.py:2298-2301` — the
  A7B2/ABFIX-005 single-tasked-by-next-turn assumption.
- Prior deferral: TASK-ABSR-WTKS (2026-04-28) — locate and fold in its
  notes.
- Mitigation in the meantime: TASK-AB-WAVECTL01 (overlap-aware
  serialization, `--max-parallel 1` operator rule per xref §5 item 2).

## Regression constraints

From xref §5/§6 — load-bearing; the design must address each explicitly:

- **Evidence boundary must cover the write surface, explicitly**
  (`.claude/rules/evidence-boundary-narrower-than-write-surface.md`):
  per-task worktrees change every oracle's spatial aperture. Declared
  roots only — no implicit scanning; the repo-qualified path contract
  (`evidence_repos.py`) is the single source of truth to extend, and the
  seam tests must stay loud.
- **Checkpoint tri-state semantics intact** (§6): `cp.tests_passed is
  False` (`worktree_checkpoints.py:738`) remains the only stall
  contributor; re-plumbing checkpoints must not collapse `None`
  (`.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/absence-must-survive-every-reconciliation-layer.md`).
- **Orchestrator-induced moves must not become honesty false-reds**
  (`.claude/rules/path-string-mismatch-is-not-dishonesty.md`): worktree
  reshuffling and merge-backs are orchestrator mutations; they must be
  tracked and filtered from Player attribution exactly as
  `state_transitions.json` moves are today.
- **A7B2 veto + amnesty are load-bearing until replaced** (§6): "do not
  remove it when adding serialization (operators can still hand-author
  overlapping waves)" — retirement requires the design's explicit
  rationale, not a silent drop.
- **Feed back, never terminate** (§6;
  `.claude/rules/smoke-gate-is-feedback-not-terminator.md`): gate
  dispositions (bounded `seed_feedback`, replace-not-append
  `wave_results[-1]`, C1 mark-gating) survive the re-plumb.
- **Bound any cross-repo/cross-worktree git op holding a lock**
  (`evidence-boundary-narrower-than-write-surface.md` remediation 7): the
  new merge hop must not introduce an unbounded git call under the shared
  `fcntl` lock.
- **BDD per-task glue race rules** (`.claude/rules/bdd-per-task-glue.md`):
  isolation likely *simplifies* these; the design should say how.
