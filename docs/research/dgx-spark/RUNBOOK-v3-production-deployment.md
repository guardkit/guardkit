# Runbook v3: Production Deployment — All-llama.cpp via llama-swap

**Purpose:** Deploy the validated all-llama.cpp architecture into production. Four models permanently loaded behind llama-swap on :9000. Zero vLLM dependency. Zero model swapping.

**Machine:** Dell DGX Spark GB10 (`promaxgb10-41b1`), 128 GB unified memory
**Predecessors:** `RESULTS-v2-all-llamacpp-validation.md` (all tests passed), `POST-VALIDATION-model-strategy-revision.md`
**Execution results:** [`RESULTS-v3-production-deployment.md`](RESULTS-v3-production-deployment.md) — see "Runbook gaps discovered while executing" for the live-execution gap analysis that was folded back into this revision (TASK-RUN-D6F4).
**Expected duration:** ~1 hour

**Target architecture:**
```
llama-swap :9000 (single front door — all agents point here)
├── Qwen2.5-14B Q8_0          (Graphiti entity extraction)      ~22 GB  always loaded
├── nomic-embed f16            (embeddings for Graphiti/ChromaDB) ~0.3 GB always loaded
├── Qwen3.6-35B-A3B Q4_K_XL   (workhorse: Player/Coach/Forge)   ~21 GB  always loaded
└── Gemma 4 26B-A4B Q4_K_M    (fine-tuned GCSE study tutor)     ~17 GB  always loaded
                                                                 -------
                                                      Total:    ~60 GB  (64 GB headroom)
```

---

## Phase 0: Pre-flight

### 0.1 Confirm v2 models are still on disk

```bash
echo "=== Checking v2 validated models ==="

# Use -iname (case-insensitive) — actual files on disk are lowercase
# (e.g. qwen2.5-14b-instruct-q8_0-...gguf), runbook v3 originally globbed
# for capital Q8/F16/Q4 and missed everything. Fixed in TASK-RUN-D6F4.
GRAPHITI_GGUF=$(find ~/.cache/huggingface -iname "*qwen2.5*14*q8*.gguf" 2>/dev/null | head -1)
EMBED_GGUF=$(find ~/.cache/huggingface -iname "*nomic*f16*.gguf" 2>/dev/null | head -1)
MOE_GGUF=$(find ~/.cache/huggingface -iname "*qwen3.6*35*q4*.gguf" 2>/dev/null | head -1)

echo "Graphiti:  ${GRAPHITI_GGUF:-NOT FOUND}"
echo "Embed:     ${EMBED_GGUF:-NOT FOUND}"
echo "Workhorse: ${MOE_GGUF:-NOT FOUND}"

for f in "$GRAPHITI_GGUF" "$EMBED_GGUF" "$MOE_GGUF"; do
    if [ -z "$f" ] || [ ! -f "$f" ]; then
        echo "ERROR: Missing model file. Re-run RUNBOOK-v2 Phase 1 to download."
        exit 1
    fi
done
echo "All v2 models present."
```

### 0.2 Inspect the fine-tuned study tutor model

The fine-tuned GCSE tutor is a merged Q4_K_M GGUF produced by `train_gemma4_moe.py` (Unsloth QLoRA → merge → quantise). The GGUF and Modelfile live together in the `gguf_gguf` subdirectory.

```bash
echo "=== Inspecting fine-tuned Gemma 4 study tutor ==="

TUTOR_GGUF_DIR="$HOME/fine-tuning/output/gcse-tutor-gemma4-26b-moe/gguf_gguf"
TUTOR_GGUF="$TUTOR_GGUF_DIR/gemma-4-26b-a4b-it.Q4_K_M.gguf"
TUTOR_MODELFILE="$TUTOR_GGUF_DIR/Modelfile"

# Verify GGUF exists
if [ -f "$TUTOR_GGUF" ]; then
    echo "GGUF found: $TUTOR_GGUF"
    ls -lh "$TUTOR_GGUF"
else
    echo "ERROR: GGUF not found at $TUTOR_GGUF"
    echo "Check if the fine-tuning output is at a different path."
    exit 1
fi

# Read the Modelfile — this contains the system prompt the model was trained against
if [ -f "$TUTOR_MODELFILE" ]; then
    echo ""
    echo "Modelfile found. Contents:"
    echo "---"
    cat "$TUTOR_MODELFILE"
    echo "---"
    echo ""
    # Extract the SYSTEM block for use in the study-tutor MCP server
    # Ollama Modelfiles use: SYSTEM """...""" or SYSTEM "..."
    TUTOR_SYSTEM_PROMPT=$(sed -n '/^SYSTEM/,/^[A-Z]/{ /^SYSTEM/d; /^[A-Z]/d; p; }' "$TUTOR_MODELFILE" | sed 's/^\"\"\"//;s/\"\"\"$//' | head -50)
    if [ -z "$TUTOR_SYSTEM_PROMPT" ]; then
        # Try single-line SYSTEM "..." format
        TUTOR_SYSTEM_PROMPT=$(grep '^SYSTEM' "$TUTOR_MODELFILE" | sed 's/^SYSTEM //' | tr -d '"')
    fi
    echo "Extracted system prompt (first 200 chars):"
    echo "${TUTOR_SYSTEM_PROMPT:0:200}"
    
    # Save the system prompt to a standalone file for reference
    echo "$TUTOR_SYSTEM_PROMPT" > "$TUTOR_GGUF_DIR/system-prompt.txt"
    echo "System prompt saved to: $TUTOR_GGUF_DIR/system-prompt.txt"
else
    echo "WARNING: Modelfile not found at $TUTOR_MODELFILE"
    echo "Push it from the MacBook:"
    echo "  rsync -avP ~/Models/gcse-tutor-gemma4-26b-moe/Modelfile promaxgb10-41b1:$TUTOR_GGUF_DIR/"
    TUTOR_SYSTEM_PROMPT=""
fi
```

### 0.3 Confirm llama.cpp build is current

```bash
~/llama.cpp/build/bin/llama-server --version
```

### 0.4 Kill any lingering test servers from v1/v2

```bash
echo "=== Cleaning up stray servers ==="
for PORT in 8080 8090 8091 8092; do
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "Killing process on :$PORT (PID $PID)"
        kill $PID 2>/dev/null || true
    fi
done
echo "Test servers cleaned up."
```

### 0.5 Check disk space

```bash
df -h /opt 2>/dev/null || df -h /
# Need ~80 GB free for model copies to /opt
```

---

## Phase 1: Verify Tutor Model (No Conversion Needed)

The fine-tuned GGUF was confirmed in Phase 0.2. No conversion required — the Unsloth pipeline already produced a merged Q4_K_M GGUF.

```bash
echo "=== Verifying tutor GGUF ==="
echo "Path: $TUTOR_GGUF"
ls -lh "$TUTOR_GGUF"
echo "Modelfile present: $([ -f "$TUTOR_MODELFILE" ] && echo YES || echo NO)"
echo "System prompt saved: $([ -f "$TUTOR_GGUF_DIR/system-prompt.txt" ] && echo YES || echo NO)"
```

---

## Phase 2: Install llama-swap

### 2.1 Download and install

