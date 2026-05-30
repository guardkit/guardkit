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
