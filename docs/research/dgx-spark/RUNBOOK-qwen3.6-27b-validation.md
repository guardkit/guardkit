# Runbook: Qwen3.6-27B Validation on GB10

**Purpose:** Validate Qwen3.6-27B as a multi-purpose workhorse model on the GB10, testing against three fleet roles: Graphiti entity extraction, AutoBuild Player (tool calling + code), and Coach/Forge reasoning.

**Machine:** Dell DGX Spark GB10 (128GB unified memory), hostname `promaxgb10-41b1`
**Prerequisite services running:** vLLM Graphiti on :8000 (Qwen2.5-14B), vLLM embeddings on :8001 (nomic-embed)
**Expected duration:** ~2 hours including model download

---

## Phase 0: Pre-flight Checks

### 0.1 Confirm existing services are running

```bash
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8001/health | jq .
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Pass:** Both return healthy. Note current VRAM usage — Graphiti + embed should be ~15 GB.

### 0.2 Confirm llama.cpp is built

```bash
~/llama.cpp/build/bin/llama-server --version
```

**If missing:** Build it:
```bash
cd ~
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build -j$(nproc)
~/llama.cpp/build/bin/llama-server --version
```

### 0.3 Check available disk space for model download

```bash
df -h ~/.cache/huggingface
```

**Need:** ~20 GB free for Q4_K_M GGUF.

---

## Phase 1: Download and Serve Qwen3.6-27B

### 1.1 Download Q4_K_M GGUF

This is the fastest path — smallest footprint (~16 GB), best llama-swap compatibility, 33-45 tok/s expected.

```bash
# Using huggingface-cli (preferred — shows progress)
pip install -U huggingface-hub --break-system-packages 2>/dev/null
huggingface-cli download \
    unsloth/Qwen3.6-27B-GGUF \
    --include "Qwen3.6-27B-Q4_K_M.gguf" \
    --local-dir ~/.cache/huggingface/hub/qwen3.6-27b-gguf

# Verify download
ls -lh ~/.cache/huggingface/hub/qwen3.6-27b-gguf/Qwen3.6-27B-Q4_K_M.gguf
```

**Pass:** File exists, ~16 GB.

**Alternative — download via llama-server -hf flag (auto-downloads):**
Skip this step and use `-hf "unsloth/Qwen3.6-27B-GGUF:Q4_K_M"` in step 1.2. First run will download automatically.

### 1.2 Start llama-server on port 8080

Port 8080 avoids conflict with existing Graphiti (:8000), embeddings (:8001), and vllm-serve (:8002).

```bash
# Kill anything on 8080 first
lsof -ti :8080 | xargs kill 2>/dev/null || true

# Start with Anthropic Messages API support
nohup ~/llama.cpp/build/bin/llama-server \
    -hf "unsloth/Qwen3.6-27B-GGUF:Q4_K_M" \
    --host 0.0.0.0 \
    --port 8080 \
    --alias "qwen3.6-27b" \
    --ctx-size 32768 \
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
    > /tmp/qwen36-27b-test.log 2>&1 &

echo "PID: $!"
echo "Logs: tail -f /tmp/qwen36-27b-test.log"
```

### 1.3 Wait for model to load and verify

```bash
# Poll until ready (may take 2-5 min on first download)
until curl -s http://localhost:8080/health | grep -q "ok"; do
    echo "Waiting for model to load..."
    sleep 10
done
echo "Model ready!"

# Verify model identity
curl -s http://localhost:8080/v1/models | jq '.data[].id'
```

**Pass:** Health returns ok. Model ID shows.

### 1.4 Verify VRAM co-existence with Graphiti

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
# Also confirm Graphiti is still healthy
curl -s http://localhost:8000/health | jq .
```

**Pass:** Total VRAM usage should be ~31 GB (Graphiti 14 + embed 1 + Qwen3.6 16). Graphiti still healthy. This is the key co-existence test.

---

## Phase 2: Test A — Tool Calling (AutoBuild Player role)

This tests whether Qwen3.6-27B can replace Qwen3-Coder-Next for AutoBuild's Player agent, which needs Anthropic Messages API with tool_use/tool_result blocks.

