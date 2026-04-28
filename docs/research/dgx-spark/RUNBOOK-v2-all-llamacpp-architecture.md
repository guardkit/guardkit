# Runbook v2: All-llama.cpp Architecture on GB10

**Purpose:** Eliminate vLLM entirely. Serve Graphiti, embeddings, and the workhorse model all via llama.cpp behind llama-swap. Validate JSON extraction, embedding quality, tool calling, throughput, and co-existence memory budget.

**Machine:** Dell DGX Spark GB10 (128GB unified memory), hostname `promaxgb10-41b1`
**Predecessor:** `RESULTS-qwen3.6-27b-validation.md` (proved quality, exposed vLLM memory overhead)
**Key insight from v1:** vLLM pre-allocates ~50 GB for a 14 GB model. llama.cpp takes only what the model needs. This runbook validates whether we can reclaim that ~36 GB.
**Expected duration:** ~2-3 hours including model downloads

---

## Phase 0: Pre-flight

### 0.1 Inventory current state

```bash
# What's running right now?
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"

# Current per-process VRAM (GB10-compatible query)
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# Total available
cat /proc/meminfo | grep MemTotal
```

**Record:** which vLLM containers are running and their VRAM. We'll compare against the all-llama.cpp footprint at the end.

### 0.2 Verify llama.cpp build

```bash
~/llama.cpp/build/bin/llama-server --version
```

**If missing or older than v8954:**
```bash
cd ~/llama.cpp
git pull
# Install libssl-dev for -hf download support (missed in v1)
sudo apt install -y libssl-dev
cmake -B build -DGGML_CUDA=ON -DLLAMA_CURL=ON
cmake --build build -j$(nproc)
~/llama.cpp/build/bin/llama-server --version
```

### 0.3 Verify llama-swap is installed

```bash
which llama-swap || echo "NOT INSTALLED"
llama-swap --version 2>/dev/null || echo "NOT INSTALLED"
```

**If missing:** Follow `llama-swap-setup.md` Phase 1 instructions, or:
```bash
# Download latest release binary
curl -L -o /usr/local/bin/llama-swap \
    https://github.com/mostlygeek/llama-swap/releases/latest/download/llama-swap-linux-arm64
chmod +x /usr/local/bin/llama-swap
llama-swap --version
```

### 0.4 Check disk space for model downloads

```bash
df -h ~/.cache/huggingface
# Need ~40 GB free total:
#   Qwen2.5-14B GGUF: ~15 GB
#   nomic-embed GGUF: ~0.3 GB  
#   Qwen3.6-35B-A3B GGUF: ~22 GB
```

---

## Phase 1: Download All Models

Download all three GGUF models before touching any running services.

### 1.1 Qwen2.5-14B-Instruct (Graphiti replacement)

```bash
hf download \
    Qwen/Qwen2.5-14B-Instruct-GGUF \
    --include "*Q8_0.gguf" \
    --local-dir ~/.cache/huggingface/hub/qwen2.5-14b-gguf

# Verify
ls -lh ~/.cache/huggingface/hub/qwen2.5-14b-gguf/*.gguf
```

**Why Q8_0:** Closest quality to the FP8-dynamic currently used by vLLM. If file is too large or unavailable, fall back to Q6_K or Q5_K_M:
```bash
# Alternative if Q8_0 not available or too large:
hf download \
    Qwen/Qwen2.5-14B-Instruct-GGUF \
    --include "*Q5_K_M.gguf" \
    --local-dir ~/.cache/huggingface/hub/qwen2.5-14b-gguf
```

**Note:** Check if the official Qwen GGUF repo exists. If not, use the unsloth version:
```bash
hf download \
    unsloth/Qwen2.5-14B-Instruct-GGUF \
    --include "*Q8_0.gguf" \
    --local-dir ~/.cache/huggingface/hub/qwen2.5-14b-gguf
```

### 1.2 nomic-embed-text-v1.5 (embeddings)

```bash
hf download \
    nomic-ai/nomic-embed-text-v1.5-GGUF \
    --include "*f16.gguf" \
    --local-dir ~/.cache/huggingface/hub/nomic-embed-gguf

# Verify
ls -lh ~/.cache/huggingface/hub/nomic-embed-gguf/*.gguf
```

**Why f16:** Embedding models are tiny (~274 MB). No point quantising.

### 1.3 Qwen3.6-35B-A3B (MoE workhorse)

