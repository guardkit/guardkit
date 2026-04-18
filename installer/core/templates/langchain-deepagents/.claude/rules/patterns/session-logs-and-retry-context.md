# Session Logs and Retry Context Pattern

Three orchestrator-level helpers that every adversarial-cooperation template
needs to survive production-scale corpora and failed runs:

- `write_session_log` — unconditional per-run diagnostic JSON
- `configure_logging` — `force=True` root-logger bootstrap
- `build_context_manifest` + `build_retry_input` — structural context
  preservation across retries

Fixes prevented: Category A (missing diagnostics, swallowed log output on
failure) and Category C (filename fabrication on retries over large corpora)
as documented in specialist-agent testing. TASK-REV-R2A1 (dual system
messages).

## When the Helpers Fire

| Helper | Called from | When |
|--------|-------------|------|
| `configure_logging` | Orchestrator dispatch entry | Once at startup, BEFORE any agent work |
| `build_context_manifest` | Orchestrator per-target loop | Once per target, BEFORE the retry loop |
| `build_retry_input` | Orchestrator retry loop | Every rejection / extraction failure |
| `write_session_log` | Orchestrator per-target loop | After BOTH success and exhaustion paths |

The symmetry of the last one is the point: session logs must fire on failure
too, or failed runs leave no trail and debugging becomes guesswork.

## write_session_log

Writes a JSON diagnostic file per target per run. Duck-typed over the result
object — it does not import any concrete `PipelineResult` type.

```python
from lib.session_logging import write_session_log

# After success OR exhaustion — unconditional
write_session_log(
    target.get("id", "unknown"),
    result,                           # needs .success, .attempts, .error, optional .verdict
    log_dir="session-logs",
)
```

The result object contract is loose:

- `result.success: bool` (required)
- `result.attempts: int` (required)
- `result.error: str | None` (required)
- `result.verdict: Any` (optional) — if present, attributes like `decision`,
  `score`, `composite_score`, `issues`, `criterion_scores`, `quality_assessment`
  are serialized when they exist. Missing attributes are skipped silently.

Source: `lib/session_logging.py`

## configure_logging

Call once at the top of orchestrator dispatch, before any role loading or
agent work. Uses `force=True` internally so it wins over framework-level
handlers installed earlier (LangGraph dev server, DeepAgents middleware).

```python
from lib.session_logging import configure_logging

def create_orchestrator(...):
    cli_args = _parse_cli_args()
    configure_logging(debug=cli_args.debug, verbose=cli_args.verbose)
    # ... everything else
```

Without `force=True`, non-greenfield dispatch paths silently swallow
`logger.info` output because the root logger already has handlers attached.

Source: `lib/session_logging.py`

## build_context_manifest

Distils the target's structural metadata into a manifest that can be
re-attached to every retry prompt. Without this, models fabricate filenames
on revision iterations when the input corpus is large (15+ documents).

```python
from lib.retry_context import build_context_manifest

# Once per target, BEFORE the retry loop
context_manifest = build_context_manifest(target, context)
```

Extraction order (first match wins for the "Document manifest" section;
scope is always appended if present):

1. `target['files']` — list of str or dicts with `name`/`path`
2. `target['documents']` — same shape as `files`
3. `target['scope']` or `target['constraints']` — appended as "Scope"
4. Fallback: context-size summary in lines

Source: `lib/retry_context.py`

## build_retry_input

Shapes the retry payload as a single `user`-role message. Follows the
TASK-REV-R2A1 contract: never put `system` messages in `ainvoke()` input
because `create_agent()` unconditionally prepends `system_prompt` and vLLM
rejects dual system messages with HTTP 400.

```python
from lib.retry_context import build_retry_input

# In the retry loop, after Coach rejection or extraction failure
player_input = build_retry_input(
    player_content,
    issues=verdict.issues,              # or [f"Extraction failed: {e}"]
    context_manifest=context_manifest,  # from build_context_manifest
)
```

Source: `lib/retry_context.py`

## Orchestrator Loop Skeleton

The canonical call pattern that wires all four helpers together:

```python
from lib.retry_context import build_context_manifest, build_retry_input
from lib.session_logging import configure_logging, write_session_log


def create_orchestrator(...):
    configure_logging(debug=cli_args.debug, verbose=cli_args.verbose)
    # ... rest of bootstrap


async def process_target(target, context, ...):
    context_manifest = build_context_manifest(target, context)
    player_input = {"messages": [{"role": "user", "content": context}]}

    for attempt in range(1, max_retries + 1):
        player_response = await player.ainvoke(player_input)
        # ... extract, invoke Coach ...

        if verdict.accepted:
            result = PipelineResult(success=True, ..., attempts=attempt)
            write_session_log(target.get("id", "unknown"), result)  # unconditional
            return result

        player_input = build_retry_input(
            player_content, issues=verdict.issues,
            context_manifest=context_manifest,
        )

    # Exhausted retries — log anyway
    result = PipelineResult(success=False, ..., attempts=max_retries)
    write_session_log(target.get("id", "unknown"), result)  # unconditional
    return result
```

## When to Use

- Any Player-Coach orchestrator with a rejection-revision loop
- Any pipeline whose inputs can exceed 15 documents (manifest matters)
- Any pipeline that ships to users (diagnostic logs are table stakes)
- Any template that `extends` the base or vendors its lib contents

## When NOT to Use

- Single-shot pipelines with no retry loop (build_retry_input has no role)
- Very small corpora (<5 docs) where filename fabrication is not a risk
  (context_manifest is still cheap, but not load-bearing)
- Libraries or unit-level code — these helpers are orchestrator boot-time
  primitives

Source: `lib/session_logging.py`, `lib/retry_context.py`
