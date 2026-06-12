---
id: TASK-QAWE-004
title: SPEC_GAP evidence (consumes factory BDDRunResult) + the one deterministic hard-guard
task_type: feature
parent_task: TASK-HMIG-BDDWIRE
feature_id: FEAT-C332
wave: 4
implementation_mode: task-work
complexity: 5
dependencies: [TASK-QAWE-002]
priority: medium
---

# Task: SPEC_GAP evidence + deterministic hard-guard (Wave 3)

## Description

SPEC_GAP detects a `@task`-tagged Gherkin scenario with no executed binding. Gherkin
enumeration is language-agnostic; the executed evidence is **consumed** from the
factory `BDDRunResult` — it writes NO per-stack code. Includes the ONE deterministic
hard-gate (whole-file silent deselection). Per
`docs/features/qa-verifier-wiring-probes-scope.md` §4.3 / §5.4.

> **CROSS-FEATURE GATE:** this task **depends on FEAT-E2CB (BDDWIRE)** being merged —
> SPEC_GAP consumes the multi-stack `BDDRunResult` that BDDWIRE wires into the Coach.
> Do NOT run this wave until BDDWIRE has landed. (Not expressible in the feature YAML;
> operator-sequenced.) Until then, the per-scenario diff degrades to `counts_only`.

## Acceptance Criteria

- [ ] **AC-011 (SPEC_GAP per-scenario):** a tagged scenario in ground truth but absent
  from the executed set → one advisory `spec_gap` finding.
- [ ] **AC-012 (absent-`scenarios_attempted` control):** a `BDDRunResult` whose
  `scenarios_attempted` key is **absent** does NOT set `whole_file_deselection` and
  does NOT fire the hard gate (`.get(...,0)` forbidden; absent = UNKNOWN).
- [ ] **AC-013 (hard-guard red→green reproducer):** `ground_truth_count > 0` with
  `scenarios_attempted` present-and-zero → `whole_file_deselection:true` → NEW
  `_apply_spec_gap_absent_guard` (modelled on `_reconcile_absent_independent_test_signal`,
  `agent_invoker.py:5083`, wired at `:2233`) overrides `approve`→`feedback`, prepends a
  `must_fix` `category:"absence_of_failure"` issue, re-persists `coach_turn_N.json`.
- [ ] **AC-014 (None-safety):** the guard no-ops when `evidence_bundle is None`,
  `spec_gap is None`, or `whole_file_deselection` absent/falsey.
- [ ] **AC-022 (SPEC_GAP unsupported-stack):** when `bdd.discover(stack)` returns
  `None`, `spec_gap.status` is `unsupported_stack` and the guard does not fire.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation
- `pytest tests/orchestrator -k "spec_gap or absent_guard" -v`
- Lint/format pass with zero errors.
