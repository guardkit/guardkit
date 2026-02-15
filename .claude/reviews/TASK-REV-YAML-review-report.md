# Review Report: TASK-REV-YAML

## Executive Summary

The recurring Feature YAML schema contract violations stem from a single root cause: **there is no canonical, machine-readable schema** that all generation paths reference, and **no validation occurs at write time**. The `FeatureLoader._parse_task()` method silently accepts invalid field values (e.g., `status: backlog`) and ignores extra fields, allowing malformed YAMLs to persist until they fail at orchestration runtime (e.g., "Tasks not in orchestration").

The fix requires two complementary changes: (1) a shared schema definition that generators can reference, and (2) write-time validation that rejects invalid YAMLs before they reach disk.

## Review Details

- **Mode**: Code Quality
- **Depth**: Standard
- **Task ID**: TASK-REV-YAML
- **Complexity**: 6/10
- **Files Reviewed**: 7

## Findings

### Finding 1: Schema Defined in 3 Separate Places with No Single Source of Truth

**Severity**: High | **Impact**: Root cause of recurring bugs

The feature YAML schema is defined in three disconnected locations:

| Location | Role | Authoritative? |
|----------|------|---------------|
| `guardkit/orchestrator/feature_loader.py` (dataclasses) | Runtime consumer | Yes (de facto) |
| `installer/core/commands/lib/generate_feature_yaml.py` (dataclasses) | Python generator | Partial copy |
| `installer/core/commands/feature-plan.md` (prose) | AI prompt reference | Documentation only |

The `FeatureLoader` dataclasses are the de facto schema, but they cannot be referenced by AI prompts or the Python generator script at import time. Each location maintains its own understanding of the schema.

**Evidence**: `generate_feature_yaml.py:TaskSpec` includes a `description` field in `to_dict()` (line 54) that `FeatureLoader._parse_task()` silently ignores.

### Finding 2: No Validation of `status` Values at Parse Time

**Severity**: High | **Impact**: Invalid status values accepted silently

`FeatureLoader._parse_task()` at line 607:
```python
status=task_data.get("status", "pending"),
```

The `FeatureTask` dataclass declares `Literal["pending", "in_progress", "completed", "failed", "skipped"]` (line 228), but Python dataclasses **do not enforce `Literal` types at runtime**. So `status: backlog` loads without error.

**Test gap**: No tests in `test_feature_loader.py` verify that invalid status values are rejected. The test suite only tests the happy path (`status: "pending"`).

### Finding 3: Extra/Unknown Fields Silently Ignored

**Severity**: Medium | **Impact**: Schema drift goes undetected

Because `_parse_task()` uses `.get()` for all fields (lines 601-615), extra fields like `task_type`, `source`, and `architecture_review` are silently dropped. No warning is logged.

Similarly, `_parse_feature()` at lines 553-564 uses `.get()` for all non-required fields at the feature level.

**Impact**: When a generator includes fields that the loader doesn't expect (like `task_type` which CoachValidator actually needs), the field is lost. This creates a false sense of correctness.

### Finding 4: No Write-Time Validation

**Severity**: High | **Impact**: Invalid YAMLs reach disk

Neither `generate_feature_yaml.py` nor `FeatureLoader.save_feature()` validates the complete YAML structure before writing. The `validate_task_paths()` function (line 252 of `generate_feature_yaml.py`) only checks that file paths exist on disk, not schema compliance.

**Evidence**: `FeatureLoader.save_feature()` (line 783) serializes directly without calling `validate_feature()`.

### Finding 5: `/system-plan` Has No Feature YAML Schema Reference

**Severity**: High | **Impact**: FEAT-AC1A class of bugs

The system-plan command spec (`.claude/commands/system-plan.md`) contains **zero references** to the feature YAML schema, `parallel_groups`, `orchestration`, or `FeatureLoader`. When system-plan chains to `/feature-plan` via the `[F]eature-plan` option (line 883), there is no mechanism to pass schema constraints.

This is exactly how the FEAT-AC1A bug occurred: system-plan generated a YAML with `parallel_groups` at the top level instead of nested under `orchestration:`.

### Finding 6: `generate_feature_yaml.py` TaskSpec Includes Extra Field

**Severity**: Low | **Impact**: Schema inconsistency

`generate_feature_yaml.py:TaskSpec.to_dict()` includes `description` (line 54) in task output. `FeatureLoader._parse_task()` does not read this field. While harmless, it indicates that the generator's schema diverges from the loader's expectations.

### Finding 7: Test Coverage Gaps for Schema Validation

**Severity**: Medium | **Impact**: Regression risk

Missing test cases in `tests/unit/test_feature_loader.py`:

| Missing Test | Risk |
|-------------|------|
| Invalid `status` value (e.g., `backlog`) | Values like `backlog` silently accepted |
| Extra/unknown fields in task data | No warning or error logged |
| Invalid `implementation_mode` value | Accepted without validation |
| `generate_feature_yaml.py` output round-trip | No integration test |
| `orchestration.parallel_groups` at wrong nesting level | Key failure mode untested |

