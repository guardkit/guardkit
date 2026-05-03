# Implementation Guide: `/feature-plan` smoke-gate path validation

## Wave Breakdown

### Wave 1 — Independent surfaces + shared helper (parallel, ~2h)

Three independently shippable changes:

- **TASK-FPSG-001 (L3a)** — `/feature-plan.md` prompt rule.
  Pure markdown edit at
  `installer/core/commands/feature-plan.md`, lines 2311-2321 area.
  Adds a "Path verification — REQUIRED" subsection above the existing
  "Non-goals" subsection. Contract test asserts the new section exists.

- **TASK-FPSG-003 (L3c)** — `smoke_gates_nudge` grounding.
  Edit `installer/core/commands/lib/smoke_gates_nudge.py` so the nudge
  banner discovers and lists the target repo's `tests/` subdirectories
  before printing the example block. New helper:
  `discover_test_roots(repo_root: Path) -> list[str]`.

- **Shared helper** (lives inside TASK-FPSG-002 by convention) —
  `guardkit/lib/pytest_argv.py` (or inside
  `guardkit/orchestrator/smoke_gates.py`):

  ```python
  def parse_positional_paths(command: str) -> list[str]:
      """
      Parse a smoke_gates.command shell snippet and return the
      positional pytest argv (everything after `pytest` and before
      the first `-` flag, plus any positional args after `--`).

      Returns an empty list if `pytest` is not invoked.
      """
  ```

  The parser must handle `set -e` prefixes, multi-line `|` block
  scalars, `\n` continuations, `pytest -x tests/foo` (flag before
  positional), and `pytest -- tests/foo` (positional after `--`).

### Wave 2 — Generator + load-time defenses (parallel, ~2.5h)

- **TASK-FPSG-002 (L3b)** — `generate-feature-yaml --validate-smoke-gates`.
  Adds a new mode to
  `installer/core/commands/lib/generate_feature_yaml.py` and a new
  Step 8.6 in `feature-plan.md`. Uses the shared `parse_positional_paths`
  helper; resolves each path against the target repo root.

- **TASK-FPSG-005 (L4)** — `FeatureLoader._parse_feature` pre-flight.
  Edits `guardkit/orchestrator/feature_loader.py` lines 645-654 to
  call a new `_validate_smoke_gates_paths` after
  `SmokeGates.model_validate`. Raises a clear error before
  `Pre-flight validation passed` prints.

### Wave 3 — `feature validate` extension + installer wrapper fix (~3h)

- **TASK-FPSG-004 (L3d)** — extends `FeatureLoader.validate_feature`
  AND fixes the installed shell wrapper at
  `~/.agentecflow/bin/guardkit` so `guardkit feature validate
  FEAT-XXXX` actually reaches `cli/feature.py`. The wrapper fix is
  installer-side (likely under `installer/core/templates/` or
  `installer/cli/`) and may benefit from a separate worktree because
  it touches install-time plumbing.

  Add a post-install smoke test:
  ```bash
  guardkit feature --help | grep -q validate
  ```

## Execution Strategy

- **Parallel-safe:** TASK-FPSG-001, TASK-FPSG-003, and the shared
  helper module can land in a single Wave 1 worktree (no overlapping
  file edits). TASK-FPSG-002 and TASK-FPSG-005 share the helper from
  Wave 1 and edit different files, so they can land in parallel
  Wave 2 worktrees.
- **Sequential:** TASK-FPSG-004 last — it consumes the helper from
  Wave 1 and depends on TASK-FPSG-002's validator design landing
  first (so `feature validate` and `--validate-smoke-gates` produce
  the same error messages).

## Smoke gate for this feature

Use a **single composite smoke gate after all waves**, grounded
correctly in the actual `tests/` tree (eat your own dog food):

```yaml
smoke_gates:
  after_wave: all
  command: |
    set -e
    pytest tests/unit/commands/test_smoke_gates_nudge.py \
           tests/unit/commands/test_generate_feature_yaml_smoke_gate_validation.py \
           tests/unit/orchestrator/test_validate_feature_smoke_gates.py \
           tests/unit/orchestrator/test_feature_loader_smoke_gate_paths.py \
           tests/unit/lib/test_pytest_argv_parser.py \
           -x
  expected_exit: 0
  timeout: 120
```

If L3b, L3d, or L4 is broken, this smoke gate either fails or — if
the regression is in path validation — crashes with the same exit-4
the bug-under-fix produced. Self-validating.

## Test fixtures to create

A shared fixture under `tests/fixtures/feature_plan_smoke_gates/`:

- `valid_feature.yaml` — `smoke_gates.command` references existing paths.
- `invalid_feature_missing_path.yaml` — references `tests/cli/`
  (mirroring TASK-REV-DEA8's defect verbatim).
- `valid_feature_no_pytest.yaml` — `smoke_gates.command` invokes
  `python3 .guardkit/smoke/foo.py` (no pytest); `parse_positional_paths`
  returns `[]`; validators pass.

## Out of Scope

- **L5 (rejected)** — promoting pytest exit 4 to soft-warn in
  `run_smoke_gate`. Documented in TASK-REV-DEA8 §F9.
- Auto-generating smoke-gate commands — explicitly forbidden by
  `feature-plan.md:2312-2314` and unchanged by this feature.
- Cross-repo edits in forge — already shipped as `TASK-FIX-DEA8-001`
  in the forge repo.
