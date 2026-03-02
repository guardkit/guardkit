# Implementation Guide: AutoBuild Instrumentation and Context Reduction

## Overview

This feature adds structured observability to the AutoBuild pipeline and migrates from static always-on markdown context to minimal role-specific digests. The implementation follows Option 1: Layered Event Emitter with Protocol-Based Injection.

**Approach**: Protocol-based EventEmitter injected into existing components
**Execution**: 4 waves with auto-detected parallelism
**Testing**: Full TDD (test-first for all tasks)
**Review**: TASK-REV-2FE2

---

## Data Flow: Read/Write Paths

```mermaid
flowchart LR
    subgraph Writes["Write Paths"]
        W1["AutoBuildOrchestrator\n.emit(task.started)"]
        W2["AutoBuildOrchestrator\n.emit(task.completed/failed)"]
        W3["AgentInvoker\n.emit(llm.call)"]
        W4["AgentInvoker\n.emit(tool.exec)"]
        W5["FeatureOrchestrator\n.emit(wave.completed)"]
        W6["GraphitiLoader\n.emit(graphiti.query)"]
    end

    subgraph Middleware["Middleware"]
        M1["SecretRedaction\nredact_secrets()"]
    end

    subgraph Emitter["EventEmitter (Protocol)"]
        E1["CompositeBackend"]
    end

    subgraph Storage["Storage"]
        S1[("JSONL File\nevents.jsonl\n(always-on)")]
        S2[("NATS Bus\n(optional)")]
    end

    subgraph Reads["Read Paths"]
        R1["A/B Comparison\nAnalysis Script"]
        R2["ConcurrencyController\n.on_wave_completed()"]
        R3["Dashboard / CLI\n(future)"]
    end

    subgraph Context["Context Assembly"]
        C1["DigestLoader\nload(role)"]
        C2[("Digest Files\n.guardkit/digests/")]
        C3["PromptProfile\nswitch(profile)"]
    end

    W1 --> E1
    W2 --> E1
    W3 --> E1
    W4 --> M1
    M1 --> E1
    W5 --> E1
    W6 --> E1

    E1 -->|"append"| S1
    E1 -->|"publish"| S2

    S1 -->|"read JSONL"| R1
    S1 -->|"read JSONL"| R3
    S2 -.->|"subscribe"| R3

    W5 -->|"wave events"| R2

    C2 -->|"load"| C1
    C1 -->|"inject digest"| C3
    C3 -->|"tag profile"| W3
```

_Look for: Every write path (left) reaches storage (centre) and every read path (right) has a data source. The ConcurrencyController reads wave events directly from the emitter output, not from storage._

---

## Integration Contracts

```mermaid
sequenceDiagram
    participant ABO as AutoBuildOrchestrator
    participant AI as AgentInvoker
    participant RD as SecretRedaction
    participant EM as EventEmitter
    participant JB as JSONLBackend
    participant NB as NATSBackend
    participant CC as ConcurrencyController
    participant DL as DigestLoader

    Note over ABO: Task starts
    ABO->>EM: emit(TaskStartedEvent)
    EM->>JB: write(event)
    EM->>NB: publish(event)

    Note over DL: Prompt assembly
    DL->>DL: load(role="player")
    DL-->>AI: digest_content + prompt_profile

    Note over AI: LLM invocation
    AI->>EM: emit(LLMCallEvent)
    EM->>JB: write(event)

    Note over AI: Tool execution
    AI->>RD: redact_secrets(cmd, stdout, stderr)
    RD-->>AI: redacted_fields
    AI->>EM: emit(ToolExecEvent)
    EM->>JB: write(event)

    Note over ABO: Wave completes
    ABO->>EM: emit(WaveCompletedEvent)
    EM->>JB: write(event)
    ABO->>CC: on_wave_completed(event)
    CC-->>ABO: ConcurrencyDecision

    Note over NB: NATS drops mid-run
    EM-xNB: publish fails
    Note over EM: Fallback: JSONL only + warning

    Note over ABO: Task completes
    ABO->>EM: emit(TaskCompletedEvent)
    ABO->>EM: flush()
    ABO->>EM: close()
```

_Look for: Data flows from orchestrator through emitter to backends. Note the NATS failure fallback mid-sequence. The ConcurrencyController receives wave events directly from the orchestrator, not from storage replay._

---

## §4: Integration Contracts

### Contract: EVENT_SCHEMAS
- **Producer task:** TASK-INST-001
- **Consumer task(s):** TASK-INST-002, TASK-INST-004, TASK-INST-005, TASK-INST-006, TASK-INST-008
- **Artifact type:** Python module (Pydantic models)
- **Format constraint:** All event objects are Pydantic BaseEvent subclasses with `model_dump()` returning `dict` for JSON serialization. Each model has a `schema_version` field defaulting to `"1.0.0"`.
- **Validation method:** Coach verifies import and instantiation of all event classes; `model_dump()` returns valid dict with required fields.

### Contract: EVENT_EMITTER
- **Producer task:** TASK-INST-002
- **Consumer task(s):** TASK-INST-004, TASK-INST-005, TASK-INST-006, TASK-INST-008
- **Artifact type:** Python protocol + implementations
- **Format constraint:** `EventEmitter` protocol with `async emit(event: BaseEvent)`, `async flush()`, `async close()` methods. `NullEmitter(capture=True)` stores events in `.captured` list.
- **Validation method:** Coach verifies NullEmitter can be injected and captures events; CompositeBackend writes to JSONL.