```bash
echo "=== Installing llama-swap ==="

if which llama-swap >/dev/null 2>&1; then
    echo "llama-swap already installed: $(llama-swap --version 2>&1 || echo 'version unknown')"
else
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) BINARY="llama-swap-linux-arm64" ;;
        x86_64)        BINARY="llama-swap-linux-amd64" ;;
        *)             echo "ERROR: Unsupported architecture: $ARCH"; exit 1 ;;
    esac

    RELEASE_URL="https://github.com/mostlygeek/llama-swap/releases/latest/download/$BINARY"
    echo "Downloading from $RELEASE_URL"
    sudo curl -L -o /usr/local/bin/llama-swap "$RELEASE_URL"
    sudo chmod +x /usr/local/bin/llama-swap
    llama-swap --version 2>&1 || echo "Installed (version check may not be supported)"
fi
```

### 2.2 Create directory structure

```bash
sudo mkdir -p /opt/llama-swap/{config,models/{qwen2.5-14b,nomic-embed,qwen36-35b,gemma4-tutor},logs}
sudo chown -R $USER:$USER /opt/llama-swap
```

---

## Phase 3: Stage Model Files

### 3.1 Copy all models to production paths

```bash
echo "=== Staging model files ==="

# Graphiti (Qwen2.5-14B Q8_0) — may be sharded
GRAPHITI_DIR=$(dirname "$GRAPHITI_GGUF")
SHARD_COUNT=$(ls "$GRAPHITI_DIR"/*Q8* 2>/dev/null | wc -l)
if [ "$SHARD_COUNT" -gt 1 ]; then
    echo "Graphiti: $SHARD_COUNT shards — copying all"
    cp "$GRAPHITI_DIR"/*Q8* /opt/llama-swap/models/qwen2.5-14b/
else
    cp "$GRAPHITI_GGUF" /opt/llama-swap/models/qwen2.5-14b/
fi

# Embeddings (nomic-embed f16)
cp "$EMBED_GGUF" /opt/llama-swap/models/nomic-embed/

# Workhorse (Qwen3.6-35B-A3B Q4_K_XL)
cp "$MOE_GGUF" /opt/llama-swap/models/qwen36-35b/

# Study tutor (fine-tuned Gemma 4 merged GGUF + Modelfile + system prompt)
cp "$TUTOR_GGUF" /opt/llama-swap/models/gemma4-tutor/
[ -f "$TUTOR_MODELFILE" ] && cp "$TUTOR_MODELFILE" /opt/llama-swap/models/gemma4-tutor/
[ -f "$TUTOR_GGUF_DIR/system-prompt.txt" ] && cp "$TUTOR_GGUF_DIR/system-prompt.txt" /opt/llama-swap/models/gemma4-tutor/

echo ""
echo "=== Staged model inventory ==="
for DIR in /opt/llama-swap/models/*/; do
    echo "$(basename $DIR): $(ls $DIR)"
done
echo ""
du -sh /opt/llama-swap/models/*/
echo ""
echo "Total:"
du -sh /opt/llama-swap/models/
```

---

## Phase 4: Stop vLLM and Old Services

### 4.1 Stop vLLM containers

```bash
echo "=== Stopping vLLM containers ==="

for CONTAINER in vllm-graphiti vllm-embedding vllm-serve; do
    if docker ps -q --filter "name=$CONTAINER" | grep -q .; then
        echo "Stopping: $CONTAINER"
        docker stop "$CONTAINER" && docker rm "$CONTAINER"
    else
        echo "Not running: $CONTAINER"
    fi
done
```

### 4.2 Kill any remaining llama-server processes

```bash
# Use -x (exact basename match) rather than -f (full command line). With -f,
# pkill matches the bash script running this block (the script text contains
# the literal string "llama-server") and self-kills before doing anything.
# Fixed in TASK-RUN-D6F4.
pkill -x llama-server 2>/dev/null && echo "Killed stray llama-server processes" || echo "No stray processes"
sleep 2

# Verify ports are free
for PORT in 8000 8001 8080 9000; do
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "WARNING: Port $PORT still in use by PID $PID — killing"
        kill "$PID" 2>/dev/null || true
    fi
done
echo "All ports clear."
```

---

## Phase 5: Write llama-swap Config and Start

### 5.1 Resolve model filenames and llama-server path

```bash
echo "=== Resolving paths ==="

LLAMA_SERVER=$(which llama-server 2>/dev/null || echo "$HOME/llama.cpp/build/bin/llama-server")
GRAPHITI_FILE=$(ls /opt/llama-swap/models/qwen2.5-14b/*.gguf | head -1)
EMBED_FILE=$(ls /opt/llama-swap/models/nomic-embed/*.gguf | head -1)
MOE_FILE=$(ls /opt/llama-swap/models/qwen36-35b/*.gguf | head -1)
TUTOR_FILE=$(ls /opt/llama-swap/models/gemma4-tutor/*.gguf | head -1)

echo "llama-server: $LLAMA_SERVER"
echo "Graphiti:     $GRAPHITI_FILE"
echo "Embed:        $EMBED_FILE"
echo "Workhorse:    $MOE_FILE"
echo "Tutor:        $TUTOR_FILE"

for f in "$GRAPHITI_FILE" "$EMBED_FILE" "$MOE_FILE" "$TUTOR_FILE"; do
    [ -f "$f" ] || { echo "ERROR: Missing $f"; exit 1; }
done
echo "All model files verified."
```

### 5.2 Write production config

