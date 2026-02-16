# Review Report: TASK-REV-8976 - Feature-Plan Filename Inconsistency

## Executive Summary

The `/feature-plan` command generates YAML `file_path` values that don't match actual task filenames on disk because **Claude creates files in Step 9 using ad-hoc slugification, while the Python script in Step 10 derives paths deterministically**. All 9 prior fix tasks (FEAT-FPP + FEAT-FP-FIX) are completed but address Python-to-Python slug divergence, not the Claude-to-Python gap. The recommended fix adds a `--discover` flag to `generate-feature-yaml` that globs for actual files on disk instead of deriving paths from names.

**Severity**: High - blocks all autonomous feature builds
**Confidence**: High - root cause confirmed through code tracing and evidence from FEAT-F97F

---

## Review Details

- **Mode**: Root Cause Analysis
- **Depth**: Standard
- **Task**: TASK-REV-8976
- **Feature Affected**: FEAT-F97F and all future features created via `/feature-plan`

---

## Finding 1: Claude vs Python Slugification Divergence

**Severity**: Critical

### Evidence

From FEAT-F97F:

| Task Name | `slugify_task_name()` Output | Claude's Actual Filename |
|-----------|------------------------------|--------------------------|
| "Set up testing infrastructure and health tests" | `set-up-testing-infrastructure-and-health-tests` | `setup-testing-infrastructure` |
| "Add dev tooling configuration" | `add-dev-tooling-configuration` | `add-dev-tooling-config` |

Claude abbreviates ("Set up" → "setup"), drops suffixes ("and health tests"), and shortens words ("configuration" → "config").

### Root Cause

The `/feature-plan` spec (`installer/core/commands/feature-plan.md`) orchestrates two independent steps:

- **Step 9**: Claude creates task markdown files using the Write tool with ad-hoc filename construction
- **Step 10**: `generate-feature-yaml` derives `file_path` using `build_task_file_path()` → `slugify_task_name()` from `installer/core/lib/slug_utils.py`

