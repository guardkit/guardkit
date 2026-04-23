# FEAT-RWOP1 — Orphan cleanup (non-cohort-blocking)

**Parent review:** [TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
**Parent cohort dependency:** [TASK-COH-RUN1](../r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md)
**Orchestrator guide:** [FEAT-RWOP1-IMPLEMENTATION-GUIDE.md](../FEAT-RWOP1-IMPLEMENTATION-GUIDE.md)

## What's in this folder

Non-cohort-blocking remediation tasks filed out of the
TASK-REV-RWOP1 runner-without-producer orphan sweep. These tasks
address the orphans that do NOT contaminate cohort evidence:

- [TASK-FIX-RWOP1.3-task-work-orphan-rollup.md](TASK-FIX-RWOP1.3-task-work-orphan-rollup.md) — triage + execute 22 wire-vs-delete decisions across `task-work.md`'s orphan surface (priority: medium, complexity: 6).
- [TASK-FIX-RWOP1.4-feature-spec-coach-gating-and-dead-surface.md](TASK-FIX-RWOP1.4-feature-spec-coach-gating-and-dead-surface.md) — decide Phase 5 Coach low-confidence gating + `FeatureSpecCommand` dead-Python-surface disposition (priority: medium, complexity: 4).
- [TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md](../../completed/2026-04/TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md) — `--from-spec` 8-helper orphan chain disposition (priority: low, complexity: 3). **Status: completed** (DELETE executed; helpers + tests quarantined to `_scratch/planning/` with 90-day grace through 2026-07-21).
- [TASK-FIX-RWOP1.6-add-lint-ac-coverage-for-live-feature-plan.md](TASK-FIX-RWOP1.6-add-lint-ac-coverage-for-live-feature-plan.md) — add lint-ac coverage for the live (non-from-spec) feature-plan path (priority: medium, complexity: 4). **Spawned by RWOP1.5** to close the coverage gap left by quarantining `test_lint_ac_compliance.py`.
- [TASK-FIX-RWOP1.7-align-wider-from-spec-docs-footprint.md](TASK-FIX-RWOP1.7-align-wider-from-spec-docs-footprint.md) — align wider `--from-spec` docs/metadata footprint (`docs/guides/two-phase-workflow.md`, `docs/reference/feature-plan.md`, `.guardkit/features/FEAT-FP-002.yaml`, `tests/fixtures/sample-research-spec.md`) with the RWOP1.5 quarantine (priority: low, complexity: 3). **Spawned by RWOP1.5**.

## What's NOT in this folder

The two **cohort-blocking** remediation tasks live in
[tasks/backlog/r2-pipeline-closure-and-forge-cohort/](../r2-pipeline-closure-and-forge-cohort/)
alongside `TASK-COH-RUN1` — they gate the forge + study-tutor cohort
run and are deliberately co-located with that workstream:

- [TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md](../r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md) — wire `/feature-plan` Step 11 auto-tagging (priority: high, complexity: 6).
- [TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md](../r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md) — fold Steps 10.6 + 10.7 nudges into `generate_feature_yaml.py` (priority: high, complexity: 3).

## Ordering

- **Nothing in this folder blocks TASK-COH-RUN1.** Run these in
  parallel with the cohort-gating workstream if you want, or defer
  all of them until after COH-RUN1 lands — they are hygiene, not
  path-critical.
- RWOP1.3 / 1.4 / 1.5 are independent of each other. Any wave order
  works.
- RWOP1.6 and RWOP1.7 both depend on RWOP1.5 having merged (they
  reference the quarantine and the stripped `feature-plan.md` it
  produced). 1.6 and 1.7 are independent of each other and can run
  in parallel after 1.5 lands.
- RWOP1.3 has the largest scope (22 orphans to triage + execute in
  its own Phase 1/2/3/4); consider splitting into its own sub-wave
  once its Phase 1 triage lands.

## Related

- Design-rule candidate (Graphiti): *"runner without producer
  anti-pattern"* — group `guardkit__project_decisions`, uuid
  `184731b0-3cb6-4eb2-a310-883421767dbf`
- Canonical fix shape: [TASK-FIX-3C9D](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
  (R1 precedent, to which all five RWOP1.x tasks refer)
