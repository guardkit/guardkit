---
id: TASK-TPL-001
title: "Extract template resolver into shared module"
task_type: refactor
parent_review: TASK-REV-B3F7
feature_id: FEAT-TPL-PLAYER
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
status: backlog
---

# Extract template resolver into shared module

## Context

`_resolve_template_source_dir()` currently lives at [guardkit/cli/init.py:485](../../../guardkit/cli/init.py#L485) and is CLI-private. The upcoming AutoBuild template-pattern loader (TASK-TPL-002) needs the same resolution logic at build time. Rather than duplicate, extract it into a shared neutral module.

## Scope

Move the resolver (and its supporting `_get_templates_base_dir()` / `_get_user_templates_dir()` helpers if appropriate) to `guardkit/templates/resolver.py`. Re-export from `guardkit/cli/init.py` to preserve the existing import surface.

## Acceptance Criteria

1. New module `guardkit/templates/resolver.py` exposes `resolve_template_source_dir(template_name: str) -> Optional[Path]` with identical behaviour to the current private function.
2. `guardkit/cli/init.py` imports from the new module; existing call sites inside `init.py` route through the new public name.
3. All existing `guardkit init` tests pass unchanged.
4. No behavioural change — this is a pure extract-and-rename.
5. All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

- `pytest tests/unit/test_cli_init*.py -v`
- Confirm `from guardkit.templates.resolver import resolve_template_source_dir` succeeds.
- Confirm lint passes on modified files.

## Notes

Keep the function signature stable. If `_get_templates_base_dir()` is also moved, update the docstring to state the resolution order (package templates first, user templates fallback).
