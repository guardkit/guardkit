---
complexity: 6
conductor_workspace: wave1-1
created_at: 2026-01-24 00:00:00+00:00
estimated_minutes: 180
feature_id: FEAT-GI
id: TASK-GI-001
implementation_mode: task-work
parent_review: TASK-REV-GI01
priority: 1
status: completed
tags:
- infrastructure
- graphiti
- docker
- critical-path
task_type: scaffolding
title: Graphiti Core Infrastructure
wave: 1
completed_at: 2026-01-28T21:30:00Z
quality_gates:
  compilation: passed
  tests_passed: 88
  tests_total: 88
  tests_skipped: 2
  line_coverage: 86.5
  branch_coverage: 96.4
  code_review_score: 92
---

# TASK-GI-001: Graphiti Core Infrastructure

> **Note**: This task was originally planned to use FalkorDB as the graph database backend, but the actual implementation uses Neo4j. The code examples and technical approach described below reflect the original plan; the implemented solution in `docker/docker-compose.graphiti.yml` and `guardkit/knowledge/` uses Neo4j instead. See TASK-REV-DB01 for the database choice decision.

## Overview

**Priority**: Critical (Foundation for all other features)
**Dependencies**: None

## Problem Statement

GuardKit needs a knowledge graph system to solve the memory/context problem where Claude Code sessions lose track of:
- What GuardKit is and how it works
- Architectural decisions made in previous sessions
- What patterns worked or failed

Graphiti (built on FalkorDB) provides temporal knowledge graph capabilities with semantic search, but we need infrastructure to run it and connect to it from GuardKit.

## Strategic Context

This is the **foundation feature** for addressing the memory problem that has plagued `/feature-build` development. Without Graphiti running and accessible, none of the other context/memory features can work.

**Key constraint**: Don't over-engineer. We need Graphiti working, not a perfect enterprise deployment. Claude Code GuardKit may become legacy once Deep Agents GuardKit is built.

## Goals

1. Graphiti and FalkorDB running via Docker Compose
2. Python client wrapper for GuardKit to query Graphiti
3. Configuration system to enable/disable Graphiti
4. Health check and initialization
5. Graceful degradation when Graphiti unavailable

## Non-Goals

- Production-grade deployment (Kubernetes, etc.)
- Multi-tenant isolation
- Advanced security/authentication
- High availability setup

## Prerequisites

- **Docker and Docker Compose** installed and running
- **`OPENAI_API_KEY`** environment variable set (required for embeddings)
  - Can be set in `.env` file at project root
  - Or exported in shell: `export OPENAI_API_KEY=your-key`
  - Without this key, Graphiti will initialize with `enabled=False` (graceful degradation)

## Technical Approach

### Docker Compose Setup

```yaml
# docker/docker-compose.graphiti.yml
version: '3.8'

services:
  falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "6379:6379"
    volumes:
      - falkordb_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  graphiti:
    image: getzep/graphiti:latest
    ports:
      - "8000:8000"
    environment:
      - FALKORDB_HOST=falkordb
      - FALKORDB_PORT=6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}  # For embeddings
    depends_on:
      falkordb:
        condition: service_healthy

volumes:
  falkordb_data:
```

### Python Client Wrapper