```bash
hf download \
    unsloth/Qwen3.6-35B-A3B-GGUF \
    --include "*Q4_K_XL.gguf" \
    --local-dir ~/.cache/huggingface/hub/qwen36-35b-a3b-gguf

# Verify
ls -lh ~/.cache/huggingface/hub/qwen36-35b-a3b-gguf/*.gguf
```

**Why Q4_K_XL:** Community standard for this model on GB10. stefan.skoog benchmarked at 48-55 tok/s. MoE at Q4 retains quality well because most expert parameters are dormant per token.

**If unsloth doesn't have the 3.6 GGUF yet**, check bartowski or lmstudio-community:
```bash
# Alternative sources:
hf search model "Qwen3.6-35B-A3B GGUF" --sort downloads
# Or try:
hf download bartowski/Qwen3.6-35B-A3B-GGUF --include "*Q4_K_XL.gguf" \
    --local-dir ~/.cache/huggingface/hub/qwen36-35b-a3b-gguf
```

---

## Phase 2: Test Graphiti on llama.cpp (Standalone)

Before touching the running vLLM services, test llama.cpp on a separate port.

### 2.1 Start Qwen2.5-14B on port 8090

```bash
GGUF_PATH=$(ls ~/.cache/huggingface/hub/qwen2.5-14b-gguf/*.gguf | head -1)

lsof -ti :8090 | xargs kill 2>/dev/null || true

nohup ~/llama.cpp/build/bin/llama-server \
    --model "$GGUF_PATH" \
    --host 0.0.0.0 \
    --port 8090 \
    --alias "qwen2.5-14b-graphiti" \
    --ctx-size 32768 \
    --batch-size 2048 \
    --ubatch-size 2048 \
    --threads 16 \
    -ngl 999 \
    --no-mmap \
    --flash-attn on \
    --jinja \
    --temp 0.0 \
    -np 2 \
    > /tmp/graphiti-llamacpp-test.log 2>&1 &

echo "PID: $!"
echo "Logs: tail -f /tmp/graphiti-llamacpp-test.log"
```

### 2.2 Wait for ready

```bash
until curl -s http://localhost:8090/health | grep -q "ok"; do
    echo "Waiting for Graphiti model..."
    sleep 10
done
echo "Graphiti model ready!"
```

### 2.3 JSON entity extraction test (Graphiti's actual workload)

This mirrors what Graphiti sends for entity extraction — strict JSON output with no markdown:

```bash
curl -s http://localhost:8090/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen2.5-14b-graphiti",
        "temperature": 0,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are an entity extraction system. Extract all entities and relationships from the given text. Respond with ONLY a valid JSON object with two arrays: \"entities\" (each with name, type, description) and \"relationships\" (each with source, target, type, description). No markdown, no explanation."},
            {"role": "user", "content": "The GuardKit AutoBuild system uses a Player-Coach adversarial loop built on the LangChain DeepAgents SDK. The Player agent generates code using Qwen3-Coder-Next served by vLLM on port 8002. The Coach agent validates the output. Both agents run on the Dell DGX Spark GB10. Graphiti stores architectural decisions in FalkorDB using nomic-embed-text-v1.5 for vector embeddings. The Forge orchestrator manages the build pipeline via NATS JetStream."}
        ]
    }' | python3 -c "
import sys, json
try:
    resp = json.load(sys.stdin)
    text = resp['choices'][0]['message']['content']
    data = json.loads(text)
    entities = data.get('entities', [])
    rels = data.get('relationships', [])
    print(f'Valid JSON: YES')
    print(f'Entities: {len(entities)}')
    print(f'Relationships: {len(rels)}')
    for e in entities:
        print(f'  - {e[\"name\"]} ({e[\"type\"]})')
except json.JSONDecodeError as e:
    print(f'INVALID JSON: {e}')
    print(f'Raw: {text[:500]}')
except Exception as e:
    print(f'ERROR: {e}')
"
```

**Pass criteria:**
1. Valid JSON (no markdown fences, no reasoning tokens)
2. 8+ entities extracted (GuardKit, Player, Coach, Qwen3-Coder-Next, vLLM, DGX Spark, Graphiti, FalkorDB, nomic-embed, Forge, NATS, DeepAgents)
3. Relationships are directional and sensible

### 2.4 Stability test — 5 sequential extractions

