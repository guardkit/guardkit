# Xunit Testcontainers Testing Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **xunit-testcontainers-testing-specialist** agent.

**Core documentation**: See [xunit-testcontainers-testing-specialist.md](./xunit-testcontainers-testing-specialist.md)

---

## Related Templates

- `templates/tests (unit)/unit/CustomerServiceTests.cs.template` — Canonical unit test fixture demonstrating NSubstitute mock setup, `Result<CustomerError, T>` stubbing with `.Returns(...)`, and FluentAssertions assertions on `.IsSuccess`, `.IsFailure`, `.Error.Kind`, and `.Value` properties. Use this as the reference for all new service-layer unit tests.
- `templates/tests (e2e)/factories/ExemplarApiFactory.cs.template` — `WebApplicationFactory<Program>` subclass that wires Testcontainers PostgreSQL and Keycloak containers into the full ASP.NET pipeline via `ConfigureAppConfiguration`. Overrides `ConnectionStrings:DefaultConnection`, `Authentication:Authority`, and OTEL/Serilog settings so the app under test runs against ephemeral containers.
- `templates/cross-cutting core/functional/Result.cs.template` — The `Result<TError, TSuccess>` struct that all service and repository methods return. Understanding `.IsSuccess`, `.IsFailure`, `.Value`, `.Error`, `.Map`, `.Bind`, and `.BindAsync` is essential for writing correct assertions and mock stubs.
- `templates/domain/errors/CustomerError.cs.template` — Enum-discriminated error record showing `CustomerErrorKind` variants (`NotFound`, `EmailAlreadyExists`, `AlreadyInactive`, `RepositoryUnavailable`) and their HTTP status code mappings. Reference when asserting on `.Error.Kind` in unit tests.
- `templates/application/services/CustomerService.cs.template` — Production service whose `.Bind`/`.BindAsync` pipeline is the subject under test. Shows how optional NATS dependencies (`INatsEventPublisher?`, `INatsAgentClient?`) should be omitted from unit test constructors.

## Code Examples

### Unit Test: Service Method with NSubstitute and Result<T> Assertions

This pattern is derived directly from `templates/tests (unit)/unit/CustomerServiceTests.cs.template`. The repository is substituted, stubs return `Result<CustomerError, T>` values, and FluentAssertions inspects the outcome.

```csharp
// CustomerServiceTests.cs
public class CustomerServiceTests
{
    private readonly ICustomerRepository _repo = Substitute.For<ICustomerRepository>();
    private readonly CustomerService _sut;

    public CustomerServiceTests() => _sut = new CustomerService(_repo);

    [Fact]
    public async Task CreateCustomerAsync_WhenEmailFree_InsertsAndReturnsDto()
    {
        var request = new CreateCustomerRequest("Alice Smith", "alice@example.com");

        // Stub: email does not exist
        _repo.EmailExistsAsync(request.Email, default)
             .Returns(Result<CustomerError, bool>.Success(false));

        // Stub: insert captures the entity and returns it
        _repo.InsertAsync(Arg.Any<Customer>(), default)
             .Returns(ci => Result<CustomerError, Customer>.Success(ci.Arg<Customer>()));

        var result = await _sut.CreateCustomerAsync(request, default);

        result.IsSuccess.Should().BeTrue();
        result.Value.Name.Should().Be("Alice Smith");
        result.Value.Email.Should().Be("alice@example.com");
        result.Value.Status.Should().Be(CustomerStatus.Active.ToString());
    }

    [Fact]
    public async Task CreateCustomerAsync_WhenEmailTaken_ReturnsEmailAlreadyExistsError()
    {
        var request = new CreateCustomerRequest("Bob", "taken@example.com");
        _repo.EmailExistsAsync(request.Email, default)
             .Returns(Result<CustomerError, bool>.Success(true));

        var result = await _sut.CreateCustomerAsync(request, default);

        result.IsFailure.Should().BeTrue();
        result.Error.Kind.Should().Be(CustomerErrorKind.EmailAlreadyExists);

        // Verify the railway pipeline short-circuited — InsertAsync never called
        await _repo.DidNotReceive().InsertAsync(Arg.Any<Customer>(), default);
    }

    [Fact]
    public async Task CreateCustomerAsync_WhenRepoUnavailable_ReturnsRepositoryUnavailableError()
    {
        var request = new CreateCustomerRequest("Charlie", "charlie@example.com");
        // Implicit conversion from CustomerError to Result<CustomerError, bool>
        _repo.EmailExistsAsync(request.Email, default)
             .Returns(CustomerError.RepositoryUnavailable(new Exception("db down")));

        var result = await _sut.CreateCustomerAsync(request, default);

        result.IsFailure.Should().BeTrue();
        result.Error.Kind.Should().Be(CustomerErrorKind.RepositoryUnavailable);
        await _repo.DidNotReceive().InsertAsync(Arg.Any<Customer>(), default);
    }
}
```

