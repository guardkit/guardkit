---
id: TASK-FIX-PD04
title: Fix auto-generated template file naming (.j.template)
status: completed
created: 2025-12-07T12:05:00Z
updated: 2025-12-07T14:35:00Z
completed: 2025-12-07T14:35:00Z
priority: high
tags: [template-create, completeness-validator, bug-fix]
complexity: 3
related_tasks: [TASK-REV-TC02]
test_results:
  status: passed
  coverage: 84
  last_run: 2025-12-07T14:30:00Z
completed_location: tasks/completed/TASK-FIX-PD04/
---

# Task: Fix Auto-Generated Template File Naming

## Description

The completeness validator auto-generates CRUD templates with incorrect file extensions:

**Current (incorrect)**:
- `Createquery.j.template`
- `Deletequery.j.template`
- `Updatequery.j.template`

**Expected**:
- `Create-query.js.template`
- `Delete-query.js.template`
- `Update-query.js.template`

Or following the entity naming pattern used by the source file.

## Root Cause

The `_estimate_file_path` method in `completeness_validator.py` had two issues:

1. **Truncated file extensions**: Used `Path.suffix` which only returns the last extension (`.template`), not compound extensions like `.js.template`. Fixed by using `Path.suffixes` and joining them.

2. **Didn't detect naming patterns correctly**: When detecting if a reference file used hyphenated naming (like `Read-query`), it compared against the canonical operation name (`Read`) rather than the actual prefix used in the filename (`Get` for `Read` operations). Fixed by looking up the actual prefix from `CRUD_PATTERNS`.

## Acceptance Criteria

- [x] Auto-generated templates have correct file extensions (.js.template for JS)
- [x] Template naming follows consistent pattern (Operation-entity.ext.template)
- [x] Re-run template-create produces correctly named files

## Files Modified

- `installer/global/lib/template_generator/completeness_validator.py` - Fixed `_estimate_file_path` method

## Tests Added

- `tests/unit/test_completeness_validator.py::TestEstimateFilePath` - 9 new tests:
  - `test_compound_extension_js_template` - Verifies .js.template preserved
  - `test_compound_extension_ts_template` - Verifies .ts.template preserved
  - `test_compound_extension_cs_template` - Verifies .cs.template preserved
  - `test_hyphenated_naming_pattern_preserved` - Verifies Read-query → Create-query
  - `test_underscore_naming_pattern_preserved` - Verifies Read_user → Update_user
  - `test_pascal_case_naming_pattern` - Verifies PascalCase preserved
  - `test_directory_preserved` - Verifies directory path from reference
  - `test_simple_template_extension` - Verifies single .template extension
  - `test_triple_extension_preserved` - Verifies .spec.ts.template preserved

## Test Results

```
✅ 25 tests passed
   - 16 existing tests: PASSED
   - 9 new tests: PASSED
   - Coverage: 84% for completeness_validator.py
```

## Related

- Review: TASK-REV-TC02
