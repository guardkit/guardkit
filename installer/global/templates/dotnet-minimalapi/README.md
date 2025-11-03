# .NET Minimal API Template

Modern, lightweight .NET 8+ Minimal API template with functional error handling, vertical slice architecture, and cloud-native patterns.

## Overview

This template provides a production-ready foundation for building high-performance microservices and cloud-native APIs using .NET Minimal APIs with the ErrorOr pattern for functional error handling.

## Key Features

- **.NET 8+ Minimal APIs**: Lightweight, high-performance web framework
- **ErrorOr Pattern**: Functional error handling for robust APIs
- **Vertical Slice Architecture**: Feature-based organization
- **TypedResults**: Compile-time safe response types
- **Route Groups**: Organized endpoint registration
- **Endpoint Filters**: Validation, error handling, cross-cutting concerns
- **FluentValidation**: Declarative validation with endpoint filters
- **OpenAPI/Swagger**: Auto-generated API documentation
- **xUnit + FluentAssertions**: Comprehensive testing setup
- **OpenTelemetry**: Observability and distributed tracing
- **Health Checks**: Built-in health endpoints
- **JWT Authentication**: Bearer token support

## When to Use This Template

**Use This Template When:**
- Building microservices or cloud-native APIs
- Performance is a critical requirement
- You prefer functional programming patterns
- You want minimal ceremony and boilerplate
- Building simple to medium complexity CRUD services
- Team is comfortable with modern C# patterns

**Consider Alternatives When:**
- Building large monolithic APIs (use **dotnet-aspnetcontroller**)
- Need advanced REPR/CQRS features (use **dotnet-fastendpoints**)
- Team prefers traditional MVC patterns (use **dotnet-aspnetcontroller**)

## Project Structure

```
{ServiceName}.API/
├── Features/                 # Vertical slices (feature-based organization)
│   └── Weather/
│       ├── GetWeather.cs
│       ├── CreateWeather.cs
│       └── UpdateWeather.cs
├── Filters/                  # Endpoint filters
│   ├── ValidationFilter.cs
│   └── ErrorHandlingFilter.cs
├── Extensions/               # Extension methods
│   └── EndpointExtensions.cs
├── Domain/                   # Domain layer
│   ├── Common/
│   │   └── Result.cs        # ErrorOr integration
│   ├── DomainErrors.cs
│   ├── Entities/
│   └── ValueObjects/
├── Application/              # Application layer
│   ├── Services/
│   │   ├── Interfaces/
│   │   └── Implementations/
│   ├── DTOs/
│   └── Validators/
├── Infrastructure/           # Infrastructure layer
│   ├── Repositories/
│   ├── Persistence/
│   └── HttpClients/
└── Program.cs               # Entry point with DI and endpoint registration

Tests/
├── Unit/
│   ├── Endpoints/
│   ├── Services/
│   └── Validators/
├── Integration/
│   └── Endpoints/
└── Fixtures/
    └── ApiFactory.cs
```

## Quick Start

### Prerequisites

- .NET 8.0 SDK or later
- Your favorite IDE (Visual Studio, VS Code, Rider)

### Installation

Initialize a new project with this template:

```bash
taskwright init dotnet-minimalapi
```

### Running the Project

```bash
cd {ServiceName}.API
dotnet run
```

Navigate to `https://localhost:5001/swagger` to view the API documentation.

### Running Tests

```bash
# Run all tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"
```

## Core Patterns

### 1. Endpoint Definition with TypedResults

```csharp
public static class GetWeatherEndpoint
{
    public static async Task<Results<Ok<WeatherResponse>, NotFound>> Handle(
        int id,
        IWeatherService service)
    {
        var result = await service.GetWeatherByIdAsync(id);

        return result.Match(
            weather => TypedResults.Ok(weather.ToResponse()),
            errors => TypedResults.NotFound()
        );
    }
}
```

### 2. Route Groups for Organization

```csharp
var weather = app.MapGroup("/api/weather")
    .WithTags("Weather")
    .WithOpenApi();

weather.MapGet("/{id:int}", GetWeatherEndpoint.Handle);
weather.MapPost("/", CreateWeatherEndpoint.Handle);
```

### 3. Service Layer with ErrorOr

