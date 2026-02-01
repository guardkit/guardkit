---
id: TASK-FB-006
title: Add --timeout Flag Passthrough to /feature-build
status: backlog
created: 2025-01-31T16:00:00Z
priority: medium
tags: [feature-build, cli, phase-1]
complexity: 2
implementation_mode: direct
parent_review: TASK-REV-FBA1
feature_id: FEAT-FB-UX
wave: 2
---

# Task: Add --timeout Flag Passthrough to /feature-build

## Context

Users should be able to specify timeout when invoking `/feature-build`, which passes through to both the Bash tool and the `guardkit autobuild` command.

**Parent Review**: [TASK-REV-FBA1](.claude/reviews/TASK-REV-FBA1-review-report.md)

## Requirements

Add `--bash-timeout` flag to `/feature-build` command spec:

1. Accept timeout value in seconds (user-friendly)
2. Convert to milliseconds for Bash tool
3. Document in command flags table
4. Pass SDK timeout via `--sdk-timeout` flag

## Acceptance Criteria

- [ ] `/feature-build TASK-XXX --bash-timeout 600` accepted
- [ ] Value converted to milliseconds for Bash tool (600 → 600000ms)
- [ ] SDK timeout passed if specified: `--sdk-timeout 900`
- [ ] Flag documented in Available Flags table
- [ ] Default: 600s (10 minutes) if not specified

## Implementation Notes

### Command Spec Update (feature-build.md)

```markdown
## Available Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--bash-timeout S` | Bash tool timeout in seconds | 600 |
| `--sdk-timeout S` | Claude SDK operation timeout in seconds | 300 |
| ... existing flags ... |
```

### Execution Instructions

```markdown
### Step 2: Execute via CLI with Timeout

When executing via Bash tool, use the `--bash-timeout` value:

```python
# Pseudo-code for Claude execution
bash_timeout_ms = args.get("bash-timeout", 600) * 1000
sdk_timeout_s = args.get("sdk-timeout", 300)

# Invoke Bash tool with timeout
bash_command = f"guardkit autobuild task {task_id} --sdk-timeout {sdk_timeout_s}"
# Bash tool parameters: timeout: {bash_timeout_ms}
```

## Example Usage

```bash
# Default timeouts (10 min bash, 5 min SDK)
/feature-build TASK-AUTH-001

# Extended timeouts for complex task
/feature-build TASK-AUTH-001 --bash-timeout 1800 --sdk-timeout 900

# Feature build with extended timeout
/feature-build FEAT-A1B2 --bash-timeout 3600
```

## Files to Modify

- `installer/core/commands/feature-build.md` - Add flag and execution logic

## Dependencies

- TASK-FB-005 (timeout documentation explains the values)
