---
id: TASK-AB-BDDAUTHOR01
title: BDD authoring sweep — unfiltered pytest over glue-bound feature files, scenarios_undefined blocking within the sweep only
status: backlog
created: 2026-07-04T09:39:00Z
priority: high
tags: [autobuild, bdd, pytest-bdd, glue, coach, oracle, design-first]
complexity: 7
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: BDD authoring sweep (artefact-activated on authored glue)

> **Status note: backlog, NOT scheduled — design-first.** The scoping that
> keeps `bdd-pending-is-not-failed` intact by construction is the design's
> load-bearing element; get it reviewed before implementation.

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 12 (R4 gaps 1+2 —
FEAT-SMP-002 / TASK-SMP2-07: Coach approved with an undefined BDD step).

Why the existing oracle could not see it (all VERIFIED, xref §3 R4):

1. **Activation gap (primary, causal):** zero scenarios carry
   `@task:TASK-SMP2-07` — by the task's own design, tags route to
   SMP2-01..06. Activation-by-artefact (`run_bdd_for_task`,
   `bdd_runner.py:673-680`) therefore returns `None` for the
   step-def-**authoring** task: no pytest run, no junit (explains the
   missing `TASK-SMP2-07_junit.xml` — pytest writes it via `--junitxml`,
   `bdd_runner.py:567`), `bdd_results` absent → gate inert. Compounding: BDD
   glue is deliberately **excluded** from the Coach's independent pytest
   command (TASK-FIX-CC-BDD, `coach_validator.py:6740-6822`, itself a fix
   for FEAT-39E1 cross-task false-reds) — so the authoring task's glue is
   exercised by **neither** leg.
2. **Classification gap (latent):** even with a tag,
   `StepDefinitionNotFoundError` is a `_PENDING_MARKERS` hit
   (`bdd_runner.py:46-49`) → `scenarios_pending` → non-blocking
   `should_fix` — **by deliberate design** (`bdd-pending-is-not-failed`,
   TASK-BDD-E8954). The retro's action "classify it as failed" **as written
   would regress** the scaffolding-before-glue workflow that rule protects.
   (Also note correction C5: `StepDefinitionNotFoundError` is a *runtime*
   per-testcase failure, not a collection error — the classification path is
   the per-testcase `pending` mapping.)

The non-regressing fix is **ownership-scoped, not marker-reclassified**:

- When a turn's authored files include pytest-bdd glue (an
  `is_bdd_glue_file` predicate over the per-task `files_authored` records),
  additionally run pytest over the feature files that glue binds **without**
  the `-m task_<ID>` filter, emitting junit (this delivers the retro's
  action (c) — the missing junit artefact — for free).
- **Within the sweep only**, count `StepDefinitionNotFoundError` as a
  distinct **blocking** `scenarios_undefined` — leaving `_PENDING_MARKERS`
  and the tag-scoped pending semantics untouched. `bdd-pending-is-not-failed`
  is preserved **by construction**: scaffolding tasks author `.feature`
  files, not glue, and never enter the sweep; only the task that authored
  the glue is held to "your step definitions must resolve".
- The sweep must respect the per-task-glue race rules in parallel waves
  (`bdd-per-task-glue.md`) — sweeping another task's glue module is the
  cross-task race those rules exist to prevent.

## Acceptance Criteria

- [ ] AC-001 (design gate): a short design doc is reviewed covering: the
      `is_bdd_glue_file` predicate; how the sweep discovers which feature
      files a glue module binds; junit naming; the `scenarios_undefined`
      field's journey through `BDDResult` → `bdd_results` →
      `_check_bdd_results`; and the parallel-wave scoping.
- [ ] AC-002: the sweep activates by artefact only — a turn whose
      `files_authored` include pytest-bdd glue. No opt-in flag; turns
      authoring no glue see zero behaviour change.
- [ ] AC-003: the sweep runs pytest over the glue-bound feature files
      WITHOUT the `-m task_<ID>` filter and writes a junit XML artefact for
      the sweep run.
