# RUNBOOK — GB10 infrastructure orchestration

**Scope.** The local infrastructure tier on `promaxgb10-41b1`: llama-swap
(LLM + embeddings), graphiti-mcp (knowledge-graph MCP server), and FalkorDB
on the NAS at `whitestocks:6379`. Out of scope: NATS infrastructure tier
and the agents tier — both have hook stubs in `scripts/infra/` that future
tasks will fill in (see §5).

**Single point of entry.** Three top-level scripts, all idempotent:

```
./scripts/infra-up.sh       # Bring everything up
./scripts/infra-down.sh     # Bring graphiti-mcp down (llama-swap stays up)
./scripts/infra-status.sh   # One-screen state summary (always exit 0)
```

Tier scripts they delegate to:

```
./scripts/graphiti-stack-up.sh      # graphiti-mcp + preconditions
./scripts/graphiti-stack-down.sh    # graphiti-mcp only
./scripts/graphiti-mcp.sh           # raw container start (called by stack-up)
./scripts/graphiti-mcp-build.sh     # one-time, builds graphiti-mcp-standalone:local
```

---

## 1. What lives where

| Component       | Where                                      | Managed by                                |
|-----------------|--------------------------------------------|-------------------------------------------|
| llama-swap      | GB10, port `:9000`                          | `llama-swap-keepalive.timer` (every 5 min) + `llama-swap-healthcheck.timer` (weekly). Never started/stopped from `infra-*.sh`. |
| `qwen-graphiti` | model served by llama-swap                  | llama-swap config (`/opt/llama-swap/config/config.yaml`)         |
| `nomic-embed`   | model served by llama-swap (768-dim)        | llama-swap config                                                |
| graphiti-mcp    | GB10, port `:8004`, container `graphiti-mcp` | `infra-up.sh` → `graphiti-stack-up.sh` → `graphiti-mcp.sh`       |
| FalkorDB        | NAS `whitestocks:6379` over Tailscale       | Compose on the NAS (`/volume1/guardkit/docker`); not local       |

**Canonical endpoints jarvis (and other clients) point at:**

```
LLM/embed  http://localhost:9000/v1            (llama-swap, host-local)
Graphiti   http://promaxgb10-41b1:8004/mcp     (no trailing slash; /mcp/ 307s)
FalkorDB   redis://whitestocks:6379            (Tailscale)
```

> **Trailing slash on `/mcp`.** `/mcp/` returns `307` to negotiate session
> establishment, which breaks Claude Code's POST flow on some clients. The
> jarvis-side env var should always be `JARVIS_GRAPHITI_ENDPOINT=http://promaxgb10-41b1:8004/mcp`
> (no trailing slash). The Docker healthcheck probes `/mcp/` (with slash)
> because we only need it to confirm the listener is alive and accepts any
> 2xx/3xx/4xx as healthy.

---

## 2. Cold-start procedure (fresh boot of GB10)

```bash
cd ~/Projects/appmilla_github/guardkit

# 1. Confirm llama-swap recovered after boot. The keepalive timer fires
#    every 5 minutes; if you don't want to wait, trigger one shot:
sudo systemctl start llama-swap-keepalive.service

# 2. Bring everything else up. infra-up.sh will:
#      - probe llama-swap and trigger keepalive if needed
#      - probe FalkorDB on whitestocks:6379
#      - start graphiti-mcp
#      - emit per-component pass/fail
./scripts/infra-up.sh

# 3. Confirm.
./scripts/infra-status.sh
```

**Expected status output** when healthy (excerpt):

```
── llama-swap (LLM + embed, :9000) ──
  endpoint:    UP at http://localhost:9000
  qwen-graphiti listed:  yes
  nomic-embed   listed:  yes

── graphiti-mcp (:8004) ──
  container:   running
  health:      healthy

── FalkorDB (whitestocks:6379, NAS via Tailscale) ──
  reachable:   yes (PONG over Tailscale)
```

---

## 3. DGX-OS-update reboot procedure

The DGX OS pushes regular kernel/driver updates. The clean cycle is:

