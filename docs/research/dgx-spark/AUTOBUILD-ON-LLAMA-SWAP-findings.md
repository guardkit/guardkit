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
