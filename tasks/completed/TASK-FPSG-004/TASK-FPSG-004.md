---
id: TASK-FPSG-004
title: "guardkit feature validate: check smoke-gate paths + fix installed wrapper to expose 'feature' subcommand (L3d)"
status: completed
created: 2026-05-02T13:30:00Z
updated: 2026-05-02T15:35:00Z
completed: 2026-05-02T15:35:00Z
completed_location: tasks/completed/TASK-FPSG-004/
priority: high
task_type: enhancement
implementation_mode: task-work
tags:
  - feature-validate
  - feature-loader
  - cli
  - installer
  - smoke-gate
  - cross-repo-followup
  - feature-plan-smoke-gate-validation
complexity: 6
estimated_minutes: 180
parent_review: appmilla_github/forge/TASK-REV-DEA8
parent_feature: feature-plan-smoke-gate-validation
wave: 3
dependencies:
  - TASK-FPSG-002  # shares parse_positional_paths helper
---

# Task: extend `guardkit feature validate` + fix installer wrapper

## Description

This task closes two compounding gaps:

1. **`FeatureLoader.validate_feature`** at
   `guardkit/orchestrator/feature_loader.py:747` checks task-file
   existence, orchestration completeness, dependency validity,
   intra-wave conflicts, and `task_type` — but **not** smoke-gate
   command paths.

2. **The installed shell wrapper** at `~/.agentecflow/bin/guardkit`
   does not expose the `feature` subcommand. Run-2 of TASK-REV-DEA8
   shows:
   ```
   ~/.agentecflow/bin/guardkit feature validate FEAT-DEA8 2>&1 | head -40
   Unknown command: feature
   Run 'guardkit help' for usage information
   ```
   The Python module exposes the command (`guardkit/cli/feature.py:223`),
   but the installer's shell wrapper does not register it. So `/feature-plan`
   Step 8.5 (which calls `guardkit feature validate FEAT-XXXX`) silently
   no-ops and the validation gap is invisible to the agent.

## Acceptance Criteria

### Validator extension

- [ ] `FeatureLoader.validate_feature` returns an additional class of
      structural error: `smoke_gates_path_error`, with payload
      `{path: str, available_roots: list[str], repo_root: str}`.
- [ ] Implementation reuses the shared `parse_positional_paths`
      helper from TASK-FPSG-002.
- [ ] Same validation rules as TASK-FPSG-002's `--validate-smoke-gates`
      mode — output messages must be **byte-identical** so the agent
      sees the same error whether invoked via `generate-feature-yaml
      --validate-smoke-gates` or `guardkit feature validate`.
- [ ] `guardkit/cli/feature.py:223` propagates the new error class
      into the existing `validate` output path. No change to exit-code
      semantics (any structural error → non-zero).

### Installer wrapper fix

- [ ] `~/.agentecflow/bin/guardkit feature --help` prints a usage line
      containing `validate` (and any other registered subcommands).
- [ ] `~/.agentecflow/bin/guardkit feature validate FEAT-AC1A` runs
      the same code path as `python -m guardkit feature validate
      FEAT-AC1A` (reaches `cli/feature.py`).
- [ ] Locate the wrapper-generation source — likely under
      `installer/core/templates/` or `installer/cli/` — and make sure
      the `feature` subcommand is registered alongside the existing
      ones (`autobuild`, `task`, `graphiti`, etc.).
- [ ] **Post-install smoke test** added to the installer test suite:
      after `guardkit init`/install, run `guardkit feature --help`
      and assert exit 0 + `validate` in stdout.

## Test Requirements

- [ ] Unit test
      `tests/unit/orchestrator/test_validate_feature_smoke_gates.py`:
      - tmp_path feature with bad smoke-gate path → validator returns
        a `smoke_gates_path_error`.
      - tmp_path feature with good paths → no errors of this class.
- [ ] CLI integration test running `guardkit feature validate` against
      a fixture YAML with bad path; asserts non-zero exit + identical
      message to TASK-FPSG-002's `--validate-smoke-gates`.
- [ ] Installer post-install smoke test (see above).

## Implementation Notes

