# Graphiti on GB10 — Deployment & Operations Runbook

This guide describes the **HTTP-centralised** Graphiti MCP deployment used across
all GuardKit-related repos on `rich@appmilla.com`'s workstation. Everything runs
as Docker containers on the DGX Spark GB10 (`promaxgb10-41b1`). Every client
(Claude Code on Mac, Claude Code on GB10, Claude Desktop) reaches the same HTTP
MCP endpoint — there is no per-client graphiti install, no per-repo stdio
subprocess, and no hard-coded file paths in `.mcp.json`.

**Supersedes**: [graphiti-gemini-rollout-setup.md](graphiti-gemini-rollout-setup.md)
(retained for history). Gemini is no longer the LLM — the local vLLM on GB10 is.

---

## Topology

```
┌─────────────────────────┐    ┌──────────────────────────────┐
│  MacBook                │    │  Claude Desktop (Mac)        │
│  Claude Code  .mcp.json │    │  claude_desktop_config.json  │
│  → http://promaxgb10…   │    │  → npx mcp-remote → http…    │
└───────────┬─────────────┘    └───────────┬──────────────────┘
            │                              │
            │   Tailscale (HTTPS MCP on port 8004)
            │                              │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│  GB10  (promaxgb10-41b1)                                    │
│                                                             │
│   ┌──────────────────┐  ┌──────────────────┐                │
│   │ vllm-graphiti    │  │ vllm-embedding   │                │
│   │   :8000 (LLM)    │  │   :8001 (embed)  │                │
│   │   Qwen2.5-14B FP8│  │   nomic-embed    │                │
│   └────────┬─────────┘  └────────┬─────────┘                │
│            │                     │                          │
│            │   localhost (--network host)                   │
│            │                     │                          │
│   ┌────────▼─────────────────────▼──────────────┐           │
│   │ graphiti-mcp :8004  (HTTP MCP server)       │           │
│   │   standalone image, mounts guardkit config  │           │
│   └────────────────────┬────────────────────────┘           │
│                        │                                    │
└────────────────────────┼────────────────────────────────────┘
                         │  Tailscale
                         ▼
            ┌──────────────────────────┐
            │  whitestocks (Synology)  │
            │  FalkorDB  :6379         │
            └──────────────────────────┘
```

Same GPU hosts both vLLM services plus the MCP container. FalkorDB lives on the
Synology NAS (`whitestocks`) reached over Tailscale.

---

## File map