```python
# guardkit/knowledge/graphiti_client.py

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import os

@dataclass
class GraphitiConfig:
    """Configuration for Graphiti connection."""
    enabled: bool = True
    host: str = "localhost"
    port: int = 8000
    timeout: int = 30

class GraphitiClient:
    """Wrapper around Graphiti SDK with graceful degradation."""

    def __init__(self, config: Optional[GraphitiConfig] = None):
        self.config = config or GraphitiConfig()
        self._client = None
        self._connected = False

    @property
    def enabled(self) -> bool:
        return self.config.enabled and self._connected

    async def initialize(self) -> bool:
        """Initialize connection to Graphiti."""
        if not self.config.enabled:
            return False

        try:
            # Initialize Graphiti client
            from graphiti_core import Graphiti
            self._client = Graphiti(
                host=self.config.host,
                port=self.config.port
            )
            await self._client.build_indices()
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"Graphiti unavailable: {e}")
            self._connected = False
            return False

    async def health_check(self) -> bool:
        """Check if Graphiti is healthy."""
        if not self._client:
            return False
        try:
            # Simple query to verify connectivity
            await self._client.search("health_check", num_results=1)
            return True
        except Exception:
            return False

    async def search(
        self,
        query: str,
        group_ids: Optional[List[str]] = None,
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search Graphiti with graceful degradation."""
        if not self.enabled:
            return []

        try:
            return await self._client.search(
                query=query,
                group_ids=group_ids,
                num_results=num_results
            )
        except Exception as e:
            logger.warning(f"Graphiti search failed: {e}")
            return []

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str
    ) -> Optional[str]:
        """Add episode with graceful degradation."""
        if not self.enabled:
            return None

        try:
            return await self._client.add_episode(
                name=name,
                episode_body=episode_body,
                group_id=group_id
            )
        except Exception as e:
            logger.warning(f"Graphiti add_episode failed: {e}")
            return None

# Singleton instance
_graphiti: Optional[GraphitiClient] = None

async def init_graphiti(config: Optional[GraphitiConfig] = None) -> GraphitiClient:
    """Initialize the global Graphiti client."""
    global _graphiti
    _graphiti = GraphitiClient(config)
    await _graphiti.initialize()
    return _graphiti

def get_graphiti() -> GraphitiClient:
    """Get the global Graphiti client."""
    if _graphiti is None:
        raise RuntimeError("Graphiti not initialized. Call init_graphiti() first.")
    return _graphiti
```

### Configuration

```yaml
# .guardkit/graphiti.yaml
graphiti:
  enabled: true
  host: localhost
  port: 8000
  timeout: 30

  # Embedding model (for semantic search)
  embedding_model: text-embedding-3-small

  # Group IDs this project uses
  group_ids:
    - product_knowledge
    - command_workflows
    - quality_gate_phases
    - technology_stack
    - feature_build_architecture
    - architecture_decisions
    - failure_patterns
    - component_status
    - integration_points
    - templates
    - agents
    - patterns
    - rules
    - adrs
    - task_outcomes
```

## Acceptance Criteria

- [x] **Docker Compose works**
  - `docker compose -f docker/docker-compose.graphiti.yml up` starts FalkorDB and Graphiti
  - Services are healthy within 30 seconds
  - Data persists across restarts

- [x] **Python client connects**
  - `init_graphiti()` successfully connects when Graphiti is running
  - `health_check()` returns True when healthy

- [x] **Graceful degradation**
  - When Graphiti is not running, `enabled` returns False
  - All methods return empty results instead of throwing exceptions
  - GuardKit commands continue to work (just without knowledge context)

- [x] **Configuration works**
  - Can enable/disable via `.guardkit/graphiti.yaml`
  - Can override host/port for different environments

- [x] **Graceful handling of missing OPENAI_API_KEY**
  - When API key not set, `initialize()` returns False
  - Warning logged: "OPENAI_API_KEY not set, Graphiti requires OpenAI for embeddings"
  - All subsequent operations return empty results (not exceptions)

## Testing Strategy

1. **Unit tests**: Mock Graphiti client, test wrapper logic
2. **Integration tests**: Start Docker, verify actual connectivity
3. **Degradation tests**: Stop Docker, verify graceful handling

## Files to Create/Modify

### New Files
- `docker/docker-compose.graphiti.yml`
- `guardkit/knowledge/__init__.py`
- `guardkit/knowledge/graphiti_client.py`
- `guardkit/knowledge/config.py`
- `tests/knowledge/test_graphiti_client.py`

### Modified Files
- `.guardkit/graphiti.yaml` (new config file)
- `guardkit/cli.py` (add Graphiti initialization)

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| OpenAI API key required for embeddings | Document requirement, support alternative embedding providers |
| Docker not available on all systems | Graceful degradation, document Docker requirement |
| FalkorDB performance issues | Start simple, optimize if needed |

## Open Questions

1. Should we support alternative embedding providers (local models, etc.)?
2. Do we need a "graphiti status" command for debugging?
3. Should Graphiti auto-start when GuardKit commands run?

---

## Related Documents

- [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md)
- [Graphiti System Context Seeding](../../docs/research/knowledge-graph-mcp/graphiti-system-context-seeding.md)
- [Graphiti Prototype Integration Plan](../../docs/research/knowledge-graph-mcp/graphiti-prototype-integration-plan.md)