**DO**: Stub repository methods with `Result<TError, TSuccess>.Success(value)` or the implicit conversion from a typed error (`CustomerError.NotFound(id)`).
**DO NOT**: Throw exceptions from stubs to simulate domain failures — use the railway-oriented error path instead.

---

### E2E Test: ExemplarApiFactory with Testcontainers PostgreSQL and Keycloak

This pattern is derived from `templates/tests (e2e)/factories/ExemplarApiFactory.cs.template`. The factory receives Testcontainers connection strings and overrides them via `AddInMemoryCollection` so the full ASP.NET pipeline (including DbUp migrations and JWT validation) runs against ephemeral containers.

```csharp
// ExemplarApiFactory.cs  (generated from template)
public sealed class ExemplarApiFactory : WebApplicationFactory<Program>
{
    private readonly string _connectionString;
    private readonly string _keycloakAuthority;

    public ExemplarApiFactory(string connectionString, string keycloakAuthority)
    {
        _connectionString = connectionString;
        _keycloakAuthority = keycloakAuthority;
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        // Use Development so RequireHttpsMetadata = false (Keycloak container is HTTP)
        builder.UseEnvironment("Development");

        builder.ConfigureAppConfiguration((_, config) =>
        {
            config.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["ConnectionStrings:DefaultConnection"] = _connectionString,
                ["Authentication:Authority"]            = _keycloakAuthority,
                ["Authentication:Audience"]             = "exemplar-api",
                ["Authentication:ClientId"]             = "exemplar-api",
                ["OTEL_EXPORTER_OTLP_ENDPOINT"]         = string.Empty,
                ["Serilog:MinimumLevel:Default"]         = "Warning",
            });
        });
    }
}

// E2E test consuming the factory
public class CreateCustomerEndpointTests : IClassFixture<ExemplarApiFactory>
{
    private readonly HttpClient _client;

    public CreateCustomerEndpointTests(ExemplarApiFactory factory)
        => _client = factory.CreateClient();

    [Fact]
    public async Task PostCustomer_WithValidPayload_Returns201WithLocation()
    {
        var payload = new { name = "Test User", email = $"test-{Guid.NewGuid():N}@example.com" };
        var response = await _client.PostAsJsonAsync("/api/v1/customers", payload);

        response.StatusCode.Should().Be(HttpStatusCode.Created);
        response.Headers.Location.Should().NotBeNull();
        response.Headers.Location!.ToString().Should().StartWith("/api/v1/customers/");
    }
}
```

**DO**: Pass Testcontainers-derived connection strings and authority URLs into the factory constructor. Let `ConfigureWebHost` inject them via `AddInMemoryCollection` so the app's normal DI wiring is preserved.
**DO NOT**: Replace service registrations inside `ConfigureTestServices` unless the test specifically needs to substitute a real dependency — overriding configuration is always preferred for infrastructure concerns.

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
