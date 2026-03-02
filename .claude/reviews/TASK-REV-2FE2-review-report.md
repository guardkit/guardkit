# Review Report: TASK-REV-2FE2

## Executive Summary

AutoBuild Instrumentation and Context Reduction adds structured observability to the AutoBuild pipeline and replaces static always-on markdown context with minimal role-specific digests. The feature touches multiple subsystems (orchestrator, agent invoker, state tracker, coach validator, progress display) and introduces new infrastructure (event emission, NATS integration, adaptive concurrency).

**Recommended Approach**: Option 1 — Layered Event Emitter with Protocol-Based Injection

**Overall Complexity**: 8/10
**Estimated Effort**: 7-9 tasks across 4 execution waves
**Risk Level**: Medium (graceful degradation patterns mitigate infrastructure risks)

---

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Focus**: All aspects (technical, architecture, performance, security)
- **Trade-off Priority**: Maintainability
- **Specific Concerns**: NATS failure modes, event schema evolution, prefill/context budget

---

## Current State Analysis

### Existing Observability
The AutoBuild pipeline currently has:
- **Python `logging`**: Standard structured logging throughout orchestrator, agent invoker, state tracker
- **ProgressDisplay**: Rich-based turn-by-turn visualization (facade pattern)
- **Turn history**: Immutable `TurnRecord` dataclass capturing player/coach results per turn
- **Agent reports**: JSON files at `.guardkit/autobuild/{task_id}/player_turn_{N}.json` and `coach_turn_{N}.json`
- **ContextStatus**: Frozen dataclass tracking context retrieval status per turn

### Gaps
- No structured event emission (events are log lines, not queryable structured data)
- No token usage tracking per LLM call (only aggregate in TurnRecord)
- No latency instrumentation at tool execution level
- No prompt profile tagging for A/B comparison
- Context injection is all-or-nothing (full rules bundle or Graphiti context, no minimal digests)
- No adaptive concurrency in FeatureOrchestrator wave execution
- No NATS or external event bus integration

---

## Technical Options Analysis

### Option 1: Layered Event Emitter with Protocol-Based Injection (Recommended)

**Architecture**: Define an `EventEmitter` protocol and inject it into existing components. Events emitted async to a pluggable backend (local JSONL file + optional NATS). Role-specific digests loaded from static files with token validation.

```
┌──────────────────────────────────────────────────────┐
│ AutoBuildOrchestrator / AgentInvoker / CoachValidator │
│         ↓ emit(event)                                │
│ ┌─────────────────┐                                  │
│ │ EventEmitter     │ (Protocol)                      │
│ │   .emit(event)   │                                 │
│ └─────────────────┘                                  │
│         ↓                                            │
│ ┌─────────────────────────────────────┐              │
│ │ CompositeBackend                    │              │
│ │  ├── JSONLFileBackend (always-on)   │              │
│ │  └── NATSBackend (optional)         │              │
│ └─────────────────────────────────────┘              │
└──────────────────────────────────────────────────────┘
```

**Complexity**: 7/10
**Effort**: 7-9 tasks
**Pros**:
- Follows existing protocol-based patterns (OrchestratorProtocol, StateTracker ABC)
- Event emission is non-blocking (async fire-and-forget)
- JSONL backend works immediately, NATS is additive
- Schema evolution via Pydantic model versioning (existing pattern in codebase)
- Testable via mock emitter injection
- Digests are static files validated at startup (fail-fast)

**Cons**:
- Requires touching multiple files (orchestrator, invoker, validator)
- NATS dependency adds operational complexity
- Digest maintenance is manual (not auto-generated)

**Maintainability Score**: 9/10 (protocol injection, clean separation, static schemas)

### Option 2: Decorator-Based Instrumentation with Middleware Pipeline

**Architecture**: Use Python decorators/middleware to intercept key methods and auto-emit events. Less explicit but lower integration effort.

```python
@instrumented("llm.call")
async def invoke_player(self, task_id: str, ...) -> AgentInvocationResult:
    ...  # Event auto-emitted with method args/return
```

**Complexity**: 6/10
**Effort**: 5-6 tasks
**Pros**:
- Lower code change footprint
- Automatic instrumentation of existing methods
- Less coupling between business logic and event emission