### 2.1 Basic Anthropic Messages API test

```bash
curl -s http://localhost:8080/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen3.6-27b",
        "max_tokens": 256,
        "messages": [
            {"role": "user", "content": "Write a Python function that reads a JSON file and returns a sorted list of keys. Include error handling."}
        ]
    }' | jq '.content[0].text' -r
```

**Pass:** Returns valid Python code with try/except handling. Check for sensible structure, not just any output.

### 2.2 Tool calling round-trip test

This simulates the Player agent's tool calling pattern (rag_retrieval, write_output):

```bash
curl -s http://localhost:8080/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen3.6-27b",
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
    }' | jq .
```

**Pass criteria:**
1. Response contains a `tool_use` content block (not just text)
2. The tool_use block calls `rag_retrieval` with `collection` and `query` fields
3. The JSON is valid and parseable
4. Tool name and parameters match the schema

### 2.3 Multi-turn tool calling test

After the tool call, send a mock tool result and check the model continues correctly:

```bash
# Save the tool_use_id from 2.2, then:
curl -s http://localhost:8080/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen3.6-27b",
        "max_tokens": 2048,
        "tools": [
            {
                "name": "rag_retrieval",
                "description": "Retrieve relevant chunks from the RAG knowledge base.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "collection": {"type": "string"},
                        "top_k": {"type": "integer", "default": 5}
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
                        "content": {"type": "object"},
                        "layer": {"type": "string", "enum": ["behaviour", "knowledge"]}
                    },
                    "required": ["content", "layer"]
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Search the gcse-english collection for AQA Paper 1 Q5 mark scheme criteria, then write a behaviour-layer training example."},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "tool_001", "name": "rag_retrieval", "input": {"query": "AQA Paper 1 Question 5 mark scheme creative writing", "collection": "gcse-english", "top_k": 5}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tool_001", "content": "AQA Paper 1 Q5 assesses: AO5 Content (communicate clearly, organise information, use vocabulary, sentence structure) and AO6 Technical accuracy (sentence demarcation, spelling, punctuation). Band 4 (13-16 marks): writing is compelling with varied complex ideas; structured for effect; extensive vocabulary; varied sentence forms. Band 3 (9-12 marks): writing is engaging with connected ideas; coherent paragraphs; vocabulary chosen for effect."}]
        ]
    }' | jq .
```

**Pass criteria:**
1. Model calls `write_output` with a well-structured training example
2. The `layer` field is set to `"behaviour"`
3. The content contains a plausible GCSE tutoring dialogue in ShareGPT format
4. The model doesn't hallucinate tool names that weren't provided

---

## Phase 3: Test B — JSON Entity Extraction (Graphiti role)

This tests whether Qwen3.6-27B could potentially replace Qwen2.5-14B for Graphiti entity extraction. Note: this is a "nice to have" — the plan is to keep Qwen2.5-14B for Graphiti regardless. But it validates the model's structured output capability.

### 3.1 Entity extraction test

```bash
curl -s http://localhost:8080/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen3.6-27b",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "Extract all entities and relationships from this text as a JSON object with \"entities\" (array of {name, type, description}) and \"relationships\" (array of {source, target, type, description}). Return ONLY valid JSON, no markdown, no explanation.\n\nText: The GuardKit AutoBuild system uses a Player-Coach adversarial loop. The Player agent generates code using Qwen3-Coder-Next served by vLLM on port 8002. The Coach agent validates the output using GPT-OSS 120B. Both agents communicate via the LangChain DeepAgents SDK running on the Dell DGX Spark GB10. Graphiti stores architectural decisions in FalkorDB."}
        ]
    }' | jq .
```

**Pass criteria:**
1. Response is valid JSON (parseable by jq)
2. Entities include: GuardKit AutoBuild, Player, Coach, Qwen3-Coder-Next, GPT-OSS 120B, vLLM, LangChain DeepAgents SDK, DGX Spark GB10, Graphiti, FalkorDB
3. Relationships are directional and make sense
4. No reasoning tokens or markdown fences leaked into the JSON output

