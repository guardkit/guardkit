---
id: TASK-FPSG-002
title: "generate-feature-yaml --validate-smoke-gates mode + /feature-plan Step 8.6 (L3b)"
status: backlog
created: 2026-05-02T13:30:00Z
priority: high
task_type: enhancement
implementation_mode: task-work
tags:
  - generate-feature-yaml
  - feature-plan
  - smoke-gate
  - validator
  - cross-repo-followup
  - feature-plan-smoke-gate-validation
complexity: 5
estimated_minutes: 120
parent_review: appmilla_github/forge/TASK-REV-DEA8
parent_feature: feature-plan-smoke-gate-validation
wave: 2
dependencies: []  # depends on the shared pytest-argv parser landing in Wave 1; treat as soft dep — implement parser as part of this task if Wave 1 hasn't landed yet
---

# Task: `generate-feature-yaml --validate-smoke-gates` + `/feature-plan` Step 8.6

## Description

`/feature-plan`'s smoke-gate emission flow has a structural gap:

1. `generate-feature-yaml --discover` runs (it has filesystem access —
   it discovers task files at `generate_feature_yaml.py:379` via
   `if not full_path.exists(): ...`).
2. The script does **not** auto-emit `smoke_gates` (deliberate —
   `feature-plan.md:2312-2314`).
3. `smoke_gates_nudge` prints a banner asking the agent to add the
   block manually.
4. The agent edits the YAML to inject `smoke_gates`.
5. **Nothing then validates the hand-injected paths.**

This task adds a `--validate-smoke-gates` mode to `generate-feature-yaml`
and a new Step 8.6 in `feature-plan.md` that runs it.

## Acceptance Criteria

- [ ] **New mode** in
      `installer/core/commands/lib/generate_feature_yaml.py`:
      `--validate-smoke-gates --feature-id FEAT-XXXX`.
      - Loads `.guardkit/features/FEAT-XXXX.yaml`.
      - If `smoke_gates.command` is absent → exit 0 (nothing to check).
      - If present → parse positional pytest argv from `command`,
        resolve each path against the target repo root.
      - Any missing path → exit non-zero with a clear message:
        ```
        ❌ smoke_gates.command references non-existent path(s):
             tests/cli   (target repo: /Users/.../forge)
           Available test roots: tests/forge, tests/integration, tests/unit, tests/bdd, tests/dockerfile, tests/hardening
        ```
      - All paths exist → exit 0 with `✓ smoke_gates.command paths OK`.
- [ ] **Shared parser** — `parse_positional_paths(command: str) -> list[str]`
      lives in a single module (suggest: `guardkit/lib/pytest_argv.py`)
      and is imported by this task, TASK-FPSG-004 (L3d), and
      TASK-FPSG-005 (L4).
- [ ] **Parser handles**:
      - `set -e\npytest tests/foo -x` (multi-line block scalar)
      - `pytest -x tests/foo` (flag before positional)
      - `pytest tests/foo -- --junit-xml=out.xml` (positional after `--`)
      - `pytest tests/foo tests/bar -k "..."` (multiple positionals)
      - Non-pytest commands (e.g. `python3 .guardkit/smoke/foo.py`) →
        returns `[]`; validator exits 0.
- [ ] **`/feature-plan.md` Step 8.6 added** between existing Steps 8
      and 8.5:
      ```
      8.6. Validate hand-injected smoke_gates (run only if smoke_gates
           was added to the feature YAML after generate-feature-yaml ran).
           Execute: python3 ~/.agentecflow/bin/generate-feature-yaml \
                    --validate-smoke-gates --feature-id FEAT-XXXX
           - Non-zero exit → display the validator's message inline;
             the agent must fix the YAML before proceeding.
           - Zero exit → continue.
      ```
- [ ] **Honours `--quiet`** — same suppression rules as the existing
      AC-quality / BDD-oracle / smoke-gates nudges.

## Test Requirements

- [ ] Unit test
      `tests/unit/commands/test_generate_feature_yaml_smoke_gate_validation.py`:
      - tmp_path repo with `tests/forge/` only (no `tests/cli/`).
      - Fixture YAML with bad path → validator exit non-zero,
        message includes both the bad path and the discovered roots.
      - Fixture YAML with good paths → validator exit 0.
      - Fixture YAML with no `smoke_gates` → validator exit 0.
      - Fixture YAML with non-pytest command → validator exit 0.
- [ ] Unit test for `parse_positional_paths` covering the parser
      cases listed under Acceptance Criteria.
- [ ] Integration test: end-to-end `/feature-plan` flow against a
      fixture repo, smoke_gates manually injected with bad path,
      Step 8.6 surfaces the error.

## Implementation Notes

- The `discover_test_roots(repo_root)` helper used by L3c can be
  reused here for the "Available test roots" section of the error
  message.
- Use `Path.exists()` and resolve relative to `cwd=repo_root`. Do NOT
  walk a worktree — the YAML's repo root is the source of truth.
- Error message must include the repo root path explicitly so the
  agent can disambiguate worktree vs. main repo if the same path
  exists in one but not the other.

## Files

- `installer/core/commands/lib/generate_feature_yaml.py` — add mode
- `guardkit/lib/pytest_argv.py` (or similar) — shared parser
- `installer/core/commands/feature-plan.md` — add Step 8.6
- `tests/unit/commands/test_generate_feature_yaml_smoke_gate_validation.py` — new
- `tests/unit/lib/test_pytest_argv_parser.py` — new