### Contract: REDACTION_PIPELINE
- **Producer task:** TASK-INST-003
- **Consumer task(s):** TASK-INST-005
- **Artifact type:** Python function
- **Format constraint:** `redact_secrets(text: str) -> str` replaces detected secrets with `[REDACTED]`. Input/output are plain strings.
- **Validation method:** Coach verifies known secret patterns are redacted and non-secret text is preserved.

---

## Task Dependencies

```mermaid
graph TD
    T1["TASK-INST-001\nEvent Schema Models\n(complexity: 4)"] --> T2["TASK-INST-002\nEvent Emitter Backends\n(complexity: 5)"]
    T1 --> T3["TASK-INST-003\nSecret Redaction\n(complexity: 4)"]
    T1 --> T7["TASK-INST-007\nRole-Specific Digests\n(complexity: 5)"]
    T2 --> T4["TASK-INST-004\nInstrument Orchestrator\n(complexity: 5)"]
    T2 --> T5["TASK-INST-005\nInstrument Agent Invoker\n(complexity: 6)"]
    T2 --> T6["TASK-INST-006\nInstrument Graphiti Loader\n(complexity: 3)"]
    T2 --> T8["TASK-INST-008\nAdaptive Concurrency\n(complexity: 5)"]
    T3 --> T5
    T4 --> T9["TASK-INST-009\nIntegration Tests\n(complexity: 4)"]
    T5 --> T9
    T6 --> T9
    T7 --> T9
    T8 --> T9

    style T2 fill:#cfc,stroke:#090
    style T3 fill:#cfc,stroke:#090
    style T7 fill:#cfc,stroke:#090
    style T4 fill:#cfc,stroke:#090
    style T5 fill:#cfc,stroke:#090
    style T6 fill:#cfc,stroke:#090
    style T8 fill:#cfc,stroke:#090
```

_Tasks with green background can run in parallel within their wave._

---

## Execution Strategy

### Wave 1: Foundation (1 task)
| Task | Name | Complexity | Mode |
|------|------|-----------|------|
| TASK-INST-001 | Event Schema Models | 4 | task-work (TDD) |

### Wave 2: Core Infrastructure (3 tasks, parallel)
| Task | Name | Complexity | Mode |
|------|------|-----------|------|
| TASK-INST-002 | Event Emitter Backends | 5 | task-work (TDD) |
| TASK-INST-003 | Secret Redaction Pipeline | 4 | task-work (TDD) |
| TASK-INST-007 | Role-Specific Digests | 5 | task-work (TDD) |

### Wave 3: Instrumentation (4 tasks, parallel)
| Task | Name | Complexity | Mode |
|------|------|-----------|------|
| TASK-INST-004 | Instrument Orchestrator | 5 | task-work (TDD) |
| TASK-INST-005 | Instrument Agent Invoker | 6 | task-work (TDD) |
| TASK-INST-006 | Instrument Graphiti Loader | 3 | task-work (TDD) |
| TASK-INST-008 | Adaptive Concurrency | 5 | task-work (TDD) |

### Wave 4: Verification (1 task)
| Task | Name | Complexity | Mode |
|------|------|-----------|------|
| TASK-INST-009 | Integration Tests | 4 | task-work (TDD) |

---

## Architecture Decision: Protocol-Based Injection

The EventEmitter is injected via constructor into existing components rather than using decorators or global state. This follows the established pattern in the codebase (OrchestratorProtocol, StateTracker ABC).

**Why not decorators?** The codebase has no decorator-based instrumentation. Adding magic behaviour would break the pattern of explicit contracts.

**Why not OpenTelemetry?** The pipeline is a single-process CLI tool. OTel's distributed tracing overhead is not justified. Structured JSONL files meet current analysis needs.

## Schema Evolution Strategy

- All events include `schema_version` field (default "1.0.0")
- New fields added as Optional with defaults (backward compatible)
- Breaking changes increment schema version
- JSONL reader validates schema version before processing
- Pydantic `model_validate` with `strict=False` handles extra fields

## NATS Failure Strategy

- CompositeBackend always includes JSONLFileBackend (never loses events)
- NATSBackend is optional; configured via environment variable
- Connection loss detected per-emit; automatic failover to JSONL-only
- Warning logged once per failover event
- Reconnection attempted on next emit
- No retry queue (events are append-only, not ordered delivery critical)

## Digest Token Budget

- Each role digest: 300-600 tokens (target)
- Hard limit: 700 tokens (validated at startup)
- Token counting: tiktoken preferred, word-based fallback
- CI validation recommended for digest files
- Phase 1: digest + full rules bundle (baseline measurement)
- Phase 2+: digest + Graphiti (reduced prefill)

## Key Files

| Component | Location |
|-----------|----------|
| Event schemas | `guardkit/orchestrator/instrumentation/schemas.py` |
| Event emitter | `guardkit/orchestrator/instrumentation/emitter.py` |
| Secret redaction | `guardkit/orchestrator/instrumentation/redaction.py` |
| Digest system | `guardkit/orchestrator/instrumentation/digests.py` |
| Prompt profiles | `guardkit/orchestrator/instrumentation/prompt_profile.py` |
| Concurrency | `guardkit/orchestrator/instrumentation/concurrency.py` |
| LLM helpers | `guardkit/orchestrator/instrumentation/llm_instrumentation.py` |
| Digest files | `.guardkit/digests/{player,coach,resolver,router}.md` |
| Event output | `.guardkit/autobuild/{task_id}/events.jsonl` |
