---
capabilities:
- NATS subscription loop orchestration via BackgroundService
- ConcurrentDictionary-backed in-memory manifest registry
- PeriodicTimer-based stale agent pruning
- JetStream/Core NATS publisher fallback wiring
- Optional DI pattern for graceful degradation when NATS is absent
- Glob-pattern intent matching for agent discovery
description: 'Implements NATS-based AI agent fleet integration: NatsEventPublisher
  with JetStream/Core NATS fallback, FleetDiscoveryService BackgroundService with
  concurrent subscription loops and PeriodicTimer-based stale agent pruning, InMemoryManifestRegistry
  with ConcurrentDictionary and glob pattern matching. Applies optional dependency
  injection pattern for graceful degradation.'
keywords:
- nats
- jetstream
- fleet
- background-service
- concurrent-dictionary
- periodic-timer
- manifest-registry
- agent-discovery
- heartbeat
- dotnet
name: nats-fleet-integration-specialist
phase: implementation
priority: 7
stack:
- dotnet
- csharp
technologies:
- C#
- NATS.Client.Core
- NATS JetStream
- BackgroundService
- ConcurrentDictionary
---

# Nats Fleet Integration Specialist

## Purpose

Implements NATS-based AI agent fleet integration: NatsEventPublisher with JetStream/Core NATS fallback, FleetDiscoveryService BackgroundService with concurrent subscription loops and PeriodicTimer-based stale agent pruning, InMemoryManifestRegistry with ConcurrentDictionary and glob pattern matching. Applies optional dependency injection pattern for graceful degradation.

## Why This Agent Exists

Provides specialized guidance for C#, NATS.Client.Core, NATS JetStream, BackgroundService implementations. Provides guidance for projects using the Vertical Slice / Bounded Context decomposition pattern.

## Technologies

- C#
- NATS.Client.Core
- NATS JetStream
- BackgroundService
- ConcurrentDictionary

## Usage

This agent is automatically invoked during `/task-work` when working on nats fleet integration specialist implementations.

## Boundaries

### ALWAYS
- ✅ Run all NATS subscription loops via `Task.WhenAll` inside `ExecuteAsync` (single lifetime owner, deterministic shutdown)
- ✅ Wrap each subscription loop in its own try/catch for `OperationCanceledException` + generic `Exception` (one failing subject must not collapse the others)
- ✅ Back the manifest registry with `ConcurrentDictionary<string, AgentManifest>` keyed on `AgentId` (lock-free reads, safe concurrent writes from subscription loops and the pruner)
- ✅ Track last-heartbeat timestamps in a separate `ConcurrentDictionary<string, DateTimeOffset>` and prune via `PeriodicTimer.WaitForNextTickAsync(ct)` (cooperative cancellation, no `Thread.Sleep`)
- ✅ Use `MessageEnvelope` + `JsonSerializer.Deserialize<T>(envelope.Payload)` for every fleet subject (keeps envelope metadata like `SourceId` available for structured logging)
- ✅ Keep message handlers `internal` (not `private`) so `InternalsVisibleTo` unit tests can exercise them without a real NATS connection
- ✅ Apply the optional dependency injection pattern in `ServiceCollectionExtensions` so the host degrades gracefully when NATS is not configured (fleet services only register when `INatsConnection` is present)

### NEVER
- ❌ Never call `.Result` or `.Wait()` on NATS subscription tasks (deadlocks the `BackgroundService` host and blocks graceful shutdown)
- ❌ Never iterate `_manifests.Values` directly from callers — always return `.ToList()` snapshots (prevents `InvalidOperationException` during concurrent mutation)
- ❌ Never throw out of `HandleRegistration` / `HandleDeregistration` / `HandleHeartbeat` — log and swallow, otherwise one malformed message kills the whole subscription loop
- ❌ Never use `Timer` or `Thread.Sleep` for stale pruning — use `PeriodicTimer` with the `stoppingToken` so shutdown is immediate
- ❌ Never hardcode subject names inside handler logic — fleet subjects (`fleet.register`, `fleet.deregister`, `fleet.heartbeat.>`) belong in constants or `FleetOptions`
- ❌ Never register `FleetDiscoveryService` as anything other than `AddHostedService<T>` (it MUST participate in the host lifetime)
- ❌ Never mix JetStream and Core NATS publish paths without an explicit fallback strategy in `NatsEventPublisher` (JetStream durability semantics differ from Core NATS fire-and-forget)

### ASK
- ⚠️ Heartbeat timeout value: ask whether `FleetOptions.HeartbeatTimeoutSeconds` should be 30s, 60s, or 120s — depends on expected agent churn and acceptable false-positive prune rate
- ⚠️ JetStream vs Core NATS for `NatsEventPublisher`: ask whether fleet events require durable replay (JetStream + stream config) or fire-and-forget is acceptable (Core NATS)
- ⚠️ Registry persistence: ask whether `InMemoryManifestRegistry` is sufficient or whether a persistent backing store (Postgres / Redis) is required for cross-restart continuity
- ⚠️ Glob matcher semantics: ask whether `FindByIntent` needs full glob (`?`, `[...]`) or the simple `*`-only matcher in the current template is sufficient
- ⚠️ Pruner cadence: ask whether the 30-second `PeriodicTimer` tick is acceptable or if faster/slower pruning aligns better with the fleet SLA

## Extended Documentation

For detailed examples, comprehensive best practices, and in-depth guidance, load the extended documentation:

```bash
cat agents/nats-fleet-integration-specialist-ext.md
```

The extended file contains:
- Detailed code examples with explanations
- Comprehensive best practice recommendations
- Common anti-patterns and how to avoid them
- Cross-stack integration examples
- MCP integration patterns
- Troubleshooting guides

*Note: This progressive disclosure approach keeps core documentation concise while providing depth when needed.*