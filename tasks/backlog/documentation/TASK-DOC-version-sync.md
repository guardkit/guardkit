# Verify Version Numbers Across MkDocs Site

**Priority**: Minor
**Category**: Documentation Consistency
**Estimated Effort**: 30 minutes

## Problem

README.md shows version `0.9.0` (line 3). Need to verify the MkDocs site footer/header displays the correct version consistently.

## Current State

- README.md badge: `version-0.9.0`
- MkDocs site version: Unknown (needs verification)

## Acceptance Criteria

1. Check MkDocs site for version display locations:
   - Homepage
   - Footer
   - Header/navigation
   - About/release notes page
2. Update all locations to show `0.9.0`
3. Verify version badge consistency
4. Document where version is configured for future updates

## Implementation Notes

- Check mkdocs.yml for version configuration
- Check docs/index.md for hardcoded versions
- Check custom theme files if applicable
- Consider automated version sync from README.md

## References

- README.md line 3
- mkdocs.yml configuration
