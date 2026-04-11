---
complexity: 5
consumer_context:
- consumes: MANIFEST_NAME
  driver: Path.read_text + json.loads
  format_note: .claude/manifest.json must contain a top-level `name` field (str) identifying
    the source template; graceful degrade if file missing, unreadable, or field absent
  framework: stdlib json
  task: guardkit init (existing)
dependencies:
- TASK-TPL-001
feature_id: FEAT-TPL-PLAYER
id: TASK-TPL-002
implementation_mode: task-work
parent_review: TASK-REV-B3F7
status: design_approved
task_type: feature
title: Template pattern loader core + TemplatePatternContext
wave: 2
---

# Template pattern loader core

## Context

Introduce the build-time loader that resolves a project's source template and returns a `TemplatePatternContext` dataclass. This is the producer module for the `TemplatePatternContext` integration contract (see §4 in the feature guide) and will be consumed by the selector (TASK-TPL-003) and the wiring task (TASK-TPL-004).

## Scope

Create `guardkit/knowledge/template_pattern_loader.py` with:

1. `TemplatePatternContext` dataclass:
   ```python
   @dataclass
   class TemplatePatternContext:
       template_name: Optional[str]      # None if unresolved
       template_dir: Optional[Path]       # templates/ subdirectory path
       available_files: List[Path]        # all .template files found
       selected_files: List[Path]         # populated by selector (TASK-TPL-003)
       prompt_block: str                  # formatted for injection (populated by wiring)
       warnings: List[str]                # graceful-degradation messages
   ```
2. `load_template_patterns(manifest_path: Path) -> TemplatePatternContext`:
   - Reads `.claude/manifest.json`
   - Extracts `name` field (NOT `template`) — per review finding F1
   - Resolves template dir via `resolve_template_source_dir()` from TASK-TPL-001
   - Populates `available_files` with all `.template` files under `<template_dir>/templates/`
   - On any failure (missing file, invalid JSON, unknown template, no templates/ subdir): returns a `TemplatePatternContext` with `template_name=None` and a descriptive warning — never raises.

The selector and prompt formatting live in TASK-TPL-003 and TASK-TPL-004 respectively — this task only produces the raw context.

## Acceptance Criteria

1. Module `guardkit/knowledge/template_pattern_loader.py` exists with the dataclass and loader function.
2. Loader reads the `name` field from `.claude/manifest.json` (confirmed to be the actual field per review F1).
3. Missing manifest → returns `TemplatePatternContext(template_name=None, ...)` with a warning; does not raise.
4. Unresolvable template name → same graceful-degradation behaviour.
5. For a valid `fastapi-python` project, `available_files` contains all 13 `.template` files under `installer/core/templates/fastapi-python/templates/`.
6. All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

- `pytest tests/unit/test_template_pattern_loader.py::TestLoader -v` (unit tests from TASK-TPL-005 cover this)
- Manual smoke: instantiate with a real fastapi-python manifest and confirm file count > 10.
- Confirm graceful degradation: run with a non-existent manifest path; must not raise.

## Seam Tests

The following seam test validates the integration contract with the producer (`guardkit init`). Implement this test to verify the boundary before integration.

```python
"""Seam test: verify MANIFEST_NAME contract from guardkit init."""
import json
from pathlib import Path
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("MANIFEST_NAME")
def test_manifest_name_format(tmp_path):
    """Verify .claude/manifest.json name field matches the expected contract.

    Contract: .claude/manifest.json must contain a top-level `name` field (str)
    identifying the source template.
    Producer: guardkit init (existing CLI command)
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    manifest_path = claude_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"name": "fastapi-python", "schema_version": "1.0.0"}))

    # Consumer side: load and verify field presence + type
    data = json.loads(manifest_path.read_text())
    assert "name" in data, "manifest.json must contain a `name` field"
    assert isinstance(data["name"], str) and data["name"], \
        f"manifest name must be non-empty str, got: {data.get('name')!r}"
```