# TASK-FIX-RWOP1.5 — `/feature-plan --from-spec` Disposition Decision

**Task**: [TASK-FIX-RWOP1.5](../../tasks/completed/2026-04/TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md)
**Parent review**: [TASK-REV-RWOP1](../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) §Finding #8
**Decision date**: 2026-04-22
**Path chosen**: **DELETE** (with preservation in repo-root `_scratch/planning/` for 90 days)

## Evidence supporting DELETE over WIRE/EXTRACT

Dependency grep (`from guardkit.planning.{helper}` + variants) across the repo:

- **Zero non-test callers** for all 7 module files. Every hit is either a test file,
  a docstring example, or a cross-import **within** the 7-helper cluster
  (e.g. `adr_generator.py` → `spec_parser.py`).
- **No shell scripts, CI workflows, or fixtures** invoke `--from-spec`.
- **`__init__.py`** re-exports complexity_gating, graphiti_arch, mode_detector,
  system_overview, coach_context_builder, impact_analysis, context_switch —
  **none of the 7 helpers**. The cluster is already sub-packaged informally.
- **`feature-plan.md` CRITICAL EXECUTION INSTRUCTIONS** (lines 1934-2533)
  never reference `--from-spec`, so Claude is never told to run the chain
  even in principle.

The "never used in anger" hypothesis is now evidence-backed. WIRE would
cement a flag nobody asks for; EXTRACT would relocate dead code under a
nicer door. DELETE removes the runner-without-producer pattern outright.

## Scope enumeration

### Module files → move to `guardkit/_scratch/planning/`

| # | File | LOC | Exports used elsewhere? |
|---|------|-----|--------------------------|
| 1 | `guardkit/planning/spec_parser.py` | 845 | **Yes — `TaskDefinition`, `parse_research_template` used by test #3 below** |
| 2 | `guardkit/planning/target_mode.py` | 165 | No |
| 3 | `guardkit/planning/task_metadata.py` | 394 | No (imports spec_parser + target_mode; both slated for move) |
| 4 | `guardkit/planning/adr_generator.py` | 176 | No (imports spec_parser; slated for move) |
| 5 | `guardkit/planning/quality_gate_generator.py` | 183 | **Yes — `generate_quality_gates` used by test #3 below** |
| 6 | `guardkit/planning/warnings_extractor.py` | 70 | No |
| 7 | `guardkit/planning/seed_script_generator.py` | 107 | No |
| | **Total** | **1,940** | |

No `__init__.py` edits needed — none of the 7 are re-exported from
`guardkit/planning/__init__.py` today.

### Test files → co-move to `guardkit/_scratch/planning/tests/`

Dedicated (exercise the 7 helpers and nothing else):

1. `tests/unit/test_spec_parser.py`
2. `tests/unit/test_target_mode.py`
3. `tests/unit/test_task_metadata.py`
4. `tests/unit/test_adr_generator.py`
5. `tests/unit/test_quality_gate_generator.py`
6. `tests/unit/test_warnings_extractor.py`
7. `tests/unit/test_seed_script_generator.py`
8. `tests/integration/test_feature_plan_pipeline.py` — imports all 7 helpers
9. `tests/seam/test_planning_module_seams.py` — seam test for the cluster

### Test requiring special handling

**`tests/planning/test_lint_ac_compliance.py`** — this test verifies **live
lint-compliance policy** (feature plans must include lint-compliance ACs in
implementation tasks), but uses `parse_research_template` +
`generate_quality_gates` as setup scaffolding.

Observation: the test asserts that **parsed** tasks carry lint-compliance ACs.
Because the parser and the research-template format are the dead path, the
coverage is defending a path nobody uses. Live lint-ac coverage for the
current (non-from-spec) feature-plan flow lives (or should live) against
`installer/core/commands/lib/generate_feature_yaml.py` — the live producer
post-RWOP1.2.

**Disposition**: co-move `test_lint_ac_compliance.py` to
`guardkit/_scratch/planning/tests/`. Open follow-up task **TASK-FIX-RWOP1.6**
to add non-from-spec lint-ac coverage against the live `generate_feature_yaml`
path. Document this as a known, accepted coverage gap in the move's README.

Rationale: keeping `spec_parser` + `quality_gate_generator` live purely to
support one test that guards a dead path would undermine the cleanup.

### `feature-plan.md` — remove the following ranges

- **Line 27**: row in the flag reference table (`| --from-spec path/to/spec.md | ... |`)
- **Lines 230-294**: "From-Spec Mode Execution Flow" section header, module
  dependencies block, 9-step execution steps, example usage block
- **Lines 296-~345**: "Output Example" block that follows, plus fallthrough
- **Line 350**: backward-compat note referencing from-spec

Task's original claim of "lines 247-278" covered only the steps list; the
actual footprint is ~115 lines. Final line numbers will be re-confirmed at
execution time.

### `_scratch/` vs outright — and *where* to put `_scratch/`

**`_scratch/` with 90-day grace window.** Rationale per task's implementation
notes: gives anyone with private `--from-spec` usage a window to speak up
before irreversible deletion.

**Deviation from task spec**: the task suggested `guardkit/_scratch/planning/`
(inside the Python package). That path is unsafe given
`[tool.hatch.build.targets.wheel] packages = ["guardkit"]` in `pyproject.toml`
— anything under `guardkit/` ships in the wheel unless explicitly excluded.
Rather than maintain a hatch-exclude rule (config surface that can regress),
this disposition uses **repo-root `_scratch/planning/`**. Clean, zero-config,
and obviously not part of the distributable package. The README will document
the relocation so a future reader knows where to look.

