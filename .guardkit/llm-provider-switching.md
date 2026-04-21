# Graphiti LLM Provider Switching

Reference doc for toggling the Graphiti LLM provider between **GB10
local vLLM** (free, but unavailable when the GPU is fine-tuning) and
**Google Gemini 2.5 Pro** (cloud, paid, runs anytime).

> **Cost trigger (2026-04-20):** Gemini 2.5 Pro accumulated **£29 over
> 3 days** of normal Graphiti ingestion. Default is being reverted to
> GB10 to stop the bleed. Switch to Gemini only while GB10 is busy
> with training jobs.

Embedding provider stays on **GB10 vLLM** (`nomic-embed-text-v1.5`,
port 8001) for both modes — only the LLM endpoint moves.

---

## Repos in scope

The 13 repos below currently have `.guardkit/graphiti.yaml` set to
Gemini and need to be reverted to GB10 to stop the cost.

| # | Repo | Current provider | Path |
|---|------|------------------|------|
| 1 | `agentic-dataset-factory` | gemini | `.guardkit/graphiti.yaml` |
| 2 | `deepagents-player-coach-exemplar` | gemini | `.guardkit/graphiti.yaml` |
| 3 | `dotnet-functional-fastendpoints-exemplar` | gemini | `.guardkit/graphiti.yaml` |
| 4 | `forge` | gemini | `.guardkit/graphiti.yaml` |
| 5 | `guardkit` | gemini | `.guardkit/graphiti.yaml` |
| 6 | `jarvis` | gemini | `.guardkit/graphiti.yaml` |
| 7 | `lpa-platform` | gemini | `.guardkit/graphiti.yaml` |
| 8 | `nats-core` | gemini | `.guardkit/graphiti.yaml` |
| 9 | `nats-infrastructure` | gemini | `.guardkit/graphiti.yaml` |
| 10 | `require-kit` | gemini | `.guardkit/graphiti.yaml` |
| 11 | `specialist-agent` | gemini | `.guardkit/graphiti.yaml` |
| 12 | `study-tutor` | gemini | `.guardkit/graphiti.yaml` |
| 13 | `youtube-transcript-mcp` | gemini | `.guardkit/graphiti.yaml` |

### Already on GB10 (no action needed)

- `architect-agent_delete_me`
- `deepagents-player-coach-exemplar-original`
- `vllm-profiling`

### Repos without a `.guardkit/graphiti.yaml` (skip)

All other appmilla_github checkouts — they don't use GuardKit/Graphiti
and have no config to toggle.

---

## Reference configs (paste-ready)

The block below replaces the `llm_provider` / `llm_model` /
`llm_base_url` group inside each repo's
`.guardkit/graphiti.yaml`. Everything else (FalkorDB host, project
ID, embedding settings, group IDs) is unchanged.

### Config A — GB10 local vLLM (default, free)

```yaml
# LLM provider for Graphiti entity extraction
# Options: openai (default), vllm, ollama, gemini
#
# GB10 local vLLM (FP8) — default. Free, but unavailable while the
# GPU is busy with fine-tuning. Switch to Gemini (Config B) for
# durations when GB10 is training; revert here when training stops.
# See: .guardkit/llm-provider-switching.md (this repo)
#
# --- GB10 (vLLM, FP8) — ACTIVE ---
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
#
# --- Fallback: Google Gemini (cloud, paid) — uncomment to switch ---
# Cost: ~£10/day under typical Graphiti ingestion (2026-04-20 measurement)
# Requires GOOGLE_API_KEY env var and `pip install guardkit-py[gemini]`.
#llm_provider: gemini
#llm_model: gemini-2.5-pro
#
# --- Fallback: MacBook Pro M2 Max (Ollama, Q4_K_M) ---
#llm_provider: ollama
#llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
#llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096  # Cap output tokens (TASK-REV-84A7)
```

### Config C — MacBook Pro M2 Max (Ollama, Q4_K_M)

Used historically when GB10 was offline entirely (machine down, not
just GPU-busy). Slower than GB10 but free; runs over Tailscale.
Requires Ollama serving `qwen2.5:14b-instruct-q4_K_M` on the MacBook.

