# Review Report: TASK-REV-A8C2

## Executive Summary

Analysis of `guardkit init python-library` failures on the nats-core project confirms two independent root causes. **Failure Category 1** (LLM connection errors) is a configuration mismatch — the copied `graphiti.yaml` still points to GB10 which is busy. **Failure Category 2** (YAML parsing) is a pre-existing bug affecting 8 rule files across 4 templates where unquoted glob patterns cause `yaml.safe_load()` to fail.

## Review Details

- **Mode**: Decision / Root Cause Analysis
- **Depth**: Standard
- **Task**: TASK-REV-A8C2
- **Artifact**: `docs/reviews/nats-core/init-project-1.md`

---

## Finding 1: LLM Connection Errors — Config Mismatch (Confirmed)

**Severity**: High (blocks all system knowledge seeding)
**Root Cause**: Confirmed — configuration mismatch between CLI and MCP

### Evidence

**nats-core `.guardkit/graphiti.yaml`** (copied from agentic-dataset-factory):
```yaml
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
```

**GuardKit `.guardkit/graphiti.yaml`** (working config):
```yaml
llm_provider: ollama
llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M
```

**GuardKit `.mcp.json`** (working MCP config):
```json
"LLM_API_URL": "http://richards-macbook-pro.tailebf801.ts.net:8000/v1",
"LLM_MODEL": "qwen2.5:14b-instruct-q4_K_M"
```

The nats-core config was copied from `agentic-dataset-factory` during init (line 74-80 of the log). That project still has the GB10 endpoint. GB10 is busy generating a training set, so all LLM calls fail with "Connection error".

### Impact

- Template sync partially succeeds (metadata written to graph, but 0 agents, 0 rules extracted)
- Circuit breaker trips after 3 failures, disabling Graphiti for the rest of the session
- Step 2 (project knowledge seeding) succeeded because it doesn't require LLM calls — it writes raw content
- Step 3 (system knowledge seeding) requires LLM for entity extraction, so it fails entirely

### Recommendations

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1a | **Immediate**: Update nats-core's `graphiti.yaml` LLM endpoint to MacBook | 2 min | Unblocks nats-core |
| 1b | **Short-term**: Update `agentic-dataset-factory` graphiti.yaml too | 2 min | Prevents recurrence on next copy |
| 1c | **Medium-term**: Add LLM health check to `guardkit init` before seeding | 2-4 hrs | Better UX on failure |
| 1d | **Medium-term**: When copying graphiti.yaml during init, validate LLM reachability | 2-4 hrs | Fail-fast with clear message |

---

## Finding 2: YAML Frontmatter Parsing — Unquoted Glob Patterns (Bug)

**Severity**: Medium (prevents rule knowledge extraction, does not block init)
**Root Cause**: Unquoted `*` in YAML frontmatter — YAML interprets `*` as an alias indicator

### Evidence

The error from the log:
```
Failed to parse agent frontmatter: while scanning an alias
  paths: **/*.py
         ^
expected alphabetic or numeric character, but found '*'
```

In YAML, `*name` is an alias reference (the counterpart to `&name` anchors). When `yaml.safe_load()` encounters `paths: **/*.py`, it tries to parse `**/*.py` as an alias starting with `*`, fails, and raises `YAMLError`.

### Affected Files (8 files across 4 templates)

**Unquoted** (broken):

| Template | File | Value |
|----------|------|-------|
| python-library | `rules/code-style.md` | `paths: **/*.py` |
| python-library | `rules/testing.md` | `paths: **/*.test.*, **/tests/**, ...` |
| langchain-deepagents | `rules/code-style.md` | `paths: **/*.py, **/*.pyx` |
| langchain-deepagents | `rules/testing.md` | `paths: **/*.test.*, **/tests/**, ...` |
| langchain-deepagents-orchestrator | `rules/code-style.md` | `paths: **/*.py, **/*.pyx` |
| langchain-deepagents-orchestrator | `rules/testing.md` | `paths: **/*.test.*, **/tests/**, ...` |
| nats-asyncio-service | `rules/code-style.md` | `paths: **/*.py, **/*.pyx` |
| nats-asyncio-service | `rules/testing.md` | `paths: **/*.test.*, **/tests/**, ...` |

**Partially unquoted** (borderline):

| Template | File | Value |
|----------|------|-------|
| react-fastapi-monorepo | `rules/monorepo/turborepo.md` | `paths: turbo.json, **/package.json` |

**Correctly quoted** (working examples from other templates):
- `paths: "**/*.py"` (fastapi-python, default)
- `paths: ["**/*.ts"]` (react-typescript, mcp-typescript)
- `paths: "**/tests/**"` (fastapi-python)

### Why This Is a Source File Bug (Not a Parser Bug)

The parsing code at [template_sync.py:82](guardkit/knowledge/template_sync.py#L82) uses `yaml.safe_load()` which is correct YAML behaviour. The `*` character is a reserved indicator in YAML. The fix should be in the source files (quoting the values), not in the parser.

Claude Code itself handles these unquoted paths fine because it uses a custom frontmatter parser (not strict YAML), but `template_sync.py` uses the standard `yaml` library which follows the YAML spec.

### Recommendations

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 2a | **Immediate**: Quote all glob patterns in the 8 affected rule files | 15 min | Fixes all current failures |
| 2b | **Short-term**: Add a validation step to `/template-validate` that checks for unquoted globs in paths | 1-2 hrs | Prevents regression |
| 2c | **Alternative**: Make `extract_agent_metadata()` pre-process the `paths` line to quote unquoted values before `yaml.safe_load()` | 1-2 hrs | Defensive parsing |

**Recommended approach**: 2a + 2b. Fix the source files and add validation to catch regressions. Option 2c is a workaround that masks the underlying inconsistency.

---

## Finding 3: Graceful Degradation Works As Designed

**Severity**: Informational
**Observation**: The circuit breaker and retry logic in `graphiti_client.py` worked correctly:

1. OpenAI client retried twice per call (0.4s, ~1s backoff)
2. Graphiti client retried 3 times with exponential backoff (2s, 4s)
3. After 3 consecutive failures, circuit breaker tripped: "Graphiti disabled after 3 consecutive failures"
4. Init continued and completed successfully despite Graphiti failures

The only improvement would be **faster failure detection** — currently takes ~32s to exhaust all retries. A pre-flight LLM health check would reduce this to <2s.

---

## Decision Matrix

| Option | Effort | Risk | Recommendation |
|--------|--------|------|----------------|
| Fix nats-core config only | 2 min | Low | Do now |
| Quote glob patterns in 8 files | 15 min | Low | Do now |
| Add LLM health check to init | 2-4 hrs | Low | Backlog task |
| Add glob validation to template-validate | 1-2 hrs | Low | Backlog task |
| Defensive YAML parsing workaround | 1-2 hrs | Medium | Not recommended |

---

## Acceptance Criteria Assessment

- [x] Root cause confirmed for LLM connection errors — config mismatch (GB10 vs MacBook)
- [x] All rule files with unquoted glob patterns identified — 8 files across 4 templates
- [x] Fix approach recommended for both failure categories
- [x] `guardkit init` error handling assessment — circuit breaker works, but pre-flight check would improve UX
- [x] YAML parsing assessment — source files should be fixed, not the parser
