# Default Template - Language-Agnostic GuardKit

Version: 2.0.0
Last Updated: 2025-11-09

## Overview

The **default** template is a minimal, language-agnostic starting point for GuardKit projects that don't fit into specialized templates. It provides the core GuardKit workflow without stack-specific constraints.

## Purpose

Use this template for:

1. **Unsupported Languages**: Go, Rust, Ruby, PHP, Kotlin, Swift, Elixir, Scala, etc.
2. **Custom Stacks**: Unique technology combinations
3. **Prototyping**: Exploring GuardKit before committing to a stack
4. **Template Development**: Building custom templates with `/template-create`

**Do NOT use for well-supported stacks** - use specialized templates instead:
- React → `react` template
- Python → `python` template
- TypeScript API → `typescript-api` template
- .NET MAUI → `maui-appshell` or `maui-navigationpage`
- .NET API → `dotnet-fastendpoints` or `dotnet-minimalapi`

## What's Included

### Directory Structure
```
.claude/
├── agents/          # Empty - add your own stack-specific agents
├── commands/        # Symlinked from global installation
├── templates/       # Empty - add your own code templates
└── settings.json    # Documentation level + quality gate configuration

tasks/               # Task management (created on init)
├── backlog/
├── in_progress/
├── in_review/
├── blocked/
└── completed/

docs/                # Documentation (created as needed)
├── guides/
└── state/
```

### Configuration

**settings.json** includes:
- **Documentation Level System**: Auto-adjust detail based on complexity
- **Quality Gates**: Compilation, tests, coverage, architecture, plan audit
- **Workflow Phases**: 2, 2.5, 2.7, 2.8, 3, 4, 4.5, 5, 5.5
- **Stack Placeholders**: Add your language/framework specifics
- **Customization Paths**: Agents, templates, linting, formatting

### Available Commands

All core GuardKit commands work out of the box:

```bash
# Task lifecycle
/task-create "Feature description" [priority:high|medium|low]
/task-work TASK-XXX [--mode=standard|tdd]
/task-complete TASK-XXX
/task-status [TASK-XXX]

# Design-first workflow (complex tasks)
/task-work TASK-XXX --design-only
/task-work TASK-XXX --implement-only

# Micro-task workflow (trivial tasks)
/task-work TASK-XXX --micro

# Utilities
/debug
```

## Installation

### Initialize Project

```bash
# Initialize with default template
guardkit init default

# Or specify path
guardkit init default --path /path/to/project
```

This creates:
- `.claude/` directory with configuration
- `tasks/` directory with state folders
- Symlinks to global commands

### Verify Installation

```bash
# Check structure
ls -la .claude/
ls -la tasks/

# Test a command
/task-status
```

## Customization

### Quick Start Configuration

Edit `.claude/settings.json` to add stack-specific settings:

```json
{
  "stack": {
    "language": "go",
    "framework": "gin",
    "testing": {
      "enabled": true,
      "command": "go test ./...",
      "coverage_command": "go test -cover ./...",
      "min_coverage": 80
    },
    "linting": {
      "enabled": true,
      "command": "golangci-lint run"
    }
  }
}
```

### Add Stack-Specific Agents

Create agents in `.claude/agents/`:

```bash
# Example: Go API agent
touch .claude/agents/go-api-specialist.md
```

Agent format:
```markdown
# Go API Specialist

You are an expert in Go API development...

## Responsibilities
- RESTful API design
- Middleware implementation
- Error handling patterns
...
```

### Add Code Templates

Create templates in `.claude/templates/`:

```bash
# Example: Go HTTP handler template
touch .claude/templates/http-handler.go.template
```

### Advanced Customization

For reusable templates with multiple projects:

```bash
# Create custom template interactively
/template-create

# Follow prompts for:
# - Stack identification
# - Agent generation
# - Template creation
# - Quality gate configuration
```

See [Creating Local Templates](../../../docs/guides/creating-local-templates.md) for details.

## Usage Examples

### Example 1: Go Project

```bash
# Initialize
guardkit init default

# Customize settings.json
{
  "stack": {
    "language": "go",
    "testing": {
      "command": "go test ./...",
      "coverage_command": "go test -cover ./..."
    }
  }
}

# Start working
/task-create "Add user authentication endpoint"
/task-work TASK-001
```

### Example 2: Rust Project

```bash
# Initialize
guardkit init default

# Customize settings.json
{
  "stack": {
    "language": "rust",
    "testing": {
      "command": "cargo test",
      "coverage_command": "cargo tarpaulin"
    },
    "linting": {
      "command": "cargo clippy"
    }
  }
}

# Start working
/task-create "Implement authentication service"
/task-work TASK-001 --mode=tdd
```

### Example 3: Custom Stack (Elixir + Phoenix)