**Cons**:
- Magic behaviour obscures event contracts
- Harder to customize event payloads per call site
- Decorator approach doesn't compose well with existing async patterns
- Schema evolution is implicit (method signature changes = event changes)
- Harder to test specific event content
- Doesn't follow established codebase patterns (no decorator-based instrumentation exists)

**Maintainability Score**: 5/10 (implicit contracts, harder to reason about)

### Option 3: OpenTelemetry Integration

**Architecture**: Use OpenTelemetry SDK for spans, metrics, and logs. Export to OTLP-compatible backends.

**Complexity**: 8/10
**Effort**: 8-10 tasks
**Pros**:
- Industry standard observability
- Rich ecosystem of exporters (Jaeger, Prometheus, Grafana)
- Built-in trace correlation and distributed tracing

**Cons**:
- Heavy dependency for a CLI tool
- OTLP collectors require infrastructure
- Over-engineered for current scale (single-process, not distributed)
- Doesn't align with NATS-first spec requirement
- Custom event schemas still needed alongside OTel spans
- Significant learning curve for contributors

**Maintainability Score**: 4/10 (heavy dependency, infrastructure requirements)

---

## Recommended Approach: Option 1

### Rationale

1. **Follows existing patterns**: The codebase already uses protocol-based injection (OrchestratorProtocol, StateTracker ABC). An EventEmitter protocol fits naturally.
2. **Maintainability priority**: Explicit event emission at each call site makes contracts visible and testable.
3. **Schema evolution**: Pydantic models for events (matching existing model patterns) support versioning with `schema_version` field.
4. **Graceful degradation**: CompositeBackend tries NATS first, falls back to JSONL — matching the spec's NATS failure requirements.
5. **Non-blocking**: Async emission doesn't add latency to the LLM call critical path (spec requirement).
6. **Testability**: Mock emitter injection enables unit testing of event content without NATS.

### Concern-Specific Analysis

**NATS Failure Modes**:
- CompositeBackend emits to all backends; JSONL is always-on fallback
- NATS connection loss mid-run detected via heartbeat; automatic failover to JSONL-only
- Reconnection attempt on next event; no event loss during transition
- Warning logged on NATS failure (matching spec scenario)

**Event Schema Evolution**:
- Each event model inherits from `BaseEvent` with `schema_version: str` field
- New fields added as Optional with defaults (backward compatible)
- Breaking changes increment schema version
- JSONL reader validates schema version before processing
- Pydantic `model_validate` with `strict=False` handles extra fields gracefully

**Prefill/Context Budget**:
- Role digests are static markdown files with token count validated at startup
- 700-token limit enforced by `DigestValidator` (matching spec boundary scenarios)
- Token counting uses tiktoken (or simple word-based estimate as fallback)
- Prompt profile tag injected into every event (matching spec A/B scenarios)
- Existing `ContextStatus` dataclass extended with `prompt_profile` field

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| NATS unavailable in dev environments | High | Low | JSONL fallback is always-on; NATS is optional |
| Digest exceeds 700 tokens after edit | Medium | Medium | CI validation of digest token counts |
| Event emission adds latency | Low | High | Async fire-and-forget; benchmarked in tests |
| Schema drift between emitter and consumer | Medium | Medium | Shared Pydantic models; schema version field |
| Secret leakage in tool.exec events | Low | High | Redaction pipeline with regex patterns; test coverage |
| Concurrent workers corrupt events | Low | Medium | Thread-safe emitter with per-worker event IDs |
| Adaptive concurrency oscillation | Medium | Low | Cooldown window (5 min stability); hysteresis |

---

## Implementation Breakdown

### Task 1: Event Schema Models (Foundation)
- Define Pydantic models: `BaseEvent`, `LLMCallEvent`, `ToolExecEvent`, `TaskLifecycleEvent`, `WaveEvent`, `GraphitiQueryEvent`
- Controlled vocabulary for `failure_category`, `agent_role`, `prompt_profile`
- Schema validation with reject on invalid fields
- **Complexity**: 4/10 | **Mode**: task-work

