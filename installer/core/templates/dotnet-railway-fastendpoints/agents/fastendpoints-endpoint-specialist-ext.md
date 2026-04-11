# Fastendpoints Endpoint Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **fastendpoints-endpoint-specialist** agent.

**Core documentation**: See [fastendpoints-endpoint-specialist.md](./fastendpoints-endpoint-specialist.md)

---

## Related Templates

### Primary Templates

**`src/Exemplar.Customers/Endpoints/CreateCustomer.cs`**
The canonical POST endpoint. Shows the full pattern: `Endpoint<TRequest, TResponse>` inheritance, constructor injection, `Configure()` with `Post(...)` and `Roles(...)`, `HandleAsync` that sets the `Location` header and sends `201 Created` on success, and delegates to `this.HandleErrorAsync(result.Error, ct)` on failure.

**`src/Exemplar.Addresses/Endpoints/GetAddressesByCustomerId.cs`**
The canonical GET-with-route-param endpoint. Demonstrates a locally defined request record holding a `Guid Id` route binding, reliance on the global authentication policy (no `AllowAnonymous()`), and the minimal `IsSuccess` / `HandleErrorAsync` response fork.

**`src/Exemplar.Core/Endpoints/EndpointResultExtensions.cs`**
The shared error-dispatch utility. `HandleErrorAsync` serialises any `BaseError` subtype to RFC 7807 ProblemDetails. `HandleResultAsync` is the higher-order overload that takes both `onSuccess` and delegates to `HandleErrorAsync` on failure.

**`src/Exemplar.Core/Functional/Result.cs`** and **`src/Exemplar.Core/Functional/ResultExtensions.cs`**
The core railway types. `Result<TError, TSuccess>` wraps `CSharpFunctionalExtensions` and exposes `Map`, `Bind`, `BindAsync`, and `Match`. `ResultExtensions` adds async continuation operators `MapAsync`, `BindAsync`, `MapErrorAsync`, and `TapAsync`.

**`src/Exemplar.Customers/Domain/Errors/CustomerError.cs`**
Reference implementation of the enum-discriminated error pattern. Extend when adding a new BC: `YourDomainError(string Message, YourErrorKind Kind) : BaseError(Message)` with `StatusCode` and `ErrorCode` switch expressions.

**`src/Exemplar.Customers/Application/Validators/CreateCustomerValidator.cs`**
Reference `Validator<TRequest>`. FastEndpoints auto-discovers validators; place them in `Application/Validators/` with field-level `WithMessage` strings.

## Code Examples

### Example 1: POST endpoint with 201 Created and Location header

```csharp
using Exemplar.Core.Endpoints;
using Exemplar.Orders.Application;
using FastEndpoints;
using Microsoft.AspNetCore.Http;

namespace Exemplar.Orders.Endpoints;

public sealed class CreateOrder : Endpoint<CreateOrderRequest, OrderDto>
{
    private readonly IOrderService _service;

    public CreateOrder(IOrderService service) => _service = service;

    public override void Configure()
    {
        Post("api/v1/orders");
        Roles("admin");
    }

    public override async Task HandleAsync(CreateOrderRequest req, CancellationToken ct)
    {
        var result = await _service.CreateOrderAsync(req, ct);
        if (result.IsSuccess)
        {
            HttpContext.Response.Headers.Location = $"/api/v1/orders/{result.Value.Id}";
            await Send.ResponseAsync(result.Value, StatusCodes.Status201Created, ct);
        }
        else
        {
            await this.HandleErrorAsync(result.Error, ct);
        }
    }
}
```

### Example 2: GET endpoint with route parameter

```csharp
public sealed class GetOrdersByCustomerIdRequest
{
    public Guid Id { get; set; }
}

public sealed class GetOrdersByCustomerId
    : Endpoint<GetOrdersByCustomerIdRequest, IReadOnlyList<OrderDto>>
{
    private readonly IOrderService _service;

    public GetOrdersByCustomerId(IOrderService service) => _service = service;

    public override void Configure()
    {
        Get("api/v1/customers/{id}/orders");
        // Global RequireAuthenticatedUser policy applies.
    }

    public override async Task HandleAsync(GetOrdersByCustomerIdRequest req, CancellationToken ct)
    {
        var result = await _service.GetByCustomerIdAsync(req.Id, ct);
        if (result.IsSuccess)
            await Send.OkAsync(result.Value, ct);
        else
            await this.HandleErrorAsync(result.Error, ct);
    }
}
```

### Example 3: Railway pipeline in an application service

```csharp
public Task<Result<OrderError, OrderDto>> CreateOrderAsync(
    CreateOrderRequest request, CancellationToken ct)
    => CheckItemsAvailableAsync(request.ItemIds, ct)
       .BindAsync(items => _repo.InsertAsync(
           Order.Create(request.CustomerId, items), ct))
       .MapAsync(ToDto)
       .TapAsync(dto => PublishOrderCreatedAsync(dto, ct));
```

### Example 4: Enum-discriminated domain error

```csharp
public record OrderError(string Message, OrderErrorKind Kind) : BaseError(Message)
{
    public override int StatusCode => Kind switch
    {
        OrderErrorKind.NotFound        => StatusCodes.Status404NotFound,
        OrderErrorKind.ItemUnavailable => StatusCodes.Status409Conflict,
        _                              => StatusCodes.Status500InternalServerError
    };

    public override string? ErrorCode => Kind switch
    {
        OrderErrorKind.NotFound        => "ORDER_NOT_FOUND",
        OrderErrorKind.ItemUnavailable => "ORDER_ITEM_UNAVAILABLE",
        _                              => null
    };

    public static OrderError NotFound(Guid id)
        => new($"Order {id} not found", OrderErrorKind.NotFound);
}
```

### Example 5: Cross-BC error translation with MapErrorAsync

```csharp
private Task<Result<AddressError, CustomerSummaryDto>> ResolveCustomerAsync(
    Guid customerId, CancellationToken ct)
    => _customerLookup.FindByIdAsync(customerId, ct)
       .MapErrorAsync(notFound =>
           new AddressError(notFound.Message, AddressErrorKind.CustomerNotFound));
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
