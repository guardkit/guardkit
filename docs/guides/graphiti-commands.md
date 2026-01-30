## # Graphiti CLI Commands Guide

Complete reference for GuardKit's Graphiti knowledge graph CLI commands.

## Overview

GuardKit integrates with Graphiti to provide persistent knowledge across Claude Code sessions. The `guardkit graphiti` commands manage seeding, verification, and clearing of knowledge.

## Commands

### `guardkit graphiti seed`

Seeds system context into the Graphiti knowledge graph.

**Usage:**
```bash
guardkit graphiti seed
guardkit graphiti seed --force
```

**Options:**
- `--force`, `-f`: Force re-seeding even if already seeded

**What it does:**
- Seeds comprehensive GuardKit knowledge into Graphiti
- Creates 15+ knowledge categories (product knowledge, command workflows, quality gates, etc.)
- Adds metadata to all episodes for tracking and deduplication
- Creates seeding marker file to prevent duplicate seeding

**Example:**
```bash
# First-time seeding
guardkit graphiti seed

# Force re-seed (e.g., after GuardKit upgrade)
guardkit graphiti seed --force
```

**Knowledge categories seeded:**
- `product_knowledge` - What GuardKit is and its value proposition
- `command_workflows` - How commands work together
- `quality_gate_phases` - The 5-phase quality gate structure
- `technology_stack` - Python CLI, Claude Code, SDK details
- `feature_build_architecture` - Player-Coach pattern
- `architecture_decisions` - Key design decisions
- `failure_patterns` - Known failures and fixes
- `component_status` - Complete/incomplete components
- `integration_points` - Component connections
- `templates` - Template metadata for search
- `agents` - Agent capabilities and boundaries
- `patterns` - Design pattern knowledge
- `rules` - Rule applicability and examples
- `failed_approaches` - Failed approaches with prevention guidance
- `quality_gate_configs` - Quality gate threshold configurations

---

### `guardkit graphiti status`

Shows Graphiti connection and seeding status.

**Usage:**
```bash
guardkit graphiti status
```

**What it shows:**
- Graphiti enabled/disabled status
- Neo4j connection details (URI, user, timeout)
- Connection health check
- Seeding status (seeded/not seeded, version)

**Example output:**
```
Graphiti Status

Enabled         Yes
Neo4j URI       bolt://localhost:7687
Neo4j User      neo4j
Timeout         30s

Connection: OK
Health: OK

Seeded: Yes (version 1.0.0)
```

---

### `guardkit graphiti verify`

Verifies seeded knowledge with test queries.

**Usage:**
```bash
guardkit graphiti verify
guardkit graphiti verify --verbose
```

**Options:**
- `--verbose`, `-v`: Show detailed query results

**What it does:**
- Runs 5 test queries against different knowledge categories
- Verifies that seeding was successful
- Checks that semantic search is working

**Example:**
```bash
# Quick verification
guardkit graphiti verify

# Verbose output with results
guardkit graphiti verify --verbose
```

---

### `guardkit graphiti clear`

Clears Graphiti knowledge graph data.

**Usage:**
```bash
# Clear ALL knowledge (requires --confirm)
guardkit graphiti clear --confirm

# Clear system-level knowledge only
guardkit graphiti clear --system-only --confirm

# Clear current project's knowledge only
guardkit graphiti clear --project-only --confirm

# Preview what would be deleted (no --confirm needed)
guardkit graphiti clear --dry-run

# Automation-friendly (skip prompts)
guardkit graphiti clear --confirm --force
```

**Options:**
- `--confirm`: **Required** for actual deletion (safety check)
- `--system-only`: Only clear system-level knowledge (templates, patterns, workflows)
- `--project-only`: Only clear current project's knowledge
- `--dry-run`: Show what would be deleted without deleting
- `--force`, `-f`: Skip confirmation prompts (for automation)

**Safety features:**
- Requires `--confirm` flag to prevent accidental deletion
- Shows preview of what will be deleted before proceeding
- `--dry-run` allows safe exploration
- `--system-only` and `--project-only` are mutually exclusive

**What it clears:**

**System Groups** (cleared with `--system-only` or default):
- `guardkit_templates` - Template metadata
- `guardkit_patterns` - Design pattern knowledge
- `guardkit_workflows` - Workflow definitions
- `product_knowledge` - GuardKit product info
- `command_workflows` - Command workflow knowledge
- `quality_gate_phases` - Quality gate information
- `technology_stack` - Technology stack details
- `feature_build_architecture` - Feature-build patterns
- And all other system-level groups

**Project Groups** (cleared with `--project-only` or default):
- `{project}__project_overview` - Project-specific overview
- `{project}__project_architecture` - Project architecture
- `{project}__feature_specs` - Feature specifications
- `{project}__project_decisions` - Project-specific decisions

**Examples:**

```bash
# Preview before clearing (safe)
guardkit graphiti clear --dry-run

# Clear everything after reviewing preview
guardkit graphiti clear --confirm

# Clear only system knowledge (preserve project context)
guardkit graphiti clear --system-only --confirm

# Clear only current project (preserve GuardKit system knowledge)
guardkit graphiti clear --project-only --confirm

# For CI/CD automation
guardkit graphiti clear --confirm --force
```

**When to use:**
- **After GuardKit upgrade**: Clear system knowledge, then re-seed
  ```bash
  guardkit graphiti clear --system-only --confirm
  guardkit graphiti seed
  ```

- **Starting fresh on a project**: Clear project knowledge
  ```bash
  guardkit graphiti clear --project-only --confirm
  ```

