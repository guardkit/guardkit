# AutoBuild on llama-swap — Findings & Operational Notes

**Date:** 2026-05-14
**Context:** DDD South West 2026 demo preparation. Attempted to run `guardkit autobuild`
end-to-end against the GB10's llama-swap stack (post-vLLM migration) using local
models as the autobuild backend.
**Companion docs:**
[`RUNBOOK-v3-production-deployment.md`](./RUNBOOK-v3-production-deployment.md),
[`llama-swap-systemd-supervision.md`](./llama-swap-systemd-supervision.md),
[`POST-VALIDATION-model-strategy-revision.md`](./POST-VALIDATION-model-strategy-revision.md).

---

## 1. TL;DR

- **llama-swap on `:9000` speaks Anthropic `/v1/messages` natively** —
  no shim/translation layer is needed for the Claude Agent SDK or
  `guardkit autobuild`. Streaming SSE event shapes
  (`message_start` → `content_block_delta` → `message_stop`) are
  Anthropic-spec-compliant. Tool-use blocks work. Model aliases route
  correctly (e.g. `claude-sonnet-4-5-20250929` → workhorse).
- **The bundled Claude Code CLI sends a ~46 K-token system prompt with
  every request.** Per-slot context size on llama.cpp must be ≥ 64 K to
  avoid `exceed_context_size_error 400`. Recommended: ≥ 98 K.
- **`--np N` divides `--ctx-size` across slots.** `-np 2` with
  `--ctx-size 49152` gives only **24 K per slot** — the bundled CLI's
  system prompt blows that instantly. **Do not raise `-np` for autobuild
  workloads without also raising `--ctx-size` proportionally.**
- **Qwen3.6-35B-A3B (workhorse) fails the autobuild design protocol.**
  The model wanders through 19 tool-use turns without emitting the
  required output markers (e.g. `Plan saved to: ...`). This is a
  protocol-following / instruction-following limitation, not infra.
- **Qwen3-Coder-30B-A3B-Instruct (UD-Q4_K_XL) downloaded and configured**
  as an opt-in alternative at `autobuild-coder` alias, but **not yet
  validated end-to-end** for autobuild.
- **The `/unload` endpoint is the system's memory safety hatch.** A
  single `curl http://localhost:9000/unload` drops every loaded
  llama-server child, returning ~100 GB to the OS. Use it any time
  memory pressure is approaching the 121 GB ceiling.
- **Memory ceiling is real and unforgiving.** Two freezes during this
  session caused by running `workhorse + coder + 3 other models`
  concurrently (~110+ GB resident before VS Code / Firefox). The
  121 GB unified-memory limit was crossed at 126.69 GB and the GB10
  required a hard reset.
- **For the DDD South West demo: run autobuild on Anthropic
  (cloud API), keep everything else local.** Player↔Coach is the most
  fragile step and the most likely to fail visibly mid-talk; the rest
  of the local fleet (Jarvis routing, ADR check via architect-agent,
  Reachy Scholar via Gemini) carries the "local AI on stage" narrative
  with much lower risk.

---

## 2. What works (validated 2026-05-14)

### 2.1 Anthropic-API compatibility

