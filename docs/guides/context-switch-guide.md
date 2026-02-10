# Context Switch Command Guide

Switch between projects without losing architectural context.

## Quick Start

```bash
/context-switch power-of-attorney
```

## What It Does

Switches the active project context in GuardKit and displays an orientation summary. It updates which project's architecture is loaded in Graphiti, shows active tasks, and gets you oriented for work - all without changing git branches or filesystem paths.

**Important**: `/context-switch` only updates the *Graphiti namespace* and config. It does NOT:
- Change your git branch
- Move you to a different directory
- Modify any project files

## Prerequisites

- GuardKit initialized: `guardkit init`
- Projects registered in `.guardkit/config.yaml`
- (Optional) Graphiti for architecture context

## Usage

```bash
/context-switch [project-name]
/context-switch --list
```

| Command | Description |
|---------|-------------|
| `/context-switch` | Show current project context |
| `/context-switch --list` | List all known projects |
| `/context-switch <name>` | Switch to named project |

## Examples

### List Known Projects

See all projects you can switch between:

```bash
/context-switch --list
```

**Output:**
```
======================================================================
KNOWN PROJECTS
======================================================================

  * guardkit (active)
      Path: /Users/dev/projects/guardkit
      Last accessed: 2026-02-10 14:30

    power-of-attorney
      Path: /Users/dev/projects/poa-platform
      Last accessed: 2026-02-09 16:45

    weather-api
      Path: /Users/dev/projects/weather-api
      Last accessed: 2026-02-08 10:00

======================================================================
Switch context: /context-switch <project-name>
======================================================================
```

### Show Current Context

Check which project is active:

```bash
/context-switch
```

**Output:**
```
======================================================================
CURRENT PROJECT: guardkit
======================================================================

PATH: /Users/dev/projects/guardkit

ARCHITECTURE:
  Methodology: Modular
  Components: 8
  ADRs: 12 (10 active)

ACTIVE TASKS (3):
  - TASK-042: Add user notifications (in_progress)
  - TASK-043: Update documentation (in_progress)
  - TASK-044: Fix test coverage (backlog)

======================================================================
Commands:
  - Overview: /system-overview
  - Impact: /impact-analysis TASK-XXX
  - Switch: /context-switch <project>
======================================================================
```

### Switch to Another Project

```bash
/context-switch power-of-attorney
```

**Output:**
```
======================================================================
CONTEXT SWITCH: guardkit -> power-of-attorney
======================================================================

PROJECT: power-of-attorney
PATH: /Users/dev/projects/poa-platform

ARCHITECTURE:
  Methodology: DDD
  Bounded Contexts: 4
  ADRs: 7 (5 active, 2 superseded)

KEY COMPONENTS:
  - Attorney Management: Donor, attorney CRUD
  - Document Generation: LPA forms, templates
  - Financial Oversight: Accounts, transactions
  - Compliance: OPG registration, verification

ACTIVE TASKS (2):
  - TASK-POA-018: Implement Moneyhub integration (in_progress)
  - TASK-POA-019: Add audit logging (backlog)

RECENT ACTIVITY:
  Last accessed: 2026-02-09 16:45
  Last completed: TASK-POA-017 (Feb 9)

======================================================================
ORIENTATION COMPLETE
======================================================================

Ready to work. Suggested next steps:
  1. Review active task: /task-status TASK-POA-018
  2. Check architecture: /system-overview
  3. Analyze impact: /impact-analysis TASK-POA-018
======================================================================
```

## Integration with Other Commands

### Typical Multi-Project Workflow

```bash
# 1. See what projects are available
/context-switch --list

# 2. Switch to target project
/context-switch power-of-attorney

# 3. Get full architecture overview
/system-overview

# 4. Check impact of planned work
/impact-analysis TASK-POA-018

# 5. Start working
/task-work TASK-POA-018
```

### With `/system-overview`

After switching, get detailed architecture:

```bash
/context-switch my-project
/system-overview --verbose
```

### Starting a New Session

Refresh context at the start of a work session:

```bash
/context-switch                    # See where you left off
/system-overview                   # Quick architecture refresh
/task-status                       # Check task states
```

## What Gets Updated

When you run `/context-switch`:

| Updated | Not Updated |
|---------|-------------|
| `active_project` in config | Git branch |
| `last_accessed` timestamp | Current directory |
| Graphiti namespace queries | Project files |
| Architecture context loaded | Environment variables |

## Configuration File

Projects are stored in `.guardkit/config.yaml`:

```yaml
active_project: guardkit

known_projects:
  - name: guardkit
    path: /Users/dev/projects/guardkit
    last_accessed: 2026-02-10T14:30:00Z

  - name: power-of-attorney
    path: /Users/dev/projects/poa-platform
    last_accessed: 2026-02-09T16:45:00Z
```

## Graceful Degradation

### No Config File

```
======================================================================
NO PROJECT CONFIGURATION
======================================================================

GuardKit config not found at .guardkit/config.yaml

This project hasn't been initialized with GuardKit yet.

TO INITIALIZE:
  guardkit init                    # Basic initialization
  guardkit init fastapi-python     # With template

This will create:
  - .guardkit/config.yaml
  - .claude/ directory
  - tasks/ directory structure
======================================================================
```

### Unknown Project

```
======================================================================
PROJECT NOT FOUND: my-new-project
======================================================================

'my-new-project' is not in known projects.

KNOWN PROJECTS:
  - guardkit
  - power-of-attorney
  - weather-api

TO ADD A NEW PROJECT:
  1. Navigate to project directory: cd /path/to/my-new-project
  2. Initialize GuardKit: guardkit init
  3. The project will be added to known_projects automatically

Or add manually to .guardkit/config.yaml
======================================================================
```

### Graphiti Unavailable

When Graphiti isn't running, architecture context won't load:

```
======================================================================
CONTEXT SWITCH: guardkit -> power-of-attorney
======================================================================

PROJECT: power-of-attorney
PATH: /Users/dev/projects/poa-platform

ARCHITECTURE:
  [Graphiti unavailable - architecture context not loaded]
  Check docs/architecture/ARCHITECTURE.md manually

ACTIVE TASKS (2):
  - TASK-POA-018: Implement Moneyhub integration (in_progress)
  - TASK-POA-019: Add audit logging (backlog)

======================================================================
Note: Architecture context unavailable. Run /system-plan when ready.
======================================================================
```

## Troubleshooting

### "Project not found" for known project

- Check exact spelling: names are case-sensitive
- Verify config file: `cat .guardkit/config.yaml`
- Re-initialize if needed: `guardkit init`

### Architecture showing as unavailable

- Verify Graphiti is running: `guardkit graphiti status`
- Check project has been seeded: `guardkit graphiti verify`
- Run system-plan: `/system-plan "project"`

### Tasks not showing after switch

- Ensure `tasks/` directory exists at project path
- Check task file naming: `TASK-*.md`
- Verify config `path` points to correct directory

### Adding a new project manually

Edit `.guardkit/config.yaml`:

```yaml
known_projects:
  # ... existing projects
  - name: new-project
    path: /Users/dev/projects/new-project
    last_accessed: null
```

## See Also

- [System Overview Guide](system-overview-guide.md) - Architecture summary for current project
- [Impact Analysis Guide](impact-analysis-guide.md) - Pre-task validation with risk scoring
- [Graphiti Commands](graphiti-commands.md) - CLI commands for knowledge management
