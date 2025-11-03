# .NET ASP.NET Controller API Template

This template provides a complete ASP.NET Core 8+ Web API structure using traditional Controllers with functional error handling via the ErrorOr pattern.

## Template Structure

```
templates/
├── CLAUDE.md                     # Instructions for Claude Code
├── BaseError.cs                  # Base error types for ErrorOr pattern
├── Result.cs                     # Result pattern implementation
├── ControllerExtensions.cs       # ErrorOr extensions for controllers
├── ValidationFilter.cs           # Model validation action filter
├── ExceptionMiddleware.cs        # Global exception handling
├── OpenTelemetryExtensions.cs    # Observability configuration
├── HealthController.cs           # Health check endpoints
├── SampleController.cs           # Example controller with CRUD operations
├── SampleService.cs              # Example service with ErrorOr pattern
├── SampleRepository.cs           # Example repository pattern
├── SampleValidator.cs            # FluentValidation examples
├── SampleEntity.cs               # Domain entity example
├── SampleRequests.cs             # Request DTOs
├── SampleResponses.cs            # Response DTOs
├── SampleDtos.cs                 # Data transfer objects
├── SampleControllerTests.cs      # Unit test examples
├── SampleIntegrationTests.cs     # Integration test examples
├── ApiFactory.cs                 # Test fixture for integration tests
├── Program.cs                    # Application entry point
├── API.csproj                    # API project file
├── Tests.csproj                  # Test project file
├── appsettings.json             # Configuration file
└── Dockerfile                    # Docker container definition
```

## Usage

### Variable Replacement

The template uses the following placeholder variables that should be replaced:

- `{ServiceName}` - The name of your API service (e.g., "ProductCatalog", "OrderManagement")
- `{Feature}` - The name of your domain feature (e.g., "Product", "Order", "Customer")
- `{feature}` - Lowercase version of feature name for URLs (e.g., "product", "order")

### Creating a New API

1. Copy the template files to your new project directory
2. Replace all occurrences of `{ServiceName}` with your service name
3. Replace all occurrences of `{Feature}` and `{feature}` with your domain feature name
4. Update the namespaces and folder structure as needed
5. Install the required NuGet packages (see project files)
6. Configure your specific business logic

### Key Patterns

#### ErrorOr Pattern for Error Handling

```csharp
public async Task<ErrorOr<Product>> GetProductAsync(Guid id)
{
    var product = await _repository.GetByIdAsync(id);
    if (product == null)
        return Error.NotFound("Product.NotFound", $"Product {id} not found");

    return product;
}
```

#### Controller Pattern with ErrorOr

```csharp
[ApiController]
[Route("api/v1/[controller]")]
public class ProductsController : ControllerBase
{
    private readonly IProductService _service;

    public ProductsController(IProductService service)
    {
        _service = service;
    }

    [HttpGet("{id}")]
    [ProducesResponseType(typeof(ProductResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById([FromRoute] Guid id)
    {
        var result = await _service.GetProductAsync(id);
        return result.Match(
            product => Ok(product),
            errors => Problem(errors)
        );
    }
}
```

#### Structured Logging with Serilog

```csharp
_logger.LogInformation("Processing order {OrderId} for customer {CustomerId}",
    orderId, customerId);
```

### Testing

The template includes comprehensive testing patterns:

- **Unit Tests**: Test services and controllers in isolation
- **Integration Tests**: Test full API endpoints with test server
- **Test Fixtures**: Shared test infrastructure and utilities

Run tests with:
```bash
dotnet test
dotnet test --filter Category=Unit
dotnet test --filter Category=Integration
```

### Docker Support

Build and run with Docker:
```bash
docker build -t {servicename}:latest .
docker run -p 8080:8080 {servicename}:latest
```

### Health Checks

The service includes health check endpoints:

- `/api/v1/health` - Detailed health check with all dependencies
- `/api/v1/health/live` - Simple liveness check for Kubernetes
- `/api/v1/health/ready` - Readiness check for traffic routing

### Configuration

The template uses standard .NET configuration with support for:

- Environment variables
- appsettings.json
- User secrets (development)
- Command line arguments

Key configuration sections:

- `Serilog` - Logging configuration
- `OpenTelemetry` - Observability endpoints
- `Authentication` - JWT/OAuth settings
- `RateLimiting` - Rate limiting policies
- `Cors` - CORS configuration
- `HealthChecks` - Health check settings

## Best Practices

1. **Always use ErrorOr pattern** for operations that can fail
2. **Keep controllers thin** - delegate to services
3. **Use action filters** for cross-cutting concerns
4. **Use structured logging** with correlation IDs
5. **Implement comprehensive health checks**
6. **Add OpenTelemetry instrumentation**
7. **Validate all inputs** using FluentValidation
8. **Handle errors functionally** - avoid throwing exceptions in business logic
9. **Write tests first** - TDD approach
10. **Document APIs** with OpenAPI/Swagger and XML comments

## Common Extensions

### Adding Database Support

1. Add Entity Framework Core packages
2. Create DbContext
3. Replace in-memory repository with EF repository
4. Add database health check
5. Configure connection string
6. Add migrations

### Adding Authentication

1. Uncomment authentication code in Program.cs
2. Configure JWT settings
3. Add authorization policies
4. Update controllers with [Authorize] attributes
5. Configure claims-based authorization

### Adding API Versioning

1. Add API versioning packages
2. Configure version policies in Program.cs
3. Add version attributes to controllers
4. Update route templates
5. Configure Swagger for versioning

### Adding Message Queue

1. Add MassTransit or similar package
2. Create message contracts
3. Add consumers/publishers
4. Configure message broker
5. Add health checks

## Resources

- [ASP.NET Core Documentation](https://docs.microsoft.com/aspnet/core)
- [ErrorOr Library](https://github.com/amantinband/error-or)
- [OpenTelemetry .NET](https://opentelemetry.io/docs/instrumentation/net/)
- [Serilog Documentation](https://serilog.net)
- [FluentValidation](https://fluentvalidation.net)
