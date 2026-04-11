---
agent: xunit-testcontainers-testing-specialist
---

# Xunit Testcontainers Testing Specialist - Quick Reference

## Purpose

Implements the three-tier test strategy: Unit tests using NSubstitute mocks with Result<TError, TSuccess> returns and FluentAssertions; Integration tests using ICollectionFixture<PostgreSqlFixture> with Testcontainers and TRUNCATE-based reset; E2E tests using WebApplicationFactory<Program> with Testcontainers PostgreSQL and Keycloak containers and in-memory configuration overrides..

## When to Use

- Implementing features related to this agent's specialty
- Need expert guidance in this specific domain

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/xunit-testcontainers-testing-specialist.md`
- Extended: `agents/xunit-testcontainers-testing-specialist-ext.md`