---
complexity: 5
dependencies:
- TASK-TPL-004
- TASK-TPL-005
feature_id: FEAT-TPL-PLAYER
id: TASK-TPL-006
implementation_mode: task-work
parent_review: TASK-REV-B3F7
status: design_approved
task_type: testing
title: 'Integration test: AutoBuild context loading with template pattern block'
wave: 5
---

# Integration test: end-to-end pattern injection

## Context

Validate that a full `get_player_context()` call, against a fixture project initialised from `fastapi-python`, produces an `AutoBuildContextResult.prompt_text` containing the labelled pattern block and that the regression path (no manifest) still produces identical output to pre-feature behaviour.

## Scope

Extend `tests/unit/test_autobuild_thread_loaders.py` (or create `tests/unit/test_autobuild_template_patterns_integration.py`) with:

1. **Fixture setup**: create a temp project with `.claude/manifest.json` containing `{"name": "fastapi-python"}`. Point the resolver at `installer/core/templates/fastapi-python`.
2. **Positive test**: call `AutoBuildContextLoader.get_player_context()` with a synthetic task that targets `app/api/users.py` and `tech_stack="Python"`. Assert:
   - `result.prompt_text` contains `"Stack Pattern Reference (from fastapi-python template)"`.
   - `result.prompt_text` contains `"### api/router.py.template"`.
   - Log output lists selected files.
3. **Regression test**: same call with no manifest file. Assert `result.prompt_text` does NOT contain `"Stack Pattern Reference"` and matches the pre-feature golden output (snapshot) for any other content.
4. **Token-cap test**: construct a task against a template with > 5 matching subdirs; assert exactly 5 files appear in the block.
5. **Cross-template test**: repeat the positive test against `dotnet-railway-fastendpoints` to verify template-agnostic behaviour.

## Acceptance Criteria

1. All integration tests listed above pass.
2. Seam tests from TASK-TPL-002, TASK-TPL-003, TASK-TPL-004 all pass in the same pytest run.
3. No regression in any existing `test_autobuild_*.py` test.
4. Integration test runs in under 5 seconds (no real AutoBuild orchestration — just context loader).
5. All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

- `pytest tests/unit/test_autobuild_*.py tests/unit/test_template_pattern_loader.py -v`
- No regressions; all new tests pass.