# Troubleshooting

Common issues and solutions for GuardKit workflows.

## Quick Reference

**First Steps:**

1. Run `/debug` to check your configuration
2. Check the [Common Issues](#common-issues) section below
3. Review [Command-Specific Troubleshooting](#command-specific-troubleshooting)
4. [Report an issue](https://github.com/guardkit/guardkit/issues) if problem persists

## Common Issues

### Installation & Setup

**Symlinks Not Working**

If slash commands fail with "file not found":

```bash
# Check symlink exists
ls -l ~/.agentecflow/bin/agent-enhance

# Verify target is valid
readlink ~/.agentecflow/bin/agent-enhance

# Re-run installation
cd ~/Projects/guardkit
./installer/scripts/install.sh
```

**Permission Denied**

If you get permission errors:

```bash
# Make scripts executable
chmod +x ~/.agentecflow/bin/*

# Or re-run installation
./installer/scripts/install.sh
```

**Template Initialization Fails**

If `guardkit init` fails:

```bash
# Check available templates
guardkit init --list

# Verify template exists
ls -la installer/global/templates/

# Re-run with verbose output
/debug
```

### Task Workflow Issues

**Task Not Moving Between States**

If `/task-complete` doesn't move files:

1. Check you're in the correct directory (repo root)
2. Verify task exists: `ls tasks/in_progress/`
3. Check git status: `git status`
4. Run `/debug` to check configuration

**Quality Gates Failing**

If tests or coverage checks fail:

1. **Compilation Errors**: Fix build issues first
2. **Test Failures**: Check Phase 4.5 auto-fix attempts (max 3)
3. **Coverage Below Threshold**: Add more tests (≥80% line, ≥75% branch)
4. **Architectural Review**: Review Phase 2.5 report (≥60/100 required)

**Task Stuck in BLOCKED State**

Causes and solutions:

- **Tests failing**: Check test output, fix failures
- **Build errors**: Fix compilation issues
- **Coverage too low**: Add tests to meet thresholds
- **Review required**: Human checkpoint needed (complexity ≥7)

### Conductor Integration

**Worktree Commands Failing**

If commands fail in Conductor worktrees:

```bash
# Verify symlinks
ls -l ~/.agentecflow/

# Check state directory
ls -la .claude/state/

# Re-run installation
./installer/scripts/install.sh
```

**State Not Syncing Across Worktrees**

GuardKit state is auto-committed on every command. If state isn't syncing:

1. Check symlinks: `ls -l .claude/`
2. Verify auto-commit working: `git log .claude/state/`
3. Pull latest from main: `git pull origin main`

### Template & Agent Issues

**Agent Discovery Not Finding Specialists**

If tasks always use task-manager:

1. Check agent frontmatter metadata (stack, phase, keywords)
2. Verify agents exist: `ls .claude/agents/`
3. Run `/agent-validate` on agents
4. Check task file extensions match stack

**Template Validation Failing**

If `/template-validate` reports errors:

- **Level 1 (Automatic)**: Auto-fix enabled, should resolve automatically
- **Level 2 (Extended)**: Review validation report in template directory
- **Level 3 (Comprehensive)**: Use interactive audit to fix issues

### MCP Integration Issues

**MCP Server Not Responding**

If context7 or design-patterns MCP fails:

```bash
# Check MCP configuration
cat ~/.claude/mcp-config.json

# Verify MCP server running
npx -y @context7/mcp-server --help

# Re-install MCP
# See: docs/deep-dives/mcp-integration/context7-setup.md
```

## Command-Specific Troubleshooting

### /task-work Issues

**Phase 2.5 Architectural Review Fails**

If SOLID/DRY/YAGNI score <60/100:

1. Review architectural recommendations
2. Choose [R]evise to modify plan
3. Address flagged issues before proceeding

**Phase 4.5 Test Enforcement Loop**

If tests fail repeatedly (3 attempts):

1. Check test output for root cause
2. Verify environment setup (dependencies installed)
3. Fix manually if auto-fix can't resolve
4. Use `/debug` to check test runner configuration

### /task-review Issues

**Review Takes Too Long**

Adjust depth level:

- Use `--depth=quick` (15-30 min) for initial assessments
- Use `--depth=standard` (1-2 hours) for regular reviews
- Reserve `--depth=comprehensive` (4-6 hours) for security audits

**Model Selection Unexpected**

Review uses Opus 4.5 for:

- All security reviews (any depth)
- Comprehensive architectural reviews
- Decision analysis (standard/comprehensive)

Use Sonnet 4.5 for faster, cheaper reviews when appropriate.

### /template-create Issues

**Agent Tasks Not Created**

By default, `/template-create` creates agent enhancement tasks. If not created:

1. Check for `--no-create-agent-tasks` flag (opt-out)
2. Verify template has agents
3. Run `/debug` to check configuration

**Validation Fails**

If template validation fails:

1. Check CRUD completeness (all layers present)
2. Verify layer symmetry (consistent patterns)
3. Review placeholder consistency
4. See validation report in template directory

## Deep-Dive Troubleshooting

### Debug Command

Use `/debug` to diagnose configuration issues:

```bash
/debug
```

**What It Checks:**

- Installation status (symlinks, directories)
- Configuration files (templates, agents, commands)
- Git repository status
- Conductor integration
- MCP server configuration
- Task state directory
- Test runner setup

**[/debug Command Reference](https://github.com/guardkit/guardkit/blob/main/installer/global/commands/debug.md)**

## Getting Help

### Before Reporting Issues

1. Run `/debug` and include output
2. Check git status: `git status`
3. Check recent commits: `git log --oneline -5`
4. Include error messages verbatim
5. Specify which command failed

### Reporting Issues

**[Create an Issue on GitHub](https://github.com/guardkit/guardkit/issues)**

**Include:**

- Output from `/debug`
- Command that failed (full command with arguments)
- Error message (full text)
- Operating system (macOS, Linux, Windows)
- Project type (React, Python, .NET, etc.)
- Relevant git log (if task workflow issue)

### Community Support

- **GitHub Issues**: [guardkit/issues](https://github.com/guardkit/guardkit/issues)
- **GitHub Discussions**: [guardkit/discussions](https://github.com/guardkit/guardkit/discussions)

---

## Next Steps

- **Run Diagnostics**: Use `/debug` to check your setup
- **Review Workflow**: [GuardKit Workflow Guide](guides/guardkit-workflow.md)
- **Check Commands**: [Command Reference](https://github.com/guardkit/guardkit/tree/main/installer/global/commands)
