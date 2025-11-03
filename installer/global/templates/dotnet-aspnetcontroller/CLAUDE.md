# .NET ASP.NET Controller API Project Context for Claude Code

This is a .NET 8+ API project using traditional ASP.NET Core Controllers with functional error handling via the ErrorOr pattern.

## Technology Stack
- **Framework**: .NET 8.0+ with ASP.NET Core Controllers (MVC pattern)
- **Architecture**: Layered Architecture (Controllers → Services → Domain → Infrastructure)
- **Error Handling**: ErrorOr pattern for functional error handling
- **Testing**: xUnit with FluentAssertions
- **API Documentation**: OpenAPI/Swagger via Swashbuckle
- **Observability**: OpenTelemetry with Serilog structured logging
- **Authentication**: JWT Bearer tokens
- **Validation**: FluentValidation with action filters
- **HTTP Client**: Typed clients with Polly resilience
- **Health Checks**: ASP.NET Core Health Checks

## Project Structure

### API Project Structure
```
{ServiceName}.API/
├── .claude/              # Agentic Flow configuration
├── Program.cs            # Application entry point with DI setup
├── appsettings.json      # Configuration
├── Controllers/
│   ├── {Feature}Controller.cs
│   └── HealthController.cs
├── Filters/
│   ├── ValidationFilter.cs
│   └── ExceptionFilter.cs
├── Middleware/
│   └── ExceptionMiddleware.cs
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
│   ├── Extensions/
│   │   ├── ControllerExtensions.cs
│   │   └── OpenTelemetryExtensions.cs
│   ├── Persistence/
│   │   └── DbContext (if using EF Core)
│   └── HttpClients/
│       └── Typed HTTP clients
└── Dockerfile

{ServiceName}.Tests/
├── Unit/
│   ├── Controllers/
│   ├── Services/
│   ├── Repositories/
│   └── Validators/
├── Integration/
│   ├── Controllers/
│   └── Fixtures/
│       └── ApiFactory.cs
└── TestHelpers/
    └── HttpTestHelpers.cs
```

## Development Standards

### Controller Pattern with ErrorOr

```csharp
using ErrorOr;
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/v1/[controller]")]
[Produces("application/json")]
public class {Feature}Controller : ControllerBase
{
    private readonly I{Feature}Service _service;
    private readonly ILogger<{Feature}Controller> _logger;

    public {Feature}Controller(
        I{Feature}Service service,
        ILogger<{Feature}Controller> logger)
    {
        _service = service;
        _logger = logger;
    }

    /// <summary>
    /// Get {feature} by ID
    /// </summary>
    /// <param name="id">The {feature} ID</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>The {feature} details</returns>
    [HttpGet("{id}")]
    [ProducesResponseType(typeof({Feature}Response), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetById(
        [FromRoute] Guid id,
        CancellationToken cancellationToken = default)
    {
        var result = await _service.Get{Feature}Async(id, cancellationToken);

        return result.Match(
            value => Ok(value),
            errors => Problem(errors)
        );
    }

    /// <summary>
    /// Create a new {feature}
    /// </summary>
    /// <param name="request">The {feature} creation request</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>The created {feature}</returns>
    [HttpPost]
    [ProducesResponseType(typeof({Feature}Response), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> Create(
        [FromBody] Create{Feature}Request request,
        CancellationToken cancellationToken = default)
    {
        var result = await _service.Create{Feature}Async(request, cancellationToken);

        return result.Match(
            value => CreatedAtAction(
                nameof(GetById),
                new { id = value.Id },
                value),
            errors => Problem(errors)
        );
    }

    /// <summary>
    /// Update an existing {feature}
    /// </summary>
    [HttpPut("{id}")]
    [ProducesResponseType(typeof({Feature}Response), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Update(
        [FromRoute] Guid id,
        [FromBody] Update{Feature}Request request,
        CancellationToken cancellationToken = default)
    {
        var result = await _service.Update{Feature}Async(id, request, cancellationToken);

        return result.Match(
            value => Ok(value),
            errors => Problem(errors)
        );
    }

    /// <summary>
    /// Delete a {feature}
    /// </summary>
    [HttpDelete("{id}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Delete(
        [FromRoute] Guid id,
        CancellationToken cancellationToken = default)
    {
        var result = await _service.Delete{Feature}Async(id, cancellationToken);

        return result.Match(
            _ => NoContent(),
            errors => Problem(errors)
        );
    }
}
```