llama-swap proxies `/v1/messages` through llama.cpp's Anthropic Messages
API support (llama.cpp PR #17570). Verified:

| Capability | Test | Result |
|---|---|---|
| Non-streaming response shape | `curl -X POST /v1/messages` with `claude-sonnet-4-5-20250929` | `type: message`, `content: [{type: text, ...}]`, `stop_reason: end_turn` ✓ |
| Streaming SSE | `stream: true` request | All standard event types emitted (`message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`) ✓ |
| Tool-use call | `tools: [...]` in request | `content` returns `{type: tool_use, name, input, id}` block, `stop_reason: tool_use` ✓ |
| Bundled Claude Code CLI | `claude --print "..."` with `ANTHROPIC_BASE_URL=http://localhost:9000` | Works against any aliased model with ≥ 64 K per-slot ctx ✓ |

### 2.2 Model alias routing

The aliases under each model in `config.yaml` resolve correctly. Tested
against workhorse and coder routings:

```
claude-sonnet-4-5-20250929 → qwen36-workhorse  (or qwen3-coder-30b if reassigned)
jarvis-reasoner            → qwen36-workhorse  (load-bearing for Jarvis)
software-architect         → architect-agent
study-tutor                → gemma4-tutor
```

### 2.3 AutoBuild orchestrator path

`guardkit autobuild task TASK-XXX` (with `ANTHROPIC_BASE_URL` env)
successfully:
1. Created the worktree
2. Pruned non-essential rules
3. Invoked the bundled Claude Code CLI via `claude_agent_sdk` subprocess
4. Streamed the design-phase prompt to llama-swap
5. Received and parsed assistant messages back

The orchestrator infrastructure (worktree management, SDK invocation,
prompt assembly, response parsing) is **not the bottleneck**. The
bottleneck is the **target model's ability to comply with the design
protocol's output marker contract**.

---

## 3. Failure modes observed

### 3.1 `-np > 1` divides per-slot context

llama.cpp's `-np N` (parallel slots) splits the total `--ctx-size`
across slots. Configuring `-np 2 --ctx-size 49152` yields 24 K
per-slot — far below the 46 K the bundled Claude Code CLI requires
just for its system-prompt baseline.

**Symptom:** Any request from the bundled CLI returns
`400 {"error":{"code":400,"message":"request (45859 tokens) exceeds the
available context size (24576 tokens)","type":"exceed_context_size_error"}}`.

**Fix:** For autobuild-bound models, keep `-np 1` and set
`--ctx-size` ≥ 98304. Trade slots for context, not the other way
round.

### 3.2 Qwen3.6-35B-A3B can't complete the autobuild design protocol

With workhorse aliased to `claude-sonnet-4-5-20250929`, autobuild's
pre-loop design phase consistently fails after ~19 SDK turns with:

```
ERROR Quality gate 'plan_generation' blocked: Design phase did not
return plan path for TASK-DEMO-D5DD. The task-work --design-only
execution may have failed.
```

The model executes tool calls (Read, Glob, etc.) but **does not** write
the required `.claude/task-plans/TASK-XXX-implementation-plan.md` file
or emit the literal output marker `Plan saved to: .claude/task-plans/...`
that `TaskWorkStreamParser` looks for.

**Diagnosis:** This is a model-capability limit, not infra. The
GuardKit design protocol is ~12 K tokens of strict-format instructions
with seven phase markers that must be emitted verbatim. 35B-A3B has
~3 B active params per token (MoE) and loses focus on the multi-phase
protocol over a long generation. Qwen3-Coder-30B-A3B (coder-trained
on agentic tool-use traces) is a more promising candidate but
**untested as of 2026-05-14**.

### 3.3 Memory ceiling: 121 GB hard, ~110 GB practical with apps

Two freezes during the session, both caused by **concurrent residency**
of workhorse + coder + 3 other models. The unified-memory ceiling is
121 GB; the GB10 froze when reported usage hit 126.69 GB (Dashboard
shows total including swap and OS buffers).

**Root cause of both freezes:** llama-swap's `matrix.sets` controls
*runtime eviction* on incoming requests, not *preload behaviour*.
With `ttl: 0` on every model (the production config), nothing
auto-unloads. Loading a new model on top of all existing models
just *adds* memory pressure until OOM.

**Mitigation hierarchy** (lightest → heaviest):
1. **Don't preload more than 5 models simultaneously.**
2. **Hit `/unload` when memory creeps over 100 GB used.** Fast and
   non-destructive — models reload on next request.
3. **Add per-model `ttl: 600`** (10-minute idle unload) to non-critical
   models so they auto-release when not in active use.
4. **Edit `matrix.sets`** to encode genuine mutual exclusion when two
   large models must alternate (e.g. `workhorse` vs `coder`).

### 3.4 The unmerged README

`docs/research/dgx-spark/README.md` has unresolved git merge conflict
markers from 2026-05-07 (`<<<<<<< Updated upstream` / `>>>>>>> Stashed
changes` at lines 7-13 and 75-103). This is **out of scope** for the
findings doc but worth flagging — a follow-up should resolve the
conflict and consolidate the two competing model-strategy paragraphs.

---

## 4. Current llama-swap config (2026-05-14)

Production config: `/opt/llama-swap/config/config.yaml`
(host `promaxgb10-41b1`).

### 4.1 Preloaded models (`hooks.on_startup.preload`)

| Model | Footprint (weights + KV @ ctx) | Used by |
|---|---|---|
| `qwen-graphiti` (Qwen2.5-14B Q8_0) | ~28 GB @ 65 K, `-np 4` (16 K per slot — bumped 2026-05-25, see §9) | Graphiti entity extraction, Jarvis intent routing |
| `nomic-embed` (nomic-embed-text-v1.5 f16) | ~2 GB @ 8 K, `-np 4` | Graphiti embeddings, ChromaDB |
| `qwen36-workhorse` (Qwen3.6-35B-A3B UD-Q4_K_XL) | ~30 GB @ 98 K, `-np 1` | AutoBuild Player/Coach (legacy), Forge, Dataset Factory, **Jarvis-reasoner subagent** |
| `gemma4-tutor` (Gemma 4 26B-A4B Q4_K_M) | ~22 GB @ 32 K, `-np 1` | GCSE study tutor (Socratic) |
| `architect-agent` (gemma-4 thinking variant Q4_K_M) | ~25 GB @ 65 K, `-np 1` | ADR / architectural review (software-architect alias) |

Steady-state baseline (post 2026-05-25 bump): **~93 GB used** (was
~87 GB pre-bump; see §9), leaving ~28 GB for OS + VS Code + Firefox
+ autobuild's Python orchestrator. The bump was deliberately landed
as `-np 4 / ctx 65 K` instead of `-np 6 / ctx 98 K` precisely to keep
the headroom growth modest (+6 GB instead of +12-16 GB). Keep
`qwen3-coder-30b` and any extra on-demand model evicted unless actively
in use, and treat `/unload` (§5.1) as the first response to memory
pressure during the demo.

### 4.2 Defined-but-not-preloaded (on-demand)

| Model | Footprint | Trigger |
|---|---|---|
| `qwen3-coder-30b` (Qwen3-Coder-30B-A3B-Instruct UD-Q4_K_XL) | ~30 GB @ 98 K, `-np 1` | Requested via `autobuild-coder` alias. **Evicts workhorse** via `coder_set`. UNTESTED for autobuild end-to-end. |

GGUF on disk: `/opt/llama-swap/models/qwen3-coder-30b/Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf` (17.67 GB).

### 4.3 Alias map (effective 2026-05-14, post-restore)

Workhorse (`qwen36-workhorse`):
```
autobuild-player
coach
jarvis-reasoner          # used by Jarvis supervisor (jarvis/src/jarvis/config/settings.py:54)
forge-orchestrator
dataset-factory
claude-sonnet-4-6
claude-opus-4-7
claude-sonnet-4-5-20250929
```

Coder (`qwen3-coder-30b`):
```
autobuild-coder          # explicit opt-in for autobuild experiments
```

To migrate the `claude-sonnet-*` aliases to coder for post-demo
experiments, edit the `aliases:` blocks under each model in
`config.yaml` and let llama-swap hot-reload via `-watch-config`.

### 4.4 `matrix.sets` (mutual exclusion)

```yaml
matrix:
  vars:
    qg: qwen-graphiti
    ne: nomic-embed
    qw: qwen36-workhorse
    qc: qwen3-coder-30b
    gt: gemma4-tutor
    aa: architect-agent
  sets:
    all:        "qg & ne & qw & gt & aa"   # default preload + workhorse-aliased traffic
    coder_set:  "qg & ne & qc & gt & aa"   # coder-aliased traffic; evicts workhorse
```

**Important behaviour:** `matrix.sets` governs **request-time eviction**,
not startup preload. The preload list is independent. When a request
hits an alias bound to a model not in the currently-loaded set,
llama-swap consults the smallest containing set and evicts everything
outside it. This makes the workhorse↔coder swap automatic on first
coder-alias request — but **only after preload has completed**.

---

## 5. Operational commands

### 5.1 `/unload` — the safety hatch

```bash
# Unload every running llama-server child. Returns ~100 GB to the OS.
curl http://localhost:9000/unload
```

Returns `OK` and a 200 status. Idempotent. Models reload on the next
request — first request pays a cold-start of 20-60 s depending on
the model size.

**When to use:**
- Memory headroom drops below ~10 GB
- After a known-to-bloat workflow (e.g. an autobuild run that
  accumulated state on multiple models)
- Before switching demo workflows (e.g. between Jarvis-heavy and
  coder-heavy work)

### 5.2 List loaded models

```bash
curl -s http://localhost:9000/v1/models | python3 -m json.tool
```

Note: this lists all *defined* models with their aliases, not just
loaded ones. To see what's actually resident in memory:

```bash
ps -eo pid,etime,args --no-headers | grep llama-server | grep -v grep
```

### 5.3 Memory check

```bash
free -g | head -2
# Useful headers:
#   total: 121 (GB10 unified memory ceiling)
#   used:  steady-state baseline (~87 GB with all 5 preloaded)
#   available: real headroom for new allocations
```

### 5.4 Anthropic-API smoke test

```bash
# Verify llama-swap proxies a tool-use call correctly
curl -s http://localhost:9000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 80,
    "tools": [{"name":"add","description":"add ints","input_schema":{"type":"object","properties":{"a":{"type":"integer"},"b":{"type":"integer"}},"required":["a","b"]}}],
    "messages": [{"role":"user","content":"What is 7 plus 4? Use the tool."}]
  }' | python3 -m json.tool
```

Expected: response includes a `tool_use` content block with
`{"a": 7, "b": 4}` and `stop_reason: tool_use`.

### 5.5 Autobuild against local backend

```bash
# Routes through llama-swap on :9000; model alias resolves to whichever
# llama-server child currently holds that alias (workhorse or coder).
ANTHROPIC_BASE_URL=http://localhost:9000 \
ANTHROPIC_API_KEY=vllm-local \
guardkit autobuild task TASK-XXX --max-turns 3 --verbose

# To explicitly target the coder model post-demo:
ANTHROPIC_BASE_URL=http://localhost:9000 \
ANTHROPIC_API_KEY=vllm-local \
guardkit autobuild task TASK-XXX --model autobuild-coder --max-turns 3 --verbose
```

### 5.6 Force a fresh autobuild run

`guardkit autobuild task` writes `autobuild_state:` to the task
frontmatter and creates a worktree. To re-run cleanly after a failure
(no `--fresh` flag on `autobuild task` as of 2026-05-14):

```bash
# 1. Remove the worktree and its branch
git worktree remove .guardkit/worktrees/TASK-XXX --force
git branch -D autobuild/TASK-XXX

# 2. Edit the task file to strip the autobuild_state block and reset
#    status back to 'backlog'

# 3. Re-launch autobuild
```

`guardkit autobuild feature` does support `--fresh`.

---

## 6. Reachy + Jarvis routing topology

Useful for demo planning — confirms which llama-swap models *are* and
*are not* exercised by each part of the demo flow.

| Demo component | Backend | Touches llama-swap? | Model alias hit |
|---|---|---|---|
| Reachy Scholar conversation (study tutor questions) | Google Gemini Live (`gemini-3.1-flash-live-preview`) | **No** | — |
| Reachy reads student model from Graphiti | FalkorDB (Synology via Tailscale) | **No** (DB, not LLM) | — |
| OpenWebUI → Jarvis supervisor (intent routing) | Anthropic API or local (depends on Jarvis config) | If local: yes | (supervisor model — check `jarvis/.env`) |
| Jarvis-reasoner subagent (reasoning hand-off) | **Local via llama-swap** | **Yes** | `jarvis-reasoner` → workhorse |
| ADR / architecture check (DDD style question) | Local | **Yes** | `software-architect` → architect-agent |
| `guardkit autobuild` (Player↔Coach) | Configurable: Anthropic or local | Optional | `claude-sonnet-4-5-20250929` → workhorse (or coder if reassigned) |

**Implication:** Reachy is independent of llama-swap. Asking Reachy a
study question on stage does **not** swap models or compete for GB10
memory.

---

## 7. Recommended DDD South West 2026 demo configuration

Based on findings 1-6:

1. **Autobuild on Anthropic API.** Set `ANTHROPIC_BASE_URL` to
   `https://api.anthropic.com` (default — i.e. don't set it) and use
   a real API key. Eliminates the riskiest, least-tested path. Frees
   ~30 GB of GB10 memory that would otherwise be needed for workhorse.
2. **Everything else local.** Reachy (Gemini), Jarvis routing
   (workhorse), ADR check (architect-agent), study tutor (gemma4-tutor)
   all stay on the GB10. The "local AI fleet on stage" narrative is
   preserved.
3. **Pre-warm before the talk** by issuing one
   `curl http://localhost:9000/v1/models` and one trivial request to
   each preloaded alias. Memory will settle at the ~87 GB baseline
   before stage time.
4. **Keep `/unload` mapped to a terminal alias on stage.** If anything
   goes sideways memory-wise:
   ```bash
   alias unload='curl http://localhost:9000/unload'
   ```
5. **Disable any background automation** that hits `jarvis-reasoner`,
   `forge-orchestrator`, `dataset-factory`, or `autobuild-coder`
   during the talk window (scheduled jobs, Dataset Factory crons,
   etc.). Any of those could trigger an unexpected model swap.

---

## 8. Open questions / follow-up work

1. **Validate Qwen3-Coder-30B-A3B for autobuild.** Run the same
   TASK-DEMO-D5DD smoke test against `--model autobuild-coder` and
   compare to workhorse's 19-turn wander. The hypothesis is that
   coder-trained models will produce the required output markers.
   Tracked: post-demo.
2. **Decide whether to migrate `claude-sonnet-*` aliases to coder
   permanently.** Depends on (1). If coder succeeds, the long-term
   default for autobuild should be the coder, with workhorse retained
   for Jarvis / Forge / Dataset Factory.
3. **Add `ttl: 600` to gemma4-tutor and qwen3-coder-30b.** Both are
   "load when needed" candidates; auto-unload on idle would reduce
   the surface for accidental over-allocation freezes.
4. **Resolve README.md merge conflict markers** (lines 7-13 and
   75-103). The two competing intros to the "Current architecture"
   section need consolidating; the "External references" section
   has parallel link lists that overlap.
5. **Document Anthropic-Messages-API endpoint coverage in llama.cpp.**
   `/v1/messages` works for non-streaming, streaming, and tool use.
   Untested: vision input, prompt caching headers, `cache_control`
   block annotations (the SDK sends these), and `anthropic-beta`
   header passthrough.
6. **Investigate why a single `/v1/messages` post-startup load shows
   ~46 K tokens.** The bundled Claude Code CLI is sending its own
   massive system prompt — verify this is intentional and not a
   prompt-caching miss that could be optimised. If avoidable, every
   per-slot ctx requirement on the GB10 drops.

---

## 9. Configuration revisions

### 9.1 2026-05-25 — qwen-graphiti `--ctx-size 32768 → 65536`, `-np 6 → 4`

**Trigger:** Graphiti architecture-seed run for the DDD South West
2026 demo failed when graphiti-core's `full_doc` chunker emitted a
**9443-token chunk** for the largest workflow rule. The chunk
exceeded the per-slot ceiling and llama.cpp returned
`exceed_context_size_error 400`, aborting the seed before the
ARCHITECTURE.md / domain-model.md chunks (expected to land in the
9-12 K range) could be processed.

**Diagnosis:** `qwen-graphiti` was running with `--ctx-size 32768`
and `-np 6`. llama.cpp's parallel-slot mode divides total ctx-size
across slots, so each slot only had **~5.6 K** of context
(32768 ÷ 6 ≈ 5461, rounded by alignment to ~5632). Anything beyond
that 400'd.

**Memory pressure at deploy-time forced a slot-trade design.**
The initial plan was to triple `--ctx-size` (32768 → 98304) while
preserving `-np 6` (so each slot would jump from 5.6 K → 16 K with
no loss of fan-out absorption). At apply-time, however, the GB10
was already at **114 GB used / 121 GB total** — only 7 GB free,
swap at 7 GB. The +12-16 GB KV-cache growth for the 98 K plan would
have crossed the 121 GB ceiling on reload, matching the freeze
profile that hard-reset the box on 2026-05-14 (see §1). The applied
design trims `-np 6 → 4` instead, holding per-slot context at the
same 16 K target with only a +6 GB KV delta.

**Change applied (live config + runbook source-of-truth):**

```diff
   "qwen-graphiti":
     cmd: >
       $LLAMA_SERVER
       --port \${PORT}
       --host 0.0.0.0
       --model $GRAPHITI_FILE
       --alias qwen-graphiti
-      --ctx-size 32768
+      --ctx-size 65536
       --batch-size 2048
       --ubatch-size 2048
       --threads 16
       -ngl 999
       --no-mmap
       --flash-attn on
       --jinja
       --temp 0.0
-      -np 6
+      -np 4
     checkEndpoint: /health
     ttl: 0
-    concurrencyLimit: 8
+    concurrencyLimit: 6
```

Per-slot context: ~5.6 K → **~16 K** (65536 ÷ 4 = 16384). Leaves
~4-7 K headroom over the 9-12 K chunk band for graphiti-core's
prompt scaffolding (entity-extract / edge-extract / dedup /
summarise templates).

**Fan-out trade.** Slot count dropped 6 → 4. graphiti-core's
typical 3-5-call `add_episode` fan-out (TASK-OPS-9F2A, 2026-05-04)
still fits in 4 slots in the common case; a worst-case 5-call burst
will queue briefly at llama-swap before dispatch. The 2026-05-04
rationale for `-np 6` was specifically to absorb a 5-call burst
*plus one* admin-probe headroom slot — that headroom is gone now,
but 5-bursts are infrequent enough that brief queueing is
acceptable. `concurrencyLimit 8 → 6` preserves the same ~1.5×
admin-probe buffer ratio over `-np`.

**VRAM cost:** KV cache scales linearly with total ctx-size. 2× ctx
(32 K → 65 K) ≈ **+6 GB**, taking Qwen2.5-14B Q8 from ~22 GB to
~28 GB. Steady-state preload baseline crosses from ~87 GB to
**~93 GB**, leaving ~28 GB of headroom — comfortable.

**Deploy steps (executed 2026-05-25 against `promaxgb10-41b1`):**

```bash
# 1. Back up the live config
sudo cp /opt/llama-swap/config/config.yaml \
        /opt/llama-swap/config/config.yaml.bak-2026-05-25-pre-ctxbump

# 2. /unload all children to free memory before reload
#    (skip this only if you have ≥20 GB free already)
curl -sS http://localhost:9000/unload    # frees ~100 GB

# 3. Edit /opt/llama-swap/config/config.yaml — apply the diff above

# 4. Probe qwen-graphiti to trigger reload with new args
curl -sS http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-graphiti","max_tokens":4,
       "messages":[{"role":"user","content":"ping"}]}'

# 5. Probe nomic-embed to bring embeddings back
curl -sS http://localhost:9000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed","input":"ping"}'

# 6. Verify the new args on the running child
ps -o pid,args -C llama-server | grep qwen-graphiti
# Expect: --ctx-size 65536 ... -np 4

# 7. Confirm memory footprint
free -h
```

**Validation:** re-run the Graphiti architecture-seed against the
workflow rule that previously 400'd. Expected: no
`exceed_context_size_error`. ARCHITECTURE.md / domain-model.md
chunks in the next wave should also flow without error provided
they land at ≤16 K including graphiti-core's prompt scaffolding.

**Follow-up considerations:**

- If ARCHITECTURE.md / domain-model.md chunks land *above* 16 K
  including scaffolding, the same trade can be made again
  (`-np 4 → 2`, `--ctx-size 65536 → 98304` would yield ~49 K per
  slot at roughly the same VRAM). Below that point, the
  graphiti-core fan-out queueing penalty starts to dominate.
- If memory headroom permits later (e.g. after evicting
  `qwen3-coder-30b` permanently), revisit the original
  `-np 6 / --ctx-size 98304` design to restore fan-out absorption.

### 9.2 2026-05-28 — add `qwen-coder-next` (vLLM/FP8, on-demand, exclusive)

**Trigger:** TASK-HMIG-009A pre-flight canary flagged that
Qwen3-Coder-Next is not served by llama-swap.

**Decision — vLLM/FP8, not llama.cpp/GGUF.** Qwen3-Coder-Next ships as
FP8 safetensors (`Qwen3NextForCausalLM` / `qwen3next` — a hybrid
linear-attention MoE). llama.cpp *can* load a GGUF of it (arch is
supported in this build, and `convert_hf_to_gguf.py` dequantizes fp8),
but the delta-net path is CPU-bound and slow — llama.cpp#19345
("40% slower than vLLM + high CPU usage", closed not-planned). The
forum "HOW-TO: Run Qwen3-Coder-Next on Spark" runs it via **vLLM FP8**
at ~42-43 tok/s, and we already have the 75 GB FP8 weights cached, so
no download/conversion is needed. Verified non-disruptively before
applying: vLLM 0.13.0 in `nvcr.io/nvidia/vllm:26.01-py3` registers
`Qwen3NextForCausalLM`, and llama-swap v208 supports `cmdStop`.

**Concurrency analysis (why exclusive, sequential).** The FP8 weights
are a ~75 GB hard floor (~90 GB resident with KV), so coder-next cannot
co-reside with the study tutor (~22 GB) under the 121 GB ceiling. The
`coder_next` matrix.set holds only this model: requesting it evicts all
llama.cpp models; any later family-alias request evicts it. Fast coder
during a build, swap back to the family afterwards.

**Change applied** (`/opt/llama-swap/config/config.yaml`, hot-reloaded
via `-watch-config`):

- New model `qwen-coder-next` (alias `autobuild-coder-next`), launched
  by `/opt/llama-swap/scripts/vllm-coder-next.sh ${PORT}` (foreground
  `docker run --rm` of vLLM serving `Qwen/Qwen3-Coder-Next-FP8` on
  container :8000; `--gpu-memory-utilization 0.75`, `--max-model-len
  131072`, `--tool-call-parser qwen3_coder`, `--attention-backend
  flashinfer`). `cmdStop: docker stop vllm-coder-next`,
  `checkEndpoint: /health`, `ttl: 0`.
  **NB:** do *not* pass `--load-format fastsafetensors` — the NGC image
  (`nvcr.io/nvidia/vllm:26.01-py3`) does not bundle the `fastsafetensors`
  package and vLLM aborts engine init with `ModuleNotFoundError: No
  module named 'fastsafetensors'`. Default (`load_format=auto`) works.
- `matrix.vars.qcn: qwen-coder-next` and `matrix.sets.coder_next:
  "qcn"`. **Not** added to `hooks.on_startup.preload` (on-demand only).
- Backup: `config.yaml.bak-2026-05-28-pre-coder-next`.

**Keepalive conflict (operational).** The keepalive timer
(`llama-swap-keepalive.timer`, active+enabled) probes the 4 core models
every ~5 min. While coder-next is loaded for a build, that probe would
revive a family model and — via matrix.sets — **evict coder-next
mid-build**. Pause it before a coder-next build and re-enable after:

```bash
sudo systemctl stop llama-swap-keepalive.timer
# ... run the build ...
sudo systemctl start llama-swap-keepalive.timer
```

**Smoke test (run when the box has headroom — needs ~90 GB free).**

```bash
# 0. Free memory first — coder-next is exclusive and large.
curl -sS http://localhost:9000/unload          # evict the family (~frees 90 GB)
sudo systemctl stop llama-swap-keepalive.timer  # stop the 5-min revive probe
free -g                                          # confirm ≥ ~95 GB available

# 1. Trigger the load (first request cold-starts vLLM; ~2-3 min).
curl -sS http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-coder-next","max_tokens":16,
       "messages":[{"role":"user","content":"print(\"hi\")"}]}'

# 2. Watch the container come up / spot flag issues (flashinfer, --gpus).
docker logs -f vllm-coder-next        # Ctrl-C once "Application startup complete"
free -g                                # expect ~90 GB resident, under 121 GB

# 3. Anthropic tool-use smoke test (the path autobuild uses).
curl -sS http://localhost:9000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-coder-next","max_tokens":80,
       "tools":[{"name":"add","description":"add ints","input_schema":{"type":"object","properties":{"a":{"type":"integer"},"b":{"type":"integer"}},"required":["a","b"]}}],
       "messages":[{"role":"user","content":"What is 7 plus 4? Use the tool."}]}'

# 4. End-to-end autobuild against the local coder.
ANTHROPIC_BASE_URL=http://localhost:9000 ANTHROPIC_API_KEY=vllm-local \
  guardkit autobuild task TASK-XXX --model qwen-coder-next --max-turns 3 --verbose

# 5. Swap back to the family + restore keepalive.
curl -sS http://localhost:9000/unload
sudo systemctl start llama-swap-keepalive.timer
```

**Known risk flags to watch in step 2:** if the GPU is not visible,
switch `--gpus all` → `--device nvidia.com/gpu=all` in the wrapper
(Docker here uses the CDI runtime). If vLLM rejects
`--attention-backend flashinfer`, drop it (falls back to flash-attn,
lower max ctx). If it 404s on the model name, confirm the request's
`model` is in the wrapper's `--served-model-name` list.

**Validated 2026-05-28 (smoke test passed).** `--gpus all` works,
flashinfer loads, hybrid (mamba/linear-attention) + FP8 MoE (Triton
backend) init OK. Cold load ~7 min (no fastsafetensors → slower weight
load; still well under the 600 s `healthCheckTimeout`). Steady resident
**~95 GB (101 GB used / ~20 GB free)** at util 0.75 / 131 K ctx — under
the 121 GB ceiling but tighter than the prior ~92 GB estimate; lower
util to ~0.68 if you need more room for VS Code/Firefox during a build.
Verified: `/v1/chat/completions` returns; `/v1/messages` returns a
correct `tool_use` block (`add{a:7,b:4}`, `stop_reason: tool_use`) —
the AutoBuild path. The *first* request during the cold load may return
empty while weights load, so **pre-warm with one throwaway request**
before starting a build (§7.3).

### 9.3 2026-05-28 — add `granite-docling` (LPA extraction VLM); coder-30b → exclusive group

**Trigger:** the LPA extraction project's `vllm-docling.sh` (standalone
vLLM on :8002, Granite Docling 258M) crashed and its curl failed.

**Two stacked problems found:**

1. **Memory clash with llama-swap (the reported symptom).** Standalone
   vLLM crashed in KV-cache init with
   `AssertionError: Error in memory profiling. Initial free memory
   21.7 GiB, current free memory 83.7 GiB ... other processes ...
   release GPU memory while vLLM is profiling.` Two independent memory
   managers (standalone vLLM + llama-swap) on one unified pool: llama-swap
   swapped a model out mid-profile and vLLM's consistency assertion
   aborted. This is DECISION-DF-001 §4.4 in practice.
2. **Vision-conv cuDNN incompatibility (the real blocker).** With memory
   stabilised, a deterministic failure surfaced in the idefics2/3 vision
   encoder's patch-embedding conv:
   `conv.py F.conv2d → RuntimeError: GET was unable to find an engine to
   execute this computation`. cuDNN in the NGC `vllm:26.01-py3` image
   (vLLM 0.13) cannot find a conv2d engine for this config on GB10
   (Blackwell sm_121).

**Fixes:**

- **Brought docling under llama-swap** (one memory manager → no clash):
  model `granite-docling` (aliases `granite-docling-258M`, `docling`)
  launched by `/opt/llama-swap/scripts/vllm-docling.sh ${PORT}`,
  `cmdStop`, `/health`, `ttl: 0`. Added to the `dl` var and **every**
  matrix.set (`all`, `coder_30b`, `coder_next`) so its ~2 GB is never
  evicted — co-resides with the family (~91 GB) and with coder-next
  (~97 GB). Not preloaded; loads on first LPA request.
- **Switched the docling image to `vllm/vllm-openai:cu130-nightly`**
  (vLLM 0.18, torch 2.10+cu130, **cuDNN 9.15**) — its newer cuDNN runs
  the Blackwell conv fine. Entrypoint is `["vllm","serve"]`, so the
  wrapper uses `--entrypoint vllm` + `serve <model>`. `--gpu-memory-
  utilization 0.10` + `--enforce-eager` + `--max-num-seqs 8` (util 0.05
  left no room for KV cache; enforce-eager drops CUDA-graph memory).
  coder-next stays on the NGC image (validated; text model, no conv).
- **Verified end-to-end:** `Application startup complete`, KV cache
  9.86 GiB / 459 K tokens, `/health` 200, `/v1/models` lists
  `granite-docling-258M`, `POST /v1/chat/completions → 200 OK` via the
  llama-swap proxy. (Granite Docling is a document-image VLM; a raw
  *text* chat generates at ~1 tok/s and may appear to hang — that's the
  model, not the proxy. The LPA pipeline sends document images.)

**Model-name alignment (2026-05-28):** llama-swap's `/v1/models` advertises
the model *key* (`granite-docling`) but forwards the client's `model` string
as-is to the vLLM backend, which initially only registered
`granite-docling-258M` → a client that auto-discovered `granite-docling` got
a 404 at the backend. Fixed by setting the wrapper's
`--served-model-name granite-docling-258M granite-docling docling`, so the
backend accepts every name llama-swap can route. All three now work
end-to-end (verified via the container's direct `/v1/models`).

**LPA client change:** point Docling at `http://promaxgb10-41b1:9000/v1/chat/completions`
from another machine (or `http://localhost:9000/...` on the GB10), model
`granite-docling-258M`, e.g.
`DOCLING_VLM_URL=http://localhost:9000/v1/chat/completions
./scripts/docling-process.sh --vlm <pdfs>`. The standalone `:8002`
`vllm-docling.sh` is superseded. (Docling's default non-VLM mode needs no
endpoint at all.)

**coder-30b → exclusive group.** `qwen3-coder-30b` moved out of the
family-mixed `coder_set` into its own exclusive set `coder_30b: "qc & dl"`
(mirrors `coder_next: "qcn & dl"`); `coder_set` retired. Reason: the
keepalive timer revives `qwen36-workhorse` every 5 min, which (under the
old `coder_set`) ping-ponged workhorse↔coder-30b and briefly co-resided
both → the ~111 GB near-ceiling spike. As with coder-next, **pause the
keepalive timer while using coder-30b** (see
`llama-swap-keepalive-start-stop.md`).

### 9.4 2026-05-29 — GB10 freeze: two compounding instability bugs

After a hard freeze + reboot, two distinct bugs were found, both making the
GB10 over-commit unified memory under the new (docling + dual-coder) fleet.

**Bug 1 — matrix multi-set membership made docling requests load coders.**
§9.3 put `granite-docling` in *every* set (`all`, `coder_30b: "qc & dl"`,
`coder_next: "qcn & dl"`) so it'd never be evicted. Side effect: the solver
could satisfy a docling request via a *coder* set, and with a coder loaded it
chose the cheapest containing set — **loading a 77 GB / 18 GB coder to serve a
tiny docling request**, thrashing docling's lifecycle (`exit 1` /
`swapState() Unexpected current state`) so `:9000` hung while the container was
healthy (0.15 s direct on its port). **Fix:** docling in `all` only; coders
fully exclusive:

```yaml
sets:
  all:        "qg & ne & qw & gt & aa & dl"
  coder_30b:  "qc"     # was "qc & dl"
  coder_next: "qcn"    # was "qcn & dl"
```

Trade-off: docling is evicted when an exclusive coder runs (lpa extraction and
autobuild are now mutually exclusive — acceptable; docling reloads fast).

**Bug 2 (the freeze driver) — keepalive revived ALL configured models.**
`/usr/local/bin/llama-swap-keepalive.sh` enumerated **every** model from
`/v1/models` and fired a `curl max_tokens:1` revive at any not-currently-ready
(parallel background curls, `REVIVE_TIMEOUT=300`). The `MODEL_PROBE_KIND` map
was only used to pick chat-vs-embed probe type, **not** to limit *which* models
were revived. So every 5 min the timer tried to revive the **on-demand** models
too — `qwen-coder-next` (77 GB), `qwen3-coder-30b` (18 GB), docling, architect —
loading the giant coders and flip-flopping the exclusive coder sets. The
orphaned probe curls (launcher exits, curls detach for up to 5 min) overlapped
successive timer fires → continuous coder thrash → unified memory past 121 GB →
**hard freeze**. The script was written (TASK-OPS-7CB1) when every configured
model was meant to be always-running; it never adapted to intentionally
on-demand models.

**Fix:** the keepalive now revives only the **always-on allowlist**
(`MODEL_PROBE_KIND` keys: `qwen-graphiti`, `nomic-embed`, `qwen36-workhorse`,
`gemma4-tutor`); non-allowlisted on-demand models are ignored. Source:
`scripts/llama-swap-keepalive.sh`. Deploy:

```bash
sudo systemctl stop llama-swap-keepalive.timer        # stop the runaway revive-all
sudo cp scripts/llama-swap-keepalive.sh /usr/local/bin/llama-swap-keepalive.sh
sudo systemctl start llama-swap-keepalive.timer       # now safe — core-only revive
```

**Lesson:** a "revive crashed models" keepalive must distinguish *always-on*
from *intentionally-on-demand* models, or it will fight the swap policy and
force-load the heaviest models on a fixed cadence. General rule for this fleet:
the keepalive allowlist must equal the preload set; on-demand models
(coders, docling, architect) are never kept warm by the keepalive.

### 9.5 2026-05-30 — workhorse-for-Graphiti experiment (failed; revert)

**Hypothesis:** point Graphiti at `qwen36-workhorse` (Qwen3.6-35B-A3B, already
resident, `--reasoning off`) instead of `qwen-graphiti` (Qwen2.5-14B-FP8), to
free ~28 GB. Recognised upfront as high-risk per
`docs/reference/graphiti-llm-selection.md` (TASK-REV-DGX1 eliminated the Qwen3
family for Graphiti — thinking-mode timeouts, poor structured JSON).

**Setup (fully reversible):** added an experimental `graphiti-llm-experimental`
alias on workhorse; backed up `.guardkit/graphiti.yaml` and swapped
`llm_model: qwen-graphiti → graphiti-llm-experimental`. qwen-graphiti left
defined and preloaded for instant revert.

**Test 1 — synthetic single-call extraction (PASSED).** Direct
`/v1/chat/completions` with `response_format: json_schema` and a small
entity-extraction prompt: HTTP 200 in **2.77 s**, 156 completion tokens, valid
schema-compliant JSON, 6/6 correct entities, `finish_reason: stop`, **no
`<think>` leak**. `--reasoning off` appears to fully disable thinking-token
generation, and llama.cpp's grammar enforced clean output.

**Test 2 — real Graphiti pipeline (FAILED).**
`guardkit graphiti add-context /tmp/graphiti-workhorse-test.md --type full_doc`
on a small (~250-word) realistic document:

| Metric | Result |
|---|---|
| Wall time | **3 min 33 s** (vs ~30–60 s on qwen-graphiti baseline) |
| OpenAI SDK retries | dozens, with exponential backoff |
| Partial-extraction warnings | `Target entity not found in nodes for edge relation: IS_USED_AS / IS_USED_FOR` |
| Final error | `Episode creation failed: Rate limit exceeded` → `Episode creation returned None (possible silent failure)` |
| Outcome | **0 episodes added, 1 failed** |

**Why the discrepancy.** Graphiti makes multiple concurrent LLM calls per
episode (entity-extract / edge-extract / dedup / summarise) with the full
~7800-token system-prompt overhead. workhorse's `-np 1` slot couldn't absorb
the parallel load — requests queued → llama.cpp returned slow/malformed
responses → the OpenAI SDK interpreted them as 429-style rate-limited,
retried, then ran out of retries. The "rate limit" was synthetic (llama.cpp
doesn't enforce one); it was the SDK reading whatever the server actually
returned under load. Consistent with TASK-REV-DGX1's "Qwen3-Coder-Next >600 s
per episode" finding, just manifested as queueing/retries rather than visible
thinking-token bloat.

**Reverted.** `graphiti.yaml.llm_model → qwen-graphiti`; experimental alias
removed from workhorse; verified `model=graphiti-llm-experimental → HTTP 400`,
`model=qwen-graphiti → HTTP 200`. Box state unchanged.

**Recommendation for the same ~28 GB win:** the **MacBook offload path**
(`docs/reference/graphiti-macbook-offload.md`, commented ollama stub already
present in `graphiti.yaml`) is the lower-risk route. It runs the **proven
Qwen2.5-14B** on the M2 Max, freeing the full 28 GB on the GB10 with no
quality gamble. Graphiti ingestion is async/background, so the Tailscale
latency is acceptable. The workhorse-consolidation route would require raising
workhorse's `-np` to absorb Graphiti's concurrency (~4 slots) — that adds
significant KV memory and may regress the jarvis/forge workloads workhorse
was tuned for; not worth pursuing.

### 9.6 2026-05-30 — workhorse-for-Graphiti retry with `-np 2` (failed; root cause unresolved)

After §9.5 surfaced that the §9.5 failure was likely request queueing not model
quality (single-call structured-extraction passed clean in 2.77 s), and the
user noted that the MacBook offload was non-viable in practice (the M2 Max
fans/thermals under sustained Graphiti load are unusable), we attempted a
conservative retry: bump workhorse to handle Graphiti's parallel extraction
load directly.

**Config attempted** (`/opt/llama-swap/config/config.yaml` + `graphiti.yaml`):

```yaml
"qwen36-workhorse":
  --ctx-size 196608   # was 131072, keeps per-slot ≥98K at -np 2 for autobuild
  -np 2               # was 1
  concurrencyLimit: 4 # was 2

# graphiti.yaml
chunk_extraction_concurrency: 2   # was 8, matches workhorse -np
llm_model: graphiti-llm-experimental   # workhorse alias
```

**Standalone load fits and works.** A direct `llama-server ... -np 2
--ctx-size 196608` run, with the GPU empty (`/unload` first, 116 GB free),
loaded cleanly in ~120 s with the expected footprint:

| Component | Size |
|---|---|
| Model weights (CUDA0) | 20 798 MiB |
| KV cache (96 K cells, 10 attn layers, 2/2 seqs) | **3 840 MiB** |
| Recurrent state (mamba/SSM, 40 layers, 2 seqs) | 125 MiB |
| Compute buffer (CUDA0 + Host) | 2 772 MiB |
| **Total projected device** | **~26.7 GB** (only +0.5 GB vs `-np 1` — Qwen3.6's mostly-mamba/SSM layers have tiny KV state) |

`main: model loaded` / `server is listening` / `chat template, thinking = 0`
all confirmed. Args are valid.

**Under llama-swap, `-np 2` fails deterministically with `exit status 1` in
exactly 5.25 s** — every attempt, regardless of:
- `ctx-size` value (failed at both 196K and the unchanged 131K)
- whether other models were preloaded or `/unload`ed first
- whether triggered by preload, explicit request, or keepalive

Even reverting to `-np 1` while keeping ctx 131K returned workhorse to its
fast-loading proven state. So **`-np 2` itself is the trigger** under
llama-swap's launch environment, not the model args being unfit.

**Hypotheses (none confirmed):** llama-swap captures child stderr but the
useful diagnostic output never surfaces in `llama-swap.log` because the
process exits before producing it. Speculation: some CUDA-context interaction
on the GB10 unified-memory pool that's sensitive to launch env (no TTY, Go
parent process), where `-np 2`'s second-slot allocation hits something that's
fine when launched from an interactive shell. Could also be llama-swap-side
(e.g. a startup timeout shorter than the `healthCheckTimeout: 600` global
that only manifests with the longer load path `-np 2` produces). Resolving it
needs upstream investigation (llama-swap issue tracker + llama.cpp logs with
debug verbosity) outside the scope of this incident.

**Reverted.** workhorse → original `--ctx-size 131072 -np 1 concurrencyLimit:
2`; `graphiti-llm-experimental` alias removed; `graphiti.yaml` →
`llm_model: qwen-graphiti`, `chunk_extraction_concurrency: 8`. Verified:
4-core preload (graphiti + embed + workhorse + tutor) at ~79 GB used /
41 GB free, workhorse warm at 0.39 s, qwen-graphiti reachable.

**Net outcome.** The ~28 GB consolidation isn't viable on the current
GB10 / llama-swap / Qwen3.6-35B-A3B / llama.cpp build without resolving the
`-np 2`-under-llama-swap issue first. Both available routes — workhorse
consolidation (§9.5 + §9.6) and MacBook offload (thermal-impractical per the
user) — are blocked. Sticking with `qwen-graphiti` (Qwen2.5-14B, 28 GB) as
the Graphiti backend; the steady-state stays at the validated ~83 GB
post-§9.4 with ~38 GB headroom. If the 28 GB reclaim becomes important
later: candidate next steps would be (a) test on a newer llama.cpp + llama-
swap combo, (b) try Gemma 4 26B-A4B as a Graphiti backend (not on the
TASK-REV-DGX1 eliminated list — no thinking mode by default, single-instruct
arch), or (c) raise the issue upstream.

### 9.7 2026-05-30 — upgrade to llama.cpp b9430 + llama-swap v219; `-np 2` retest still fails (different signature, same outcome)

After §9.6 surfaced that the GB10-optimised
[`croll83/llama.cpp-dgx`](https://github.com/croll83/llama.cpp-dgx) fork was
**deprecated 2026-05-25** with the maintainer's own note that *"upstream
llama.cpp has surpassed this fork for our target workload,"* and given both
our builds were a month old (llama.cpp `b8954` from Apr 28 with **394
commits** of upstream activity since; llama-swap `v208` from Apr 26 with
**11 releases** since), we executed §9.6's candidate next step (a): upgrade
both.

**Upgrade procedure** (no disruption to the running stack until the swap):

```bash
# llama.cpp: build in a side worktree, swap by config path
git -C /home/richardwoollcott/llama.cpp worktree add /home/richardwoollcott/llama.cpp-new origin/master
cd /home/richardwoollcott/llama.cpp-new
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DGGML_NATIVE=ON -DGGML_CUDA_FA=ON -DGGML_CUDA_COMPRESSION_MODE=size
cmake --build build --target llama-server -j 20    # ~8 min, auto-detects CMAKE_CUDA_ARCHITECTURES=121a-real
# then in config.yaml, sed replace /home/.../llama.cpp/build/bin/llama-server → /home/.../llama.cpp-new/build/bin/llama-server (6 entries)
systemctl --user restart llama-swap.service

# llama-swap v219 (skip v218 — marked broken)
curl -sSL -o /tmp/llama-swap-v219.tgz https://github.com/mostlygeek/llama-swap/releases/download/v219/llama-swap_219_linux_arm64.tar.gz
tar -xzf /tmp/llama-swap-v219.tgz -C /tmp/llama-swap-v219
sudo rm /usr/local/bin/llama-swap                  # unlink-then-cp avoids "Text file busy"
sudo cp /tmp/llama-swap-v219/llama-swap /usr/local/bin/llama-swap
systemctl --user restart llama-swap.service
```

**Upgrade outcome — clean win on stability/hygiene.** All 4 core models came
up on the new stack, warm-respond <600 ms (graphiti 0.47 s, workhorse 0.31 s,
tutor 0.13 s, embed 0.16 s). Memory at the same ~80 GB / ~40 GB free stable
baseline. New llama.cpp builds with **`CMAKE_CUDA_ARCHITECTURES=121a-real`**
auto-detected — that's the Blackwell sm_121-architecture-specific kernels
(including the upstreamed GatedDeltaNet for Qwen3-Next), not the generic
`121-real`. *Definitely worth doing*; the upgrade itself is now baseline.

**`-np 2` retest — still failed, but with a different signature.**

| Stack | Symptom |
|---|---|
| `b8954 + v208` (§9.6) | Workhorse exits with `exit status 1` in **exactly 5.25 s** every attempt |
| `b9430 + v219` (this entry) | Immediate `proxy error: dial tcp 127.0.0.1:5807: connect: connection refused`, then `matrix: running qwen36-workhorse exited: upstream command exited prematurely`, in **~0.5 s** |

The standalone reproduction nails the puzzle:
**`/home/richardwoollcott/llama.cpp-new/build/bin/llama-server` with the
*exact* args llama-swap uses for workhorse (`--port 5897 --host 0.0.0.0
--ctx-size 131072 -np 2 ...`) launched directly from an interactive shell
loads cleanly in ~13 s and binds the port** (`server is listening on
http://0.0.0.0:5897`). Same args, same binary. So the args are valid; the
binary is valid; both versions of llama-swap fail to launch it — *differently*.

The differentiator is the **systemd-user-service launch environment** vs the
interactive shell. The unit (`~/.config/systemd/user/llama-swap.service`) is
`Type=simple` with no explicit limits, but the inherited stack-size limit
differs (`8 MB` for systemd-launched vs `12.5 MB` for the shell) and other
env differences (no TTY, different fd layout, possibly different cgroup
delegation) appear to interact with llama.cpp's `-np 2` slot setup in a way
that causes the child to die before binding. Crucially, **v219 streams *less*
useful info than v208** — no child stderr in the journal, no captured stack —
so further diagnosis needs running llama-swap under strace or hacking the
unit to redirect child stderr separately.

**Reverted to `-np 1` on the upgraded stack.** Steady-state again confirmed:
4 core models loaded, ~66 GB used / ~55 GB free, both workhorse and
qwen-graphiti warm <500 ms.

**Net of §9.5/§9.6/§9.7:** the 28 GB Graphiti reclaim via workhorse-
consolidation is **definitively blocked** on this exact GB10 build + llama-
swap launch environment, irrespective of llama.cpp/llama-swap version.
Future investigation paths if this becomes important again:

1. **strace under systemd:** start a one-off `strace -f -e trace=process` of
   llama-swap's workhorse spawn to capture exactly what signal/error kills
   it, then file upstream with the trace.
2. **Bypass systemd:** run llama-swap from an interactive shell instead of
   the user service (loses auto-restart but proves the systemd-vs-shell
   theory).
3. **Gemma 4 26B-A4B as the Graphiti backend (§9.6 (b)):** still the most
   promising untried path — same arch as `gemma4-tutor` (which already
   works at `-np 1` and we have on disk), no thinking mode, not on the
   TASK-REV-DGX1 eliminated list. Would need its own dedicated llama-swap
   model entry pointed at the existing GGUF, with `-np 4` config matching
   qwen-graphiti's. Decoupled from the workhorse-consolidation problem.

The upgrade is a clean keep regardless of `-np 2` outcome — current state
documented in §1 is now llama.cpp **b9430** at
`/home/richardwoollcott/llama.cpp-new/build/bin/llama-server` (the original
`b8954` at `/home/richardwoollcott/llama.cpp/build/bin/llama-server` is
preserved as fallback) and llama-swap **v219** (`v208` backed up at
`/usr/local/bin/llama-swap.v208.bak`).

### 9.8 2026-05-30 — Gemma 4 as Graphiti backend (failed; revert)

**Trigger.** §9.7 (c) candidate. Runbook
[`gemma4-as-graphiti-experiment-runbook.md`](gemma4-as-graphiti-experiment-runbook.md)
authored on the same day to formalise the experiment. Hypothesis: reuse
the `gemma4-tutor` GGUF (Gemma 4 26B-A4B Q4_K_M, already on disk and
proven under llama-swap at `-np 1`) as a new `gemma4-graphiti` model
entry, with Graphiti-tuned args (`-np 4`, ctx 65 K, temp 0, no Socratic
template), replacing `qwen-graphiti` for a ~7 GB net headroom win.
Decoupled from §9.5–§9.7 (pure attention arch — no mamba/SSM, so the
`-np N` launch failure shouldn't apply).

**What was tested.** Stage-by-stage per the runbook, with two
deviations forced by reality:

- **Stage 1 (standalone smoke) skipped.** Pre-flight showed only ~20 GB
  MemAvailable vs the runbook's expected ~40 GB (qwen36-workhorse's
  131 K-ctx KV had heated up, plus the existing 4-model steady-state ran
  closer to ~85 GB used than the documented ~76 GB). Loading Gemma at
  `-np 4 / ctx 65 K` on the side port would have needed ~16 GB weights +
  several GB KV — tight enough to risk OOM. Skipped to Stage 2 and let
  llama-swap's matrix solver manage eviction.
- **Stage 2 (config add) extended.** The runbook didn't mention
  `matrix.sets`, but llama-swap's solver requires every loadable model
  to belong to some set. Added a new `graphiti_swap: "gg & ne & qw & gt"`
  set alongside the existing `all`, so requesting `graphiti-llm-test`
  picks `graphiti_swap` and evicts `qwen-graphiti` (~28 GB freed for
  the ~21 GB Gemma load). This is realistic — it previews the Stage 6
  end state.

Stages 3 and 4 ran cleanly:

- **Stage 3** PASSED structurally — `gemma4-graphiti` cold-loaded via
  llama-swap in 5.3 s, evicted `qwen-graphiti` as designed, served HTTP 200.
  A schema-constrained JSON entity-extraction probe returned a
  well-formed 5-entity reply (`Apple Inc.`, `Tim Cook`,
  `Cupertino California`, `iPhone`, `MacBook`), 148 completion tokens,
  `finish: stop`, parses cleanly.
- **But Stage 3 also surfaced a hidden risk.** A free-text probe
  (no `response_format`) returned `<|channel>thought\n<channel|>ok` —
  gpt-oss-style thinking-mode markers leaking into content. The
  runbook's claim *"no thinking mode by default ✓ pure instruct"* is
  **wrong**: Gemma 4 26B-A4B's default chat template is a thinking-mode
  template that emits `<|channel>thought\n<channel|>` blocks. The
  existing `gemma4-tutor.jinja` template has the same pattern; it works
  for the tutor because the tutor consumer wants/parses thought blocks.
  Schema-constrained generation (`response_format: json_schema`)
  suppressed the markers via llama.cpp's grammar enforcement; less
  strict modes (`json_object`, free text) did not.

**Stage 5 first run — failed on chat-template alternation.** Wall time
1m30 s, `Added 1 file, 0 episodes. Failed: 1 episode`. Two distinct
errors interleaved:

1. First call: `Expecting value: line 569 column 10 (char 5263)` — model
   returned ~5 KB of mixed content that wasn't parseable as JSON. Likely
   the channel/thinking content prefixing a JSON body.
2. Subsequent retries: HTTP 400
   `Conversation roles must alternate user/assistant/user/assistant/...`.

Root-causing the 400: read
`graphiti_core/llm_client/openai_generic_client.py:198-207` — on error,
graphiti-core **appends another `user` message** to the message list
and retries. So the sequence becomes `[system, user, user]`, which
Gemma's chat template (with its
`{%- if (message['role'] == 'user') != (loop.index0 % 2 == 0) -%}
raise_exception(...) %}` check) rejects.

**Attempted fix: custom permissive non-thinking Gemma template.**
Authored `/opt/llama-swap/config/gemma4-graphiti.jinja` — a fork of
`gemma4-tutor.jinja` that:
- Removes the strict alternation check (any role sequence permitted).
- Removes the `<|channel>thought\n<channel|>` wrapping from both the
  per-turn model header and the generation prompt.

Wired it via `--chat-template-file` on the `gemma4-graphiti` entry,
forced a reload, re-ran the smoke probes:
- `[system, user, user]` now returns HTTP 200 ✓ (alternation fixed).
- But the free-text probe still returned
  `<|channel>thought\n<channel|>ok` — **the markers are baked into the
  weights, not just the template**. The model is trained to start
  responses with `<|channel>thought\n<channel|>` even without a
  template-supplied generation prompt. The template can't suppress what
  the weights emit. The runbook's "no thinking mode by default" claim is
  not template-fixable.

**Stage 5 second run — failed differently, more conclusively.** Wall
time **10m01 s (timed out)**, `Added 1 file, 0 episodes`. Failure mix:

- `Error in generating LLM response: Expecting value: line 1 column 4146
  (char 4145)` — first call still returns ~4 KB of non-JSON content
  (the channel markers + thinking text). This is a `json_object`
  call (no Pydantic model passed → graphiti-core's default
  `response_format`); llama.cpp's `json_object` enforcement is less
  strict than `json_schema` and lets the channel prefix through.
- `LLM did not return resolutions for IDs: [1, 2, 3, 4]` — node dedup
  call returned output that didn't include expected ID resolutions.
- `LLM returned invalid duplicate_facts idx values [0, 3, 5, 7] (valid
  range: 0--1 for EXISTING FACTS)` — edge dedup call **hallucinated
  index values outside the valid range**. The model isn't following
  Graphiti's expected output semantics.
- Final: `Episode creation timed out after 600s`.

**Reverted per runbook §6.** Restored `.guardkit/graphiti.yaml` from
`.bak-2026-05-30-gemma4-test`, removed the `gemma4-graphiti` entry and
the `graphiti_swap` matrix.set from `/opt/llama-swap/config/config.yaml`
(backup at `config.yaml.bak-2026-05-30-pre-gemma4-graphiti`). Left the
orphan `gemma4-graphiti.jinja` on disk as a historical record. Hot-reload
fired, preload recovered the original 4-model set, baseline restored:
`free -g` shows ~84 GB used / 37 GB free, `qwen-graphiti` HTTP 200 in
0.49 s.

**Outcome (numbers).**

| Probe | Stage 3 (smoke) | Stage 5 #1 (default template) | Stage 5 #2 (custom template) |
|---|---|---|---|
| HTTP outcome | 200 | 400 alternation + JSON parse errors | no HTTP errors; pipeline timeout |
| Wall time | 5.3 s cold load | 1m30 s fast-fail | 10m01 s timeout |
| Episodes ingested | n/a | **0 / 1** | **0 / 1** |
| Specific failure | channel markers in free text | retry → `[system,user,user]` → 400 | weights emit `<|channel>thought\|>`; dedup hallucination |

**Net memory delta committed:** **0 GB** (experiment reverted). No
keepalive allowlist change (gemma4-graphiti was never promoted to
preload, so it was never in the allowlist).

**Updated guidance.** Gemma 4 26B-A4B is **not suitable** as a Graphiti
backend. Three distinct blockers, listed in order of how
template-fixable they are:

1. **Strict chat-template alternation** (template-fixable — see
   `gemma4-graphiti.jinja`). Graphiti's `[system, user, user-on-retry]`
   pattern requires a permissive template.
2. **Thinking-mode `<|channel>thought\n<channel|>` markers baked into
   weights** (NOT template-fixable). Suppressed only by
   `response_format: json_schema` (llama.cpp grammar enforcement);
   leaks through `json_object` and free text. graphiti-core uses
   `json_object` whenever a caller doesn't supply a `response_model`,
   so the leak hits real production calls.
3. **Hallucinated dedup IDs** (NOT fixable without retraining /
   different model). Even with grammar-enforced output, the model
   doesn't track Graphiti's `EXISTING FACTS` index space correctly —
   returns indices outside the valid range. This alone is a hard
   disqualifier for any merge/dedup-heavy workflow.

`docs/reference/graphiti-llm-selection.md` should be amended to add
Gemma 4 26B-A4B (and by extension the Gemma 4 family's thinking-mode
variants) to the eliminated list, with reasons (2) and (3) cited.

After §9.5–§9.8, the §9.7 candidate path inventory now reads:
**(a) Qwen3-4B-Instruct-2507 small-model retry** — untried, low
priority (TASK-REV-DGX1 already eliminated the 4B class for Graphiti
quality); **(b) keep qwen-graphiti at 28 GB** — current state, accepted;
**(c) Gemma 4 26B-A4B** — disqualified by §9.8; **(d) cloud Gemini /
GPT-4o-mini** — untried, paid (£10/day documented in
`graphiti.yaml` comments). No remaining local-LLM path that meaningfully
moves the memory budget.

### 9.9 2026-05-30 — drop `qwen-coder-next`; rotate preload tutor→architect; add `tutor` matrix.set

**Trigger.** Memory-budget review following §9.8. The user asked whether
`qwen-graphiti + nomic-embed + qwen36-workhorse + qwen-coder-next` could
co-reside (autobuild Player on workhorse, dedicated Coder on coder-next,
Graphiti hot). The math said no: ~28 + 2 + 30 + 90 = **~150 GB** vs the
~115 GB effective budget. Per §9.2, coder-next is exclusive — it cannot
share. Every GuardKit command that captures to Graphiti
(`/feature-spec`, `/system-arch`, `/system-design`, `/task-work` outcome
write, `/task-complete` rollup) would block during any autobuild run
that used coder-next.

Two follow-up questions surfaced from that analysis:

1. **Is coder-next actually worth the operational tax?** Forum research on
   the NVIDIA DGX Spark GB10 category turned up direct comparative data
   between coder-next and the workhorse-class Qwen3.6 family:
   - **AgentBench**: Qwen3.6 27B = **59.3%**, Qwen3-Coder-Next = **46.0%**.
     The workhorse-class *beats* coder-next on agent benchmarks — exactly
     the workload autobuild's Player↔Coach loop is.
     ([forum thread][f-agent])
   - User reports: *"coder-next get stuck in a few things and 122B fixes
     it at once"*, *"I default to 35B most of the times"* (same thread,
     azampatti). Coder-next has reasoning bottlenecks in agent loops.
   - Single-stream gen speed: coder-next ~43–45 t/s, workhorse-class
     ~31–32 t/s — a real but modest ~1.3–1.5× speedup, not the 10×
     suggested by the often-misquoted 483 t/s figure (which is *batch*
     throughput at c=32+, not single-stream).
     ([HOW-TO thread][f-howto], [perf thread][f-perf])
   - Quantization alternatives don't escape the memory floor: NVFP4
     "couldn't find one that works" on GB10; AWQ allocation errors
     reported. FP8 at ~92 GB resident is the only viable path.
     ([quant thread][f-quant], [cluster thread][f-cluster])

2. **Why have a dedicated autobuild coder at all?** The current config
   already routes autobuild's Player and Coach to `qwen36-workhorse`
   via the `autobuild-player` and `coach` aliases — coder-30b and
   coder-next are *opt-in* via `--model autobuild-coder` /
   `--model autobuild-coder-next`. The default path doesn't need them.

**Decision.** Drop `qwen-coder-next` entirely; keep `qwen3-coder-30b` as
an on-demand opt-in alternative; rotate the always-on preload set so
`architect-agent` (Gemma 4 26B-A4B with the thinking template, used by
`/system-arch` / `/system-design` / `/arch-refine` / `/system-plan`)
takes `gemma4-tutor`'s slot; create a dedicated `tutor` matrix.set so
tutor sessions load on-demand.

**New layout (post-change).**

| Set | Members | Resident (GB, approx) | When |
|---|---|---:|---|
| `all` (default) | qg + ne + qw + aa + dl | ~80 (dl loads on demand) | always-on |
| `tutor` | gt + qw | ~45 | on first `study-tutor` request; auto-unload after 30 min idle |
| `coder_30b` | qc | ~22 | on first `autobuild-coder` request; evicts the family |

Preload list rotated: `gemma4-tutor` → `architect-agent`. Tutor's TTL
flipped `0` → `1800`; architect's TTL flipped `1800` → `0`.

**Keepalive script update.** `MODEL_PROBE_KIND` in
`scripts/llama-swap-keepalive.sh` swapped `gemma4-tutor` →
`architect-agent` to match the new preload set. The keepalive MUST equal
the preload set or §9.4-class incidents recur. Deployed via:

```bash
sudo cp scripts/llama-swap-keepalive.sh /usr/local/bin/llama-swap-keepalive.sh
```

**Operational caveat for tutor sessions.** The `tutor` matrix.set does
not contain `qg`/`ne`/`aa`. When the keepalive fires (5-min cadence) it
probes `qwen-graphiti` (in `all` only), causing the solver to switch
from `tutor` back to `all`, evicting `gemma4-tutor` mid-session. Two
mitigations:

- **Short turns** (under 5 min between user messages) won't notice — the
  tutor reloads on the next message in ~8 s (warm-cache cold reload).
- **Long sessions** should pause the timer first:
  ```bash
  sudo systemctl stop llama-swap-keepalive.timer
  # ...tutor session...
  sudo systemctl start llama-swap-keepalive.timer
  ```

This is the same discipline that §9.2 documented for coder-next, applied
sparingly because tutor sessions are interactive and recoverable.

**Verified (2026-05-30).** Hot-reload picked up the change. New preload
healthy: qg + ne + qw + aa, all probes HTTP 200 in <1 s, memory steady
at ~88 GB used / ~33 GB available. Tutor-mode switch verified:
`set=tutor dsl="gt & qw" evict=[architect-agent nomic-embed qwen-graphiti]
target=[gemma4-tutor qwen36-workhorse] cost=3`, cold load 8.3 s, memory
drops to ~57 GB used / ~63 GB free. Switch-back to `all` on next graphiti
request: `set=all evict=[gemma4-tutor]`, qg responds, memory returns to
the always-on baseline.

**Net memory delta committed.** No always-on RAM change (preload set
same size, architect's ctx 65 K adds ~5 GB KV vs tutor's ctx 32 K, so
~80 GB vs prior ~76 GB). **Disk reclaim potential: 75 GB** in the
`~/.cache/huggingface/hub/models--Qwen--Qwen3-Coder-Next-FP8` cache —
left in place pending an explicit decision to reclaim, so restoration
remains zero-download.

#### Restoration recipe — putting `qwen-coder-next` back

Three artifacts needed; all preserved:

1. **Launch script** — `/opt/llama-swap/scripts/vllm-coder-next.sh`
   (left in place, unchanged).
2. **HF cache** — `~/.cache/huggingface/hub/models--Qwen--Qwen3-Coder-Next-FP8`
   (75 GB, left in place).
3. **Config block** — captured below for re-insertion into
   `/opt/llama-swap/config/config.yaml`:

```yaml
# 2026-05-28 (TASK-HMIG-009A): on-demand vLLM-served Qwen3-Coder-Next-FP8.
# UNLIKE every other entry this launches vLLM in Docker (not llama.cpp) via
# /opt/llama-swap/scripts/vllm-coder-next.sh, because Qwen3-Coder-Next ships
# as FP8 safetensors (qwen3next hybrid linear-attention MoE) and the
# delta-net path is CPU-bound/slow under llama.cpp (llama.cpp#19345). vLLM
# FP8 is the proven ~43 tok/s path on GB10 (forum "HOW-TO: Run
# Qwen3-Coder-Next on Spark"); see AUTOBUILD-ON-LLAMA-SWAP-findings.md.
#
# EXCLUSIVE: ~75 GB FP8 weights + KV ≈ ~90 GB resident. The `coder_next`
# matrix.set below holds ONLY this model, so requesting it evicts every
# llama.cpp model, and any family-alias request evicts this. Sequential by
# design (DECISION-DF-001 concurrency analysis) — it cannot co-reside with
# the study tutor under the 121 GB ceiling.
#
# BEFORE LOADING: pause the keepalive timer
#   sudo systemctl stop llama-swap-keepalive.timer
# (its 5-min family-revive probe would evict coder-next mid-build), check
# `free -g`, and `curl :9000/unload` if the family is resident. Use via
#   guardkit autobuild task TASK-XXX --model qwen-coder-next
"qwen-coder-next":
  cmd: /opt/llama-swap/scripts/vllm-coder-next.sh ${PORT}
  cmdStop: docker stop vllm-coder-next
  checkEndpoint: /health
  ttl: 600                 # on-demand: auto-unload the ~77 GB beast after 10 min idle
  concurrencyLimit: 2
  aliases:
    - "autobuild-coder-next"
```

Plus three matrix re-edits:

```yaml
matrix:
  vars:
    ...
    qcn: qwen-coder-next   # re-add
    ...
  sets:
    ...
    coder_next: "qcn"      # re-add
```

After the edits, hot-reload picks up the entry within ~5 s. Verify with:
`curl -s http://localhost:9000/v1/models | python3 -c "import sys,json;
print('qwen-coder-next' in [m['id'] for m in json.load(sys.stdin)['data']])"`.

To **fully reclaim** the 75 GB disk (if you decide coder-next won't be
restored), the only additional step is:
`rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen3-Coder-Next-FP8`.

#### Pointers

- [Forum: For local Agent, QWEN3.6 35B OR QWEN3-CODER-NEXT?][f-agent]
- [Forum: HOW-TO Run Qwen3-Coder-Next on Spark][f-howto]
- [Forum: Which quantization for Qwen3-Coder-Next 80B][f-quant]
- [Forum: Does Qwen3.5-35B-A3B on GB10 leave performance on the table?][f-perf]
- [Forum: Issues with qwen3 coder next on dual node cluster][f-cluster]
- §9.2: original coder-next adoption
- §9.4: keepalive ↔ exclusive-set ping-pong (the failure mode this avoids)
- §9.8: gemma4-as-graphiti experiment (failed; companion experiment in the same memory-budget exercise)

[f-agent]: https://forums.developer.nvidia.com/t/for-loacl-agent-qwen3-6-35b-or-qwen3-coder-next/367721
[f-howto]: https://forums.developer.nvidia.com/t/how-to-run-qwen3-coder-next-on-spark/359571
[f-quant]: https://forums.developer.nvidia.com/t/which-quantization-should-i-pick-for-qwen3-coder-next-80b-to-run-on-a-single-dgx-spark/360600
[f-perf]: https://forums.developer.nvidia.com/t/does-qwen3-5-35b-a3b-on-gb10-leave-a-lot-of-performance-on-the-table/362200
[f-cluster]: https://forums.developer.nvidia.com/t/issues-with-qwen3-coder-next-on-dual-node-cluster/362767

### 9.10 2026-05-30 — register `granite-vision-4-1-4b` for the LPA platform; add `lpa` matrix.set

**Trigger.** `lpa-platform-poc/docs/history/lpa-extraction-e2e-smoke-4.md`
AC-009: the LPA POC's planned swap from `granite-docling-258M` to
`ibm-granite/granite-vision-4.1-4b` (Option 3 — ~16× more params, designed
for general document understanding) was blocked because the routable id
was not yet served by the GB10's llama-swap. Repo-side prep had landed
(prompt seam in `src/lpa/clients/docling.py`); the model swap + smoke
test could not run until granite-vision was advertised on `/v1/models`
and routed on `/chat/completions`.

User asked for "a configuration for the lpa platform with Qwen3.6
workhorse and granite-vision-4.1-4b" — meaning both: register the model
in llama-swap, and document the LPA-shaped layout (vision + workhorse).

**Two adaptations from the LPA runbook in the source doc.**

1. **Image: `vllm/vllm-openai:cu130-nightly`, NOT NGC `26.01-py3`.** The
   LPA runbook suggested NGC, which was the same starting point that
   docling-258M used and ran into in §9.3: NGC's older cuDNN fails the
   idefics2/3 vision encoder's `F.conv2d` patch embedding on Blackwell
   sm_121 with *"GET was unable to find an engine to execute this
   computation"*. The cu130-nightly image (vLLM 0.18, torch 2.10+cu130,
   cuDNN 9.15) runs the conv fine. Granite Vision shares the same vision
   encoder family as Granite Docling, so the same lesson applies.