```bash
PASS_COUNT=0
for i in $(seq 1 5); do
    RESULT=$(curl -s http://localhost:8090/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{
            "model": "qwen2.5-14b-graphiti",
            "temperature": 0,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Extract entities as JSON: {\"entities\": [{\"name\": \"...\", \"type\": \"...\"}]}. Return ONLY valid JSON."},
                {"role": "user", "content": "The Forge orchestrator manages build pipelines on the GB10. It uses NATS JetStream for messaging and coordinates with the Architect Agent for C4 validation. Jarvis routes requests via the CAN bus discovery pattern."}
            ]
        }' | python3 -c "
import sys, json
try:
    resp = json.load(sys.stdin)
    data = json.loads(resp['choices'][0]['message']['content'])
    n = len(data.get('entities', []))
    print(f'Run {$i}: {n} entities — VALID')
except:
    print(f'Run {$i}: INVALID JSON')
" 2>&1)
    echo "$RESULT"
    if echo "$RESULT" | grep -q "VALID"; then
        PASS_COUNT=$((PASS_COUNT + 1))
    fi
done
echo ""
echo "JSON stability: $PASS_COUNT/5 valid"
```

**Pass:** 5/5 valid JSON. This is the make-or-break test for dropping vLLM's xgrammar enforcement.

### 2.5 Measure throughput and memory

```bash
# Throughput
time curl -s http://localhost:8090/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen2.5-14b-graphiti",
        "temperature": 0,
        "max_tokens": 512,
        "messages": [
            {"role": "user", "content": "Write a detailed JSON object describing the architecture of a microservices system with 5 services."}
        ]
    }' > /tmp/graphiti-speed-test.json

# Memory footprint (llama.cpp process only)
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv | grep llama

# Compare with vLLM Graphiti
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" vllm-graphiti 2>/dev/null || echo "vLLM not running"
```

**Record:** llama.cpp VRAM for Qwen2.5-14B vs the ~50 GB that vLLM claimed. Expect ~15-18 GB.

---

## Phase 3: Test Embeddings on llama.cpp (Standalone)

### 3.1 Start nomic-embed on port 8091

```bash
EMBED_PATH=$(ls ~/.cache/huggingface/hub/nomic-embed-gguf/*.gguf | head -1)

lsof -ti :8091 | xargs kill 2>/dev/null || true

nohup ~/llama.cpp/build/bin/llama-server \
    --model "$EMBED_PATH" \
    --host 0.0.0.0 \
    --port 8091 \
    --alias "nomic-embed-text-v1.5" \
    --embedding \
    --ctx-size 8192 \
    --batch-size 8192 \
    --ubatch-size 8192 \
    --threads 16 \
    -ngl 999 \
    --no-mmap \
    -np 4 \
    > /tmp/embed-llamacpp-test.log 2>&1 &

echo "PID: $!"
```

### 3.2 Wait and verify

```bash
until curl -s http://localhost:8091/health | grep -q "ok"; do
    echo "Waiting for embedding model..."
    sleep 5
done
echo "Embedding model ready!"
```

### 3.3 Embedding dimension test

```bash
curl -s http://localhost:8091/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{
        "model": "nomic-embed-text-v1.5",
        "input": "The GuardKit AutoBuild system uses adversarial cooperation."
    }' | python3 -c "
import sys, json
resp = json.load(sys.stdin)
emb = resp['data'][0]['embedding']
print(f'Dimensions: {len(emb)}')
print(f'First 5 values: {emb[:5]}')
print(f'Non-zero: {sum(1 for v in emb if abs(v) > 1e-8)}')
assert len(emb) == 768, f'FAIL: Expected 768 dims, got {len(emb)}'
print('PASS: 768 dimensions confirmed')
"
```

**Pass:** Exactly 768 dimensions (must match FalkorDB index).

### 3.4 Batch embedding test

```bash
curl -s http://localhost:8091/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{
        "model": "nomic-embed-text-v1.5",
        "input": [
            "First document about architecture decisions.",
            "Second document about NATS JetStream messaging.",
            "Third document about Player-Coach adversarial loops."
        ]
    }' | python3 -c "
import sys, json
resp = json.load(sys.stdin)
for d in resp['data']:
    print(f'  Index {d[\"index\"]}: {len(d[\"embedding\"])} dims')
print(f'Total embeddings: {len(resp[\"data\"])}')
assert len(resp['data']) == 3, 'FAIL: Expected 3 embeddings'
assert all(len(d['embedding']) == 768 for d in resp['data']), 'FAIL: Dimension mismatch'
print('PASS: Batch embeddings working')
"
```