### Service Pattern with ErrorOr

```csharp
using ErrorOr;

public interface I{Feature}Service
{
    Task<ErrorOr<{Feature}Response>> Get{Feature}Async(Guid id, CancellationToken ct);
    Task<ErrorOr<{Feature}Response>> Create{Feature}Async(Create{Feature}Request request, CancellationToken ct);
    Task<ErrorOr<{Feature}Response>> Update{Feature}Async(Guid id, Update{Feature}Request request, CancellationToken ct);
    Task<ErrorOr<Deleted>> Delete{Feature}Async(Guid id, CancellationToken ct);
}

public class {Feature}Service : I{Feature}Service
{
    private readonly I{Feature}Repository _repository;
    private readonly ILogger<{Feature}Service> _logger;

    public {Feature}Service(
        I{Feature}Repository repository,
        ILogger<{Feature}Service> logger)
    {
        _repository = repository;
        _logger = logger;
    }

    public async Task<ErrorOr<{Feature}Response>> Get{Feature}Async(
        Guid id,
        CancellationToken ct)
    {
        var entity = await _repository.GetByIdAsync(id, ct);

        if (entity is null)
        {
            _logger.LogWarning("{Feature} with ID {Id} not found", id);
            return Error.NotFound(
                "{Feature}.NotFound",
                $"{Feature} with ID {id} not found");
        }

        return new {Feature}Response
        {
            Id = entity.Id,
            Name = entity.Name,
            // ... map other properties
        };
    }

    public async Task<ErrorOr<{Feature}Response>> Create{Feature}Async(
        Create{Feature}Request request,
        CancellationToken ct)
    {
        // Check for duplicates
        var existing = await _repository.FindByNameAsync(request.Name, ct);
        if (existing is not null)
        {
            return Error.Conflict(
                "{Feature}.Duplicate",
                $"{Feature} with name '{request.Name}' already exists");
        }

        var entity = new {Feature}
        {
            Id = Guid.NewGuid(),
            Name = request.Name,
            // ... map other properties
            CreatedAt = DateTime.UtcNow
        };

        await _repository.AddAsync(entity, ct);

        _logger.LogInformation("{Feature} {Id} created successfully", entity.Id);

        return new {Feature}Response
        {
            Id = entity.Id,
            Name = entity.Name,
            // ... map other properties
        };
    }
}
```

### Domain Errors with ErrorOr

```csharp
using ErrorOr;

public static class Errors
{
    public static class {Feature}
    {
        public static Error NotFound => Error.NotFound(
            code: "{Feature}.NotFound",
            description: "{Feature} not found.");

        public static Error DuplicateName => Error.Conflict(
            code: "{Feature}.DuplicateName",
            description: "{Feature} with this name already exists.");

        public static Error InvalidData => Error.Validation(
            code: "{Feature}.InvalidData",
            description: "Invalid {feature} data provided.");
    }
}
```

### Controller Extensions for ErrorOr

