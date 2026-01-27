---
paths: **/*.py, **/schemas/**
---

# Pydantic Field Constraint Patterns

## When to Use Strict Constraints

Use `ge=0`, `le=N`, `min_length`, etc. for:

- **User-provided input** (IDs, quantities, prices)
- **Application-level metrics** you control
- **Domain values** with known valid ranges

## When to Avoid Strict Constraints

Avoid strict constraints for:

- **Third-party library metrics** (database pools, cache stats)
- **System resource measurements** (memory, CPU, disk)
- **External API responses** (may have unexpected values)

## Database Pool Metrics Example

```python
# BAD - Can fail with valid SQLAlchemy pool metrics
class HealthResponse(BaseModel):
    pool_size: int = Field(ge=0)
    pool_overflow: int = Field(ge=0)  # Fails! Can be negative

# GOOD - Accepts valid range including overflow indicators
class HealthResponse(BaseModel):
    pool_size: int = Field(description="Current pool size")
    pool_overflow: int = Field(
        description="Overflow count (negative indicates available capacity)"
    )
```

## Constraint Decision Matrix

| Data Source | Strict Constraints? | Rationale |
|-------------|---------------------|-----------|
| User input | Yes | Validate early |
| Database IDs | Yes (ge=1) | IDs are positive |
| Quantities/Prices | Yes (ge=0) | Business rule |
| External APIs | No | Unpredictable |
| Library metrics | No | Implementation details |
| System stats | No | Can be negative/overflow |

## Default Behavior

When unsure, prefer **documentation over constraints**:

```python
# Prefer this
field: int = Field(description="Value from external system, may be negative")

# Over this
field: int = Field(ge=0, description="Must be positive")
```

## Validation Layers

Apply constraints at appropriate layers:

1. **API Input**: Strict validation (user-provided)
2. **Internal Processing**: Type hints only
3. **External Data**: Loose validation, handle errors

```python
# API input - strict
class UserCreate(BaseModel):
    age: int = Field(ge=0, le=150)

# Internal - no constraints
class InternalMetrics(BaseModel):
    pool_overflow: int  # No constraints

# External - handle gracefully
class ExternalAPIResponse(BaseModel):
    value: Optional[int] = None  # May be missing
```

## Common Anti-Patterns

### Over-Constraining Health Checks

```python
# BAD - Assumes all metrics are positive
class HealthCheck(BaseModel):
    db_connections: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    pool_overflow: int = Field(ge=0)  # SQLAlchemy can return negative

# GOOD - Document behavior, don't constrain
class HealthCheck(BaseModel):
    db_connections: int = Field(description="Active database connections")
    cache_hits: int = Field(description="Cache hit count since startup")
    pool_overflow: int = Field(
        description="Pool overflow (-N = N connections available)"
    )
```

### Constraining External API Data

```python
# BAD - External API might return unexpected values
class ExternalServiceStatus(BaseModel):
    latency_ms: int = Field(ge=0)  # What if clock skew causes negative?
    error_count: int = Field(ge=0)  # Safe assumption, but unnecessary

# GOOD - Accept what the API returns
class ExternalServiceStatus(BaseModel):
    latency_ms: int = Field(description="Response latency in milliseconds")
    error_count: int = Field(description="Error count from service")
```

## When Constraints Are Appropriate

### User Input Schemas

```python
class ProductCreate(BaseModel):
    """User-created product - validate strictly."""
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(ge=0, decimal_places=2)
    quantity: int = Field(ge=0, le=10000)
    sku: str = Field(pattern=r"^[A-Z]{2}-\d{6}$")
```

### Database ID References

```python
class OrderCreate(BaseModel):
    """Order referencing existing entities."""
    user_id: int = Field(ge=1, description="User ID must exist")
    product_id: int = Field(ge=1, description="Product ID must exist")
    quantity: int = Field(ge=1, description="Must order at least 1")
```

### Configuration Values

```python
class AppSettings(BaseSettings):
    """Application configuration - constrain to valid ranges."""
    max_connections: int = Field(ge=1, le=1000)
    timeout_seconds: int = Field(ge=1, le=300)
    retry_attempts: int = Field(ge=0, le=10)
```
