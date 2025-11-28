# Update Template Philosophy in MkDocs

**Priority**: Critical
**Category**: Documentation Sync - Philosophy
**Estimated Effort**: 2 hours

## Problem

README.md has updated template philosophy (lines 273-343) emphasizing "learning resources, not production code" and documenting the removal of `taskwright-python` template. The MkDocs Templates page may not reflect these changes.

## Current State

**README.md includes**:
- "Templates are learning resources, not production code" philosophy
- Removal of `taskwright-python` template with explanation
- Clear guidance: use reference templates for evaluation, `/template-create` for production
- 5 high-quality templates focus
- Quality standards and scoring

**MkDocs site**: May have outdated philosophy or list `taskwright-python`

## Acceptance Criteria

1. Update `docs/templates/index.md` with current philosophy
2. Remove any references to `taskwright-python` template
3. Add explanation of why it was removed
4. Content must include:
   - "Learning resources, not production code" emphasis
   - When to use reference templates (evaluation)
   - When to use `/template-create` (production)
   - Current 5 templates with quality scores
   - Template quality standards explanation
5. Update template comparison table if exists
6. Add migration notes for users who used old templates

## Implementation Notes

- Extract from README.md lines 273-343
- Check for any `taskwright-python` references across docs
- Emphasize `/template-create` as production path
- Link to Template Philosophy Guide

## References

- README.md lines 273-343
- docs/guides/template-philosophy.md
- docs/guides/template-migration.md