```csharp
using ErrorOr;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.ModelBinding;

public static class ControllerExtensions
{
    /// <summary>
    /// Convert ErrorOr errors to ProblemDetails response
    /// </summary>
    public static IActionResult Problem(this ControllerBase controller, List<Error> errors)
    {
        if (errors.Count is 0)
        {
            return controller.Problem();
        }

        if (errors.All(error => error.Type == ErrorType.Validation))
        {
            return ValidationProblem(controller, errors);
        }

        return Problem(controller, errors[0]);
    }

    private static IActionResult Problem(ControllerBase controller, Error error)
    {
        var statusCode = error.Type switch
        {
            ErrorType.Conflict => StatusCodes.Status409Conflict,
            ErrorType.Validation => StatusCodes.Status400BadRequest,
            ErrorType.NotFound => StatusCodes.Status404NotFound,
            ErrorType.Unauthorized => StatusCodes.Status401Unauthorized,
            ErrorType.Forbidden => StatusCodes.Status403Forbidden,
            _ => StatusCodes.Status500InternalServerError,
        };

        return controller.Problem(
            statusCode: statusCode,
            title: GetTitle(error.Type),
            detail: error.Description,
            type: error.Code);
    }

    private static IActionResult ValidationProblem(
        ControllerBase controller,
        List<Error> errors)
    {
        var modelStateDictionary = new ModelStateDictionary();

        foreach (var error in errors)
        {
            modelStateDictionary.AddModelError(
                error.Code,
                error.Description);
        }

        return controller.ValidationProblem(modelStateDictionary);
    }

    private static string GetTitle(ErrorType errorType) => errorType switch
    {
        ErrorType.Conflict => "Conflict",
        ErrorType.Validation => "Validation Error",
        ErrorType.NotFound => "Not Found",
        ErrorType.Unauthorized => "Unauthorized",
        ErrorType.Forbidden => "Forbidden",
        _ => "Server Error"
    };
}
```

### Validation Pattern with Action Filter

```csharp
using FluentValidation;

public class Create{Feature}Validator : AbstractValidator<Create{Feature}Request>
{
    public Create{Feature}Validator()
    {
        RuleFor(x => x.Name)
            .NotEmpty().WithMessage("Name is required")
            .MaximumLength(100).WithMessage("Name must not exceed 100 characters");

        RuleFor(x => x.Email)
            .NotEmpty().WithMessage("Email is required")
            .EmailAddress().WithMessage("Invalid email format");

        RuleFor(x => x.Value)
            .GreaterThan(0).WithMessage("Value must be greater than zero");
    }
}

// Action Filter for validation
public class ValidationFilter : IAsyncActionFilter
{
    private readonly IServiceProvider _serviceProvider;

    public ValidationFilter(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    public async Task OnActionExecutionAsync(
        ActionExecutingContext context,
        ActionExecutionDelegate next)
    {
        if (!context.ModelState.IsValid)
        {
            context.Result = new BadRequestObjectResult(context.ModelState);
            return;
        }

        await next();
    }
}
```

### Exception Middleware

```csharp
public class ExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionMiddleware> _logger;

    public ExceptionMiddleware(
        RequestDelegate next,
        ILogger<ExceptionMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "An unhandled exception occurred");
            await HandleExceptionAsync(context, ex);
        }
    }

    private static async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        context.Response.ContentType = "application/problem+json";
        context.Response.StatusCode = StatusCodes.Status500InternalServerError;

        var problemDetails = new ProblemDetails
        {
            Status = StatusCodes.Status500InternalServerError,
            Title = "An error occurred while processing your request",
            Detail = exception.Message,
            Instance = context.Request.Path
        };

        await context.Response.WriteAsJsonAsync(problemDetails);
    }
}
```

## NuGet Packages Required

