---
id: TASK-TPL-005
title: "Unit tests for resolver, loader, selector, and graceful degradation"
task_type: testing
parent_review: TASK-REV-B3F7
feature_id: FEAT-TPL-PLAYER
wave: 4
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-TPL-002
  - TASK-TPL-003
status: backlog
---

# Unit tests for template pattern loader

## Scope

Create `tests/unit/test_template_pattern_loader.py` with test classes:

### `TestResolverReuse`
- Verifies `guardkit.templates.resolver.resolve_template_source_dir` resolves `fastapi-python` to `installer/core/templates/fastapi-python`.
- Unknown template returns `None` (no exception).

### `TestLoader`
- Valid `.claude/manifest.json` with `name: "fastapi-python"` populates `template_name`, `template_dir`, and `available_files` with > 10 files.
- Missing manifest file → `template_name is None`, warning recorded, no exception.
- Invalid JSON → same graceful-degradation path.
- Manifest without `name` field → same graceful-degradation path.
- Template whose `templates/` subdirectory does not exist (e.g. `default` template) → `available_files == []` with warning.

### `TestSelector`
- File-path hint `["app/api/users.py"]` + fastapi-python available files → selects `templates/api/router.py.template`.
- File-path hint `["app/crud/users.py"]` → selects from `templates/crud/`.
- Empty hints + `tech_stack="Python"` → alphabetical first-3 fallback.
- `max_files=5` hard cap respected when > 5 matches exist.
- `max_tokens=500` cap causes oversize files to be skipped with a warning.
- Selector does not mutate `available_files`.

### `TestGracefulDegradation`
- End-to-end: call `load_template_patterns` + `select_patterns` on a project with no manifest; confirm returned context has `template_name is None` and `selected_files == []`.

## Acceptance Criteria

1. All test classes above exist and pass.
2. Line coverage for `guardkit/knowledge/template_pattern_loader.py` ≥ 80%.
3. Branch coverage ≥ 75%.
4. Seam tests from TASK-TPL-003 and TASK-TPL-004 are included and pass in this suite (or in a sibling `test_template_pattern_seams.py`).
5. All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

- `pytest tests/unit/test_template_pattern_loader.py --cov=guardkit.knowledge.template_pattern_loader --cov-report=term-missing`
- Coverage thresholds met.