These use fundamentally different slugification: one is non-deterministic (Claude's language model), the other is deterministic (Python regex). They will never reliably produce the same output.

### Location

- Claude file creation: `installer/core/commands/feature-plan.md` Step 9 (lines 1804-1839)
- Python path derivation: `installer/core/commands/lib/generate_feature_yaml.py:133-176` (`build_task_file_path()`)

---

## Finding 2: Post-Creation Validation Only Warns

**Severity**: Medium

### Evidence

From `installer/core/commands/lib/generate_feature_yaml.py:519-530`:

```python
path_errors = validate_task_paths(feature, base_dir)
if path_errors:
    print(f"\n⚠️  Path validation warnings ({len(path_errors)}):", file=sys.stderr)
    ...
    print("\n   Task files may not exist yet if they will be created later.")
```

The validation (added by TASK-FPP-005) runs but only prints warnings to stderr. The `feature-plan.md` spec does not instruct Claude to pass `--strict`. Mismatches are silently tolerated.

---

## Finding 3: All Prior Fix Tasks Are Complete

**Severity**: Informational

Both prior fix features are **100% completed**:

### FEAT-FPP (5/5 completed, Feb 7)

| Task | Title | Completed |
|------|-------|-----------|
| TASK-FPP-001 | Fix FEAT-D4CE.yaml | `tasks/completed/TASK-FPP-001/` |
| TASK-FPP-002 | Unify slug generation | `tasks/completed/TASK-FPP-002/` |
| TASK-FPP-003 | Fix path doubling | `tasks/completed/fix-feature-plan-paths/` |
| TASK-FPP-004 | Simplify --task format | `tasks/completed/fix-feature-plan-paths/` |
| TASK-FPP-005 | Add path validation | `tasks/completed/TASK-FPP-005/` |

### FEAT-FP-FIX (4/4 completed, Feb 10)

| Task | Title | Completed |
|------|-------|-----------|
| TASK-FIX-FP01 | Add --feature-slug to spec | `tasks/completed/TASK-FIX-FP01/` |
| TASK-FIX-FP02 | Add directory check | `tasks/completed/TASK-FIX-FP02/` |
| TASK-FIX-FP03 | Raise on copy failure | `tasks/completed/TASK-FIX-FP03/` |
| TASK-FIX-FP04 | Require --feature-slug | `tasks/completed/TASK-FIX-FP04/` |

These fixes correctly addressed Python-to-Python slug divergence, path doubling, missing validation, and missing `--feature-slug`. **The remaining gap is architectural**: Claude creates files in Step 9, Python derives paths in Step 10.

---

## Finding 4: Residual Local Slug Function in guardkit/cli/task.py

**Severity**: Low

`guardkit/cli/task.py` (lines 133-161) still defines a local `_generate_slug()` function instead of importing `slugify_task_name` from `slug_utils.py`. This is a leftover from incomplete slug unification (TASK-FPP-002 unified `implement_orchestrator.py` and `generate_feature_yaml.py` but missed `task.py`). This affects `/task-create` CLI but not `/feature-plan`.

---

## Recommendations

### R1: Add --discover flag to generate-feature-yaml (Critical)

Add a `--discover` mode that globs for actual task files on disk instead of deriving paths from task names.

**Implementation**: Add to `generate_feature_yaml.py`:
```python
def discover_task_file(task_id, feature_slug, base_path):
    pattern = f"{base_path}/{feature_slug}/{task_id}*.md"
    matches = glob.glob(pattern)
    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        return None  # Fall back to derivation
    else:
        raise ValueError(f"Multiple files match {task_id}: {matches}")
```

**Files**: `installer/core/commands/lib/generate_feature_yaml.py`
**Effort**: 1-2 hours | **Risk**: Low

### R2: Update feature-plan.md to use --discover (Critical)

Update Step 10 in the spec to always pass `--discover`.

**Files**: `installer/core/commands/feature-plan.md`
**Effort**: 15 minutes | **Risk**: None

### R3: Make --strict the default (Recommended)

Change `validate_task_paths()` behavior to fail by default, add `--lenient` for opt-out.

**Files**: `installer/core/commands/lib/generate_feature_yaml.py`
**Effort**: 30 minutes | **Risk**: Low (may need `--lenient` for edge cases)

### R4: Unify guardkit/cli/task.py slug function (Low priority)

Replace local `_generate_slug()` with import from `slug_utils.py`.

**Files**: `guardkit/cli/task.py`
**Effort**: 15 minutes | **Risk**: None

---

## Decision Matrix

| Fix | Impact | Effort | Risk | Priority |
|-----|--------|--------|------|----------|
| R1: --discover flag | Eliminates all filename mismatches | 1-2 hrs | Low | **Critical** |
| R2: Update spec | Enables R1 for all future features | 15 min | None | **Critical** |
| R3: Strict validation | Catches regressions immediately | 30 min | Low | Recommended |
| R4: Unify task.py | Completes slug unification | 15 min | None | Low |

**Total effort**: ~3 hours

---

## Appendix: Slug Function Audit

| File | Function | Source | Status |
|------|----------|--------|--------|
| `installer/core/lib/slug_utils.py` | `slugify_task_name()` | Canonical | **Shared utility** |
| `installer/core/commands/lib/generate_feature_yaml.py` | Import from slug_utils | Canonical | **Unified** |
| `installer/core/lib/implement_orchestrator.py` | Import from slug_utils | Canonical | **Unified** |
| `guardkit/cli/task.py` | `_generate_slug()` | Local | **Not unified** |
| `guardkit/planning/adr_generator.py` | `_create_slug()` | Local | Domain-specific (OK) |
| `installer/core/lib/utils/feature_utils.py` | `extract_feature_slug()` | Local | Different purpose (OK) |
