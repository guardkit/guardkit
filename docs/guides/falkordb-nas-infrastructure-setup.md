# FalkorDB NAS Infrastructure Setup

**Date**: 12 February 2026  
**Status**: ✅ OPERATIONAL  
**Migration**: Complete — Neo4j removed, FalkorDB on NAS validated 8/8

---

## Architecture Overview

GuardKit's knowledge graph (powered by Graphiti) runs on FalkorDB, hosted on a Synology DS918+ NAS accessible to all development machines via a Tailscale WireGuard mesh.

```
┌──────────────────────────┐     Tailscale Mesh (WireGuard)     ┌──────────────────────────┐
│  MacBook Pro M2 Max      │◄──────────────────────────────────►│  Dell ProMax GB10        │
│  richards-macbook-pro    │                                     │  promaxgb10-41b1         │
│  100.111.236.109         │                                     │  100.84.90.91            │
│                          │                                     │                          │
│  • GuardKit development  │                                     │  • Compute/embeddings    │
│  • Claude Code           │                                     │  • Ollama (future)       │
│  • No local graph DB     │                                     │  • .NET PoA Platform     │
└──────────┬───────────────┘                                     └──────────┬───────────────┘
           │                                                                │
           │                  ┌──────────────────────────┐                  │
           │                  │  Synology DS918+ NAS      │                  │
           └─────────────────►│  whitestocks              │◄─────────────────┘
                              │  100.92.74.2              │
                              │  LAN: 172.30.1.156        │
                              │                            │
                              │  • FalkorDB :6379          │
                              │  • FalkorDB Browser :3000  │
                              │  • NATS (planned)          │
                              │  • Dolt (planned)          │
                              └────────────────────────────┘
```

---

## Tailscale Network

| Machine | Hostname | Tailscale IP | OS | Role |
|---------|----------|-------------|-----|------|
| MacBook Pro M2 Max (96GB) | `richards-macbook-pro` | 100.111.236.109 | macOS 15.6.1 | Daily development |
| Dell ProMax GB10 (128GB) | `promaxgb10-41b1` | 100.84.90.91 | DGX OS (Ubuntu 24.04 ARM64) | Compute, embeddings, .NET |
| Synology DS918+ (8GB) | `whitestocks` | 100.92.74.2 | DSM 7.x (Linux 4.4.180+) | Shared infrastructure |

**Tailscale versions**: MacBook & GB10 at 1.94.1, NAS at 1.58.2-700058002 (latest available for Synology).

All machines use Tailscale MagicDNS — hostnames resolve automatically (e.g., `redis-cli -h whitestocks`). If MagicDNS has issues, use Tailscale IPs directly.

---

## NAS Hardware & Resource Budget

| Spec | Value |
|------|-------|
| CPU | Intel Celeron J3455 (4-core, 1.5GHz burst 2.3GHz) |
| RAM | 8GB DDR3L |
| Storage | 12TB (4×3TB Seagate IronWolf, SHR) |
| OS | DSM 7.x |
| Kernel | Linux 4.4.180+ |

| Service | Expected RAM | Max Configured | Notes |
|---------|-------------|----------------|-------|
| FalkorDB | ~200-500MB | 1.5GB (container) / 1GB (maxmemory) | Currently deployed |
| NATS + JetStream | ~50-100MB | 512MB | Planned |
| Dolt | ~100-200MB | 512MB | Planned |
| DSM + file services | ~1-2GB | — | Always running |
| **Remaining** | **~4.5-6.5GB** | — | Comfortable headroom |

**Kernel limitation**: The DS918+ kernel (4.4.180+) does not support CPU CFS scheduler, so Docker `cpus` limits cannot be used. Memory limits (`mem_limit`) work fine. FalkorDB's `--maxmemory 1gb` is the primary resource constraint.

---

## FalkorDB Deployment

### What's Deployed

| Component | Location | Details |
|-----------|----------|---------|
| Docker Compose file | NAS: `/volume1/guardkit/docker/docker-compose.falkordb.yml` | Also in repo: `docker/nas/docker-compose.falkordb.yml` |
| Data directory | NAS: `/volume1/docker/infrastructure/data/falkordb/` | Bind-mounted to container `/data` |
| Container name | `falkordb` | `falkordb/falkordb:latest` |
| Redis protocol | `whitestocks:6379` | Main connection for Graphiti |
| Browser UI | `http://whitestocks:3000` | Web-based graph browsing |

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: falkordb
    ports:
      - "6379:6379"   # Redis protocol
      - "3000:3000"   # FalkorDB Browser UI
    volumes:
      - falkordb_data:/data
    command: >
      --maxmemory 1gb
      --save 900 1
      --save 300 10
      --save 60 10000
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    mem_limit: 1536m