```bash
cat > /opt/llama-swap/config/config.yaml << EOF
# =============================================================================
# llama-swap production config — all-llama.cpp architecture
# =============================================================================
# Single process tree. No vLLM. No Docker for inference.
# Four models permanently loaded. Zero swap overhead.
#
# Port: :9000 (all agents, Graphiti, study tutor point here)
# Routing: by model name/alias in the request
#
# Memory budget (validated 2026-04-28):
#   Qwen2.5-14B Q8_0:                  ~22 GB
#   nomic-embed f16:                    ~0.3 GB
#   Qwen3.6-35B-A3B Q4_K_XL:           ~21 GB
#   Gemma 4 26B-A4B Q4_K_M (tutor):    ~17 GB
#   Total:                              ~60 GB / 128 GB (64 GB headroom)
# =============================================================================

# 600s timeout (was 300s) gives the 21 GB workhorse and 19 GB tutor enough
# cold-start budget on first preload — see TASK-RUN-D6F4 / RESULTS-v3 Gap #1.
healthCheckTimeout: 600
startPort: 5800
logLevel: info

# Coexistence matrix — declares all four models can be resident
# simultaneously. Without this, llama-swap v208 evicts the previously
# running model on every request to a different one (ttl: 0 only governs
# *idle* eviction, not request-driven eviction). First execution without
# this block produced a load → kill → load → kill thrash loop on parallel
# polling. Added in TASK-RUN-D6F4 / RESULTS-v3 Gap #1.
matrix:
  vars:
    qg: qwen-graphiti
    ne: nomic-embed
    qw: qwen36-workhorse
    gt: gemma4-tutor
  sets:
    all: "qg & ne & qw & gt"

# Preload all four models at startup so cold-start is deterministic.
hooks:
  on_startup:
    preload:
      - qwen-graphiti
      - nomic-embed
      - qwen36-workhorse
      - gemma4-tutor

models:
  # ===========================================================================
  # GRAPHITI — entity extraction + Jarvis intent routing
  #
  # concurrencyLimit tuning notes (TASK-OPS-9F2A):
  #   This caps parallel /v1/chat/completions requests llama-swap will accept
  #   for this model.  Excess requests get HTTP 429 ("Rate limit exceeded").
  #
  #   Graphiti's full_doc parser splits large docs into many chunks and fires
  #   their entity-extraction LLM calls in parallel inside a single
  #   add_episode().  If the client's parallel fan-out (graphiti-core's
  #   SEMAPHORE_LIMIT, exposed in GuardKit as `chunk_extraction_concurrency`
  #   in .guardkit/graphiti.yaml) exceeds this concurrencyLimit, callers see
  #   spammy "Retrying request" log lines and 2-3x wall time inflation.
  #
  #   Two layers must agree:
  #     - Server (here):     concurrencyLimit
  #     - Client (graphiti): chunk_extraction_concurrency
  #   Set the client equal to or just below the server limit.
  #
  #   Capacity bound: -np N below sets the on-server parallel slot count.
  #   Each extra slot costs ~1-2 GB KV cache for Qwen2.5-14B Q8.
  #
  #   2026-05-04 bump (study-tutor TASK-GR-SEED Wave 5+): raised
  #   -np 2 → 6 and concurrencyLimit 4 → 8. graphiti-core's add_episode
  #   fans out 3-5 LLM calls in parallel within a single episode (entity
  #   extract + edge extract + dedup + summarise), which silently exceeded
  #   the previous 2-slot ceiling and abandoned ~40-50 % of seed writes
  #   under retry exhaustion. Six slots absorbs the worst observed burst
  #   (5 simultaneous POSTs in a 20 ms window) with one slot of headroom;
  #   concurrencyLimit 8 keeps the same proportion of admin-probe buffer.
  #   VRAM cost: +6-8 GB versus the previous baseline (~22 GB → ~28-30 GB
  #   for Qwen2.5-14B Q8) — well within the 64 GB headroom in the memory
  #   budget at the top of this file.
  # ===========================================================================
  "qwen-graphiti":
    cmd: >
      $LLAMA_SERVER
      --port \${PORT}
      --host 0.0.0.0
      --model $GRAPHITI_FILE
      --alias qwen-graphiti
      --ctx-size 32768
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      --temp 0.0
      -np 6
    checkEndpoint: /health
    ttl: 0
    concurrencyLimit: 8
    aliases:
      - "neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic"
      - "graphiti-llm"
      - "jarvis-router"

  # ===========================================================================
  # EMBEDDINGS — Graphiti + ChromaDB vector embeddings (768 dims)
  # ===========================================================================
  "nomic-embed":
    cmd: >
      $LLAMA_SERVER
      --port \${PORT}
      --host 0.0.0.0
      --model $EMBED_FILE
      --alias nomic-embed
      --embedding
      --ctx-size 8192
      --batch-size 8192
      --ubatch-size 8192
      --threads 16
      -ngl 999
      --no-mmap
      -np 4
    checkEndpoint: /health
    ttl: 0
    concurrencyLimit: 8
    aliases:
      - "nomic-embed-text-v1.5"
      - "nomic-ai/nomic-embed-text-v1.5"
      - "embeddings"

  # ===========================================================================
  # WORKHORSE — AutoBuild Player/Coach, Forge, Jarvis GP, Dataset Factory
  # ===========================================================================
  "qwen36-workhorse":
    cmd: >
      $LLAMA_SERVER
      --port \${PORT}
      --host 0.0.0.0
      --model $MOE_FILE
      --alias qwen36-workhorse
      --ctx-size 65536
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      --reasoning off
      --temp 0.6
      --top-p 0.95
      -np 1
    checkEndpoint: /health
    ttl: 0
    concurrencyLimit: 2
    aliases:
      - "autobuild-player"
      - "coach"
      - "jarvis-reasoner"
      - "forge-orchestrator"
      - "dataset-factory"
      - "claude-sonnet-4-6"
      - "claude-opus-4-7"

  # ===========================================================================
  # STUDY TUTOR — Fine-tuned Gemma 4 for GCSE tutoring (Socratic method)
  # ===========================================================================
  "gemma4-tutor":
    cmd: >
      $LLAMA_SERVER
      --port \${PORT}
      --host 0.0.0.0
      --model $TUTOR_FILE
      --alias gemma4-tutor
      --ctx-size 32768
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      --temp 0.7
      --top-p 0.9
      -np 1
    checkEndpoint: /health
    ttl: 0
    concurrencyLimit: 2
    aliases:
      - "study-tutor"
      - "gcse-tutor"
      - "architect-agent"
      - "gemma4-specialist"
EOF

echo "Config written to /opt/llama-swap/config/config.yaml"
```

### 5.3 Start llama-swap

```bash
echo "=== Starting llama-swap ==="

# llama-swap v208 uses single-dash flags (-config, -listen). Double-dash
# variants are silently rejected. Fixed in TASK-RUN-D6F4 / RESULTS-v3 Gap #3.
nohup llama-swap \
    -config /opt/llama-swap/config/config.yaml \
    -listen :9000 \
    > /opt/llama-swap/logs/llama-swap.log 2>&1 &

SWAP_PID=$!
echo "llama-swap PID: $SWAP_PID"
echo "Logs: tail -f /opt/llama-swap/logs/llama-swap.log"
sleep 5
curl -s http://localhost:9000/ > /dev/null 2>&1 && echo "llama-swap proxy is up" || echo "Waiting for proxy..."
```

### 5.4 Trigger all four model loads and wait

```bash
echo "=== Triggering model loads (this takes 3-8 minutes) ==="

# Fire all four load requests in parallel
curl -s http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen-graphiti","max_tokens":1,"messages":[{"role":"user","content":"test"}]}' > /dev/null 2>&1 &

curl -s http://localhost:9000/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model":"nomic-embed","input":"test"}' > /dev/null 2>&1 &

curl -s http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen36-workhorse","max_tokens":1,"messages":[{"role":"user","content":"test"}]}' > /dev/null 2>&1 &

curl -s http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"gemma4-tutor","max_tokens":1,"messages":[{"role":"user","content":"test"}]}' > /dev/null 2>&1 &

echo "Load requests sent. Waiting..."

# Poll until all respond
READY=0
ATTEMPTS=0
while [ $READY -lt 4 ] && [ $ATTEMPTS -lt 60 ]; do
    READY=0
    for MODEL in qwen-graphiti nomic-embed qwen36-workhorse gemma4-tutor; do
        if [ "$MODEL" = "nomic-embed" ]; then
            curl -s --max-time 5 http://localhost:9000/v1/embeddings \
                -H "Content-Type: application/json" \
                -d "{\"model\":\"$MODEL\",\"input\":\"test\"}" 2>/dev/null | grep -q "embedding" && READY=$((READY + 1))
        else
            curl -s --max-time 5 http://localhost:9000/v1/chat/completions \
                -H "Content-Type: application/json" \
                -d "{\"model\":\"$MODEL\",\"max_tokens\":1,\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}" 2>/dev/null | grep -q "choices\|content" && READY=$((READY + 1))
        fi
    done
    echo "  Models ready: $READY/4 (attempt $((ATTEMPTS+1)))"
    ATTEMPTS=$((ATTEMPTS + 1))
    [ $READY -lt 4 ] && sleep 10
done

if [ $READY -eq 4 ]; then
    echo "ALL FOUR MODELS LOADED SUCCESSFULLY"
else
    echo "WARNING: Only $READY/4 models loaded. Check logs:"
    echo "  tail -50 /opt/llama-swap/logs/llama-swap.log"
fi
```

