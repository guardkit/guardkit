# Railway Result Pipeline Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **railway-result-pipeline-specialist** agent.

**Core documentation**: See [railway-result-pipeline-specialist.md](./railway-result-pipeline-specialist.md)

---

## Related Templates

Core pipeline primitives this agent owns:

- `templates/cross-cutting core/functional/Result.cs.template` — `Result<TError, TSuccess>` discriminated type with `Map`, `Bind`, `Match`.
- `templates/cross-cutting core/functional/ResultExtensions.cs.template` — `MapAsync`, `BindAsync`, `MapErrorAsync`, `TapAsync` extension methods on `Task<Result<,>>`.
- `templates/cross-cutting core/errors/BaseError.cs.template` — `BaseError` abstract record, `StatusCode`/`ErrorCode`/`InnerException` contract.
- `templates/cross-cutting core/endpoints/EndpointResultExtensions.cs.template` — FastEndpoints adapter that terminates a Result pipeline into an HTTP response.

Domain error hierarchy (enum-discriminated, Pattern A):

- `templates/domain/errors/CustomerError.cs.template` — `CustomerError(Message, CustomerErrorKind)` record with static factories (`NotFound`, `EmailAlreadyExists`, `AlreadyInactive`, `RepositoryUnavailable`).
- `templates/domain/domain/Customer.cs.template` — aggregate used in pipeline return types.

Pipelines that consume the extensions (canonical examples):

- `templates/application/services/CustomerService.cs.template` — `CreateCustomerAsync`, `DeactivateCustomerAsync`, `FindByIdAsync` — the reference call sites.
- `templates/application/services/AddressService.cs.template` — cross-BC pipeline that uses `MapErrorAsync` to adapt `NotFoundError` → `CustomerNotFoundError`.
- `templates/application/validators/CreateCustomerValidator.cs.template` — FluentValidation integration (validation happens *before* the Result pipeline).
- `templates/infrastructure/repositories/CustomerRepository.cs.template` — how repositories return `Result<CustomerError, T>` for the pipeline to bind on.
- `templates/endpoints/endpoints/CreateCustomer.cs.template` — endpoint that terminates the pipeline via `EndpointResultExtensions`.
- `templates/endpoints/endpoints/GetAddressesByCustomerId.cs.template` — cross-BC endpoint using `MapErrorAsync`.
- `templates/tests (unit)/unit/CustomerServiceTests.cs.template` — how to test Result pipelines without mocking mid-chain checks.

## Code Examples

### Example 1: `ResultExtensions` — the four canonical async combinators

From `templates/cross-cutting core/functional/ResultExtensions.cs.template`. These are the **only** combinators callers should chain on a `Task<Result<,>>`:

```csharp
public static async Task<Result<TError, TNew>> BindAsync<TError, TSuccess, TNew>(
    this Task<Result<TError, TSuccess>> resultTask,
    Func<TSuccess, Task<Result<TError, TNew>>> binder)
    where TError : BaseError
{
    var result = await resultTask;
    return await result.BindAsync(binder);
}

public static async Task<Result<TNewError, TSuccess>> MapErrorAsync<TError, TSuccess, TNewError>(
    this Task<Result<TError, TSuccess>> resultTask,
    Func<TError, TNewError> errorMapper)
    where TError : BaseError
    where TNewError : BaseError
{
    var result = await resultTask;
    return result.IsSuccess
        ? Result<TNewError, TSuccess>.Success(result.Value)
        : Result<TNewError, TSuccess>.Failure(errorMapper(result.Error));
}

public static async Task<Result<TError, TSuccess>> TapAsync<TError, TSuccess>(
    this Task<Result<TError, TSuccess>> resultTask,
    Func<TSuccess, Task> action)
    where TError : BaseError
{
    var result = await resultTask;
    if (result.IsSuccess)
    {
        try { await action(result.Value); }
        catch (Exception) { /* best-effort side effect */ }
    }
    return result;
}
```

**Key rules enforced by the signatures:**
- `TError : BaseError` constraint on every combinator — no stray error types.
- `TapAsync` swallows exceptions so best-effort side effects (domain events) cannot fail the pipeline.
- `MapErrorAsync` is the *only* sanctioned way to adapt error types across bounded contexts.