```csharp
public interface IWeatherService
{
    Task<ErrorOr<Weather>> GetWeatherByIdAsync(int id);
}

public class WeatherService : IWeatherService
{
    public async Task<ErrorOr<Weather>> GetWeatherByIdAsync(int id)
    {
        var weather = await _repository.GetByIdAsync(id);

        if (weather is null)
        {
            return DomainErrors.Weather.NotFound(id);
        }

        return weather;
    }
}
```

### 4. Validation with Endpoint Filters

```csharp
public class CreateWeatherValidator : AbstractValidator<CreateWeatherRequest>
{
    public CreateWeatherValidator()
    {
        RuleFor(x => x.Location).NotEmpty();
        RuleFor(x => x.Temperature).InclusiveBetween(-100, 100);
    }
}

// Apply filter to endpoint
weather.MapPost("/", CreateWeatherEndpoint.Handle)
    .AddEndpointFilter<ValidationFilter<CreateWeatherRequest>>();
```

## Template Comparison

### .NET API Templates Comparison

| Feature | FastEndpoints | ASP.NET Controllers | **Minimal API** |
|---------|--------------|---------------------|-----------------|
| **Best For** | CQRS, Vertical Slices | Enterprise, Traditional | **Microservices, Cloud-Native** |
| **Ceremony** | Low | Medium | **Lowest** |
| **Performance** | High | Medium | **Highest** |
| **Organization** | Vertical Slices | Layered | **Flexible** |
| **Learning Curve** | Medium | Low | **Low** |
| **Boilerplate** | Low | High | **Lowest** |

## Key Benefits

### Performance
- Fastest .NET web API pattern
- Minimal overhead and ceremony
- Optimized for cloud-native deployments
- Lower memory footprint

### Developer Experience
- Less boilerplate code
- Functional programming style
- Strong typing with TypedResults
- Easy to test and maintain

### Modern Patterns
- Vertical slice architecture
- Endpoint filters for cross-cutting concerns
- Route groups for organization
- ErrorOr for functional error handling

## Technology Stack

### Core Framework
- .NET 8.0+ Minimal APIs
- Top-level statements
- Endpoint routing
- Route groups

### Error Handling
- ErrorOr pattern
- ProblemDetails support
- Endpoint filters

### Validation
- FluentValidation
- Custom validation filters

### Testing
- xUnit
- FluentAssertions
- WebApplicationFactory
- Moq

### Documentation
- OpenAPI/Swagger
- Endpoint descriptions
- TypedResults support

### Observability
- OpenTelemetry
- Serilog structured logging
- Health checks

## Configuration

### appsettings.json

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*",
  "ConnectionStrings": {
    "DefaultConnection": "..."
  },
  "JwtSettings": {
    "Secret": "...",
    "Issuer": "...",
    "Audience": "..."
  }
}
```

## Testing

### Unit Testing Endpoints

```csharp
[Fact]
public async Task Handle_WhenWeatherExists_ReturnsOk()
{
    // Arrange
    var weather = new Weather { Id = 1, Location = "Sydney" };
    _serviceMock.Setup(x => x.GetWeatherByIdAsync(1))
        .ReturnsAsync(weather);

    // Act
    var result = await GetWeatherEndpoint.Handle(1, _serviceMock.Object);

    // Assert
    result.Result.Should().BeOfType<Ok<WeatherResponse>>();
}
```

### Integration Testing

```csharp
public class WeatherEndpointsTests : IClassFixture<ApiFactory>
{
    [Fact]
    public async Task GetWeather_WhenExists_ReturnsOk()
    {
        var response = await _client.GetAsync("/api/weather/1");
        response.StatusCode.Should().Be(HttpStatusCode.OK);
    }
}
```

## Best Practices

1. **Organize by Feature**: Use vertical slice architecture
2. **Use TypedResults**: Leverage compile-time safety
3. **Apply ErrorOr**: Functional error handling in services
4. **Group Endpoints**: Use route groups for related endpoints
5. **Add Filters**: Validation, logging, error handling
6. **Document APIs**: Use WithSummary and WithDescription
7. **Test Thoroughly**: Unit and integration tests
8. **Follow Conventions**: Consistent naming and structure

## Resources

- [Official Minimal APIs Documentation](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis)
- [ErrorOr Library](https://github.com/amantinband/error-or)
- [Vertical Slice Architecture](https://www.jimmybogard.com/vertical-slice-architecture/)
- [FluentValidation](https://fluentvalidation.net/)

## Support

For issues, questions, or contributions, please refer to the main Taskwright repository.

## License

This template is part of the Taskwright project and follows the same license.
