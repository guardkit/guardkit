---
id: TASK-FBC2
legacy_id: TASK-039
title: Create dotnet-aspnetcontroller template
created: 2025-11-03
updated: 2025-11-03
priority: medium
status: in_review
tags: [templates, dotnet, aspnet, controllers]
completed: 2025-11-03
---

# TASK-FBC2: Create dotnet-aspnetcontroller template

## Overview

Create a traditional ASP.NET Core Web API template using Controllers, providing an alternative to FastEndpoints and Minimal API approaches.

## Template Characteristics

**Name**: `dotnet-aspnetcontroller`

**Description**: Traditional ASP.NET Core Web API with Controllers, MVC pattern, and enterprise-grade features

**Target Audience**:
- Teams familiar with traditional ASP.NET / MVC
- Enterprise applications requiring established patterns
- Projects needing extensive middleware pipeline control
- Teams wanting familiar controller-based routing

## Proposed Tech Stack

**Core Framework**:
- ASP.NET Core 8.0+ Web API
- Controller-based architecture
- Model-View-Controller (MVC) pattern

**Error Handling**:
- ErrorOr/Result pattern (consistent with other templates)
- Global exception handling middleware
- ProblemDetails RFC 7807 compliance

**Validation**:
- FluentValidation for request validation
- ModelState validation
- Custom validation attributes

**Architecture Patterns**:
- Layered architecture (Controllers → Services → Repository)
- Dependency injection
- Repository pattern (optional)
- Unit of Work pattern (for database scenarios)

**Testing**:
- xUnit for unit tests
- WebApplicationFactory for integration tests
- Moq/NSubstitute for mocking
- FluentAssertions for readable assertions

**API Documentation**:
- Swagger/OpenAPI (Swashbuckle)
- XML documentation comments
- API versioning support

**Additional Features**:
- CORS configuration
- Rate limiting
- Response caching
- Health checks
- Logging (Serilog or Microsoft.Extensions.Logging)

## File Structure

```
dotnet-aspnetcontroller/
├── template.json
├── CLAUDE.md
├── README.md
├── src/
│   ├── Api/
│   │   ├── Controllers/
│   │   │   └── WeatherForecastController.cs (example)
│   │   ├── Filters/
│   │   │   ├── ValidationFilter.cs
│   │   │   └── ExceptionFilter.cs
│   │   ├── Middleware/
│   │   │   └── ErrorHandlingMiddleware.cs
│   │   ├── Models/
│   │   │   ├── Requests/
│   │   │   └── Responses/
│   │   └── Program.cs
│   ├── Application/
│   │   ├── Services/
│   │   ├── Interfaces/
│   │   ├── DTOs/
│   │   └── Validators/
│   ├── Domain/
│   │   ├── Entities/
│   │   ├── Common/
│   │   │   └── Result.cs
│   │   └── Errors/
│   └── Infrastructure/
│       ├── Persistence/
│       └── Configuration/
├── tests/
│   ├── UnitTests/
│   │   └── Controllers/
│   └── IntegrationTests/
│       └── Api/
└── .claude/
    ├── agents/ (API, Service, Testing specialists)
    └── commands/
```

## Acceptance Criteria

- [ ] Template structure created with layered architecture
- [ ] Example controller with CRUD operations
- [ ] ErrorOr/Result pattern implemented
- [ ] FluentValidation integrated
- [ ] Global exception handling middleware
- [ ] Swagger/OpenAPI documentation
- [ ] Unit tests for controllers
- [ ] Integration tests using WebApplicationFactory
- [ ] Health checks configured
- [ ] CORS and rate limiting examples
- [ ] Template documentation (README.md, CLAUDE.md)
- [ ] Stack-specific AI agents created
- [ ] Template.json configuration complete

## Best Practices to Research

1. Controller organization and routing strategies
2. Action filter vs middleware for cross-cutting concerns
3. API versioning approaches (URL, header, query string)
4. Response pagination and filtering patterns
5. ETag and caching strategies
6. Authentication/Authorization with JWT
7. Clean Architecture vs Traditional Layered Architecture

## Implementation Steps

Following `docs/guides/template-creation-workflow.md` principles:

### Phase 1: Create Template Structure
```bash
# Create template directory
mkdir -p installer/global/templates/dotnet-aspnetcontroller/{templates,agents}
```

### Phase 2: Create Template Files
- [ ] `template.json` - Template metadata
- [ ] `CLAUDE.md` - AI guidance document
- [ ] `README.md` - Human-readable documentation
- [ ] `templates/controller/*.template` - Controller templates
- [ ] `templates/service/*.template` - Service layer templates
- [ ] `templates/domain/*.template` - Domain layer templates
- [ ] `templates/testing/*.template` - Test templates

### Phase 3: Update Installer Scripts
Update `installer/scripts/install.sh`:
- [ ] Line ~249: Add `dotnet-aspnetcontroller` to mkdir command
- [ ] Line ~468: Add `dotnet-aspnetcontroller` to stack-agents mkdir
- [ ] Line ~500-520: Add template to help text list
  ```bash
  echo "  dotnet-aspnetcontroller - ASP.NET Core Web API with Controllers"
  ```
- [ ] Line ~509: Add example command
  ```bash
  echo "  taskwright-init dotnet-aspnetcontroller # Initialize with Controllers"
  ```
- [ ] Line ~570: Add to another help section
- [ ] Line ~1089: Add case statement for template
  ```bash
  dotnet-aspnetcontroller)
      echo "Setting up ASP.NET Core Web API with Controllers..."
      ;;
  ```
- [ ] Line ~1117: Add to examples

### Phase 4: Update CLI Commands
Update `taskwright-init` help text in install.sh (line ~476-520):
- [ ] Add template to list
- [ ] Add description
- [ ] Add usage example

### Phase 5: Update Documentation
- [ ] `README.md` - Add to template table
  ```markdown
  | dotnet-aspnetcontroller | ASP.NET Core Web API with Controllers, layered architecture |
  ```
- [ ] `CLAUDE.md` - Add to template list
  ```markdown
  - **dotnet-aspnetcontroller**: .NET + Controllers + Clean Architecture + Repository pattern
  ```
- [ ] Update `docs/research/dotnet-api-templates-research-2025.md` - Add implementation status

### Phase 6: Create Stack-Specific Agents
- [ ] `agents/aspnetcontroller-api-specialist.md` - Controller patterns
- [ ] `agents/aspnetcontroller-service-specialist.md` - Service layer
- [ ] `agents/aspnetcontroller-testing-specialist.md` - Testing patterns

### Phase 7: Update Post-Installation Messages
- [ ] Install script success message
- [ ] `taskwright doctor` output
- [ ] Next steps guidance

### Phase 8: Testing & Validation
```bash
# Test installation
./installer/scripts/install.sh

# Verify template appears in help
taskwright-init --help | grep dotnet-aspnetcontroller

# Verify in doctor command
taskwright doctor

# Test template initialization (if init command exists)
taskwright init dotnet-aspnetcontroller --dry-run
```

## Related Tasks

- TASK-292E: Rename dotnet-microservice to dotnet-fastendpoints
- TASK-7F18: Create dotnet-minimalapi template

## References

- Research: `docs/research/dotnet-api-templates-research-2025.md`
- Template Guide: `docs/guides/template-creation-workflow.md`
- Local Templates: `docs/guides/creating-local-templates.md`
- Microsoft official documentation
- Enterprise patterns for Web APIs
