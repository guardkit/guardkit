# Add Quick Install Script to MkDocs Getting Started

**Priority**: Minor
**Category**: Documentation Enhancement
**Estimated Effort**: 1 hour

## Problem

README.md has a curl-based one-liner install script (lines 122-125) for quick installation. Need to verify the MkDocs Getting Started guide includes this convenient option.

## Current State

**README.md includes**:
```bash
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash
```

**MkDocs site**: May only show git clone method

## Acceptance Criteria

1. Update `docs/guides/GETTING-STARTED.md` to include quick install option
2. Show both installation methods:
   - Option 1: Quick Install (curl one-liner) - **Recommended**
   - Option 2: Clone Repository (manual)
3. Include platform-specific guidance:
   - macOS/Linux: Direct curl command
   - Windows: WSL2 requirement, then curl command
4. Add security note about inspecting scripts before piping to bash
5. Include verification step: `guardkit --version`

## Implementation Notes

- Place quick install as Option 1 (recommended)
- Keep clone option for developers who want source
- Add link to view install.sh script on GitHub
- Suggest inspecting script first for security-conscious users

## References

- README.md lines 119-145 (5-Minute Quickstart)
- installer/scripts/install.sh