```bash
# Initialize
guardkit init default

# Customize settings.json
{
  "stack": {
    "language": "elixir",
    "framework": "phoenix",
    "testing": {
      "command": "mix test",
      "coverage_command": "mix test --cover"
    }
  }
}

# Create custom agent
cat > .claude/agents/elixir-phoenix-specialist.md << 'EOF'
# Elixir Phoenix Specialist

You are an expert in Elixir and Phoenix framework...
EOF

# Start working
/task-create "Add GraphQL API endpoint"
/task-work TASK-001
```

## Quality Gates

The default template includes all GuardKit quality gates:

| Gate | Threshold | Blocking | Description |
|------|-----------|----------|-------------|
| **Compilation** | 100% | Yes | Must compile (language-dependent) |
| **Tests Pass** | 100% | Yes | All tests must pass (Phase 4.5) |
| **Coverage** | ≥80% | No | Line coverage (recommended) |
| **Architecture** | ≥60/100 | No | SOLID/DRY/YAGNI score (Phase 2.5) |
| **Plan Audit** | 0 violations | No | Scope creep detection (Phase 5.5) |

Customize thresholds in `settings.json`:

```json
{
  "quality_gates": {
    "tests": {
      "pass_rate": 100,
      "blocking": true
    },
    "coverage": {
      "line_coverage": 85,
      "blocking": true
    }
  }
}
```

## Documentation Levels

The template supports three documentation levels:

### Minimal (Complexity 1-3)
- Quick summaries
- Embedded results
- Fast execution (8-12 min)
- 2 files generated

### Standard (Complexity 4-10) - DEFAULT
- Full reports
- Comprehensive coverage
- Balanced execution (12-18 min)
- 2-5 files generated

### Comprehensive (Complexity 7-10 or Triggers)
- Standalone documents
- Enhanced analysis
- Thorough execution (36+ min)
- 13+ files generated

**Force triggers**: security, authentication, compliance, breaking changes

Control via flags:
```bash
/task-work TASK-001 --docs minimal
/task-work TASK-002 --docs comprehensive
```

## Migration Path

When ready for more structure:

### Migrate to Specialized Template

```bash
# 1. Backup state
cp -r .claude/state/ ../backup/
cp -r tasks/ ../backup/
cp -r docs/ ../backup/

# 2. Reinitialize with specialized template
guardkit init react  # or python, typescript-api, etc.

# 3. Restore state
cp -r ../backup/state/ .claude/
cp -r ../backup/tasks/ .
cp -r ../backup/docs/ .
```

### Create Custom Template

```bash
# Use existing project as basis
/template-create

# Or specify source
/template-create --from-directory .

# Save to personal templates
# Location: ~/.agentecflow/templates/my-custom-template
```

See [Template Migration Guide](../../../docs/guides/template-migration.md) for complete instructions.

## Troubleshooting

### Issue: Commands not found

**Symptom**: `/task-create` returns "command not found"

**Solution**:
```bash
# Verify symlinks
ls -la .claude/commands/

# If missing, reinitialize
guardkit init default --force
```

### Issue: Tests not running

**Symptom**: Phase 4 skips test execution

**Solution**: Add test command to `settings.json`:
```json
{
  "stack": {
    "testing": {
      "enabled": true,
      "command": "your-test-command"
    }
  }
}
```

### Issue: Quality gates too strict

**Symptom**: Tasks blocked by coverage/architecture scores

**Solution**: Adjust thresholds in `settings.json`:
```json
{
  "quality_gates": {
    "coverage": {
      "line_coverage": 70,
      "blocking": false
    }
  }
}
```

## Best Practices

1. **Migrate Early**: Don't stay on default template longer than needed
2. **Configure Tests**: Add test commands immediately after initialization
3. **Create Templates**: Use `/template-create` for repeated patterns
4. **Leverage Documentation Levels**: Use `--docs minimal` for simple tasks
5. **Use Specialized Templates**: Default is for unsupported stacks only

## Support

- **Template Guide**: [Creating Local Templates](../../../docs/guides/creating-local-templates.md)
- **Migration Guide**: [Template Migration Guide](../../../docs/guides/template-migration.md)
- **Main Documentation**: Root `CLAUDE.md` in repository
- **Issue Tracker**: GitHub Issues

## Changelog

### 2.0.0 (2025-11-09)
- Reinstated default template with quality improvements
- Added comprehensive settings.json configuration
- Added README.md usage guide
- Improved CLAUDE.md with clear use case guidance
- Added quality score target: 8.0/10 (from 6.0/10)
- Clarified language-agnostic philosophy
- Added migration path documentation

### 1.0.0 (Historical)
- Initial default template
- Basic configuration
- Removed in template consolidation

## License

Part of the GuardKit project. See root LICENSE file.