> **Operational note (TASK-OPS-7CB1, 2026-04-29):** llama-swap's `Restart=on-failure` only covers the parent. If individual model children die unexpectedly (e.g. SIGKILL from a parent cgroup, segfault under load, or — observed on 2026-04-28→29 — an unexplained four-way exit), `hooks.on_startup.preload` does NOT auto-revive them; matrix.sets only resurrects them when traffic hits. Phase 5.6 below installs a periodic keep-alive that closes this gap.

### 5.5 Verify VRAM footprint

```bash
echo "=== Production VRAM footprint ==="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

echo ""
nvidia-smi --query-compute-apps=used_memory --format=csv,noheader | \
    awk -F' ' '{sum += $1} END {print "Total VRAM: " sum " MiB (" sum/1024 " GiB)"}'
```

**Expected:** ~65 GB total for all four models, broken down as
(measured 2026-04-28, see RESULTS-v3 Follow-up #3):

| Model                          | VRAM   |
|--------------------------------|--------|
| Qwen2.5-14B Q8_0 (Graphiti)    | 21.3 GB |
| nomic-embed f16 (embeddings)   |  0.9 GB |
| Qwen3.6-35B-A3B Q4_K_XL (workhorse) | 23.7 GB |
| Gemma 4 26B-A4B Q4_K_M (tutor) | 19.1 GB |
| **Total**                      | **~65 GB** |

Workhorse and tutor run ~3 GB above the original estimate combined — likely
KV-cache contribution at 64K and 32K context respectively. 60 GB headroom
remains on a 128 GB GB10.

### 5.6 Install the keep-alive timer (TASK-OPS-7CB1)

llama-swap does not auto-revive crashed model children — only the parent gets
`Restart=on-failure` from the systemd unit (Phase 10.2), and matrix.sets only
resurrects a child when traffic next reaches it. The keep-alive timer fires
every 5 minutes, asks `/running` for the configured-but-not-running set, and
sends a one-shot warmup to each missing model. The probe request returns
immediately (1-token chat / single-token embed), so it does not pin any
`concurrencyLimit` slot.

```bash
REPO=~/Projects/appmilla_github/guardkit

# 1. Install the script alongside llama-swap binaries (or leave in repo and
#    point the unit file at the repo path — that's what the shipped unit
#    already does).
sudo install -m 0755 "$REPO/scripts/llama-swap-keepalive.sh" \
    /usr/local/bin/llama-swap-keepalive.sh

# 2. Drop the unit + timer (the shipped versions reference the repo path; the
#    install command below overwrites with the binary path for production).
sudo install -m 0644 "$REPO/scripts/llama-swap-keepalive.service" \
    /etc/systemd/system/llama-swap-keepalive.service
sudo install -m 0644 "$REPO/scripts/llama-swap-keepalive.timer" \
    /etc/systemd/system/llama-swap-keepalive.timer

# Adjust ExecStart in the installed copy to use /usr/local/bin
sudo sed -i 's|ExecStart=.*llama-swap-keepalive\.sh|ExecStart=/usr/local/bin/llama-swap-keepalive.sh|' \
    /etc/systemd/system/llama-swap-keepalive.service

sudo systemctl daemon-reload
sudo systemctl enable --now llama-swap-keepalive.timer

# Verify
systemctl list-timers llama-swap-keepalive.timer
journalctl -u llama-swap-keepalive.service -n 30 --no-pager
```

**Expected output of first manual run (after killing one child):**

```
[llama-swap-keepalive] Reviving: nomic-embed
[llama-swap-keepalive]   nomic-embed: revived (HTTP 200)
```

**To verify keep-alive does not hold a slot,** kill a child, run keep-alive,
then fire 8 parallel requests against the revived model — none should 429:

```bash
sudo kill -9 $(pgrep -f "alias nomic-embed")
sudo systemctl start llama-swap-keepalive.service
for i in $(seq 1 8); do
    (curl -s --max-time 10 http://localhost:9000/v1/embeddings \
        -H "Content-Type: application/json" \
        -d '{"model":"nomic-embed","input":"slot test"}' \
        -o /dev/null -w "req $i: %{http_code}\n") &
done; wait
```

**See also**: TASK-OPS-7CB1 captures the original observation (one four-way
exit on 2026-04-28→29 with no kernel/CUDA/OOM evidence) and an operational
finding that the running stack was hosted inside a VS Code Chromium scope
rather than under the systemd unit installed in Phase 10.2. The keep-alive
patches the symptom; the structural fix (use the systemd unit, run outside
the GUI session) is captured in Phase 10.2 below.

### 5.7 Install the weekly health check (TASK-OPS-7CB1 follow-up)

The keep-alive timer reacts to crashes within 5 minutes. On its own that's
enough to keep the stack serving — but if model children start crashing
repeatedly (e.g. a fresh upstream regression), nobody notices until they
look at the journal. The weekly health check audits the keep-alive's last
7 days of activity and writes a structured report to
`/opt/llama-swap/logs/healthcheck-YYYYMMDD.log`. Status field summary:

- `HEALTHY` (exit 0) — timer firing, no fresh crashes, all four models up
- `ATTENTION` (exit 1) — revivals happened (recovered fine, but worth a
  glance) or VRAM drifted
- `CRITICAL` (exit 2) — timer not firing, llama-swap unreachable, models
  missing, or repeated keep-alive failures

The runs are non-noisy because they only escalate on **new** crash events
since the last run (delta-tracked via `last_exit_count` state file).

```bash
REPO=~/Projects/appmilla_github/guardkit

# 1. Install the script
sudo install -m 0755 "$REPO/scripts/llama-swap-healthcheck.sh" \
    /usr/local/bin/llama-swap-healthcheck.sh

# 2. Install the unit + timer
sudo install -m 0644 "$REPO/scripts/llama-swap-healthcheck.service" \
    /etc/systemd/system/llama-swap-healthcheck.service
sudo install -m 0644 "$REPO/scripts/llama-swap-healthcheck.timer" \
    /etc/systemd/system/llama-swap-healthcheck.timer

# 3. Repoint ExecStart at /usr/local/bin (was the repo path in the
#    shipped unit so it's runnable for development)
sudo sed -i 's|ExecStart=.*llama-swap-healthcheck\.sh|ExecStart=/usr/local/bin/llama-swap-healthcheck.sh|' \
    /etc/systemd/system/llama-swap-healthcheck.service

# 4. Seed the state file with the current cumulative crash count, so the
#    first real run reports zero "new" events instead of replaying every
#    historical exit. Skip this step if you want the first report to
#    enumerate all prior events.
sudo mkdir -p /opt/llama-swap/logs/healthcheck-state
sudo chown -R $USER:$USER /opt/llama-swap/logs/healthcheck-state
grep -c "process exited but not StateStopping" /opt/llama-swap/logs/llama-swap.log \
    > /opt/llama-swap/logs/healthcheck-state/last_exit_count

# 5. daemon-reload + enable + start now (immediate first run useful for
#    smoke-testing; skip --now if you'd rather wait for the next Monday)
sudo systemctl daemon-reload
sudo systemctl enable --now llama-swap-healthcheck.timer

# 6. Verify
systemctl is-enabled llama-swap-healthcheck.timer
systemctl is-active  llama-swap-healthcheck.timer
systemctl list-timers llama-swap-healthcheck.timer --no-pager
journalctl -u llama-swap-healthcheck.service -n 50 --no-pager
ls -la /opt/llama-swap/logs/healthcheck-*.log | tail -3
```

**To run it manually any time** (without waiting for Monday 09:00):

```bash
sudo systemctl start llama-swap-healthcheck.service
journalctl -u llama-swap-healthcheck.service -n 100 --no-pager
```

**Why local + not a remote agent**: the original plan was to schedule a
remote agent (Anthropic cloud) to do this audit, but a remote agent has
no path to `journalctl` / `systemctl` / `nvidia-smi` on
`promaxgb10-41b1`. A local systemd timer runs where the data lives, no
GitHub creds, no MCP, no cloud — and survives daily OS updates and
reboots the same way the keep-alive does (`Persistent=true` +
`WantedBy=timers.target`).

---

## Phase 6: Validate All Endpoints

### 6.1 Graphiti JSON extraction

```bash
echo "=== Test: Graphiti entity extraction ==="
curl -s http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen-graphiti",
        "temperature": 0,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Extract entities and relationships as JSON: {\"entities\": [{\"name\": \"...\", \"type\": \"...\", \"description\": \"...\"}], \"relationships\": [{\"source\": \"...\", \"target\": \"...\", \"type\": \"...\", \"description\": \"...\"}]}. Return ONLY valid JSON."},
            {"role": "user", "content": "The GuardKit AutoBuild system uses a Player-Coach adversarial loop. The Player generates code using Qwen3.6-35B-A3B served by llama.cpp. The Coach validates using the same model. Both run on the Dell DGX Spark GB10 behind llama-swap. Graphiti stores decisions in FalkorDB."}
        ]
    }' | python3 -c "
import sys, json
resp = json.load(sys.stdin)
text = resp['choices'][0]['message']['content']
data = json.loads(text)
entities = data.get('entities', [])
rels = data.get('relationships', [])
print(f'Entities: {len(entities)}')
print(f'Relationships: {len(rels)}')
print('PASS' if len(entities) >= 6 and len(rels) >= 3 else 'FAIL')
"
```

### 6.2 Embeddings (768 dims)

```bash
echo "=== Test: Embeddings ==="
curl -s http://localhost:9000/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model":"nomic-embed","input":"Test embedding via llama-swap production."}' \
    | python3 -c "
import sys, json
resp = json.load(sys.stdin)
dims = len(resp['data'][0]['embedding'])
print(f'Dimensions: {dims}')
print('PASS' if dims == 768 else f'FAIL: expected 768, got {dims}')
"
```

### 6.3 Workhorse tool calling

```bash
echo "=== Test: Workhorse tool calling ==="
curl -s http://localhost:9000/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: not-needed" \
    -d '{
        "model": "qwen36-workhorse",
        "max_tokens": 1024,
        "tools": [{"name":"rag_retrieval","description":"Retrieve chunks from RAG.","input_schema":{"type":"object","properties":{"query":{"type":"string"},"collection":{"type":"string"}},"required":["query","collection"]}}],
        "messages": [{"role": "user", "content": "Search the architecture-decisions collection for the dark factory inference strategy."}]
    }' | python3 -c "
import sys, json
resp = json.load(sys.stdin)
tool_use = [b for b in resp.get('content', []) if b['type'] == 'tool_use']
if tool_use:
    print(f'Tool: {tool_use[0][\"name\"]}')
    print(f'Stop reason: {resp.get(\"stop_reason\")}')
    print('PASS')
else:
    print('FAIL: no tool_use block')
"
```

### 6.4 Workhorse throughput

```bash
echo "=== Test: Workhorse throughput ==="
START=$(date +%s%N)
curl -s http://localhost:9000/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: not-needed" \
    -d '{"model":"qwen36-workhorse","max_tokens":256,"messages":[{"role":"user","content":"Write a Python async function to subscribe to NATS subject fleet.register."}]}' > /tmp/prod-speed-test.json
END=$(date +%s%N)
ELAPSED_MS=$(( (END - START) / 1000000 ))
echo "Wall time: ${ELAPSED_MS}ms (expect ~5-6s for 256 tokens at 45+ tok/s)"
```

### 6.5 Study tutor — GCSE Socratic dialogue

Uses the system prompt from the Modelfile if available, otherwise falls back to a generic tutor prompt.

```bash
echo "=== Test: Study tutor ==="

# Read the trained system prompt if it was extracted
SYSTEM_PROMPT=""
if [ -f /opt/llama-swap/models/gemma4-tutor/system-prompt.txt ]; then
    SYSTEM_PROMPT=$(cat /opt/llama-swap/models/gemma4-tutor/system-prompt.txt)
    echo "Using trained system prompt from Modelfile"
fi

# Fall back to generic if empty
if [ -z "$SYSTEM_PROMPT" ]; then
    SYSTEM_PROMPT="You are a GCSE English Language tutor following the AQA specification. Use the Socratic method — guide the student to discover answers through questions rather than giving them directly. Be encouraging and age-appropriate."
    echo "Using fallback system prompt (Modelfile not found)"
fi

# Escape the system prompt for JSON
ESCAPED_PROMPT=$(echo "$SYSTEM_PROMPT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")

curl -s http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"gemma4-tutor\",
        \"max_tokens\": 512,
        \"temperature\": 0.7,
        \"messages\": [
            {\"role\": \"system\", \"content\": $ESCAPED_PROMPT},
            {\"role\": \"user\", \"content\": \"I have my Paper 1 exam next week and I always struggle with Question 5. How do I write a good descriptive piece?\"}
        ]
    }" | python3 -c "
import sys, json
resp = json.load(sys.stdin)
text = resp['choices'][0]['message']['content']
words = len(text.split())
print(f'Words: {words}')
print()
print(text[:600])
print()
has_question = '?' in text
has_encouragement = any(w in text.lower() for w in ['great', 'good', 'well done', 'think about', 'what if', 'can you', 'have you', 'try', 'imagine', 'consider'])
print(f'Contains questions (Socratic): {\"YES\" if has_question else \"NO\"}')
print(f'Contains encouragement: {\"YES\" if has_encouragement else \"NO\"}')
print('PASS' if has_question and words > 50 else 'NEEDS REVIEW')
"
```

### 6.6 Alias routing test

```bash
echo "=== Test: Alias routing ==="
for ALIAS in study-tutor gcse-tutor; do
    RESULT=$(curl -s http://localhost:9000/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$ALIAS\",\"max_tokens\":10,\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}" 2>/dev/null)
    if echo "$RESULT" | grep -q "choices"; then
        echo "  $ALIAS → PASS"
    else
        echo "  $ALIAS → FAIL"
    fi
done
```

---

## Phase 7: Update Graphiti Config

### 7.1 Update graphiti-mcp-config.yaml

```bash
echo "=== Updating Graphiti MCP config ==="

CONFIG_FILE="$HOME/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml"
BACKUP_FILE="${CONFIG_FILE}.pre-llamacpp.bak"

cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "Backed up to: $BACKUP_FILE"

# Three changes:
#   1. LLM API URL: localhost:8000 → localhost:9000
#   2. Embedding API URL: localhost:8001 → localhost:9000
#   3. Embedding dimensions: 1024 → 768 (bug fix — actual model is 768)

sed -i 's|api_url: ${LLM_API_URL:http://localhost:8000/v1}|api_url: ${LLM_API_URL:http://localhost:9000/v1}|' "$CONFIG_FILE"
sed -i 's|api_url: ${EMBEDDING_API_URL:http://localhost:8001/v1}|api_url: ${EMBEDDING_API_URL:http://localhost:9000/v1}|' "$CONFIG_FILE"
sed -i 's|dimensions: 1024|dimensions: 768|' "$CONFIG_FILE"

echo ""
echo "=== Verify MCP changes ==="
grep -n "api_url\|dimensions" "$CONFIG_FILE"

# ---------------------------------------------------------------------------
# Also patch the Python client config used by `guardkit graphiti add-context`
# and `guardkit graphiti seed`. The MCP container reads the file above; the
# Python client reads .guardkit/graphiti.yaml. Without this second patch,
# Phase 8 fails with `openai._base_client:Retrying request` followed by
# `Episode creation failed: Connection error.` because the Python client
# is still pointed at the old vLLM ports 8000/8001.
# Added in TASK-RUN-D6F4 / RESULTS-v3 Gap #2.
# ---------------------------------------------------------------------------

CLIENT_CONFIG="$HOME/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml"
CLIENT_BACKUP="${CLIENT_CONFIG}.pre-llamacpp.bak"

if [ -f "$CLIENT_CONFIG" ]; then
    cp "$CLIENT_CONFIG" "$CLIENT_BACKUP"
    echo "Backed up Python client config to: $CLIENT_BACKUP"

    sed -i 's|http://promaxgb10-41b1:8000/v1|http://promaxgb10-41b1:9000/v1|g' "$CLIENT_CONFIG"
    sed -i 's|http://promaxgb10-41b1:8001/v1|http://promaxgb10-41b1:9000/v1|g' "$CLIENT_CONFIG"

    echo ""
    echo "=== Verify Python client changes ==="
    grep -n "promaxgb10-41b1" "$CLIENT_CONFIG" || echo "(no promaxgb10-41b1 references — using local hostnames?)"
else
    echo "WARNING: $CLIENT_CONFIG not found — Phase 8 may fail with connection errors"
fi
```

### 7.2 Rebuild and restart Graphiti MCP server

```bash
echo "=== Rebuilding Graphiti MCP image at the pinned fork tag ==="

cd ~/Projects/appmilla_github/guardkit

# graphiti-mcp.sh refuses to start if the image is missing, but it will
# happily reuse a stale image built from an older fork tag. We must rebuild
# explicitly whenever the default GRAPHITI_TAG in graphiti-mcp-build.sh
# moves (currently v0.29.5-guardkit.6 — carries the get_episodes MCP fix
# verified in Phase 8.1 plus the TASK-INF-5054 LLM endpoint routing fix
# verified in Phase 8.1b).
./scripts/graphiti-mcp-build.sh

# Confirm the checkout is at the pinned tag before we ship it.
GRAPHITI_REPO_DIR="${GRAPHITI_REPO_DIR:-$HOME/Projects/appmilla_github/graphiti}"
ACTUAL_TAG=$(git -C "$GRAPHITI_REPO_DIR" describe --tags --exact-match HEAD 2>/dev/null || echo "(no tag at HEAD)")
echo "Graphiti fork checkout: $ACTUAL_TAG"
[ "$ACTUAL_TAG" = "v0.29.5-guardkit.6" ] || echo "WARNING: not at v0.29.5-guardkit.6 — Phase 8.1/8.1b will likely fail"

echo "=== Restarting Graphiti MCP server ==="

docker stop graphiti-mcp 2>/dev/null && docker rm graphiti-mcp 2>/dev/null || true

./scripts/graphiti-mcp.sh

sleep 10
curl -s http://localhost:8004/health 2>/dev/null && echo "Graphiti MCP server healthy" || echo "Waiting..."
```

---

## Phase 8: End-to-End Graphiti Seed Test

> **Phase 8.1 below verifies the v0.29.5-guardkit.5 MCP `get_episodes` bug
> fix.** The seed test in Phase 8 exercises the Python client write path
> (`guardkit graphiti seed`); Phase 8.1 exercises the MCP read path
> (`get_episodes` over streamable HTTP) which is where the bug lived.
> Both must pass.

### 8.1 Verify MCP get_episodes returns non-empty results (v0.29.5-guardkit.5)

The bug had two layers, both fixed in v0.29.5-guardkit.5:

1. **MCP-side (v0.29.5-guardkit.5):** `mcp_server/src/graphiti_mcp_server.py`
   `get_episodes` now routes through `Graphiti.retrieve_episodes` (decorated)
   instead of calling `EpisodicNode.get_by_group_ids` directly with the
   shared driver.
2. **Decorator-side + packaging (v0.29.5-guardkit.5):** the
   `@handle_multiple_group_ids` decorator now takes the FalkorDB
   per-group `driver.clone(database=gid)` path for *single*-group calls
   too, not only multi-group calls. Equally important: the Dockerfile
   now installs graphiti-core from the local fork source tree
   (`[tool.uv.sources]` resolves `path = "../"`) instead of stripping
   the override and pulling broken upstream graphiti-core 0.28.1 from
   PyPI. Without this, all the fork's `graphiti_core/` patches were
   orphaned at runtime.

See
`~/Projects/appmilla_github/graphiti/docs/bugs/get-episodes-mcp-empty-results.md`
and the audit trail in this runbook's Phase 8.1 commit history.

This phase reads from groups that are already populated in FalkorDB. A
synthetic write-then-read design was tried first and found unsuitable
because **TASK-INF-5054** (graphiti-core misroutes LLM calls to
`api.openai.com/v1/responses` instead of the local llama-swap) prevents
`add_memory` from completing extraction — the EpisodicNode never lands
even on a passing get_episodes path. Reading a pre-populated group
isolates this phase from TASK-INF-5054 and exercises only the bug we
care about here.

**Precondition:** at least one of the probe groups below must already
contain Episodic nodes. On a greenfield deployment, run
`guardkit graphiti seed-system` first (or pick any group you know has
been populated by prior captures). If all probe groups are empty, the
script exits 2 (inconclusive) rather than passing or failing.

```bash
echo "=== Phase 8.1: MCP get_episodes (bug fix verification) ==="

python3 - <<'PY'
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://localhost:8004/mcp/"
# System groups that should be populated by guardkit graphiti seed-system,
# plus a couple of project groups that accumulate via task captures.
# Add or remove as appropriate for your deployment.
PROBE_GROUPS = [
    "command_workflows",
    "patterns",
    "guardkit__project_decisions",
    "guardkit__task_outcomes",
]


def _payload(result):
    if not getattr(result, "content", None):
        return {}
    text = result.content[0].text or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


async def main() -> int:
    async with streamablehttp_client(URL) as (read, write, _close):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Single-group calls — this is the path that returned [] pre-fix.
            results = []
            for group in PROBE_GROUPS:
                res = await session.call_tool("get_episodes", {
                    "group_ids": [group],
                    "max_episodes": 3,
                })
                eps = _payload(res).get("episodes", [])
                results.append((group, len(eps), eps[0].get("name") if eps else None))

            print("=== single-group MCP get_episodes ===")
            for grp, count, sample in results:
                marker = "PASS " if count > 0 else "EMPTY"
                line = f"  [{marker}] {grp:35s} -> {count} episode(s)"
                if sample:
                    line += f"  sample={sample!r}"
                print(line)

            # Multi-group regression check: this path also has to keep working.
            multi_res = await session.call_tool("get_episodes", {
                "group_ids": PROBE_GROUPS[:2],
                "max_episodes": 4,
            })
            multi_eps = _payload(multi_res).get("episodes", [])
            print(f"\n=== multi-group regression ({PROBE_GROUPS[:2]}) ===")
            print(f"  {'PASS ' if multi_eps else 'EMPTY'}: {len(multi_eps)} episode(s)")

            non_empty = [g for g, n, _ in results if n > 0]
            if not non_empty:
                print("\nENV-NOT-READY: all probe groups returned 0 episodes.")
                print("Seed the system groups first, then re-run Phase 8.1:")
                print("  guardkit graphiti seed-system")
                return 2  # inconclusive

            if not multi_eps:
                print(
                    "\nFAIL: multi-group call returned [] from probe groups "
                    "that single-group calls confirmed are populated. "
                    "Decorator may have regressed."
                )
                return 1

            print(
                f"\nPASS: {len(non_empty)}/{len(results)} probe groups returned "
                f"episodes via single-group MCP get_episodes; multi-group "
                f"returned {len(multi_eps)}. v0.29.5-guardkit.5 is in effect."
            )
            return 0


sys.exit(asyncio.run(main()))
PY
```

**Expected output (PASS path):**
```
=== single-group MCP get_episodes ===
  [PASS ] command_workflows                   -> 3 episode(s)  sample='cli_guardkit_graphiti'
  [PASS ] patterns                            -> 3 episode(s)  sample='Orchestrator Pattern: Error Recovery'
  [PASS ] guardkit__project_decisions         -> 3 episode(s)  sample='Design rule: ...'
  [PASS ] guardkit__task_outcomes             -> 3 episode(s)  sample='OUT-...'

=== multi-group regression (['command_workflows', 'patterns']) ===
  PASS : 6 episode(s)

PASS: 4/4 probe groups returned episodes via single-group MCP get_episodes; multi-group returned 6. v0.29.5-guardkit.5 is in effect.
```

**If single-group probes return 0 but multi-group works** → only the
guardkit.4 MCP-side fix is live; the guardkit.5 Dockerfile/decorator
fix has not landed. Re-check: (a) the fork checkout in Phase 7.2 reports
`v0.29.5-guardkit.6` and (b) `docker run --rm --entrypoint sh
graphiti-mcp-standalone:local -c "grep -c 'len(group_ids)'
/app/graphiti_core/decorators.py"` returns 0. If either is wrong, force
a clean rebuild:

```bash
docker rmi graphiti-mcp-standalone:local
./scripts/graphiti-mcp-build.sh --no-cache
docker stop graphiti-mcp; docker rm graphiti-mcp
./scripts/graphiti-mcp.sh
```

### 8.1b Verify MCP add_memory→get_episodes round-trip (TASK-INF-5054 / v0.29.5-guardkit.6)

This phase verifies the **write** path now works end-to-end. Pre-fix
(v0.29.5-guardkit.5 and earlier), `mcp_server/src/services/factories.py`
`LLMClientFactory.create` dropped `base_url` on the floor for the
`openai` provider and always returned `OpenAIClient`. `OpenAIClient`'s
structured-output path calls `client.responses.parse` (the OpenAI
Responses API at `/v1/responses`), which exists only on OpenAI cloud —
local llama-swap / vLLM / ollama only implement `/v1/chat/completions`.
Result: `add_memory` queued the episode, the queue worker called
`https://api.openai.com/v1/responses` with the local
`not-needed-vllm-local` API key, got HTTP 401, retried twice, dropped
the episode. The EpisodicNode never landed in FalkorDB.

v0.29.5-guardkit.6 fixes both layers: the factory now passes `base_url`
to `LLMConfig` (matching the embedder factory which always did) and
picks `OpenAIGenericClient` (chat.completions + json_schema response
format) for any non-`api.openai.com` endpoint. Verify:

```bash
echo "=== Phase 8.1b: MCP add_memory → get_episodes round-trip ==="

python3 - <<'PY'
import asyncio
import json
import sys
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://localhost:8004/mcp/"
GROUP = f"runbook_v3_addmem_smoke_{int(time.time())}"
POLL_SECONDS = 90      # ~3-5 LLM calls × ~10s each at local-model latency
POLL_INTERVAL = 5


async def main() -> int:
    async with streamablehttp_client(URL) as (rd, wr, _):
        async with ClientSession(rd, wr) as s:
            await s.initialize()
            print(f"Test group: {GROUP}")

            add_res = await s.call_tool("add_memory", {
                "name": "TASK-INF-5054 round-trip smoke",
                "episode_body": (
                    "GuardKit AutoBuild runs on the GB10 behind llama-swap. "
                    "Alice approved the deployment. The DGX Spark is the test host."
                ),
                "source": "text",
                "source_description": "runbook v3 8.1b smoke",
                "group_id": GROUP,
            })
            print(f"add_memory: {add_res.content[0].text if add_res.content else '(no content)'}")

            deadline = time.time() + POLL_SECONDS
            attempt = 0
            episodes: list = []
            while time.time() < deadline:
                attempt += 1
                await asyncio.sleep(POLL_INTERVAL)
                get_res = await s.call_tool("get_episodes", {
                    "group_ids": [GROUP],
                    "max_episodes": 5,
                })
                payload = json.loads(get_res.content[0].text) if get_res.content else {}
                episodes = payload.get("episodes", [])
                if episodes:
                    break
                print(f"  attempt {attempt}: queue still processing, retrying in {POLL_INTERVAL}s")

            try:
                await s.call_tool("clear_graph", {"group_ids": [GROUP]})
            except Exception as exc:
                print(f"clear_graph: WARNING — cleanup failed for {GROUP}: {exc}")

            if not episodes:
                print(
                    f"\nFAIL: episode never appeared after {POLL_SECONDS}s. "
                    "Likely cause: TASK-INF-5054 fix not in image. Check "
                    "`docker logs graphiti-mcp --tail 50` for "
                    "`POST https://api.openai.com/v1/responses` 401s — "
                    "if present, factory still routes to the cloud Responses API."
                )
                return 1

            ep = episodes[0]
            print(
                f"\nPASS: add_memory → get_episodes round-trip works. "
                f"Episode persisted in {attempt * POLL_INTERVAL}s "
                f"(uuid={ep.get('uuid','')[:8]}, name={ep.get('name')!r}). "
                "v0.29.5-guardkit.6 (TASK-INF-5054) is in effect."
            )
            return 0


