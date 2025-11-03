# .NET Minimal API Project Context for Claude Code

This is a .NET 8+ API project using Minimal APIs with functional error handling via the ErrorOr pattern.

## Technology Stack
- **Framework**: .NET 8.0+ with Minimal APIs
- **Architecture**: Vertical Slices with feature-based organization
- **Error Handling**: ErrorOr pattern for functional error handling
- **Testing**: xUnit with FluentAssertions
- **API Documentation**: OpenAPI/Swagger via Microsoft.AspNetCore.OpenApi
- **Observability**: OpenTelemetry with Serilog structured logging
- **Authentication**: JWT Bearer tokens
- **Validation**: FluentValidation with endpoint filters
- **HTTP Client**: Typed clients with Polly resilience
- **Health Checks**: ASP.NET Core Health Checks

## Project Structure

### API Project Structure
```
{ServiceName}.API/
├── .claude/              # Agentic Flow configuration
├── Program.cs            # Application entry point with DI and endpoint registration
├── appsettings.json      # Configuration
├── Features/
│   └── {Feature}/
│       ├── Get{Feature}.cs
│       ├── Create{Feature}.cs
│       ├── Update{Feature}.cs
│       └── Delete{Feature}.cs
├── Filters/
│   ├── ValidationFilter.cs
│   └── ErrorHandlingFilter.cs
├── Extensions/
│   ├── EndpointExtensions.cs
│   └── RouteGroupExtensions.cs
├── Domain/
│   ├── Common/
│   │   ├── BaseError.cs     # Base error types
│   │   └── Result.cs        # Result pattern
│   ├── DomainErrors.cs      # Specific error types
│   ├── Entities/            # Domain entities
│   └── ValueObjects/        # Domain value objects
├── Application/
│   ├── Services/
│   │   ├── Interfaces/
│   │   │   └── I{Service}.cs
│   │   └── Implementations/
│   │       └── {Service}.cs
│   ├── DTOs/
│   │   ├── Requests/
│   │   ├── Responses/
│   │   └── Common/
│   └── Validators/
│       └── {Feature}Validator.cs
├── Infrastructure/
│   ├── Repositories/
│   │   ├── Interfaces/
│   │   │   └── I{Repository}.cs
│   │   └── Implementations/
│   │       └── {Repository}.cs
│   ├── Persistence/
│   │   └── DbContext (if using EF Core)
│   └── HttpClients/
│       └── Typed HTTP clients
└── Dockerfile

{ServiceName}.Tests/
├── Unit/
│   ├── Endpoints/
│   ├── Services/
│   ├── Repositories/
│   └── Validators/
├── Integration/
│   ├── Endpoints/
│   └── Fixtures/
│       └── ApiFactory.cs
└── TestHelpers/
    └── HttpTestHelpers.cs
```

## Development Standards

### Minimal API Endpoint Pattern with ErrorOr

```csharp
using ErrorOr;
using Microsoft.AspNetCore.Http.HttpResults;

public static class GetWeatherEndpoint
{
    public static async Task<Results<Ok<WeatherResponse>, NotFound, ProblemHttpResult>> Handle(
        int id,
        IWeatherService service,
        ILogger<GetWeatherEndpoint> logger)
    {
        logger.LogInformation("Getting weather with ID: {Id}", id);

        ErrorOr<Weather> result = await service.GetWeatherByIdAsync(id);

        return result.Match(
            weather => TypedResults.Ok(weather.ToResponse()),
            errors => errors[0] switch
            {
                { Type: ErrorType.NotFound } => TypedResults.NotFound(),
                _ => TypedResults.Problem(errors.ToProblemDetails())
            }
        );
    }
}
```

### Route Group Organization

