# Graphiti Integration Spec — Fleet-Wide Knowledge & Project Export

## For: Architect Agent integration, fleet-wide knowledge seeding, client project portability
## Date: 4 April 2026
## Status: Draft
## Location: guardkit repo (owns Graphiti client, FalkorDB docker, vLLM scripts)
## Builds on: docs/research/graphiti-refinement/ (FEAT-GR-000 through FEAT-GR-006)

---

## Purpose

This spec covers three concerns that extend the existing Graphiti refinement features:

1. **Fleet-wide architectural knowledge** — seeding and querying D1-D21 decisions,
   architectural patterns, and cross-project knowledge that all agents share
2. **Architect Agent read/write patterns** — how the Architect Agent specifically
   uses Graphiti for architectural memory that compounds over projects
3. **Client project export/import** — selective extraction of project-scoped
   knowledge for handover to clients (e.g., FinProxy → client's own infrastructure)

---

## Relationship to Existing Work

The graphiti-refinement features (Jan 2026) established:
- **FEAT-GR-PRE-001**: Project namespace foundation (`project_id__base_group` convention)
- **FEAT-GR-001**: Project knowledge seeding (entity types, `guardkit init` integration)
- **FEAT-GR-006**: Job-specific context retrieval

This spec does NOT duplicate that work. It adds:
- A new group ID scope for fleet-wide knowledge (not project-specific)
- Architect Agent-specific entity types and query patterns
- Export/import tooling for client data portability

---

## 1. Group ID Convention (Extended)

Building on FEAT-GR-PRE-001's namespace pattern:

| Scope | Group ID Pattern | Example | Who Writes | Who Reads |
|-------|-----------------|---------|------------|-----------|
| **GuardKit system** | `guardkit` | `guardkit` | `guardkit graphiti seed` | All agents (how commands work) |
| **Fleet architecture** | `appmilla-fleet` | `appmilla-fleet` | Architect Agent, manually | All agents (patterns, ADRs, decisions) |
| **Project knowledge** | `{project_id}` | `finproxy` | PO Agent, Architect Agent, manually | Agents working on that project |
| **Project sub-scope** | `{project_id}__{scope}` | `finproxy__feature_specs` | Feature spec seeding | Agents working on that project |

The key addition is `appmilla-fleet` — this is where D1-D21 resolved decisions,
architectural patterns, and cross-project lessons live. It's never exported to
clients. It's the internal "institutional memory."

**Query patterns by agent:**

| Agent | Default group_ids | Purpose |
|-------|------------------|---------|
| Architect Agent (on FinProxy) | `["appmilla-fleet", "finproxy"]` | Fleet patterns + project context |
| Architect Agent (on GCSE tutor) | `["appmilla-fleet", "gcse-tutor"]` | Fleet patterns + project context |
| GuardKit Factory (AutoBuild) | `["guardkit", "appmilla-fleet", "{project_id}"]` | System + fleet + project |
| Ideation Agent | `["appmilla-fleet"]` | Cross-project patterns for idea evaluation |
| Product Owner Agent | `["appmilla-fleet", "{project_id}"]` | Fleet context + project docs |

---

## 2. Fleet-Wide Entity Types (New — `appmilla-fleet` scope)

### Seed Data: Resolved Decisions

Each decision becomes an episode. Graphiti extracts entities and relationships.

```python
# Example episode for D4
await graphiti.add_episode(
    name="resolved-decision-D4",
    episode_body="""
    Resolved Decision D4: Event Bus Selection.
    Decision: NATS JetStream as the event bus for all agent communication.
    Rationale: Single binary deployment, sub-millisecond latency, built-in
    JetStream persistence, KV store for agent registry, account-based
    multi-tenancy. Evaluated against Kafka (too heavy for solo dev),
    Redis Streams (no native account isolation), and RabbitMQ (AMQP
    complexity not needed).
    Status: Accepted. Do not reopen.
    Scope: Fleet-wide — all agents communicate via NATS.
    Source: Dev Pipeline System Spec, ADR-SP-001.
    """,
    source_description="Fleet-wide resolved decisions (April 2026)",
    group_id="appmilla-fleet",
)
```

### Seed Data: Architectural Patterns

```python
patterns = [
    {
        "name": "c4-validation",
        "body": """
        Architectural Pattern: C4 Validation.
        Description: Use C4 diagramming (Context, Container, Component) and trace
        flows across system and technology boundaries to create sequence diagrams
        that validate architectural thinking. This changes root cause analysis
        outcomes approximately 9 out of 10 times versus verbal analysis alone.
        When to use: Any architectural decision, system boundary definition,
        integration point design, or debugging session.
        Evidence: Applied across GuardKit pipeline, Ship's Computer fleet,
        FinProxy architecture, agentic dataset factory.
        """,
    },
    {
        "name": "stay-at-altitude",
        "body": """
        Architectural Pattern: Stay at Altitude First.
        Description: Iterate at the architectural level before diving into
        implementation detail. Produce Context diagram first, then Container,
        then Component — with evaluation at each level before going deeper.
        Premature detail generates rework when higher-level decisions change.
        When to use: Any new project or major feature architecture.
        Anti-pattern: Jumping straight to class diagrams or API design before
        system boundaries are validated.
        """,
    },
    {
        "name": "review-before-fix",
        "body": """
        Architectural Pattern: Review Before Fix.
        Description: Create TASK-REV review tasks to diagnose root cause before
        creating fix tasks. Applied to architecture: validate the problem space
        before proposing solutions. The TASK-REV-F5F5 series (180+ review
        reports) demonstrated that root cause analysis produces better outcomes
        than fix-first approaches.
        When to use: Any unexpected behaviour, bug, or architectural concern.
        """,
    },
    {
        "name": "two-model-separation",
        "body": """
        Architectural Pattern: Two-Model Separation (D5).
        Description: The orchestration/reasoning model must differ from the
        implementation model. This prevents self-confirmation bias where the
        same model that generated a plan also evaluates it. In practice:
        Gemini 3.1 Pro for reasoning/evaluation, Claude Code SDK or local
        vLLM for implementation.
        When to use: Any Player-Coach or adversarial cooperation workflow.
        """,
    },
    {
        "name": "provider-independence",
        "body": """
        Architectural Pattern: Provider Independence.
        Description: Runtime switchability between cloud and local inference
        modes via configuration. No architecture should lock into a single
        vendor. Tool interface signatures must be identical across cloud and
        local modes (D7). Implemented via agent-config.yaml model selection.
        When to use: Any model integration, any external API dependency.
        """,
    },
    {
        "name": "exemplar-first-methodology",
        "body": """
        Architectural Pattern: Exemplar-First Methodology (D9).
        Description: Build and validate a working exemplar, then run
        /template-create to extract the template. Never build templates
        speculatively. The template is a proven pattern, not a guess.
        Evidence: deepagents-player-coach-exemplar → base template,
        deepagents-orchestrator-exemplar → orchestrator template.
        When to use: Any reusable pattern, any template creation.
        """,
    },
]

for pattern in patterns:
    await graphiti.add_episode(
        name=f"pattern-{pattern['name']}",
        episode_body=pattern["body"],
        source_description="Architectural patterns (April 2026)",
        group_id="appmilla-fleet",
    )
```

### Full Seed Script

A new command or script that seeds all fleet knowledge:

```bash
# New command in guardkit CLI
guardkit graphiti seed-fleet

# Or standalone script
python scripts/graphiti-seed-fleet.py
```

Seeds: all 21 resolved decisions (D1-D21), 6 architectural patterns, existing
ADRs from nats-core (ADR-001 through ADR-005), and key template descriptions.

---

## 3. Architect Agent Read/Write Patterns

### Reads (before generating architecture)

```python
# 1. Get fleet-wide patterns relevant to this project
patterns = await graphiti.search_nodes(
    query="architectural patterns for event-driven systems",
    group_ids=["appmilla-fleet"],
    limit=10,
)

# 2. Get prior ADRs from similar projects
prior_adrs = await graphiti.search_facts(
    query="architecture decisions for open banking integration",
    group_ids=["appmilla-fleet", "finproxy"],
    limit=10,
)

# 3. Get project-specific context
project_context = await graphiti.search_nodes(
    query="tech stack regulatory constraints data architecture",
    group_ids=["finproxy"],
    limit=20,
)

# 4. Get resolved fleet decisions (always included)
fleet_decisions = await graphiti.search_facts(
    query="resolved decisions fleet-wide",
    group_ids=["appmilla-fleet"],
    limit=25,
)
```

### Writes (after architecture approved)

```python
# 1. Write new ADRs from this architecture session
await graphiti.add_episode(
    name="adr-finproxy-001-moneyhub-bounded-context",
    episode_body="""
    ADR: FinProxy uses a bounded context pattern for Open Banking integration.
    The MoneyHub API is abstracted behind an internal interface contract so the
    provider can be swapped to Yapily later without affecting the AI intelligence
    layer. Decision date: April 2026. Status: Accepted.
    Project: FinProxy. Related pattern: provider-independence.
    """,
    source_description="Architect Agent output — FinProxy Phase 1",
    group_id="finproxy",
)

# 2. Record cross-project pattern application
await graphiti.add_episode(
    name="pattern-application-bounded-context-finproxy",
    episode_body="""
    The bounded context pattern was applied to FinProxy's Open Banking
    integration. MoneyHub is the initial provider, abstracted behind an
    internal interface. This is the same pattern used for model provider
    independence (D7) — the principle generalises beyond model selection
    to any external dependency.
    """,
    source_description="Cross-project pattern observation",
    group_id="appmilla-fleet",
)
```

---

## 4. Client Project Export/Import

### Problem

FinProxy is a client project. At handover, Appmilla needs to provide FinProxy
with their project-specific knowledge (ADRs, architecture decisions, domain
knowledge) without leaking Appmilla's internal fleet knowledge.

### Export Design

New script: `guardkit/scripts/graphiti-export.sh`

```bash
# Export all FinProxy knowledge
./scripts/graphiti-export.sh export --project finproxy

# Export with specific sub-scopes
./scripts/graphiti-export.sh export --project finproxy --scopes "feature_specs,architecture"

# Output
exports/finproxy-knowledge-20260404/
├── episodes.json           ← All episodes with group_id matching finproxy*
├── entities.json           ← All nodes from those episodes
├── facts.json              ← All edges/relationships
├── metadata.json           ← Export timestamp, Graphiti version, group_ids included
├── import.py               ← Self-contained import script
└── README.md               ← Instructions for the receiving party
```

### Implementation

The export uses Graphiti's search APIs with `group_ids` filtering plus
direct FalkorDB Cypher queries for completeness:

```python
# scripts/graphiti-export.py

import asyncio
import json
from datetime import datetime
from pathlib import Path

async def export_project(project_id: str, output_dir: Path, scopes: list[str] | None = None):
    """Export all Graphiti knowledge for a project.

    Only exports data scoped to the project's group_ids.
    Fleet-wide knowledge (appmilla-fleet) is NEVER included.
    GuardKit system knowledge (guardkit) is NEVER included.
    """
    # Determine which group_ids to export
    group_ids = [project_id]
    if scopes:
        group_ids.extend(f"{project_id}__{scope}" for scope in scopes)
    else:
        # Export all sub-scopes: query FalkorDB for all group_ids starting with project_id
        all_groups = await get_all_group_ids()
        group_ids = [g for g in all_groups if g == project_id or g.startswith(f"{project_id}__")]

    # Safety check: never export fleet or system knowledge
    forbidden = {"appmilla-fleet", "guardkit", "guardkit_validation_test"}
    if any(g in forbidden for g in group_ids):
        raise ValueError(f"Cannot export protected group_ids: {forbidden & set(group_ids)}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Export episodes (the source data — most important)
    episodes = await get_episodes_by_group_ids(group_ids)

    # Export derived entities and facts
    entities = await search_all_nodes(group_ids)
    facts = await search_all_facts(group_ids)

    # Write files
    (output_dir / "episodes.json").write_text(
        json.dumps(episodes, indent=2, default=str)
    )
    (output_dir / "entities.json").write_text(
        json.dumps(entities, indent=2, default=str)
    )
    (output_dir / "facts.json").write_text(
        json.dumps(facts, indent=2, default=str)
    )
    (output_dir / "metadata.json").write_text(json.dumps({
        "exported_at": datetime.now().isoformat(),
        "project_id": project_id,
        "group_ids_included": group_ids,
        "episode_count": len(episodes),
        "entity_count": len(entities),
        "fact_count": len(facts),
        "graphiti_version": "0.x",  # detect from installed package
        "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
        "embedding_dimensions": 768,
        "note": "Embeddings are NOT included. The receiving Graphiti instance "
                "will re-embed using its own model during import.",
    }, indent=2))

    # Write self-contained import script
    (output_dir / "import.py").write_text(IMPORT_SCRIPT_TEMPLATE)

    # Write instructions
    (output_dir / "README.md").write_text(f"""# {project_id} — Knowledge Graph Export

Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Episodes: {len(episodes)}
Entities: {len(entities)}
Facts: {len(facts)}

## Import Instructions

1. Stand up a Graphiti instance (FalkorDB + Graphiti MCP):
   ```bash
   # Docker Compose from the Graphiti repo
   git clone https://github.com/getzep/graphiti.git
   cd graphiti/mcp_server/docker
   docker compose up -d
   ```

2. Configure your embedding model (any model works — embeddings are regenerated):
   ```bash
   # Set your LLM and embedding endpoints in .env
   ```

3. Run the import:
   ```bash
   pip install graphiti-core httpx
   python import.py --group-id {project_id}
   ```

The import replays all episodes through `add_episode`, which triggers
Graphiti's entity extraction pipeline. The receiving instance builds its
own graph from the source episodes — no embedding dimension coupling.
""")

    return len(episodes), len(entities), len(facts)
```

### Import Script (bundled with export)

The `import.py` replays episodes via `add_episode`. This is deliberately
simple — Graphiti re-extracts entities from the episode text using whatever
LLM and embedding model the receiving instance is configured with:

```python
# import.py (bundled with export, self-contained)

async def import_episodes(episodes_file: str, group_id: str, graphiti_url: str):
    """Replay episodes into a Graphiti instance via MCP API."""
    episodes = json.loads(Path(episodes_file).read_text())

    for i, episode in enumerate(episodes):
        await add_episode_via_mcp(
            graphiti_url=graphiti_url,
            name=episode["name"],
            episode_body=episode["episode_body"],
            source_description=episode.get("source_description", "Imported"),
            group_id=group_id,
        )
        print(f"  [{i+1}/{len(episodes)}] {episode['name']}")
```

### Shell Wrapper

```bash
#!/usr/bin/env bash
# graphiti-export.sh — Selective project knowledge export
#
# Usage:
#   ./scripts/graphiti-export.sh export --project finproxy
#   ./scripts/graphiti-export.sh export --project finproxy --scopes "feature_specs,architecture"
#   ./scripts/graphiti-export.sh list-projects
#
# Output: exports/{project}-knowledge-{timestamp}/
```

---

## 5. Embedding Model Confirmation

| Component | Model | Dimensions | Port | Status |
|-----------|-------|-----------|------|--------|
| Graphiti embeddings | `nomic-ai/nomic-embed-text-v1.5` | 768 | 8001 | Running, confirmed working |
| Graphiti LLM | `Qwen2.5-14B-Instruct-FP8` | N/A | 8000 | Running, xgrammar json_schema enforcement |
| FalkorDB vector index | Configured for 768-dim | 768 | 6379 | Rebuilt after OpenAI→nomic switch |

The dimension mismatch was resolved when switching from OpenAI API to local
nomic embeddings on GB10. FalkorDB was cleared and reseeded via
`guardkit graphiti seed --force`. No further action needed.

---

## 6. Decisions to Record

| # | Decision | Rationale |
|---|----------|-----------|
| GR-D1 | `appmilla-fleet` group ID for internal fleet knowledge | Separates Appmilla's institutional knowledge from client projects. Never exported. |
| GR-D2 | Episode-based export (not graph dump) | Receiving party re-extracts entities with their own LLM/embeddings. No dimension coupling. Cleaner, more portable. |
| GR-D3 | Export script lives in guardkit repo | Guardkit owns the Graphiti client, FalkorDB docker, and vLLM scripts. Export is a Graphiti operational concern. |
| GR-D4 | Agents query both fleet + project scope by default | Cross-project pattern discovery is the compounding value. `group_ids=["appmilla-fleet", "{project_id}"]` |
| GR-D5 | Safety guard: export NEVER includes `appmilla-fleet` or `guardkit` groups | Prevents accidental leaking of internal knowledge to clients |
| GR-D6 | Embedding model: nomic-embed-text-v1.5 (768-dim) on GB10 | Confirmed working. Dimension mismatch resolved. No migration needed. |

---

## Implementation Sequence

1. **Create `scripts/graphiti-seed-fleet.py`** — seeds D1-D21 decisions and
   6 architectural patterns into `appmilla-fleet` group
2. **Create `scripts/graphiti-export.sh` + `scripts/graphiti-export.py`** —
   selective project export with safety guards
3. **Run seed-fleet** before first Architect Agent run on FinProxy
4. **Test export** with FinProxy data after first Architect Agent session

Items 1-2 are pre-requisites for the Architect Agent build (Phase A in the
build plan). Item 3 is part of task A7. Item 4 validates the export mechanism
with real data.

---

## Relationship to Existing Specs

- **Extends:** FEAT-GR-PRE-001 (project namespace) — adds `appmilla-fleet` scope
- **Extends:** FEAT-GR-001 (project seeding) — adds fleet-wide entity types
- **New:** Export/import tooling (no existing spec)
- **Consumed by:** Architect Agent (read/write patterns), build plan task A7

---

*Created: 4 April 2026 | Graphiti integration for fleet + Architect Agent + export*
