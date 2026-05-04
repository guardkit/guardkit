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
| llama-swap (daemon) | GB10, port `:9000`                      | **User-mode systemd**: `~/.config/systemd/user/llama-swap.service` (`Restart=on-failure`). The keepalive/healthcheck timers below revive crashed *workers*, not the daemon. To restart the daemon: `systemctl --user restart llama-swap.service`. |
| llama-swap (worker revival) | GB10                            | `llama-swap-keepalive.timer` (every 5 min) wakes any model worker that crashed since the last poll. **`MODEL_PROBE_KIND` in `llama-swap-keepalive.sh` is hardcoded** — see §9 followup when adding new models. |
| llama-swap (weekly health) | GB10                             | `llama-swap-healthcheck.timer` (weekly), structured logs to `/opt/llama-swap/logs/`. |
| `qwen-graphiti` | model served by llama-swap                  | llama-swap config (`/opt/llama-swap/config/config.yaml`)         |
| `nomic-embed`   | model served by llama-swap (768-dim)        | llama-swap config                                                |
| `qwen36-workhorse` | model served by llama-swap (player/coach for dataset-factory and autobuild) | llama-swap config       |
| `gemma4-tutor`  | model served by llama-swap (study-tutor)    | llama-swap config                                                |
| `architect-agent` | model served by llama-swap (architect domain fine-tune, added 2026-05-03 — see §8 worked example) | llama-swap config |
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
  `qwen-graphiti`, `nomic-embed`, `qwen36-workhorse`, `gemma4-tutor`,
  `architect-agent` (5 models as of 2026-05-03).
- **Recover (workers crashed but daemon up):**
  `systemctl --user start llama-swap-keepalive.service` (one-shot revive).
  The timer also fires every 5 min. Each worker takes ~10-15s to spawn cold;
  the largest can take 3-4 min if it has to mmap from disk.
- **Recover (daemon itself stopped, e.g. config edit, accidental kill):**
  `systemctl --user restart llama-swap.service`. Do NOT `pkill llama-swap`
  followed by `nohup` re-launch — that detaches the daemon from systemd and
  loses `Restart=on-failure`. (Observed 2026-05-03 during the
  architect-agent integration; see §8.)
- **Logs (daemon):**  `journalctl --user -u llama-swap.service --since '1 hour ago'`,
  also appended to `/opt/llama-swap/logs/llama-swap.log`.
