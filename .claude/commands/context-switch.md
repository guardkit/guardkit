# /context-switch - Multi-Project Navigation

Switches the active project context and displays an orientation summary. Enables seamless navigation between multiple projects managed by GuardKit.

## Command Syntax

```bash
/context-switch [project-name]
/context-switch --list
```

## Available Flags

| Flag | Description |
|------|-------------|
| `--list` | List all known projects without switching |
| (no args) | Display current project context |

## Overview

The `/context-switch` command enables developers and AI agents to navigate between multiple projects managed by GuardKit. It:

- **Switches** the active project context in `.guardkit/config.yaml`
- **Loads** the target project's architecture summary from Graphiti
- **Displays** an orientation summary (active tasks, key components)
- **Updates** the `last_accessed` timestamp for tracking

**Use cases:**
- Working on multiple projects in one session
- Returning to a project after time away
- Quick context refresh at session start

## Execution Flow

### Phase 1: Load Configuration

**LOAD** GuardKit config:

```python
from guardkit.planning.context_switch import GuardKitConfig

config = GuardKitConfig()

# Get current active project
current = config.active_project
known = config.list_known_projects()
```

### Phase 2: Handle Mode

**DETERMINE** operation mode:

```python
if "--list" in flags:
    mode = "list"
elif not args:
    mode = "current"
else:
    mode = "switch"
    target_project = args[0]
```

### Phase 3: Execute Operation

#### List Mode (--list)

```python
from guardkit.planning.context_switch import format_context_switch_display

projects = config.list_known_projects()
output = format_context_switch_display(projects, mode="list", current=current)
print(output)
```

#### Current Mode (no args)

```python
if not current:
    print(NO_PROJECT_MESSAGE)
    return

output = format_context_switch_display(
    current,
    mode="current",
    active_tasks=_find_active_tasks(current.get("path"))
)
print(output)
```

#### Switch Mode (project-name)

```python
from guardkit.planning.context_switch import execute_context_switch

# Validate target exists
target = config.get_known_project(target_project)
if not target:
    print(f"ERROR: Project '{target_project}' not found")
    print("\nKnown projects:")
    for p in known:
        print(f"  - {p['name']}")
    return

# Execute switch
result = execute_context_switch(client, target_project, config)

# Display orientation
output = format_context_switch_display(result, mode="switch")
print(output)
```

## Output Format

### List Mode (--list)

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

### Current Mode (no args)

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

### Switch Mode (project-name)

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

## Configuration File

The `/context-switch` command reads and writes `.guardkit/config.yaml`:

```yaml
# .guardkit/config.yaml
active_project: guardkit

known_projects:
  - name: guardkit
    path: /Users/dev/projects/guardkit
    last_accessed: 2026-02-10T14:30:00Z

  - name: power-of-attorney
    path: /Users/dev/projects/poa-platform
    last_accessed: 2026-02-09T16:45:00Z

  - name: weather-api
    path: /Users/dev/projects/weather-api
    last_accessed: 2026-02-08T10:00:00Z
```

## Graceful Degradation

### No Config File

When `.guardkit/config.yaml` doesn't exist:

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

When switching to a project not in `known_projects`:

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

