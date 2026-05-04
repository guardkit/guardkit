# `/feature-plan` defects — three known classes

This folder collects the work that hardens `/feature-plan` against
the three classes of defect we have observed in production runs. The
classes are independent: a single feature run can hit one, two, or
all three. Each class has its own subfolder, parent review, and
prevention strategy.

> **Operator-facing classification guide**:
> [`docs/guides/feature-plan-task-classification.md`](../../../docs/guides/feature-plan-task-classification.md)
> — concise reference for the three classes, the strong/weak signal
> taxonomy, and the `operator_handoff` escape hatch.

## The three classes

| Class | Defect | Reproducer | Parent review | Subfolder |
|---|---|---|---|---|
| **A** | Invented paths — Plan agent emits pytest paths that do not exist on disk | forge FEAT-DEA8 Run 2 (2026-05-02) | [`TASK-REV-DEA8`](https://github.com/appmilla/forge) (in `appmilla_github/forge/`) | [`class-a-invented-paths/`](class-a-invented-paths/) |
| **B** | Temporal mis-sequencing — `after_wave` fires a smoke gate before the wave that creates its target file | study-tutor FEAT-FD32 Run 2 (2026-05-02) | [`TASK-REV-DEA8`](https://github.com/appmilla/forge) (shared with Class A) | [`class-b-temporal-sequencing/`](class-b-temporal-sequencing/) (cross-links into class-a/ for the validator carve-out) |
| **C** | Task-design mismatch — ACs specify `observed_at_runtime(real_world)` predicates that the Player↔Coach loop cannot satisfy | study-tutor FEAT-FD32 TASK-GR-SEED, TASK-GR-DEMO (2026-05-02 → 2026-05-03) | [`../TASK-REV-AUTM-decide-how-feature-plan-handles-autobuild-unsuitable-tasks.md`](../TASK-REV-AUTM-decide-how-feature-plan-handles-autobuild-unsuitable-tasks.md) | [`class-c-task-design-mismatch/`](class-c-task-design-mismatch/) |

## Class A — invented paths

**Problem.** `/feature-plan` designs `smoke_gates.command` shell
snippets without verifying that the positional pytest paths exist
in the target repo's `tests/` tree. A single bad token (e.g.
`tests/cli/` when only `tests/unit/` exists) bricks an otherwise
green autobuild run with pytest exit 4.

**Defence layers.** Five small edits across the authoring,
generation, validation, and load surfaces. Same defect must be
rejected by **at least two** layers before reaching `run_smoke_gate`.
See [`class-a-invented-paths/README.md`](class-a-invented-paths/README.md)
for the full layer breakdown (L3a / L3b / L3c / L3d / L4).

## Class B — temporal mis-sequencing

**Problem.** `/feature-plan` references test paths that a *later
wave* of the same feature is supposed to create, then sets
`after_wave` to a wave number that fires *before* the creation
wave. Reproducer: study-tutor FEAT-FD32 Run 2 set
`after_wave: [2, 3]` for a gate that referenced
`tests/smoke/test_graphiti_live_smoke.py`, which TASK-GR-SMOK
(Wave 3) was supposed to create. The gate fired after Wave 2,
hit pytest exit 4, blocked 4 of 5 tasks. Manual fix:
`after_wave: [2, 3]` → `[3]`.

**Defence layers.** The same validators as Class A
(L3b / L3d / L4) gain a temporal check on top of the path-existence
check. The check logic lives with the Class A validators — see the
"Class B carve-out" section in
[`class-a-invented-paths/README.md`](class-a-invented-paths/README.md)
and the stub at
[`class-b-temporal-sequencing/README.md`](class-b-temporal-sequencing/README.md)
for the cross-reference.

## Class C — task-design mismatch

**Problem.** `/feature-plan` routinely emits acceptance criteria
whose verification predicate is `observed_at_runtime(real_world)`
rather than `present_in_codebase(artifact)`. AutoBuild's Player↔Coach
loop cannot satisfy these by construction — Coach is a deterministic
file-existence and test-passing checker, not an oracle. Reproducers
in study-tutor FEAT-FD32 burned ~110 minutes of SDK budget across
two tasks before manual completion.

**Defence layers.** Plan-time detector + `task_type: operator_handoff`
enforcement (Shape D in the parent review). Two layers: a strong/weak
signal detector at plan time (cheap), and an orchestrator skip +
validator awareness at run time (safety net). Both must miss for a
Class C failure. See
[`class-c-task-design-mismatch/README.md`](class-c-task-design-mismatch/README.md)
for the full subtask breakdown (FPTC-001 through FPTC-007).

## Cross-class philosophy

All three classes share a design principle:
**plan-time prevention beats runtime detection.** The cheapest place
to reject a bad feature plan is the prompt round-trip with the
operator (one yes/no question). The most expensive place is the
turn-budget burn that wastes SDK minutes producing artefacts that
will never satisfy the gate. Each class's defence is anchored at
plan time (L3a for Class A/B, FPTC-001 for Class C) with run-time
safety nets (L4, FPTC-003/004) for cases the planner misses.

The classification guide at
[`docs/guides/feature-plan-task-classification.md`](../../../docs/guides/feature-plan-task-classification.md)
is the operator-facing summary of these classes, the signal
taxonomy used by the Class C detector, and the `operator_handoff`
escape hatch.

## Sibling completed work (orthogonal)

- Coach validator AC-matching:
  [`tasks/completed/2026-05/coach-validator-ac-id-matching/`](../../completed/2026-05/coach-validator-ac-id-matching/)
  — TASK-CVAC-001 (parser), TASK-CVAC-002 (bidirectional matching).
  Was a confound for Class C diagnosis until it shipped 2026-05-03;
  not a defect class itself.
