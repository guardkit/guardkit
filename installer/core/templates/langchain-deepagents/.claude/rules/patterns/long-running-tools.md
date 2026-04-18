---
paths: tools/**/*.py, agents/**/*.py, agent.py, lib/**/*.py
---

# Long-Running Tools Pattern

Discipline for tools (and tool-shaped wrappers) whose work can exceed the
30s/240s latency thresholds enforced by typical MCP / serverless / gateway
deployments. The single goal: never let a synchronous tool surface a
generation-loop or retry-loop class of latency.

Fixes prevented: LES1 §4 POLR (Premature Online-Response timeout) — and the
associated description-contract bugs where a tool's docstring claims
"long-running" but its implementation `await`s synchronously.

## The 30s / 240s threshold rule (LES1 §4)

Two thresholds matter:

- **30s** — the soft threshold. Anything that *can* exceed 30s in p95 must
  not be exposed as a synchronous tool. Even if a current call is fast, if
  the worst-case path involves a generation loop, an external API, or
  retries, treat it as long-running.
- **240s** — the hard MCP timeout. Once a wrapped tool blocks for 240s,
  the MCP layer returns a generic timeout to the caller, the work is lost,
  and the caller has no way to recover state. This is POLR.

If a tool *can* exceed 30s in any plausible path, it MUST be implemented as
fire-and-forget + poll (see below), not as a synchronous `await`.

## Fire-and-forget + poll pattern

The shape:

1. The triggering tool (`run_thing`) starts the work in the background,
   stores a session record, and returns a `session_id` **immediately**
   (target: <1s).
2. A `run_thing_status` companion accepts a `session_id` and returns
   `{state: pending|running|done|failed, result?: ..., error?: ...}`.
3. A `run_thing_cancel` companion accepts a `session_id` and cancels the
   background work.

```python
# DO — fire-and-forget + poll
@tool
def run_thing(prompt: str) -> str:
    """Long-running — session tracked.

    Starts the generation in the background and returns a session_id.
    Poll run_thing_status(session_id) until state == "done"; then read
    result. Use run_thing_cancel(session_id) to abort.
    """
    session_id = _sessions.create(prompt)
    asyncio.create_task(_run_in_background(session_id, prompt))
    return json.dumps({"session_id": session_id, "state": "pending"})


@tool
def run_thing_status(session_id: str) -> str:
    """Return {state, result?, error?} for a session_id from run_thing."""
    return json.dumps(_sessions.get(session_id))


@tool
def run_thing_cancel(session_id: str) -> str:
    """Cancel the background work for session_id."""
    _sessions.cancel(session_id)
    return json.dumps({"session_id": session_id, "state": "cancelled"})
```

```python
# DON'T — synchronous "long-running" tool
@tool
async def run_thing(prompt: str) -> str:
    """Long-running — session tracked."""  # the docstring lies
    return await player_agent.ainvoke(  # blocks for 30-240s+
        {"messages": [{"role": "user", "content": prompt}]}
    )
```

## Description is a contract

A tool's docstring is consumed by the model as part of the system prompt.
If the docstring says "long-running — session tracked", the implementation
MUST return a `session_id` and not block the caller. If the docstring says
"returns the result", the implementation MUST be a synchronous path with a
worst-case latency comfortably under the deployment threshold.

Mismatches cause two failure modes:

- **Caller plans for polling, tool blocks** — the model schedules a
  `_status` call that never happens, then times out at the MCP layer.
- **Caller plans for a result, tool returns a session_id** — the model
  treats the session_id JSON as the result, surfacing it to the user.

Audit the docstring/implementation pair on every change to either side.
The base template's `langchain-tool-specialist` guidance enforces this
during tool authoring; this rule enforces it at template-review time.

## Latency-class separation

Do not share one tool shape across two latency classes. If a domain has
both a sync probe path (cheap lookup, <500ms) and a generation-loop path
(LLM call, 10-60s), they MUST be two distinct tools with distinct names
and docstrings — not one tool that branches on an argument.

```python
# DO — two latency classes, two tools
@tool
def lookup_record(record_id: str) -> str:
    """Sync — returns a record by id (<500ms)."""
    ...

@tool
def synthesise_record(prompt: str) -> str:
    """Long-running — session tracked. Returns session_id."""
    ...
```

```python
# DON'T — one tool, two latency classes, one docstring that can't be both
@tool
def get_record(record_id: str | None = None, prompt: str | None = None) -> str:
    """Returns a record (lookup or synthesis)."""
    if record_id is not None:
        return _lookup(record_id)        # 200ms
    return _synthesise(prompt)           # 45s
```

The shared shape forces the model to guess the latency class from the
docstring, which can't be right for both branches. The MCP wrapper (if any)
can't pick a timeout that's right for both branches. Split the tool.

## Adversarial-cooperation context (NOTE for orchestrator and weighted-eval)

The Player→Coach loop in this template is *itself* a long-running surface
once a domain wires real LLM calls in. A single Player→Coach round trip
with a 30-60s Player call easily exceeds 240s across `max_retries` retries.

> **NOTE**: If you wrap an `Orchestrator.process_target()` (base) or
> `AdversarialOrchestrator.process_target()` (weighted-eval) call behind an
> MCP tool — or behind any synchronous gateway with a fixed timeout — that
> wrapper MUST be fire-and-forget + poll. The orchestrator loop is an
> accumulated-latency surface (LES1 §4, table row 21). Do not expose it
> as a synchronous tool with the docstring "evaluates content" — at best
> the wrapper times out under load; at worst it loses the partial Player
> output mid-loop with no session to resume from.

The same applies to anything that runs an `ainvoke` chain or an iterative
revision loop behind a tool surface.

## When to use this pattern

- Any tool that calls an LLM, an external API, a subprocess, or a
  retry/revision loop that can plausibly exceed 30s in p95.
- Any tool you intend to expose behind MCP, a gateway, or a serverless
  function with a fixed request timeout.
- Any wrapper around `Orchestrator.process_target()` /
  `AdversarialOrchestrator.process_target()` or other multi-turn agent
  loops.

## When NOT to use this pattern

- Pure local lookups, in-memory transforms, and other paths whose worst
  case is comfortably under 1s.
- Tools used only inside the same Python process as the agent loop where
  the parent already owns its own timeout discipline (e.g. an internal
  helper called by the orchestrator, never exposed as an MCP tool).

## Related

- LES1 §4 (POLR / description-contract)
- Review: `TASK-REV-LES1` §MEDIUM-2
- Orchestrator-template adaptation:
  `langchain-deepagents-orchestrator/.claude/rules/patterns/long-running-tools.md`

Source: tools/*.py, agents/*.py
