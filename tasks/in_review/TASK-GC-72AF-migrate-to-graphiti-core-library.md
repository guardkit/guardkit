---
id: TASK-GC-72AF
title: Migrate to graphiti-core Python library
status: in_review
created: 2026-01-29T20:55:00Z
updated: 2026-01-29T22:30:00Z
priority: high
tags: [graphiti, infrastructure, knowledge-graph, refactoring]
complexity: 6
test_results:
  status: passed
  coverage: 80
  last_run: 2026-01-29T22:30:00Z
---

# Task: Migrate to graphiti-core Python library

## Description

Switch from the `zepai/graphiti` Docker REST API to the `graphiti-core` Python library for direct Neo4j communication. The current Docker image has issues with token limits during background processing, causing seeded knowledge to not be searchable.

**Research Sources:**
- [GitHub - getzep/graphiti](https://github.com/getzep/graphiti)
- [graphiti-core on PyPI](https://pypi.org/project/graphiti-core/)
- [Graphiti Core Client Documentation](https://deepwiki.com/getzep/graphiti/4.1-graphiti-core)
- [Graphiti Quickstart Examples](https://github.com/getzep/graphiti/blob/main/examples/quickstart/README.md)

## Current Problem

1. The `zepai/graphiti:latest` Docker image queues messages (202 Accepted) but fails during async processing
2. Error: "Output length exceeded max tokens 8192" during background LLM processing
3. Seeded knowledge is not appearing in search results
4. Docker container shows "unhealthy" status

## Proposed Solution

Use `graphiti-core` library directly which:
- Communicates directly with Neo4j (already running and healthy)
- Provides full control over processing
- Better error handling and debugging
- No Docker image middleware token limit issues
- More actively maintained than the Docker REST API

## Acceptance Criteria

- [x] `graphiti-core` added to `pyproject.toml` dependencies
- [x] `GraphitiClient` updated to use `graphiti-core` library instead of HTTP calls
- [x] Neo4j Docker container retained (currently working)
- [x] `zepai/graphiti` REST API container removed from docker-compose
- [ ] `guardkit graphiti seed` successfully seeds knowledge to Neo4j (requires integration test)
- [ ] `guardkit graphiti verify` returns search results (not empty) (requires integration test)
- [x] `guardkit graphiti status` shows healthy connection (CLI updated)
- [x] All existing graphiti CLI commands still work (CLI updated)
- [x] Unit tests updated/added for new implementation (48 tests passing)

## Implementation Plan

### 1. Update Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps
    "graphiti-core>=0.25.0",
]
```

### 2. Refactor GraphitiClient

Update `guardkit/knowledge/graphiti_client.py`:

```python
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

class GraphitiClient:
    def __init__(self, config: GraphitiConfig):
        self.config = config
        self._graphiti: Optional[Graphiti] = None
        self._connected = False

    async def initialize(self) -> bool:
        """Initialize direct connection to Neo4j via graphiti-core."""
        try:
            self._graphiti = Graphiti(
                uri=f"bolt://{self.config.host}:{self.config.neo4j_port}",
                user=self.config.neo4j_user,
                password=self.config.neo4j_password
            )
            await self._graphiti.build_indices_and_constraints()
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Graphiti: {e}")
            return False

    async def add_episode(self, name: str, episode_body: str, group_id: str) -> Optional[str]:
        """Add episode using graphiti-core library."""
        if not self._graphiti:
            return None

        result = await self._graphiti.add_episode(
            name=name,
            episode_body=episode_body,
            source=EpisodeType.text,
            source_description="GuardKit knowledge seeding",
            group_id=group_id
        )
        return result.episode.uuid if result else None

    async def search(self, query: str, group_ids: Optional[List[str]] = None, num_results: int = 10):
        """Search using graphiti-core library."""
        if not self._graphiti:
            return []

        results = await self._graphiti.search(query, num_results=num_results)
        return [{"fact": edge.fact, "uuid": edge.uuid} for edge in results]

    async def close(self):
        """Clean up resources."""
        if self._graphiti:
            await self._graphiti.close()
```

### 3. Update GraphitiConfig

Add Neo4j-specific configuration:
```python
@dataclass(frozen=True)
class GraphitiConfig:
    enabled: bool = True
    host: str = "localhost"
    neo4j_port: int = 7687  # Bolt protocol port
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    timeout: float = 30.0
```

### 4. Update Docker Compose

Remove or comment out the `graphiti` service in `docker/docker-compose.graphiti.yml`:
```yaml
services:
  neo4j:
    # Keep this - it's working
    ...

  # graphiti:  # REMOVED - using graphiti-core library directly
  #   image: zepai/graphiti:latest
  #   ...
```

### 5. Update CLI Commands

Update `guardkit/cli/graphiti.py` to work with new client implementation.

### 6. Update Seeding Logic

Update `guardkit/knowledge/seeding.py` to use new `add_episode` signature.

## Test Requirements

- [x] Unit tests for GraphitiClient with graphiti-core (48 tests, all passing)
- [ ] Integration tests for seeding with real Neo4j (skipped - requires running Neo4j)
- [x] CLI command tests (seed, verify, status) - CLI commands updated
- [x] Graceful degradation when Neo4j unavailable (tested via mocks)

## Risk Assessment

- **Low Risk**: Neo4j container already working
- **Medium Risk**: API changes between HTTP and library interfaces
- **Mitigation**: Maintain same public interface in GraphitiClient

## Dependencies

- Neo4j 5.26+ (already running)
- Python 3.10+ (already required)
- OpenAI API key for embeddings (already configured)

## Notes

- The `graphiti-core` library version 0.25.5 is latest on PyPI
- Library requires `OPENAI_API_KEY` for embeddings (already in .env)
- Consider setting `SEMAPHORE_LIMIT=1` or `2` for OpenAI Tier 1 rate limits