```bash
# 1. Bring the local infra down. graphiti-mcp first; llama-swap stays up
#    by default because other tiers (autobuild, jarvis) consume it. Pass
#    --stop-llama-swap if you want a really cold tear-down.
./scripts/infra-down.sh
# (optional, rare:)
./scripts/infra-down.sh --stop-llama-swap

# 2. Reboot.
sudo reboot

# 3. After the box comes back, llama-swap-keepalive.timer (re-armed by
#    systemd's persistent flag) will revive llama-swap within 5 minutes.
#    Don't wait — trigger it:
sudo systemctl start llama-swap-keepalive.service

# 4. Bring graphiti-mcp + hooks back up.
./scripts/infra-up.sh

# 5. Confirm.
./scripts/infra-status.sh
```

---

## 4. Per-component healthcheck strategy

### 4.1 llama-swap

- **Probe:** `curl -fsS http://localhost:9000/v1/models` should list
  `qwen-graphiti`, `nomic-embed`, `qwen36-workhorse`, `gemma4-tutor`.
- **Recover:** `sudo systemctl start llama-swap-keepalive.service`
  (one-shot revive). The timer also fires every 5 min.
- **Logs:** `journalctl -u llama-swap-keepalive.service --since '1 hour ago'`.
- **Touch policy:** `infra-*.sh` never modifies llama-swap. The only place
  that does is the keepalive script, and the only systemd touch the
  orchestrator does is `start llama-swap-keepalive.service` — same as the
  timer.

### 4.2 graphiti-mcp

- **Probe (TCP/listener):** `docker inspect graphiti-mcp --format '{{.State.Health.Status}}'`
  → `healthy`. The container's own healthcheck probes
  `http://localhost:8004/mcp/` and accepts 2xx/3xx/4xx as serving (graphiti
  returns 307 there to negotiate sessions).

  > The vendored upstream Dockerfile bakes `curl -f http://localhost:8000/health`
  > as its HEALTHCHECK. We override that at `docker run` time inside
  > `graphiti-mcp.sh` (via `--health-cmd`/`--health-interval`/etc.) because
  > (a) we bind `:8004`, not `:8000`, and (b) graphiti-mcp has no `/health`
  > endpoint. The vendored repo (`~/Projects/appmilla_github/graphiti`) is
  > intentionally treated as read-only.

- **Probe (MCP protocol round-trip):** the canonical jarvis-style smoke
  check, returns HTTP 200 with a JSON-RPC `initialize` response —

  ```bash
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' --max-time 5 \
    -X POST http://promaxgb10-41b1:8004/mcp \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
         "params":{"protocolVersion":"2024-11-05",
                   "capabilities":{},
                   "clientInfo":{"name":"smoke-check","version":"0.1"}}}'
  # Expected: HTTP 200
  ```

- **Logs:** `docker logs --tail 100 graphiti-mcp`. On a clean boot you
  should see lines like `Using LLM provider: openai / qwen-graphiti`,
  `Successfully initialized Graphiti client`, and
  `Running MCP server with streamable HTTP transport on 0.0.0.0:8004`.

- **Recover:** `./scripts/graphiti-stack-down.sh && ./scripts/graphiti-stack-up.sh`.

### 4.3 FalkorDB (on NAS)

- **Probe:** `(echo -e "PING\r"; sleep 0.3) | nc -w 2 whitestocks 6379`
  → expect `+PONG` on stdout.
- **Recover:** SSH to NAS and check the FalkorDB compose:
  ```
  ssh richardwoollcott@whitestocks
  cd /volume1/guardkit/docker
  sudo docker-compose -f docker-compose.falkordb.yml ps
  sudo docker-compose -f docker-compose.falkordb.yml restart
  ```
- **`infra-*.sh` never restarts FalkorDB.** It's on a different machine.

### 4.4 The Tailscale precondition

If the GB10 cannot reach the NAS, every FalkorDB probe in `infra-up.sh`
and `infra-status.sh` will fail. Verify with `tailscale status` and look
for `whitestocks` listed and reachable. Recover with
`sudo tailscale up`.

---

## 5. Future-tier hooks (extension surface)

`infra-up.sh`, `infra-down.sh`, and `infra-status.sh` already source
hook stubs from `scripts/infra/`. Each is currently a no-op that prints a
"TODO: implemented by future task" line. The intended shape:

```
scripts/infra/
├── nats-up.sh        ← currently a no-op; to be filled in
├── nats-down.sh      ← currently a no-op; to be filled in
├── nats-status.sh    ← currently a no-op; to be filled in
├── agents-up.sh      ← currently a no-op; to be filled in
├── agents-down.sh    ← currently a no-op; to be filled in
└── agents-status.sh  ← currently a no-op; to be filled in
```