When Graphiti is not available (architecture context won't load):

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

## Examples

### Basic Usage

```bash
# Show current project
/context-switch

# List all known projects
/context-switch --list

# Switch to another project
/context-switch power-of-attorney
```

### Workflow Integration

```bash
# 1. See what projects are available
/context-switch --list

# 2. Switch to target project
/context-switch power-of-attorney

# 3. Get full architecture overview
/system-overview

# 4. Start working
/task-work TASK-POA-018
```

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

**IMPORTANT: Follow these steps exactly when `/context-switch` is invoked.**

### Step 1: Load Configuration

```python
from guardkit.planning.context_switch import GuardKitConfig

try:
    config = GuardKitConfig()
except FileNotFoundError:
    print(NO_CONFIG_MESSAGE)
    return

current = config.active_project
known = config.list_known_projects()
```

### Step 2: Determine Mode

```python
if "--list" in args:
    mode = "list"
elif len(args) == 0:
    mode = "current"
else:
    mode = "switch"
    target_project = args[0]
```

### Step 3: Execute Based on Mode

#### List Mode

```python
if mode == "list":
    print("=" * 70)
    print("KNOWN PROJECTS")
    print("=" * 70)
    print()

    for project in known:
        is_active = project["name"] == current.get("name") if current else False
        marker = "* " if is_active else "  "
        active_label = " (active)" if is_active else ""

        print(f"{marker}{project['name']}{active_label}")
        print(f"      Path: {project.get('path', 'N/A')}")
        print(f"      Last accessed: {project.get('last_accessed', 'Never')}")
        print()

    print("=" * 70)
    print("Switch context: /context-switch <project-name>")
    print("=" * 70)
    return
```

#### Current Mode

```python
if mode == "current":
    if not current:
        print("No active project. Run: /context-switch <project>")
        return

    # Find active tasks
    from guardkit.planning.context_switch import _find_active_tasks
    active_tasks = _find_active_tasks(current.get("path"))

    print("=" * 70)
    print(f"CURRENT PROJECT: {current['name']}")
    print("=" * 70)
    print()
    print(f"PATH: {current.get('path', 'N/A')}")
    print()

    # Try to get architecture from Graphiti
    # (graceful if unavailable)

    print("ACTIVE TASKS:")
    if active_tasks:
        for task in active_tasks[:5]:
            print(f"  - {task['id']}: {task['title']} ({task['status']})")
    else:
        print("  No active tasks")

    print()
    print("=" * 70)
    return
```

#### Switch Mode

```python
if mode == "switch":
    # Validate target exists
    target = config.get_known_project(target_project)

    if not target:
        print(f"ERROR: Project '{target_project}' not found")
        print()
        print("KNOWN PROJECTS:")
        for p in known:
            print(f"  - {p['name']}")
        print()
        print("Add with: cd /path/to/project && guardkit init")
        return

    # Execute switch
    from guardkit.planning.context_switch import execute_context_switch
    from guardkit.knowledge.graphiti_client import get_graphiti

    client = get_graphiti()

    result = execute_context_switch(client, target_project, config)

    # Display orientation
    print("=" * 70)
    print(f"CONTEXT SWITCH: {current['name'] if current else 'None'} -> {target_project}")
    print("=" * 70)
    print()
    print(f"PROJECT: {target_project}")
    print(f"PATH: {target.get('path', 'N/A')}")
    print()

    # Architecture section (from Graphiti or N/A)
    if result.get("architecture"):
        arch = result["architecture"]
        print("ARCHITECTURE:")
        print(f"  Methodology: {arch.get('methodology', 'N/A')}")
        print(f"  Components: {len(arch.get('components', []))}")
        print(f"  ADRs: {len(arch.get('decisions', []))}")
    else:
        print("ARCHITECTURE:")
        print("  [Graphiti unavailable - check docs/architecture/ manually]")

    print()

    # Active tasks
    print("ACTIVE TASKS:")
    tasks = result.get("active_tasks", [])
    if tasks:
        for task in tasks[:5]:
            print(f"  - {task['id']}: {task['title']} ({task['status']})")
    else:
        print("  No active tasks")

    print()
    print("=" * 70)
    print("ORIENTATION COMPLETE")
    print("=" * 70)
    print()
    print("Ready to work. Suggested next steps:")
    print("  1. Review architecture: /system-overview")
    print("  2. Check task status: /task-status")
    print("  3. Start working: /task-work TASK-XXX")
    print("=" * 70)
```

### What NOT to Do

- **DO NOT** switch to a project that doesn't exist in config
- **DO NOT** crash if Graphiti is unavailable - degrade gracefully
- **DO NOT** modify config without updating `last_accessed` timestamp
- **DO NOT** skip the orientation summary after switching
- **DO NOT** assume task directories exist - check before reading

### Message Constants

```python
NO_CONFIG_MESSAGE = """
======================================================================
NO PROJECT CONFIGURATION
======================================================================

GuardKit config not found at .guardkit/config.yaml

TO INITIALIZE:
  guardkit init                    # Basic initialization
  guardkit init fastapi-python     # With template
======================================================================
"""

UNKNOWN_PROJECT_MESSAGE = """
======================================================================
PROJECT NOT FOUND: {project_name}
======================================================================

'{project_name}' is not in known projects.

TO ADD A NEW PROJECT:
  1. Navigate to project directory
  2. Run: guardkit init
======================================================================
"""
```

---

## Related Commands

- `/system-overview` - Architecture summary for current project
- `/impact-analysis` - Pre-task architecture validation
- `/system-plan` - Interactive architecture planning
- `/task-status` - View task status across projects