- **Logs (keepalive):**  `journalctl -u llama-swap-keepalive.service --since '1 hour ago'`.
- **Touch policy:** `infra-*.sh` never modifies llama-swap by default. With
  `--stop-llama-swap` it stops *only the keepalive timer/service*, not the
  daemon — the script's "may still be running" warning is correct. To fully
  stop the daemon: `systemctl --user stop llama-swap.service` after the
  `--stop-llama-swap`. See §9 followup; this is a known gap.

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
├── llama-swap-keepalive.sh      ← out of scope for routine edits, but the
│                                  hardcoded MODEL_PROBE_KIND list MUST be
│                                  updated when a new model is added (§8)
└── llama-swap-healthcheck.sh    ← out of scope; do not modify
```

External (not in this repo, but coupled to this runbook):
```
~/.config/systemd/user/llama-swap.service   ← user-mode systemd unit, supervises the daemon
/opt/llama-swap/config/config.yaml           ← model definitions, owned by user (not git-tracked)
/opt/llama-swap/config/*.jinja               ← chat templates; reuse the generic gemma4-thinking.jinja
/opt/llama-swap/models/<domain>/             ← GGUF + Modelfile + (optional) system-prompt.txt per served model
```

---

## 8. Adding a fine-tuned model to llama-swap (worked example: `architect-agent`, 2026-05-03)

When a fine-tune in another repo (e.g. `agentic-dataset-factory`) produces a new GGUF and you want to serve it via llama-swap, the integration is six steps. This is the canonical recipe; the dataset-side runbook (e.g. `RUNBOOK-architect-fine-tune.md` Phase 5.3) cross-references this section rather than duplicating it.

**Prerequisites:** the fine-tune has produced a `…Q4_K_M.gguf` and (for Gemma-4) a `Modelfile`. The artefacts live wherever the trainer wrote them — for the architect-agent case that was `~/fine-tuning/output/architect-agent-gemma4-26b-moe/gguf_gguf/`.

### 8.1 Stage the GGUF into `/opt/llama-swap/models/`

The directory `/opt/llama-swap/models/` is owned by your user (no sudo). Create a per-domain subdirectory and copy the artefacts in. Don't symlink — keep a real copy so the source `~/fine-tuning/output/` can be cleaned up independently.

```bash
mkdir -p /opt/llama-swap/models/architect-agent
cp ~/fine-tuning/output/architect-agent-gemma4-26b-moe/gguf_gguf/gemma-4-26b-a4b-it.Q4_K_M.gguf \
   /opt/llama-swap/models/architect-agent/architect-agent.Q4_K_M.gguf
cp ~/fine-tuning/output/architect-agent-gemma4-26b-moe/gguf_gguf/Modelfile \
   /opt/llama-swap/models/architect-agent/Modelfile
```

The rename on the GGUF is optional but tidier when several models share the directory layout. Copy is ~16 GB → ~30s on local NVMe.

### 8.2 Reuse the generic chat template

For Gemma-4 fine-tunes, point at `/opt/llama-swap/config/gemma4-thinking.jinja` (created 2026-05-03 as a renamed copy of `gemma4-tutor.jinja`; the file is byte-identical and contains no tutor-specific persona text). Don't make a per-domain copy unless you genuinely need to override the template.

```bash
ls -la /opt/llama-swap/config/*.jinja
# Confirm gemma4-thinking.jinja exists; if not, copy from gemma4-tutor.jinja:
# cp /opt/llama-swap/config/gemma4-tutor.jinja /opt/llama-swap/config/gemma4-thinking.jinja
```

### 8.3 Add a model block to `/opt/llama-swap/config/config.yaml`

Pattern: copy the gemma4-tutor block as a starting point, then change the GGUF path, alias, chat template, and (often) `--temp` for domain-appropriate determinism.

```yaml
  "architect-agent":
    cmd: >
      /home/richardwoollcott/llama.cpp/build/bin/llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/architect-agent/architect-agent.Q4_K_M.gguf
      --alias architect-agent
      --ctx-size 32768
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      --chat-template-file /opt/llama-swap/config/gemma4-thinking.jinja
      --temp 0.4
      --top-p 0.9
      -np 1
    checkEndpoint: /health
    ttl: 0
    concurrencyLimit: 2
    aliases:
      - "software-architect"
      - "ddd-architect"
```

Also update the `matrix.vars` and `matrix.sets[all]` lists to include the new model, and add it to `hooks.on_startup.preload`. The matrix update tells the eviction solver "all N models can run concurrently" — it informs whether llama-swap will keep them all hot vs evict one. Skip the matrix update if you'd rather have on-demand-only behaviour, but be aware preload won't load it then.

**Memory-budget update:** each new ~26B Q4_K_M model adds ~17 GB of GPU. Update the file's header comment to record the new total. As of 2026-05-03 with `architect-agent` added the budget is ~82 GB / 121 GB unified.

### 8.4 Update `MODEL_PROBE_KIND` in `llama-swap-keepalive.sh`

**This is mandatory** — the keepalive script revives crashed workers using a per-model probe (chat or embed). New models need a new array entry. The current state (as of 2026-05-03) is the keepalive script has 4 models hardcoded; adding `architect-agent` to it is on the followups list (§9). Until that's done, **the architect-agent worker will not get auto-revived if it crashes overnight** — it will simply be missing on next request, leading to the same "request silently routed elsewhere" problem we hit during the integration.

```bash
# In ~/Projects/appmilla_github/guardkit/scripts/llama-swap-keepalive.sh:
declare -A MODEL_PROBE_KIND=(
    [qwen-graphiti]=chat
    [nomic-embed]=embed
    [qwen36-workhorse]=chat
    [gemma4-tutor]=chat
    [architect-agent]=chat   # ← add this line for any new chat model
)
```

### 8.5 Restart the daemon (canonical, via systemd)

```bash
systemctl --user restart llama-swap.service
sleep 5
journalctl --user -u llama-swap.service --since '30 sec ago' --no-pager | tail -20
```

**Critical:** do not `pkill llama-swap` followed by `nohup`. That detaches the daemon from the systemd unit and you lose `Restart=on-failure`. If you have already done that (say, during a debugging session), recover with:

```bash
pkill -f "^/usr/local/bin/llama-swap "      # stop the un-supervised process
systemctl --user start llama-swap.service   # start it under systemd again
```

### 8.6 Verify

```bash
# Confirm the model is registered
curl -s http://localhost:9000/v1/models | python3 -m json.tool | grep -E '"id"'

# Trigger a worker spawn and verify it routes correctly
curl -s --max-time 180 http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"architect-agent","messages":[{"role":"user","content":"smoke"}],
       "max_completion_tokens":50,"temperature":0.4}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print('model in response:', r['model'])"

# Verify the worker process is running with the right GGUF
ps -ef | grep "architect-agent.Q4_K_M" | grep -v grep
```

**Healthy signs:**
- `architect-agent` (and any aliases) appear in `/v1/models`
- The chat-completions response field `model` matches the requested model — **NOT** a fallback like `gemma4-tutor`. A fallback name signals the new worker did not spawn and the request silently routed elsewhere; daemon-restart almost certainly didn't happen.
- A `llama-server` process is running with the new GGUF path

---

## 9. Followups (open gaps in the orchestration model)

| # | Followup | Severity | Where it bites |
|---|---|---|---|
| 1 | **`infra-down.sh --stop-llama-swap` does not stop the daemon.** It stops only the keepalive timer + service (`llama-swap-keepalive.{timer,service}`). The daemon itself is supervised by the user-mode systemd unit `~/.config/systemd/user/llama-swap.service`. The script's "may still be running, find and kill manually" message is correct but easy to misread as "this command did its job." Fix: extend `infra-down.sh --stop-llama-swap` to also run `systemctl --user stop llama-swap.service` (and `infra-up.sh` to `systemctl --user start` symmetrically). | Medium — caused real confusion 2026-05-03; users assume it works and don't notice the daemon hasn't reloaded its config. |
| 2 | **`MODEL_PROBE_KIND` in `llama-swap-keepalive.sh` is hardcoded.** Currently lists 4 models. `architect-agent` (added 2026-05-03) is missing — if its worker crashes overnight, it won't be revived. Either: (a) add `[architect-agent]=chat` to the array, or (b) refactor the script to derive the list from `/opt/llama-swap/config/config.yaml` (yq the `models:` keys; map `--embedding`-flagged ones to `embed`, rest to `chat`). | High for any new model — silent operational drift. |
| 3 | **`/opt/llama-swap/config/` is not version-controlled.** Lives at `/opt/`, owned by user, no git repo. Edits to `config.yaml` and the `*.jinja` files are durable but unauditable; rollback relies on hand-named `.bak-*` files (see `config.yaml.bak-pre-arch-bump-20260501-163546` for a precedent). Either: (a) move the canonical copy into `guardkit/config/llama-swap/` with `infra-up.sh` syncing it to `/opt/`, or (b) symlink `/opt/llama-swap/config/` to a tracked dir. Option (a) plays nicer with multi-host deployments. | Low — works fine in single-host steady state, hurts you when something is mis-edited overnight and you want `git log` to tell you what changed. |
| 4 | **User-mode systemd unit may not survive a logout.** `loginctl enable-linger richardwoollcott` is the usual fix to keep user services running across logouts; verify whether it's already set on the GB10 (`loginctl show-user richardwoollcott | grep Linger`). If not enabled, the daemon dies when the user logs out and only revives on next login (and only if something explicitly starts it). System-mode systemd would sidestep this entirely; that's a bigger refactor. | Medium — symptom is "daemon was running yesterday, I logged out, today it's dead and `infra-up` reports OK because keepalive briefly woke it up but it died again right after." |

These four are not blocking the current architect-agent serve — that's working — but they're real gaps that the next infra task should pick up. The dataset-factory side has its own follow-up (chat template / `<think>` tag interaction); that's documented in [`agentic-dataset-factory/domains/architect-agent/FOLLOWUP-chat-template-thinking-tags.md`](../../../agentic-dataset-factory/domains/architect-agent/FOLLOWUP-chat-template-thinking-tags.md).

---

*Last updated: 2026-05-03 — added §1 user-mode systemd row, §4.1 daemon-vs-keepalive distinction, §8 worked example, §9 followups.*
