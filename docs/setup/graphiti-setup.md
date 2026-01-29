# Graphiti Setup Guide

**Purpose**: Set up the Graphiti temporal knowledge graph to provide persistent memory and context across GuardKit sessions.

**Technology**: Graphiti + Neo4j (temporal knowledge graph with semantic search)

---

## Overview

Graphiti is a temporal knowledge graph that gives GuardKit persistent memory across sessions. Instead of re-learning your project's architecture and patterns every time, GuardKit can recall previous decisions, patterns, and context from the knowledge graph.

**Key Benefits**:
- **Persistent Memory**: Context survives across sessions and restarts
- **Semantic Search**: Find related decisions, patterns, and architecture
- **Temporal Tracking**: See how decisions evolved over time
- **Automatic Integration**: Works transparently during `/task-work` and `/feature-build`

**What Gets Stored**:
- Product knowledge (GuardKit concepts, entities, relationships)
- Command workflows (usage patterns, best practices)
- Quality gate phases (testing, review processes)
- Technology stack information (templates, agents, patterns)
- Architecture Decision Records (ADRs for feature-build workflow)

---

## Prerequisites

Before installing, ensure you have:

- **Docker Desktop** (or Docker Engine + Docker Compose) ([download here](https://www.docker.com/products/docker-desktop))
- **Python 3.10+** with async support
- **OpenAI API Key** for embeddings ([get one here](https://platform.openai.com/api-keys))
- **Recommended**: 4GB RAM, SSD storage for graph database

Verify Docker installation:
```bash
docker --version        # Should show 20.10.0 or later
docker compose version  # Should show 2.0.0 or later
```

---

## Installation Steps

### Step 1: Start Graphiti Services

Start the Neo4j graph database and Graphiti API server using Docker Compose:

```bash
# From your GuardKit project directory
docker compose -f docker/docker-compose.graphiti.yml up -d
```

**Expected output**:
```
[+] Running 3/3
 ✔ Network guardkit-knowledge      Created
 ✔ Container guardkit-neo4j        Started
 ✔ Container guardkit-graphiti     Started
```

**What this does**:
- Creates `guardkit-knowledge` network for service communication
- Starts `guardkit-neo4j` on ports 7474 (HTTP) and 7687 (Bolt) (graph database backend)
- Starts `guardkit-graphiti` on port 8000 (API server)
- Creates persistent volumes for data storage

**Verify services are running**:
```bash
docker ps
```

You should see:
```
CONTAINER ID   IMAGE                      STATUS         PORTS
abc123def456   zepai/graphiti:latest      Up 30 seconds  0.0.0.0:8000->8000/tcp
def456ghi789   neo4j:5.26.0               Up 31 seconds  0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
```

---

### Step 2: Configure Environment

Set your OpenAI API key for embeddings:

```bash
# Option 1: Export in shell (temporary)
export OPENAI_API_KEY="sk-your-api-key-here"

# Option 2: Add to ~/.bashrc or ~/.zshrc (permanent)
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Option 3: Use .env file (project-specific)
echo "OPENAI_API_KEY=sk-your-api-key-here" > .env
```

**Optional Configuration Overrides**:

Graphiti uses `.guardkit/graphiti.yaml` for configuration. Override any setting via environment variables:

```bash
# Disable Graphiti temporarily
export GRAPHITI_ENABLED=false

# Change host/port (if running remotely)
export GRAPHITI_HOST=192.168.1.100
export GRAPHITI_PORT=8080

# Increase timeout for slow connections
export GRAPHITI_TIMEOUT=60.0

# Change config directory location
export GUARDKIT_CONFIG_DIR=/path/to/custom/config
```

---

### Step 3: Verify Connection

Check that GuardKit can connect to Graphiti:

```bash
guardkit graphiti status
```

**Expected output**:
```
Graphiti Status

Enabled   Yes
Host      localhost
Port      8000
Timeout   30.0s

Checking connection...
Connection: OK
Health: OK

Seeded: No
Run 'guardkit graphiti seed' to seed system context.
```

**If connection fails**, see [Troubleshooting: Connection Failed](#connection-failed).

---

### Step 4: Seed Knowledge

Load GuardKit system context into the knowledge graph:

```bash
guardkit graphiti seed
```

**Expected output**:
```
Graphiti System Context Seeding

Connecting to Graphiti at localhost:8000...
Connected to Graphiti

Seeding system context...

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

Run 'guardkit graphiti verify' to test queries.
```

**Note**: Seeding is a one-time operation. Use `--force` to re-seed:
```bash
guardkit graphiti seed --force
```

---

### Step 5: Verify Seeding

Run test queries to verify knowledge was seeded correctly:

```bash
guardkit graphiti verify --verbose
```

**Expected output**:
```
Graphiti Verification

Connecting to Graphiti at localhost:8000...
Connected

Running verification queries...

✓ What is GuardKit?
    -> guardkit_product (score: 0.92)
    -> quality_gates (score: 0.87)
✓ How to invoke task-work?
    -> task-work_command (score: 0.94)
    -> workflow_phases (score: 0.86)
✓ What are the quality phases?
    -> phase_2_planning (score: 0.91)
    -> phase_4_testing (score: 0.89)
✓ What is the Player-Coach pattern?
    -> player_agent (score: 0.93)
    -> coach_agent (score: 0.90)
✓ How to use SDK vs subprocess?
    -> adr-fb-001 (score: 0.95)
    -> sdk_usage (score: 0.88)

Results: 5 passed, 0 failed
Verification complete!
```

**If queries fail**, see [Troubleshooting: No Context in Sessions](#no-context-in-sessions).

---

## Configuration File Reference

The complete `.guardkit/graphiti.yaml` configuration file:

```yaml
# Graphiti Knowledge Graph Configuration
#
# All settings can be overridden via environment variables:
#   - GRAPHITI_ENABLED: Enable/disable integration
#   - GRAPHITI_HOST: Server hostname
#   - GRAPHITI_PORT: Server port
#   - GRAPHITI_TIMEOUT: Connection timeout in seconds
#
# To start Graphiti services:
#   docker compose -f docker/docker-compose.graphiti.yml up -d

# Enable Graphiti integration (set to false to disable)
enabled: true

# Graphiti server connection settings
host: localhost
port: 8000
timeout: 30.0

# OpenAI embedding model for semantic search
# Requires OPENAI_API_KEY environment variable
embedding_model: text-embedding-3-small

# Group IDs for organizing knowledge
# These create separate namespaces in the knowledge graph
group_ids:
  - product_knowledge      # Domain concepts, entities, relationships
  - command_workflows      # GuardKit command patterns and usage
  - architecture_decisions # ADRs and design rationale
```

**Configuration Priority** (highest to lowest):
1. Environment variables (`GRAPHITI_ENABLED`, `GRAPHITI_HOST`, etc.)
2. YAML configuration file (`.guardkit/graphiti.yaml`)
3. Default values (enabled, localhost:8000, 30s timeout)

**Environment Variable Override Patterns**:

| Setting | Environment Variable | Type | Example |
|---------|---------------------|------|---------|
| `enabled` | `GRAPHITI_ENABLED` | bool | `true`, `false`, `1`, `0` |
| `host` | `GRAPHITI_HOST` | string | `localhost`, `192.168.1.100` |
| `port` | `GRAPHITI_PORT` | int | `8000`, `9000` |
| `timeout` | `GRAPHITI_TIMEOUT` | float | `30.0`, `60.0` |

---

## Troubleshooting

### Connection Failed

**Symptom**: `guardkit graphiti status` shows "Connection: Failed"

**Causes & Solutions**:

1. **Docker containers not running**:
   ```bash
   # Check container status
   docker ps

   # Restart containers if stopped
   docker compose -f docker/docker-compose.graphiti.yml up -d
   ```

2. **Port conflicts** (another service using 7474, 7687, or 8000):
   ```bash
   # Check what's using the ports
   lsof -i :7474
   lsof -i :7687
   lsof -i :8000

   # Change ports in docker-compose.graphiti.yml
   # Then restart containers
   docker compose -f docker/docker-compose.graphiti.yml down
   docker compose -f docker/docker-compose.graphiti.yml up -d
   ```

3. **Container health check failing**:
   ```bash
   # View container logs
   docker compose -f docker/docker-compose.graphiti.yml logs -f

   # Look for error messages
   docker logs guardkit-graphiti
   docker logs guardkit-neo4j
   ```

4. **Network issues**:
   ```bash
   # Recreate network
   docker compose -f docker/docker-compose.graphiti.yml down
   docker compose -f docker/docker-compose.graphiti.yml up -d
   ```

---

### Seeding Errors

**Symptom**: `guardkit graphiti seed` fails with error

**Common errors**:

1. **"OPENAI_API_KEY not set"**:
   ```bash
   # Verify API key is set
   echo $OPENAI_API_KEY

   # If empty, export it
   export OPENAI_API_KEY="sk-your-api-key-here"
   ```

2. **"Connection timeout"**:
   ```bash
   # Increase timeout in config or via env var
   export GRAPHITI_TIMEOUT=60.0

   # Retry seeding
   guardkit graphiti seed --force
   ```

3. **"Already seeded"**:
   ```bash
   # Force re-seeding (overwrites existing data)
   guardkit graphiti seed --force
   ```

4. **"Permission denied"** or **"Cannot write to .guardkit/"**:
   ```bash
   # Check directory permissions
   ls -la .guardkit/

   # Fix permissions if needed
   chmod 755 .guardkit/
   ```

---

### No Context in Sessions

**Symptom**: Queries return no results or Graphiti doesn't seem to provide context

**Verification steps**:

1. **Check seeding status**:
   ```bash
   guardkit graphiti status
   ```

   Should show "Seeded: Yes (version X.Y.Z)"

2. **Run verbose verification**:
   ```bash
   guardkit graphiti verify --verbose
   ```

   Should show query results with scores

3. **Manually test search**:
   ```python
   from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
   from guardkit.knowledge.config import load_graphiti_config
   import asyncio

   async def test_search():
       settings = load_graphiti_config()
       config = GraphitiConfig(
           enabled=settings.enabled,
           host=settings.host,
           port=settings.port,
           timeout=settings.timeout
       )
       client = GraphitiClient(config)
       await client.initialize()

       results = await client.search(
           "What is GuardKit?",
           group_ids=["product_knowledge"],
           num_results=5
       )

       print(f"Found {len(results)} results")
       for r in results:
           print(f"  - {r.get('name', 'unknown')}: {r.get('score', 0):.2f}")

   asyncio.run(test_search())
   ```

4. **Re-seed if necessary**:
   ```bash
   guardkit graphiti seed --force
   ```

---

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Connection refused` | Graphiti API not running | Start containers with `docker compose up -d` |
| `Name or service not known` | DNS resolution failed | Check `host` setting in config |
| `Timeout waiting for response` | Connection too slow | Increase `timeout` in config |
| `API key not found` | OPENAI_API_KEY not set | Export API key to environment |
| `Permission denied` | Cannot access config directory | Fix file permissions with `chmod` |
| `Invalid port number` | Port out of range (1-65535) | Check `port` setting in config |

---

## Docker Compose Reference

### Services Started

The `docker-compose.graphiti.yml` file starts two services:

**1. Neo4j** (Graph Database):
- **Image**: `neo4j:5.26.0`
- **Container**: `guardkit-neo4j`
- **Ports**: `7474` (HTTP/Browser), `7687` (Bolt protocol)
- **Volumes**: `neo4j_data:/data`, `neo4j_logs:/logs` (persistent storage)
- **Health Check**: Cypher shell check every 10s
- **Browser**: http://localhost:7474

**2. Graphiti API** (Knowledge Graph Server):
- **Image**: `zepai/graphiti:latest`
- **Container**: `guardkit-graphiti`
- **Port**: `8000` (HTTP API)
- **Dependencies**: Waits for Neo4j to be healthy
- **Environment**:
  - `OPENAI_API_KEY`: Your OpenAI API key (required)
  - `NEO4J_URI`: Connection to Neo4j (`bolt://neo4j:7687`)
  - `NEO4J_USER`: Neo4j username (`neo4j`)
  - `NEO4J_PASSWORD`: Neo4j password (`password123`)
  - `EMBEDDING_MODEL`: OpenAI embedding model (`text-embedding-3-small`)

### Port Mappings

| Service | Container Port | Host Port | Purpose |
|---------|---------------|-----------|---------|
| Neo4j | 7474 | 7474 | HTTP/Browser interface |
| Neo4j | 7687 | 7687 | Bolt protocol (database connections) |
| Graphiti | 8000 | 8000 | HTTP API for knowledge graph |

### Volume Persistence

Data is persisted in Docker volumes:

```bash
# View volumes
docker volume ls

# Inspect Neo4j data volume
docker volume inspect guardkit-graphiti_neo4j_data

# Backup volume (optional)
docker run --rm -v guardkit-graphiti_neo4j_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/neo4j-backup.tar.gz -C /data .

# Restore volume (optional)
docker run --rm -v guardkit-graphiti_neo4j_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/neo4j-backup.tar.gz -C /data
```

### Container Management

**View logs**:
```bash
# All services
docker compose -f docker/docker-compose.graphiti.yml logs -f

# Specific service
docker logs guardkit-graphiti -f
docker logs guardkit-neo4j -f
```

**Stop services** (preserves data):
```bash
docker compose -f docker/docker-compose.graphiti.yml down
```

**Stop and remove volumes** (clean slate):
```bash
docker compose -f docker/docker-compose.graphiti.yml down -v
```

**Restart services**:
```bash
docker compose -f docker/docker-compose.graphiti.yml restart
```

---

## Next Steps

Once Graphiti is set up and verified:

1. **Use in workflows**: Graphiti automatically provides context during `/task-work` and `/feature-build`
2. **Seed ADRs**: Run `guardkit graphiti seed-adrs` to load Architecture Decision Records
3. **Monitor usage**: Check logs to see Graphiti queries during sessions
4. **Disable if needed**: Set `GRAPHITI_ENABLED=false` to temporarily disable

**Related Documentation**:
- [Feature-Build Workflow](../guides/feature-build-workflow.md) - How Graphiti enhances autonomous builds
- [ADR Seeding](../guides/adr-seeding.md) - Loading Architecture Decision Records
- [Graphiti Integration Deep Dive](../deep-dives/graphiti-integration.md) - Technical details