**Pass:** 3 embeddings returned, all 768 dimensions.

---

## Phase 4: Test MoE Workhorse on llama.cpp (Standalone)

### 4.1 Start Qwen3.6-35B-A3B on port 8092

```bash
MOE_PATH=$(ls ~/.cache/huggingface/hub/qwen36-35b-a3b-gguf/*.gguf | head -1)

lsof -ti :8092 | xargs kill 2>/dev/null || true

nohup ~/llama.cpp/build/bin/llama-server \
    --model "$MOE_PATH" \
    --host 0.0.0.0 \
    --port 8092 \
    --alias "qwen36-workhorse" \
    --ctx-size 65536 \
    --batch-size 2048 \
    --ubatch-size 2048 \
    --threads 16 \
    -ngl 999 \
    --no-mmap \
    --flash-attn on \
    --jinja \
    --reasoning off \
    --temp 0.6 \
    --top-p 0.95 \
    -np 1 \
    > /tmp/moe-workhorse-test.log 2>&1 &

echo "PID: $!"
echo "Logs: tail -f /tmp/moe-workhorse-test.log"
```

### 4.2 Wait for ready

```bash
until curl -s http://localhost:8092/health | grep -q "ok"; do
    echo "Waiting for MoE workhorse..."
    sleep 10
done
echo "MoE workhorse ready!"
```

### 4.3 Tool calling test (Player role)

Same test as v1 runbook P2.2, adapted for the MoE model:

```bash
curl -s http://localhost:8092/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen36-workhorse",
        "max_tokens": 1024,
        "tools": [
            {
                "name": "rag_retrieval",
                "description": "Retrieve relevant chunks from the RAG knowledge base for a given query.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "collection": {"type": "string", "description": "The ChromaDB collection name"},
                        "top_k": {"type": "integer", "description": "Number of results to return", "default": 5}
                    },
                    "required": ["query", "collection"]
                }
            },
            {
                "name": "write_output",
                "description": "Write a training example to the output file, routed by layer.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "object", "description": "The training example content"},
                        "layer": {"type": "string", "enum": ["behaviour", "knowledge"], "description": "Output routing layer"}
                    },
                    "required": ["content", "layer"]
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Search the gcse-english collection for information about AQA mark schemes for Paper 1 Question 5 creative writing, then generate a training example about how to structure a descriptive writing response."}
        ]
    }' | python3 -c "
import sys, json
resp = json.load(sys.stdin)
for block in resp.get('content', []):
    if block['type'] == 'tool_use':
        print(f'Tool called: {block[\"name\"]}')
        print(f'Input: {json.dumps(block[\"input\"], indent=2)}')
        print('PASS: tool_use block present')
    elif block['type'] == 'text':
        print(f'Text: {block[\"text\"][:200]}...')
print(f'Stop reason: {resp.get(\"stop_reason\", \"unknown\")}')
"
```

**Pass:** `tool_use` block with `rag_retrieval`, correct parameters, `stop_reason: tool_use`.

### 4.4 Throughput test

```bash
echo "Starting throughput test..."
START=$(date +%s%N)

curl -s http://localhost:8092/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen36-workhorse",
        "max_tokens": 512,
        "messages": [
            {"role": "user", "content": "Write a Python async function that connects to a NATS server, subscribes to \"fleet.register\", and processes AgentRegistrationPayload messages. Include proper error handling, connection retry logic, and type hints. Use the nats-py library."}
        ]
    }' > /tmp/moe-speed-test.json

END=$(date +%s%N)
ELAPSED=$(( (END - START) / 1000000 ))

# Count output tokens from server logs
TOKENS=$(grep "eval time" /tmp/moe-workhorse-test.log | tail -1)
echo "Wall time: ${ELAPSED}ms"
echo "Server stats: $TOKENS"
echo ""
echo "Response preview:"
cat /tmp/moe-speed-test.json | python3 -c "
import sys, json
resp = json.load(sys.stdin)
text = resp['content'][0]['text'] if resp.get('content') else 'NO CONTENT'
words = len(text.split())
print(f'Words: {words}')
print(text[:300])
"
```

**Expected:** 30-50 tok/s for MoE Q4_K_XL (vs 8.35 tok/s for the dense 27B in v1). This is the critical speed test.