```xml
<!-- Core packages -->
<PackageReference Include="ErrorOr" Version="2.0.1" />
<PackageReference Include="FluentValidation.AspNetCore" Version="11.3.0" />
<PackageReference Include="Swashbuckle.AspNetCore" Version="6.6.2" />

<!-- OpenTelemetry -->
<PackageReference Include="OpenTelemetry" Version="1.11.2" />
<PackageReference Include="OpenTelemetry.Exporter.OpenTelemetryProtocol" Version="1.11.2" />
<PackageReference Include="OpenTelemetry.Extensions.Hosting" Version="1.11.2" />
<PackageReference Include="OpenTelemetry.Instrumentation.AspNetCore" Version="1.11.1" />
<PackageReference Include="OpenTelemetry.Instrumentation.Http" Version="1.11.1" />

<!-- Logging -->
<PackageReference Include="Serilog.AspNetCore" Version="9.0.0" />
<PackageReference Include="Serilog.Sinks.Console" Version="6.0.0" />
<PackageReference Include="Serilog.Sinks.OpenTelemetry" Version="4.1.1" />

<!-- Health Checks -->
<PackageReference Include="AspNetCore.HealthChecks.Uris" Version="9.0.0" />

<!-- HTTP Resilience -->
<PackageReference Include="Microsoft.Extensions.Http.Polly" Version="8.0.0" />

<!-- Testing packages -->
<PackageReference Include="xunit" Version="2.6.1" />
<PackageReference Include="xunit.runner.visualstudio" Version="2.5.3" />
<PackageReference Include="FluentAssertions" Version="6.12.0" />
<PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="8.0.0" />
<PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
<PackageReference Include="Moq" Version="4.20.0" />
```

## Testing Patterns

### Integration Testing

```csharp
public class {Feature}ControllerTests : IClassFixture<ApiFactory>
{
    private readonly ApiFactory _factory;
    private readonly HttpClient _client;

    public {Feature}ControllerTests(ApiFactory factory)
    {
        _factory = factory;
        _client = _factory.CreateClient();
    }

    [Fact]
    public async Task Get{Feature}_WhenExists_ReturnsOk()
    {
        // Arrange
        var id = Guid.NewGuid();
        _factory.Seed{Feature}(id);

        // Act
        var response = await _client.GetAsync($"/api/v1/{feature}/{id}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var content = await response.Content.ReadFromJsonAsync<{Feature}Response>();
        content.Should().NotBeNull();
        content!.Id.Should().Be(id);
    }

    [Fact]
    public async Task Get{Feature}_WhenNotFound_Returns404()
    {
        // Act
        var response = await _client.GetAsync($"/api/v1/{feature}/{Guid.NewGuid()}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
        var problemDetails = await response.Content.ReadFromJsonAsync<ProblemDetails>();
        problemDetails.Should().NotBeNull();
        problemDetails!.Status.Should().Be(404);
    }

    [Fact]
    public async Task Create{Feature}_WithValidData_ReturnsCreated()
    {
        // Arrange
        var request = new Create{Feature}Request
        {
            Name = "Test {Feature}",
            // ... other properties
        };

        // Act
        var response = await _client.PostAsJsonAsync("/api/v1/{feature}", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        var created = await response.Content.ReadFromJsonAsync<{Feature}Response>();
        created.Should().NotBeNull();
        created!.Name.Should().Be(request.Name);
        response.Headers.Location.Should().NotBeNull();
    }
}
```

### Unit Testing Controllers

```csharp
public class {Feature}ControllerTests
{
    private readonly Mock<I{Feature}Service> _serviceMock;
    private readonly {Feature}Controller _controller;

    public {Feature}ControllerTests()
    {
        _serviceMock = new Mock<I{Feature}Service>();
        var logger = new Mock<ILogger<{Feature}Controller>>();
        _controller = new {Feature}Controller(_serviceMock.Object, logger.Object);
    }

    [Fact]
    public async Task GetById_WhenExists_ReturnsOk()
    {
        // Arrange
        var id = Guid.NewGuid();
        var expected = new {Feature}Response { Id = id, Name = "Test" };
        _serviceMock
            .Setup(x => x.Get{Feature}Async(id, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expected);

        // Act
        var result = await _controller.GetById(id);

        // Assert
        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var response = okResult.Value.Should().BeOfType<{Feature}Response>().Subject;
        response.Id.Should().Be(id);
    }

    [Fact]
    public async Task GetById_WhenNotFound_ReturnsNotFound()
    {
        // Arrange
        var id = Guid.NewGuid();
        _serviceMock
            .Setup(x => x.Get{Feature}Async(id, It.IsAny<CancellationToken>()))
            .ReturnsAsync(Error.NotFound());

        // Act
        var result = await _controller.GetById(id);

        // Assert
        var notFoundResult = result.Should().BeOfType<ObjectResult>().Subject;
        notFoundResult.StatusCode.Should().Be(404);
    }
}
```