2. **GPU util `0.12`, NOT `0.40`.** The LPA runbook suggested 0.40
   (~50 GB allocation), which is wasteful for a 4B bf16 model. 0.12
   (~15 GB) covers weights (~8 GB) + KV at max-len 8192 × max-num-seqs 4
   (~2-3 GB) + activations (~1-2 GB) with headroom. Bumpable via
   `VLLM_GV_GPU_UTIL` if real LPA load shows KV pressure.

**What landed.**

- **`/opt/llama-swap/scripts/vllm-granite-vision.sh`** — new launch
  script, mirrors the `vllm-docling.sh` pattern (vLLM in Docker under
  llama-swap so one memory manager owns the unified pool — avoids the
  KV-cache profiling clash from §9.3). Container name
  `vllm-granite-vision`. `HF_HUB_OFFLINE` deliberately NOT set so the
  first load can download the ~8 GB weights; remove after first load if
  desired. Three served-model-names registered: `granite-vision-4-1-4b`
  (entry key — listed in `/v1/models`), `granite-vision-4.1-4b` (HF
  model id), and bare `granite-vision`.
- **`/opt/llama-swap/config/config.yaml`** — new `granite-vision-4-1-4b`
  entry (`ttl: 1800`, `concurrencyLimit: 4`, aliases match the
  served-model-names). New matrix var `gv` added to `matrix.vars`.
  `gv` included in `all` (loads on-demand alongside the family — total
  ~95 GB when loaded), plus a new dedicated `lpa: "gv & qw & ne"` set
  (~42-45 GB) for memory-constrained LPA runs.

