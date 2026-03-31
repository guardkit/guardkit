# Implementation Guide: Fix Feature-Plan Path Generation

## Architecture Overview

The feature-plan path generation involves three components:

1. **Task file creator** (`implement_orchestrator.py`) - creates `.md` files on disk using `_slugify()`
2. **YAML generator** (`generate_feature_yaml.py`) - records `file_path` in YAML using `slugify_task_name()` + `build_task_file_path()`
3. **Feature loader** (`feature_loader.py`) - validates paths at build time

The fix ensures components 1 and 2 use identical path logic.

## Wave 1: Foundation Fixes (Parallel)

### TASK-FPP-001: Fix FEAT-D4CE.yaml (5 min)
Simple YAML edit - correct 8 file paths. No code changes.

### TASK-FPP-002: Unify Slug Generation (1-2 hrs)
1. Create `installer/core/lib/slug_utils.py`
2. Move `slugify_task_name()` there with 50-char limit
3. Update both consumers to import from shared location
4. Run existing tests

### TASK-FPP-003: Fix Path Doubling (30 min - 1 hr)
1. Add guard in `build_task_file_path()` to detect when `base_path` already contains `feature_slug`
2. Add regression test
3. Run existing tests

## Wave 2: Hardening (Parallel, after Wave 1)

### TASK-FPP-004: Simplify Spec (30 min)
Documentation-only change to `feature-plan.md` Step 10.

### TASK-FPP-005: Add Path Validation (1-2 hrs)
Add validation after YAML write that checks all paths resolve to files.

## Key Files

| File | Changes |
|------|---------|
| `installer/core/commands/lib/generate_feature_yaml.py` | Fix `build_task_file_path()`, update slug import |
| `installer/core/lib/implement_orchestrator.py` | Replace `_slugify()` with shared import |
| `installer/core/lib/slug_utils.py` | New shared slug utility |
| `installer/core/commands/feature-plan.md` | Simplify --task format docs |
| `.guardkit/features/FEAT-D4CE.yaml` | Fix 8 paths |
| `tests/unit/test_generate_feature_yaml.py` | Add regression tests |

## Risk Assessment

- **Low risk**: All changes are isolated to path/slug logic
- **No breaking changes**: Parser already handles 4-field format
- **Easy verification**: Run `guardkit autobuild feature FEAT-D4CE` to validate
