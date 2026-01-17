# FEAT-001: Graphiti Infrastructure Setup

> **Feature ID**: FEAT-001
> **Status**: Ready for Planning
> **Priority**: Critical (Foundation)
> **Estimated Complexity**: Medium
> **Dependencies**: None

---

## Overview

### Problem Statement

GuardKit needs persistent knowledge storage to solve the "session amnesia" problem where each Claude Code session starts fresh without knowledge of:
- What GuardKit is and how it works
- Previous decisions and their rationale
- What failed and why
- What patterns and templates exist

### Solution

Integrate Graphiti (a temporal knowledge graph built on FalkorDB) as the foundation for all knowledge storage in GuardKit. This feature establishes the infrastructure that all other Graphiti features depend on.

### Success Criteria

1. Graphiti can be started with a single command
2. GuardKit CLI can connect to Graphiti and perform basic operations
3. System gracefully handles Graphiti being unavailable
4. Configuration is flexible (local Docker, remote service, disabled)

---

## Technical Requirements

### Docker Infrastructure

**Requirement**: Provide Docker Compose configuration for local Graphiti deployment.

The official Graphiti Docker image includes:
- FalkorDB (graph database on port 6379)
- Graphiti MCP Server (on port 8000)
- Web UI (on port 3000)

```yaml
# Expected docker-compose.yml structure
services:
  graphiti:
    image: falkordb/graphiti-knowledge-graph-mcp:latest
    ports:
      - "6379:6379"   # FalkorDB
      - "3000:3000"   # Web UI
      - "8000:8000"   # MCP Server
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}  # For embeddings
    volumes:
      - graphiti-data:/data
```

**Questions to Answer**:
- Where should docker-compose.yml live? Options:
  - Repository root (visible, easy to find)
  - `.guardkit/docker/` (organized, hidden)
  - `infrastructure/` (separate from app code)
- Should we support Anthropic embeddings as alternative to OpenAI?
- Should data volume be configurable for multi-project isolation?

### Python Client Wrapper

**Requirement**: Create a Python client that wraps the Graphiti SDK for GuardKit's needs.

```python
# Expected interface
class GraphitiClient:
    """Wrapper around Graphiti SDK for GuardKit."""
    
    enabled: bool  # Is Graphiti available?
    
    async def connect(self) -> bool
    async def disconnect(self) -> None
    async def health_check(self) -> HealthStatus
    
    async def add_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str,
        source: str = "guardkit"
    ) -> str  # Returns episode ID
    
    async def search(
        self,
        query: str,
        group_ids: List[str],
        num_results: int = 10
    ) -> List[SearchResult]
```

**Questions to Answer**:
- Should we use the Graphiti Python SDK directly or the MCP protocol?
- How should connection pooling work for CLI commands?
- What's the retry strategy for transient failures?

### Configuration System

**Requirement**: Allow flexible configuration of Graphiti connection.

```python
# Expected configuration options
class GraphitiConfig:
    # Connection
    host: str = "localhost"
    port: int = 8000
    protocol: str = "http"  # or "https"
    
    # Authentication (for remote deployments)
    api_key: Optional[str] = None
    
    # Behavior
    enabled: bool = True
    timeout_seconds: int = 30
    retry_count: int = 3
    
    # Embedding provider
    embedding_provider: str = "openai"  # or "anthropic"
    embedding_api_key: Optional[str] = None
```

**Configuration Sources** (in priority order):
1. Environment variables (`GUARDKIT_GRAPHITI_HOST`, etc.)
2. `.guardkit/config.yaml` in project
3. `~/.guardkit/config.yaml` global
4. Defaults

**Questions to Answer**:
- Should configuration be per-project or global?
- How to handle embedding API key securely?
- Should we support multiple Graphiti instances?

### Graceful Degradation

**Requirement**: GuardKit must work even when Graphiti is unavailable.