sys.exit(asyncio.run(main()))
PY
```

**Sanity check after PASS** — confirm the LLM endpoint actually used:

```bash
docker logs graphiti-mcp --since 2m 2>&1 | \
    grep -E "POST.*chat/completions|api.openai.com" | head -10
```

Expected: only `POST http://localhost:9000/v1/chat/completions "HTTP/1.1
200 OK"` lines. If you see `api.openai.com/v1/responses 401`, the
factory is routing to the wrong client — confirm the
`OpenAI-compatible endpoint detected ... using OpenAIGenericClient`
log line is present at startup
(`docker logs graphiti-mcp 2>&1 | grep factories`).

### 8.2 Graphiti seed through the Python client

```bash
echo "=== E2E: Graphiti seed through llama-swap ==="

cd ~/Projects/appmilla_github/guardkit

TEST_DOC=$(find docs/decisions -name "DECISION-DF*" -type f | head -1)

if [ -n "$TEST_DOC" ]; then
    echo "Seeding: $TEST_DOC"
    guardkit graphiti seed "$TEST_DOC" --verbose 2>&1 | tee /tmp/graphiti-prod-seed.log

    if grep -qi "error\|exception\|traceback" /tmp/graphiti-prod-seed.log; then
        echo "FAIL: Errors detected"
        grep -i "error\|exception" /tmp/graphiti-prod-seed.log
    else
        echo "PASS: Seed completed without errors"
    fi
else
    echo "SKIP: No decision doc found to seed."
fi
```

