---
complexity: 5
consumer_context:
- consumes: TemplatePatternContext
  driver: direct attribute access
  format_note: 'Reads `available_files: List[Path]` from context; populates `selected_files:
    List[Path]` in-place (or returns a new context). Must not mutate other fields.'
  framework: stdlib dataclass
  task: TASK-TPL-002
dependencies:
- TASK-TPL-002
feature_id: FEAT-TPL-PLAYER
id: TASK-TPL-003
implementation_mode: task-work
parent_review: TASK-REV-B3F7
status: design_approved
task_type: feature
title: Domain-hint selector with tech_stack + file-path matching
wave: 3
---

# Domain-hint selector

## Context

The Player does not have a `domain_tags` field on tasks (review finding F3). The selector must derive the "what subdirectories does this task care about?" signal from what already exists: `TaskCharacteristics.tech_stack` ([guardkit/knowledge/task_analyzer.py:146](../../../guardkit/knowledge/task_analyzer.py#L146)) and the task's modified/target file paths.

## Scope

Extend `guardkit/knowledge/template_pattern_loader.py` with:

```python
def select_patterns(
    context: TemplatePatternContext,
    tech_stack: str,
    file_path_hints: List[str],
    max_files: int = 5,
    max_tokens: int = 3000,
) -> TemplatePatternContext:
    ...
```

Selection rules (in priority order):

1. **File-path hints take precedence.** For each hint (e.g. `app/api/users.py`), match path segments against template subdirectory names. Segment `api` matches `<templates>/api/`. Collect all `.template` files from matched subdirs.
2. **Tech-stack fallback.** If file-path hints produced zero matches, fall back to tech_stack keyword matching against subdirectory names.
3. **Alphabetical fallback (spec §7).** If still nothing, take the first 3 `.template` files alphabetically.
4. **Cap enforcement.** Truncate to `max_files` (default 5). Compute rough token count (`len(content) / 4`); stop adding files once `max_tokens` reached. Record skipped files as warnings.
5. Populate `selected_files` and append any skip-reasons to `warnings`.

## Acceptance Criteria

1. File-path hint `["app/api/users.py"]` on the fastapi-python template selects `templates/api/router.py.template`.
2. Empty file-path hints + `tech_stack="Python"` falls back to tech-stack path; empty still → alphabetical-3.
3. Hard cap: never returns more than 5 files regardless of matches.
4. Token cap: measured oversize files are skipped with a warning recorded.
5. Selection does not mutate `available_files`.
6. All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

- `pytest tests/unit/test_template_pattern_loader.py::TestSelector -v` (from TASK-TPL-005)
- Seam test `test_template_pattern_context_contract` passes.

## Seam Tests

The following seam test validates the `TemplatePatternContext` integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify TemplatePatternContext contract from TASK-TPL-002."""
import pytest
from pathlib import Path

from guardkit.knowledge.template_pattern_loader import (
    TemplatePatternContext,
    select_patterns,
)


@pytest.mark.seam
@pytest.mark.integration_contract("TemplatePatternContext")
def test_template_pattern_context_contract():
    """Verify TemplatePatternContext contract from TASK-TPL-002.

    Contract: consumer reads `available_files: List[Path]` and populates
    `selected_files: List[Path]` without mutating other fields.
    Producer: TASK-TPL-002 (load_template_patterns)
    """
    ctx = TemplatePatternContext(
        template_name="fastapi-python",
        template_dir=Path("/tmp/fake"),
        available_files=[Path("a.template"), Path("b.template"), Path("c.template")],
        selected_files=[],
        prompt_block="",
        warnings=[],
    )

    # Consumer side: verify contract invariants
    assert hasattr(ctx, "available_files"), "context must expose available_files"
    assert isinstance(ctx.available_files, list), "available_files must be List[Path]"
    assert all(isinstance(f, Path) for f in ctx.available_files), \
        "available_files entries must be Path instances"
    assert ctx.selected_files == [], "selected_files starts empty for selector consumption"

    result = select_patterns(ctx, tech_stack="Python", file_path_hints=[])
    assert len(result.selected_files) <= 5, "must respect max_files cap"
    assert result.available_files == ctx.available_files, \
        "selector must not mutate available_files"
```