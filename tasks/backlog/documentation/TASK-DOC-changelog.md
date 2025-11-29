# Create Comprehensive Changelog

**Priority**: Enhancement
**Category**: Documentation - History
**Estimated Effort**: 2-3 hours

## Problem

Users need to track Taskwright's evolution, understand what's changed between versions, and plan upgrades accordingly. A comprehensive changelog provides transparency and helps users stay informed.

## Changelog Structure

### Version Entry Format
Each version should include:
- Version number and release date
- Summary of changes
- Breaking changes (if any)
- New features
- Improvements
- Bug fixes
- Deprecations
- Migration notes

### Categories to Track

**Added**
- New features
- New commands
- New templates
- New agents

**Changed**
- Modified behavior
- Updated dependencies
- Improved performance

**Deprecated**
- Features marked for removal
- Migration path provided

**Removed**
- Deleted features
- Removed templates (e.g., taskwright-python)
- Cleanup

**Fixed**
- Bug fixes
- Security patches

**Security**
- Vulnerability fixes
- Security improvements

## Acceptance Criteria

1. Create `CHANGELOG.md` in repository root
2. Create `docs/changelog.md` for MkDocs site
3. Add to top-level navigation
4. Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
5. Use [Semantic Versioning](https://semver.org/)
6. Document all versions from 0.1.0 to current
7. Include migration notes for breaking changes
8. Add "Unreleased" section for upcoming changes
9. Link to relevant documentation for features

## Example Entry

```markdown
## [0.9.0] - 2025-01-XX

### Added
- Hash-based task IDs for collision-free parallel development (#123)
- PM tool integration with automatic ID mapping (#145)
- Spec-Oriented Development (SOD) positioning
- Parallel development support with Conductor.build
- Agent boundary sections (ALWAYS/NEVER/ASK framework)

### Changed
- Template philosophy: "Learning resources, not production code"
- Improved template validation with 3-level system
- Enhanced agent discovery with metadata-based matching

### Removed
- `taskwright-python` template (use `/template-create` instead)

### Fixed
- Windows WSL2 installation issues (#156)
- Working directory detection errors (#167)

### Migration Notes
- Run `scripts/migrate-my-tasks.py` to convert sequential to hash-based IDs
- Remove references to `taskwright-python` template
- See [Migration Guide](docs/guides/migration.md) for details
```

## Implementation Notes

- Review git commit history for changes
- Check GitHub issues/PRs for features
- Cross-reference with task completion dates
- Link to relevant PRs/issues where applicable
- Add comparison links (e.g., [0.8.0...0.9.0])

## References

- Git commit history
- GitHub releases
- Task completion records
- Keep a Changelog format
- Semantic Versioning spec