### 3.2 Repeated extraction stability test

Run the same prompt 3 times and check consistency:

```bash
for i in 1 2 3; do
    echo "=== Run $i ==="
    curl -s http://localhost:8080/v1/messages \
        -H "Content-Type: application/json" \
        -H "x-api-key: test" \
        -d '{
            "model": "qwen3.6-27b",
            "max_tokens": 512,
            "messages": [
                {"role": "user", "content": "Extract entities as JSON: {\"entities\": [{\"name\": \"...\", \"type\": \"...\"}]}. Return ONLY JSON.\n\nThe Forge orchestrator manages build pipelines on the GB10. It uses NATS JetStream for event messaging and coordinates with the Architect Agent for C4 diagram validation."}
            ]
        }' | jq -r '.content[0].text' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Entities: {len(d.get(\"entities\",[]))}'); print('Valid JSON: YES')" 2>&1 || echo "INVALID JSON"
    echo ""
done
```

**Pass:** All 3 runs produce valid JSON with consistent entity counts (within ±1).

---

## Phase 4: Test C — Reasoning Quality (Coach/Forge role)

This tests whether Qwen3.6-27B can serve as the Coach (code review, quality evaluation) and Forge (confidence-gated decisions).

### 4.1 Code review test (Coach role)

```bash
curl -s http://localhost:8080/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen3.6-27b",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "You are a Coach agent reviewing code. Evaluate this implementation against the acceptance criteria and respond with a JSON object: {\"decision\": \"accept\" or \"reject\", \"score\": 0.0-1.0, \"issues\": [{\"severity\": \"critical\"|\"warning\"|\"info\", \"description\": \"...\"}], \"summary\": \"...\"}. Return ONLY the JSON.\n\nAcceptance criteria:\n- Function must handle empty input\n- Must return sorted results\n- Must include type hints\n\nCode:\n```python\ndef process_items(items: list[str]) -> list[str]:\n    return sorted(items)\n```"}
        ]
    }' | jq .
```

**Pass criteria:**
1. Valid JSON output
2. Should identify the missing empty-input check (at minimum a warning)
3. Score should be 0.5-0.8 (partial pass — type hints present, sorting works, but empty input not explicitly handled)
4. Decision should be "reject" or score < 0.8 due to the missing criterion

### 4.2 Confidence gate test (Forge role)

```bash
curl -s http://localhost:8080/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen3.6-27b",
        "max_tokens": 512,
        "messages": [
            {"role": "user", "content": "You are a pipeline orchestrator making a confidence-gated decision. Given these Coach scores for 3 tasks in a feature build, decide whether to auto-approve the feature, flag for human review, or hard-stop. Respond with JSON: {\"decision\": \"auto-approve\"|\"flag-review\"|\"hard-stop\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}\n\nTask 1: score 0.92 (all acceptance criteria met)\nTask 2: score 0.78 (1 warning: missing edge case test)\nTask 3: score 0.45 (2 critical issues: function signature mismatch, import missing)\n\nThresholds: auto-approve > 0.85 all tasks, flag-review if any task 0.5-0.85, hard-stop if any task < 0.5.\n\nReturn ONLY JSON."}
        ]
    }' | jq .
```

**Pass criteria:**
1. Valid JSON
2. Decision should be "hard-stop" (Task 3 at 0.45 is below the 0.5 threshold)
3. Reasoning should reference Task 3 specifically
4. Confidence of the gate decision itself should be high (>0.8) since the rules are clear

---

## Phase 5: Performance Measurement

### 5.1 Generation speed test

```bash
# Time a coding task (representative of AutoBuild Player workload)
time curl -s http://localhost:8080/v1/messages \
    -H "Content-Type: application/json" \
    -H "x-api-key: test" \
    -d '{
        "model": "qwen3.6-27b",
        "max_tokens": 512,
        "messages": [
            {"role": "user", "content": "Write a Python async function that connects to a NATS server, subscribes to \"fleet.register\", and processes AgentRegistrationPayload messages. Include proper error handling, connection retry logic, and type hints. Use the nats-py library."}
        ]
    }' | jq -r '.content[0].text' | wc -w

# Check server metrics
curl -s http://localhost:8080/metrics 2>/dev/null || echo "Metrics endpoint not available (llama.cpp)"
```

