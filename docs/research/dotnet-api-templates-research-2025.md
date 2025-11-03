# .NET API Templates Research - 2025 Best Practices

**Date**: 2025-11-03  
**Purpose**: Research for creating three distinct .NET API templates (FastEndpoints, Controllers, Minimal API)

---

## Executive Summary

Modern .NET 8+ offers three viable approaches for building Web APIs, each with distinct strengths:

| Approach | Best For | Ceremony Level | Performance | Learning Curve |
|----------|----------|----------------|-------------|----------------|
| **FastEndpoints** | CQRS, DDD, Vertical Slices | Low | High | Medium |
| **Controllers** | Traditional Enterprise, Familiar Teams | Medium | Medium | Low |
| **Minimal API** | Microservices, Cloud-Native, Simple APIs | Lowest | Highest | Low |

---

## 1. ASP.NET Core Controller-Based APIs

### Architecture Patterns

#### Clean/Onion Architecture
- Most common architecture in web application development
- Developed with repository patterns and dependency injection
- **Layer Structure**:
  - **Domain/Core**: Business logic, doesn't depend on other layers
  - **Application**: Interfaces for infrastructure, use cases
  - **Infrastructure**: Concrete implementations (repositories, EF Core)
  - **API/Presentation**: Controllers

#### Dependency Flow
- Dependency is **inward facing only**
- Satisfies Dependency Inversion from SOLID principles
- Application layer only accesses Domain layer
- Infrastructure and Presentation layers access Application layer

### Repository Pattern Considerations

**Arguments FOR Repository Pattern**:
- Abstraction over data access
- Easy to mock for testing
- Enforces consistent data access patterns
- Domain layer doesn't know about EF Core

**Arguments AGAINST** (Important Debate):
- EF Core **already implements** Repository and Unit of Work patterns
- Adds extra layer of abstraction
- Can leak IQueryable and violate abstraction

**Recommendation**: 
- Use repository pattern when:
  - Multiple data sources
  - Need to swap ORMs
  - Team preference for explicit abstraction
- Skip repository pattern when:
  - Single data source (EF Core only)
  - Small/medium projects
  - Team comfortable with EF Core directly

### Controller Design Principles

**Keep Controllers Thin**:
```csharp
[ApiController]
[Route("api/[controller]")]
public class WeatherController : ControllerBase
{
    private readonly IWeatherService _service;
    
    public WeatherController(IWeatherService service) => _service = service;
    
    [HttpGet("{id}")]
    public async Task<ActionResult<WeatherResponse>> Get(int id)
    {
        var result = await _service.GetWeatherAsync(id);
        return result.Match(
            success => Ok(success),
            error => NotFound(error.Message)
        );
    }
}
```

**Key Principles**:
- Controllers should be as clean as possible
- **No business logic** in controllers
- Always use **async/await** (entire call stack asynchronous)
- Return appropriate HTTP status codes
- Use ActionResult<T> for type safety

### Best Practices

#### 1. Routing
- Use **nouns**, not verbs: `/api/weather` not `/api/getweather`
- Follow RESTful principles
- Use attribute routing over conventional routing

#### 2. Pagination
- Always paginate collections
- Use page size and page index parameters
- Return partial results for performance

#### 3. Exception Handling
- **Exceptions should be rare**
- Throwing/catching exceptions is slow
- Don't use exceptions for normal program flow
- Use Result/ErrorOr patterns for expected failures

#### 4. Dependency Injection
- Register services in IOC container
- Use scoped lifetime for EF Core DbContext
- Use singleton for stateless services

#### 5. Performance
- Use async/await throughout
- Avoid N+1 query problems
- Use projection (Select) instead of fetching full entities
- Consider response caching

### Recommended Structure

```
dotnet-aspnetcontroller/
├── src/
│   ├── Api/
│   │   ├── Controllers/
│   │   ├── Filters/           # Action filters, exception filters
│   │   ├── Middleware/        # Error handling, logging
│   │   └── Program.cs
│   ├── Application/
│   │   ├── Services/          # Business logic
│   │   ├── Interfaces/        # Service contracts
│   │   ├── DTOs/              # Data transfer objects
│   │   └── Validators/        # FluentValidation
│   ├── Domain/
│   │   ├── Entities/          # Domain models
│   │   ├── Common/
│   │   │   └── Result.cs      # Result pattern
│   │   └── Errors/            # Domain errors
│   └── Infrastructure/
│       ├── Persistence/       # EF Core, repositories
│       └── Configuration/     # DB config, migrations
```

### Essential NuGet Packages

- **FluentValidation.AspNetCore** - Request validation
- **ErrorOr** or **LanguageExt** - Result pattern
- **Swashbuckle.AspNetCore** - OpenAPI/Swagger
- **Serilog.AspNetCore** - Structured logging
- **MediatR** (optional) - CQRS pattern
- **AutoMapper** or **Mapster** - Object mapping

---

## 2. Minimal API Approach

### Architecture Patterns

#### Vertical Slice Architecture (Recommended)

**Philosophy**: Organize code by features, not technical layers

