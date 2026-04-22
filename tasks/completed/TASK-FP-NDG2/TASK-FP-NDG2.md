---
id: TASK-FP-NDG2
title: Add /feature-plan nudge when feature YAML lacks smoke_gates: (R3 opt-in ergonomics)
status: completed
task_type: implementation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
completed: 2026-04-22T00:00:00Z
priority: medium
complexity: 2
tags: [feature-plan, r3, ergonomics, nudge, smoke-gates, task-smk-f703a]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: direct
wave: 1
conductor_workspace: r2-pipeline-closure-wave1-r3-nudge
depends_on: []
previous_state: in_review
state_transition_reason: "task-complete — all 6 AC satisfied, 14/14 unit tests pass, 92% module coverage"
intensity: minimal
completed_location: tasks/completed/TASK-FP-NDG2/
organized_files:
  - TASK-FP-NDG2.md
---

# Task: Add /feature-plan nudge for missing smoke_gates: (R3 ergonomics)

## Problem Statement

TASK-REV-4D190 surfaced a parallel ergonomics gap for R3. FEAT-JARVIS-001.yaml was explicitly produced *after* the R3 smoke-gate remediation landed, by an author aware of the remediation, and still had no `smoke_gates:` key. The opt-in is silent: `/feature-plan` does not nudge authors to add one, and for features large enough to have wave-level composition risk, the absence of the nudge means R3 won't fire when it's most needed.

Same shape as TASK-FP-NDG1 but for R3. Print a notice if the generated feature YAML has no `smoke_gates:` key and the feature has ≥2 waves (single-wave features have nothing to gate between).

## Scope

### In-Scope

- In `/feature-plan`, after the feature YAML is generated, check:
  - does it have a `smoke_gates:` top-level key? (`yes` / `no`)
  - how many waves does the plan have? (`>= 2` triggers the nudge; `1` does not)
- If `no smoke_gates` AND `>= 2 waves`, print:

  ```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ℹ️  Feature-level smoke gates (R3) not configured
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  This feature has {N} waves but no smoke_gates: key in the generated YAML.
  Between-wave smoke checks will not fire during autobuild.

  This is the gate that catches composition failures (e.g., the PEX-014..020
  "13/13 green + e2e broken" pattern) that per-task Coach approval misses.

  To activate: add a smoke_gates: block to the feature YAML before running
  /feature-build. Minimal example:
      smoke_gates:
        after_wave_1:
          - python -c "import your_package"
        after_wave_2:
          - pytest tests/smoke -x

  See installer/core/commands/feature-plan.md § "Smoke gates".
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ```

- If `smoke_gates` is present, or the feature has only 1 wave, no notice.
- Notice is suppressible via `--no-questions` or equivalent quiet flag.

### Out-of-Scope

- Auto-generating smoke gate commands (authors know their stack; generic `python -c "import X"` is fine as the example, not the generator).
- Blocking `/feature-build` from running without smoke gates (that's a much larger policy change — do not do here).
- Any changes to R1 or R2.

## Acceptance Criteria

- [x] Notice fires when feature YAML lacks `smoke_gates:` AND has ≥ 2 waves.
- [x] Notice does not fire when `smoke_gates:` is present (even if minimal).
- [x] Notice does not fire for single-wave features.
- [x] Notice is suppressible via quiet flag.
- [x] Unit tests cover the four branches (2 × wave-count × smoke-key-presence).
- [x] Notice text includes a minimal copy-pasteable example and a doc reference.

## Implementation Summary

- Added `installer/core/commands/lib/smoke_gates_nudge.py` — pure-read helper
  `check_smoke_gates_activation(feature_yaml_path, quiet=False)` that returns a
  notice string iff the YAML has ≥ 2 waves and no top-level `smoke_gates:`
  key. Twin to `bdd_oracle_nudge.check_bdd_oracle_activation`.
- Added `tests/unit/commands/test_smoke_gates_nudge.py` — 14 unit tests:
  4 AC branches (2 × wave-count × smoke-key) + quiet suppression + 6
  defensive branches (missing file, malformed YAML, non-mapping root, missing
  `orchestration`, missing/malformed `parallel_groups`).
- Added Step 10.7 to `installer/core/commands/feature-plan.md` — documents
  when and how `/feature-plan` calls the helper, suppression via
  `--no-questions`, branch table, and non-goals. Placed adjacent to Step 10.6
  (R2 nudge) to keep the twin structure visible.
- No changes to `generate_feature_yaml.py` — follows NDG1's integration
  pattern (helper + doc, no producer wiring). Nudge is advisory output, not a
  correctness gate, so the RunnerWithoutProducer determinism fix that moved
  the AC linter into the producer (TASK-FIX-3C9D) does not apply here.

## Test Results

- 14/14 unit tests pass (`pytest tests/unit/commands/test_smoke_gates_nudge.py`).
- 92% line coverage on `smoke_gates_nudge.py` (uncovered: yaml `ImportError`
  fallback, `OSError` on `read_text` — both defensive environments).
- NDG1 tests (9) re-run unchanged to confirm no regression.

## Implementation Notes

- Twin to TASK-FP-NDG1; implement them together (same file, same interaction point, same test harness).
- The N ≥ 2 wave threshold matters: single-wave features (rare but they exist, e.g., documentation-only features) have nothing to gate between. Don't spam those authors.
- If `docs/` around smoke gates doesn't yet have a "Smoke gates" section for `/feature-plan.md`, add one as part of this task.

## Related

- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` (§R3 per-remediation)
- R3 task: `tasks/completed/TASK-SMK-F703A/TASK-SMK-F703A.md`
- Graphiti: "AutoBuild smoke gates fire between waves, not tasks" (justifies the ≥2-wave threshold)