**Layout (post-change).**

| Set | Members | Resident (GB, approx) | When |
|---|---|---:|---|
| `all` (default) | qg + ne + qw + aa + dl + gv | ~80 always-on; +11 if docling loaded; +12-15 if vision loaded | always-on family + on-demand vision/docling co-resident |
| `tutor` | gt + qw | ~45 | on first `study-tutor` request |
| `lpa` | gv + qw + ne | ~42-45 | when memory pressure forces a smaller layout; otherwise gv loads in-place within `all` |
| `coder_30b` | qc | ~22 | on first `autobuild-coder` request |

**Co-residency caution.** Docling + granite-vision both loaded
simultaneously with the family hits ~108 GB resident, close to the
~115 GB safe ceiling. The LPA POC's migration replaces docling with
vision, so this is a transitional concern: avoid invoking both VLMs
back-to-back during the cutover window. After the migration completes,
docling can be removed (entry, var, and set member) for a cleaner setup.

**LPA POC AC-009 status (cleared step 4a; 4b pending first load).**

- **Step 4a (catalogue check):** ✅ cleared.
  `curl http://promaxgb10-41b1:9000/v1/models | jq '.data[].id'` now
  returns `granite-vision-4-1-4b` in the list. The two aliases
  (`granite-vision-4.1-4b` and bare `granite-vision`) route on
  `/chat/completions` but don't appear in `/v1/models` — same behavior as
  `granite-docling` and consistent with the LPA02-A gotcha called out in
  the source runbook (the displayed id is the routable one; aliases
  route but aren't listed).
- **Step 4b (chat-completions smoke against a real LPA page):** ⏳
  deferred. The first chat-completions request will trigger a ~8 GB
  download of the granite-vision weights to
  `~/.cache/huggingface/hub/models--ibm-granite--granite-vision-4.1-4b`,
  then vLLM cold-start (~30-90 s), then serve the request. This is the
  LPA team's smoke (it needs a real PDF page from the LPA test corpus),
  not part of this infra change. Recommended: do the first load against
  a stable memory state (no concurrent model swap) — same constraint
  docling has, per §9.3.

**Routable id to set in `DOCLING_VLM_MODEL`.** Any of these will route:

- `granite-vision-4-1-4b` (the id shown in `/v1/models` — pick this
  if you want the routable id to match the listed id exactly)
- `granite-vision-4.1-4b` (the HF model name — matches what
  `lpa-platform-poc/docs/history/lpa-extraction-e2e-smoke-4.md`
  suggested)
- `granite-vision` (short alias)

**Keepalive note.** `granite-vision-4-1-4b` is on-demand and MUST NOT be
added to `scripts/llama-swap-keepalive.sh`'s `MODEL_PROBE_KIND` — same
rationale as docling, coder-30b, and tutor. The keepalive allowlist
remains the 4 always-on (qg, ne, qw, aa). Probing gv would auto-trigger
the 8 GB download every 5 min until cached, then auto-load it every 5
min thereafter — defeating the on-demand intent.

**Verified (2026-05-30).** Hot-reload picked up the change. New entry
listed in `/v1/models`. Always-on preload unaffected (qg + ne + qw + aa
all health-checked OK after reload). Memory steady at ~81 GB / ~39 GB
free. Did NOT trigger the first cold load — leaving that for the LPA
team's smoke run with a real test PDF.

#### Pointers

- [`lpa-platform-poc/docs/history/lpa-extraction-e2e-smoke-4.md`][lpa]
  — source runbook (AC-009 unblocker)
- §9.3 — original docling NGC vs cu130 lesson (same cuDNN/sm_121 issue
  applies to granite-vision)
- §9.9 — preceding change (preload rotation, coder-next removal) — this
  is the next addition to the same matrix-config evolution

[lpa]: ../../../../lpa-platform-poc/docs/history/lpa-extraction-e2e-smoke-4.md

### 9.11 2026-05-30 — granite-vision-4-1-4b actually-working config (vLLM v0.22.0; `lpa` set is mutually exclusive)

**Trigger.** §9.10's initial config didn't work. LPA team's smoke (step 4b)
reported vLLM crashing when llama-swap tried to start vllm-granite-vision.
Investigation surfaced THREE distinct problems with the §9.10 design,
each fixed:

#### Problem 1: `--limit-mm-per-prompt image=1` rejected by newer vLLM

**Symptom.**
```
vllm serve: error: argument --limit-mm-per-prompt:
  Value image=1 cannot be converted to <function loads at 0x...>
```

**Cause.** vLLM changed the format of `--limit-mm-per-prompt` from
`key=value` shorthand to JSON. The LPA runbook
(`lpa-extraction-e2e-smoke-4.md`) was written for an older vLLM. New vLLM
accepts either:
- JSON: `--limit-mm-per-prompt '{"image": 1}'`
- Dotted CLI form: `--limit-mm-per-prompt.image=1`

**Fix.** Updated `vllm-granite-vision.sh` to use the dotted form (avoids
shell-quoting headaches in the heredoc-like `exec docker run`).

#### Problem 2: cu130-nightly image (vLLM 0.18.1rc1) doesn't natively support `Granite4VisionForConditionalGeneration`

**Symptom.** After fixing problem 1, vLLM started, downloaded the model
(~6 GB), then EngineCore crashed with:
```
ValueError: There is no module or parameter named 'image_newline' in
TransformersMultiModalForCausalLM.
```

**Cause.** Granite Vision 4.1 uses the
`Granite4VisionForConditionalGeneration` architecture (introduced for the
4.1 family). Native vLLM support was added in v0.21+. Our cu130-nightly
image had v0.18.1rc1 — too old. It fell back to
`TransformersMultiModalForCausalLM` (the generic Transformers backend),
which doesn't know about the `image_newline` parameter the 4.1 model
ships with. Cause confirmed via vLLM docs: *"Granite Vision 4.1 is
supported natively in vLLM as of v0.21.0"*.

**Fix.** Pulled `vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404`
(31 GB image, released 2026-05-29). Re-ran the granite-vision serve —
log now shows:
```
INFO [model.py:617] Resolved architecture: Granite4VisionForConditionalGeneration
INFO: Application startup complete.   (at 106 s)
```

Native impl, not Transformers fallback. Updated `vllm-granite-vision.sh`
default image to v0.22.0. The cu130-nightly image is **kept** as the
default for `vllm-docling.sh` — docling doesn't need vLLM v0.21+ and is
on a known-good cuDNN. Per-script image scoping; do not synchronise.

#### Problem 3: actual memory footprint is ~26 GB, not the estimated ~12-15 GB

**Symptom.** With granite-vision loaded alongside the always-on family
(qg + ne + qw + aa ~80 GB), `free -h` showed **114 GB used / 7 GB free,
11 GB swap**. A text-only chat-completion test timed out at 30 s —
almost certainly swap-thrash-induced. This is right at the §9.4 freeze
threshold.

**Cause.** Initial estimate (12-15 GB) was based on
`gpu-memory-utilization 0.12` ≈ 15 GB allocated KV cache. But on unified
memory, the vLLM process also consumes substantial system memory for:
- bf16 weights (~8 GB)
- Vision encoder + spatial/layerwise projectors (Granite4Vision's
  qformer scaffolding adds noticeable Python-side state)
- Image processor / multi-modal pipeline state
- vLLM Python process overhead (torch import, CUDA contexts, etc.)
- Activation buffers during model load

Measured delta on this hardware: **~26 GB** with `gpu-memory-utilization
0.12, max-model-len 8192, max-num-seqs 4`. Even with aggressive trimming
(util 0.08, max-len 4096, max-seqs 2), co-residency with the family
would land near the freeze line — not worth the risk.

**Fix.** **Removed `gv` from the `all` matrix.set; left it in `lpa`
only.** Requesting `granite-vision` now triggers a switch to the `lpa`
set (`gv & qw & ne`), evicting qg + aa + dl, keeping qw + ne, loading
gv. Total resident: ~56 GB, well under the safe ceiling. After ttl 1800
idle, gv unloads and the next probe revives the family.

This makes granite-vision a **mutually-exclusive workload** like the
(removed) qwen-coder-next — Graphiti is unavailable during LPA runs.
That's acceptable because LPA pipeline output is captured by the LPA
POC's own storage (not Graphiti), and LPA runs are bounded discrete
sessions, not continuous background work.

**Operational note.** A long LPA session needs the keepalive paused
(`sudo systemctl stop llama-swap-keepalive.timer`) to prevent the
5-min qg/ne/qw/aa probe cycle from evicting gv mid-session. Same
discipline §9.2 documented for coder-next.

#### Final working config (verified 2026-05-30)

```yaml
# /opt/llama-swap/config/config.yaml
"granite-vision-4-1-4b":
  cmd: /opt/llama-swap/scripts/vllm-granite-vision.sh ${PORT}
  cmdStop: docker stop vllm-granite-vision
  checkEndpoint: /health
  ttl: 1800
  concurrencyLimit: 4
  aliases:
    - "granite-vision-4.1-4b"
    - "granite-vision"

matrix:
  vars:
    gv: granite-vision-4-1-4b   # only member of `lpa`
  sets:
    all: "qg & ne & qw & aa & dl"   # gv NOT here
    lpa: "gv & qw & ne"             # mutually exclusive with `all`
```

```bash
# /opt/llama-swap/scripts/vllm-granite-vision.sh — key changes vs §9.10
IMAGE="${VLLM_GV_IMAGE:-vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404}"
# ...
--limit-mm-per-prompt.image=1   # not 'image=1'
```

**LPA POC AC-009 status (re-checked 2026-05-30 post-fix).**

- **Step 4a (catalogue check):** ✅ still cleared
  (`granite-vision-4-1-4b` in `/v1/models`).
- **Step 4b (chat-completions smoke against a real LPA page):** ⏳
  pending — the failed text-only test was a memory-pressure timeout
  under the bad config; the LPA team's actual smoke (image_url POST
  against an LPA page) hasn't been re-attempted since the fixes.
  Recommended workflow:
  1. Optionally pause keepalive if the session will be long.
  2. POST chat-completions with
     `{type:image_url, image_url:{url:"data:image/png;base64,..."}}`.
  3. First request triggers cold-load via the v0.22.0 image (~110 s) and
     the `lpa` matrix.set switch (qg+aa+dl evicted, gv+qw+ne resident).
  4. Subsequent requests within the 30-min ttl window are warm.
  5. After the session, the next qg/ne/qw/aa probe (keepalive or
     explicit) auto-evicts gv and revives the family.