```
Features/
└── Weather/
    ├── GetWeather.cs          # Query handler
    ├── CreateWeather.cs       # Command handler
    ├── WeatherEndpoints.cs    # Endpoint definitions
    └── WeatherValidator.cs    # FluentValidation
```

**Benefits**:
- All related code in one place
- Easy to add/remove features
- Reduces merge conflicts
- Clear feature ownership

**vs. Layered Architecture**:
- No shared layers like repositories, services
- Think vertical (features) not horizontal (layers)
- Reduces coupling between features

#### CQRS with Minimal API

**Popular Pattern**: MediatR + Vertical Slices + Minimal API

```csharp
// Feature: Get Weather
public record GetWeatherQuery(int Id) : IRequest<Result<WeatherResponse>>;

public class GetWeatherHandler : IRequestHandler<GetWeatherQuery, Result<WeatherResponse>>
{
    // Handler implementation
}

// Endpoint definition
public static class WeatherEndpoints
{
    public static void MapWeatherEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/weather")
            .WithTags("Weather")
            .WithOpenApi();

        group.MapGet("/{id}", async (int id, IMediator mediator) =>
        {
            var result = await mediator.Send(new GetWeatherQuery(id));
            return result.Match(
                success => Results.Ok(success),
                error => Results.NotFound()
            );
        });
    }
}
```

### Route Groups (Essential Pattern)

**Benefits**:
- Reduce repetitive code
- Apply common metadata/filters to groups
- Support nested groups
- Organize related endpoints

**Example**:
```csharp
var api = app.MapGroup("/api")
    .AddEndpointFilter<ErrorHandlingFilter>()
    .RequireAuthorization();

var weather = api.MapGroup("/weather")
    .WithTags("Weather")
    .WithOpenApi();

weather.MapGet("/", GetWeather);
weather.MapPost("/", CreateWeather)
    .AddEndpointFilter<ValidationFilter<CreateWeatherRequest>>();
```

**Global Filter Pattern**:
```csharp
// Apply filters to ALL endpoints
var root = app.MapGroup("")
    .AddEndpointFilter<GlobalLoggingFilter>()
    .AddEndpointFilter<GlobalErrorFilter>();

// All endpoints now inherit global filters
root.MapGroup("/api/weather").MapWeatherEndpoints();
root.MapGroup("/api/forecast").MapForecastEndpoints();
```

### Endpoint Filters

**Key Difference from Middleware**:
- MVC: Opt-out (runs entire filter pipeline)
- Minimal API: Opt-in (explicit filter registration)

**Filter Execution**:
```csharp
public class ValidationFilter<T> : IEndpointFilter where T : class
{
    public async ValueTask<object?> InvokeAsync(
        EndpointFilterInvocationContext context,
        EndpointFilterDelegate next)
    {
        var request = context.GetArgument<T>(0);
        var validator = context.HttpContext.RequestServices
            .GetRequiredService<IValidator<T>>();
        
        var result = await validator.ValidateAsync(request);
        
        if (!result.IsValid)
            return Results.ValidationProblem(result.ToDictionary());
        
        return await next(context); // Continue to next filter/endpoint
    }
}
```

**Filter Order**:
- Order matters if applied to same group/endpoint
- Order doesn't matter if applied to different groups
- Filters execute in registration order

### TypedResults (Best Practice)

**Benefits**:
- Type-safe responses
- Better OpenAPI documentation
- Compile-time checking

**Example**:
```csharp
static async Task<Results<Ok<WeatherResponse>, NotFound, ValidationProblem>> GetWeather(
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

### Organization Strategies

#### Option 1: Carter Library
- Fluent API for endpoint definition
- Automatic endpoint discovery
- Clean organization

```csharp
public class WeatherModule : ICarterModule
{
    public void AddRoutes(IEndpointRouteBuilder app)
    {
        app.MapGroup("/api/weather")
            .MapGet("/{id}", GetWeather)
            .WithName("GetWeather");
    }
}
```

#### Option 2: Extension Methods
```csharp
public static class WeatherEndpoints
{
    public static IEndpointRouteBuilder MapWeatherEndpoints(
        this IEndpointRouteBuilder app)
    {
        // Endpoint definitions
        return app;
    }
}

