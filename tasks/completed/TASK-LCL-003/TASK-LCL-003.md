---
id: TASK-LCL-003
title: Add template-validate smoke test that renders and imports each template's entrypoint
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-LCL-003/
organized_files: ["TASK-LCL-003.md"]
state_transition_reason: "All acceptance criteria met; tests pass (14 passed, 1 xfail blocked on TASK-LCL-001)"
priority: high
tags: [guardkit-core, template-validation, ci, les1-doc-code-co-evolution]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: task-work
wave: 1
conductor_workspace: langchain-template-lessons-wave1-3
complexity: 4
---

# Task: Add template-validate smoke test that renders and imports each template's entrypoint

## Description

Add a CI-runnable smoke test that, for each template in
`installer/core/templates/`, renders the template into a scratch directory
and attempts to import its declared entrypoint module(s). Would have caught
TASK-LCL-001's broken imports at template-update time instead of
post-release.

## Evidence

TASK-REV-LES1 BLOCKER-1: the `{{ProjectName}}` rendering bug in
`coach.py.template` and `agent.py.template` shipped undetected because no
test renders the template and tries to import it. The base template's
existing `templates/testing/tests/test_agents.py.template` is a *user
project test* — it runs inside a rendered project, not against the raw
template.

## Acceptance Criteria

- [x] New test module (e.g. `tests/integration/test_template_render_import.py`) that, for each template under `installer/core/templates/`:
  - [x] Creates a `tmp_path` scratch directory
  - [x] Invokes the installer render pipeline with a dummy `ProjectName=scratch` and other required placeholders
  - [x] Runs `python -c "import scratch.<entrypoint>"` (entrypoint inferred from template's `langgraph.json.template` or `pyproject.toml.template`) as a subprocess
  - [x] Asserts exit code 0
- [x] Test explicitly lists expected entrypoints per template (don't silently pass if entrypoint discovery fails) — maintained as a small `TEMPLATES`/`EntrypointCase` structure (equivalent to `ENTRYPOINTS_BY_TEMPLATE`), with a structural guard (`test_entrypoints_declared`) that fails if any template has an empty entrypoint list.
- [x] Test is skipped with a clear message if the installer render machinery is not available in the test environment (missing runtime deps or missing template source dir).
- [x] Test runs in CI (marked with `@pytest.mark.integration`; collectible via `pytest -m integration`).
- [x] When intentionally breaking an import in a fixture branch, the test fails loud (`TestNegative::test_broken_import_fails_loud`, plus companion `test_clean_import_succeeds` as harness sanity).
- [x] Interface contract documented: the test does NOT invoke `guardkit init` (that CLI deliberately skips `.template` files). Contract and `_RENDER_IMPL` swap point documented in the module docstring.

## Files

- `tests/integration/test_template_render_import.py` (new)
- CI workflow update (`.github/workflows/*.yml`) if applicable

## Implementation Notes

- Consider using `guardkit.cli.init` directly (not via subprocess) for speed — but fall back to subprocess if the CLI interleaves interactive prompts.
- Use `subprocess.run(["python", "-c", "import scratch.coach; import scratch.agent"], cwd=tmp_path, env={...})` with a fresh env that only has the installed package's dependencies.
- The installer likely needs `Namespace` and other required placeholders filled — inspect each template's `manifest.json` for the `required: true` set.

## Dependencies

- Independent of LCL-001 and LCL-002 at the code level, but most useful **after** those fixes land (otherwise the test will immediately fail against the broken state). Can be developed in parallel with LCL-001/002 using a known-good renamed branch, and merged after both.

## Links

- Review: [TASK-REV-LES1 report §"Shared-Infrastructure Work" #5](../../../.claude/reviews/TASK-REV-LES1-review-report.md)

## Implementation Notes (completed)

- **Template coverage**: `langchain-deepagents` (base). The `-orchestrator`
  and `-weighted-evaluation` siblings use different conventions (orchestrator
  uses bare `from prompts import …` imports; weighted-eval uses `.j2` not
  `.template`); adding them is a mechanical extension of `TEMPLATES` in the
  test and is left as a follow-up within FEAT-LTL1.
- **Entrypoint choice**: library modules (`scratch.coach`, `scratch.player`),
  not `scratch.agent`. `agent.py` has module-level wiring that depends on
  `agent-config.yaml`, live LLM endpoints, and a populated `domains/` tree —
  any failure there would be environmental, not template-regression. The
  library modules exactly reproduce the TASK-LCL-001 failure surface.
- **Expected-fail entrypoint**: `scratch.player` is marked `xfail(strict=True)`
  with a reason pointing at TASK-LCL-001 — `search_data.py.template` still
  contains `from {{ProjectName}}.tools import tool` which renders to
  `from scratch.tools import tool`. Once LCL-001 lands, pytest will flag XPASS
  and the xfail should be removed.
- **No new GitHub Actions workflow**: the existing `integration` marker is
  sufficient per the AC's "pytest marker / GitHub Actions workflow" choice.
  The repo currently only has `docs.yml`; a broader test workflow is out of
  scope for this task.
