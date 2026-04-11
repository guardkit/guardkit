# Nats Fleet Integration Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **nats-fleet-integration-specialist** agent.

**Core documentation**: See [nats-fleet-integration-specialist.md](./nats-fleet-integration-specialist.md)

---

## Related Templates

These templates demonstrate the NATS fleet integration patterns this agent implements:

- `templates/fleet/services/FleetDiscoveryService.cs.template` — `BackgroundService` with concurrent subscription loops for `fleet.register`, `fleet.deregister`, `fleet.heartbeat.>` plus a `PeriodicTimer`-based stale-agent pruner
- `templates/fleet/registry/InMemoryManifestRegistry.cs.template` — thread-safe `ConcurrentDictionary`-backed `IManifestRegistry` with glob pattern matching for `FindByIntent`
- `templates/infrastructure/infrastructure/ServiceCollectionExtensions.cs.template` — reference for the optional DI registration pattern (NATS connection + fleet services wired only when configured)
- `templates/host / composition root/exemplar.api/Program.cs.template` — composition-root wiring of fleet services into the host
- `templates/cross-cutting core/functional/Result.cs.template` — `Result<T>` monad used when fleet operations need railway-oriented error handling

## Code Examples

### Example 1: Concurrent subscription loops inside a BackgroundService

From `templates/fleet/services/FleetDiscoveryService.cs.template` — all subscription loops and the pruner run concurrently via `Task.WhenAll`, so a single `ExecuteAsync` owns the full lifetime:

```csharp
protected override Task ExecuteAsync(CancellationToken stoppingToken)
{
    return Task.WhenAll(
        SubscribeRegistrationsAsync(stoppingToken),
        SubscribeDeregistrationsAsync(stoppingToken),
        SubscribeHeartbeatsAsync(stoppingToken),
        PruneStaleAgentsAsync(stoppingToken));
}

private async Task SubscribeRegistrationsAsync(CancellationToken ct)
{
    try
    {
        await foreach (var msg in _nats.SubscribeAsync<MessageEnvelope>("fleet.register", cancellationToken: ct))
        {
            if (msg.Data is null) continue;
            HandleRegistration(msg.Data);
        }
    }
    catch (OperationCanceledException) { /* normal shutdown */ }
    catch (Exception ex)
    {
        _logger.LogError(ex, "fleet.register subscription error");
    }
}
```

Each loop owns its own try/catch so one failing subject never collapses the others.

### Example 2: PeriodicTimer-based stale agent pruning

A `PeriodicTimer` driven off the same `CancellationToken` prunes agents whose last heartbeat exceeds `FleetOptions.HeartbeatTimeoutSeconds`:

```csharp
private async Task PruneStaleAgentsAsync(CancellationToken ct)
{
    using var timer = new PeriodicTimer(TimeSpan.FromSeconds(30));
    try
    {
        while (await timer.WaitForNextTickAsync(ct))
        {
            var threshold = DateTimeOffset.UtcNow.AddSeconds(-_opts.HeartbeatTimeoutSeconds);
            foreach (var (agentId, lastSeen) in _heartbeats)
            {
                if (lastSeen < threshold)
                {
                    _registry.Deregister(agentId);
                    _heartbeats.TryRemove(agentId, out _);
                    _logger.LogWarning(
                        "Fleet: pruned stale agent {AgentId} (last seen {LastSeen:O})",
                        agentId, lastSeen);
                }
            }
        }
    }
    catch (OperationCanceledException) { /* normal shutdown */ }
}
```

### Example 3: ConcurrentDictionary-backed registry with glob matching

From `templates/fleet/registry/InMemoryManifestRegistry.cs.template` — lookups return immutable snapshots so callers never iterate live state:

```csharp
public sealed class InMemoryManifestRegistry : IManifestRegistry
{
    private readonly ConcurrentDictionary<string, AgentManifest> _manifests = new();

    public void Register(AgentManifest manifest)
        => _manifests[manifest.AgentId] = manifest;

    public void Deregister(string agentId)
        => _manifests.TryRemove(agentId, out _);

    public IReadOnlyList<AgentManifest> FindByIntent(string intentPattern)
        => _manifests.Values
            .Where(m => m.Intents.Any(i => MatchesGlob(i.Name, intentPattern)))
            .ToList();
}
```

### Example 4: Deserialization inside message handlers

Handlers are kept `internal` so unit tests can drive them directly without a live NATS connection:

```csharp
internal void HandleRegistration(MessageEnvelope envelope)
{
    try
    {
        var manifest = JsonSerializer.Deserialize<AgentManifest>(envelope.Payload);
        if (manifest is null) return;

        _registry.Register(manifest);
        _heartbeats[manifest.AgentId] = DateTimeOffset.UtcNow;
    }
    catch (Exception ex)
    {
        _logger.LogWarning(ex, "Failed to process fleet.register message from {SourceId}", envelope.SourceId);
    }
}
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
