---
id: TASK-YSC-002
title: Create Pydantic schema models for feature YAML validation
status: backlog
created: 2026-02-14T00:00:00Z
priority: high
tags: [schema, pydantic, feature-loader, validation]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: task-work
wave: 1
complexity: 6
depends_on: []
---

# Task: Create Pydantic schema models for feature YAML validation

## Description

Replace the current `FeatureTask`, `FeatureOrchestration`, `FeatureExecution`, and `Feature` dataclasses in `guardkit/orchestrator/feature_loader.py` with Pydantic v2 models that enforce type validation at parse time.

The current dataclasses use `Literal` type hints that Python does not enforce at runtime, allowing invalid values like `status: backlog` to be silently accepted. Pydantic models enforce these constraints.

## Acceptance Criteria

- [ ] `FeatureTask` is a Pydantic `BaseModel` with `Literal` type enforcement
- [ ] `Feature` is a Pydantic `BaseModel` with strict field validation
- [ ] `model_config = ConfigDict(extra="warn")` logs warnings for unknown fields (not "forbid" to avoid breaking existing YAMLs immediately)
- [ ] Invalid `status` values (e.g., `backlog`) raise `ValidationError` at parse time
- [ ] Invalid `implementation_mode` values raise `ValidationError` at parse time
- [ ] `FeatureLoader._parse_task()` and `_parse_feature()` use `model_validate()` instead of manual `.get()` calls
- [ ] `FeatureLoader.save_feature()` uses `model_dump()` for serialization
- [ ] JSON Schema can be exported via `Feature.model_json_schema()` for AI prompt inclusion
- [ ] All existing tests in `test_feature_loader.py` continue to pass
- [ ] `generate_feature_yaml.py` updated to align its `TaskSpec` with the new schema
- [ ] Backward compatibility: existing valid YAML files load without errors

## Implementation Notes

- Pydantic is already a dependency in GuardKit
- Follow patterns in `.claude/rules/patterns/pydantic-models.md`
- The `file_path` field should use `str` (not `Path`) in the Pydantic model since YAML deserializes to strings, then convert to `Path` after validation
- Keep the dataclass versions for `FeatureExecution` and `FeatureOrchestration` if they don't need validation (they are internal state, not user-facing YAML fields)
- Consider using `extra="warn"` initially, then tightening to `extra="forbid"` in a later release

## Files to Modify

- `guardkit/orchestrator/feature_loader.py` - Replace dataclasses with Pydantic models
- `installer/core/commands/lib/generate_feature_yaml.py` - Align TaskSpec with new schema
- `tests/unit/test_feature_loader.py` - Update tests for Pydantic validation behavior
