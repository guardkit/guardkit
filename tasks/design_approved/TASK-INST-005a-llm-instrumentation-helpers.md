---
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
complexity: 3
dependencies:
- TASK-INST-001
- TASK-INST-002
feature_id: FEAT-INST
id: TASK-INST-005a
implementation_mode: task-work
parent_review: TASK-REV-2FE2
status: design_approved
task_type: scaffolding
title: Create LLM instrumentation helper module
wave: 3
---

# Task: Create LLM Instrumentation Helper Module

## Description

Create a standalone helper module with pure functions for extracting instrumentation data from SDK responses. This module has no side effects and does not modify `agent_invoker.py` — it provides the building blocks that TASK-INST-005b and TASK-INST-005c will use.

## Requirements

### Provider Detection

```python
def detect_provider(base_url: Optional[str], model: Optional[str]) -> str:
    """Detect provider from base URL or model string.

    Returns: "anthropic" | "openai" | "local-vllm"
    """
```

- `None` or `api.anthropic.com` → `"anthropic"`
- Contains `openai` → `"openai"`
- Contains `localhost` or `vllm` → `"local-vllm"`
- Unknown → `"anthropic"` (default)

### Token Extraction

```python
def extract_token_usage(response_messages: list) -> tuple[int, int]:
    """Extract input_tokens and output_tokens from SDK response messages.

    Returns: (input_tokens, output_tokens), defaulting to (0, 0) if unavailable.
    """
```

- Parse `ResultMessage` usage fields if present
- Handle missing usage data gracefully (return 0, 0)
- Zero tokens is a valid value (not an error)

### Latency Measurement

```python
@contextmanager
def measure_latency() -> Generator[LatencyResult, None, None]:
    """Context manager that measures wall-clock latency in milliseconds.

    Usage:
        with measure_latency() as latency:
            await sdk_call()
        print(latency.ms)  # float
    """
```

- Uses `time.perf_counter()` for precision
- Records latency even if the wrapped call raises an exception
- `LatencyResult` is a simple dataclass with `ms: float`

### Error Classification

```python
def classify_error(exception: Exception) -> Optional[str]:
    """Classify an SDK exception into controlled vocabulary.

    Returns: "rate_limited" | "timeout" | "tool_error" | "other" | None
    """
```

- `asyncio.TimeoutError` / `SDKTimeoutError` → `"timeout"`
- Rate limit errors (429 status) → `"rate_limited"`
- `ProcessError` → `"tool_error"`
- Other exceptions → `"other"`
- No error → `None`

### Prefix Cache Estimation

```python
def check_prefix_cache(response_headers: Optional[dict]) -> tuple[Optional[bool], bool]:
    """Check vLLM response for prefix cache hit indicator.

    Returns: (prefix_cache_hit, prefix_cache_estimated)
    - (True, False): Direct cache hit confirmed by server
    - (True, True): Estimated cache hit (heuristic)
    - (None, False): No cache info available
    """
```

- Check for vLLM-specific headers
- If not directly provided, return `(None, False)` — estimation logic deferred

### Tool Name Sanitisation

```python
def sanitise_tool_name(raw_name: str) -> str:
    """Sanitise tool name by removing shell metacharacters.

    Keeps only alphanumeric, hyphens, underscores, dots.
    """
```

## Acceptance Criteria

- [ ] `detect_provider()` correctly classifies anthropic, openai, local-vllm, and unknown URLs
- [ ] `extract_token_usage()` returns (0, 0) for missing usage data
- [ ] `measure_latency()` records time even when wrapped call raises
- [ ] `classify_error()` maps all exception types to controlled vocabulary
- [ ] `check_prefix_cache()` handles None headers gracefully
- [ ] `sanitise_tool_name()` strips shell metacharacters
- [ ] All functions are pure (no side effects, no imports of agent_invoker)
- [ ] Unit tests cover all functions with valid, invalid, and edge case inputs

## File Location

`guardkit/orchestrator/instrumentation/llm_instrumentation.py`

## Test Location

`tests/orchestrator/instrumentation/test_llm_instrumentation.py`