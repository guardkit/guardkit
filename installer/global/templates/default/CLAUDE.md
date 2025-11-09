# Taskwright - Default Template

## When to Use This Template

The **default** template is a **language-agnostic** starting point for projects that don't fit Taskwright's specialized templates. Use this template if:

1. **Language Not Yet Supported**: Working with Go, Rust, Ruby, PHP, Kotlin, Swift, etc.
2. **Custom Tech Stack**: Unique combination of technologies not covered by existing templates
3. **Learning/Prototyping**: Exploring Taskwright's workflow before committing to a specific stack
4. **Template Development**: Building a custom template using `/template-create`

## When NOT to Use This Template

**DO NOT use the default template if** you're working with these well-supported stacks:

- **React/TypeScript** → Use `react` template
- **Python/FastAPI** → Use `python` template
- **TypeScript/NestJS** → Use `typescript-api` template
- **.NET MAUI** → Use `maui-appshell` or `maui-navigationpage` template
- **.NET API** → Use `dotnet-fastendpoints` or `dotnet-minimalapi` template
- **Full-Stack (React + Python)** → Use `fullstack` template

**Why?** Specialized templates provide:
- Stack-specific quality gates
- Technology-appropriate testing frameworks
- Pre-configured agents and workflows
- Optimized for language/framework best practices

## What This Template Provides

### Minimal Structure
```
.claude/                    # Configuration
├── agents/                # (Empty - add your own)
├── commands/              # (Symlinked from global)
├── templates/             # (Empty - add your own)
└── settings.json          # Documentation level configuration

tasks/                      # Task management
├── backlog/
├── in_progress/
├── in_review/
├── blocked/
└── completed/

docs/                       # Documentation
├── guides/                # (Created as needed)
└── state/                 # (Created as needed)
```

### Core Taskwright Workflow
All core commands are available via global symlinks:
```bash
/task-create "Feature description"
/task-work TASK-XXX
/task-complete TASK-XXX
/task-status
```

### Documentation Level System
The template includes `settings.json` with documentation level configuration:
- **Minimal** (complexity 1-3): Quick summaries, embedded results
- **Standard** (complexity 4-10): Full reports, comprehensive coverage
- **Comprehensive** (complexity 7-10 or triggers): Standalone documents, enhanced analysis

## Getting Started

### 1. Initialize with Default Template
```bash
taskwright init default
```

### 2. Customize for Your Stack
Add stack-specific configuration:

**For testing:**
- Add test commands to `.claude/settings.json` (if needed)
- Configure test runners for your language

**For agents:**
- Add stack-specific agents to `.claude/agents/` (optional)
- Use `/template-create` for systematic agent generation

**For templates:**
- Add code templates to `.claude/templates/` (optional)

### 3. Start Working
```bash
/task-create "Your first task"
/task-work TASK-001
```

## Customization Path

### Quick Customization
For simple projects, add minimal configuration:

```json
// .claude/settings.json (extend the default)
{
  "documentation": { ... },
  "stack": {
    "language": "go",
    "testing": {
      "command": "go test ./...",
      "coverage_command": "go test -cover ./..."
    }
  }
}
```

### Full Template Creation
For reusable templates, use `/template-create`:

```bash
# Interactive template creation
/template-create

# Follow prompts to create a complete template with:
# - Agents
# - Commands
# - File templates
# - Configuration
# - Testing infrastructure
```

See [Creating Local Templates](../../../docs/guides/creating-local-templates.md) for details.

## Core Taskwright Workflow

The default template includes the complete Taskwright workflow:

### Phase Execution
```
Phase 1: Requirements Analysis (skipped in Taskwright)
Phase 2: Implementation Planning
Phase 2.5: Architectural Review
Phase 2.7: Complexity Evaluation
Phase 2.8: Human Checkpoint (if needed)
Phase 3: Implementation
Phase 4: Testing
Phase 4.5: Test Enforcement
Phase 5: Code Review
Phase 5.5: Plan Audit
```

### Quality Gates
- **Compilation**: 100% (language-dependent)
- **Tests Pass**: 100% (enforced)
- **Coverage**: ≥80% (recommended)
- **Architecture**: ≥60/100
- **Plan Compliance**: 0 violations

## Migration to Specialized Template

When your project matures or you add team members, migrate to a specialized template:

1. **Identify your stack**: React, Python, .NET, etc.
2. **Generate new template**: Use `/template-create` or use existing template
3. **Preserve state**: Copy `.claude/state/`, `tasks/`, `docs/`
4. **Reinitialize**: `taskwright init <specialized-template>`

See [Template Migration Guide](../../../docs/guides/template-migration.md) for details.

## Project Standards

### Code Quality
- **Test coverage** recommended but not enforced (language-dependent)
- **Quality gates** active for all phases
- **Test execution** verified in Phase 4

### Documentation
- **ADRs** for architectural decisions
- **Task tracking** in markdown
- **Implementation plans** in `.claude/task-plans/`

### Testing Philosophy
**"Implementation and testing are inseparable"** - Every implementation should include tests, though specific frameworks are stack-dependent.

## Best Practices

1. **Use specialized templates when possible** - Better tooling and quality gates
2. **Add stack-specific configuration early** - Don't delay customization
3. **Create reusable templates** - Use `/template-create` for repeated patterns
4. **Leverage documentation levels** - Adjust detail based on task complexity
5. **Migrate when ready** - Don't stay on default longer than needed

## Support and Documentation

- **User Guide**: See root `CLAUDE.md` for complete Taskwright documentation
- **Template Guide**: [Creating Local Templates](../../../docs/guides/creating-local-templates.md)
- **Migration Guide**: [Template Migration Guide](../../../docs/guides/template-migration.md)

## Philosophy

The default template embodies Taskwright's philosophy:

**"Start simple, scale as needed"**

It provides the core workflow without imposing stack-specific constraints, allowing you to:
- Explore Taskwright with any language
- Build custom templates for specialized stacks
- Prototype quickly before committing to structure
- Develop in languages not yet supported by built-in templates

When you're ready for more structure, migrate to a specialized template or create your own using `/template-create`.