### Finding 8: FEAT-AC1A.yaml Is Now Correctly Structured

**Severity**: Info | **Impact**: None (already fixed)

The current `.guardkit/features/FEAT-AC1A.yaml` file has `orchestration.parallel_groups` properly nested (lines 112-124) and uses `status: pending` for all tasks. This was likely regenerated after the initial error was discovered.

## Schema Mismatch Catalogue

### Generator: `generate_feature_yaml.py` vs FeatureLoader

| Field | Generator Output | FeatureLoader Expectation | Match? |
|-------|-----------------|--------------------------|--------|
| `orchestration.parallel_groups` | Correct nesting | `orchestration.parallel_groups` | Yes |
| `tasks[].status` | `"pending"` | `Literal[...]` (not enforced) | Yes |
| `tasks[].file_path` | Present (required) | Present (required) | Yes |
| `tasks[].description` | Present | Not read | Extra field |

### Generator: AI via `/feature-plan` vs FeatureLoader

| Field | Risk | Mitigation |
|-------|------|-----------|
| `parallel_groups` nesting | High - AI may put at top level | Schema reference in prompt (TASK-FP-002 fix) |
| `tasks[].status` | Medium - AI may use `backlog` | No validation |
| Extra fields (`task_type`, `source`) | Low - silently ignored | No validation |

### Generator: AI via `/system-plan` vs FeatureLoader

| Field | Risk | Mitigation |
|-------|------|-----------|
| All fields | High - no schema reference in spec | **None** |

## Root Cause Confirmation

The root cause is confirmed as stated in the task description:

1. **No canonical schema**: The schema is implicit in Python dataclasses, not exportable or referenceable
2. **No write-time validation**: YAMLs are written without schema checks
3. **Silent acceptance**: `.get()` with defaults hides all mismatches
4. **Multiple unlinked generators**: Each path has its own schema understanding

## Recommendations

### Recommendation 1: Create a Pydantic Schema Model (Recommended)

Replace `FeatureTask`/`Feature` dataclasses with Pydantic models that:
- Enforce `Literal` types at parse time
- Reject unknown fields (`model_config = ConfigDict(extra="forbid")`)
- Generate JSON Schema for AI prompt inclusion
- Provide `model_validate()` for write-time validation

**Effort**: Medium (4-6 hours) | **Impact**: High | **Risk**: Low (Pydantic already in GuardKit deps)

### Recommendation 2: Add Write-Time Validation

Add a `FeatureLoader.validate_yaml(data: dict) -> List[str]` static method that validates raw YAML data against the schema before writing. Call it from:
- `generate_feature_yaml.py` before `write_yaml()`
- `FeatureLoader.save_feature()` before `yaml.dump()`
- New CLI command `guardkit feature validate FEAT-XXX`

**Effort**: Low (2-3 hours) | **Impact**: High | **Risk**: Low

### Recommendation 3: Add Schema Reference to system-plan.md

Include a canonical YAML schema example in the system-plan command spec, or add a cross-reference to the feature-plan schema section. Ensure that when system-plan chains to feature-plan, the schema contract is explicit.

**Effort**: Low (1 hour) | **Impact**: High | **Risk**: None

### Recommendation 4: Add Schema Validation Tests

Add tests for:
- Invalid `status` values rejected (or warned)
- Extra fields logged as warnings (or rejected)
- Invalid `implementation_mode` values
- Round-trip test: `generate_feature_yaml.py` output -> `FeatureLoader.load_feature()`
- `parallel_groups` at wrong nesting level

**Effort**: Low (2-3 hours) | **Impact**: Medium | **Risk**: None

### Recommendation 5: Add `guardkit feature validate` CLI Command

Pre-flight validation command that checks a feature YAML before running `autobuild feature`:
```bash
guardkit feature validate FEAT-AC1A
```

**Effort**: Low (2-3 hours) | **Impact**: Medium | **Risk**: Low

## Decision Matrix

| Option | Impact | Effort | Risk | Recommendation |
|--------|--------|--------|------|----------------|
| R1: Pydantic Schema | High | Medium | Low | **Do first** |
| R2: Write-time validation | High | Low | Low | **Do second** |
| R3: system-plan schema ref | High | Low | None | **Do immediately** |
| R4: Schema validation tests | Medium | Low | None | **Do with R1** |
| R5: CLI validate command | Medium | Low | Low | **Do with R2** |

## Suggested Implementation Order

1. **R3** (1h) - Immediate fix: add schema reference to system-plan.md
2. **R1 + R4** (6-8h) - Core fix: Pydantic models with strict validation + tests
3. **R2 + R5** (4-6h) - Defense-in-depth: write-time validation + CLI command

Total estimated effort: 11-15 hours across 3 waves.

## Acceptance Criteria Status

- [x] All feature YAML generation paths identified and documented (5 paths found)
- [x] Schema mismatches between each generator and FeatureLoader catalogued
- [x] Root cause confirmed (no canonical schema, no write-time validation, silent acceptance)
- [x] Recommended fix approach identified (Pydantic models + write-time validation + schema refs)
- [ ] Implementation tasks created if [I]mplement chosen
