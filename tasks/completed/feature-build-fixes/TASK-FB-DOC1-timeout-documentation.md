---
id: TASK-FB-DOC1
title: Document Timeout Recommendations and Best Practices
status: completed
task_type: documentation
created: 2026-01-09T12:00:00Z
completed: 2026-01-09T14:30:00Z
priority: low
tags: [feature-build, autobuild, timeout, documentation]
complexity: 2
parent_feature: feature-build-fixes
wave: 2
implementation_mode: direct
conductor_workspace: feature-build-fixes-wave2-2
related_review: TASK-REV-FB01
---

# Document Timeout Recommendations and Best Practices

## Problem

Users encountering timeout issues have limited guidance on:
1. Appropriate timeout values for different task complexities
2. How to configure timeouts (CLI, frontmatter, environment)
3. The external bash timeout issue when running from Claude Code

## Requirements

1. Add timeout guidance table to CLAUDE.md
2. Document the Claude Code bash timeout limitation
3. Provide troubleshooting guidance for timeout errors

## Acceptance Criteria

- [x] CLAUDE.md includes timeout guidance table
- [x] Claude Code limitation documented with workaround
- [x] Error message guidance added

## Implementation

### Change 1: Add Timeout Guidance Table

Add to CLAUDE.md under SDK Timeout Configuration:

```markdown
### Recommended Timeout Values

| Task Complexity | Recommended Timeout | Use Case |
|-----------------|---------------------|----------|
| 1-3 (Simple) | 300s (5 min) | Quick fixes, single-file changes |
| 4-6 (Medium) | 600s (10 min) | Standard features, multiple files |
| 7-10 (Complex) | 900s (15 min) | Large features, architectural changes |

**Phase Duration Reference**:
- Pre-Loop (Phases 2-2.8): 125-315 seconds
- Loop (Phases 3-5.5): 180-420 seconds per turn
- Total typical range: 305-735 seconds
```

### Change 2: Document Claude Code Limitation

Add new section:

```markdown
### Running Feature-Build from Claude Code

**Important**: Claude Code's VS Code extension has a 10-minute bash command timeout. For long-running feature builds, run from terminal instead:

\`\`\`bash
# From terminal (recommended for feature builds)
cd /path/to/project
guardkit autobuild feature FEAT-XXX --sdk-timeout 900

# NOT from Claude Code for long builds
\`\`\`

If you see exit code 137 (SIGKILL), this indicates the bash command was killed by the external timeout.
```

### Change 3: Improve Error Message Guidance

Add to Troubleshooting section:

```markdown
### Timeout Errors

**Error**: `SDK timeout after Xs: Agent invocation exceeded Xs timeout`

**Solution**:
1. Increase timeout: `guardkit autobuild task TASK-XXX --sdk-timeout 900`
2. Or set in task frontmatter:
   \`\`\`yaml
   autobuild:
     sdk_timeout: 900
   \`\`\`
3. For feature builds, consider running from terminal instead of Claude Code
```

## Files to Modify

| File | Change |
|------|--------|
| `CLAUDE.md` | Add timeout guidance, Claude Code limitation, troubleshooting |

## Test Plan

1. Review documentation for clarity
2. Verify code blocks render correctly

## Estimated Effort

30 minutes

## Dependencies

- Should be done alongside or after TASK-FB-TIMEOUT1

## Notes

- Documentation changes don't require testing
- Helps users self-serve when encountering timeout issues