```csharp
var weather = app.MapGroup("/api/weather")
    .WithTags("Weather")
    .WithOpenApi()
    .AddEndpointFilter<ValidationFilter>()
    .AddEndpointFilter<ErrorHandlingFilter>();

weather.MapGet("/{id:int}", GetWeatherEndpoint.Handle)
    .WithName("GetWeather")
    .WithSummary("Get weather by ID")
    .Produces<WeatherResponse>(StatusCodes.Status200OK)
    .Produces(StatusCodes.Status404NotFound);

weather.MapPost("/", CreateWeatherEndpoint.Handle)
    .WithName("CreateWeather")
    .WithSummary("Create new weather entry")
    .Produces<WeatherResponse>(StatusCodes.Status201Created)
    .ProducesValidationProblem();
```

### Endpoint Filters

```csharp
public class ValidationFilter<TRequest> : IEndpointFilter where TRequest : class
{
    private readonly IValidator<TRequest> _validator;

    public ValidationFilter(IValidator<TRequest> validator)
    {
        _validator = validator;
    }

    public async ValueTask<object?> InvokeAsync(
        EndpointFilterInvocationContext context,
        EndpointFilterDelegate next)
    {
        var request = context.GetArgument<TRequest>(0);

        var validationResult = await _validator.ValidateAsync(request);

        if (!validationResult.IsValid)
        {
            return TypedResults.ValidationProblem(
                validationResult.ToDictionary());
        }

        return await next(context);
    }
}
```

### Service Layer with ErrorOr

```csharp
public interface IWeatherService
{
    Task<ErrorOr<Weather>> GetWeatherByIdAsync(int id);
    Task<ErrorOr<Weather>> CreateWeatherAsync(CreateWeatherRequest request);
}

public class WeatherService : IWeatherService
{
    private readonly IWeatherRepository _repository;
    private readonly ILogger<WeatherService> _logger;

    public WeatherService(
        IWeatherRepository repository,
        ILogger<WeatherService> logger)
    {
        _repository = repository;
        _logger = logger;
    }

    public async Task<ErrorOr<Weather>> GetWeatherByIdAsync(int id)
    {
        var weather = await _repository.GetByIdAsync(id);

        if (weather is null)
        {
            return DomainErrors.Weather.NotFound(id);
        }

        return weather;
    }

    public async Task<ErrorOr<Weather>> CreateWeatherAsync(CreateWeatherRequest request)
    {
        var weather = Weather.Create(request.Location, request.Temperature);

        if (weather.IsError)
        {
            return weather.Errors;
        }

        await _repository.AddAsync(weather.Value);

        return weather.Value;
    }
}
```

### Domain Errors

```csharp
public static class DomainErrors
{
    public static class Weather
    {
        public static Error NotFound(int id) => Error.NotFound(
            "Weather.NotFound",
            $"Weather with ID {id} was not found");

        public static Error InvalidTemperature => Error.Validation(
            "Weather.InvalidTemperature",
            "Temperature must be between -100 and 100");

        public static Error DuplicateLocation => Error.Conflict(
            "Weather.DuplicateLocation",
            "A weather entry for this location already exists");
    }
}
```

### Extension Methods for Error Handling

```csharp
public static class ErrorExtensions
{
    public static ProblemDetails ToProblemDetails(this List<Error> errors)
    {
        var firstError = errors[0];

        var statusCode = firstError.Type switch
        {
            ErrorType.NotFound => StatusCodes.Status404NotFound,
            ErrorType.Validation => StatusCodes.Status400BadRequest,
            ErrorType.Conflict => StatusCodes.Status409Conflict,
            _ => StatusCodes.Status500InternalServerError
        };

        return new ProblemDetails
        {
            Status = statusCode,
            Title = firstError.Code,
            Detail = firstError.Description,
            Extensions = { ["errors"] = errors.Select(e => e.Description).ToArray() }
        };
    }
}
```

## Testing Patterns

### Unit Testing Endpoints