### Example 2: `CustomerService.CreateCustomerAsync` — the canonical pipeline

From `templates/application/services/CustomerService.cs.template`. This is the reference shape for every write pipeline:

```csharp
public Task<Result<CustomerError, CustomerDto>> CreateCustomerAsync(
    CreateCustomerRequest request, CancellationToken ct)
    => CheckEmailNotTakenAsync(request.Email, ct)
       .BindAsync(email => _repo.InsertAsync(Customer.Create(request.Name, email), ct))
       .MapAsync(ToDto)
       .TapAsync(dto => PublishCustomerCreatedAsync(dto, ct));
```

**What to notice:**
- Expression-bodied method; the *method is the pipeline*.
- No `if (result.IsSuccess)` anywhere — short-circuiting is the combinators' job.
- `BindAsync` chains steps that may fail; `MapAsync` transforms the happy value; `TapAsync` publishes a domain event as a best-effort side effect.
- The private helper returns `Task<Result<CustomerError, string>>` so it composes seamlessly.

### Example 3: Enum-discriminated error with static factories (Pattern A)

From `templates/domain/errors/CustomerError.cs.template`. This is the shape every domain error record must follow:

```csharp
public record CustomerError(string Message, CustomerErrorKind Kind) : BaseError(Message)
{
    public override int StatusCode => Kind switch
    {
        CustomerErrorKind.NotFound            => StatusCodes.Status404NotFound,
        CustomerErrorKind.EmailAlreadyExists  => StatusCodes.Status409Conflict,
        CustomerErrorKind.AlreadyInactive     => StatusCodes.Status409Conflict,
        _                                     => StatusCodes.Status500InternalServerError
    };

    public static CustomerError NotFound(Guid id)
        => new($"Customer {id} not found", CustomerErrorKind.NotFound);

    public static CustomerError EmailAlreadyExists(string email)
        => new($"Email {email} is already registered", CustomerErrorKind.EmailAlreadyExists);
}
```

**Rules:**
- Single record per bounded context; the enum, not subclassing, discriminates variants.
- `StatusCode` and `ErrorCode` are switch-expressions on `Kind` — no per-variant records.
- All construction goes through static factories; callers never `new CustomerError(...)` directly.

### Example 4: `MapErrorAsync` for cross-BC error adaptation

From `templates/application/services/CustomerService.cs.template` (`FindByIdAsync`) — when a pipeline crosses a bounded context, adapt the error type rather than leaking it:

```csharp
public async Task<Result<NotFoundError, CustomerSummaryDto>> FindByIdAsync(Guid id, CancellationToken ct)
{
    var result = await _repo.GetByIdAsync(id, ct);
    return result.Match<Result<NotFoundError, CustomerSummaryDto>>(
        onSuccess: c => new CustomerSummaryDto(c.Id, c.Name, c.Email),
        onFailure: _ => new NotFoundError($"Customer {id} not found"));
}
```

For async pipelines, prefer `.MapErrorAsync(e => NotFoundError.From(e))` at the BC boundary. Never let a `CustomerError` escape into a caller that lives in another bounded context — adapt it first.

### Example 5: Private helpers must compose, not branch

From `CustomerService.cs.template` — helpers used inside a pipeline return `Task<Result<,>>`:

```csharp
private Task<Result<CustomerError, string>> CheckEmailNotTakenAsync(string email, CancellationToken ct)
    => _repo.EmailExistsAsync(email, ct)
       .BindAsync(exists => Task.FromResult(exists
           ? (Result<CustomerError, string>)CustomerError.EmailAlreadyExists(email)
           : Result<CustomerError, string>.Success(email)));

private static Task<Result<CustomerError, Customer>> ValidateActiveStatus(Customer customer)
    => Task.FromResult(customer.Status == CustomerStatus.Inactive
        ? (Result<CustomerError, Customer>)CustomerError.AlreadyInactive(customer.Id)
        : Result<CustomerError, Customer>.Success(customer));
```

These helpers are *first-class pipeline steps* — they are passed directly to `BindAsync` without being awaited by the caller.

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
