# CLI vs Claude Code: Choosing Your Interface

**Version**: 1.0.0
**Last Updated**: 2026-01-24
**Document Type**: Usage Comparison Guide

---

## Overview

GuardKit provides two ways to use the AutoBuild system:

1. **Claude Code (Slash Commands)**: Interactive use within Claude Code sessions
2. **Python CLI (Shell Commands)**: Direct command-line execution

Both interfaces invoke the same underlying functionality with identical behavior. Your choice depends on your workflow preferences and use case.

---

## Quick Comparison

| Aspect | Claude Code | Python CLI |
|--------|-------------|------------|
| **Interface** | `/feature-build TASK-XXX` | `guardkit autobuild task TASK-XXX` |
| **Interactivity** | Conversational context | Standalone execution |
| **Debugging** | Limited visibility | Full debug logging |
| **Scripting** | Not scriptable | CI/CD integration ready |
| **Environment** | Claude session only | Any terminal |
| **Log Access** | Summary output | Full logs with `GUARDKIT_LOG_LEVEL=DEBUG` |
| **Background Execution** | Not supported | Use `&` or `nohup` |

---

## Claude Code Usage

### When to Use Claude Code

Use the slash command interface when:

- Working interactively in a Claude Code session
- Want conversational context before/after execution
- Prefer integrated workflow within the AI assistant
- Need guidance on options or troubleshooting

### Syntax

```bash
# Single task
/feature-build TASK-XXX [options]

# Feature (multiple tasks)
/feature-build FEAT-XXX [options]
```

### Examples

```bash
# Basic execution
/feature-build TASK-AUTH-001

# With options
/feature-build TASK-AUTH-001 --max-turns 10 --verbose

# Feature mode
/feature-build FEAT-A1B2

# Resume interrupted execution
/feature-build FEAT-A1B2 --resume
```

### Advantages

1. **Contextual Guidance**: Claude can explain options, troubleshoot errors, and suggest next steps
2. **Integrated Workflow**: Seamlessly transitions to review and merge guidance
3. **Natural Language Queries**: Ask questions about the build process
4. **Progress Interpretation**: Claude interprets output and highlights important details

### Limitations

1. **Session Dependent**: Requires active Claude Code session
2. **Limited Debugging**: Cannot access full debug logs
3. **No Background Execution**: Cannot run in background while doing other work
4. **Not Scriptable**: Cannot be used in CI/CD pipelines

---

## Python CLI Usage

### When to Use the CLI

Use the Python CLI when:

- Running builds outside of Claude Code
- Need detailed debug logging
- Integrating with CI/CD pipelines
- Running builds in the background
- Scripting multiple builds

### Installation

```bash
# Install with AutoBuild support
pip install guardkit-py[autobuild]

# Verify installation
guardkit autobuild --help
```

### Commands

| Command | Description |
|---------|-------------|
| `guardkit autobuild task TASK-XXX` | Build single task |
| `guardkit autobuild feature FEAT-XXX` | Build feature with waves |
| `guardkit autobuild status [ID]` | Check build status |
| `guardkit autobuild complete ID` | Merge to main branch |

### Syntax

```bash
# Single task
guardkit autobuild task TASK-XXX [OPTIONS]

# Feature
guardkit autobuild feature FEAT-XXX [OPTIONS]
```

### Examples

```bash
# Basic execution
guardkit autobuild task TASK-AUTH-001

# With options
guardkit autobuild task TASK-AUTH-001 --max-turns 10 --verbose

# Debug logging for troubleshooting
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-AUTH-001

# Feature mode with parallel execution
guardkit autobuild feature FEAT-A1B2 --parallel 2

# Background execution
guardkit autobuild feature FEAT-A1B2 &

# Check status
guardkit autobuild status FEAT-A1B2

# Complete after review
guardkit autobuild complete FEAT-A1B2
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUARDKIT_LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `GUARDKIT_SDK_TIMEOUT` | `300` | Claude SDK timeout in seconds |
| `GUARDKIT_MAX_TURNS` | `5` | Default max Player-Coach iterations |

### Advantages

1. **Full Debug Logging**: Access complete execution logs with `GUARDKIT_LOG_LEVEL=DEBUG`
2. **Background Execution**: Run builds while doing other work
3. **CI/CD Integration**: Use in scripts and pipelines
4. **Environment Control**: Full control over environment variables
5. **Batch Operations**: Script multiple builds sequentially or in parallel

### Limitations

1. **No Conversational Context**: No AI guidance or interpretation
2. **Manual Troubleshooting**: Must interpret errors yourself
3. **Setup Required**: Requires pip installation

---

## Feature Comparison by Use Case

### Development Workflow (Recommended: Claude Code)

For day-to-day development work:

```bash
# In Claude Code session
/feature-build TASK-AUTH-001 --verbose

# Claude provides:
# - Pre-execution guidance
# - Progress interpretation
# - Post-execution review assistance
# - Troubleshooting help
```

### Debugging a Failed Build (Recommended: CLI)

When a build fails and you need detailed logs:

```bash
# Get full debug output
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-AUTH-001 --verbose 2>&1 | tee build.log