---

## Phase 9: Decision Gate

| Test | Result | Notes |
|---|---|---|
| P0.1: v2 models on disk | | |
| P0.2: Fine-tuned tutor GGUF found | | Path: ~/fine-tuning/output/.../gguf_gguf/ |
| P0.2: Modelfile system prompt extracted | | |
| P1: Tutor model verified | | |
| P2: llama-swap installed | | |
| P3: All models staged to /opt | | Record total disk |
| P4: vLLM stopped | | |
| P5.3: llama-swap started | | |
| P5.4: All 4 models loaded | | |
| P5.5: Production VRAM | | **Record total** |
| P6.1: Graphiti JSON extraction | | |
| P6.2: Embeddings (768 dims) | | |
| P6.3: Workhorse tool calling | | |
| P6.4: Workhorse throughput | | **Record tok/s** |
| P6.5: Study tutor Socratic dialogue | | |
| P6.6: Alias routing | | |
| P7: Graphiti config updated | | dims 1024→768 |
| P7.2: Graphiti fork checkout at v0.29.5-guardkit.6 | | `git describe --tags --exact-match HEAD` |
| P7.2: graphiti-core editable install (not PyPI) | | `docker run --rm --entrypoint sh graphiti-mcp-standalone:local -c 'test -f /app/graphiti_core/decorators.py'` |
| P8.1: MCP get_episodes single-group returns non-empty | | v0.29.5-guardkit.5 verification |
| P8.1b: MCP add_memory→get_episodes round-trip | | v0.29.5-guardkit.6 verification (TASK-INF-5054) |
| P8.2: E2E Graphiti seed | | **No JSON errors** |

