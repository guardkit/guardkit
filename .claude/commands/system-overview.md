# /system-overview - Architecture Summary Command

Displays a concise summary of the project's architecture context stored in Graphiti. Provides quick orientation for developers and AI agents before starting work.

## Command Syntax

```bash
/system-overview [--verbose] [--section=SECTION] [--format=FORMAT]
```

## Available Flags

| Flag | Description |
|------|-------------|
| `--verbose` | Include full descriptions and details for all sections |
| `--section=SECTION` | Filter to a specific section: `components`, `decisions`, `crosscutting`, `stack`, `all` (default: all) |
| `--format=FORMAT` | Output format: `display` (terminal), `markdown`, `json` (default: display) |

## Overview

The `/system-overview` command provides a quick architectural summary of the current project by querying Graphiti for stored architecture context. It's the simplest of the three "system context read" commands:

- **/system-overview** - Quick orientation (this command)
- **/impact-analysis** - Pre-task validation with risk scoring
- **/context-switch** - Multi-project navigation

**Use cases:**
- Quickly orient yourself at the start of a session
- Review project architecture before planning features
- Get structured output for documentation

## Execution Flow

### Phase 1: Load Architecture Context

**INITIALIZE** Graphiti client:

```python
from guardkit.knowledge.graphiti_client import get_graphiti
from guardkit.planning.graphiti_arch import SystemPlanGraphiti

# Get Graphiti client (returns None if unavailable)
client = get_graphiti()

if client:
    project_id = "current_project"  # From config or default
    sp = SystemPlanGraphiti(client, project_id)
else:
    sp = None
```

### Phase 2: Get System Overview

**INVOKE** system overview module:

```python
from guardkit.planning.system_overview import (
    get_system_overview,
    format_overview_display,
)

# Parse flags
verbose = "--verbose" in flags
section = flags.get("section", "all")
format_type = flags.get("format", "display")

# Get overview
if sp and sp.is_available():
    overview = get_system_overview(sp, verbose=verbose)
else:
    overview = {"status": "no_context"}
```

### Phase 3: Display Results

**FORMAT** and display:

```python
if overview.get("status") == "no_context":
    # Display helpful hints
    print(NO_CONTEXT_MESSAGE)
else:
    # Format and display
    output = format_overview_display(overview, section=section, format=format_type)
    print(output)
```

## Output Format

### Default Display (Terminal)

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
NEXT STEPS:
  - Impact analysis: /impact-analysis TASK-XXX
  - Plan feature: /feature-plan "description"
  - Full architecture: /system-plan "project"
======================================================================
```

### Verbose Mode (--verbose)

Includes full descriptions for each component, ADR context and consequences, and detailed concern descriptions.

### JSON Format (--format=json)

```json
{
  "status": "success",
  "system": {
    "name": "My Project",
    "purpose": "CLI tool for task management with quality gates",
    "methodology": "modular",
    "users": ["Developers", "AI agents"]
  },
  "components": [
    {
      "name": "CLI Parser",
      "description": "Command routing, argument validation",
      "responsibilities": ["Parse arguments", "Route commands"]
    }
  ],
  "decisions": [
    {
      "id": "ADR-001",
      "title": "Use Click for CLI",
      "status": "active"
    }
  ],
  "concerns": [
    {
      "name": "Logging",
      "description": "Structured logging with [Module] prefixes"
    }
  ]
}
```

### Section Filtering (--section)

Only display a specific section:

```bash
/system-overview --section=components
# Only shows COMPONENTS section

/system-overview --section=decisions
# Only shows ARCHITECTURE DECISIONS section
```

## Graceful Degradation

### No Architecture Context

When no architecture data exists in Graphiti:

```
======================================================================
NO ARCHITECTURE CONTEXT
======================================================================

No architecture information found for this project.

This typically means /system-plan hasn't been run yet to capture
the project's architecture.

NEXT STEPS:
  1. Run /system-plan "project description" to capture architecture
  2. Or create architecture docs manually in docs/architecture/

For quick project understanding, try:
  - Read CLAUDE.md for project conventions
  - Check docs/architecture/ for existing documentation