### 4.5 Coach reasoning test (same as v1 P4.2)

```bash
curl -s http://localhost:8092/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen36-workhorse",
        "max_tokens": 512,
        "messages": [
            {"role": "user", "content": "You are a pipeline orchestrator making a confidence-gated decision. Given these Coach scores for 3 tasks in a feature build, decide whether to auto-approve, flag for review, or hard-stop. Respond with JSON only: {\"decision\": \"auto-approve\"|\"flag-review\"|\"hard-stop\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}\n\nTask 1: score 0.92 (all criteria met)\nTask 2: score 0.78 (1 warning)\nTask 3: score 0.45 (2 critical issues)\n\nThresholds: auto-approve > 0.85 all tasks, flag-review if any 0.5-0.85, hard-stop if any < 0.5.\n\nReturn ONLY JSON."}
        ]
    }' | python3 -c "
import sys, json
resp = json.load(sys.stdin)
text = resp['content'][0]['text']
# Strip any markdown fencing
text = text.strip().removeprefix('\`\`\`json').removesuffix('\`\`\`').strip()
data = json.loads(text)
print(f'Decision: {data[\"decision\"]}')
print(f'Confidence: {data.get(\"confidence\", \"missing\")}')
print(f'Reasoning: {data.get(\"reasoning\", \"missing\")[:200]}')
correct = data['decision'] == 'hard-stop'
print(f'Correct decision: {\"YES\" if correct else \"NO (expected hard-stop)\"}')
"
```

**Pass:** `hard-stop` decision citing Task 3 below threshold.

---

## Phase 5: Three-Model Co-existence Test

All three llama.cpp instances should be running from Phases 2-4 (ports 8090, 8091, 8092).

### 5.1 Verify all three are healthy

```bash
echo "Graphiti (8090): $(curl -s http://localhost:8090/health)"
echo "Embeddings (8091): $(curl -s http://localhost:8091/health)"
echo "Workhorse (8092): $(curl -s http://localhost:8092/health)"
```

### 5.2 Measure combined VRAM footprint

```bash
echo "=== llama.cpp processes ==="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv | grep -i llama

echo ""
echo "=== vLLM processes (for comparison) ==="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv | grep -i python

echo ""
echo "=== All GPU memory users ==="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

**Record:** Total VRAM for all three llama.cpp models. Compare against the v1 baseline (~70 GB with vLLM Graphiti + embed + Qwen3.6-27B).

**Expected:** ~35-40 GB total (14B model ~15 GB + embed ~0.5 GB + 35B MoE ~20 GB), leaving ~85-90 GB headroom.

### 5.3 Concurrent request test

Fire requests at all three simultaneously:

```bash
# Run all three concurrently, wait for all to finish
echo "Starting concurrent requests..."

# Graphiti extraction
curl -s http://localhost:8090/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5-14b-graphiti","temperature":0,"max_tokens":512,"response_format":{"type":"json_object"},"messages":[{"role":"system","content":"Extract entities as JSON."},{"role":"user","content":"The Forge manages builds via NATS. Jarvis routes intent."}]}' \
    > /tmp/concurrent-graphiti.json &
PID_G=$!

# Embedding
curl -s http://localhost:8091/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model":"nomic-embed-text-v1.5","input":"Test embedding during concurrent load."}' \
    > /tmp/concurrent-embed.json &
PID_E=$!

# Workhorse coding
curl -s http://localhost:8092/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{"model":"qwen36-workhorse","max_tokens":256,"messages":[{"role":"user","content":"Write a Python function to parse NATS subject strings."}]}' \
    > /tmp/concurrent-workhorse.json &
PID_W=$!

wait $PID_G $PID_E $PID_W

echo "Graphiti: $(python3 -c "import json; d=json.load(open('/tmp/concurrent-graphiti.json')); print('OK' if 'choices' in d else 'FAIL')")"
echo "Embed: $(python3 -c "import json; d=json.load(open('/tmp/concurrent-embed.json')); print(f'OK - {len(d[\"data\"][0][\"embedding\"])} dims') if 'data' in d else print('FAIL')")"
echo "Workhorse: $(python3 -c "import json; d=json.load(open('/tmp/concurrent-workhorse.json')); print('OK') if 'content' in d else print('FAIL')")"
```

**Pass:** All three return valid responses simultaneously. No OOM, no crashes.

---

## Phase 6: Switchover Test — Stop vLLM, Run Graphiti Through llama.cpp

This is the real end-to-end test. If you have `guardkit graphiti seed` available, run it against the llama.cpp backend.

### 6.1 Reconfigure Graphiti to point at llama.cpp

```bash
# Check current Graphiti LLM endpoint config
cat ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml
```

Temporarily update the endpoint to point at llama.cpp on :8090:
```bash
# Back up current config
cp ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml \
   ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml.bak

