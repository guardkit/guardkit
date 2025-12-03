# Add Working Directory Warning to MkDocs Getting Started

**Priority**: Minor
**Category**: Documentation - User Experience
**Estimated Effort**: 30 minutes

## Problem

README.md has a prominent warning about running commands from the project root directory (lines 149-155), not from the GuardKit installation directory. This critical user guidance should be in the MkDocs Getting Started guide.

## Current State

**README.md includes**:
- ⚠️ Important callout box
- Clear instruction: run from project root
- Example showing correct directory navigation
- Explanation of why (stack detection, file creation)

**MkDocs site**: May lack this warning

## Acceptance Criteria

1. Update `docs/guides/GETTING-STARTED.md` with prominent warning
2. Warning must appear:
   - After installation section
   - Before first usage example
   - As a callout/admonition box
3. Content must include:
   - "Always run `/task-work` from project root"
   - Why: stack detection and file creation location
   - Example: `cd /path/to/your/project`
   - What happens if run from wrong directory
4. Add similar warning to workflow guides that use `/task-work`

## Implementation Notes

- Use MkDocs admonition syntax for visual emphasis
- Place strategically before first command examples
- Consider adding to troubleshooting guide
- Link to troubleshooting for "wrong directory" issues

## Example Format

```markdown
!!! warning "Working Directory"
    Always run `/task-work` from your **project root directory** (where your code lives), not from the GuardKit installation directory. The command uses your current directory to detect the tech stack and create files.

    ```bash
    cd /path/to/your/project  # ✅ Navigate to project root first
    ```
```

## References

- README.md lines 149-155
- MkDocs admonition documentation
