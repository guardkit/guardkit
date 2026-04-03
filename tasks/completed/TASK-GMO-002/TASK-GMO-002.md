---
id: TASK-GMO-002
title: "Test json_schema enforcement with Ollama for Graphiti compatibility"
status: completed
updated: 2026-04-03T14:10:00Z
created: 2026-04-03T00:00:00Z
priority: high
tags: [graphiti, ollama, json-schema, testing]
task_type: implementation
parent_review: TASK-REV-GMAC
feature_id: FEAT-GMO
implementation_mode: direct
wave: 1
complexity: 3
depends_on:
  - TASK-GMO-001
---

# Task: Test json_schema enforcement with Ollama for Graphiti compatibility

## Description

Graphiti uses the OpenAI Python SDK to send requests with `response_format={"type": "json_schema", "json_schema": {...}}`.
Ollama has a [known compatibility gap](https://github.com/ollama/ollama/issues/10001) where this format may be ignored.
This task tests whether the current Ollama version handles it correctly.

## Steps

### Test 1: OpenAI-style json_schema via curl

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:14b-instruct-q4_K_M",
    "messages": [
      {"role": "system", "content": "You are an entity extraction assistant. Extract entities as JSON."},
      {"role": "user", "content": "John Smith went to Apple headquarters in Cupertino."}
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "entities",
        "schema": {
          "type": "object",
          "properties": {
            "entities": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "name": {"type": "string"},
                  "type": {"type": "string"}
                },
                "required": ["name", "type"]
              }
            }
          },
          "required": ["entities"]
        }
      }
    }
  }'
```

### Test 2: OpenAI Python SDK (mimicking Graphiti)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

response = client.chat.completions.create(
    model="qwen2.5:14b-instruct-q4_K_M",
    messages=[
        {"role": "system", "content": "Extract entities as JSON."},
        {"role": "user", "content": "John Smith went to Apple headquarters in Cupertino."}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "entities",
            "schema": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"}
                            },
                            "required": ["name", "type"]
                        }
                    }
                },
                "required": ["entities"]
            }
        }
    }
)
print(response.choices[0].message.content)
```

### Test 3: If json_schema fails — try Ollama native format

```bash
curl -X POST http://localhost:8000/api/chat \
  -d '{
    "model": "qwen2.5:14b-instruct-q4_K_M",
    "messages": [{"role": "user", "content": "Extract entities from: John Smith at Apple in Cupertino"}],
    "format": {
      "type": "object",
      "properties": {
        "entities": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "type": {"type": "string"}
            },
            "required": ["name", "type"]
          }
        }
      },
      "required": ["entities"]
    },
    "stream": false
  }'
```

## Decision Gate

- If Test 1 or 2 produces valid schema-compliant JSON → **Ollama is confirmed, proceed to TASK-GMO-003**
- If Test 1/2 fails but Test 3 works → Graphiti may need a patch to use Ollama's native format (escalate)
- If all tests fail → **Fall back to llama-server** (see review report Option B)

### llama-server fallback steps

```bash
brew install llama.cpp
# Download GGUF model
huggingface-cli download bartowski/Qwen2.5-14B-Instruct-GGUF Qwen2.5-14B-Instruct-Q4_K_M.gguf --local-dir ~/models/

# Start with json_schema grammar support
llama-server \
  --model ~/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8000 \
  --n-gpu-layers 99 \
  --ctx-size 32768
```

Then re-run Test 1 against llama-server (it supports grammar-based json_schema enforcement natively).

## Acceptance Criteria

- [x] json_schema enforcement tested with OpenAI SDK (mimicking Graphiti)
- [x] Decision made: **Ollama confirmed** — no llama-server fallback needed
- [x] Response quality validated (correct entity extraction from test text)

## Results

### Test 1 (curl): PASSED
- Ollama accepted `response_format.json_schema` via OpenAI-compatible `/v1/chat/completions`
- Returned valid, schema-compliant JSON with correct entities

### Test 2 (OpenAI Python SDK): PASSED
- Identical request via `openai.OpenAI(base_url="http://localhost:8000/v1")`
- Schema validation passed: all entities have required `name` and `type` fields
- Entities extracted: John Smith (Person), Apple headquarters (Organization), Cupertino (Location)

### Test 3 (Ollama native format): SKIPPED
- Not needed — Tests 1 and 2 both succeeded

### Decision: **Ollama confirmed — proceed to TASK-GMO-003**

Ollama v0.18.0 with Qwen2.5-14B-Instruct Q4_K_M correctly handles OpenAI-style
`json_schema` response format. No llama-server fallback required.