- **Complete reset**: Clear everything
  ```bash
  guardkit graphiti clear --confirm
  guardkit graphiti seed
  ```

- **Before testing**: Ensure clean state
  ```bash
  guardkit graphiti clear --dry-run  # Check what exists
  guardkit graphiti clear --confirm  # Clear it
  ```

**Output example:**
```
Graphiti Knowledge Clear

Connecting to Neo4j at bolt://localhost:7687...
Connected to Graphiti

The following will be deleted:

System Groups:
  - product_knowledge
  - command_workflows
  - quality_gate_phases

Project Groups:
  - guardkit__project_overview
  - guardkit__feature_specs

Total groups: 5
Estimated episodes: 150

Clearing knowledge...

All knowledge cleared!
System groups cleared: 3
Project groups cleared: 2
Total episodes deleted: 150
```

---

### `guardkit graphiti seed-adrs`

Seeds feature-build Architecture Decision Records (ADRs).

**Usage:**
```bash
guardkit graphiti seed-adrs
guardkit graphiti seed-adrs --force
```

**Options:**
- `--force`, `-f`: Force re-seeding even if already seeded

**What it seeds:**
- ADR-FB-001: Use SDK query() for task-work invocation
- ADR-FB-002: Use FEAT-XXX paths in feature mode
- ADR-FB-003: Pre-loop must invoke real task-work

**When to use:**
- After running `/feature-build` for the first time
- When upgrading feature-build implementation
- When troubleshooting feature-build issues

---

## Metadata in Episodes

All seeded episodes include a `_metadata` block for tracking and deduplication:

```json
{
  "entity_type": "command",
  "name": "/task-work",
  "purpose": "Implement tasks through quality gates",
  "_metadata": {
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2024-01-30T12:00:00Z",
    "updated_at": "2024-01-30T12:00:00Z",
    "source_hash": null,
    "entity_id": "command_task_work"
  }
}
```

**Metadata fields:**
- `source`: Always `"guardkit_seeding"` for system context
- `version`: Seeding version (e.g., `"1.0.0"`)
- `created_at`: ISO timestamp when episode was created
- `updated_at`: ISO timestamp of last update
- `source_hash`: Hash of source file (null for generated content)
- `entity_id`: Unique identifier for deduplication

**Benefits:**
- **Deduplication**: Prevent duplicate episodes across re-seeding
- **Version tracking**: Know which seeding version created the episode
- **Provenance**: Track where knowledge came from
- **Updates**: Detect when content has changed

---

## Configuration

Graphiti configuration is in `~/.guardkit/config.yaml`:

```yaml
graphiti:
  enabled: true
  neo4j_uri: bolt://localhost:7687
  neo4j_user: neo4j
  neo4j_password: password
  timeout: 30
```

**Environment variables** (override config file):
- `GRAPHITI_ENABLED`: Set to `false` to disable
- `GRAPHITI_NEO4J_URI`: Neo4j connection URI
- `GRAPHITI_NEO4J_USER`: Neo4j username
- `GRAPHITI_NEO4J_PASSWORD`: Neo4j password
- `GRAPHITI_TIMEOUT`: Connection timeout in seconds

---

## Workflow Examples

### Initial Setup
```bash
# Check status
guardkit graphiti status

# Seed knowledge
guardkit graphiti seed

# Verify it worked
guardkit graphiti verify
```

### After GuardKit Upgrade
```bash
# Clear old system knowledge
guardkit graphiti clear --system-only --confirm

# Seed new version
guardkit graphiti seed --force

# Verify
guardkit graphiti verify
```

### Fresh Project Start
```bash
# Clear project-specific knowledge only
guardkit graphiti clear --project-only --confirm

# System knowledge is preserved, project starts fresh
```

### Troubleshooting
```bash
# Check what's in the graph
guardkit graphiti clear --dry-run

# Check connection
guardkit graphiti status

# Verify seeded knowledge
guardkit graphiti verify --verbose

# Complete reset
guardkit graphiti clear --confirm
guardkit graphiti seed
```

---

## Error Handling

All commands handle errors gracefully:

- **Connection failures**: Show clear error message, exit cleanly
- **Disabled client**: Skip operations, show warning
- **Partial failures**: Continue with other operations, show warnings
- **Missing marker**: Safe to re-seed or clear

**Common issues:**

1. **"Graphiti not available"**: Check Neo4j is running
   ```bash
   # Start Neo4j (Docker example)
   docker run -d \
     -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/password \
     neo4j:latest
   ```

2. **"Connection refused"**: Check `neo4j_uri` in config
   ```bash
   guardkit graphiti status
   ```

3. **"Seeding marker missing"**: Run seed again
   ```bash
   guardkit graphiti seed
   ```

---

## Best Practices

1. **Seed after installation**
   ```bash
   guardkit graphiti seed
   ```

2. **Verify periodically**
   ```bash
   guardkit graphiti verify
   ```

3. **Clear before major upgrades**
   ```bash
   guardkit graphiti clear --system-only --confirm
   guardkit graphiti seed --force
   ```

4. **Use --dry-run before clearing**
   ```bash
   guardkit graphiti clear --dry-run
   ```

5. **Keep project knowledge across upgrades**
   ```bash
   # Only clear system knowledge
   guardkit graphiti clear --system-only --confirm
   ```

---

## See Also

- [Graphiti Integration Guide](graphiti-integration-guide.md) - Overall integration architecture
- [Graphiti Setup](../setup/graphiti-setup.md) - Installation and configuration
- [Episode Metadata Deep-Dive](../deep-dives/graphiti/episode-metadata.md) - Metadata schema details