| Path | Role |
|------|------|
| `guardkit/scripts/graphiti-mcp-config.yaml` | **Single source of truth** for LLM, embedder, FalkorDB, group IDs, entity types. Mounted read-only into the MCP container. |
| `guardkit/scripts/graphiti-mcp-build.sh` | One-time: clones `getzep/graphiti` read-only and builds `graphiti-mcp-standalone:local` from `Dockerfile.standalone`. |
| `guardkit/scripts/graphiti-mcp.sh` | Starts the MCP container (`--network host`, port 8004), mounts the config above and the bootstrap below. |
| `guardkit/scripts/graphiti-mcp-bootstrap.py` | Mounted into the container at `/app/mcp/bootstrap.py` and used as the entrypoint. Monkey-patches MCP's DNS rebinding protection off before importing graphiti's main. See [Known upstream quirks](#known-upstream-quirks). |
| `guardkit/scripts/vllm-graphiti.sh` | Starts the Qwen2.5-14B LLM container on port 8000. |
| `guardkit/scripts/vllm-embed.sh` | Starts the nomic-embed container on port 8001. |
| `guardkit/scripts/graphiti-stack-up.sh` | Daily start: boots all three in order with health-gated waits. |
| `guardkit/scripts/graphiti-stack-down.sh` | Daily stop: shuts all three down in reverse order. |
| `~/Projects/appmilla_github/graphiti/` | Upstream graphiti repo checkout — **read-only**, used only as Docker build context. Never edited. |
| `<repo>/.mcp.json` (×15) | Claude Code MCP config per repo. All now point at `http://promaxgb10-41b1:8004/mcp`. |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop config. Uses `mcp-remote` to bridge stdio → HTTP. |

### Repos whose `.mcp.json` point at the stack

```
guardkit                                   specialist-agent
jarvis (+ FEAT-J002 worktree)              dotnet-functional-fastendpoints-exemplar
study-tutor                                lpa-platform
youtube-transcript-mcp                     nats-core
deepagents-player-coach-exemplar           nats-infrastructure
require-kit                                forge
agentic-dataset-factory                    architect-agent_delete_me
```

`study-tutor` and `specialist-agent` also declare a second MCP server alongside
`graphiti` — those entries are preserved untouched.

---

## Config relationships

There is exactly **one** Graphiti config that matters at runtime:
`guardkit/scripts/graphiti-mcp-config.yaml`. Everything else references it.

```
graphiti-mcp-config.yaml     ◄── LLM URL, embedder URL, FalkorDB URI, group IDs
        │                        live here. Edit here to change behaviour.
        │  mounted at /app/mcp/config/config.yaml
        ▼
graphiti-mcp container  ─────────►  http://0.0.0.0:8004/mcp
        ▲
        │  every client points here
        │
        ├── Claude Code   .mcp.json     type:"http" url:"…:8004/mcp"
        └── Claude Desktop              npx mcp-remote …:8004/mcp
```

Key env-overridable fields inside the YAML (all have sensible defaults so the
file is valid as-is):

| Field | Default | Override via |
|-------|---------|-------------|
| `llm.model` | `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` | `LLM_MODEL` env |
| `llm.providers.openai.api_url` | `http://localhost:8000/v1` | `LLM_API_URL` env |
| `embedder.providers.openai.api_url` | `http://localhost:8001/v1` | `EMBEDDING_API_URL` env |
| `database.providers.falkordb.uri` | `redis://whitestocks:6379` | `FALKORDB_URI` env |
| `server.port` | `8004` | set in YAML (must match `docker run` port) |

`localhost` inside the container works because `graphiti-mcp.sh` uses
`--network host` — the MCP container shares the GB10's network namespace, so
`localhost:8000` resolves to the vLLM LLM container on the same host.

---

## One-time GB10 setup

Prerequisites on the GB10:
- Docker with NVIDIA runtime (already in use by `vllm-*` scripts)
- Tailscale up (so `whitestocks` resolves and other machines can reach GB10)
- The `guardkit` repo cloned at `~/Projects/appmilla_github/guardkit` (matches the paths used by the existing `vllm-*.sh` scripts)

Then, once:

```bash
cd ~/Projects/appmilla_github/guardkit

# Clones getzep/graphiti (read-only) and builds graphiti-mcp-standalone:local.
# ~5 minutes. Re-run with --pull to update graphiti, --no-cache to force rebuild.
./scripts/graphiti-mcp-build.sh
```

This is the only step that writes to the `graphiti/` checkout — and it only
clones; it never modifies anything inside.

---

## Daily startup

```bash
cd ~/Projects/appmilla_github/guardkit
./scripts/graphiti-stack-up.sh
```

What happens, in order:

1. `vllm-graphiti.sh` → LLM container on :8000. Script waits for
   `http://localhost:8000/health` (up to 300s — model load dominates).
2. `vllm-embed.sh` → embedder on :8001. Waits for `/health` (up to 120s).
3. `graphiti-mcp.sh` → MCP HTTP server on :8004. Waits for `/mcp/` (trailing
   slash) to respond within 60s — a 3xx/4xx is treated as "up" because FastMCP
   redirects the slash form to `/mcp` (no slash) and also requires an MCP
   session for the canonical endpoint. Clients should use `/mcp` directly;
   see the trailing-slash note in [Known upstream quirks](#known-upstream-quirks).

Final output gives URLs for sanity-checking:

```
LLM:    http://promaxgb10-41b1:8000/v1
Embed:  http://promaxgb10-41b1:8001/v1
MCP:    http://promaxgb10-41b1:8004/mcp
```

Skip flags (when rebooting after a GB10 OS update you may only need parts):

```bash
SKIP_LLM=1   ./scripts/graphiti-stack-up.sh   # LLM already running
SKIP_EMBED=1 ./scripts/graphiti-stack-up.sh
SKIP_MCP=1   ./scripts/graphiti-stack-up.sh   # start just the vLLM pair
```

After the stack is up, **restart Claude Code / Claude Desktop** on any machine
that had a stale MCP connection.

---

## Daily shutdown

```bash
./scripts/graphiti-stack-down.sh
```

Stops in reverse order — MCP first (so clients see it disappear cleanly),
then embed, then LLM. Each container is `docker stop`ped and `docker rm`oved,
so next start-up is a clean slate.

Partial shutdown (e.g. freeing the GPU for a different job while keeping the
knowledge graph query path available — note that queries do not need the LLM,
only ingestion does):

```bash
./scripts/graphiti-stack-down.sh --keep-embed --keep-llm  # stop only MCP
./scripts/graphiti-stack-down.sh --keep-embed             # stop MCP + LLM
```

---

## Training-mode switchover (freeing the GB10 LLM GPU)

When the GB10 needs to host fine-tuning or training-data generation, you can
stop running the Graphiti LLM locally and route just the LLM calls to a
different backend. The MCP container, embedder, FalkorDB, and every
`.mcp.json` / Claude Desktop entry stay exactly as they are — clients keep
hitting `http://promaxgb10-41b1:8004/mcp` throughout. Only the outbound
hop from the MCP container changes.

### Why this works (and its one caveat)

Graphiti only calls the LLM during **ingestion** (seeding, capture, turn-state
writes). **Queries** — which happen constantly during Claude Code sessions —
go directly to the embedder and FalkorDB and never touch the LLM. So the only
thing affected by routing the LLM elsewhere is the latency and reliability of
`add_memory` calls.

**Caveat — JSON schema enforcement.** The local vLLM setup uses
`--structured-outputs-config.backend xgrammar`, which enforces Graphiti's
`response_format=json_schema` at the token level. Ollama does not — it prompts
the model and hopes. Expect occasional JSON parse failures on ingestion when
using `--llm=mac`; Graphiti retries, so short bursts are fine, but don't run
large seeding jobs against Ollama. If you need reliable ingestion during a
long fine-tune, use `--llm=custom` with a paid API (Gemini / Anthropic)
instead.

### Switch to MacBook Ollama

Prerequisites: Ollama running on the MacBook, serving a ~14B instruct model.
The defaults assume `http://richards-macbook-pro.tailebf801.ts.net:8000/v1`
and `qwen2.5:14b-instruct` — override via `MAC_LLM_API_URL` /
`MAC_LLM_MODEL` if yours differ.

```bash
# On GB10: stop everything cleanly, then bring the stack back up in mac-LLM mode
./scripts/graphiti-stack-down.sh
./scripts/graphiti-stack-up.sh --llm=mac
```

`--llm=mac` implies `SKIP_LLM=1` — the `vllm-graphiti` container is not
started, freeing the GPU slice it would have claimed. The MCP container
starts with `LLM_API_URL` / `LLM_MODEL` env vars that override the YAML
defaults.

### Switch to a paid API (Gemini / Anthropic / OpenAI)

Use `--llm=custom` when you need reliable JSON-mode ingestion during a long
training window, or if the MacBook is off/unreachable:

```bash
# Gemini example (was the pre-2026-04-24 setup)
GRAPHITI_LLM_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/ \
GRAPHITI_LLM_MODEL=gemini-2.5-pro \
OPENAI_API_KEY=$GOOGLE_API_KEY \
./scripts/graphiti-stack-up.sh --llm=custom
```

Any OpenAI-compatible endpoint works — Anthropic's OpenAI-compat shim,
OpenAI itself, Groq, etc. `--llm=custom` also skips `vllm-graphiti`.

### Switch back to full GB10

```bash
./scripts/graphiti-stack-down.sh
./scripts/graphiti-stack-up.sh       # default == --llm=gb10
```

### Partial switch (MCP container already running)

If the stack is up and you just want to re-point the LLM without touching
the embedder:

```bash
LLM_API_URL=http://richards-macbook-pro.tailebf801.ts.net:8000/v1 \
LLM_MODEL=qwen2.5:14b-instruct \
./scripts/graphiti-mcp.sh            # restarts just the MCP container

# (optionally free the GPU)
docker stop vllm-graphiti && docker rm vllm-graphiti
```

The old `graphiti-endpoint-toggle.sh` (shell-env-based toggling) no longer
applies — env has to reach the container, not the shell. The script is
retained as a deprecation stub that prints the replacement commands.

---

## Updating the config

Change `guardkit/scripts/graphiti-mcp-config.yaml`, then:

```bash
./scripts/graphiti-mcp.sh    # restarts the MCP container with the new mount
```

No rebuild needed — the config is a bind mount, so edits take effect on
container restart. The vLLM containers do not read this file and don't need
restarting unless you change their own scripts.

---

## Updating graphiti itself (rare)

```bash
./scripts/graphiti-mcp-build.sh --pull      # git pull + docker build
./scripts/graphiti-mcp.sh                   # restart with new image
```

Only do this when you actually want to track upstream graphiti changes.
`graphiti-core` is pinned inside the Dockerfile (currently `0.28.1`) — the
upstream repo is only used for `main.py` and server code.

---

## Migration: propagating the 2026-04-24 fix to clients

One-time sweep after pulling the guardkit changes that fixed
[Known upstream quirks #2](#known-upstream-quirks) (trailing-slash MCP URL).
The server-side monkey-patch for quirk #1 is already live as soon as the
GB10 stack is restarted; these commands are only about rewriting client
configs so they stop hitting the 307 redirect.

All commands are idempotent — running them twice is safe.

### On the Mac

**1. Sweep the sibling repos' `.mcp.json` files:**

```bash
cd ~/Projects/appmilla_github
for d in jarvis study-tutor youtube-transcript-mcp deepagents-player-coach-exemplar \
         require-kit agentic-dataset-factory specialist-agent \
         dotnet-functional-fastendpoints-exemplar lpa-platform \
         nats-core nats-infrastructure forge architect-agent_delete_me; do
  [ -f "$d/.mcp.json" ] && sed -i '' 's#:8004/mcp/#:8004/mcp#' "$d/.mcp.json" \
    && echo "fixed $d"
done
```

`guardkit` is already fixed in this commit; skip it in the list to keep the
output clean. Repos you haven't cloned locally are skipped automatically.

**2. Update Claude Desktop:**

```bash
sed -i '' 's#:8004/mcp/#:8004/mcp#' \
  "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

**3. Ensure `--allow-http` is present in the Claude Desktop config:**

As of 2026-04-27, `mcp-remote` enforces HTTPS for non-localhost URLs.
The args array must include `"--allow-http"` after the URL. If missing,
the bridge process exits silently and Claude Desktop shows no Graphiti
server at all. Check with:

```bash
grep -A5 'mcp-remote' "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

Restart Claude Desktop after any config change — it reads the config at launch.

**4. Restart any running Claude Code sessions** on the Mac so they re-read
`.mcp.json` for each repo.

### On the GB10

The `guardkit` repo on the GB10 is already fixed. If you later clone any of
the other sibling repos to the GB10 and their `.mcp.json` still has the
trailing slash (e.g. the Mac sweep ran first and hasn't been pulled yet),
the Linux-sed form is:

```bash
sed -i 's#:8004/mcp/#:8004/mcp#' <repo>/.mcp.json
```

(Linux GNU sed takes no argument after `-i`; macOS BSD sed requires `''`.)

### Verification

From each client machine after restart, inside Claude Code:

```
/mcp
```

Expect `graphiti: connected`. If you see `graphiti: failed` or the server
missing from the list, see [Troubleshooting](#troubleshooting) — most likely
a stale config that didn't get rewritten.

---

## Client configuration summary

### Claude Code `.mcp.json` (every repo)

```json
{
  "mcpServers": {
    "graphiti": {
      "type": "http",
      "url": "http://promaxgb10-41b1:8004/mcp"
    }
  }
}
```

That's the whole file. No `.env` sourcing, no hard-coded `uv` path, no
per-machine paths. Works identically on Mac and GB10.

### Claude Desktop `claude_desktop_config.json`

Claude Desktop is stdio-only, so it uses `mcp-remote` (from npm) as a local
stdio↔HTTP proxy:

```json
"graphiti": {
  "command": "/opt/homebrew/bin/npx",
  "args": ["-y", "mcp-remote", "http://promaxgb10-41b1:8004/mcp", "--allow-http"]
}
```

Absolute path to `npx` because Claude Desktop launches subprocesses with a
minimal PATH and won't find `nvm`-managed Node.

`--allow-http` is required because `mcp-remote` enforces HTTPS for
non-localhost URLs by default. Without it the process exits silently with
`Error: Non-HTTPS URLs are only allowed for localhost or when --allow-http
flag is provided` — Claude Desktop shows no error, the server just never
appears. This is safe here because the connection runs over Tailscale
(encrypted WireGuard tunnel).

---

## Troubleshooting

### Claude Code reports "Graphiti MCP is not configured"

1. Is the container up on the GB10?
   ```bash
   docker ps --filter name=graphiti-mcp
   ```
2. Can you reach the endpoint from the client machine?
   ```bash
   curl -v http://promaxgb10-41b1:8004/mcp
   ```
   Expect a 4xx (FastMCP wants a session) — that's fine; a connection error is
   not.
3. Tailscale up on both ends?
   ```bash
   tailscale status | grep promaxgb10
   ```
4. Restart Claude Code — `.mcp.json` is read at launch.

### MCP container crashes on startup

```bash
docker logs graphiti-mcp
```

Most common causes:
- `Failed to connect to FalkorDB` — check `whitestocks:6379` is reachable
  from the GB10: `redis-cli -h whitestocks ping` (install redis-tools if
  needed) or check Tailscale.
- `Failed to connect to LLM` — vLLM container for port 8000 isn't ready yet.
  Start-up script should handle this via health gates, but a very slow
  first-run download can push past 300s. Re-run `graphiti-stack-up.sh` once
  the LLM is ready; it's idempotent.
- `YAML parse error` — you edited `graphiti-mcp-config.yaml` and broke it.

### Embedder dimension mismatch

If you see errors like `dimension mismatch: expected 1024, got 768`, something
changed the embedder model and the FalkorDB vector index now disagrees. The
`vllm-embed.sh` script prints a post-start verification curl — run it and
confirm dimension matches `embedder.dimensions` in
`graphiti-mcp-config.yaml`.

### Container up, but client gets "MCP server not connected" / curl gets 421

The server is binding to 0.0.0.0 correctly, but MCP's DNS rebinding protection
rejects the Host header. This is the upstream bug described in
[Known upstream quirks](#known-upstream-quirks). Two things to check:

1. The container is running `bootstrap.py`, not `main.py`:
   ```bash
   docker inspect graphiti-mcp --format '{{.Config.Cmd}}'
   # expect: [uv run --no-sync bootstrap.py]
   ```
2. The bootstrap file exists and is mounted:
   ```bash
   docker exec graphiti-mcp cat /app/mcp/bootstrap.py | head -5
   ```

If either is missing, `graphiti-mcp.sh` didn't find `graphiti-mcp-bootstrap.py`
next to it. Re-pull guardkit.

If the container is correct but the 421 persists, upstream may have renamed
`TransportSecurityMiddleware._validate_host`. See the "When this might break
silently" note in the Known upstream quirks section.

### Claude Desktop shows no Graphiti server (no logs at all)

If the Claude Desktop MCP logs show other servers connecting but zero
Graphiti log lines, the `mcp-remote` bridge is crashing before it reaches
the MCP handshake. The most common cause (as of 2026-04-27) is a missing
`--allow-http` flag — `mcp-remote` now enforces HTTPS for non-localhost
URLs. Add `"--allow-http"` to the args array in
`claude_desktop_config.json`. See the
[Claude Desktop config](#claude-desktop-claude_desktop_configjson) section
for the correct format.

To confirm, run `mcp-remote` manually:

```bash
/opt/homebrew/bin/npx -y mcp-remote http://promaxgb10-41b1:8004/mcp
```

If it prints `Non-HTTPS URLs are only allowed for localhost`, that's the
problem.

### Client uses `/mcp/` and silently fails

See [Known upstream quirks #2](#known-upstream-quirks). The trailing slash
triggers a 307 redirect Claude Code's HTTP MCP transport doesn't follow.
Drop the slash in every `.mcp.json` and the Claude Desktop config.

### Port 8004 in use

Change `GRAPHITI_MCP_PORT` on the GB10 script call **and**
`server.port` in `graphiti-mcp-config.yaml` **and** the URL in every
`.mcp.json` / `claude_desktop_config.json`. Easier to just find the process
hogging 8004 and stop it.

---

## Why this layout

Four design calls are worth knowing, because each resolves a real past
problem:

1. **HTTP transport, not stdio.** Stdio requires graphiti installed on every
   client machine and bakes Mac-specific paths into each `.mcp.json`. Moving
   to HTTP on the GB10 means one install, one config, and `.mcp.json` files
   that are identical and machine-agnostic.
2. **Config lives in `guardkit/scripts/`, not inside the graphiti repo.**
   The graphiti checkout is vendored source — we clone it, we don't own it,
   and we never edit files inside. All GuardKit-specific settings live in
   `guardkit`, which is where you expect them.
3. **Standalone image + `--network host`.** The official combined image
   bundles FalkorDB, which we don't want (FalkorDB lives on `whitestocks`).
   The standalone image connects to external FalkorDB. Host networking
   lets the MCP container talk to vLLM via `localhost` without exposing a
   Docker bridge DNS layer.
4. **Local vLLM for the LLM.** Graphiti only calls the LLM during ingestion
   (seeding, capture, turn-state writes), not during queries. Moving back
   from Gemini to local vLLM eliminates per-call cost and keeps the
   workload on hardware we already run.

---

## Known upstream quirks

Two issues in the upstream graphiti-mcp-server / MCP SDK stack caused real
diagnostic round-trips (2026-04-24). They're documented here because the
workarounds look arbitrary in isolation, but each has a specific cause.

### 1. DNS rebinding protection locks the MCP to localhost-only

**Symptom.** `curl http://promaxgb10-41b1:8004/mcp` returns
`421 Invalid Host header`. Localhost (`http://localhost:8004/mcp`,
`http://127.0.0.1:8004/mcp`) works fine. A remote Claude Code session (Mac)
reports *"no Graphiti MCP server is currently connected"* with no logs on
either end pointing at a cause.

**Cause.** In `graphiti_mcp_server.py` the `FastMCP(...)` constructor is called
*without* a `host=` argument, so it defaults to `"127.0.0.1"`. The MCP SDK's
FastMCP class has a dedicated branch (`mcp/server/fastmcp/server.py`, circa
line 178) that — when it sees a localhost default — auto-enables DNS
rebinding protection and builds a `TransportSecuritySettings` object with
`allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]`. Graphiti later
mutates `mcp.settings.host = "0.0.0.0"` at line 900 to make uvicorn bind all
interfaces — but the `transport_security` object is already frozen. Uvicorn
accepts the connection, the MCP middleware rejects the Host header. This is
an upstream bug in graphiti-mcp-server; `--host` / env vars cannot fix it
because the settings object is built before they apply.

**Workaround.** `graphiti-mcp-bootstrap.py` monkey-patches
`TransportSecurityMiddleware._validate_host` / `_validate_origin` to return
True, and is used as the container entrypoint by `graphiti-mcp.sh`. The
deployment is Tailscale-only (not on the public internet) and the rebinding
threat model — a browser tricked into issuing same-origin requests at a
localhost-bound MCP — doesn't apply. If the upstream bug is ever fixed,
the monkey-patch becomes a no-op and can be removed.

**When this might break silently.** If a `graphiti-mcp-build.sh --pull`
brings in an upstream rename of `TransportSecurityMiddleware` or its methods,
the monkey-patch will stop applying. Symptom: the 421 returns. Check
`grep -rn "_validate_host" /app/mcp/.venv/lib/python3.11/site-packages/mcp/`
inside the container to see what the method is called now, and update
`graphiti-mcp-bootstrap.py` to match.

### 2. MCP endpoint URL must NOT have a trailing slash

**Symptom.** Client configs that use `http://promaxgb10-41b1:8004/mcp/`
silently fail to connect, with no error on either end. The same endpoint
reached without the trailing slash (`/mcp`) works.

**Cause.** FastMCP's streamable HTTP transport serves the MCP endpoint at
`/mcp` and 307-redirects `/mcp/` to `/mcp`. It also rewrites the Location
header host to its internally-recorded host (`localhost`) rather than the
inbound Host — so even clients that do follow 307-on-POST would be pointed
at `http://localhost:8004/mcp`, which is the client's own loopback from any
remote machine. Claude Code's HTTP MCP transport does not follow 307 on
POST (standard safety behaviour; the RFC makes POST-preserving redirects
optional and many clients refuse them).

**Workaround.** All `.mcp.json` and Claude Desktop configs must point at
`/mcp` with no trailing slash. The health check in `graphiti-stack-up.sh`
still probes `/mcp/` because a 307 proves the server is listening —
"ready" in that script means "reachable", not "correctly addressed".

**Don't forget.** Every `.mcp.json` across the 15 listed repos and
`claude_desktop_config.json` on the Mac need the trailing slash dropped. See
[Migration: propagating the 2026-04-24 fix to clients](#migration-propagating-the-2026-04-24-fix-to-clients)
below for copy-paste commands.
