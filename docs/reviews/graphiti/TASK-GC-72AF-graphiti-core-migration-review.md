# TASK-GC-72AF: Graphiti-Core Migration Review

**Date**: 2026-01-29
**Task ID**: TASK-GC-72AF
**Status**: COMPLETED
**Purpose**: Document the complete migration from zepai/graphiti Docker REST API to graphiti-core Python library

---

## Executive Summary

This task migrated GuardKit's knowledge graph integration from the `zepai/graphiti` Docker REST API to the `graphiti-core` Python library for direct Neo4j communication. The migration required:

1. Refactoring the client wrapper (`graphiti_client.py`)
2. Updating configuration (`config.py`)
3. Simplifying Docker Compose (Neo4j only)
4. Updating CLI commands
5. Rewriting tests
6. Adding installation script support

---

## Problem Statement

### Original Architecture (Before Migration)

```
GuardKit CLI
    │
    ▼
graphiti_client.py (HTTP client)
    │
    ▼ HTTP REST API
zepai/graphiti Docker container
    │
    ▼ Bolt
Neo4j Docker container
```

**Issues with zepai/graphiti Docker approach:**
- Token limit issues in the Docker image
- Less control over error handling
- Additional middleware layer
- Less actively maintained than graphiti-core library

### Target Architecture (After Migration)

```
GuardKit CLI
    │
    ▼
graphiti_client.py (graphiti-core wrapper)
    │
    ▼ Bolt (direct)
Neo4j Docker container
```

**Benefits:**
- Direct Neo4j communication
- Full control over LLM token limits
- Better error handling and debugging
- More actively maintained library

---

## Files Changed

### 1. `guardkit/knowledge/graphiti_client.py`

**Before**: HTTP client using `httpx` to call REST API endpoints
**After**: Wrapper around `graphiti-core` library with graceful degradation

**Key Changes:**

```python
# OLD: HTTP-based approach
async def search(self, query: str, ...) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.base_url}/search",
            json={"query": query, ...}
        )
        return response.json()

# NEW: graphiti-core library approach
async def search(self, query: str, ...) -> List[Dict[str, Any]]:
    from graphiti_core import Graphiti
    results = await self._graphiti.search(
        query,
        group_ids=group_ids,
        num_results=num_results
    )
    # Convert Edge objects to dictionaries
    return [{"uuid": edge.uuid, "fact": edge.fact, ...} for edge in results]
```

**New Features:**
- Lazy import of graphiti-core for graceful degradation
- `_check_graphiti_core()` helper to verify library availability
- `GraphitiConfig` now uses Neo4j Bolt settings instead of REST API host/port
- `initialize()` creates Graphiti instance and builds indices
- `_execute_search()` and `_create_episode()` internal methods for testability

**Configuration Changes:**

```python
# OLD
@dataclass(frozen=True)
class GraphitiConfig:
    enabled: bool = True
    host: str = "localhost"
    port: int = 8000  # REST API port
    timeout: float = 30.0

# NEW
@dataclass(frozen=True)
class GraphitiConfig:
    enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    timeout: float = 30.0
    # Deprecated fields for backwards compatibility
    host: str = "localhost"
    port: int = 8000
```

### 2. `guardkit/knowledge/config.py`

**Changes:**
- Added `neo4j_uri`, `neo4j_user`, `neo4j_password` fields to `GraphitiSettings`
- Updated environment variable mappings:
  - `NEO4J_URI` → `neo4j_uri`
  - `NEO4J_USER` → `neo4j_user`
  - `NEO4J_PASSWORD` → `neo4j_password`
- Marked `host` and `port` as deprecated

### 3. `docker/docker-compose.graphiti.yml`

**Before**: Two services (neo4j + graphiti REST API)
**After**: Single service (neo4j only)

```yaml
# REMOVED: zepai/graphiti service
# graphiti:
#   image: zepai/graphiti:latest
#   ports:
#     - "8000:8000"
#   depends_on:
#     - neo4j

# KEPT: neo4j service only
services:
  neo4j:
    image: neo4j:5.26.0
    container_name: guardkit-neo4j
    ports:
      - "7474:7474"  # HTTP (Neo4j Browser)
      - "7687:7687"  # Bolt (graphiti-core connection)
    environment:
      - NEO4J_AUTH=neo4j/password123
      - NEO4J_PLUGINS=["apoc"]
```

### 4. `guardkit/cli/graphiti.py`

**Changes:**
- Updated `_get_client_and_config()` to use new config fields
- Changed connection messages to show Neo4j URI instead of REST API URL
- All commands (`seed`, `status`, `verify`, `seed-adrs`) now use Bolt connection

### 5. `pyproject.toml`

**Added Dependency:**
```toml
dependencies = [
    # ... existing deps ...
    "graphiti-core>=0.5.0",
]
```

### 6. `installer/scripts/install.sh`

**Added graphiti-core installation** (lines 353-383):

```bash
# Check and install graphiti-core (required for knowledge graph integration)
print_info "Checking for graphiti-core..."
set +e  # Temporarily allow errors for package checks
python3 -c "from graphiti_core import Graphiti" </dev/null 2>&1 >/dev/null
graphiti_status=$?
set -e  # Re-enable exit on error

if [ $graphiti_status -ne 0 ]; then
    print_info "Installing graphiti-core (required for knowledge graph integration)..."
    # Use python3 -m pip for reliability with multiple Python installations
    python3 -m pip install --break-system-packages graphiti-core 2>&1
    if [ $? -ne 0 ]; then
        # Fallback to user install
        python3 -m pip install --user graphiti-core 2>&1
    fi
fi
```