volumes:
  falkordb_data:
    driver: local
    driver_opts:
      type: none
      device: /volume1/docker/infrastructure/data/falkordb
      o: bind
```

### RDB Persistence

FalkorDB uses Redis-style RDB snapshots with three save intervals:

| Interval | Condition | Purpose |
|----------|-----------|---------|
| 15 minutes | ≥1 change | Catch infrequent updates |
| 5 minutes | ≥10 changes | Normal development activity |
| 1 minute | ≥10,000 changes | Bulk operations / batch imports |

Snapshots are written to `/volume1/docker/infrastructure/data/falkordb/` — add this to Synology Hyper Backup.

### Management Commands

```bash
# SSH into NAS
ssh richardwoollcott@whitestocks

# Start / stop / restart
cd /volume1/guardkit/docker
sudo docker-compose -f docker-compose.falkordb.yml up -d
sudo docker-compose -f docker-compose.falkordb.yml down
sudo docker-compose -f docker-compose.falkordb.yml restart

# View logs
sudo docker logs falkordb --tail 50
sudo docker logs falkordb -f  # follow

# Check status
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Redis CLI on the NAS directly
redis-cli -p 6379 PING

# Redis CLI from MacBook (via Tailscale)
redis-cli -h whitestocks -p 6379 PING

# FalkorDB Browser UI (from any machine on Tailscale)
# http://whitestocks:3000
```

---

## GuardKit Configuration

### YAML Config (`.guardkit/graphiti.yaml`)

```yaml
project_id: guardkit
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
embedding_model: text-embedding-3-small
group_ids:
  - product_knowledge
  - command_workflows
  - architecture_decisions
```

### Environment Variables (`.env`)

```bash
# OpenAI API Key - required for Graphiti embeddings
OPENAI_API_KEY=sk-proj-...

