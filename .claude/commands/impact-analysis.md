# /impact-analysis - Pre-Task Architecture Validation

Analyzes the architectural impact of a proposed task or change against the stored architecture context. Provides risk scoring, affected component identification, and ADR conflict detection.

## Command Syntax

```bash
/impact-analysis TASK-XXX [--depth=DEPTH] [--include-bdd] [--include-tasks]
/impact-analysis "topic description" [--depth=DEPTH]
```

## Available Flags

| Flag | Description |
|------|-------------|
| `--depth=DEPTH` | Analysis depth: `quick`, `standard` (default), `deep` |
| `--include-bdd` | Include BDD scenario impact (auto-enabled in deep mode) |
| `--include-tasks` | Include related task search (auto-enabled in deep mode) |

## Overview

The `/impact-analysis` command evaluates a proposed change against the project's architecture context stored in Graphiti. It identifies:

- **Affected Components** - Which parts of the system will be impacted
- **ADR Constraints** - Architecture decisions that may conflict or apply
- **Risk Score** - Numerical assessment of change complexity (1-5)
- **BDD Scenarios** - Test scenarios potentially affected (deep mode)

**Use before:**
- Starting work on a task (`/task-work`)
- Planning a feature (`/feature-plan`)
- Making architecture decisions (`/system-plan --mode=review`)

## Depth Tiers

| Depth | Queries | Time | Use Case |
|-------|---------|------|----------|
| `quick` | Components only | ~5s | Quick sanity check |
| `standard` | Components + ADRs + implications | ~10s | Normal pre-task validation |
| `deep` | All + BDD + related tasks | ~20s | Complex or risky changes |

## Input Modes

### Task ID Mode

```bash
/impact-analysis TASK-042
```

- Reads task file from `tasks/*/TASK-042*.md`
- Extracts title, description, and tags for semantic query
- Enriches Graphiti search with task metadata

### Topic Mode

```bash
/impact-analysis "add real-time notifications"
```

- Uses topic string directly as semantic query
- Useful for exploring impact before creating a task
- Good for "what if" scenarios

## Execution Flow

### Phase 1: Parse Input and Initialize

**PARSE** command arguments:

```python
# Determine input type
task_pattern = r"TASK-[A-Z0-9-]+"
if re.match(task_pattern, input_arg):
    input_type = "task_id"
    task_id = input_arg
else:
    input_type = "topic"
    topic = input_arg

# Parse flags
depth = flags.get("depth", "standard")
include_bdd = "--include-bdd" in flags or depth == "deep"
include_tasks = "--include-tasks" in flags or depth == "deep"
```

**INITIALIZE** Graphiti:

```python
from guardkit.knowledge.graphiti_client import get_graphiti
from guardkit.planning.graphiti_arch import SystemPlanGraphiti

client = get_graphiti()

if client:
    sp = SystemPlanGraphiti(client, "current_project")
else:
    sp = None
```

### Phase 2: Build Query

**BUILD** semantic query:

```python
from guardkit.planning.impact_analysis import _build_query

if input_type == "task_id":
    # Read task file for enriched query
    query = _build_query(task_id)
    # Combines: title + description + tags
else:
    # Use topic directly
    query = topic
```

### Phase 3: Run Impact Analysis

**INVOKE** impact analysis module:

```python
from guardkit.planning.impact_analysis import (
    run_impact_analysis,
    format_impact_display,
)

if not sp or not sp.is_available():
    print(GRAPHITI_UNAVAILABLE_MESSAGE)
    return

impact = run_impact_analysis(
    sp=sp,
    client=client,
    task_or_topic=input_arg,
    depth=depth,
    include_bdd=include_bdd,
    include_tasks=include_tasks,
)
```

### Phase 4: Display Results

**FORMAT** and display:

```python
output = format_impact_display(impact, depth=depth)
print(output)
```

### Phase 5: Decision Checkpoint

**PRESENT** decision options:

```python
print()
print("=" * 70)
print("DECISION CHECKPOINT")
print("=" * 70)
print()
print("Options:")
print("  [P]roceed - Start implementation")
print("  [R]eview - Get more details on a specific finding")
print("  [S]ystem-plan - Open architecture planning session")
print("  [C]ancel - Abort and reconsider approach")
print()
choice = input("Your choice [P/R/S/C]: ")
```

**HANDLE** user choice:

```python
if choice.lower() == "p":
    # User proceeds
    if input_type == "task_id":
        print(f"\nProceeding with task. Run: /task-work {task_id}")
    else:
        print("\nProceeding. Create task with: /task-create \"{topic}\"")

elif choice.lower() == "r":
    # Deep dive into specific finding
    finding_num = input("Which finding number? ")
    # Display detailed information for selected finding

elif choice.lower() == "s":
    # Chain to system-plan review mode
    print(f"\nLaunching /system-plan \"{topic}\" --mode=review")
    # Execute system-plan with architecture context

elif choice.lower() == "c":
    print("\nAnalysis cancelled.")
```

