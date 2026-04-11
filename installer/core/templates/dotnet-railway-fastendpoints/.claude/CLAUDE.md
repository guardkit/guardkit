# dotnet-functional-fastendpoints-exemplar

## Project Overview

This is a C# project using ASP.NET Core 10.0, FastEndpoints, CSharpFunctionalExtensions, FluentValidation (via FastEndpoints Validator<T>), Dapper, Npgsql, DbUp (PostgreSQL migrations), NATS.Client.Core / NATS.Client.JetStream, OpenTelemetry (AspNetCore + Http + OTLP), Serilog (AspNetCore + OpenTelemetry sink), Microsoft JWT Bearer / Keycloak.
Architecture: Modular Monolith with Bounded Context isolation

## Quick Start

```bash
# Install dependencies
dotnet restore

# Run tests
dotnet test

# Start development
# See project documentation
```

## Detailed Guidance

For detailed code style, testing patterns, architecture patterns, and agent-specific
guidance, see the `.claude/rules/` directory. Rules load automatically when you
work on relevant files.

- **Code Style**: `.claude/rules/code-style.md`
- **Testing**: `.claude/rules/testing.md`
- **Patterns**: `.claude/rules/patterns/`
- **Guidance**: `.claude/rules/guidance/`

## Technology Stack

**Language**: C#
**Frameworks**: ASP.NET Core 10.0, FastEndpoints, CSharpFunctionalExtensions, FluentValidation (via FastEndpoints Validator<T>), Dapper, Npgsql, DbUp (PostgreSQL migrations), NATS.Client.Core / NATS.Client.JetStream, OpenTelemetry (AspNetCore + Http + OTLP), Serilog (AspNetCore + OpenTelemetry sink), Microsoft JWT Bearer / Keycloak
**Architecture**: Modular Monolith with Bounded Context isolation