**Record:** Wall-clock time, word count, and calculate approximate tok/s.

### 5.2 Concurrent Graphiti test

While Qwen3.6-27B is loaded and serving, confirm Graphiti is still responsive:

```bash
# Simple Graphiti health check
curl -s http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Extract entities from: The Player agent generates code."}
        ]
    }' | jq -r '.choices[0].message.content'
```

**Pass:** Graphiti responds normally while Qwen3.6-27B is loaded. This confirms co-existence.

---

## Phase 6: Decision Gate

Record results in this table:

| Test | Pass/Fail | Notes |
|---|---|---|
| P0: Graphiti + embed running | | |
| P0: llama.cpp built | | |
| P1: Model downloaded and serving | | |
| P1: VRAM co-existence (~31 GB total) | | |
| P2.1: Basic code generation | | |
| P2.2: Single tool call | | |
| P2.3: Multi-turn tool calling | | |
| P3.1: JSON entity extraction | | |
| P3.2: Extraction stability (3/3 valid) | | |
| P4.1: Coach code review (correct JSON + reasoning) | | |
| P4.2: Forge confidence gate (correct decision) | | |
| P5.1: Generation speed (tok/s) | | |
| P5.2: Concurrent Graphiti still works | | |

### Decision criteria

**All tests pass → Promote to builders group in llama-swap config:**
- Add `qwen3.6-27b` as a third member of the builders group
- Test as AutoBuild Player on one real FEAT task
- If FEAT task quality matches Coder-Next, promote to forever group (always-on)

**Tool calling fails (P2) → Fallback:**
- Qwen3.6-27B may still work for Coach/Forge/reasoning (if P4 passes)
- Keep Coder-Next for Player role
- Investigate `--tool-call-parser qwen3_coder` if using vLLM instead of llama.cpp

**JSON extraction fails (P3) → No impact:**
- Keep Qwen2.5-14B for Graphiti (already the plan)
- Qwen3.6-27B still valid for other roles if P2 and P4 pass

**Reasoning fails (P4) → Significant:**
- If structured JSON evaluation quality is poor, the model can't serve as Coach
- Fall back to GPT-OSS 120B for Coach/Forge roles
- Qwen3.6-27B may still work as Player (if P2 passes)

**Speed < 20 tok/s → Consider FP8 + MTP path instead:**
- Try vLLM with MTP: `--speculative-config '{"method": "mtp", "num_speculative_tokens": 3}'`
- Or try PrismaQuant 5.5bit: `rdtand/Qwen3.6-27B-PrismaQuant-5.5bit-vllm`

---

## Phase 7: Cleanup

```bash
# Stop the test server
kill $(lsof -ti :8080) 2>/dev/null

# Confirm Graphiti unaffected
curl -s http://localhost:8000/health | jq .

# VRAM returned
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

---

## Appendix: llama-swap Integration (after validation passes)

If all tests pass, add to `guardkit/docs/research/dgx-spark/llama-swap-config.yaml`:

```yaml
  "qwen3.6-27b":
    name: "Multi-purpose workhorse (Qwen3.6-27B Q4_K_M)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/qwen3.6-27b/Qwen3.6-27B-Q4_K_M.gguf
      --alias qwen3.6-27b
      --ctx-size 32768
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
    checkEndpoint: /health
    ttl: 1800
    concurrencyLimit: 2
    aliases:
      - "autobuild-player"
      - "coach"
      - "jarvis-reasoner"
      - "dataset-factory"
      - "claude-sonnet-4-6"
```

Then copy model weights to the llama-swap models directory:

```bash
sudo mkdir -p /opt/llama-swap/models/qwen3.6-27b
sudo cp ~/.cache/huggingface/hub/qwen3.6-27b-gguf/Qwen3.6-27B-Q4_K_M.gguf \
    /opt/llama-swap/models/qwen3.6-27b/
```
