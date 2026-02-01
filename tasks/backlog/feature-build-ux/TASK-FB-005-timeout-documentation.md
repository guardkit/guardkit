---
id: TASK-FB-005
title: Update Timeout Documentation for /feature-build
status: backlog
created: 2025-01-31T16:00:00Z
priority: medium
tags: [feature-build, documentation, phase-1]
complexity: 2
implementation_mode: direct
parent_review: TASK-REV-FBA1
feature_id: FEAT-FB-UX
wave: 2
---

# Task: Update Timeout Documentation for /feature-build

## Context

The current documentation mentions VS Code extension timeout, but the actual issue is the Claude Code Bash tool's default 120s timeout. Documentation needs to be corrected and clarified.

**Parent Review**: [TASK-REV-FBA1](.claude/reviews/TASK-REV-FBA1-review-report.md)

## Requirements

Update documentation to correctly explain:

1. Bash tool default timeout (120s/2min)
2. How to use `--timeout` parameter with Bash tool
3. Recommended timeouts for different task complexities
4. Relationship between Bash timeout and SDK timeout

## Acceptance Criteria

- [ ] `installer/core/commands/feature-build.md` updated with correct timeout info
- [ ] `.claude/rules/autobuild.md` updated with timeout guidance
- [ ] CLAUDE.md troubleshooting section updated
- [ ] Examples show `--timeout` usage in Bash tool calls

## Documentation Updates

### feature-build.md Section

```markdown
## Timeout Configuration

### Bash Tool Timeout (Claude Code Context)

When running `/feature-build` via Claude Code, the Bash tool has a **default timeout of 120 seconds** (2 minutes). Most builds exceed this.

**Solution**: Use the `timeout` parameter when invoking Bash:

```bash
# Bash tool with extended timeout (10 minutes)
guardkit autobuild task TASK-XXX
# With Bash tool parameter: timeout: 600000 (ms)
```

### SDK Timeout (Internal)

The `--sdk-timeout` flag controls how long each agent invocation can run:

| Task Complexity | SDK Timeout | Total Build Time |
|-----------------|-------------|------------------|
| 1-3 (Simple) | 300s (5m) | ~5-10 min |
| 4-6 (Medium) | 600s (10m) | ~10-20 min |
| 7-10 (Complex) | 900s (15m) | ~20-45 min |

### Recommended Bash Timeout

Set Bash tool timeout to **at least 2x expected total build time**:

| Build Type | Recommended Bash Timeout |
|------------|--------------------------|
| Single simple task | 600000ms (10 min) |
| Single complex task | 1800000ms (30 min) |
| Small feature (3-5 tasks) | 3600000ms (60 min) |
| Large feature (6+ tasks) | Run from terminal instead |
```

## Files to Modify

- `installer/core/commands/feature-build.md` - Timeout section
- `.claude/rules/autobuild.md` - Timeout recommendations
- `CLAUDE.md` - Troubleshooting section

## Dependencies

None - documentation only.
