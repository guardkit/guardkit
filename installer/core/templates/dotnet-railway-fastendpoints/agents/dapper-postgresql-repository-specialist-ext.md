# Dapper Postgresql Repository Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **dapper-postgresql-repository-specialist** agent.

**Core documentation**: See [dapper-postgresql-repository-specialist.md](./dapper-postgresql-repository-specialist.md)

---

## Related Templates

- `templates/infrastructure/repositories/CustomerRepository.cs.template` — Primary reference. Shows sealed repository class with static constructor setting `DefaultTypeMap.MatchNamesWithUnderscores = true`, `NpgsqlConnection` factory method, and every public method returning `Result<CustomerError, T>` with exceptions caught and converted via `CustomerError.RepositoryUnavailable(ex)`.

- `templates/domain/errors/CustomerError.cs.template` — Defines the error record (inheriting `BaseError`) with an enum-discriminated `Kind` property, `StatusCode` and `ErrorCode` switch expressions, and the `RepositoryUnavailable(Exception ex)` static factory that repositories call in every catch block.

- `templates/domain/domain/Customer.cs.template` — The aggregate root that Dapper hydrates. Public setters are required for Dapper materialisation; domain mutations go through static factory methods (`Create`, `Deactivate`) so the entity stays consistent outside the repository.

- `templates/cross-cutting core/functional/Result.cs.template` — Error-first `Result<TError, TSuccess>` wrapper over `CSharpFunctionalExtensions`. Exposes `Success`, `Failure`, `Map`, `Bind`, `BindAsync`, and `Match` so callers chain results without unwrapping.

- `templates/infrastructure/infrastructure/ServiceCollectionExtensions.cs.template` — Shows how `CustomerRepository` is registered as `ICustomerRepository` inside `AddCustomers`, resolving the connection string from `IConfiguration` at scoped-service creation time so test overrides applied after `Build()` take effect.

## Code Examples

### Example 1: Repository method structure — try/catch wrapping every public method

Every public repository method follows the same structural contract: open a connection, execute a Dapper query, return `Result<TError, T>.Success(...)`, and catch all exceptions by returning the domain-specific `RepositoryUnavailable` factory. Nothing escapes the boundary as a raw exception.

```csharp
// DO — correct pattern from CustomerRepository.cs.template
public async Task<Result<CustomerError, Customer>> GetByIdAsync(Guid id, CancellationToken ct)
{
    try
    {
        await using var conn = CreateConnection();
        await conn.OpenAsync(ct);
        var customer = await conn.QuerySingleOrDefaultAsync<Customer>(
            "SELECT id, name, email, status, created_at FROM customers WHERE id = @Id",
            new { Id = id });
        return customer is null
            ? CustomerError.NotFound(id)
            : Result<CustomerError, Customer>.Success(customer);
    }
    catch (Exception ex)
    {
        return CustomerError.RepositoryUnavailable(ex);
    }
}

// DON'T — letting exceptions propagate breaks the railway contract
public async Task<Customer?> GetByIdAsync(Guid id)
{
    await using var conn = new NpgsqlConnection(_connectionString);
    await conn.OpenAsync();
    // NpgsqlException leaks to callers — they must handle it or crash
    return await conn.QuerySingleOrDefaultAsync<Customer>(
        "SELECT * FROM customers WHERE id = @Id", new { Id = id });
}
```

### Example 2: Static constructor for snake_case column mapping

The static constructor runs once per type, ensuring Dapper maps `created_at` → `CreatedAt`, `customer_id` → `CustomerId`, etc. without per-query column aliases.

```csharp
// DO — from CustomerRepository.cs.template, static constructor
public sealed class CustomerRepository : ICustomerRepository
{
    private readonly string _connectionString;

    static CustomerRepository()
    {
        // Map snake_case column names (e.g. created_at) to PascalCase properties (CreatedAt)
        Dapper.DefaultTypeMap.MatchNamesWithUnderscores = true;
    }

    public CustomerRepository(string connectionString)
        => _connectionString = connectionString;

    private NpgsqlConnection CreateConnection() => new(_connectionString);
}

// DON'T — setting the flag inside each method wastes allocations
//           and is not thread-safe during startup
public async Task<Result<CustomerError, Customer>> GetByIdAsync(Guid id, CancellationToken ct)
{
    DefaultTypeMap.MatchNamesWithUnderscores = true; // repeated on every call
    ...
}
```

### Example 3: RETURNING clause for insert/update round-trips

Use `RETURNING` in PostgreSQL DML so the repository hands back the persisted row (with any DB-generated defaults) rather than constructing a synthetic response.

```csharp
// DO — from CustomerRepository.cs.template InsertAsync
var inserted = await conn.QuerySingleAsync<Customer>(
    """
    INSERT INTO customers (id, name, email, status, created_at)
    VALUES (@Id, @Name, @Email, @Status, @CreatedAt)
    RETURNING id, name, email, status, created_at
    """,
    new { customer.Id, customer.Name, customer.Email,
          Status = (int)customer.Status, customer.CreatedAt });
return Result<CustomerError, Customer>.Success(inserted);

// DON'T — re-fetching after insert adds a round-trip and risks
//           reading stale data if replication lag is present
await conn.ExecuteAsync(insertSql, param);
return await GetByIdAsync(customer.Id, ct); // extra query, not atomic
```

### Example 4: Domain error record with RepositoryUnavailable factory

The error record derives from `BaseError`, uses an enum discriminant (`CustomerErrorKind`) for `StatusCode` and `ErrorCode` mapping, and stores the original exception for observability without exposing it to callers.

```csharp
// From CustomerError.cs.template
public record CustomerError(string Message, CustomerErrorKind Kind) : BaseError(Message)
{
    public override int StatusCode => Kind switch
    {
        CustomerErrorKind.NotFound           => StatusCodes.Status404NotFound,
        CustomerErrorKind.EmailAlreadyExists => StatusCodes.Status409Conflict,
        CustomerErrorKind.AlreadyInactive    => StatusCodes.Status409Conflict,
        _                                    => StatusCodes.Status500InternalServerError
    };

    public override string? ErrorCode => Kind switch
    {
        CustomerErrorKind.NotFound           => "CUSTOMER_NOT_FOUND",
        CustomerErrorKind.EmailAlreadyExists => "CUSTOMER_EMAIL_EXISTS",
        CustomerErrorKind.AlreadyInactive    => "CUSTOMER_ALREADY_INACTIVE",
        _                                    => null
    };

    // Called in every repository catch block
    public static CustomerError RepositoryUnavailable(Exception ex)
        => new("Customer data store unavailable", CustomerErrorKind.RepositoryUnavailable)
           { InnerException = ex };
}
```

### Example 5: DI registration resolving connection string at scope creation time

Registering the repository as a scoped service and resolving `IConfiguration` at scope creation time (not at `AddCustomers` call time) ensures WebApplicationFactory test overrides applied after `Build()` are respected.

```csharp
// From ServiceCollectionExtensions.cs.template
services.AddScoped<ICustomerRepository>(sp =>
{
    var cs = sp.GetService<IConfiguration>()?.GetConnectionString("DefaultConnection")
             ?? connectionString;
    return new CustomerRepository(cs);
});
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
