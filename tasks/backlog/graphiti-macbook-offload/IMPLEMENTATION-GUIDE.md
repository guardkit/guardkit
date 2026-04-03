# Implementation Guide: Graphiti MacBook Offload

## Wave 1: Setup + Validation

### TASK-GMO-001: Install Ollama on MacBook
**Method**: Direct (manual on MacBook)
**Duration**: ~15 minutes

```bash
brew install ollama
ollama pull qwen2.5:14b-instruct-q4_K_M
OLLAMA_HOST=0.0.0.0:8000 ollama serve
```

Verify: `curl http://localhost:8000/v1/models`

### TASK-GMO-002: Test json_schema enforcement
**Method**: Direct (manual testing)
**Duration**: ~30 minutes
**Decision gate**: Pass → Wave 2. Fail → switch to llama-server.

Test with OpenAI Python SDK mimicking Graphiti's `response_format` parameter.
See task file for full test protocol and llama-server fallback steps.

---

## Wave 2: Config + Integration

### TASK-GMO-003: Update Graphiti config
**Method**: task-work
**Duration**: ~15 minutes

Two files to update:
1. `.mcp.json` — `LLM_API_URL`
2. `.guardkit/graphiti.yaml` — `llm_base_url`

Plus create toggle script at `scripts/graphiti-endpoint-toggle.sh`.

### TASK-GMO-004: End-to-end test
**Method**: Direct
**Duration**: ~30 minutes

Test MCP add_memory, CLI add-context, search, and performance timing.
Success: episode ingested, searchable, under 180 seconds.

---

## Wave 3: Documentation

### TASK-GMO-005: Setup instructions
**Method**: Direct
**Duration**: ~30 minutes

Create `docs/reference/graphiti-macbook-offload.md` with tested instructions.

---

## Risk Mitigation

| Risk | Trigger | Mitigation |
|------|---------|------------|
| Ollama ignores json_schema | GMO-002 Test 1/2 fails | Switch to llama-server (documented in GMO-002) |
| Model quality too low at Q4 | GMO-004 entity extraction poor | Upgrade to Q5_K_M: `ollama pull qwen2.5:14b-instruct-q5_K_M` |
| macOS firewall blocks port | GMO-001 remote curl fails | System Preferences → Firewall → Allow Ollama |
| Performance too slow (>180s) | GMO-004 timing test | Accept if under 300s; consider Q4 with shorter context |