### Task 2: Event Emitter Protocol and Backends
- `EventEmitter` protocol with `emit(event: BaseEvent)` method
- `JSONLFileBackend`: Append-only JSONL to `.guardkit/autobuild/{task_id}/events.jsonl`
- `NATSBackend`: Async NATS publish with connection management
- `CompositeBackend`: Fan-out to all backends with fallback
- `NullEmitter`: No-op for testing
- **Complexity**: 5/10 | **Mode**: task-work

### Task 3: Secret Redaction Pipeline
- Regex-based redaction for API keys, tokens, passwords
- Applied to `tool.exec` cmd, stdout_tail, stderr_tail fields
- Sanitisation of tool names against injection
- **Complexity**: 4/10 | **Mode**: task-work

### Task 4: Instrument AutoBuild Orchestrator
- Emit `task.started`, `task.completed`, `task.failed` events
- Emit `wave.completed` events from FeatureOrchestrator
- Inject EventEmitter via constructor (dependency injection)
- **Complexity**: 5/10 | **Mode**: task-work

### Task 5: Instrument Agent Invoker (LLM + Tool Events)
- Emit `llm.call` events with token counts, latency, prompt_profile, agent_role
- Emit `tool.exec` events with redacted cmd/stdout/stderr
- Handle failed LLM calls (timeout, error events)
- Prefix cache hit estimation for vLLM
- **Complexity**: 6/10 | **Mode**: task-work

### Task 6: Instrument Graphiti Context Loader
- Emit `graphiti.query` events with query_type, items_returned, tokens_injected
- Handle Graphiti unavailability (error status event, fallback)
- **Complexity**: 3/10 | **Mode**: task-work

### Task 7: Role-Specific Digest System
- Create digest files for Player, Coach, Resolver, Router roles
- DigestValidator: Validate token count <= 700 at startup
- DigestLoader: Load role-specific digest during prompt assembly
- Prompt profile switching: `digest_only`, `digest+rules_bundle`, `digest+graphiti`
- Phase 1 migration: Keep full rules bundle alongside digest
- **Complexity**: 5/10 | **Mode**: task-work

### Task 8: Adaptive Concurrency Controller
- Monitor `wave.completed` events for rate_limit_count and p95_latency
- Reduce concurrency by 50% on any rate limit
- Reduce concurrency when p95 > 2x baseline
- Increase by +1 after 5 minutes stability
- Integration with FeatureOrchestrator wave execution
- **Complexity**: 5/10 | **Mode**: task-work

### Task 9: Integration Tests
- End-to-end test: AutoBuild run produces correct event stream
- NATS fallback test: Events written to JSONL when NATS unavailable
- Concurrent worker test: Independent events without corruption
- A/B comparison test: Same task, different profiles produce comparable data
- Digest validation tests: Boundary at 700/701 tokens
- **Complexity**: 4/10 | **Mode**: task-work

---

## Dependencies and Parallel Execution

```
Wave 1: [Task 1: Event Schemas]  ← Foundation, no dependencies
    ↓
Wave 2: [Task 2: Emitter Backends] [Task 3: Redaction] [Task 7: Digests]  ← Parallel
    ↓
Wave 3: [Task 4: Orchestrator] [Task 5: Agent Invoker] [Task 6: Graphiti] [Task 8: Concurrency]  ← Parallel
    ↓
Wave 4: [Task 9: Integration Tests]  ← Depends on all
```

---

## Appendix: Event Schema Summary

| Event Type | Required Fields | Source Component |
|-----------|----------------|------------------|
| `llm.call` | run_id, input_tokens, output_tokens, latency_ms, prompt_profile, agent_role | AgentInvoker |
| `tool.exec` | run_id, tool_name, exit_code, latency_ms, stdout_tail, stderr_tail | AgentInvoker |
| `task.started` | run_id, task_id, attempt | AutoBuildOrchestrator |
| `task.completed` | run_id, task_id, turn_count, diff_stats, verification_status, prompt_profile | AutoBuildOrchestrator |
| `task.failed` | run_id, task_id, failure_category | AutoBuildOrchestrator |
| `wave.completed` | run_id, wave_id, queue_depth_start, queue_depth_end, rate_limit_count, p95_latency_ms | FeatureOrchestrator |
| `graphiti.query` | run_id, query_type, items_returned, tokens_injected, latency_ms | Context Loader |