# If the config uses base_url or similar, update it to http://localhost:8090
# The exact field name depends on your graphiti.yaml structure.
# Key fields to change:
#   llm_base_url: http://localhost:8090/v1  (was http://localhost:8000/v1)
#   embedding_base_url: http://localhost:8091/v1  (was http://localhost:8001/v1)
#   llm_model: qwen2.5-14b-graphiti  (or whatever the model field needs to be)
```

### 6.2 Test Graphiti seed on a small document

```bash
cd ~/Projects/appmilla_github/guardkit

# Seed one small document to validate the round-trip
guardkit graphiti seed docs/decisions/DECISION-DF-001-local-first-inference-on-dark-factory-critical-path.md --verbose 2>&1 | tee /tmp/graphiti-llamacpp-seed.log
```

**Pass criteria:**
1. Seed completes without JSON parse errors
2. Entity extraction produces sensible entities
3. Embedding storage succeeds
4. No `xgrammar` or `json_schema` errors in the log

**If this fails with JSON errors:** llama.cpp's `response_format: json_object` enforcement isn't strict enough for Graphiti. This is the go/no-go gate for dropping vLLM entirely. Record the failure mode — it may be fixable with GBNF grammar or a system prompt adjustment.

### 6.3 Restore config

```bash
# Restore original config regardless of result
cp ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml.bak \
   ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml
```

---

## Phase 7: Decision Gate

| Test | Result | Notes |
|---|---|---|
| P1: All models downloaded | | |
| P2.3: Graphiti JSON extraction (single) | | |
| P2.4: Graphiti JSON stability (5/5) | | |
| P2.5: Graphiti throughput + memory | | Record VRAM |
| P3.3: Embedding dimensions (768) | | |
| P3.4: Batch embeddings | | |
| P4.3: MoE tool calling | | |
| P4.4: MoE throughput (tok/s) | | **Must exceed 20 tok/s** |
| P4.5: MoE Coach reasoning | | |
| P5.2: Combined VRAM (3 models) | | Record total |
| P5.3: Concurrent requests | | |
| P6.2: Graphiti seed end-to-end | | **Go/no-go for dropping vLLM** |

### Decision matrix

**All pass → Go all-in on llama.cpp:**
- Stop all vLLM containers
- Deploy production llama-swap config (Phase 8)
- Delete `vllm-graphiti.sh`, `vllm-embed.sh`, `vllm-agentic-factory.sh` from active use (archive)

**P6.2 fails (Graphiti JSON) → Partial migration:**
- Keep vLLM for Graphiti only (the one role where xgrammar enforcement matters)
- Move embeddings + workhorse to llama.cpp via llama-swap
- Still a significant win — reclaims the workhorse from vLLM's memory overhead

**P4.4 fails (MoE speed < 20 tok/s) → Investigate:**
- Check if llama.cpp MoE kernels are suboptimal on GB10
- Try vLLM serving for the MoE model instead (AEON-7 container)
- The MoE should NOT hit the same bandwidth wall as dense — if it does, something is wrong

**P3.3 fails (wrong embedding dimensions) → Keep vLLM for embeddings:**
- Only affects the embedding model
- Graphiti + workhorse can still move to llama.cpp

---

## Phase 8: Production llama-swap Config

Deploy only after Phase 7 passes. This replaces the current `llama-swap-config.yaml` entirely.

```yaml
# llama-swap config — all-llama.cpp architecture
# ================================================
# Single process tree. No vLLM. Every model takes only what it needs.
# Total footprint: ~35-40 GB (vs ~85 GB with vLLM)
# Headroom: ~85-90 GB for KV cache and future models
#
# Port: :9000 (unchanged — all agents point here)

healthCheckTimeout: 300
globalTTL: 0                      # forever group models never unload
startPort: 5800
includeAliasesInList: true
logLevel: info