```yaml
# --- MacBook Pro M2 Max (Ollama, Q4_K_M) — ACTIVE ---
llm_provider: ollama
llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M
#
# --- Default: GB10 (vLLM, FP8) — uncomment to revert ---
#llm_provider: vllm
#llm_base_url: http://promaxgb10-41b1:8000/v1
#llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
#
# --- Fallback: Google Gemini (cloud, paid) — uncomment if both local LLMs offline ---
#llm_provider: gemini
#llm_model: gemini-2.5-pro
llm_max_tokens: 4096  # Cap output tokens (TASK-REV-84A7)
```

**Pre-req before switching:** confirm Ollama is reachable on the
MacBook over Tailscale:
```bash
curl -s http://richards-macbook-pro.tailebf801.ts.net:8000/v1/models \
  | python3 -m json.tool | head -10
```

### Config B — Google Gemini 2.5 Pro (cloud, paid)

Use only when GB10 is unavailable (training jobs running). Revert to
Config A as soon as GB10 frees up.

```yaml
# LLM provider for Graphiti entity extraction
# Options: openai (default), vllm, ollama, gemini
#
# Gemini 2.5 Pro (paid tier) — TEMPORARY while GB10 is fine-tuning.
# Graphiti only calls the LLM during ingestion/seeding, not queries.
# Requires GOOGLE_API_KEY env var and `pip install guardkit-py[gemini]`.
# Paid tier chosen after free-tier 429s during seeding (Wave 2 smoke
# test, 2026-04-17). See: docs/guides/graphiti-gemini-rollout-setup.md
# Cost: ~£10/day under typical ingestion. Revert to GB10 (Config A)
# the moment training finishes.
#
# --- Google Gemini (cloud) — ACTIVE ---
llm_provider: gemini
llm_model: gemini-2.5-pro
#
# --- Default: GB10 (vLLM, FP8) — uncomment to revert ---
#llm_provider: vllm
#llm_base_url: http://promaxgb10-41b1:8000/v1
#llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
#
# --- Fallback: MacBook Pro M2 Max (Ollama, Q4_K_M) ---
#llm_provider: ollama
#llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
#llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096  # Cap output tokens (TASK-REV-84A7)
```

---

## Embedding side (unchanged in both modes)

Keep this block identical regardless of LLM choice. The cost driver
is the LLM, not the embedder — and the embedder runs locally on GB10
port 8001 with negligible compute cost.

```yaml
# Embedding provider for Graphiti vector search
# Options: openai (default), vllm, ollama
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
# Embedding dimension is resolved from KNOWN_EMBEDDING_DIMS.
```

> **Note:** the embedder side runs on GB10 port 8001 even when the
> LLM moves to Gemini. If GB10 is *fully* offline (machine powered
> down, not just GPU-busy), embeddings will also fail and Graphiti
> ingestion will halt entirely. In that case, either delay ingestion
> or temporarily switch `embedding_provider` to a cloud option — but
> avoid; cost will spike further.

---

## Switching procedure

### Manual (per repo)

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/<repo>
# Edit .guardkit/graphiti.yaml — replace the LLM block with Config A or B
# Commit:
git add .guardkit/graphiti.yaml
git commit -m "chore(graphiti): switch LLM provider to <gb10|gemini>"
git push
```

### Batched (all 13 repos at once)

Recommended when reverting from Gemini → GB10 (the cost-stop case)
or vice-versa at the start of a long training run.

Sketch — adapt paths first, dry-run before committing:

```bash
REPOS=(
  agentic-dataset-factory
  deepagents-player-coach-exemplar
  dotnet-functional-fastendpoints-exemplar
  forge
  guardkit
  jarvis
  lpa-platform
  nats-core
  nats-infrastructure
  require-kit
  specialist-agent
  study-tutor
  youtube-transcript-mcp
)

for repo in "${REPOS[@]}"; do
  cfg="/Users/richardwoollcott/Projects/appmilla_github/${repo}/.guardkit/graphiti.yaml"
  [ -f "$cfg" ] || { echo "SKIP $repo (no config)"; continue; }
  # ... apply your sed/python edit here ...
  echo "TODO $repo"
