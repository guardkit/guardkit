# TASK-CR-T05 Completion Report

## Summary
Added path-gating validation to `/template-validate` (Section 7: Global Template Validation) to detect rules files missing `paths:` frontmatter and prevent regressions in conditional loading.

## Files Modified

| File | Change |
|------|--------|
| `installer/core/lib/template_validation/models.py` | Added `PATH_GATING` to `IssueCategory` enum |
| `installer/core/lib/template_validation/sections/section_07_global.py` | Added `has_paths_frontmatter()`, `suggest_paths()`, `validate_rules_path_gating()` functions; enhanced `GlobalTemplateValidationSection.execute()` with path-gating checks |
| `installer/core/templates/default/.claude/rules/code-style.md` | Added `paths:` frontmatter |
| `installer/core/templates/default/.claude/rules/quality-gates.md` | Added `paths:` frontmatter |
| `installer/core/templates/default/.claude/rules/workflow.md` | Added `paths:` frontmatter |

## Files Created

| File | Purpose |
|------|---------|
| `tests/unit/test_path_gating_validation.py` | 29 unit tests covering all validation logic |

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `/template-validate` checks for `paths:` in all rules files | Done | `validate_rules_path_gating()` scans `.claude/rules/**/*.md` |
| Warning generated for missing `paths:` frontmatter | Done | `MEDIUM` severity `PATH_GATING` issues created per file |
| Suggestion provided for appropriate path pattern | Done | `suggest_paths()` with 12 known patterns + fallback |
| Validation report includes "Path-Gating Coverage" metric | Done | `metadata` dict includes `path_gating_total`, `path_gating_gated`, `path_gating_coverage_pct`, `path_gating_ungated_files` |
| Existing templates updated to fix gaps | Done | 3 default template rules files fixed |
| Documentation updated with path-gating requirement | Done | `.claude/rules/patterns/template.md` already documents the requirement |

## Test Results

- **29 tests**, all passing
- **94% coverage** on `section_07_global.py`
- Test categories: frontmatter detection (11), path suggestions (5), validation function (7), section integration (6)

## Preventive Value

This validation prevents regressions where new rules files are added without `paths:` frontmatter, which would cause them to load unconditionally in every conversation, wasting ~200-500 tokens each.
