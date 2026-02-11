# Graphiti Shared Infrastructure Guide

**Purpose**: Migrate from Neo4j to FalkorDB, deploy shared knowledge graph on Synology NAS, enable multi-machine access via Tailscale, and expose Graphiti to Claude Desktop via MCP server.

**Date**: February 2026  
**Status**: Implementation ready  
**Machines**: MacBook Pro M2 Max (96GB) · Dell GB10 (128GB) · Synology DS918+ (8GB)

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Phase 0: Backup Current Neo4j Data](#phase-0-backup-current-neo4j-data)
- [Phase 1: Query Current Knowledge Graph](#phase-1-query-current-knowledge-graph)
- [Phase 2: FalkorDB Migration](#phase-2-falkordb-migration)
- [Phase 3: Tailscale Mesh Network](#phase-3-tailscale-mesh-network)
- [Phase 4: NAS Deployment](#phase-4-nas-deployment)
- [Phase 5: Graphiti MCP Server](#phase-5-graphiti-mcp-server)
- [Phase 6: Claude Desktop Integration](#phase-6-claude-desktop-integration)
- [Embeddings Strategy](#embeddings-strategy)
- [Project Namespacing](#project-namespacing)
- [Backup and Restore for FalkorDB](#backup-and-restore-for-falkordb)
- [Docs to Update](#docs-to-update)
- [Troubleshooting](#troubleshooting)
- [Cost Summary](#cost-summary)

---

## Architecture Overview

### Target State

```
┌─────────────────────────────────────────────────────────────────┐
│                    Synology DS918+ (NAS)                        │
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  FalkorDB Container  │  │  NATS +      │  │  Dolt        │  │
│  │  Port 6379 (Redis)   │  │  JetStream   │  │  (Task       │  │
│  │  Port 3000 (Browser) │  │              │  │   Archive)   │  │
│  └──────────────────────┘  └──────────────┘  └──────────────┘  │
│           ↑                                                     │
│   Tailscale: 100.x.x.x                                        │
└─────────────────────────────────────────────────────────────────┘
         ↑                              ↑
    Tailscale mesh                 Tailscale mesh
         ↑                              ↑
┌────────────────────┐    ┌──────────────────────────┐
│  MacBook Pro M2    │    │  Dell GB10               │
│                    │    │                           │
│  Graphiti MCP      │    │  Graphiti MCP             │
│  Server (local)    │    │  Server (local)           │
│       ↓            │    │       ↓                   │
│  Claude Desktop    │    │  Claude Code              │
│  Claude Code       │    │  Ollama (optional         │
│                    │    │    local embeddings)       │
│  OpenAI embeddings │    │  OpenAI embeddings        │
└────────────────────┘    └──────────────────────────┘
```

### Why FalkorDB Over Neo4j

| Factor | Neo4j | FalkorDB |
|--------|-------|----------|
| **Latency (p99)** | 46.9s aggregate expansion | Sub-140ms (500x faster) |
| **RAM usage** | 2-4GB JVM heap minimum | ~500MB (7x more efficient) |
| **NAS fit** | Heavy for DS918+ 8GB | Comfortable on 8GB |
| **Deployment** | Complex (APOC plugins, JVM tuning) | Single container |
| **Protocol** | Bolt (7687) | Redis (6379) |
| **Browser** | Port 7474 (polished) | Port 3000 (functional) |
| **Graphiti default** | Legacy (pre-v0.26) | Default since v0.26.3 |
| **Query language** | Cypher | Cypher (compatible) |

### Why This Architecture (Option A)

FalkorDB on NAS, MCP server on each machine. Alternatives considered:

- **Both on NAS**: Simpler deployment, but higher per-call MCP latency (every tool call crosses network). MCP server responsiveness matters for Claude Desktop UX.
- **Everything local**: No shared state. Defeats the purpose of cross-machine knowledge.
- **AWS deployment**: £15-30/month ongoing cost vs £0 for Tailscale + NAS you already own.

**Selected approach**: Fastest MCP response (server is local), network latency only for Redis calls to FalkorDB (sub-ms on LAN, ~10ms via Tailscale).

---

## Phase 0: Backup Current Neo4j Data

**Do this first, before any migration work.**

### Take a Fresh Backup

```bash
cd /path/to/guardkit

# Check if Neo4j is running
docker ps | grep guardkit-neo4j

# If not running, start it
docker compose -f docker/docker-compose.graphiti.yml up -d
sleep 15  # Wait for healthy

# Create both backup types
./scripts/graphiti-backup.sh backup    # Volume tar (fast restore)
./scripts/graphiti-backup.sh dump      # Portable dump (cross-version)

# Verify backups created
./scripts/graphiti-backup.sh list
```

### Verify Before Proceeding

```bash
./scripts/graphiti-backup.sh verify
```

This confirms Neo4j connectivity, counts nodes, and validates the knowledge graph is intact. Record the node count — you'll compare this after FalkorDB migration.

### Existing Backup

A backup exists from February 5, 2026 (`neo4j-backup-20260205_135334.tar.gz`, 34MB). Take a fresh one anyway to capture any recent work.

---

## Phase 1: Query Current Knowledge Graph

**Before migrating, audit what's actually in Graphiti to assess quality and completeness.**

### Option A: Via GuardKit CLI

```bash
# Overall status
guardkit graphiti status

# Run verification queries
guardkit graphiti verify --verbose

# Search specific knowledge areas
guardkit graphiti search "authentication" --group architecture_decisions
guardkit graphiti search "quality gates" --group quality_gate_phases
guardkit graphiti search "player coach" --group feature_build_architecture
```

### Option B: Via Neo4j Browser (Visual)

Open http://localhost:7474 and run Cypher queries:

```cypher
-- Count all nodes by label
MATCH (n) RETURN labels(n) AS label, count(n) AS count ORDER BY count DESC

-- List all episodes with their group_ids
MATCH (e:EpisodicNode) RETURN e.group_id, count(e) AS episodes ORDER BY episodes DESC

-- Show recent episodes (most recently created)
MATCH (e:EpisodicNode) RETURN e.name, e.group_id, e.created_at 
ORDER BY e.created_at DESC LIMIT 20

-- View all entity nodes (the extracted knowledge)
MATCH (n:EntityNode) RETURN n.name, n.summary LIMIT 50

-- Check facts/relationships
MATCH (a:EntityNode)-[r:RELATES_TO]->(b:EntityNode) 
RETURN a.name, r.fact, b.name LIMIT 30

-- Knowledge by project namespace
MATCH (e:EpisodicNode) WHERE e.group_id STARTS WITH 'guardkit__'
RETURN e.group_id, count(e) AS count ORDER BY count DESC

-- Search for specific patterns
MATCH (n:EntityNode) WHERE n.name CONTAINS 'task-work' OR n.summary CONTAINS 'task-work'
RETURN n.name, n.summary
```

### Option C: Set Up Graphiti MCP Locally First (Recommended)

This is the quickest way to get interactive querying working via Claude Desktop. Point the MCP server at your existing local Neo4j before any migration.

**Step 1: Clone and install graphiti-mcp**

```bash
cd ~/Projects
git clone https://github.com/getzep/graphiti.git
cd graphiti/mcp_server

# Create virtualenv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[mcp]"
```

**Step 2: Configure for local Neo4j**

Create a `.env` file in the `mcp_server` directory:

```env
# Point to local Neo4j (current setup)
GRAPH_STORE_PROVIDER=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# OpenAI for embeddings
OPENAI_API_KEY=sk-your-key-here

# LLM for entity extraction
MODEL_NAME=gpt-4o-mini

# MCP transport
TRANSPORT=http
PORT=8000
```

**Step 3: Start the MCP server**

```bash
cd ~/Projects/graphiti/mcp_server
source .venv/bin/activate
python -m mcp_server
```

Server starts on http://localhost:8000/mcp/

**Step 4: Add to Claude Desktop**

On macOS, edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "graphiti-local": {
      "transport": "http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

Restart Claude Desktop. You can now query your knowledge graph conversationally:

> "Search for all entity nodes related to task-work"  
> "What facts exist about the player-coach pattern?"  
> "Show me recent episodes in the architecture_decisions group"

**This gives you immediate insight into what's actually stored before committing to migration.**

---

## Phase 2: FalkorDB Migration

### Step 1: Export from Neo4j (Optional)

If you want to preserve project-specific knowledge, export via Cypher before switching. For system knowledge (seeded data), re-seeding is simpler:

```cypher
-- Export episodes for reference
MATCH (e:EpisodicNode) 
RETURN e.name, e.body, e.group_id, e.source, e.source_description, 
       e.created_at, e.valid_at, e.expired_at
```

### Step 2: Stop Neo4j

```bash
docker compose -f docker/docker-compose.graphiti.yml down
```

### Step 3: Update Docker Compose for FalkorDB

Replace `docker/docker-compose.graphiti.yml`:

```yaml
# Docker Compose configuration for FalkorDB knowledge graph backend
#
# Migration: Replaced Neo4j with FalkorDB (February 2026)
# Rationale: ADR-003 - 500x faster queries, 7x lower RAM, Graphiti default
#
# FalkorDB uses Redis protocol on port 6379 and provides
# a browser UI on port 3000.
#
# Usage:
#   docker compose -f docker/docker-compose.graphiti.yml up -d
#   docker compose -f docker/docker-compose.graphiti.yml down
#   docker compose -f docker/docker-compose.graphiti.yml down -v  # clean slate

services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: guardkit-falkordb
    ports:
      - "6379:6379"    # Redis protocol (Graphiti connection)
      - "3000:3000"    # Browser UI
    volumes:
      - falkordb_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped
    networks:
      - guardkit-knowledge

volumes:
  falkordb_data:
    driver: local

networks:
  guardkit-knowledge:
    driver: bridge
```

Start it:

```bash
docker compose -f docker/docker-compose.graphiti.yml up -d

# Verify
docker ps | grep falkordb
# Browse: http://localhost:3000
```

### Step 4: Update GuardKit Configuration

Update `.guardkit/graphiti.yaml`:

```yaml
enabled: true
project_id: guardkit
host: localhost
port: 6379
timeout: 30.0
graph_store: falkordb

embedding_model: text-embedding-3-small

group_ids:
  - product_knowledge
  - command_workflows
  - architecture_decisions
```

### Step 5: Update GraphitiClient Code

The `graphiti-core` library supports FalkorDB natively since v0.26.3. Update connection in `guardkit/knowledge/graphiti_client.py`:

```python
from graphiti_core import Graphiti

# FalkorDB connection (replaces Neo4j)
graphiti = Graphiti(
    "bolt://localhost:6379",  # FalkorDB uses bolt protocol on Redis port
    store_raw_episode_content=True,
)
```

### Step 6: Re-seed Knowledge

```bash
guardkit graphiti seed --force

# Verify
guardkit graphiti verify --verbose
```

### Step 7: Re-add Project Context

```bash
guardkit graphiti add-context CLAUDE.md --force
guardkit graphiti add-context docs/architecture/ --pattern "ADR-*.md"
guardkit graphiti add-context docs/features/ --pattern "FEATURE-SPEC-*.md"
```

---

## Phase 3: Tailscale Mesh Network

### Install on Each Machine (~10 min per device)

**MacBook Pro:**
```bash
brew install tailscale
tailscale up
```

**Dell GB10 (Ubuntu/Linux):**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**Synology DS918+:**
1. Open Package Center → Search "Tailscale" → Install
2. Authenticate via browser

**James's Mac (if needed later):**
Download app from tailscale.com, sign in. Done.

### Verify Connectivity

```bash
tailscale status
# Shows all devices with 100.x.x.x addresses

ping 100.64.1.3  # NAS Tailscale IP (yours will differ)
```

### MagicDNS (Optional)

Enable in Tailscale admin console → DNS → Enable MagicDNS. Then use hostnames:
```bash
ping synology-nas  # Instead of 100.64.1.3
```

---

## Phase 4: NAS Deployment

### Deploy FalkorDB on Synology

**Via SSH + Docker CLI:**

```bash
ssh admin@synology-nas

docker run -d \
  --name guardkit-falkordb \
  --restart unless-stopped \
  -p 6379:6379 \
  -p 3000:3000 \
  -v /volume1/docker/falkordb:/data \
  falkordb/falkordb:latest
```

**Via Synology Container Manager UI:**
Pull `falkordb/falkordb:latest`, map ports 6379 and 3000, mount `/volume1/docker/falkordb` to `/data`.

### Test Remote Access

From MacBook Pro:
```bash
redis-cli -h 100.64.1.3 -p 6379 PING
# Should return: PONG

# Browser UI: http://100.64.1.3:3000
```

### Update Configuration for NAS

```yaml
# .guardkit/graphiti.yaml
falkordb_host: 100.64.1.3    # NAS Tailscale IP
falkordb_port: 6379
```

---

## Phase 5: Graphiti MCP Server

### Install on Each Development Machine

Both MacBook Pro and Dell GB10 run their own local MCP server instance:

```bash
cd ~/Projects
git clone https://github.com/getzep/graphiti.git
cd graphiti/mcp_server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[mcp]"
```

### Configure for Remote FalkorDB

`.env` in the `mcp_server` directory:

```env
# FalkorDB on NAS (via Tailscale)
GRAPH_STORE_PROVIDER=falkordb
FALKORDB_HOST=100.64.1.3
FALKORDB_PORT=6379

# OpenAI embeddings (consistent vector space everywhere)
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# LLM for entity extraction
MODEL_NAME=gpt-4o-mini

# MCP server
TRANSPORT=http
PORT=8000
SEMAPHORE_LIMIT=10
```

### Launch Script

```bash
#!/bin/bash
# ~/bin/start-graphiti-mcp.sh
cd ~/Projects/graphiti/mcp_server
source .venv/bin/activate
exec python -m mcp_server
```

### MCP Tools Exposed to Claude Desktop

| Tool | Purpose |
|------|---------|
| `add_episode` | Store text, JSON, or message episodes |
| `search_nodes` | Find entity summaries (semantic search) |
| `search_facts` | Query relationships between entities |
| `delete_entity_edge` | Remove specific relationships |
| `delete_episode` | Remove stored episodes |

---

## Phase 6: Claude Desktop Integration

### Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "graphiti-guardkit": {
      "transport": "http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

Restart Claude Desktop.

### Example Queries

**Architecture queries:**
> "Search for nodes related to the quality gate system"

**Decision recall:**
> "Search for architecture decisions about SDK usage"

**Knowledge capture during planning:**
> "Add an episode: We decided to use FalkorDB instead of Neo4j for the knowledge graph backend. Reasons: 500x faster queries, 7x lower RAM, single container deployment."

---

## Embeddings Strategy

### Default: OpenAI (Always Available)

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-your-key-here
```

Works from home, Bristol, client sites. Cost: ~£1-2/month.

### Optional: Ollama on GB10

When at home with GB10 on, you can use local embeddings:

```python
# Ollama uses OpenAI-compatible API
embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        api_key="ollama",
        embedding_model="nomic-embed-text",
        embedding_dim=768,
        base_url="http://100.64.1.2:11434/v1"  # GB10 Tailscale IP
    )
)
```

**Warning**: Mixing embedding models within the same graph breaks semantic search. Pick one and stick with it per graph instance.

**Recommendation**: Use OpenAI `text-embedding-3-small` everywhere. Reserve Ollama for LLM inference (entity extraction) rather than embeddings.

---

## Project Namespacing

Each project gets prefixed group IDs:

```
guardkit__project_architecture    guardkit__feature_specs
poa__project_architecture         poa__domain_knowledge
gcse__project_architecture        gcse__domain_knowledge
```

System groups (shared, never prefixed):
```
role_constraints    guardkit_templates    guardkit_patterns
product_knowledge   command_workflows
```

---

## Backup and Restore for FalkorDB

### Redis BGSAVE (No Downtime)

```bash
# Trigger background save
redis-cli -h 100.64.1.3 -p 6379 BGSAVE

# Copy the dump.rdb
scp admin@synology-nas:/volume1/docker/falkordb/dump.rdb \
    ./backups/graphiti/falkordb-dump-$(date +%Y%m%d_%H%M%S).rdb
```

### Volume Backup (Full Consistency)

```bash
docker stop guardkit-falkordb
docker run --rm \
  -v falkordb_data:/data \
  -v $(pwd)/backups/graphiti:/backup \
  alpine tar czf /backup/falkordb-backup-$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
docker start guardkit-falkordb
```

### Scheduled Backup on NAS

```bash
# Synology Task Scheduler or crontab - daily at 2am
0 2 * * * redis-cli -p 6379 BGSAVE && sleep 5 && \
  cp /volume1/docker/falkordb/dump.rdb \
  /volume1/backups/graphiti/falkordb-$(date +\%Y\%m\%d).rdb
```

### Restore

```bash
docker stop guardkit-falkordb
cp falkordb-dump-YYYYMMDD.rdb /volume1/docker/falkordb/dump.rdb
docker start guardkit-falkordb
```

---

## Docs to Update

### Must Update

| File | Changes |
|------|---------|
| `docs/setup/graphiti-setup.md` | Replace Neo4j with FalkorDB throughout. Ports: 7474/7687 → 6379/3000. Docker Compose reference. Backup section. |
| `docker/docker-compose.graphiti.yml` | Replace Neo4j service with FalkorDB |
| `scripts/graphiti-backup.sh` | Rewrite for FalkorDB: remove neo4j-admin, add Redis BGSAVE, update container/volume names |
| `docs/guides/graphiti-integration-guide.md` | Update Quick Start (FalkorDB ports). FAQ Docker references. Troubleshooting. |
| `docs/architecture/graphiti-architecture.md` | Update architecture diagram and connection details |
| `docs/guides/graphiti-shared-infrastructure.md` | Replace stub with link to this document |

### Should Update

| File | Changes |
|------|---------|
| `docs/guides/graphiti-commands.md` | Verify CLI commands work with FalkorDB |
| `docs/guides/graphiti-testing-validation.md` | Update test setup |
| `docs/deep-dives/graphiti/*` | Review for Neo4j-specific details |
| `docs/features/graphiti-integration/INSTALL-AND-VALIDATE.md` | Update installation steps |

### Python Code

| File | Changes |
|------|---------|
| `guardkit/knowledge/graphiti_client.py` | Update connection for FalkorDB |
| `guardkit/knowledge/config.py` | Add FalkorDB config fields |
| `tests/knowledge/test_graphiti_client*.py` | Update test fixtures |

### New Files

| File | Purpose |
|------|---------|
| `docs/adr/ADR-003-falkordb-migration.md` | ADR documenting the switch |
| This document | Operations and deployment reference |

---

## Troubleshooting

### FalkorDB Won't Start on NAS

```bash
docker logs guardkit-falkordb

# Port conflict (6379 used by another Redis instance)
lsof -i :6379
# Fix: use alternate port: -p 6380:6379
```

### MCP Server Can't Connect to FalkorDB

```bash
# Test Redis connectivity
redis-cli -h 100.64.1.3 -p 6379 PING

# Check Tailscale
tailscale status

# Check NAS firewall: Control Panel → Security → Firewall
# Allow port 6379 for Tailscale subnet (100.64.0.0/10)
```

### Claude Desktop Doesn't Show MCP Tools

1. Verify MCP server running: `curl http://localhost:8000/mcp/`
2. Check JSON syntax in `claude_desktop_config.json`
3. Full restart Claude Desktop (quit from menu bar, relaunch)
4. Check Claude Desktop logs for MCP errors

### Embedding Dimension Mismatch

If you mixed OpenAI and Ollama embeddings:
```bash
guardkit graphiti clear --confirm
guardkit graphiti seed --force
```

---

## Cost Summary

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| Tailscale | £0 | Free personal plan (100 devices, 3 users) |
| OpenAI embeddings | ~£1-2 | text-embedding-3-small |
| FalkorDB on NAS | £0 | Existing hardware |
| OpenAI entity extraction | ~£2-5 | gpt-4o-mini for MCP operations |
| **Total** | **~£3-7/month** | vs £25-30+ for AWS equivalent |

---

## Implementation Order

1. **Backup Neo4j** (5 min) — Phase 0
2. **Set up Graphiti MCP locally pointing at existing Neo4j** (30 min) — Phase 1 Option C
3. **Query via Claude Desktop to audit current knowledge** (explore)
4. **Install Tailscale on all machines** (30 min total) — Phase 3
5. **Deploy FalkorDB on NAS** (15 min) — Phase 4
6. **Migrate: re-seed FalkorDB, re-add project context** (30 min) — Phase 2
7. **Point MCP servers at NAS FalkorDB** (5 min) — Phase 5
8. **Update GuardKit docs** (incremental, separate tasks)

**Quick win**: Steps 1-3 can be done today with zero infrastructure changes. Immediate value from querying what's in Graphiti right now via Claude Desktop.
