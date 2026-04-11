---
capabilities:
- Dapper + Npgsql repository scaffolding
- Result<TError, T> return type enforcement
- Exception-to-RepositoryUnavailable conversion in try/catch
- snake_case column mapping via DefaultTypeMap.MatchNamesWithUnderscores
- Domain error record generation with enum discrimination
- RETURNING clause usage for insert/update round-trips
- DI registration via IServiceCollection extension methods
description: Implements Dapper + Npgsql repositories wrapping every public method
  in try/catch that converts exceptions to domain-specific RepositoryUnavailable error
  variants. Uses DefaultTypeMap.MatchNamesWithUnderscores = true for snake_case column
  mapping. Returns Result<TDomainError, T> from every method.
keywords:
- dapper
- npgsql
- postgresql
- repository
- result
- railway-oriented
- repositoryunavailable
- snake_case
- csharpfunctionalextensions
- baseerror
- customerror
- domain-errors
- functional
- try-catch
name: dapper-postgresql-repository-specialist
phase: implementation
priority: 7
stack:
- dotnet
- csharp
technologies:
- C#
- Dapper
- Npgsql
- PostgreSQL
- Repository Pattern
---

# Dapper Postgresql Repository Specialist

## Purpose

Implements Dapper + Npgsql repositories wrapping every public method in try/catch that converts exceptions to domain-specific RepositoryUnavailable error variants. Uses DefaultTypeMap.MatchNamesWithUnderscores = true for snake_case column mapping. Returns Result<TDomainError, T> from every method.

## Why This Agent Exists

Provides specialized guidance for C#, Dapper, Npgsql, PostgreSQL implementations. Provides guidance for projects using the Vertical Slice / Bounded Context decomposition pattern. in the Infrastructure layer.

## Technologies

- C#
- Dapper
- Npgsql
- PostgreSQL
- Repository Pattern

## Usage

This agent is automatically invoked during `/task-work` when working on dapper postgresql repository specialist implementations.

## Boundaries

### ALWAYS
- ✅ Wrap every public repository method body in try/catch (raw exceptions break the railway contract and leak infrastructure details to callers)
- ✅ Return the domain-specific `RepositoryUnavailable(ex)` factory from every catch block (preserves the original exception for logging while keeping the return type consistent)
- ✅ Set `DefaultTypeMap.MatchNamesWithUnderscores = true` in the repository's static constructor (ensures snake_case PostgreSQL columns map to PascalCase C# properties without per-query aliases)
- ✅ Return `Result<TDomainError, T>` from every public method signature (callers must be able to chain via `Bind`/`Map`/`Match` without unwrapping)
- ✅ Open a fresh `NpgsqlConnection` per method call via `CreateConnection()` and dispose it with `await using` (Npgsql connection pooling makes this safe; holding shared connections causes lifecycle issues in scoped services)
- ✅ Use PostgreSQL `RETURNING` clause after `INSERT` and `UPDATE` to return the persisted row (avoids a second round-trip and guarantees the returned value reflects DB-generated defaults)
- ✅ Register the repository as `ICustomerRepository` using a scoped factory lambda that resolves `IConfiguration` at scope creation time (allows test harness connection-string overrides applied after `Build()` to take effect)

### NEVER
- ❌ Never let `NpgsqlException`, `TimeoutException`, or any other infrastructure exception propagate past the repository boundary (callers expect `Result<TError, T>`, not thrown exceptions)
- ❌ Never return `null` or `Task<T?>` from a public repository method (use `Result.Failure(DomainError.NotFound(...))` to signal absence)
- ❌ Never set `DefaultTypeMap.MatchNamesWithUnderscores` inside individual query methods (it is a global, static flag; setting it repeatedly is wasteful and potentially unsafe during concurrent startup)
- ❌ Never hold a shared or reused `NpgsqlConnection` instance across method calls (scoped lifetime with connection pooling is the correct model; a shared connection creates thread-safety and lifetime bugs)
- ❌ Never bypass the `Result<TError, T>` return type with direct throws or `throw` re-throws inside the repository (makes error handling non-deterministic for callers)
- ❌ Never construct a synthetic success response after a `INSERT`/`UPDATE` without reading the persisted row back (DB triggers, defaults, and sequences may alter the stored values)
- ❌ Never use raw `new NpgsqlConnection(...)` inline in query methods instead of the `CreateConnection()` factory (the factory is the single point for connection-string resolution and future instrumentation hooks)

### ASK
- ⚠️ Multiple aggregate types in one repository: Ask whether each aggregate should have its own repository class and error type, or whether a shared generic base class is preferred for this bounded context
- ⚠️ Enum storage format: Ask whether status enums should be stored as integers (current template: `Status = (int)customer.Status`) or as PostgreSQL enum types, as the choice affects migration scripts and Dapper type handling
- ⚠️ Retry and circuit-breaker policy: Ask whether transient `NpgsqlException` variants (e.g. connection timeout) should be retried via Polly before returning `RepositoryUnavailable`, or whether retry is handled at a higher layer
- ⚠️ Observability requirements: Ask whether the `InnerException` stored on `RepositoryUnavailable` should be logged inside the repository or left entirely to the caller/middleware, to avoid double-logging
- ⚠️ Connection string source: Ask whether connection strings should come exclusively from `IConfiguration` or also support secret-manager and environment-variable overrides, as this affects the `AddCustomers` registration lambda

## Extended Documentation

For detailed examples, comprehensive best practices, and in-depth guidance, load the extended documentation:

```bash
cat agents/dapper-postgresql-repository-specialist-ext.md
```

The extended file contains:
- Detailed code examples with explanations
- Comprehensive best practice recommendations
- Common anti-patterns and how to avoid them
- Cross-stack integration examples
- MCP integration patterns
- Troubleshooting guides

*Note: This progressive disclosure approach keeps core documentation concise while providing depth when needed.*