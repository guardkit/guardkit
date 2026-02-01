# Graphiti Query Commands Guide

Complete reference for querying and inspecting knowledge stored in the Graphiti knowledge graph.

## Overview

After seeding knowledge into Graphiti, you need ways to:

1. **Verify** what was captured ("Did my feature spec get indexed correctly?")
2. **Search** for specific knowledge ("What do we know about authentication?")
3. **View** knowledge details ("Show me feature FEAT-SKEL-001")
4. **Debug** context issues ("Why didn't Claude know about X?")

The `guardkit graphiti` query commands provide these capabilities through the CLI.

---

## Quick Reference

```bash
# Show specific knowledge by ID
guardkit graphiti show FEAT-SKEL-001
guardkit graphiti show ADR-001

# Search for knowledge
guardkit graphiti search "authentication patterns"
guardkit graphiti search "error handling" --group patterns --limit 20

# List all knowledge in a category
guardkit graphiti list features
guardkit graphiti list adrs
guardkit graphiti list patterns

# View knowledge graph status
guardkit graphiti status
guardkit graphiti status --verbose
```

---

## Commands

### `guardkit graphiti show`

Display detailed information about specific knowledge by ID.

**Usage:**
```bash
guardkit graphiti show <knowledge_id>
```

**Arguments:**
- `knowledge_id`: The ID of the knowledge to display (e.g., `FEAT-SKEL-001`, `ADR-001`)

**Features:**
- Auto-detects knowledge type from ID prefix (FEAT-*, ADR-*, etc.)
- Shows structured fields (title, description, status, etc.)
- Displays relevance score and metadata
- Formats output based on knowledge type

**Examples:**
```bash
# Show a feature specification
guardkit graphiti show FEAT-SKEL-001

# Show an architecture decision record
guardkit graphiti show ADR-001

# Show a pattern
guardkit graphiti show PATTERN-state-machine
```

**Example Output:**
```
============================================================
  FEAT-SKEL-001: Walking Skeleton
============================================================
  ID: FEAT-SKEL-001
  Description: Basic MCP server with ping tool and Docker setup
  Status: planned

  Success Criteria:
    • MCP server responds to ping tool
    • Returns {pong: true, timestamp: <iso>}
    • Docker container runs successfully
    • Health check endpoint works
```

---

### `guardkit graphiti search`

Search across all knowledge with relevance scoring.

**Usage:**
```bash
guardkit graphiti search <query> [OPTIONS]
```

**Arguments:**
- `query`: Search query (e.g., "authentication", "error handling")

**Options:**
- `--group`, `-g`: Limit search to specific group (e.g., `patterns`, `feature_specs`)
- `--limit`, `-n`: Maximum number of results (default: 10)

**Features:**
- Full-text search with relevance scoring
- Color-coded results by relevance (green >0.8, yellow >0.5, white ≤0.5)
- Optional group filtering for targeted searches
- Configurable result limits

**Examples:**
```bash
# Search across all knowledge
guardkit graphiti search "authentication"

# Search only patterns
guardkit graphiti search "error handling" --group patterns

# Limit results
guardkit graphiti search "API" --limit 5

# Search turn states for specific task
guardkit graphiti search "turn TASK-XXX" --group turn_states --limit 5
```

**Example Output:**
```
Found 5 results for 'authentication':

1. [0.92] Pattern: JWT authentication using bearer tokens...
2. [0.85] ADR-003: Chose OAuth2 over API keys because...
3. [0.71] Feature FEAT-AUTH-001: User authentication system...
4. [0.65] Constraint: Must support SSO for enterprise users...
5. [0.52] Task outcome: Auth implementation took 3 turns...
```

---

### `guardkit graphiti list`

List all items in a knowledge category.

**Usage:**
```bash
guardkit graphiti list <category>
```

**Arguments:**
- `category`: One of `features`, `adrs`, `patterns`, `constraints`, `all`

**Features:**
- Shows IDs and titles for all items in category
- Supports listing all categories at once
- Organized output with category headers