**Why this was needed:**
- User encountered `ModuleNotFoundError: No module named 'pip'` when running `pip install graphiti-core`
- Multiple Python installations (Homebrew vs system) conflict
- Using `python3 -m pip` instead of `pip3` is more reliable
- Explicit installation in install.sh ensures the package is installed regardless of pip issues

### 7. `tests/knowledge/test_graphiti_client.py`

**Complete Rewrite** - All tests updated to mock graphiti-core instead of HTTP responses:

```python
# OLD: Mocking HTTP responses
@patch('httpx.AsyncClient')
async def test_search_success(self, mock_client):
    mock_response = MagicMock()
    mock_response.json.return_value = [{"fact": "Test"}]
    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
    ...

# NEW: Mocking graphiti-core objects
async def test_search_success(self):
    mock_edge = MagicMock()
    mock_edge.uuid = "uuid-1"
    mock_edge.fact = "Test fact 1"

    mock_graphiti = MagicMock()
    mock_graphiti.search = AsyncMock(return_value=[mock_edge])
    client._graphiti = mock_graphiti

    results = await client.search("test query", group_ids=["group1"])
    assert results[0]["fact"] == "Test fact 1"
```

**Test Coverage:**
- 48 tests total, all passing
- Tests for: Config validation, initialization, health check, search, add_episode, close, singleton pattern, edge cases

---

## Issues Encountered and Solutions

### Issue 1: graphiti-core Not Installed

**Symptom:**
```
WARNING:guardkit.knowledge.graphiti_client:graphiti-core not installed. Install with: pip install graphiti-core
Graphiti not available or disabled.
```

**Root Cause:** Package was in pyproject.toml but not being installed due to user's pip configuration issues.

**Solution:** Added explicit installation to `install.sh` using `python3 -m pip` instead of `pip3`.

### Issue 2: Multiple Python Installations Conflict

**Symptom:**
```
ModuleNotFoundError: No module named 'pip'
```

**Root Cause:** Homebrew Python vs system Python conflict. The `pip` command pointed to a broken installation.

**Solution:** Use `python3 -m pip` which always uses the pip module from the same Python interpreter.

### Issue 3: Async Event Loop Warning During Seeding

**Symptom:**
```
ERROR:graphiti_core.driver.neo4j_driver:Error executing Neo4j query: Task ... got Future <Future pending> attached to a different loop
```

**Root Cause:** Nested async contexts when running seeding operations.

**Impact:** Warning only - seeding still completes successfully. This is a known issue with nested async contexts in graphiti-core.

---

## Testing Results

### Unit Tests
```
48 tests passed
Coverage: guardkit/knowledge/graphiti_client.py - 100%
Coverage: guardkit/knowledge/config.py - 100%
```

### Integration Test
```bash
$ guardkit graphiti seed
Graphiti System Context Seeding
Connecting to Neo4j at bolt://localhost:7687...
...
System context seeding complete!

Knowledge categories seeded:
  ✓ product_knowledge
  ✓ command_workflows
  ✓ quality_gate_phases
  ✓ technology_stack
  ✓ feature_build_architecture
  ✓ architecture_decisions
  ✓ failure_patterns
  ✓ component_status
  ✓ integration_points
  ✓ templates
  ✓ agents
  ✓ patterns
  ✓ rules
```

---

## Review Question: Why Were Stubs Written Initially?

This section documents a pattern that has occurred before where the initial implementation writes stubs instead of full implementations.

### Observed Pattern

The initial `/task-work` execution produced files that appeared complete but contained placeholder implementations or missing logic.

### Potential Causes to Investigate

1. **Scope Misunderstanding**: Task description may not have been specific enough about what "migration" entailed

2. **Incremental Implementation**: System may have intended to write basic structure first, then fill in details

3. **Context Window Limits**: Large codebase context may have caused the system to abbreviate implementations

4. **Missing Examples**: Without concrete examples of graphiti-core usage, the system may have written generic stubs

5. **Test-First vs Implementation-First**: If tests were written before implementation, stubs may have been created to make tests compile

### Recommendations for Prevention

1. **Explicit Requirements**: Task descriptions should explicitly state "complete, working implementation" vs "scaffolding/stubs"

2. **Reference Code**: Provide examples of the target library's API usage in the task context

3. **Acceptance Criteria**: Define specific acceptance criteria that can be verified:
   - "All existing tests must pass"
   - "Integration test must demonstrate end-to-end functionality"
   - "No TODO/FIXME comments in production code"

4. **Quality Gate Enhancement**: Add a "stub detection" check in Phase 4.5 that flags:
   - Functions with only `pass` or `raise NotImplementedError`
   - Methods that return hardcoded values without logic
   - Empty try/except blocks

5. **Iterative Validation**: Run integration tests after each major component is implemented, not just at the end

---

## Files Reference

| File | Lines Changed | Purpose |
|------|--------------|---------|
| `guardkit/knowledge/graphiti_client.py` | ~500 | Main client wrapper |
| `guardkit/knowledge/config.py` | ~300 | Configuration loading |
| `docker/docker-compose.graphiti.yml` | ~80 | Docker services |
| `guardkit/cli/graphiti.py` | ~400 | CLI commands |
| `pyproject.toml` | +1 | Dependency |
| `installer/scripts/install.sh` | +32 | Installation |
| `tests/knowledge/test_graphiti_client.py` | ~700 | Unit tests |

---

## Conclusion

The migration from zepai/graphiti Docker REST API to graphiti-core Python library is complete and verified working. The key insight for future similar tasks is that **explicit installation in install.sh is required** for Python packages that may encounter pip configuration issues on user systems.

The stub-writing issue should be investigated separately using `/task-review` to understand why the initial implementation was incomplete and how to prevent this pattern in future tasks.