### NATS tier

- **Where the compose lives:**
  `~/Projects/appmilla_github/nats-infrastructure/docker-compose.yml`.
- **What `nats-up.sh` should grow into:** `docker compose -f` against the
  above file, with health-gated waits for the cluster nodes
  (`ships-computer-nats` is the local node currently up; the future
  cluster will add more).
- **What `nats-down.sh` should grow into:** the inverse compose-down.
- **What `nats-status.sh` should grow into:** per-node up/down lines,
  ideally probing each node's `http://<node>:8222/healthz` endpoint
  (NATS monitoring port).

### Agents tier

- **What's there today:** specialist-agent containers (none currently
  on this host). Eventually: jarvis itself.
- **What `agents-up.sh` should grow into:** start the per-agent
  containers, in dependency order (jarvis last, after NATS and the
  specialists are reachable).
- **What `agents-status.sh` should grow into:** per-agent
  container-state + healthcheck lines.

### Hook contract

The hooks are **sourced**, not exec'd, so:

1. They must not call `exit` (it would terminate the parent script).
2. They must respect `set -euo pipefail` (no swallowed errors).
3. They should emit one or more clearly-prefixed lines so the orchestrator
   output stays scannable.

When future tasks fill them in, the top-level `infra-*.sh` scripts do
**not** need to change.

---

## 6. The jarvis → graphiti smoke check

After `./scripts/infra-up.sh`, jarvis should be able to reach graphiti.
The minimal HTTP-level confirmation (no jarvis runtime needed) is the
MCP `initialize` POST in §4.2. The same call from the jarvis side, using
its configured env var:

```bash
# In ~/Projects/appmilla_github/jarvis/.env, set:
#   JARVIS_GRAPHITI_ENDPOINT=http://promaxgb10-41b1:8004/mcp
# (without the trailing slash, see §1)

curl -s -o /dev/null -w 'HTTP %{http_code}\n' --max-time 5 \
  -X POST "$JARVIS_GRAPHITI_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2024-11-05",
                 "capabilities":{},
                 "clientInfo":{"name":"smoke-check","version":"0.1"}}}'
# Expected: HTTP 200
```

A 200 here means: TCP reachable, FastMCP listener up, MCP protocol
handshake succeeds, graphiti-core initialized against FalkorDB.

If this call fails:

| Symptom                                | Likely cause                              | Try                                                                  |
|----------------------------------------|-------------------------------------------|----------------------------------------------------------------------|
| `Connection refused`                   | graphiti-mcp not running                  | `./scripts/graphiti-stack-up.sh`                                     |
| `Connection timed out`                 | Tailscale routing or wrong hostname       | `tailscale status`; check `JARVIS_GRAPHITI_ENDPOINT`                 |
| `HTTP 307` (instead of 200)            | trailing slash on `/mcp/`                 | drop the slash in `JARVIS_GRAPHITI_ENDPOINT`                          |
| `HTTP 421 Invalid Host`                | DNS-rebinding protection bypass missing   | `bootstrap.py` not mounted; rebuild via `./scripts/graphiti-mcp-build.sh` and restart |
| `HTTP 5xx` from inside graphiti-mcp    | LLM/embed/Falkor unreachable inside container | `docker logs --tail 100 graphiti-mcp` and follow the chain          |

---

## 7. Index of source files this runbook describes

```
scripts/
├── infra-up.sh                  ← top-level entry (this runbook §2, §3)
├── infra-down.sh                ← top-level teardown
├── infra-status.sh              ← top-level status
├── infra/                       ← extension hooks (this runbook §5)
│   ├── nats-up.sh / down / status      (no-ops today)
│   └── agents-up.sh / down / status    (no-ops today)
├── graphiti-stack-up.sh         ← graphiti tier start
├── graphiti-stack-down.sh       ← graphiti tier stop
├── graphiti-mcp.sh              ← raw container start
├── graphiti-mcp-build.sh        ← one-time image build
├── graphiti-mcp-config.yaml     ← container config (LLM + embed + DB)
├── graphiti-mcp-bootstrap.py    ← MCP DNS-rebind workaround
├── graphiti-endpoint-toggle.sh  ← deprecated; kept as informative stub
├── llama-swap-keepalive.sh      ← out of scope; do not modify
└── llama-swap-healthcheck.sh    ← out of scope; do not modify
```