**Memory footprints (corrected from §9.10).**

| Mode | Resident | Headroom |
|---|---:|---:|
| `all` only (always-on) | ~80 GB | ~40 GB |
| `all` + granite-vision (NOT recommended — was the original design) | ~106 GB | ~15 GB (§9.4 danger zone) |
| `lpa` (gv + qw + ne) — granite-vision exclusive | ~56 GB | ~65 GB |

**Restoration of §9.10 design (if granite-vision footprint shrinks in
future).** If a future vLLM build measurably reduces granite-vision's
unified-memory cost to ≤15 GB (e.g. via int4 quantization, smaller
multi-modal state, etc.), re-adding `gv` to `all` becomes safe and
brings back on-demand co-residency. To check: load granite-vision alone
under the v0.22.0 image and measure `free -h` delta vs no-gv baseline.
If under 15 GB net, re-add to `all`; if not, leave in `lpa` only.

#### Lessons for future LPA-style vLLM additions

1. **Pin a vLLM image that natively supports the target model.** Falling
   back to `TransformersMultiModalForCausalLM` rarely works for newer
   multi-modal architectures with custom parameters. Check vLLM's
   `Resolved architecture:` line in the log — if it's
   `TransformersMultiModalForCausalLM`, expect failures.
2. **Measure actual resident memory before assuming budget.** On unified
   memory, `gpu-memory-utilization` is a target for KV cache, NOT the
   total process footprint. Add 2-3× headroom to the GPU util setting
   when sizing matrix.sets.