## Program.cs Configuration

```csharp
using Serilog;
using {ServiceName}.API.Infrastructure.Extensions;

var builder = WebApplication.CreateBuilder(args);

// Configure Serilog
builder.Host.UseSerilog((context, config) =>
{
    config.ReadFrom.Configuration(context.Configuration);
});

// Add controllers
builder.Services.AddControllers(options =>
{
    options.Filters.Add<ValidationFilter>();
});

// Add FluentValidation
builder.Services.AddValidatorsFromAssemblyContaining<Program>();

// Add Swagger
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new() { Title = "{ServiceName} API", Version = "v1" });

    // Enable XML comments
    var xmlFile = $"{Assembly.GetExecutingAssembly().GetName().Name}.xml";
    var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
    c.IncludeXmlComments(xmlPath);
});

// Add OpenTelemetry
builder.Services.AddOpenTelemetryServices(builder.Configuration);

// Add Health Checks
builder.Services.AddHealthChecks();

// Add CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

// Register domain services
builder.Services.AddScoped<I{Feature}Service, {Feature}Service>();
builder.Services.AddScoped<I{Feature}Repository, {Feature}Repository>();

// Add HTTP clients
builder.Services.AddHttpClient<IExternalApiClient, ExternalApiClient>()
    .AddPolicyHandler(GetRetryPolicy())
    .AddPolicyHandler(GetCircuitBreakerPolicy());

var app = builder.Build();

// Configure middleware pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseMiddleware<ExceptionMiddleware>();
app.UseHttpsRedirection();
app.UseCors("AllowAll");
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.MapHealthChecks("/api/v1/health");

app.Run();
```

## Best Practices

1. **Always use ErrorOr pattern** for operations that can fail
2. **Keep controllers thin** - delegate to services
3. **Use action filters** for cross-cutting concerns (validation, logging)
4. **Use structured logging** with correlation IDs
5. **Implement health checks** for all external dependencies
6. **Add OpenTelemetry** instrumentation for observability
7. **Validate all inputs** using FluentValidation
8. **Handle errors functionally** - avoid throwing exceptions in business logic
9. **Use typed HTTP clients** with resilience policies
10. **Test behavior, not implementation** - focus on contracts
11. **Document APIs** with XML comments and Swagger
12. **Use attribute routing** for clear route definitions
13. **Version your API** for backward compatibility
14. **Implement proper caching** strategies where appropriate
15. **Follow REST conventions** for resource naming and HTTP verbs

## Common Patterns

### Pagination

```csharp
public class PagedRequest
{
    [FromQuery] public int Page { get; set; } = 1;
    [FromQuery] public int PageSize { get; set; } = 20;
}

public class PagedResponse<T>
{
    public List<T> Data { get; set; } = new();
    public int TotalCount { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
    public int TotalPages => (int)Math.Ceiling(TotalCount / (double)PageSize);
}
```

### Response Caching

```csharp
[HttpGet("{id}")]
[ResponseCache(Duration = 60, VaryByQueryKeys = new[] { "id" })]
public async Task<IActionResult> GetById([FromRoute] Guid id)
{
    // Implementation
}
```

## Resources
- [ASP.NET Core Documentation](https://docs.microsoft.com/aspnet/core)
- [ErrorOr Library](https://github.com/amantinband/error-or)
- [OpenTelemetry .NET](https://opentelemetry.io/docs/instrumentation/net/)
- [Serilog Documentation](https://serilog.net)
- [FluentValidation](https://fluentvalidation.net)