**Behavior when Graphiti unavailable**:
- Log warning on first detection
- Skip all Graphiti operations silently
- Don't block command execution
- Cache unavailability status (don't retry every operation)
- Periodic re-check (every 60 seconds?)

```python
# Expected pattern
graphiti = get_graphiti()
if graphiti.enabled:
    context = await graphiti.search(...)
else:
    context = []  # Proceed without context
```

**Questions to Answer**:
- Should we show a warning to user when Graphiti unavailable?
- How long to cache "unavailable" status?
- Should some features require Graphiti (fail instead of degrade)?

### CLI Commands

**Requirement**: Provide CLI commands for managing Graphiti.

```bash
# Start Graphiti (docker compose up)
guardkit graphiti start

# Stop Graphiti
guardkit graphiti stop

# Check status
guardkit graphiti status
# Output: Graphiti running at localhost:8000, 1,234 episodes, 56 entities

# Seed with system context (delegates to FEAT-002)
guardkit graphiti seed

# Reset (clear all data - dangerous!)
guardkit graphiti reset --confirm
```

**Questions to Answer**:
- Should `guardkit graphiti start` auto-pull Docker image?
- Should we include a `guardkit graphiti logs` command?
- How to handle Docker not being installed?

---

## Implementation Approach

### File Structure

```
guardkit/
├── infrastructure/
│   └── docker/
│       └── docker-compose.graphiti.yml
│
├── installer/
│   └── core/
│       ├── lib/
│       │   └── graphiti/
│       │       ├── __init__.py
│       │       ├── client.py        # GraphitiClient class
│       │       ├── config.py        # GraphitiConfig class
│       │       ├── exceptions.py    # GraphitiError, etc.
│       │       └── models.py        # SearchResult, etc.
│       │
│       └── commands/
│           └── graphiti.md          # Slash command for Claude Code
│
├── cli/
│   └── graphiti_commands.py         # CLI subcommands
```

### Key Dependencies

- `graphiti-core` - Official Graphiti Python SDK
- `docker` - Python Docker SDK (for start/stop commands)
- `httpx` - Async HTTP client (for health checks)

### Testing Strategy

- **Unit tests**: Mock Graphiti SDK for client wrapper tests
- **Integration tests**: Use Testcontainers to spin up real Graphiti
- **Smoke tests**: Verify Docker Compose starts correctly

---

## Acceptance Criteria

1. [ ] `guardkit graphiti start` starts Graphiti in Docker
2. [ ] `guardkit graphiti status` shows connection status and stats
3. [ ] `guardkit graphiti stop` stops Graphiti cleanly
4. [ ] Python client can connect and perform basic operations
5. [ ] Configuration can be set via environment variables
6. [ ] Configuration can be set via config file
7. [ ] System works (degraded) when Graphiti unavailable
8. [ ] Health check returns useful status information
9. [ ] Connection errors are handled gracefully with retry
10. [ ] Documentation explains setup and configuration

---

## Out of Scope

- Seeding with system context (FEAT-002)
- Seeding with development knowledge (FEAT-003)
- Task/feature storage (FEAT-005, FEAT-006)
- Any querying beyond health checks

---

## Related Documents

- [Unified Data Architecture Decision](../../research/knowledge-graph-mcp/unified-data-architecture-decision.md)
- [Graphiti Prototype Integration Plan](../../research/knowledge-graph-mcp/graphiti-prototype-integration-plan.md)
- [Graphiti Official Documentation](https://github.com/getzep/graphiti)

---

## Questions for Clarification

The following questions should be answered during feature planning:

1. **Docker Location**: Where should docker-compose.yml live?
2. **Embedding Provider**: OpenAI only, or support Anthropic too?
3. **Configuration Scope**: Per-project, global, or both?
4. **Degradation UX**: Show warnings when Graphiti unavailable?
5. **Auto-start**: Should commands auto-start Graphiti if not running?
6. **Multi-project**: Should one Graphiti instance serve multiple projects?
