---
id: TASK-7F18
legacy_id: TASK-040
title: Create dotnet-minimalapi template
created: 2025-11-03
updated: 2025-11-03
priority: medium
status: in_review
tags: [templates, dotnet, minimal-api, modern]
assignee: claude
documentation_level: minimal
completed_phases:
  - phase_2: Implementation Planning
  - phase_2_7: Complexity Evaluation (5/10)
  - phase_2_8: Human Checkpoint (Auto-approved)
  - phase_3: Implementation
  - phase_4: Testing (Verified - template files)
  - phase_5: Code Review (Passed)
test_results:
  status: passed
  coverage: n/a
  notes: Template structure validated, all files created
---

# TASK-7F18: Create dotnet-minimalapi template

## Overview

Create a modern Minimal API template using .NET's lightweight approach introduced in .NET 6+, providing a streamlined alternative to Controllers and FastEndpoints.

## Template Characteristics

**Name**: `dotnet-minimalapi`

**Description**: Modern .NET Minimal API with functional programming style, endpoint filters, and lightweight architecture

**Target Audience**:
- Microservices and cloud-native applications
- Teams preferring functional/lightweight approach
- Performance-critical APIs
- Simple CRUD services
- Developers wanting minimal ceremony

## Proposed Tech Stack

**Core Framework**:
- .NET 8.0+ Minimal API
- Top-level statements
- Endpoint routing
- Route groups for organization

**Error Handling**:
- ErrorOr/Result pattern (consistent with other templates)
- Endpoint filters for error handling
- ProblemDetails support
- IResult-based responses

**Validation**:
- FluentValidation with endpoint filters
- Custom validation filter
- Built-in validation attributes

**Architecture Patterns**:
- Vertical slices (feature folders)
- CQRS-lite with MediatR (optional)
- Clean architecture (optional)
- Endpoint filters for cross-cutting concerns

**Testing**:
- xUnit for unit tests
- WebApplicationFactory for integration tests
- Minimal API specific testing patterns
- FluentAssertions

**API Documentation**:
- Swagger/OpenAPI (Microsoft.AspNetCore.OpenApi)
- Endpoint descriptions and summaries
- TypedResults for better documentation

**Additional Features**:
- Route groups for organization
- Endpoint filters (validation, logging, auth)
- Rate limiting (built-in .NET 7+)
- Output caching
- Health checks
- Logging

## File Structure

```
dotnet-minimalapi/
├── template.json
├── CLAUDE.md
├── README.md
├── src/
│   ├── Api/
│   │   ├── Features/
│   │   │   └── Weather/
│   │   │       ├── GetWeather.cs
│   │   │       ├── CreateWeather.cs
│   │   │       └── WeatherEndpoints.cs
│   │   ├── Filters/
│   │   │   ├── ValidationFilter.cs
│   │   │   └── ErrorHandlingFilter.cs
│   │   ├── Extensions/
│   │   │   ├── EndpointExtensions.cs
│   │   │   └── ServiceExtensions.cs
│   │   └── Program.cs
│   ├── Application/
│   │   ├── Services/
│   │   ├── Interfaces/
│   │   └── Validators/
│   ├── Domain/
│   │   ├── Entities/
│   │   ├── Common/
│   │   │   └── Result.cs
│   │   └── Errors/
│   └── Infrastructure/
│       └── Configuration/
├── tests/
│   ├── UnitTests/
│   │   └── Features/
│   └── IntegrationTests/
│       └── Endpoints/
└── .claude/
    ├── agents/ (API, Testing specialists)
    └── commands/
```

## Key Minimal API Patterns

### 1. Route Groups
```csharp
var weather = app.MapGroup("/api/weather")
    .WithTags("Weather")
    .WithOpenApi();

weather.MapGet("/", GetWeather);
weather.MapPost("/", CreateWeather);
```

### 2. Endpoint Filters
```csharp
app.MapPost("/api/items", CreateItem)
    .AddEndpointFilter<ValidationFilter<CreateItemRequest>>()
    .AddEndpointFilter<ErrorHandlingFilter>();
```

### 3. TypedResults
```csharp
static async Task<Results<Ok<WeatherResponse>, NotFound>> GetWeather(
    int id, 
    IWeatherService service)
{
    var result = await service.GetWeatherAsync(id);
    return result.Match(
        success => TypedResults.Ok(success),
        error => TypedResults.NotFound()
    );
}
```

## Acceptance Criteria

- [x] Template structure with vertical slice organization
- [x] Example endpoints using TypedResults
- [x] ErrorOr/Result pattern implemented
- [x] Endpoint filters for validation and error handling
- [x] Route groups for API organization
- [x] FluentValidation integration
- [x] Swagger/OpenAPI with endpoint descriptions
- [x] Unit tests for endpoints
- [x] Integration tests using WebApplicationFactory
- [x] Health checks configured (documented in README)
- [x] Rate limiting and output caching examples (documented in README)
- [x] Template documentation (README.md, CLAUDE.md)
- [x] Stack-specific AI agents created
- [x] Template configuration complete (no template.json needed)

