# Expand Troubleshooting Guide

**Priority**: Enhancement
**Category**: Documentation - Support
**Estimated Effort**: 2-3 hours

## Problem

Users will encounter common issues that should be documented proactively in the troubleshooting guide, especially related to new features like hash-based IDs, parallel development, and platform-specific issues.

## New Troubleshooting Sections Needed

### 1. Hash-Based Task ID Issues
- "Task ID format not recognized"
- "PM tool integration not working"
- "Migration script errors"
- "Duplicate hash collisions" (theoretical)

### 2. Parallel Development Issues
- "State not syncing between worktrees"
- "Conductor.build integration broken"
- "Symlink errors"
- "Conflicts between parallel tasks"

### 3. Platform-Specific Issues
- WSL2 installation problems
- Path issues on Windows
- Permission errors on macOS
- Linux distribution compatibility

### 4. Working Directory Issues
- "Commands run from wrong directory"
- "Stack detection fails"
- "Files created in wrong location"

### 5. Agent Discovery Issues
- "Specialist agent not found"
- "Wrong agent selected"
- "Agent metadata missing"
- "Fallback to task-manager"

### 6. Template Issues
- "Template initialization fails"
- "Template validation errors"
- "Missing agent files"
- "Boundary section validation fails"

### 7. Quality Gate Failures
- "Tests fail repeatedly"
- "Coverage thresholds not met"
- "Architectural review fails"
- "Plan audit violations"

## Acceptance Criteria

1. Update `docs/troubleshooting/index.md` or create separate sections
2. Each issue must include:
   - Clear problem description
   - Symptoms/error messages
   - Root cause explanation
   - Step-by-step solution
   - Prevention tips
3. Add search-friendly headings
4. Include command examples for diagnosis
5. Link to related documentation
6. Add "Still stuck?" section with support options

## Implementation Notes

- Use actual error messages users will see
- Provide copy-paste diagnostic commands
- Show expected vs actual output
- Include verification steps
- Cross-reference to main documentation

## Example Format

```markdown
### Task Created in Wrong Directory

**Symptoms:**
- Files appear in Taskwright installation directory
- Stack detection fails
- "Unknown technology" errors

**Cause:**
Running `/task-work` from Taskwright repo instead of your project.

**Solution:**
1. Navigate to your project root:
   \`\`\`bash
   cd /path/to/your/project
   \`\`\`
2. Verify you're in the right directory:
   \`\`\`bash
   pwd  # Should show your project path, not taskwright
   \`\`\`
3. Run task command again

**Prevention:**
Always check your current directory before running task commands.
```

## References

- Existing troubleshooting documentation
- Common user support issues
- Error messages in codebase
