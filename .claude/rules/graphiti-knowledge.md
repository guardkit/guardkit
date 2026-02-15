---
paths: config/graphiti.yaml, guardkit/graphiti/**/*.py, docs/**/graphiti*
---

# Graphiti Knowledge Capture

## ⚠️ Access Method: Python Client Library (NOT MCP)

Graphiti is accessed via the `guardkit.knowledge` Python client library, connecting
directly to FalkorDB. There is NO Graphiti MCP server configured for this project.

- Do NOT check for MCP tools (`mcp__graphiti__*`) to determine availability
- Use `python -m installer.core.commands.lib.graphiti_check --status` to check availability
- Use the Python client imports (`from guardkit.knowledge import get_graphiti`) for direct access
- Configuration: `.guardkit/graphiti.yaml` (FalkorDB at whitestocks:6379)

GuardKit integrates with Graphiti for persistent knowledge capture across sessions. Build project understanding through guided Q&A and query stored knowledge via CLI.

## Interactive Capture

```bash
guardkit graphiti capture --interactive
guardkit graphiti capture --interactive --focus <category> --max-questions 5
```

### Focus Categories

**Project Knowledge:**

| Category | Captures |
|----------|----------|
| `project-overview` | Purpose, target users, goals, problem statement |
| `architecture` | Components, services, data flow |
| `domain` | Domain terminology, business rules |
| `constraints` | Technical/business constraints |
| `decisions` | Technology choices, rationale, trade-offs |
| `goals` | Key objectives and success criteria |

**AutoBuild Customization:**

| Category | Captures |
|----------|----------|
| `role-customization` | Player ask-before rules, Coach escalation rules |
| `quality-gates` | Coverage thresholds, arch review scores |
| `workflow-preferences` | Implementation mode preferences, turn limits |

## Knowledge Query Commands

```bash
# Show specific knowledge by ID
guardkit graphiti show <knowledge_id>

# Search knowledge
guardkit graphiti search "<query>" [--group <group>] [--limit N]

# List all knowledge in a category
guardkit graphiti list <category>    # features | adrs | patterns | constraints | all

# View knowledge graph status
guardkit graphiti status [--verbose]

# Seed/re-seed system context
guardkit graphiti seed [--force]
```

### Knowledge Groups

- **System**: product_knowledge, command_workflows, patterns, agents
- **Project**: project_overview, project_architecture, feature_specs
- **Decisions**: project_decisions, architecture_decisions
- **Learning**: task_outcomes, failure_patterns, successful_fixes
- **Turn States**: turn_states (AutoBuild turn tracking)

## Turn State Tracking

During `/feature-build`, GuardKit captures turn states for cross-turn learning:
- Player decisions/actions, Coach feedback, files modified
- Acceptance criteria status, blockers, progress summary

```bash
guardkit graphiti search "turn FEAT-XXX" --group turn_states
```

## Job-Specific Context Retrieval

Automatic context loading during task execution based on task type, complexity, and novelty. Categories: feature context, similar outcomes, patterns, architecture, warnings, domain knowledge.

Budget scales with complexity: 2000 tokens (simple) to 6000+ tokens (complex).

## Threading Model

GuardKit uses a per-thread factory pattern (`GraphitiClientFactory`) for Graphiti client management. Key rules:

- `get_graphiti()` is **sync** — never `await` it. Returns a thread-local `GraphitiClient`.
- Each thread gets its own client with its own Neo4j driver bound to that thread's event loop.
- `GraphitiConfig` (frozen dataclass) is shared across threads — thread-safe by design.
- In async contexts, `get_thread_client()` defers connection (creates client but skips `initialize()`). The client's `enabled` property returns `False` until connected.
- For multi-threaded scenarios (e.g., `FeatureOrchestrator` parallel execution), use `get_factory()` to get the factory and let each worker thread call `get_thread_client()`.
- `init_graphiti(config)` creates the factory and initializes a client for the **calling thread only**.

```python
# Single-threaded (most common)
client = get_graphiti()  # Lazy-init factory + thread client

# Multi-threaded (e.g., AutoBuild in FeatureOrchestrator)
factory = get_factory()
if factory:
    thread_client = factory.get_thread_client()  # Per-thread, lazy
```

**See**: [Interactive Capture Guide](../../docs/guides/graphiti-knowledge-capture.md) | [Integration Guide](../../docs/guides/graphiti-integration-guide.md)