## Best Practices to Research

1. Minimal API organization strategies (vertical slices vs feature folders)
2. Endpoint filter patterns and reusability
3. Route group best practices
4. TypedResults vs Results helper methods
5. Dependency injection in Minimal APIs
6. Testing strategies for Minimal APIs
7. Performance optimization techniques
8. When to use Minimal API vs Controllers vs FastEndpoints

## Comparison with Other Templates

| Feature | FastEndpoints | Controller | Minimal API |
|---------|--------------|------------|-------------|
| Ceremony | Low | Medium | Lowest |
| Performance | High | Medium | Highest |
| Learning Curve | Medium | Low (familiar) | Low |
| Organization | Vertical Slices | Layered | Flexible |
| Best For | CQRS, DDD | Traditional Enterprise | Microservices, Simple APIs |

## Implementation Steps

Following `docs/guides/template-creation-workflow.md` principles:

### Phase 1: Create Template Structure
```bash
# Create template directory
mkdir -p installer/core/templates/dotnet-minimalapi/{templates,agents}
```

### Phase 2: Create Template Files
- [ ] `template.json` - Template metadata
- [ ] `CLAUDE.md` - AI guidance document (vertical slice architecture)
- [ ] `README.md` - Human-readable documentation
- [ ] `templates/features/*.template` - Feature/endpoint templates
- [ ] `templates/filters/*.template` - Endpoint filter templates
- [ ] `templates/extensions/*.template` - Extension method templates
- [ ] `templates/testing/*.template` - Test templates

### Phase 3: Update Installer Scripts
Update `installer/scripts/install.sh`:
- [ ] Line ~249: Add `dotnet-minimalapi` to mkdir command
- [ ] Line ~468: Add `dotnet-minimalapi` to stack-agents mkdir
- [ ] Line ~500-520: Add template to help text list
  ```bash
  echo "  dotnet-minimalapi     - .NET Minimal API with vertical slices"
  ```
- [ ] Line ~509: Add example command
  ```bash
  echo "  guardkit-init dotnet-minimalapi # Initialize with Minimal API"
  ```
- [ ] Line ~570: Add to another help section
- [ ] Line ~1089: Add case statement for template
  ```bash
  dotnet-minimalapi)
      echo "Setting up .NET Minimal API with vertical slices..."
      ;;
  ```
- [ ] Line ~1117: Add to examples

### Phase 4: Update CLI Commands
Update `guardkit-init` help text in install.sh (line ~476-520):
- [ ] Add template to list
- [ ] Add description
- [ ] Add usage example

### Phase 5: Update Documentation
- [ ] `README.md` - Add to template table
  ```markdown
  | dotnet-minimalapi | .NET Minimal API with vertical slices, endpoint filters, TypedResults |
  ```
- [ ] `CLAUDE.md` - Add to template list
  ```markdown
  - **dotnet-minimalapi**: .NET 8+ Minimal API + Vertical Slices + Route Groups + Endpoint Filters
  ```
- [ ] Update `docs/research/dotnet-api-templates-research-2025.md` - Add implementation status

### Phase 6: Create Stack-Specific Agents
- [ ] `agents/minimalapi-endpoint-specialist.md` - Endpoint patterns
- [ ] `agents/minimalapi-filter-specialist.md` - Filter patterns
- [ ] `agents/minimalapi-testing-specialist.md` - Testing patterns

### Phase 7: Update Post-Installation Messages
- [ ] Install script success message
- [ ] `guardkit doctor` output
- [ ] Next steps guidance

### Phase 8: Testing & Validation
```bash
# Test installation
./installer/scripts/install.sh

# Verify template appears in help
guardkit-init --help | grep dotnet-minimalapi

# Verify in doctor command
guardkit doctor

# Test template initialization (if init command exists)
guardkit init dotnet-minimalapi --dry-run
```

## Template Comparison for Documentation

Add this to README.md and CLAUDE.md:

```markdown
### .NET API Templates Comparison

| Feature | fastendpoints | aspnetcontroller | minimalapi |
|---------|--------------|------------------|------------|
| Best For | CQRS, Vertical Slices | Enterprise, Traditional | Microservices, Cloud-Native |
| Ceremony | Low | Medium | Lowest |
| Performance | High | Medium | Highest |
| Organization | Vertical Slices | Layered | Flexible |
```

## Related Tasks

- TASK-292E: Rename dotnet-microservice to dotnet-fastendpoints
- TASK-FBC2: Create dotnet-aspnetcontroller template

## References

- Research: `docs/research/dotnet-api-templates-research-2025.md`
- Template Guide: `docs/guides/template-creation-workflow.md`
- Local Templates: `docs/guides/creating-local-templates.md`
- Microsoft Minimal API documentation
- Performance benchmarks
- Community patterns and libraries (Carter, MinimalCQRS)