---

## Phase 10: Cleanup and Harden

### 10.1 Archive vLLM scripts

```bash
mkdir -p ~/Projects/appmilla_github/guardkit/scripts/archive-vllm

for SCRIPT in vllm-graphiti.sh vllm-embed.sh vllm-serve.sh vllm-serve.original.sh vllm-neomtron3-nano.sh vllm-agentic-factory.sh; do
    if [ -f ~/Projects/appmilla_github/guardkit/scripts/$SCRIPT ]; then
        mv ~/Projects/appmilla_github/guardkit/scripts/$SCRIPT \
           ~/Projects/appmilla_github/guardkit/scripts/archive-vllm/
        echo "Archived: $SCRIPT"
    fi
done
```

### 10.2 Create systemd service for auto-start

```bash
sudo tee /etc/systemd/system/llama-swap.service << 'EOF'
[Unit]
Description=llama-swap model serving (all-llama.cpp architecture)
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/llama-swap -config /opt/llama-swap/config/config.yaml -listen :9000
Restart=on-failure
RestartSec=10
StandardOutput=append:/opt/llama-swap/logs/llama-swap.log
StandardError=append:/opt/llama-swap/logs/llama-swap.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable llama-swap
echo "Systemd service created. Auto-starts on boot."
echo "  sudo systemctl start llama-swap"
echo "  sudo systemctl status llama-swap"
echo "  journalctl -u llama-swap -f"
```