// In Program.cs
app.MapWeatherEndpoints();
```

#### Option 3: Feature Folders
```
Features/
├── Weather/
│   ├── Endpoints/
│   ├── Queries/
│   ├── Commands/
│   └── Validators/
```

### Performance Advantages

Minimal APIs are **the fastest** option:
- Less overhead than MVC/Controllers
- No action filter pipeline by default
- Optimized for cloud/microservices
- Better throughput in benchmarks

### Recommended Structure

```
dotnet-minimalapi/
├── src/
│   ├── Api/
│   │   ├── Features/
│   │   │   └── Weather/
│   │   │       ├── GetWeather.cs
│   │   │       ├── CreateWeather.cs
│   │   │       └── Endpoints.cs
│   │   ├── Filters/
│   │   │   ├── ValidationFilter.cs
│   │   │   └── ErrorHandlingFilter.cs
│   │   ├── Extensions/
│   │   │   └── EndpointExtensions.cs
│   │   └── Program.cs
│   ├── Application/         # Optional for complex scenarios
│   ├── Domain/
│   └── Infrastructure/
```

### Essential NuGet Packages

- **Carter** - Endpoint organization (optional)
- **FluentValidation** - Validation
- **MediatR** - CQRS (optional)
- **ErrorOr** - Result pattern
- **Mapster** - Fast object mapping
- **MinimalCQRS** - Zero-setup CQRS (optional)

---

## 3. Comparison Matrix

### When to Use Each Approach

| Scenario | FastEndpoints | Controllers | Minimal API |
|----------|--------------|-------------|-------------|
| Microservices | ✅ Excellent | ⚠️ Works | ✅ Best |
| Enterprise Monolith | ✅ Good | ✅ Best | ⚠️ Works |
| Team New to .NET | ⚠️ Medium | ✅ Best | ✅ Good |
| CQRS Architecture | ✅ Best | ⚠️ Complex | ✅ Excellent |
| Vertical Slices | ✅ Best | ❌ Not Natural | ✅ Excellent |
| Traditional Layers | ⚠️ Works | ✅ Best | ⚠️ Works |
| Performance Critical | ✅ Excellent | ⚠️ Good | ✅ Best |
| Simple CRUD | ⚠️ Overkill | ✅ Good | ✅ Best |
| Complex Business Logic | ✅ Excellent | ✅ Excellent | ⚠️ Can Work |

### Feature Comparison

| Feature | FastEndpoints | Controllers | Minimal API |
|---------|--------------|-------------|-------------|
| OpenAPI/Swagger | ✅ Built-in | ✅ Swashbuckle | ✅ Built-in (.NET 8+) |
| Validation | ✅ FluentValidation | ✅ FluentValidation | ✅ Endpoint Filters |
| Dependency Injection | ✅ Full Support | ✅ Full Support | ✅ Full Support |
| Testing | ✅ Easy | ✅ Easy | ✅ Easy |
| Code Organization | ✅ Vertical Slices | ⚠️ Layers | ✅ Flexible |
| Learning Resources | ⚠️ Limited | ✅ Extensive | ✅ Growing |
| Community Size | ⚠️ Small | ✅ Huge | ✅ Growing |

---

## 4. Shared Patterns Across All Templates

### ErrorOr / Result Pattern

All three templates should use consistent error handling:

```csharp
public sealed record Error(string Code, string Description);

public class Result<T>
{
    public bool IsSuccess { get; }
    public T Value { get; }
    public Error Error { get; }
    
    public TResult Match<TResult>(
        Func<T, TResult> onSuccess,
        Func<Error, TResult> onFailure)
    {
        return IsSuccess ? onSuccess(Value) : onFailure(Error);
    }
}
```

### FluentValidation

All templates should use FluentValidation for consistency:

```csharp
public class CreateWeatherRequestValidator : AbstractValidator<CreateWeatherRequest>
{
    public CreateWeatherRequestValidator()
    {
        RuleFor(x => x.Temperature)
            .InclusiveBetween(-100, 100);
    }
}
```

### Testing Approach

All templates should include:
- **Unit Tests**: Business logic, validators
- **Integration Tests**: WebApplicationFactory
- **Architecture Tests**: Layer dependencies (optional)

```csharp
public class WeatherEndpointTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;
    
    public WeatherEndpointTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }
    
    [Fact]
    public async Task GetWeather_ReturnsOk()
    {
        var response = await _client.GetAsync("/api/weather/1");
        response.StatusCode.Should().Be(HttpStatusCode.OK);
    }
}
```

---

## 5. Recommendations

### Template Naming

- `dotnet-fastendpoints` - Current template, rename from dotnet-microservice
- `dotnet-aspnetcontroller` - Traditional controller-based
- `dotnet-minimalapi` - Modern minimal API

### Implementation Priority

1. **TASK-038**: Rename dotnet-microservice → dotnet-fastendpoints (Low effort)
2. **TASK-040**: Create dotnet-minimalapi (High demand, modern approach)
3. **TASK-039**: Create dotnet-aspnetcontroller (Traditional, team familiarity)

### Shared Components

Create shared/common components for all templates:
- ErrorOr/Result pattern
- FluentValidation setup
- Testing utilities
- OpenAPI configuration
- Health checks
- Logging configuration

---

## References

**Controller Best Practices**:
- https://code-maze.com/aspnetcore-webapi-best-practices/
- https://learn.microsoft.com/en-us/aspnet/core/fundamentals/best-practices
- https://medium.com/@codebob75/repository-pattern-c-ultimate-guide

**Minimal API**:
- https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis
- https://github.com/isaacOjeda/MinimalApiArchitecture
- https://mehmetozkaya.medium.com/net-8-microservices-ddd-cqrs-vertical-clean-architecture-2dd7ebaaf4bd

**Vertical Slice Architecture**:
- https://medium.com/@v.cheshmy/introduction-ae32b9f32ac5
- https://dev.to/kedzior_io/building-net-8-apis-with-zero-setup-cqrs-and-vertical-slice-architecture-528p

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-03  
**Next Review**: Before implementation of TASK-039, TASK-040