# FalkorDB Knowledge Graph - hosted on NAS via Tailscale
GRAPH_STORE=falkordb
FALKORDB_HOST=whitestocks
FALKORDB_PORT=6379
```

### Config Resolution Priority

1. **Environment variables** (`FALKORDB_HOST`, `GRAPH_STORE`, etc.) — highest
2. **YAML config** (`.guardkit/graphiti.yaml`) — middle
3. **Code defaults** — lowest (localhost, neo4j)

The `.env` file is auto-loaded by the validation script. For other usage, run `export $(cat .env | grep -v '^#' | xargs)` or source it in your shell profile.

---

## Validation

### Running the 8-Point Validation

```bash
cd ~/Projects/appmilla_github/guardkit
python scripts/graphiti-validation/validate_falkordb.py
```

The script auto-loads `.env` from the project root (no manual `export` needed). It tests:

| Check | What It Validates |
|-------|-------------------|
| AC-001 | `falkordb` + `graphiti_core` importable, `OPENAI_API_KEY` set |
| AC-002 | TCP connection + Redis PING to `whitestocks:6379` |
| AC-003 | `Graphiti(graph_driver=FalkorDriver(...))` + `build_indices_and_constraints()` |
| AC-004 | `add_episode()` creates episode (verified by UUID) |
| AC-005 | `search()` returns episode with correct content |
| AC-006 | Fulltext search with `group_ids` filtering across two groups |
| AC-007 | Datetime fields survive `add_episode` → `search` round-trip |
| AC-008 | `execute_query()` returns `(records, header, None)` tuple |

### Latest Validation Result (12 Feb 2026)

```
FalkorDB: whitestocks:6379
Total: 8 passed, 0 failed, 0 skipped
ALL 8 CHECKS PASSED
```

---

## Migration History

### What Was Migrated

All 8 FalkorDB migration tasks (TASK-FKDB-001 through TASK-FKDB-008) plus one discovered task (TASK-FKDB-32D9 for upstream bug workaround) were completed. Key changes:

| File | Change |
|------|--------|
| `guardkit/knowledge/config.py` | Added `graph_store`, `falkordb_host`, `falkordb_port` fields |
| `guardkit/knowledge/graphiti_client.py` | Conditional `FalkorDriver`/`Neo4jDriver`, `execute_query()` refactor |
| `guardkit/knowledge/falkordb_workaround.py` | Monkey-patch for upstream decorator bug (#1161) |
| `docker/nas/docker-compose.falkordb.yml` | NAS-specific compose (this file) |
| `docs/adr/ADR-003-*.md` | Migration decision record |

### What Was Removed

| Component | Status |
|-----------|--------|
| Neo4j container (`guardkit-neo4j`) | ❌ Removed from MacBook |
| Local FalkorDB container (`guardkit-falkordb`) | ❌ Removed from MacBook |
| Neo4j Docker volume | ❌ Pruned |
| Local FalkorDB Docker volume | ❌ Pruned |

### Test Results Post-Migration

| Test Suite | Result |
|------------|--------|
| 18 workaround tests | ✅ All passing |
| 129 existing graphiti client tests | ✅ All passing (0 regressions) |
| 8-point FalkorDB E2E validation (NAS) | ✅ 8/8 PASS |
| graphiti-core version | v0.26.3 |
| falkordb package version | 1.4.0 |

---

## Known Issues

### Upstream Decorator Bug (graphiti-core)

The `@handle_multiple_group_ids` decorator in `graphiti_core/decorators.py` uses `> 1` instead of `>= 1`, causing single `group_id` FalkorDB searches to use the wrong database after `add_episode()` mutates the shared driver.

**GuardKit workaround**: `guardkit/knowledge/falkordb_workaround.py` — auto-detects upstream fix.  
**Upstream issue**: [getzep/graphiti#1161](https://github.com/getzep/graphiti/issues/1161)  
**Upstream PR**: [getzep/graphiti#1170](https://github.com/getzep/graphiti/pull/1170) (open, unreviewed 3+ weeks)  
**Bug report doc**: `docs/reviews/graphiti-falkordb-migration/upstream-decorator-bug-report.md` — ready for upstream comment.

---

## Future Infrastructure (Planned)

| Service | Purpose | NAS Deployment | Status |
|---------|---------|----------------|--------|
| **NATS + JetStream** | Message bus for agent orchestration | Port 4222 (client), 8222 (monitoring) | Planned |
| **Dolt** | Task archive (Git-for-data) | Port 3306 (MySQL protocol) | Planned |
| **GB10 Ollama** | Local embeddings (replace OpenAI API) | `promaxgb10-41b1:11434` | Planned |

These are independent of FalkorDB and can be deployed incrementally to the NAS using the full stack compose from the three-machine infrastructure guide.

---

## Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| Can't connect to FalkorDB | `redis-cli -h whitestocks -p 6379 PING` | Check container: `ssh richardwoollcott@whitestocks "sudo docker ps"` |
| MagicDNS not resolving `whitestocks` | `ping whitestocks` | Use IP: `redis-cli -h 100.92.74.2 -p 6379 PING` |
| Container won't start (cpus error) | Check compose file | Remove any `cpus:` line — kernel doesn't support CFS scheduler |
| OPENAI_API_KEY not set | `echo $OPENAI_API_KEY` | `export $(cat .env \| grep -v '^#' \| xargs)` |
| Validation script can't find .env | Run from project root | `cd ~/Projects/appmilla_github/guardkit` |
| NAS SSH access | `ssh richardwoollcott@whitestocks` | Enable SSH in DSM: Control Panel → Terminal & SNMP |
| FalkorDB Browser UI not loading | `http://whitestocks:3000` | Check port 3000 exposed in compose |

---

## Key File Reference

| File | Purpose |
|------|---------|
| `.guardkit/graphiti.yaml` | GuardKit Graphiti config (points to NAS) |
| `.env` | Environment variables (OPENAI_API_KEY, FALKORDB_HOST) |
| `.env.example` | Template for new setups |
| `docker/nas/docker-compose.falkordb.yml` | NAS FalkorDB compose (repo copy) |
| `guardkit/knowledge/config.py` | Config loading with env var overrides |
| `guardkit/knowledge/graphiti_client.py` | Conditional FalkorDB/Neo4j driver |
| `guardkit/knowledge/falkordb_workaround.py` | Upstream decorator bug workaround |
| `scripts/graphiti-validation/validate_falkordb.py` | 8-point validation script |
| `docs/adr/ADR-003-*.md` | Migration decision record |
| `docs/guides/falkordb-nas-deployment-runbook.md` | Step-by-step deployment runbook |
