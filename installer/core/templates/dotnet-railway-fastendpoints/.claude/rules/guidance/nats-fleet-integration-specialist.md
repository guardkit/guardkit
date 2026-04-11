---
agent: nats-fleet-integration-specialist
---

# Nats Fleet Integration Specialist - Quick Reference

## Purpose

Implements NATS-based AI agent fleet integration: NatsEventPublisher with JetStream/Core NATS fallback, FleetDiscoveryService BackgroundService with concurrent subscription loops and PeriodicTimer-based stale agent pruning, InMemoryManifestRegistry with ConcurrentDictionary and glob pattern matching. Applies optional dependency injection pattern for graceful degradation..

## When to Use

- Implementing features related to this agent's specialty
- Need expert guidance in this specific domain

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/nats-fleet-integration-specialist.md`
- Extended: `agents/nats-fleet-integration-specialist-ext.md`