> **Operational warning (TASK-OPS-7CB1, 2026-04-29):** Once you create this
> unit, **start it via `sudo systemctl start llama-swap` rather than running
> the binary from a shell** — and especially not from a VS Code integrated
> terminal. The 2026-04-28 production cutover ran the binary directly from
> a VS Code terminal; the resulting process tree (parent + four
> `llama-server` children) all inherited VS Code's Chromium cgroup
> (`app-org.chromium.Chromium-<pid>.scope`). Anything in that scope is
> subject to VS Code's lifecycle (window reload, Chromium memory pressure,
> child reaping), which leaves no kernel-visible evidence and bypasses
> `Restart=on-failure`. Verify with:
>
> ```bash
> systemctl status llama-swap                 # must be active (running)
> cat /proc/$(pgrep -x llama-swap)/cgroup     # must be /system.slice/llama-swap.service
> ```
>
> If `/proc/$pid/cgroup` shows a `chromium` or `app-` scope, kill llama-swap
> and start it via `sudo systemctl start llama-swap` so it lives under the
> system slice and gets restart supervision.

### 10.3 Record final state

```bash
echo "============================================"
echo "  PRODUCTION DEPLOYMENT COMPLETE"
echo "============================================"
echo ""
echo "Architecture: all-llama.cpp via llama-swap"
echo "Endpoint:     http://promaxgb10-41b1:9000"
echo ""
echo "Models:"
curl -s http://localhost:9000/v1/models 2>/dev/null | python3 -c "
import sys, json
resp = json.load(sys.stdin)
for m in resp.get('data', []):
    print(f'  - {m[\"id\"]}')
" 2>/dev/null || echo "  (query /v1/models to list)"
echo ""
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
echo ""
echo "Config:   /opt/llama-swap/config/config.yaml"
echo "Models:   /opt/llama-swap/models/"
echo "Logs:     /opt/llama-swap/logs/llama-swap.log"
echo "Rollback: scripts/archive-vllm/ + graphiti-mcp-config.yaml.pre-llamacpp.bak"
echo "============================================"
```

---

## Appendix: Rollback Plan

```bash
# 1. Stop llama-swap
sudo systemctl stop llama-swap 2>/dev/null || pkill llama-swap

# 2. Restore Graphiti config
cp ~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml.pre-llamacpp.bak \
   ~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml

# 3. Restore and restart vLLM
cp ~/Projects/appmilla_github/guardkit/scripts/archive-vllm/vllm-graphiti.sh \
   ~/Projects/appmilla_github/guardkit/scripts/
cp ~/Projects/appmilla_github/guardkit/scripts/archive-vllm/vllm-embed.sh \
   ~/Projects/appmilla_github/guardkit/scripts/

cd ~/Projects/appmilla_github/guardkit
./scripts/vllm-graphiti.sh
./scripts/vllm-embed.sh

curl -s http://localhost:8000/health && echo "vLLM Graphiti: OK"
curl -s http://localhost:8001/health && echo "vLLM Embed: OK"
```

---

*Runbook v3 — prepared 2026-04-28*
*Fine-tuned tutor GGUF: ~/fine-tuning/output/gcse-tutor-gemma4-26b-moe/gguf_gguf/gemma-4-26b-a4b-it.Q4_K_M.gguf*
*Modelfile with trained system prompt: same directory*