done
```

Better: keep two snippet files
(`.guardkit/snippets/llm-gb10.yaml`, `.guardkit/snippets/llm-gemini.yaml`)
and use a Python helper to splice them in between known marker
comments. Out of scope for this doc — ad-hoc editing is fine for 13
repos.

---

## Verification after switching

1. Check the live config:
   ```bash
   grep -E "^llm_provider:|^llm_model:" .guardkit/graphiti.yaml
   ```
2. Smoke test ingestion (≤30s):
   ```bash
   guardkit graphiti capture --interactive  # Ctrl-C after one capture
   ```
3. Smoke test search (≤5s):
   ```bash
   guardkit graphiti search "any-known-query"
   ```
4. If on GB10, confirm vLLM is reachable:
   ```bash
   curl -s http://promaxgb10-41b1:8000/v1/models | python3 -m json.tool | head -20
   ```
5. If on Gemini, confirm `GOOGLE_API_KEY` is set in the shell.

---

## When to switch which way

| Trigger | Switch to | Why |
|---------|-----------|-----|
| GB10 GPU busy training | MacBook (Config C) first, Gemini (Config B) if MacBook also unavailable | Both are free; only fall through to paid Gemini if neither local option works |
| GB10 finishes training | GB10 (Config A) | Stop Gemini cost accrual / faster than MacBook |
| GB10 hardware fully down (not just GPU) | MacBook (Config C) | Embedder also lives on GB10:8001 — ingestion will fail; switching LLM alone won't fix that |
| MacBook also offline | Gemini (Config B), short-term only | Last resort; budget cap applies |
| Daily Gemini spend > £5 | GB10 (Config A) or MacBook (Config C) | Soft budget cap; investigate ingestion volume |
| New repo onboarding | GB10 (Config A) | Cheaper default; opt-in to Gemini per-repo only when needed |

---

## MacBook Pro Ollama serving setup

Stand up the Ollama LLM endpoint on the MacBook Pro M2 Max so Config C
above can route Graphiti's LLM calls to it. Embeddings stay on GB10
port 8001 in this mode — only the LLM moves. Switching the YAML
config alone does nothing if Ollama isn't already listening.

> **Canonical deep dive:** [docs/reference/graphiti-macbook-offload.md](../docs/reference/graphiti-macbook-offload.md).
> The steps below are the minimum needed to bring serving up.

### Prerequisites

- MacBook Pro M2 Max with ≥20 GB free RAM (~10 GB for the model + headroom)
- Homebrew installed
- Tailscale running and the MacBook reachable as
  `richards-macbook-pro.tailebf801.ts.net`
- GB10 still serving the embedder on port 8001
  (independent of LLM choice)

### 1. Install Ollama

```bash
brew install ollama
```

### 2. Pull the model (one-time, ~9 GB download)

```bash
ollama pull qwen2.5:14b-instruct-q4_K_M
```

Q4_K_M is the validated quantization (TASK-GMO-004). Comparable
entity-extraction quality to GB10's FP8 build, ~2-3× slower.

### 3. Configure the listen port

Graphiti configs in this org expect Ollama at port **8000** (matches
the GB10 vLLM port shape). Ollama defaults to **11434**, so set
`OLLAMA_HOST` before starting:

```bash
export OLLAMA_HOST=0.0.0.0:8000
```

Make it persistent — add to `~/.zshrc` (or `~/.bashrc`):

```bash
echo 'export OLLAMA_HOST=0.0.0.0:8000' >> ~/.zshrc
```

> Binding `0.0.0.0` (not `127.0.0.1`) is required so the service is
> reachable over Tailscale from GB10 / other repos. Tailscale's network
> ACL is the security boundary here, not loopback.

### 4. Start serving

**Foreground (for testing / first-run validation):**

```bash
ollama serve
```

You should see `Listening on [::]:8000` in the log. Leave the terminal
open while the service is running.

**Background via launchd (recommended for daily use):**

```bash
brew services start ollama
```

Brew's service definition picks up `OLLAMA_HOST` from your shell env
when started. To verify the service is actually bound to 8000:

```bash
brew services list | grep ollama
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

