# System Overview Command Guide

Get a quick architectural summary of your project from Graphiti.

## Quick Start

```bash
/system-overview
```

## What It Does

Displays a condensed view of your project's components, ADRs, cross-cutting concerns, and tech stack - all pulled from Graphiti's knowledge graph. Think of it as "remind me where I am" for architecture.

## Prerequisites

- Run `/system-plan` at least once to capture architecture context
- (Optional) Graphiti stack running for live queries

## Usage

```bash
/system-overview [--verbose] [--section=SECTION] [--format=FORMAT]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--verbose` | Include full descriptions for all sections | Off |
| `--section` | Filter to specific section: `components`, `decisions`, `crosscutting`, `stack`, `all` | `all` |
| `--format` | Output format: `display`, `markdown`, `json` | `display` |

## Examples

### Basic Overview

```bash
/system-overview
```

**Output:**
```
======================================================================
SYSTEM OVERVIEW: My Project
======================================================================

SYSTEM CONTEXT:
  Purpose: CLI tool for task management with quality gates
  Methodology: Modular
  Users: Developers, AI agents

COMPONENTS (5):
  - CLI Parser: Command routing, argument validation
  - Planning Engine: Question flow, markdown generation
  - Graphiti Integration: Persist architecture context
  - Task Manager: Task state management
  - Quality Gates: Test and coverage enforcement

ARCHITECTURE DECISIONS (3):
  - ADR-001: Use Click for CLI (active)
  - ADR-002: YAML for config files (active)
  - ADR-003: Graphiti for knowledge storage (active)

CROSS-CUTTING CONCERNS (2):
  - Logging: Structured logging with [Module] prefixes
  - Error Handling: Graceful degradation for external services

======================================================================
```

### Verbose Mode

Get full descriptions for each component and ADR:

```bash
/system-overview --verbose
```

### Filter to Specific Section

Only show components:

```bash
/system-overview --section=components
```

Only show architecture decisions:

```bash
/system-overview --section=decisions
```

### JSON Output for Scripting

```bash
/system-overview --format=json
```

Returns structured JSON with `system`, `components`, `decisions`, and `concerns` objects.

## Integration with Other Commands

### Typical Workflow

```bash
# 1. Get oriented at start of session
/system-overview

# 2. Analyze impact of planned work
/impact-analysis TASK-042

# 3. Plan a feature with architecture context
/feature-plan "add user notifications"
```

### With `/system-plan`

`/system-overview` reads what `/system-plan` captures:

```bash
# First time: capture architecture
/system-plan "project description"

# Later: quick refresh
/system-overview
```

### With `/task-work`

Review architecture before implementing:

```bash
/system-overview              # Quick refresh
/task-work TASK-042           # Start implementation
```

## Graceful Degradation

### No Architecture Context

If `/system-plan` hasn't been run yet:

```
======================================================================
NO ARCHITECTURE CONTEXT
======================================================================

No architecture information found for this project.

NEXT STEPS:
  1. Run /system-plan "project description" to capture architecture
  2. Or create architecture docs manually in docs/architecture/

For quick project understanding, try:
  - Read CLAUDE.md for project conventions
  - Check docs/architecture/ for existing documentation
======================================================================
```

### Graphiti Unavailable

If Graphiti service is not running:

```
======================================================================
ARCHITECTURE CONTEXT UNAVAILABLE
======================================================================

Cannot query Graphiti for architecture information.

ALTERNATIVES:
  - Read docs/architecture/ARCHITECTURE.md directly
  - Check CLAUDE.md for project conventions
  - Run /system-plan when Graphiti is available

To configure Graphiti:
  pip install guardkit-py[graphiti]
======================================================================
```

## Troubleshooting

### "No architecture context" but I ran /system-plan

- Verify Graphiti is running: `guardkit graphiti status`
- Check seeding: `guardkit graphiti verify`
- Re-run system-plan: `/system-plan "project" --force`

### Sections showing as empty

- Some projects may not have ADRs or cross-cutting concerns defined
- Use `--verbose` to see what data exists
- Run `/system-plan` again to capture more detail

### Output is stale

Architecture context reflects the last `/system-plan` run. To update:

```bash
/system-plan "project" --mode=review
```

## See Also

- [Impact Analysis Guide](impact-analysis-guide.md) - Pre-task validation with risk scoring
- [Context Switch Guide](context-switch-guide.md) - Multi-project navigation
- [Graphiti Commands](graphiti-commands.md) - CLI commands for knowledge management