models:
  # ============================================================
  # FOREVER GROUP — always loaded, never evicted
  # ============================================================

  "qwen-graphiti":
    name: "Graphiti entity extraction (Qwen2.5-14B Q8_0)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/qwen2.5-14b/qwen2.5-14b-instruct-q8_0.gguf
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

  "nomic-embed":
    name: "Embeddings (nomic-embed-text-v1.5 f16)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/nomic-embed/nomic-embed-text-v1.5-f16.gguf
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

  # ============================================================
  # BUILDERS GROUP — MoE workhorse + fine-tuned specialists
  # ============================================================

  "qwen36-workhorse":
    name: "AutoBuild + Coach + Forge + Jarvis (Qwen3.6-35B-A3B Q4_K_XL)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/qwen36-35b/qwen3.6-35b-a3b-q4_k_xl.gguf
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
    ttl: 1800
    concurrencyLimit: 2
    aliases:
      - "autobuild-player"
      - "coach"
      - "jarvis-reasoner"
      - "forge-orchestrator"
      - "dataset-factory"
      - "claude-sonnet-4-6"
      - "claude-opus-4-7"

  "gemma4-specialist":
    name: "Fine-tuned specialist (Gemma 4 26B A4B MoE)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/gemma4-26b/gemma4-26b-a4b.gguf
      --alias gemma4-specialist
      --ctx-size 32768
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      -np 1
    checkEndpoint: /health
    ttl: 1800
    concurrencyLimit: 1
    aliases:
      - "architect-agent"
      - "study-tutor"
      - "product-owner"

groups:
  "forever":
    persistent: true
    swap: false
    exclusive: false
    members:
      - "qwen-graphiti"
      - "nomic-embed"

  "builders":
    swap: true
    exclusive: true
    members:
      - "qwen36-workhorse"
      - "gemma4-specialist"

hooks:
  on_startup:
    preload:
      - "qwen36-workhorse"
```

### Model file placement

After validation passes, copy models to the production paths:

```bash
sudo mkdir -p /opt/llama-swap/models/{qwen2.5-14b,nomic-embed,qwen36-35b,gemma4-26b}
sudo chown -R $USER:$USER /opt/llama-swap/models

# Copy from download cache to production paths
cp ~/.cache/huggingface/hub/qwen2.5-14b-gguf/*.gguf /opt/llama-swap/models/qwen2.5-14b/
cp ~/.cache/huggingface/hub/nomic-embed-gguf/*.gguf /opt/llama-swap/models/nomic-embed/
cp ~/.cache/huggingface/hub/qwen36-35b-a3b-gguf/*.gguf /opt/llama-swap/models/qwen36-35b/
# Gemma 4 GGUF — when available from fine-tuning pipeline

# Update config filenames to match actual downloaded files
ls -la /opt/llama-swap/models/*/
```

### Stop vLLM and start llama-swap

```bash
# Stop all vLLM containers
docker stop vllm-graphiti vllm-embedding 2>/dev/null
docker rm vllm-graphiti vllm-embedding 2>/dev/null

# Start llama-swap with the new config
llama-swap --config /opt/llama-swap/config/config.yaml --listen :9000
```

---

## Phase 9: Cleanup

```bash
# Stop all test servers from Phases 2-4
lsof -ti :8090 | xargs kill 2>/dev/null || true
lsof -ti :8091 | xargs kill 2>/dev/null || true
lsof -ti :8092 | xargs kill 2>/dev/null || true

# Restore Graphiti config if changed
if [ -f ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml.bak ]; then
    cp ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml.bak \
       ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml
    rm ~/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml.bak
fi

# Verify original services still running (if not migrated)
docker ps --format "table {{.Names}}\t{{.Status}}" | grep vllm
```

---

## Appendix: Rollback Plan

If the all-llama.cpp architecture fails in production:

```bash
# Stop llama-swap
pkill llama-swap

# Restart vLLM services
~/Projects/appmilla_github/guardkit/scripts/vllm-graphiti.sh
~/Projects/appmilla_github/guardkit/scripts/vllm-embed.sh

# Verify
curl -s http://localhost:8000/health
curl -s http://localhost:8001/health
```

The vLLM scripts and Docker images remain on the GB10. Nothing is deleted.

---

*Runbook v2 — prepared 2026-04-28*
*Cross-references: RESULTS-qwen3.6-27b-validation.md, POST-VALIDATION-model-strategy-revision.md, llama-swap-setup.md*
