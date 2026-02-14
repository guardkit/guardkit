# FalkorDB NAS Deployment Runbook

**Date**: 12 February 2026  
**Status**: ✅ COMPLETE  
**Prerequisite**: Tailscale mesh operational (whitestocks, richards-macbook-pro, promaxgb10-41b1)  
**Goal**: Move FalkorDB from MacBook to Synology DS918+ NAS (`whitestocks`), remove Neo4j  
**See also**: `docs/guides/falkordb-nas-infrastructure-setup.md` for comprehensive reference

---

## Step 1: Deploy FalkorDB on NAS

```bash
# SSH into NAS via Tailscale
ssh richardwoollcott@whitestocks

# Create data directory for bind mount
sudo mkdir -p /volume1/docker/infrastructure/data/falkordb
```

Copy the compose file from MacBook (via Finder SMB share to `/volume1/guardkit/docker/`)  
or via scp:

```bash
# From MacBook
scp ~/Projects/appmilla_github/guardkit/docker/nas/docker-compose.falkordb.yml \
    richardwoollcott@whitestocks:/volume1/guardkit/docker/docker-compose.falkordb.yml
```

Start FalkorDB:

```bash
# On the NAS
ssh richardwoollcott@whitestocks
cd /volume1/guardkit/docker
sudo docker-compose -f docker-compose.falkordb.yml up -d

# Verify container is running and healthy
sudo docker-compose -f docker-compose.falkordb.yml ps
sudo docker logs falkordb --tail 20
```

**Note**: The DS918+ kernel (4.4.180+) does not support CPU CFS scheduler.
If you see a `NanoCPUs` error, ensure there is no `cpus:` line in the compose file.

---

## Step 2: Validate Connectivity from MacBook

```bash
# Test Redis protocol via Tailscale
redis-cli -h whitestocks -p 6379 PING
# Expected: PONG

# Test FalkorDB Browser UI — open in browser:
#   http://whitestocks:3000

# Quick graph round-trip test
redis-cli -h whitestocks -p 6379 GRAPH.QUERY test "CREATE (n:Test {name: 'connectivity_check'}) RETURN n"
redis-cli -h whitestocks -p 6379 GRAPH.QUERY test "MATCH (n:Test) RETURN n.name"
redis-cli -h whitestocks -p 6379 GRAPH.DELETE test
```

---

## Step 3: Verify GuardKit Config

The config has already been updated. Confirm:

```bash
cd ~/Projects/appmilla_github/guardkit
cat .guardkit/graphiti.yaml | grep -E "graph_store|falkordb_host|falkordb_port"
# graph_store: falkordb
# falkordb_host: whitestocks
# falkordb_port: 6379
```

---

## Step 4: Run 8-Point Validation Against NAS

```bash
cd ~/Projects/appmilla_github/guardkit

# Run full validation (auto-loads .env for OPENAI_API_KEY + FALKORDB_HOST)
python scripts/graphiti-validation/validate_falkordb.py
# Expected: 8/8 PASS
```

The validation script auto-loads `.env` from the project root. No manual `export` needed.

---

## Step 5: Remove Neo4j from MacBook

```bash
# Stop and remove Neo4j container + volume
docker stop guardkit-neo4j
docker rm guardkit-neo4j
docker volume rm guardkit_neo4j_data 2>/dev/null || true

# Verify
docker ps -a | grep neo4j
# Should return nothing
```

---

## Step 6: Remove Local FalkorDB from MacBook

```bash
# Stop and remove local FalkorDB container + volume
docker stop guardkit-falkordb
docker rm guardkit-falkordb
docker volume rm guardkit_falkordb_data 2>/dev/null || true
docker volume rm guardkit_docker_falkordb_data 2>/dev/null || true

# Verify — no graph DB containers on MacBook
docker ps -a | grep -E "neo4j|falkordb"
# Should return nothing
```

---

## Step 7: Verify End State

```bash
# MacBook: No graph database containers
docker ps -a | grep -E "neo4j|falkordb"
# Empty

# NAS: FalkorDB running
ssh richardwoollcott@whitestocks "sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
# falkordb   Up X minutes   0.0.0.0:6379->6379/tcp, 0.0.0.0:3000->3000/tcp

# GuardKit config
cat .guardkit/graphiti.yaml | grep falkordb_host
# falkordb_host: whitestocks

# Final validation
python scripts/graphiti-validation/validate_falkordb.py
# 8/8 PASS
```

---

## Tailscale Network Reference

| Machine | Hostname | Tailscale IP | Role |
|---------|----------|-------------|------|
| Dell ProMax GB10 | `promaxgb10-41b1` | 100.84.90.91 | Compute/embeddings |
| MacBook Pro | `richards-macbook-pro` | 100.111.236.109 | Daily development |
| Synology DS918+ | `whitestocks` | 100.92.74.2 | FalkorDB host |

---

## Rollback

If anything goes wrong, restart FalkorDB locally on MacBook:

```bash
cd ~/Projects/appmilla_github/guardkit
docker compose -f docker/docker-compose.graphiti.yml up -d
```

And revert the config:

```yaml
# .guardkit/graphiti.yaml
graph_store: falkordb
falkordb_host: localhost
falkordb_port: 6379
```

---

## Notes

- NAS kernel is Linux 4.4.180+ (DSM 7.x on Celeron J3455) — FalkorDB image is multi-arch x86_64, runs fine
- NAS Tailscale version is 1.58.2-1 (older than MacBook/GB10 at 1.94.1) — works fine for basic connectivity
- `--maxmemory 1gb` caps FalkorDB within DS918+ resource budget
- RDB persistence: saves at 15min/5min/1min intervals based on change frequency
- Add `/volume1/docker/infrastructure/data/` to Synology Hyper Backup for disaster recovery
- Upstream decorator bug workaround is code-level, unaffected by where FalkorDB runs
