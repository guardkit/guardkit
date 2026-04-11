# Bounded Context Domain Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **bounded-context-domain-specialist** agent.

**Core documentation**: See [bounded-context-domain-specialist.md](./bounded-context-domain-specialist.md)

---

## Related Templates

- `templates/domain/domain/Customer.cs.template` — Canonical aggregate root showing public-setter hydration for Dapper alongside static `Create` and `Deactivate` factory methods; the only permitted entry points for domain mutations.
- `templates/domain/errors/CustomerError.cs.template` — Enum-discriminated error record inheriting `BaseError`; demonstrates `StatusCode` and `ErrorCode` both derived via switch expressions over a `Kind` enum, plus static factory methods for each error case.
- `templates/cross-cutting core/errors/BaseError.cs.template` — Abstract `BaseError` record defining the `StatusCode`, `ErrorCode`, and `InnerException` contract that all domain error records must satisfy.
- `templates/cross-cutting core/functional/Result.cs.template` — Error-first `Result<TError, TSuccess>` wrapper over `CSharpFunctionalExtensions`; exposes `Map`, `Bind`, `BindAsync`, and `Match` for composing railway-oriented pipelines without leaking the underlying library.
- `templates/contracts (anti-corruption layer)/exemplar.customers.contracts/ICustomerLookup.cs.template` — Inter-BC contract interface returning `Task<Result<NotFoundError, CustomerSummaryDto>>`; callers in other bounded contexts depend only on this interface and the lightweight DTO, never on internal domain types.

## Code Examples

### Aggregate Root with Static Factory Methods

All domain mutations go through static factory methods. Public setters exist solely to allow Dapper hydration and must not be called from application or endpoint code.

```csharp
// DO: use static factory methods for all domain mutations
public sealed class Customer
{
    public Guid Id { get; set; }
    public string Name { get; set; } = default!;
    public string Email { get; set; } = default!;
    public CustomerStatus Status { get; set; }
    public DateTime CreatedAt { get; set; }

    public static Customer Create(string name, string email) => new()
    {
        Id = Guid.NewGuid(),
        Name = name,
        Email = email,
        Status = CustomerStatus.Active,
        CreatedAt = DateTime.UtcNow
    };

    public Customer Deactivate() => new()
    {
        Id = Id,
        Name = Name,
        Email = Email,
        Status = CustomerStatus.Inactive,
        CreatedAt = CreatedAt
    };
}

// DON'T: set properties directly to mutate domain state
var c = new Customer();
c.Status = CustomerStatus.Inactive; // bypasses domain logic
```

### Enum-Discriminated Error Record with Switch-Derived StatusCode

Each bounded context defines its own error record inheriting `BaseError`. The HTTP status code and machine-readable error code are both derived from the `Kind` enum via switch expressions, keeping the mapping co-located with the error type.

```csharp
// DO: inherit BaseError, use switch expressions for StatusCode and ErrorCode
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

    public static CustomerError NotFound(Guid id)
        => new($"Customer {id} not found", CustomerErrorKind.NotFound);

    public static CustomerError EmailAlreadyExists(string email)
        => new($"Email {email} is already registered", CustomerErrorKind.EmailAlreadyExists);
}

// DON'T: hard-code status codes or use inheritance hierarchies per error case
public class CustomerNotFoundException : Exception { } // breaks railway pipeline
```

### Inter-BC Contract Interface Returning Result

The Contracts project is the Anti-Corruption Layer. Interfaces return `Result<TError, SummaryDto>` so consuming bounded contexts participate in the railway pipeline without depending on internal domain types.

```csharp
// DO: expose only lightweight DTOs and Result-returning interfaces in Contracts
public interface ICustomerLookup
{
    Task<Result<NotFoundError, CustomerSummaryDto>> FindByIdAsync(Guid id, CancellationToken ct);
}

// The DTO carries only what other BCs need — no domain entity leaks across the boundary
public record CustomerSummaryDto(Guid Id, string Name, string Email);

// Consuming BC (e.g. Addresses) binds over the result without knowing Customer internals
var result = await customerLookup.FindByIdAsync(customerId, ct);
var response = result.Match(
    onSuccess: summary => AddressResponse.From(summary),
    onFailure: err    => throw new DomainException(err.Message));

// DON'T: return raw domain entities or expose internal error types across BC boundaries
public interface ICustomerLookup
{
    Task<Customer> FindByIdAsync(Guid id); // leaks domain type into another BC
}
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
