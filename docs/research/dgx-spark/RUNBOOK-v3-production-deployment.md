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
      -np 2
    checkEndpoint: /health
    ttl: 0
    concurrencyLimit: 4
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

### 7.2 Restart Graphiti MCP server

```bash
echo "=== Restarting Graphiti MCP server ==="

docker stop graphiti-mcp 2>/dev/null && docker rm graphiti-mcp 2>/dev/null || true

cd ~/Projects/appmilla_github/guardkit
./scripts/graphiti-mcp.sh

sleep 10
curl -s http://localhost:8004/health 2>/dev/null && echo "Graphiti MCP server healthy" || echo "Waiting..."
```

---

## Phase 8: End-to-End Graphiti Seed Test

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
| P8: E2E Graphiti seed | | **No JSON errors** |

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