**Examples:**
```bash
# List all feature specifications
guardkit graphiti list features

# List all architecture decision records
guardkit graphiti list adrs

# List all patterns
guardkit graphiti list patterns

# List all constraints
guardkit graphiti list constraints

# List everything
guardkit graphiti list all
```

**Example Output:**
```
Feature Specifications (4 items)
----------------------------------------
  • FEAT-SKEL-001: Walking Skeleton
  • FEAT-SKEL-002: Video Info Tool
  • FEAT-SKEL-003: Transcript Tool
  • FEAT-INT-001: Insight Extraction
```

---

### `guardkit graphiti status`

Show knowledge graph health and statistics.

**Usage:**
```bash
guardkit graphiti status [OPTIONS]
```

**Options:**
- `--verbose`, `-v`: Show all groups including empty ones

**Features:**
- Connection status (enabled/disabled)
- Episode counts by category
- Total knowledge count
- Health check indicators

**Examples:**
```bash
# Standard status
guardkit graphiti status

# Verbose status (includes empty groups)
guardkit graphiti status --verbose
```

**Example Output:**
```
╔════════════════════════════════════════╗
║       Graphiti Knowledge Status        ║
╚════════════════════════════════════════╝

  Status: ENABLED

  System Knowledge:
    • product_knowledge: 3
    • command_workflows: 7
    • patterns: 12
    • agents: 8

  Project Knowledge:
    • project_overview: 1
    • project_architecture: 1
    • feature_specs: 4

  Decisions:
    • project_decisions: 2
    • architecture_decisions: 5

  Learning:
    • task_outcomes: 15
    • failure_patterns: 3
    • successful_fixes: 8

  Total Episodes: 69
```

---

## Knowledge Groups

Graphiti organizes knowledge into logical groups for efficient querying and context retrieval.

### System Knowledge

Core GuardKit product knowledge that applies across all projects.

| Group | Description | Example Content |
|-------|-------------|-----------------|
| `product_knowledge` | What GuardKit is and its value proposition | Core concepts, benefits |
| `command_workflows` | How commands work together | Workflow sequences, command relationships |
| `patterns` | Design pattern knowledge | State machine patterns, error handling patterns |
| `agents` | Agent capabilities and boundaries | Agent roles, responsibilities |

### Project Knowledge

Project-specific context and requirements.

| Group | Description | Example Content |
|-------|-------------|-----------------|
| `project_overview` | High-level project description | Mission, goals, constraints |
| `project_architecture` | Technical architecture | Component structure, data flow |
| `feature_specs` | Feature specifications | FEAT-XXX specs with acceptance criteria |

### Decisions

Architecture and project decisions with rationale.

| Group | Description | Example Content |
|-------|-------------|-----------------|
| `project_decisions` | Project-level decisions | Technology choices, constraints |
| `architecture_decisions` | Architecture Decision Records | ADR-XXX with context, decision, consequences |

### Learning

Captured outcomes and patterns from task execution.

| Group | Description | Example Content |
|-------|-------------|-----------------|
| `task_outcomes` | Results from completed tasks | What worked, timing, approach |
| `failure_patterns` | Failed approaches and fixes | What failed, why, prevention |
| `successful_fixes` | Proven solutions | What worked for specific problems |

### Turn States

AutoBuild workflow state for cross-turn learning.

| Group | Description | Example Content |
|-------|-------------|-----------------|
| `turn_states` | Feature-build turn tracking | Player decisions, Coach feedback, files modified |

---

## Turn State Tracking

GuardKit captures turn states during `/feature-build` workflows for cross-turn learning.

### What Gets Captured

- **Player decisions and actions** - What the Player implemented
- **Coach feedback and approval status** - APPROVED, REJECTED, or FEEDBACK
- **Files modified during turn** - List of changed files
- **Acceptance criteria status** - Which criteria are verified, pending, or rejected
- **Blockers encountered** - Issues found during implementation
- **Progress summary** - Overview of what was accomplished

### Turn State Schema