# Analyze the log
grep -i "error\|failed\|exception" build.log
```

### CI/CD Pipeline (Recommended: CLI)

In automated pipelines:

```yaml
# .github/workflows/feature-build.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install GuardKit
        run: pip install guardkit-py[autobuild]
      - name: Build Feature
        run: |
          guardkit autobuild feature ${{ github.event.inputs.feature_id }} \
            --max-turns 10 \
            --stop-on-failure
        env:
          GUARDKIT_LOG_LEVEL: INFO
```

### Long-Running Feature Builds (Recommended: CLI)

For features with many tasks:

```bash
# Start in background
nohup guardkit autobuild feature FEAT-LARGE --verbose > build.log 2>&1 &

# Check progress periodically
tail -f build.log

# Or use status command
guardkit autobuild status FEAT-LARGE
```

### Quick Single Task (Either)

For simple tasks, both work equally well:

```bash
# Claude Code
/feature-build TASK-FIX-123

# CLI
guardkit autobuild task TASK-FIX-123
```

---

## Output Comparison

### Claude Code Output

```
══════════════════════════════════════════════════════════════
FEATURE BUILD: TASK-AUTH-001
══════════════════════════════════════════════════════════════

Task: Implement authentication service
Max Turns: 5

Turn 1/5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Player: Implementing...
Coach: Validating... ✓ APPROVED

══════════════════════════════════════════════════════════════
RESULT: SUCCESS
══════════════════════════════════════════════════════════════

Worktree: .guardkit/worktrees/TASK-AUTH-001

Next Steps:
  1. Review: cd .guardkit/worktrees/TASK-AUTH-001 && git diff main
  2. Merge: git checkout main && git merge autobuild/TASK-AUTH-001
```

### CLI Output (with DEBUG)

```
2026-01-24 10:30:15 DEBUG [agent_invoker] Creating player agent...
2026-01-24 10:30:15 DEBUG [agent_invoker] SDK timeout: 300s
2026-01-24 10:30:15 DEBUG [agent_invoker] Tools: ['Read', 'Write', 'Edit', 'Bash', ...]
2026-01-24 10:30:16 INFO  [autobuild] Starting turn 1/5
2026-01-24 10:30:16 DEBUG [player] Executing task-work --implement-only --mode=tdd
2026-01-24 10:31:45 DEBUG [player] Phase 3: Implementation complete
2026-01-24 10:32:10 DEBUG [player] Phase 4: Tests passing (12/12)
2026-01-24 10:32:15 DEBUG [player] Phase 5: Code review approved
2026-01-24 10:32:16 INFO  [autobuild] Player turn complete, invoking coach
2026-01-24 10:32:20 DEBUG [coach] Validating acceptance criteria...
2026-01-24 10:32:25 DEBUG [coach] All criteria satisfied
2026-01-24 10:32:25 INFO  [autobuild] Coach APPROVED
2026-01-24 10:32:25 INFO  [autobuild] Build complete: SUCCESS (1 turn)

══════════════════════════════════════════════════════════════
FEATURE BUILD: TASK-AUTH-001 - SUCCESS
══════════════════════════════════════════════════════════════

Worktree: .guardkit/worktrees/TASK-AUTH-001
```

---

## Workflow Integration

### Hybrid Approach (Recommended for Most Users)

Combine both interfaces for optimal workflow:

1. **Start with Claude Code** for planning and initial builds
2. **Switch to CLI** for debugging or batch operations
3. **Return to Claude Code** for review and merge guidance

```bash
# Step 1: Plan in Claude Code
/feature-plan "Add OAuth2 authentication"

# Step 2: Build via CLI for better logging
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-A1B2 --verbose

# Step 3: Back to Claude Code for review
# "Help me review the changes in .guardkit/worktrees/FEAT-A1B2"

# Step 4: Complete via CLI or Claude Code
guardkit autobuild complete FEAT-A1B2
# OR
# "Merge the FEAT-A1B2 worktree to main"
```

---

## Summary

| Scenario | Recommended |
|----------|-------------|
| Interactive development | Claude Code |
| Debugging failures | CLI with DEBUG |
| CI/CD pipelines | CLI |
| Background execution | CLI |
| Quick tasks | Either |
| Learning the system | Claude Code |
| Batch operations | CLI |

Both interfaces are fully equivalent in functionality. Choose based on your immediate needs:
- **Need guidance or context?** → Claude Code
- **Need logs or automation?** → CLI

---

## See Also

- [AutoBuild Workflow Guide](autobuild-workflow.md) - Comprehensive AutoBuild documentation
- [AutoBuild Architecture](../deep-dives/autobuild-architecture.md) - Technical deep-dive
- [GuardKit Workflow Guide](guardkit-workflow.md) - Core task-work phases

---

**Version**: 1.0.0 | **License**: MIT