```csharp
public class GetWeatherEndpointTests
{
    private readonly Mock<IWeatherService> _serviceMock;
    private readonly Mock<ILogger<GetWeatherEndpoint>> _loggerMock;

    public GetWeatherEndpointTests()
    {
        _serviceMock = new Mock<IWeatherService>();
        _loggerMock = new Mock<ILogger<GetWeatherEndpoint>>();
    }

    [Fact]
    public async Task Handle_WhenWeatherExists_ReturnsOk()
    {
        // Arrange
        var weather = new Weather { Id = 1, Location = "Sydney" };
        _serviceMock
            .Setup(x => x.GetWeatherByIdAsync(1))
            .ReturnsAsync(weather);

        // Act
        var result = await GetWeatherEndpoint.Handle(1, _serviceMock.Object, _loggerMock.Object);

        // Assert
        result.Result.Should().BeOfType<Ok<WeatherResponse>>();
    }

    [Fact]
    public async Task Handle_WhenWeatherNotFound_ReturnsNotFound()
    {
        // Arrange
        _serviceMock
            .Setup(x => x.GetWeatherByIdAsync(1))
            .ReturnsAsync(DomainErrors.Weather.NotFound(1));

        // Act
        var result = await GetWeatherEndpoint.Handle(1, _serviceMock.Object, _loggerMock.Object);

        // Assert
        result.Result.Should().BeOfType<NotFound>();
    }
}
```

### Integration Testing with WebApplicationFactory

```csharp
public class WeatherEndpointsTests : IClassFixture<ApiFactory>
{
    private readonly HttpClient _client;

    public WeatherEndpointsTests(ApiFactory factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task GetWeather_WhenExists_ReturnsOk()
    {
        // Arrange
        var id = 1;

        // Act
        var response = await _client.GetAsync($"/api/weather/{id}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);

        var weather = await response.Content.ReadFromJsonAsync<WeatherResponse>();
        weather.Should().NotBeNull();
        weather!.Id.Should().Be(id);
    }

    [Fact]
    public async Task GetWeather_WhenNotFound_ReturnsNotFound()
    {
        // Arrange
        var id = 999;

        // Act
        var response = await _client.GetAsync($"/api/weather/{id}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }

    [Fact]
    public async Task CreateWeather_WithValidData_ReturnsCreated()
    {
        // Arrange
        var request = new CreateWeatherRequest
        {
            Location = "Melbourne",
            Temperature = 22
        };

        // Act
        var response = await _client.PostAsJsonAsync("/api/weather", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);

        var weather = await response.Content.ReadFromJsonAsync<WeatherResponse>();
        weather.Should().NotBeNull();
        weather!.Location.Should().Be(request.Location);
    }
}
```

## Key Minimal API Patterns

### 1. Static Methods for Endpoints
- Keep endpoint logic in static methods for better testability
- Group related endpoints in static classes (e.g., `WeatherEndpoints`)

### 2. TypedResults for Compile-Time Safety
- Use `Results<T1, T2, T3>` return type for explicit response types
- Enables OpenAPI to document all possible responses
- Provides compile-time safety for response types

### 3. Route Groups for Organization
- Organize endpoints by feature using `MapGroup`
- Apply common filters, middleware, and metadata to groups
- Improves code organization and reduces duplication

### 4. Endpoint Filters for Cross-Cutting Concerns
- Use filters for validation, logging, error handling, auth
- Filters execute in order, allowing pipeline composition
- More lightweight than middleware for endpoint-specific logic

### 5. Vertical Slice Architecture
- Organize code by feature, not layer
- Each feature contains endpoints, services, validators in one folder
- Reduces cognitive load and improves maintainability

## Performance Characteristics

Minimal APIs provide the best performance of all .NET web API patterns:
- Minimal ceremony and overhead
- Direct handler invocation without controller abstraction
- Optimized for cloud-native and microservices
- Lower memory footprint than controllers

## When to Use Minimal API

**Use When:**
- Building microservices or cloud-native APIs
- Performance is critical
- Prefer functional programming style
- Want minimal ceremony and boilerplate
- Building simple CRUD services
- Team comfortable with C# and modern patterns

