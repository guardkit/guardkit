# Add Windows/WSL2 Installation Instructions to MkDocs

**Priority**: Critical
**Category**: Documentation Gap - Platform Support
**Estimated Effort**: 1-2 hours

## Problem

README.md includes explicit Windows/WSL2 installation steps (lines 129-137), noting that native PowerShell is not supported. The MkDocs Getting Started guide likely lacks these platform-specific instructions.

## Current State

**README.md includes**:
- WSL2 installation command
- WSL2 terminal setup steps
- Project initialization in WSL2
- Note about native PowerShell limitation

**MkDocs site**: May lack Windows-specific guidance

## Acceptance Criteria

1. Update `docs/guides/GETTING-STARTED.md` with Windows section
2. Content must include:
   - WSL2 installation steps (`wsl --install`)
   - Opening WSL2 terminal
   - Running install script in WSL2
   - Initializing project in WSL2
   - Clear note: "Native PowerShell installation not supported"
   - Explanation of why bash is required
3. Add platform selector or tabs (macOS | Linux | Windows)
4. Include troubleshooting section for common Windows issues

## Implementation Notes

- Extract from README.md lines 129-137
- Consider adding platform detection recommendations
- Link to WSL2 official documentation
- Add note about VS Code + WSL2 extension

## References

- README.md lines 129-137
- Microsoft WSL2 documentation