- [ ] AC-004: within the sweep only, `StepDefinitionNotFoundError` results
      are counted under a NEW distinct field `scenarios_undefined`, which is
      blocking (feeds back to the Player naming the undefined steps).
- [ ] AC-005: the tag-scoped oracle is byte-for-byte unchanged:
      `_PENDING_MARKERS` untouched; tag-scoped
      `StepDefinitionNotFoundError` still → `scenarios_pending`,
      non-blocking `should_fix`. The pinned tests for
      `bdd-pending-is-not-failed` (`test_pending_step_recorded_distinctly`,
      `test_bdd_pending_approves_with_feedback`) still pass unmodified.
- [ ] AC-006: the sweep only exercises glue authored by THIS task (per-task
      glue naming per `bdd-per-task-glue.md`); in a parallel wave it never
      collects a sibling task's glue module.
- [ ] AC-007: sweep failures feed back (bounded), never terminate the loop;
      a sweep that cannot run (pytest-bdd absent, runner error) surfaces as
      the existing synthesised-failure/absent semantics — never a vacuous
      pass.
- [ ] AC-008: regression tests: authoring-task-with-undefined-step →
      blocking `scenarios_undefined`; scaffolding task (feature file, no
      glue) → no sweep, pending semantics intact; parallel-wave glue
      isolation.

## Implementation Notes

File:line anchors from the xref (§3 R4, §5 item 12):

- `guardkit/orchestrator/quality_gates/bdd_runner.py:673-680` —
  `run_bdd_for_task` activation-by-tag (returns `None` for the authoring
  task; the sweep is an additional leg, not a change to this one).
- `bdd_runner.py:567` — `--junitxml` (the sweep reuses this to produce the
  missing junit artefact).
- `bdd_runner.py:46-49` — `_PENDING_MARKERS` (must remain untouched).
- `coach_validator.py:6740-6822` — TASK-FIX-CC-BDD glue exclusion from the
  independent pytest command (must remain; the sweep is a separate,
  BDD-aware leg, not a re-inclusion).
- `_check_bdd_results` (`coach_validator.py:7335`) — extend the
  `(blocking, non_blocking)` split with the sweep's `scenarios_undefined`.
- `feature_orchestrator.py:2401-2443` — `_wave_authored_files` (the
  `files_authored` reader the `is_bdd_glue_file` predicate runs over).
- Correction C5 (xref §2): classify via the per-testcase path, not the
  collection-error path.

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **Pending stays non-blocking for tag-scoped scenarios** (§6;
  `.claude/rules/bdd-pending-is-not-failed.md` pinned tests): the fix is
  **ownership-scoped (the authoring sweep), not a marker reclassification**.
  Any change to `_PENDING_MARKERS` or the tag-scoped pending mapping is the
  regression this constraint exists to block.
- **Activate by artefact, not opt-in flag**
  (`.claude/rules/activate-by-artefact-not-opt-in-flag.md`): authored glue
  IS the activation artefact; absent glue → silent, behaviour-identical
  skip. No `bdd_sweep: true` flag.
- **Per-task glue race rules**
  (`.claude/rules/bdd-per-task-glue.md`): the sweep must scope to
  `test_<slug>__<TASK_ID>.py` modules authored by this task; do not bind or
  collect a sibling task's scenarios in a parallel wave.
- **Glue exclusion from independent tests stays** (§6; TASK-FIX-CC-BDD):
  the Coach's independent pytest command keeps excluding glue; the sweep is
  a new leg with its own junit, not a widening of the old one.
- **Feed back, never terminate** (§6;
  `.claude/rules/smoke-gate-is-feedback-not-terminator.md`): a blocking
  `scenarios_undefined` produces Player feedback within the adversarial
  loop, bounded — never a bare terminator.
- **Vacuous-true guard**
  (`.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/bdd-pending-is-not-failed.md` remediation 4): a sweep that
  could not run is never zero-failures-approve; BDDNEUTRAL01's exit-4
  "not found" neutral semantics and the runner-error synthesised failure
  both remain intact
  (`.claude/rules/absence-must-survive-every-reconciliation-layer.md` for
  any new field's serialization journey).