- The wrapper fix is install-time plumbing and may benefit from
  landing in a separate worktree from the validator extension. They
  share a goal but no code.
- Look for how other recently-added subcommands (e.g. `graphiti`)
  are registered — copy that pattern.
- If the wrapper is generated at `init` time from a template, the fix
  may also need a re-init or `guardkit init --extend` migration path
  for users who already installed.
- Surface the wrapper gap as a release note — users on the broken
  wrapper version will need to re-run install.

## Files

- `guardkit/orchestrator/feature_loader.py` — add `_validate_smoke_gates_paths`
- `guardkit/cli/feature.py` — surface the new error class
- Installer wrapper source (TBD — locate during exploration)
- `tests/unit/orchestrator/test_validate_feature_smoke_gates.py` — new
- `tests/integration/cli/test_feature_validate_smoke_gates.py` — new
- Installer post-install smoke test — new

## Implementation Notes (2026-05-02)

### Validator extension

- Added `validate_paths: bool = True` kwarg to `FeatureLoader.load_feature`
  and `_parse_feature`. Default preserves the existing L4 raise behaviour
  (TASK-FPSG-005); CLI `validate` passes `False` so the L4 pre-flight is
  skipped and `validate_feature` aggregates the path error alongside other
  structural errors.
- Added `FeatureLoader._validate_smoke_gate_paths_for_validate(feature, repo_root)`
  — collect-without-raising sibling of `_validate_smoke_gates_paths`. Uses
  the shared `format_smoke_gate_path_error` formatter so the error wording
  is byte-identical with L3b and L4. Wired into `validate_feature` after
  the `task_type` checks.
- `cli/feature.py validate` now calls `load_feature(..., validate_paths=False)`.
  The smoke-gate path error then flows through the existing `structural_errors`
  pipeline. Smoke-gate path errors are emitted via `click.echo` (verbatim)
  rather than `console.print` so Rich's word-wrap doesn't break byte-identicalness
  with the L3b stderr output.

### Installer wrapper

- Added `feature)` case arm to the `cat > "$INSTALL_DIR/bin/guardkit" <<
  'EOF'` heredoc inside `installer/scripts/install.sh`. Mirrors the
  `autobuild)` and `graphiti)` arms — locates `guardkit-py`, then
  `exec "$GUARDKIT_PY" feature "$@"`. Updated the wrapper's `print_help`
  block to advertise the new subcommand and the `feature validate
  FEAT-XXXX` example.
- Users who installed before this change ship a wrapper without the arm.
  They need to re-run `./installer/scripts/install.sh` to pick it up.
  Surfacing as a release note is recommended.

### Tests

- `tests/unit/orchestrator/test_validate_feature_smoke_gates.py` (7 tests):
  pins the `validate_feature` smoke-gate AC scenarios, byte-identical
  formatter output, multi-line block scalars, multi-positional pytest
  invocations.
- `tests/integration/cli/test_feature_validate_smoke_gates.py` (5 tests):
  drives the click CLI directly via `CliRunner`; covers exit-code,
  human-mode output, byte-identical formatter content, JSON-mode payload.
- `tests/unit/installer/test_install_wrapper_feature_subcommand.py` (4 tests):
  asserts the heredoc in `install.sh` contains the `feature)` arm,
  the `exec "$GUARDKIT_PY" feature "$@"` delegation, and the help-text
  advertisement. End-to-end post-install testing (running the installer
  in a sandboxed `$HOME`) is out of scope — content equivalence is the
  no-side-effects contract.

### Known issue (out of scope)

- `tests/rules/test_no_dead_task_id_references.py` flags
  `feature_loader.py:484 TASK-REV-DEA8`. This reference predates this task
  (introduced in commit `0bc25929` for TASK-FPSG-005) and was failing on
  `main` before TASK-FPSG-004 started. The reference points at a task in
  the upstream `appmilla_github/forge` repo, not in guardkit's `tasks/`,
  so the rule lint correctly flags it from guardkit's POV. Fix is a
  separate task — either rename to a placeholder or relax the rule for
  cross-repo `parent_review` references.
