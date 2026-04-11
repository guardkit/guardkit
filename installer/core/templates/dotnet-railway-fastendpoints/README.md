# .NET Railway-Oriented FastEndpoints Template

GuardKit's first C#/.NET built-in template. Provides an opinionated ASP.NET Core 10.0 starter built around **Railway-Oriented Programming** (Result monad error handling) and **Modular Monolith** architecture with bounded-context isolation, using **FastEndpoints** for the REPR API pattern, Dapper/Npgsql for persistence, NATS for agent-fleet integration, and Keycloak for authentication.

## Quick Start

```bash
guardkit init dotnet-railway-fastendpoints
```

## When to Use

Use this template when you want a production-shaped C# backend that enforces functional error handling (no mid-pipeline `IsSuccess` checks), bounded-context isolation via a Contracts anti-corruption layer, and testcontainer-backed integration/E2E testing out of the box. Not intended for library or single-endpoint microservice scenarios — pick something lighter for those.

## Placeholders

| Name              | Required | Description                                                                 |
|-------------------|----------|-----------------------------------------------------------------------------|
| `{{ProjectName}}` | yes      | Solution / project name (e.g. `AcmeBilling`)                                |
| `{{Namespace}}`   | yes      | Root namespace (e.g. `Acme.Billing`)                                        |
| `{{Author}}`      | no       | Project author name for manifest metadata                                   |
| `{{DefaultRole}}` | no       | Default Keycloak realm role for admin-only endpoints (defaults to `admin`)  |

## Technology Stack

- **Runtime**: ASP.NET Core 10.0 (`net10.0`)
- **API**: FastEndpoints (REPR) + FluentValidation via `Validator<T>`
- **Functional core**: CSharpFunctionalExtensions `Result<TError, TSuccess>`, BaseError hierarchy, static factory methods on aggregates
- **Persistence**: Dapper + Npgsql with DbUp migrations (PostgreSQL)
- **Messaging**: NATS.Client.Core / NATS.Client.JetStream (fleet integration, background services)
- **Auth**: Microsoft JWT Bearer + Keycloak (realm/resource role mapping)
- **Observability**: OpenTelemetry (AspNetCore + Http + OTLP), Serilog structured logging
- **Testing**: xUnit, FluentAssertions 7.x, NSubstitute, Testcontainers.PostgreSql, WebApplicationFactory

## Architecture

**Modular Monolith with Bounded Context isolation.** Layers: Domain, Application, Infrastructure, Endpoints, Cross-Cutting Core, Contracts (anti-corruption layer), Fleet. Only lightweight contract DTOs cross bounded-context boundaries.

Seven specialist agents ship with the template: bounded-context-domain, railway-result-pipeline, fastendpoints-endpoint, dapper-postgresql-repository, keycloak-auth-observability, nats-fleet-integration, and xunit-testcontainers-testing. See `agents/` and `.claude/rules/guidance/` for details.
