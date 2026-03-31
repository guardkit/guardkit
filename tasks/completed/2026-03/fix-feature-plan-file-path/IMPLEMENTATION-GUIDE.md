# Implementation Guide: Fix Feature Plan file_path Generation

## Wave 1 (All tasks - parallel safe)

### TASK-FIX-FP01: Spec fix (direct, ~10 min)
- Edit `installer/core/commands/feature-plan.md`
- Add `--feature-slug "{feature_slug}"` to 3 example invocations
- Fix inconsistent task format at line ~1875

### TASK-FIX-FP02: Validation fix (task-work, ~30 min)
- Edit `guardkit/orchestrator/feature_loader.py:644-648`
- Add `is_dir()`, `.md` suffix, and "tasks" presence checks
- Add tests in `tests/unit/test_feature_loader.py`

### TASK-FIX-FP03: Fail-fast fix (task-work, ~30 min)
- Edit `guardkit/orchestrator/feature_orchestrator.py:646-675`
- Replace warning returns with `FeatureValidationError` raises
- Keep per-file copy warnings at line ~719 as-is
- Add tests in `tests/unit/test_feature_orchestrator.py`

### TASK-FIX-FP04: Input validation fix (task-work, ~20 min)
- Edit `installer/core/commands/lib/generate_feature_yaml.py:371-376`
- Make `--feature-slug` required or validate non-empty
- Update existing tests in `tests/unit/test_generate_feature_yaml.py`

## Verification

After all fixes, re-run the FEAT-CEE8 scenario:
```bash
cd guardkit-examples/fastapi
/feature-plan "Add comprehensive API documentation..."
guardkit autobuild feature FEAT-XXXX --max-turns 25
```

Expected: All tasks should have proper `file_path` values and copy successfully to worktree.