## Output Format

### Standard Display

```
======================================================================
IMPACT ANALYSIS: TASK-042 - Add user notifications
======================================================================

RISK ASSESSMENT:
  Score: 3/5 (Medium)
  [##########----------] 60%

  Rationale: 2 components affected, 1 ADR conflict detected

AFFECTED COMPONENTS (2):
  - Attorney Management (HIGH)
      Impact: Notification triggers for status changes
      Files: src/attorney/*.py

  - Financial Oversight (MEDIUM)
      Impact: Alerts for transaction anomalies
      Files: src/financial/*.py

ADR CONSTRAINTS (2):
  - ADR-003: "Synchronous HTTP for inter-service communication"
    Status: CONFLICT
    Issue: Real-time notifications require async/WebSocket

  - ADR-007: "Event-driven updates for status changes"
    Status: ALIGNED
    Note: Notification system aligns with event pattern

IMPLICATIONS:
  - Need new shared concern: Notification Service
  - Cross-cutting: WebSocket connection management
  - Domain events: StatusChanged, TransactionFlagged

======================================================================
DECISION CHECKPOINT
======================================================================

Options:
  [P]roceed - Start implementation
  [R]eview - Get more details on a specific finding
  [S]ystem-plan - Open architecture planning session
  [C]ancel - Abort and reconsider approach

Your choice [P/R/S/C]:
```

### Quick Depth (Abbreviated)

```
======================================================================
QUICK IMPACT: Add user notifications
======================================================================

RISK: 3/5 (Medium)

AFFECTED COMPONENTS: Attorney Management, Financial Oversight

Run with --depth=standard for full analysis.

[P]roceed / [C]ancel:
```

### Deep Depth (Extended)

Includes additional sections:

```
BDD SCENARIOS AT RISK (2):
  - user_receives_notification_on_status_change.feature
    Risk: Scenario may need updates for async delivery

  - attorney_alerts_for_anomalies.feature
    Risk: Alert timing expectations may change

RELATED TASKS (3):
  - TASK-038: Implement event sourcing (completed)
  - TASK-041: Add WebSocket infrastructure (in_progress)
  - TASK-045: Update notification preferences (backlog)
```

## Risk Score Calculation

The risk score (1-5) is calculated using these heuristics:

| Factor | Score Contribution |
|--------|-------------------|
| Base score | 1.0 |
| Each additional component | +0.5 (after first) |
| ADR conflict | +1.0 each |
| ADR informational | +0.25 each |
| BDD scenario at risk | +0.3 each |

**Labels:**
- 1: Very Low - Minimal architectural impact
- 2: Low - Limited impact, proceed with normal caution
- 3: Medium - Multiple components affected, review recommended
- 4: High - ADR conflicts detected, architectural review needed
- 5: Very High - Major cross-cutting impact, full review required

## Graceful Degradation

### Graphiti Unavailable

```
======================================================================
IMPACT ANALYSIS UNAVAILABLE
======================================================================

Cannot query Graphiti for architecture context.

ALTERNATIVES:
  - Review docs/architecture/ARCHITECTURE.md manually
  - Check existing ADRs in docs/architecture/decisions/
  - Proceed with caution (no automated impact check)

To configure Graphiti:
  pip install guardkit-py[graphiti]
======================================================================
```

### No Architecture Context

```
======================================================================
NO ARCHITECTURE CONTEXT
======================================================================

Cannot analyze impact - no architecture information in Graphiti.

This means /system-plan hasn't captured architecture yet.

ALTERNATIVES:
  1. Run /system-plan "project" to capture architecture first
  2. Proceed without impact analysis (use caution)
  3. Review CLAUDE.md for project conventions

Without architecture context, impact analysis cannot:
  - Identify affected components
  - Check ADR constraints
  - Calculate meaningful risk scores
======================================================================
```

### BDD Group Empty (Deep Mode)

In deep mode, when `bdd_scenarios` group is empty:

```python
# Log and skip gracefully
print("[Graphiti] No BDD scenarios found, skipping BDD impact section")
# Continue with other sections
```

## Examples

### Basic Usage

```bash
# Analyze impact of a specific task
/impact-analysis TASK-042

# Quick check before starting work
/impact-analysis TASK-042 --depth=quick

# Deep analysis for complex change
/impact-analysis TASK-042 --depth=deep

# Explore impact of an idea
/impact-analysis "migrate to microservices"
```

### Workflow Integration

```bash
# 1. Get project overview
/system-overview

# 2. Analyze impact of planned work
/impact-analysis TASK-042

# 3. If approved, start implementation
/task-work TASK-042
```

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