======================================================================
```

### Graphiti Unavailable

When Graphiti service is not available:

```
======================================================================
ARCHITECTURE CONTEXT UNAVAILABLE
======================================================================

Cannot query Graphiti for architecture information.

This means:
  - Graphiti service is not running or not configured
  - Architecture context exists but is not queryable

ALTERNATIVES:
  - Read docs/architecture/ARCHITECTURE.md directly
  - Check CLAUDE.md for project conventions
  - Run /system-plan when Graphiti is available to capture context

To configure Graphiti:
  pip install guardkit-py[graphiti]
  # Add Graphiti settings to .env
======================================================================
```

## Examples

### Basic Usage

```bash
# Quick overview of current project
/system-overview

# Verbose with full details
/system-overview --verbose

# Only components
/system-overview --section=components

# JSON output for scripting
/system-overview --format=json
```

### Integration with Other Commands

```bash
# 1. Get oriented
/system-overview

# 2. Analyze impact of planned work
/impact-analysis TASK-042

# 3. Plan feature with architecture context
/feature-plan "add user notifications"
```

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

**IMPORTANT: Follow these steps exactly when `/system-overview` is invoked.**

### Step 1: Parse Arguments

```python
# Extract flags from command
verbose = "--verbose" in args
section = "all"  # Default
format_type = "display"  # Default

# Parse specific flags
for arg in args:
    if arg.startswith("--section="):
        section = arg.split("=")[1]
    if arg.startswith("--format="):
        format_type = arg.split("=")[1]
```

### Step 2: Initialize Graphiti

```python
from guardkit.knowledge.graphiti_client import get_graphiti
from guardkit.planning.graphiti_arch import SystemPlanGraphiti

client = get_graphiti()

if client:
    sp = SystemPlanGraphiti(client, "current_project")
    available = sp.is_available()
else:
    sp = None
    available = False
```

### Step 3: Get and Display Overview

```python
from guardkit.planning.system_overview import (
    get_system_overview,
    format_overview_display,
)

if not available:
    # Display Graphiti unavailable message
    print(GRAPHITI_UNAVAILABLE_MESSAGE)
    return

overview = get_system_overview(sp, verbose=verbose)

if overview.get("status") == "no_context":
    # Display no context message
    print(NO_CONTEXT_MESSAGE)
    return

# Format and display
output = format_overview_display(overview, section=section, format=format_type)
print(output)
```

### Step 4: Show Next Steps

After displaying the overview, show helpful next steps:

```python
print()
print("=" * 70)
print("NEXT STEPS:")
print("  - Impact analysis: /impact-analysis TASK-XXX")
print("  - Plan feature: /feature-plan \"description\"")
print("  - Full architecture: /system-plan \"project\"")
print("=" * 70)
```

### What NOT to Do

- **DO NOT** skip the Graphiti availability check
- **DO NOT** try to fetch architecture data if Graphiti is unavailable
- **DO NOT** display empty sections (skip them gracefully)
- **DO NOT** make up architecture information - only display what Graphiti returns
- **DO NOT** block on errors - always provide helpful degradation messages

### Error Handling

```python
# Always wrap Graphiti calls
try:
    overview = get_system_overview(sp, verbose=verbose)
except Exception as e:
    print(f"[Graphiti] Error fetching overview: {e}")
    print(GRAPHITI_UNAVAILABLE_MESSAGE)
    return
```

### Message Constants

```python
GRAPHITI_UNAVAILABLE_MESSAGE = """
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
"""

NO_CONTEXT_MESSAGE = """
======================================================================
NO ARCHITECTURE CONTEXT
======================================================================

No architecture information found for this project.

NEXT STEPS:
  1. Run /system-plan "project description" to capture architecture
  2. Or create docs manually in docs/architecture/

For quick understanding:
  - Read CLAUDE.md for project conventions
  - Check docs/architecture/ for existing docs
======================================================================
"""
```

---

## Related Commands

- `/impact-analysis` - Pre-task architecture validation with risk scoring
- `/context-switch` - Switch between multiple projects
- `/system-plan` - Interactive architecture planning (creates the context this command reads)
- `/feature-plan` - Plan features with architecture context
