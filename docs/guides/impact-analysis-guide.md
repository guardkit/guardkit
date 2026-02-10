# Impact Analysis Command Guide

Analyze the architectural impact of a task before starting implementation.

## Quick Start

```bash
/impact-analysis TASK-042
```

## What It Does

Evaluates a proposed change against your project's architecture stored in Graphiti. Identifies affected components, ADR constraints, and calculates a risk score - all before you write a line of code.

## Prerequisites

- Run `/system-plan` at least once to capture architecture context
- Task file exists in `tasks/` directory (for task ID mode)
- (Optional) Graphiti stack running for live queries

## Usage

```bash
/impact-analysis TASK-XXX [--depth=DEPTH] [--include-bdd] [--include-tasks]
/impact-analysis "topic description" [--depth=DEPTH]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--depth` | Analysis depth: `quick`, `standard`, `deep` | `standard` |
| `--include-bdd` | Include BDD scenario impact | Off (auto in deep) |
| `--include-tasks` | Include related task search | Off (auto in deep) |

### Depth Tiers

| Depth | Queries | Time | Use Case |
|-------|---------|------|----------|
| `quick` | Components only | ~5s | Quick sanity check |
| `standard` | Components + ADRs + implications | ~10s | Normal pre-task validation |
| `deep` | All + BDD + related tasks | ~20s | Complex or risky changes |

## Examples

### Task ID Mode

Analyze an existing task:

```bash
/impact-analysis TASK-042
```

**Output:**
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

### Topic Mode

Explore impact before creating a task:

```bash
/impact-analysis "add real-time notifications"
```

Useful for "what if" scenarios and architectural exploration.

### Quick Check

Fast sanity check before starting work:

```bash
/impact-analysis TASK-042 --depth=quick
```

**Output:**
```
======================================================================
QUICK IMPACT: Add user notifications
======================================================================

RISK: 3/5 (Medium)

AFFECTED COMPONENTS: Attorney Management, Financial Oversight

Run with --depth=standard for full analysis.

[P]roceed / [C]ancel:
```

### Deep Analysis

Comprehensive analysis for complex changes:

```bash
/impact-analysis TASK-042 --depth=deep
```

Adds BDD scenarios at risk and related tasks to the output.

## The Decision Checkpoint

After displaying results, you're presented with options:

- **[P]roceed** - Ready to implement. For task IDs, shows `/task-work TASK-XXX` command.
- **[R]eview** - Deep dive into specific finding (component, ADR, risk)
- **[S]ystem-plan** - Chain to `/system-plan --mode=review` for architecture discussion
- **[C]ancel** - Stop and reconsider approach

## Risk Score Explained

Risk is calculated on a 1-5 scale:

| Score | Level | Meaning |
|-------|-------|---------|
| 1 | Very Low | Minimal architectural impact |
| 2 | Low | Limited impact, proceed normally |
| 3 | Medium | Multiple components affected, review recommended |
| 4 | High | ADR conflicts detected, architectural review needed |
| 5 | Very High | Major cross-cutting impact, full review required |

### Scoring Factors

- Base score: 1.0
- Each additional component: +0.5
- ADR conflict: +1.0 each
- ADR informational: +0.25 each
- BDD scenario at risk: +0.3 each (deep mode)

## Integration with Other Commands

### Pre-Task Workflow

```bash
# 1. Get project overview
/system-overview

# 2. Analyze impact of planned work
/impact-analysis TASK-042

# 3. If [P]roceed, start implementation
/task-work TASK-042
```

### With `/feature-plan`

Analyze before planning:

```bash
/impact-analysis "user authentication overhaul"
# Review impact, then:
/feature-plan "user authentication overhaul"
```

### Chaining to `/system-plan`

When impact reveals architecture issues, option [S] chains to review mode:

```bash
# Impact analysis shows ADR conflicts
# Select [S] for system-plan
# Opens: /system-plan "notifications" --mode=review
```

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
======================================================================
```

### No Architecture Context

```
======================================================================
NO ARCHITECTURE CONTEXT
======================================================================

Cannot analyze impact - no architecture information in Graphiti.

ALTERNATIVES:
  1. Run /system-plan "project" to capture architecture first
  2. Proceed without impact analysis (use caution)
  3. Review CLAUDE.md for project conventions
======================================================================
```

### BDD Group Empty (Deep Mode)

In deep mode, if no BDD scenarios exist:

```
[Graphiti] No BDD scenarios found, skipping BDD impact section
```

Analysis continues with other sections.

## Troubleshooting

### "Project not found" for task ID

- Verify task file exists: `ls tasks/*/TASK-042*.md`
- Check task ID format matches pattern `TASK-XXX`
- Use topic mode as fallback: `/impact-analysis "task description"`

### Risk score seems too low/high

Risk calculation is heuristic-based. For manual override:
- Use `--depth=deep` for more comprehensive analysis
- Select [R]eview to examine individual factors
- Use [S]ystem-plan for architectural discussion

### ADR conflicts not showing

- Verify ADRs are captured in Graphiti: `guardkit graphiti verify`
- Re-run system-plan: `/system-plan "project" --mode=review`
- Check ADR status (only active ADRs are checked)

## See Also

- [System Overview Guide](system-overview-guide.md) - Quick architecture summary
- [Context Switch Guide](context-switch-guide.md) - Multi-project navigation
- [Graphiti Commands](graphiti-commands.md) - CLI commands for knowledge management
