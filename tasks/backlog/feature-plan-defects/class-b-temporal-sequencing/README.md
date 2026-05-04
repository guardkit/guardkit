# Class B: temporal mis-sequencing

**Defect**: `/feature-plan` sets `smoke_gates.after_wave` to fire a
gate **before** the wave that creates the gate's target test file.
The gate's positional pytest path does not exist on disk yet —
pytest exits 4, the wave is blocked.

**Reproducer**: study-tutor FEAT-FD32 Run 2 (2026-05-02). Plan
emitted `after_wave: [2, 3]` for a gate referencing
`tests/smoke/test_graphiti_live_smoke.py`, which TASK-GR-SMOK
(Wave 3, AC-SMOK-01) is responsible for creating. Gate fired after
Wave 2, hit exit 4, blocked 4/5 tasks. Manual fix:
`after_wave: [2, 3]` → `[3]`.

**Parent review**: [`TASK-REV-DEA8`](https://github.com/appmilla/forge)
(in `appmilla_github/forge/` — shared with Class A; both classes
were diagnosed in the same review pass).

## Where the actual fix lives

Class B does not have its own subtask set. The temporal-sequencing
check is a carve-out within the Class A validators —
[`../class-a-invented-paths/`](../class-a-invented-paths/) —
because they share the same parser (`parse_positional_paths`) and
the same enforcement points (L3b generator, L3d feature-validate,
L4 feature-loader pre-flight).

The carve-out specifies, for each `after_wave` value W and each
positional path P in `smoke_gates.command`:

- **Class A check**: Does P exist on disk **right now**?
- **Class B check**: If P does not exist now, does some task whose
  `wave < W` declare P (or a parent directory of P) in its
  `task_type=testing` test-output declarations?
  - If yes → fine.
  - If no → **reject as Class B mis-sequencing** with a message
    naming the wave that creates the file.

Read [`../class-a-invented-paths/README.md`](../class-a-invented-paths/README.md)
("Class B" subsections) and
[`../class-a-invented-paths/IMPLEMENTATION-GUIDE.md`](../class-a-invented-paths/IMPLEMENTATION-GUIDE.md)
for the full layer breakdown. The relevant tasks are:

- **TASK-FPSG-002** (L3b — `generate-feature-yaml --validate-smoke-gates`)
  — primary location of the temporal carve-out logic.
- **TASK-FPSG-004** (L3d — `feature validate` extension) — re-uses
  the same parser/check logic for the CLI validator.
- **TASK-FPSG-005** (L4 — `FeatureLoader._parse_feature` pre-flight)
  — defence-in-depth at feature-load time.

## Why no separate subfolder of tasks

The task scope was "one validator surface, two checks per call".
Splitting the validator into Class-A-only and Class-B-only files
would force callers to invoke two separate validators per
`smoke_gates` block, with no benefit — both checks need the same
parsed argv. The pragmatic choice was: one validator, one parser,
both checks. The defects are conceptually distinct (catalogued
here for diagnosis); the implementations are shared.

## See also

- [`docs/guides/feature-plan-task-classification.md`](../../../../docs/guides/feature-plan-task-classification.md)
  — operator-facing classification guide for all three classes.
- [`../class-a-invented-paths/README.md`](../class-a-invented-paths/README.md)
  — full Class A + Class B problem statement and wave plan.
- [`../README.md`](../README.md) — three-class umbrella.