| Field | Type | Description |
|-------|------|-------------|
| `feature_id` | string | FEAT-XXX identifier |
| `task_id` | string | TASK-XXX being worked on |
| `turn_number` | int | Sequential turn number |
| `player_decision` | string | What Player implemented |
| `coach_decision` | string | APPROVED \| REJECTED \| FEEDBACK |
| `feedback_summary` | string | Key feedback points |
| `blockers_found` | list | List of blockers encountered |
| `files_modified` | list | List of changed files |
| `acceptance_criteria_status` | dict | {criterion: verified\|pending\|rejected} |
| `mode` | string | FRESH_START \| RECOVERING_STATE \| CONTINUING_WORK |

### Querying Turn States

```bash
# View all recent turns for a feature
guardkit graphiti search "turn FEAT-XXX" --group turn_states

# View specific task turns
guardkit graphiti search "turn TASK-XXX" --group turn_states --limit 5
```

### Benefits

- **Turn N+1 knows what Turn N learned** - Cross-turn context preservation
- **Prevents repeated mistakes** - Coach feedback carries forward
- **Tracks progress across autonomous sessions** - Continuity in long-running features
- **Provides audit trail** - Complete history of feature development

---

## Output Formatting

### Relevance Color Coding

Search results are color-coded by relevance score:

| Color | Score Range | Meaning |
|-------|-------------|---------|
| Green | > 0.8 | High relevance - strong match |
| Yellow | 0.5 - 0.8 | Medium relevance - related |
| White | ≤ 0.5 | Low relevance - tangential |

### Score Interpretation

- **0.9+**: Almost exact match to query
- **0.7-0.9**: Strong semantic match
- **0.5-0.7**: Related content
- **< 0.5**: Weak association (may need more specific query)

---

## Troubleshooting

### Command Not Found

```bash
# Verify Graphiti is enabled
guardkit graphiti status

# Check configuration
cat config/graphiti.yaml
```

### Connection Errors

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Verify connection settings in config/graphiti.yaml
# Default: neo4j://localhost:7687
```

### No Results from Queries

```bash
# Check if system context is seeded
guardkit graphiti status

# Seed system context if needed
guardkit graphiti seed

# Verify with test query
guardkit graphiti search "guardkit" --limit 5
```

### Empty Turn States

```bash
# Turn states are only captured during /feature-build
# Run a feature-build task to generate turn states
guardkit autobuild task TASK-XXX

# Then query turn states
guardkit graphiti search "turn" --group turn_states
```

### Slow Queries

- Reduce `--limit` value (default: 10)
- Use specific `--group` filters instead of searching all groups
- Check Neo4j resource allocation

### Stale Knowledge

```bash
# Re-seed system context to update knowledge
guardkit graphiti seed --force

# Note: Force re-seeding clears previous system context
```

---

## Performance Characteristics

**Query Response Times** (based on typical usage):

| Command | Response Time | Notes |
|---------|---------------|-------|
| `show` | ~100-200ms | Single lookup |
| `search` | ~200-500ms | Depends on query complexity |
| `list` | ~300-800ms | Depends on category size |
| `status` | ~500-1000ms | Counts all groups |

**Optimizations Applied:**

- Limited default results (10 for search, 50 for list)
- Text truncation to reduce output size
- Async/await for concurrent queries in status command
- Caching of client connections

---

## Best Practices

1. **Use specific queries** - More specific queries return more relevant results
   ```bash
   # Better
   guardkit graphiti search "JWT authentication tokens"

   # Worse
   guardkit graphiti search "auth"
   ```

2. **Filter by group when possible** - Reduces search space and improves relevance
   ```bash
   guardkit graphiti search "error handling" --group patterns
   ```

3. **Check status first** - Verify Graphiti is enabled and seeded
   ```bash
   guardkit graphiti status
   ```

4. **Use show for known IDs** - More efficient than searching
   ```bash
   guardkit graphiti show FEAT-AUTH-001
   ```

5. **Review turn states after feature-build** - Debug cross-turn issues
   ```bash
   guardkit graphiti search "turn TASK-XXX" --group turn_states
   ```

---

## See Also

- [Graphiti Commands Guide](graphiti-commands.md) - Seed, clear, and add-context commands
- [Graphiti Integration Guide](graphiti-integration-guide.md) - Overall integration architecture
- [FEAT-GR-005: Knowledge Query Command](../research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md) - Technical specification