3. **Don't trust runbook arg syntax for newer vLLM.** Format changes
   (e.g., `--limit-mm-per-prompt`) happen between minor versions.
   Verify against `vllm serve --help=<arg-name>` for the chosen image.
4. **Use a dedicated matrix.set for high-footprint on-demand models.**
   The §9.2 coder-next pattern (exclusive set, evicts family) is the
   correct default for anything >20 GB resident, not in-place
   co-residency within `all`.

### 9.12 2026-05-31 — register `granite-vision-3-3-2b` as LPA fallback after 4.1-4b's page-4 EOS collapse

**Trigger.** LPA POC team ran 7 full Ashworth smokes against
`granite-vision-4-1-4b` on 2026-05-31 (see `lpa-platform-poc/docs/
history/lpa-extraction-e2e-smoke-4.md` and `TASK-FIX-LPA02-F` progress
log). Result: AC-001 still 0/0 primary attorneys. Root-caused to a
**1-token EOS collapse** on Ashworth page-4-Section-2 with the prompt
`"Convert this page to markdown."` in greedy decoding (`temperature: 0`).
The collapse is reproducible across vLLM-container restarts (a 165 s
cold call still emitted a single stop-token); adding any token to the
prompt prefix (e.g. `"Please convert this page to markdown."`) unsticks
page 4 in isolation, but every per-page tuning that fixes page 4
degrades enough other pages in the 23-page Docling loop to drop
"Sarah Bennett" from the markdown and net-regress the JSON extraction
(the "per-page tuning → pipeline regression" pattern). The temperature
sweep (Runs E + F) and the max_tokens sweep (Run G) all confirmed.