`_scratch/planning/README.md` will document: (a) why moved, (b) deletion date
(2026-07-21), (c) how to wire back if someone surfaces a legitimate use case.

If the 90-day window passes with no complaint, `_scratch/planning/` is deleted
outright in a follow-up housekeeping task (no new decision required — this
doc authorises it).

## Execution plan

1. Capture baseline: `pytest tests/unit tests/integration tests/seam tests/planning -q --tb=no`
   and save output to this folder.
2. Create `guardkit/_scratch/planning/` + `guardkit/_scratch/planning/tests/`
   with a `README.md` per scope above.
3. `git mv` the 7 module files + 10 test files (9 listed + `test_lint_ac_compliance.py`).
4. Strip `--from-spec` sections from `feature-plan.md` (ranges above).
5. Remove the row from `installer/core/commands/bin-entries.txt` — *check first
   that no entry exists* (from inspection so far, there is no `feature-plan-from-spec`
   bin entry, so this step is likely a no-op).
6. Re-run the test suite. Expected result: same pass count minus the moved tests.
7. Re-run dependency grep to confirm `from guardkit.planning.{any of 7}` now returns
   only hits inside `_scratch/`.
8. Draft follow-up task `TASK-FIX-RWOP1.6` (lint-ac coverage for live path) and place
   in `tasks/backlog/feat-rwop1-orphan-cleanup/` or stand-alone.

## Rollback

If baseline tests regress post-move in a way not explained by the move itself
(i.e. a test outside the 10 files above starts failing), revert the whole
change set with `git revert` and escalate for re-scoping. No destructive git
operations; everything is `git mv` + edits, so rollback is mechanical.

## Known, accepted outcomes and out-of-scope footprint

### Accepted outcomes

- Coverage gap for live lint-ac policy until RWOP1.6 lands (the from-spec
  coverage it replaces was already defending dead code).
- Anyone with private `--from-spec` usage gets a 90-day complaint window
  before `_scratch/` is deleted.
- The adjacent flags `--target`, `--generate-adrs`, `--generate-quality-gates`
  were also removed from `feature-plan.md` (lines 28-30). They exist only to
  feed the from-spec pipeline and share its dead-producer status; leaving
  them documented while removing their producers would be doubly dead.

### Out-of-scope `--from-spec` footprint (follow-up cleanup)

Dependency grep surfaced a wider doc/metadata footprint referencing
`--from-spec`, `--target`, `--generate-adrs`, and `--generate-quality-gates`
that the original task scope did not cover. These remain in place and are
**out-of-scope for RWOP1.5**:

- `docs/guides/two-phase-workflow.md` — extensive usage examples
- `docs/reference/feature-plan.md` — flag table + dedicated sections
- `.guardkit/features/FEAT-FP-002.yaml` — feature metadata
- `docs/research/system-level-understanding/FEAT-FP-002-two-phase-feature-plan-enhancements.md`
  — historical research doc (should stay: historical record)
- `tasks/backlog/two-phase-feature-plan/TASK-FP002-007`/`008` and
  `tasks/in_review/TASK-FP002-007`/`008`/`009` — task tracking for the work
  that originally added these flags (should stay: historical record)
- `tests/fixtures/sample-research-spec.md` — orphaned fixture data

**Follow-up task**: **TASK-FIX-RWOP1.7** — align user-facing docs
(`docs/guides/two-phase-workflow.md`, `docs/reference/feature-plan.md`) and
`.guardkit/features/FEAT-FP-002.yaml` with the quarantine, and delete
`tests/fixtures/sample-research-spec.md`. The task tracking files and the
research doc stay as historical records.

Rationale for scope discipline: the task explicitly said "remove the
`--from-spec` flag handling from `feature-plan.md` lines 247-278 entirely."
Widening that to all `--from-spec` references repo-wide would be a
~10-file doc cleanup with its own review surface.

## Execution log

- 2026-04-22: Baseline captured — 172 failed, 9427 passed, 130 skipped
  (172 pre-existing failures, **zero in any of the 10 targeted test files**).
  Saved to
  [`TASK-FIX-RWOP1.5-baseline-pytest.txt`](TASK-FIX-RWOP1.5-baseline-pytest.txt).
- 2026-04-22: `_scratch/planning/` + `_scratch/planning/tests/` created with
  README documenting rationale, 90-day grace window (deletion 2026-07-21),
  and wire-back instructions.
- 2026-04-22: 7 module files + 10 test files moved via `git mv` — moves
  preserve history.
- 2026-04-22: `feature-plan.md` stripped — lines 27-30 (4 flag-table rows)
  + lines 230-350 (From-Spec Mode Execution Flow section). File size:
  2733 → 2608 lines (Δ 125 lines = 4 + 121; matches expected).
- 2026-04-22: No edit to `bin-entries.txt` needed — pre-edit grep confirmed
  zero `from-spec` references.
- 2026-04-22: Post-move dependency grep confirmed all 8 helper symbols are
  absent from live code. Remaining hits are in the review doc that
  *identified* the anti-pattern (TASK-REV-RWOP1) and the `sample-research-spec.md`
  fixture (flagged for RWOP1.7).

## Acceptance criteria mapping

- [x] AC1: Path chosen (DELETE) and rationale captured — this file.
- [x] AC2: Chosen path executed — 17 files moved, `feature-plan.md` stripped.
- [x] AC3: Post-execution grep — all 8 helpers absent from live code.
- [x] AC4: `/feature-plan` unit + integration suite remains green —
      `tests/integration/feature_plan/` runs 56/56 passing; full suite shows
      172 failures (identical to baseline set), 9118 passed
      (baseline 9427 − 309 moved tests, arithmetic confirms no test flipped
      state), 130 skipped (unchanged).
