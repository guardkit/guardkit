# Feature-Plan Command Reference

**Command**: `/feature-plan`
**Version**: 2.0
**Last Updated**: 2025-02-10

## Overview

The `/feature-plan` command orchestrates feature planning by combining task creation and review analysis into a single workflow. It automatically creates a review task, executes decision-making analysis, and optionally creates implementation tasks from recommendations.

## Command Syntax

```bash
/feature-plan "feature description" [flags]
```

## Available Flags

### Core Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--context path/to/file.md` | Explicitly specify context files (can be used multiple times) | Auto-detect |
| `--no-questions` | Skip all clarification (review scope + implementation prefs) | Off |
| `--with-questions` | Force clarification even for simple features | Off |
| `--defaults` | Use clarification defaults throughout workflow | Off |
| `--answers="..."` | Inline answers (propagated to task-review and subtask creation) | None |
| `--no-structured` | Disable structured YAML feature file output | Enabled by default |

## Flag Details

### --context

**Purpose**: Explicitly specify context files when auto-detection isn't sufficient.

**Syntax**:
```bash
/feature-plan "description" --context path/to/file.md
/feature-plan "description" --context file1.md --context file2.md
```

**Behavior**:
- Loads specified files before analysis
- Works alongside auto-detection (explicit files loaded first)
- Supports multiple `--context` flags

**Example**:
```bash
# Single context file
/feature-plan "implement OAuth" --context docs/auth-design.md

# Multiple context files
/feature-plan "add API" --context docs/api-spec.md --context docs/security-requirements.md
```

### --no-questions, --with-questions, --defaults, --answers

**Purpose**: Control clarification behavior during planning.

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip all clarification prompts |
| `--with-questions` | Force clarification even for simple features |
| `--defaults` | Use defaults without prompting |
| `--answers="..."` | Provide inline answers for automation |

**Example (CI/CD automation)**:
```bash
/feature-plan "add caching" --answers="focus:technical tradeoff:speed approach:1 execution:sequential testing:minimal"
```

### --no-structured

**Purpose**: Disable structured YAML feature file generation.

**Default Behavior**:
By default, `/feature-plan` generates both:
1. Task markdown files in `tasks/backlog/{feature-slug}/`
2. Structured YAML file in `.guardkit/features/FEAT-XXX.yaml`

**With --no-structured**:
Only task markdown files are created, skipping the YAML generation.

**Example**:
```bash
# Default (both markdown and YAML)
/feature-plan "add OAuth2 authentication"

# Markdown only (skip YAML)
/feature-plan "add OAuth2 authentication" --no-structured
```

## Complete Examples

### Example 1: Standard Feature Planning

```bash
/feature-plan "implement dark mode"
```

Creates:
- Review task: `TASK-REV-xxxx`
- After [I]mplement decision:
  - `tasks/backlog/dark-mode/TASK-DM-001.md`
  - `tasks/backlog/dark-mode/IMPLEMENTATION-GUIDE.md`
  - `.guardkit/features/FEAT-xxxx.yaml`

### Example 2: Automated Pipeline

```bash
/feature-plan "add user notifications" \
              --no-questions \
              --answers="focus:all tradeoff:balanced approach:1 execution:parallel testing:standard"
```

Runs complete flow with predetermined answers for CI/CD integration.

### Example 3: Context-Rich Planning

```bash
/feature-plan "implement FEAT-AUTH-001" \
              --context docs/features/FEAT-AUTH-001-spec.md \
              --context docs/security-requirements.md \
              --with-questions
```

Loads explicit context and forces clarification prompts.

## Output Summary

### Standard Flow Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING: implement dark mode
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Creating review task...
✅ Task created: TASK-REV-A3F2

Step 2: Analyzing technical options...
[Analysis output]

Step 3: Decision checkpoint
[A/R/I/C options]

Step 4: Creating implementation structure...
✅ Feature folder created
✅ 5 subtasks generated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Related Commands

| Command | Purpose |
|---------|---------|
| `/task-create` | Create individual tasks |
| `/task-review` | Run review on existing tasks |
| `/task-work` | Implement tasks |
| `/feature-build` | Autonomous feature implementation |
| `/feature-complete` | Complete and verify features |

## See Also

- [Task Workflow Guide](../guides/task-workflow-guide.md)
- [AutoBuild Documentation](../../.claude/rules/autobuild.md)