The team's recommended next step (`smoke-4.md` §"Open questions"
candidate 1): **fall back to `ibm-granite/granite-vision-3.3-2b`** —
different training lineage, may not share the EOS-collapse signature;
also smaller (3B vs 4B) so should help AC-007's 8-min runtime budget.

**What landed.**

- **New launch script** `/opt/llama-swap/scripts/vllm-granite-vision-3-3-2b.sh`
  — mirrors the 4.1-4b script. Uses the same
  `vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404` image (3.3-2b's
  `LlavaNextForConditionalGeneration` arch is universally supported in
  vLLM since v0.4 — the cu130-nightly image would also work, but
  staying on v0.22.0 for consistency with the 4.1-4b setup).
  `gpu-memory-utilization 0.10` (down from 4.1-4b's 0.12; the smaller
  model needs less KV-cache budget). Container name
  `vllm-granite-vision-3-3-2b`.
- **New model entry** in `/opt/llama-swap/config/config.yaml`:
  `granite-vision-3-3-2b` with alias `granite-vision-3.3-2b` (HF model
  id form). `ttl: 1800`. NOT given the bare `granite-vision` alias
  (4.1-4b owns that to avoid ambiguity).
- **New matrix var** `gv33` and **new matrix.set**
  `lpa_v3: "gv33 & qw & ne"` — parallel to the existing
  `lpa: "gv & qw & ne"` (§9.11). Both LPA sets are mutually exclusive
  with `all` AND mutually exclusive with each other (only one vision
  model loads at a time — they're substitutable for the LPA workload).
  The LPA POC picks via `DOCLING_VLM_MODEL` env var on its side. **4.1-4b
  is KEPT registered** as a comparison/rollback option; not removed.
- **Inline comment for the LPA sets** was rewritten to capture both
  (the old §9.10-era comment about "loads in-place within `all`" was
  stale — §9.11 already made it mutually exclusive).

**Verified end-to-end 2026-05-31.** Image-content POST via
`/chat/completions` on `:9000`:

```
HTTP 200 in 353 s (cold load: 6 GB download + vLLM init + image processing)
matrix: model=granite-vision-3-3-2b set=lpa_v3 dsl="gv33 & qw & ne"
        evict=[architect-agent qwen-graphiti]
        target=[granite-vision-3-3-2b nomic-embed qwen36-workhorse]
        cost=2
system_fingerprint: vllm-0.22.0-c935d4d0
```

Coherent response on a 1×1 transparent PNG (model hallucinated trees,
which is normal for empty-image behavior). Switch-back to `all` worked:
qg in 17 s, aa in 17 s (cold reloads — they had been evicted during the
test; warm responses would be sub-second on subsequent probes).

**Measured memory footprint: ~15 GB resident** for `granite-vision-3-3-2b`
under the configured args. Significantly leaner than 4.1-4b's ~26 GB,
matching the smaller parameter count. Memory math during the test:

| Phase | Resident | Used | Free |
|---|---|---:|---:|
| Always-on family before test | qg + ne + qw + aa | ~88 GB | ~33 GB |
| `lpa_v3` after cold load | gv33 + qw + ne | ~53 GB | ~68 GB |
| After switch-back to `all` | qg + ne + qw + aa | ~88 GB | ~33 GB |

`lpa_v3` is **comfortably under the 115 GB safe ceiling** with ~65 GB
headroom — the leanest mutually-exclusive set in the matrix.

**LPA POC AC-009 status (for the 3.3-2b variant).**

- **Step 4a (catalogue check):** ✅ `granite-vision-3-3-2b` advertised in
  `/v1/models`.
- **Step 4b (chat-completions smoke):** ✅ generic 1×1-PNG smoke passed.
  The LPA team's real-page smoke against Ashworth pages 1–23 is the next
  step on their side — set `DOCLING_VLM_MODEL: granite-vision-3-3-2b`
  in `docker-compose.poc.yml` and re-run `_smoke_lpa_extraction.py`.
- **Routable id:** `granite-vision-3-3-2b` (listed) or alias
  `granite-vision-3.3-2b` (routes but not listed — same LPA02-A gotcha
  pattern; safer to use the listed id).

**Operational caveat.** Same as `lpa`/4.1-4b: long LPA sessions need
the keepalive paused — see [`llama-swap-keepalive-start-stop.md`](./llama-swap-keepalive-start-stop.md)
"When to pause keep-alive — `lpa`" (also applies to `lpa_v3`).

**What this leaves available.** Both LPA vision models are now registered
and selectable per-environment via `DOCLING_VLM_MODEL`:

| Model | Resident | Set | Use when |
|---|---:|---|---|
| `granite-vision-4-1-4b` | ~26 GB | `lpa` | Comparison / rollback / future re-attempt with prompt-per-page workaround |
| `granite-vision-3-3-2b` | ~15 GB | `lpa_v3` | LPA POC current default — fallback per smoke-4 evidence |

If 3.3-2b also fails the LPA acceptance tests, the runbook's next
candidates (per `smoke-4.md`) are non-IBM VLMs (Qwen2.5-VL-7B,
Pixtral-12B) or escalation to Option 2 (StandardPdfPipeline / pure OCR
via Docling's traditional pipeline). Both would require fresh
registration work on the GB10 side.

#### Pointers

- [`lpa-platform-poc/docs/history/lpa-extraction-e2e-smoke-4.md`](../../../../lpa-platform-poc/docs/history/lpa-extraction-e2e-smoke-4.md)
  — 7-run Ashworth evidence + root-cause analysis
- [`lpa-platform-poc/tasks/backlog/TASK-FIX-LPA02-F-swap-vlm-to-granite-vision-4-1-4b.md`](../../../../lpa-platform-poc/tasks/backlog/TASK-FIX-LPA02-F-swap-vlm-to-granite-vision-4-1-4b.md)
  §"Progress log" — repo-side seam evolution + recommendation
- §9.10 / §9.11 — granite-vision-4-1-4b registration history
- README "On-demand models" + "Matrix sets" tables — both updated to
  include gv33 / lpa_v3

---

## 10. Provenance

This document captures findings from an interactive session on
2026-05-14 attempting to set up `guardkit autobuild` against
Qwen3.6-workhorse, then Qwen3-Coder-30B, on llama-swap for DDD South
West 2026 demo prep. Two GB10 OOM freezes occurred during the session;
both root-caused to concurrent residency of workhorse + coder + 3
other models. Final state: original 5-model preload restored, coder
defined as opt-in, autobuild recommended to run on Anthropic for the
demo.

Related task plans: `tasks/backlog/dddsw-demo/TASK-DEMO-D5DD-version-short-flag.md`
(the purpose-built demo task used as the smoke-test target).