**IMPORTANT: Follow these steps exactly when `/impact-analysis` is invoked.**

### Step 1: Parse Input

```python
import re

# Get the input argument (task ID or topic)
input_arg = args[0] if args else None

if not input_arg:
    print("ERROR: Missing task ID or topic")
    print("Usage: /impact-analysis TASK-XXX")
    print("       /impact-analysis \"topic description\"")
    return

# Determine input type
task_pattern = r"^TASK-[A-Z0-9-]+$"
if re.match(task_pattern, input_arg):
    input_type = "task_id"
else:
    input_type = "topic"

# Parse flags
depth = "standard"  # Default
include_bdd = False
include_tasks = False

for arg in args[1:]:
    if arg.startswith("--depth="):
        depth = arg.split("=")[1]
    if arg == "--include-bdd":
        include_bdd = True
    if arg == "--include-tasks":
        include_tasks = True

# Deep mode auto-enables both
if depth == "deep":
    include_bdd = True
    include_tasks = True
```

### Step 2: Initialize Graphiti

```python
from guardkit.knowledge.graphiti_client import get_graphiti
from guardkit.planning.graphiti_arch import SystemPlanGraphiti

client = get_graphiti()

if not client:
    print(GRAPHITI_UNAVAILABLE_MESSAGE)
    return

sp = SystemPlanGraphiti(client, "current_project")

if not sp.is_available():
    print(NO_CONTEXT_MESSAGE)
    return
```

### Step 3: Run Analysis

```python
from guardkit.planning.impact_analysis import (
    run_impact_analysis,
    format_impact_display,
)

try:
    impact = run_impact_analysis(
        sp=sp,
        client=client,
        task_or_topic=input_arg,
        depth=depth,
        include_bdd=include_bdd,
        include_tasks=include_tasks,
    )
except Exception as e:
    print(f"[Graphiti] Error running analysis: {e}")
    print(GRAPHITI_UNAVAILABLE_MESSAGE)
    return
```

### Step 4: Display Results

```python
output = format_impact_display(impact, depth=depth)
print(output)
```

### Step 5: Decision Checkpoint

```python
print()
print("=" * 70)
print("DECISION CHECKPOINT")
print("=" * 70)
print()
print("Options:")
print("  [P]roceed - Start implementation")
print("  [R]eview - Get more details on a specific finding")
print("  [S]ystem-plan - Open architecture planning session")
print("  [C]ancel - Abort and reconsider approach")
print()

choice = input("Your choice [P/R/S/C]: ").lower()

if choice == "p":
    if input_type == "task_id":
        print(f"\nReady to proceed. Run: /task-work {input_arg}")
    else:
        print(f"\nCreate task first: /task-create \"{input_arg}\"")

elif choice == "r":
    # Request more detail
    print("\nWhich finding would you like to review?")
    print("  1. Component details")
    print("  2. ADR conflicts")
    print("  3. Risk calculation")
    # ... handle selection

elif choice == "s":
    # Chain to system-plan review
    topic = input_arg if input_type == "topic" else impact.get("query", input_arg)
    print(f"\nLaunching: /system-plan \"{topic}\" --mode=review")
    # Execute system-plan command

elif choice == "c":
    print("\nAnalysis cancelled. Consider revising approach.")
```

### What NOT to Do

- **DO NOT** skip the decision checkpoint - it's a core feature of this command
- **DO NOT** proceed automatically without user input
- **DO NOT** make up impact data if Graphiti returns no results
- **DO NOT** crash on missing task files - fall back to using the task ID as query
- **DO NOT** skip BDD analysis in deep mode - degrade gracefully if empty

### Message Constants

```python
GRAPHITI_UNAVAILABLE_MESSAGE = """
======================================================================
IMPACT ANALYSIS UNAVAILABLE
======================================================================

Cannot query Graphiti for architecture context.

ALTERNATIVES:
  - Review docs/architecture/ARCHITECTURE.md manually
  - Check existing ADRs in docs/architecture/decisions/
  - Proceed with caution (no automated impact check)
======================================================================
"""

NO_CONTEXT_MESSAGE = """
======================================================================
NO ARCHITECTURE CONTEXT
======================================================================

Cannot analyze impact - no architecture information in Graphiti.

ALTERNATIVES:
  1. Run /system-plan "project" to capture architecture first
  2. Proceed without impact analysis (use caution)
  3. Review CLAUDE.md for project conventions
======================================================================
"""
```

---

## Related Commands

- `/system-overview` - Quick architecture summary (simpler, no risk scoring)
- `/context-switch` - Switch between multiple projects
- `/system-plan` - Interactive architecture planning (with review mode)
- `/task-work` - Start working on a task (after impact analysis)
- `/feature-plan` - Plan a feature (can chain from impact analysis)
