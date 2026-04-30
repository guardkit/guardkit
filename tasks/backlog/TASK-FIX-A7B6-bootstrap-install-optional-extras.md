---
id: TASK-FIX-A7B6
title: Make environment_bootstrap install configurable optional-dependency extras
status: backlog
task_type: feature
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
priority: medium
complexity: 4
dependencies: []
external_reference:
  source_repo: appmilla_github/study-tutor
  reports:
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-report.md
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md
  related_sibling_task: TASK-FIX-AB7A-001b (per-feature workaround in sibling repo's smoke-gate command)
related_features: [autobuild, bootstrap-venv]
tags: [autobuild, bootstrap, environment, dependency-management, dev-extras, smoke-gate]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Make environment_bootstrap install configurable optional-dependency extras

## Description

`guardkit/orchestrator/environment_bootstrap.py` runs `pip install -e .`
against pyproject.toml manifests but does not install optional-dependency
extras. This is fine for projects whose runtime dependencies fully cover
the test surface, but it breaks any project whose smoke gate or BDD oracle
invokes `pytest` from the worktree venv: `pytest` itself is conventionally
declared as a `[dev]` (or `[test]`) optional-dependency extra, not a
runtime dep.

In the sibling study-tutor repo, FEAT-70A4's smoke gate runs
`pytest tests/unit/knowledge/` after each wave. The bootstrap created
`.guardkit/venv` and editable-installed `study-tutor` correctly, but
`pytest` was missing because the project's
`[project.optional-dependencies] dev = ["pytest>=9.0.2", ...]` group was
never installed. Coach gates passed because Coach uses
`sys.executable -m pytest` (the GuardKit-side interpreter, which has
pytest available), but the smoke gate runs in a separate `shell=True`
subprocess and has no path to that interpreter.

The local workaround (sibling task `TASK-FIX-AB7A-001b`) prepends
`pip install -e ".[dev]"` to the smoke-gate command — fast and
idempotent, but not portable across projects. The right upstream fix is
to let projects opt into extras at bootstrap time so the worktree venv
arrives with everything its quality gates need.

## Cross-reference

- TASK-FIX-A7B1 fixed the smoke-gate's PATH (so a bare `python` in the
  command resolves to the bootstrap venv interpreter); A7B6 fixes the
  smoke-gate's _environment_ (so `pytest` is actually present inside that
  interpreter). Together the two fully resolve the
  smoke-gate-blocked-autobuild class of failure.
- Diagnostic: `<sibling>/.claude/reviews/TASK-REV-AB7A-report.md` §1
  ("Smoke-gate venv miss") and the corresponding section in
  `…-addendum-source-traced.md` for the line-level trace through
  `environment_bootstrap.py`.
- Sibling workaround: `TASK-FIX-AB7A-001b` prepends
  `pip install -e ".[dev]"` to the feature YAML's smoke-gate command;
  works locally but every project would have to repeat the trick.

## Scope

- Add `bootstrap_extras: List[str]` to the `.guardkit/config.yaml`
  schema (default `[]`).
- When non-empty, `environment_bootstrap.py` runs
  `pip install -e ".[<extras>]"` instead of plain `pip install -e .`.
- Optionally surface the same setting at feature granularity:
  `<feature>.yaml: bootstrap.extras: [dev]` overrides the global default
  for that feature only.
- Document the choice in the `.guardkit/config.yaml` schema docs; the
  guidance for any project whose smoke gates reference `pytest` is to
  configure `bootstrap_extras: [dev]` (or whichever extras group owns
  the test deps).

## Acceptance Criteria

- [ ] AC-001: A project with `bootstrap_extras: [dev]` in
      `.guardkit/config.yaml` and a `[dev]` group in pyproject.toml gets
      `pytest` (and the rest of the `[dev]` group) installed into the
      worktree venv automatically by `environment_bootstrap`.
- [ ] AC-002: Backward compatible — existing projects without the
      `bootstrap_extras` key continue to get the current
      `pip install -e .` behaviour with no functional change.
- [ ] AC-003: A feature YAML can declare `bootstrap.extras: [...]` and
      that list overrides the global `bootstrap_extras` for that feature
      only.
- [ ] AC-004: Smoke gates that run `<venv>/bin/python -m pytest …`
      succeed without per-feature workarounds in projects that opt in.
- [ ] AC-005: Schema documentation updated to describe
      `bootstrap_extras` and the feature-level `bootstrap.extras`
      override.
- [ ] AC-006: Regression coverage for both the opted-in install path
      (extras present in venv) and the opted-out default path (no
      behaviour change vs. today).

## Files Likely To Change

- `guardkit/orchestrator/environment_bootstrap.py` — extend the editable
  install command to honour `bootstrap_extras`.
- `.guardkit/config.yaml` schema and validator — add the new key with
  default `[]`.
- Feature-YAML schema/loader — accept optional `bootstrap.extras` block
  and plumb through to the bootstrap call site.
- Schema docs (wherever `.guardkit/config.yaml` is documented).
- Test additions under `tests/orchestrator/` — both the extras-honoured
  install and the no-config backward-compat path.

## Out Of Scope

- Auto-detecting which extras group holds test deps — projects opt in
  explicitly.
- Non-pip / non-pyproject toolchains (poetry-only, hatch-only, uv-only
  flows beyond what `pip install -e .[…]` already handles).
- Reworking the bootstrap venv path itself (keep `.guardkit/venv/`).
