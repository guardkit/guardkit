# Keycloak Auth Observability Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **keycloak-auth-observability-specialist** agent.

**Core documentation**: See [keycloak-auth-observability-specialist.md](./keycloak-auth-observability-specialist.md)

---

## Related Templates

- `templates/host / composition root/authentication/AuthenticationExtensions.cs.template`
  Canonical implementation of `AddKeycloakAuthentication` and `AddAuthorizationPolicies`. Demonstrates `MapInboundClaims = false`, `ProcessKeycloakRoles` parsing both `realm_access.roles` and `resource_access.{client}.roles` into `ClaimTypes.Role`, and the fallback authorization policy that requires authentication on all endpoints unless `AllowAnonymous()` is explicit.

- `templates/host / composition root/exemplar.api/Program.cs.template`
  Composition root that establishes the required startup ordering: observability first (OpenTelemetry + Serilog), then authentication/authorization, then health checks, then `app.RunDbMigrations()` before any middleware is registered. The health check registration pattern with `"ready"` tags for PostgreSQL and Keycloak readiness probes is defined here.

- `templates/tests (e2e)/factories/ExemplarApiFactory.cs.template`
  `WebApplicationFactory<Program>` override used in E2E tests. Shows how to supply a `Development` environment so `RequireHttpsMetadata = false` applies to the Keycloak TestContainer, how to blank `OTEL_EXPORTER_OTLP_ENDPOINT` to suppress OTLP export in CI, and how to inject test-specific `Authentication:Authority` and `Authentication:Audience` values.

## Code Examples

### DO — Configure Keycloak JWT Bearer with MapInboundClaims=false

Extracted from `AuthenticationExtensions.cs.template`:

```csharp
// REQUIRED: preserve Keycloak claim names — do not let ASP.NET Core
// remap "sub", "preferred_username", etc. to its own claim type URIs.
options.MapInboundClaims = false;

options.RequireHttpsMetadata = !environment.IsDevelopment();

options.TokenValidationParameters = new TokenValidationParameters
{
    ValidateAudience = true,
    ValidateIssuer   = true,
    NameClaimType    = "preferred_username",
    RoleClaimType    = ClaimTypes.Role
};

options.Events = new JwtBearerEvents
{
    OnTokenValidated = ProcessKeycloakRoles
};
```

**Why MapInboundClaims = false is mandatory**: Without it, ASP.NET Core remaps `"sub"` to the long-form WS-Federation URI and drops Keycloak-specific names like `preferred_username` and `realm_access`. All downstream `[Authorize(Roles = ...)]` checks and `User.Identity.Name` lookups break silently.

---

### DO — Map both realm_access and resource_access roles

Extracted from the `ProcessKeycloakRoles` method in `AuthenticationExtensions.cs.template`:

```csharp
private static Task ProcessKeycloakRoles(TokenValidatedContext ctx)
{
    if (ctx.Principal is null) return Task.CompletedTask;
    var identity = (ClaimsIdentity?)ctx.Principal.Identity;
    if (identity is null) return Task.CompletedTask;

    var payload = ctx.SecurityToken.UnsafeToString();
    var base64Payload = PadBase64(payload.Split('.')[1])
        .Replace('-', '+').Replace('_', '/');
    using var doc = JsonDocument.Parse(Convert.FromBase64String(base64Payload));
    var root = doc.RootElement;

    // realm_access.roles → ClaimTypes.Role
    if (root.TryGetProperty("realm_access", out var realmAccess) &&
        realmAccess.TryGetProperty("roles", out var realmRoles))
    {
        foreach (var role in realmRoles.EnumerateArray())
        {
            var roleName = role.GetString();
            if (!string.IsNullOrEmpty(roleName))
                identity.AddClaim(new Claim(ClaimTypes.Role, roleName));
        }
    }

    // resource_access.{audience}.roles → ClaimTypes.Role
    var audience = ctx.Options.Audience;
    if (!string.IsNullOrEmpty(audience) &&
        root.TryGetProperty("resource_access", out var resourceAccess) &&
        resourceAccess.TryGetProperty(audience, out var clientAccess) &&
        clientAccess.TryGetProperty("roles", out var clientRoles))
    {
        foreach (var role in clientRoles.EnumerateArray())
        {
            var roleName = role.GetString();
            if (!string.IsNullOrEmpty(roleName))
                identity.AddClaim(new Claim(ClaimTypes.Role, roleName));
        }
    }

    return Task.CompletedTask;
}
```

**Both sources are required.** Realm roles cover global grants; client roles cover fine-grained per-service permissions. Mapping only one source causes silent authorization failures for users whose grant lives in the other.

---

### DO — Follow the Program.cs startup ordering

Extracted from `Program.cs.template`:

```csharp
// 1. Observability first — captures startup events before anything else runs
builder.Services.AddOpenTelemetryServices(builder.Configuration, "Exemplar.API");
builder.Host.UseSerilogStructuredLogging();

// 2. Authentication & authorisation
builder.Services.AddKeycloakAuthentication(builder.Configuration, builder.Environment);
builder.Services.AddAuthorizationPolicies();

// 3. HttpClient factory — required by KeycloakHealthCheck
builder.Services.AddHttpClient();

// 7. Health checks
builder.Services.AddHealthChecks()
    .AddCheck<KeycloakHealthCheck>("keycloak",  tags: new[] { "ready" })
    .AddNpgSql(connectionString, name: "postgresql", tags: new[] { "ready" });

var app = builder.Build();

// 8. DbUp migrations — run before the app accepts traffic
app.RunDbMigrations();

// 9. Middleware pipeline
app.UseAuthentication();
app.UseAuthorization();
app.UseApiConfiguration();
app.MapHealthEndpoints();

app.Run();
```

**Why order matters**: Observability must be first to capture startup failures. `AddHttpClient()` must precede `AddHealthChecks()` because `KeycloakHealthCheck` depends on `IHttpClientFactory`. DbUp runs after `app.Build()` but before `app.Run()` so no traffic reaches a stale schema.

---

### DON'T — Leave MapInboundClaims at its default

```csharp
// WRONG — roles never appear in ClaimTypes.Role with default mapping
.AddJwtBearer(options =>
{
    options.Authority = configuration["Authentication:Authority"];
    options.Audience  = configuration["Authentication:Audience"];
    // MapInboundClaims defaults to true
});
```

`User.IsInRole("admin")` always returns `false` because ASP.NET Core remapped the role claims to URI-form keys.

---

### DO — Override authority and suppress OTLP in E2E tests

Extracted from `ExemplarApiFactory.cs.template`:

```csharp
builder.UseEnvironment("Development"); // RequireHttpsMetadata = false for Keycloak container

config.AddInMemoryCollection(new Dictionary<string, string?>
{
    ["ConnectionStrings:DefaultConnection"] = _connectionString,
    ["Authentication:Authority"] = _keycloakAuthority,
    ["Authentication:Audience"]  = "exemplar-api",
    ["OTEL_EXPORTER_OTLP_ENDPOINT"] = string.Empty, // suppress OTLP in CI
    ["Serilog:MinimumLevel:Default"] = "Warning",
});
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