**Consider Alternatives When:**
- Large monolithic APIs (Controllers provide better organization)
- Need REPR pattern features (use FastEndpoints)
- Complex CQRS workflows (use FastEndpoints with MediatR)
- Team prefers traditional MVC patterns

## NuGet Packages

Essential packages for Minimal API projects:

```xml
<PackageReference Include="ErrorOr" Version="1.3.0" />
<PackageReference Include="FluentValidation" Version="11.8.0" />
<PackageReference Include="FluentValidation.DependencyInjectionExtensions" Version="11.8.0" />
<PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="8.0.0" />
<PackageReference Include="Swashbuckle.AspNetCore" Version="6.5.0" />
<PackageReference Include="Serilog.AspNetCore" Version="8.0.0" />
<PackageReference Include="OpenTelemetry.Exporter.Console" Version="1.6.0" />
<PackageReference Include="OpenTelemetry.Extensions.Hosting" Version="1.6.0" />
<PackageReference Include="OpenTelemetry.Instrumentation.AspNetCore" Version="1.6.0" />
```

Test packages:
```xml
<PackageReference Include="xUnit" Version="2.6.0" />
<PackageReference Include="xUnit.runner.visualstudio" Version="2.5.3" />
<PackageReference Include="FluentAssertions" Version="6.12.0" />
<PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="8.0.0" />
<PackageReference Include="Moq" Version="4.20.69" />
```

## AI Task Guidelines

When implementing features in a Minimal API project:

1. **Organize by Feature**: Create feature folders with all related files
2. **Use TypedResults**: Always return strongly-typed results
3. **Apply ErrorOr Pattern**: All service methods return `ErrorOr<T>`
4. **Group Endpoints**: Use route groups for related endpoints
5. **Add Filters**: Apply validation and error handling filters
6. **Document Endpoints**: Use WithSummary, WithDescription, Produces
7. **Test Thoroughly**: Write both unit and integration tests
8. **Follow Naming**: {Verb}{Feature}Endpoint.cs for endpoint classes

## Example Feature Implementation

When asked to implement a new feature (e.g., "Add product management"), create:

```
Features/Products/
├── GetProduct.cs           # GET /api/products/{id}
├── GetProducts.cs          # GET /api/products
├── CreateProduct.cs        # POST /api/products
├── UpdateProduct.cs        # PUT /api/products/{id}
├── DeleteProduct.cs        # DELETE /api/products/{id}
└── ProductEndpoints.cs     # Route group configuration

Application/Services/
├── Interfaces/
│   └── IProductService.cs
└── Implementations/
    └── ProductService.cs

Application/Validators/
└── CreateProductValidator.cs
└── UpdateProductValidator.cs

Domain/Entities/
└── Product.cs

Tests/Unit/Endpoints/
└── GetProductEndpointTests.cs

Tests/Integration/Endpoints/
└── ProductEndpointsTests.cs
```

## Comparison with Other .NET API Templates

| Feature | FastEndpoints | ASP.NET Controllers | Minimal API |
|---------|--------------|---------------------|-------------|
| **Best For** | CQRS, Vertical Slices | Enterprise, Traditional | Microservices, Cloud-Native |
| **Ceremony** | Low | Medium | Lowest |
| **Performance** | High | Medium | Highest |
| **Organization** | Vertical Slices | Layered | Flexible (Vertical Slices Recommended) |
| **Learning Curve** | Medium | Low (familiar) | Low |
| **Boilerplate** | Low | High | Lowest |
| **Testability** | High | High | High |
| **OpenAPI Support** | Excellent | Excellent | Excellent |

## Additional Resources

- [Minimal APIs Overview](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis)
- [Route Groups](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis/route-handlers#route-groups)
- [Endpoint Filters](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis/min-api-filters)
- [ErrorOr Library](https://github.com/amantinband/error-or)
- [Vertical Slice Architecture](https://www.jimmybogard.com/vertical-slice-architecture/)