If brew started Ollama on the default 11434 instead, stop it, set
`OLLAMA_HOST` in `~/Library/LaunchAgents/homebrew.mxcl.ollama.plist`'s
`EnvironmentVariables` block, and `brew services restart ollama`.

### 5. Allow inbound through the macOS firewall (first run only)

macOS will prompt the first time Ollama tries to listen on a non-loopback
port. Click **Allow**. To verify or change later:

`System Settings → Network → Firewall → Options → Ollama: Allow`

If you missed the prompt, re-launch `ollama serve` and the prompt
re-appears.

### 6. Pre-warm the model (avoid 10-30 s cold start on first request)

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:14b-instruct-q4_K_M",
    "messages": [{"role":"user","content":"ready check"}],
    "max_tokens": 8
  }' | python3 -m json.tool | head -20
```

Keeps the model resident. Without this, the first real Graphiti
ingestion request pays the load latency.

### 7. Verify reachability over Tailscale

From the MacBook:

```bash
curl -s http://localhost:8000/v1/models | python3 -m json.tool | head -10
```

From GB10 or any other Tailscale node:

```bash
curl -s http://richards-macbook-pro.tailebf801.ts.net:8000/v1/models \
  | python3 -m json.tool | head -10
```

Both should return a JSON list including `qwen2.5:14b-instruct-q4_K_M`.

### 8. Smoke-test against Graphiti

In any repo where you've flipped the YAML to Config C
(MacBook ACTIVE):

```bash
guardkit graphiti capture --interactive --max-questions 1
```

Answer one question, watch for successful ingestion. ~30-60 s on
MacBook vs ~10-20 s on GB10 — slower but real.

### Stopping the service

```bash
brew services stop ollama   # if started via brew
# or Ctrl-C the foreground `ollama serve` process
```

### Common gotchas

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Connection refused` from GB10 | Ollama bound to 127.0.0.1 not 0.0.0.0 | Re-export `OLLAMA_HOST=0.0.0.0:8000` then restart |
| `Connection refused` over Tailscale only | macOS firewall blocking | Allow Ollama in System Settings → Firewall |
| `model 'qwen2.5:...' not found` | Model never pulled (or pulled on a different user account) | `ollama pull qwen2.5:14b-instruct-q4_K_M` |
| First request takes 30+ s | Cold model load | Run the pre-warm curl from step 6 |
| Tailscale name doesn't resolve | MagicDNS off, or MacBook not in tailnet | `tailscale status` from GB10; reconnect MacBook |
| Brew service running but port 8000 not listening | `OLLAMA_HOST` not in launchd env | Edit the brew plist's `EnvironmentVariables`, restart |
| Ingestion succeeds but is very slow | Other memory-heavy apps on MacBook | Close browsers; check `vm_stat` and `ollama ps` |

### Performance baseline (TASK-GMO-004 measurements, 2026-04-03)

| Workload | MacBook (Q4_K_M) | GB10 (FP8) |
|----------|------------------|------------|
| Single entity-extraction call | ~17 s | ~9 s |
| Full episode pipeline | ~55 s | ~30 s |
| Tokens/sec | 15-25 | 40 |
| Prefix caching | ❌ no | ✅ yes |

Acceptable for interactive use; obviously slower for bulk seeding.
If a bulk reseed across all 13 repos is needed and GB10 is unavailable,
prefer waiting for GB10 over running it on MacBook.

---

## Related

- [TASK-REV-E8D1 review report](../.claude/reviews/TASK-REV-E8D1-review-report.md)
  — embedding dim alignment (separate concern, kept as-is in both modes)
- [docs/guides/graphiti-gemini-rollout-setup.md](../docs/guides/graphiti-gemini-rollout-setup.md)
  — Gemini paid-tier setup and `GOOGLE_API_KEY` provisioning
- [docs/reference/graphiti-macbook-offload.md](../docs/reference/graphiti-macbook-offload.md)
  — full deep-dive on MacBook offload: architecture, MCP server config,
  toggle script, troubleshooting
