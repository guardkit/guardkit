---
id: TASK-TPL-004
title: "Wire pattern loader into AutoBuildContextLoader + logging"
task_type: feature
parent_review: TASK-REV-B3F7
feature_id: FEAT-TPL-PLAYER
wave: 4
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-TPL-003
status: backlog
consumer_context:
  - task: TASK-TPL-002
    consumes: TemplatePatternContext
    framework: "stdlib dataclass"
    driver: "direct attribute access"
    format_note: "Reads `selected_files` + template dir, formats each file's content into a markdown code block, assigns to `prompt_block`, and appends `prompt_block` to AutoBuildContextResult.prompt_text."
---

# Wire pattern loader into AutoBuildContextLoader

## Context

The integration point identified in the review: [`AutoBuildContextLoader.get_player_context()`](../../../guardkit/knowledge/autobuild_context_loader.py) returns `AutoBuildContextResult` with a formatted `prompt_text` field. We append the template-pattern block to that string so it flows through the existing context pipeline (per decision D4).

## Scope

1. In `guardkit/knowledge/autobuild_context_loader.py`:
   - After existing context retrieval, call `load_template_patterns()` with the resolved project manifest path (`.claude/manifest.json` relative to the project root).
   - Extract `tech_stack` from `TaskCharacteristics` and file-path hints from the task's modified-files list.
   - Call `select_patterns(context, tech_stack, file_path_hints)`.
   - Format `selected_files` into a markdown block (the existing `TemplatePatternContext.prompt_block` field):
     ```
     ## Stack Pattern Reference (from {template_name} template)
     The following template files show the canonical patterns for this
     project's architecture. Use these as reference when generating code.

     ### api/router.py.template
     ```python
     {file contents}
     ```
     ...
     ```
   - Append `prompt_block` to `AutoBuildContextResult.prompt_text`.
2. Logging: emit an info log listing selected files and the total token estimate. For skipped files, log the reason at debug level. Log graceful-degradation warnings at warning level.
3. If `TemplatePatternContext.template_name is None`, skip the append silently (graceful degradation per US-3) — only log at debug level.

## Acceptance Criteria

1. `AutoBuildContextResult.prompt_text` contains the pattern block when the project is initialised from a known template.
2. For projects with no `.claude/manifest.json`, `prompt_text` is identical to pre-change behaviour (regression-free — verified by existing AutoBuild tests).
3. Log output (captured in tests) lists selected file names and token estimate.
4. The wiring does not alter the signature of `get_player_context()`; all existing callers remain compatible.
5. All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

- `pytest tests/unit/test_autobuild_thread_loaders.py -v` (regression)
- `pytest tests/unit/test_template_pattern_loader.py::TestWiring -v` (new integration coverage)
- Manual: run an AutoBuild turn on a fastapi-python fixture and inspect the logged context payload for the pattern block.

## Seam Tests

The following seam test validates the `TemplatePatternContext` → prompt_text contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify TemplatePatternContext → prompt_text contract."""
import pytest
from pathlib import Path

from guardkit.knowledge.template_pattern_loader import TemplatePatternContext


@pytest.mark.seam
@pytest.mark.integration_contract("TemplatePatternContext")
def test_template_pattern_prompt_block_contract():
    """Verify the wiring contract for prompt_block injection.

    Contract: consumer (wiring) reads `selected_files` + produces `prompt_block`,
    which must be a non-empty str when selected_files is non-empty.
    Producer: TASK-TPL-002/003 (loader + selector)
    """
    ctx = TemplatePatternContext(
        template_name="fastapi-python",
        template_dir=Path("/tmp/fake/templates"),
        available_files=[Path("api/router.py.template")],
        selected_files=[Path("api/router.py.template")],
        prompt_block="",
        warnings=[],
    )

    # Simulate wiring formatter (production code in autobuild_context_loader)
    from guardkit.knowledge.autobuild_context_loader import format_pattern_block
    block = format_pattern_block(ctx, file_contents={Path("api/router.py.template"): "stub"})

    assert isinstance(block, str), "prompt_block must be a string"
    assert "Stack Pattern Reference" in block, \
        "prompt_block must carry the labelled header per spec §6"
    assert "fastapi-python" in block, "prompt_block must name the source template"
```
