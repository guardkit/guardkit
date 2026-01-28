---
paths: src/**/*.py, **/.mcp.json, **/config/*.py
---

# MCP Security Patterns

Security patterns for FastMCP servers, including OAuth 2.1 requirements (mandatory for HTTP transport as of March 2025), transport security, and secrets management.

## OAuth 2.1 Requirements (March 2025 Mandatory)

For HTTP-based MCP transports, OAuth 2.1 is **mandatory** per the June 2025 specification update. MCP servers are officially classified as OAuth Resource Servers.

### Required Security Features

1. **PKCE (Proof Key for Code Exchange)** - Required for ALL clients
2. **Short-lived Access Tokens** - 15-60 minutes maximum
3. **Refresh Token Rotation** - New refresh token issued on each use
4. **Scope-based Access Control** - Granular permissions per tool
5. **Resource Indicators (RFC 8707)** - Prevent token mis-redemption across servers

### OAuth Configuration Example

```json
{
  "security": {
    "auth_required": true,
    "oauth": {
      "pkce_required": true,
      "token_ttl_seconds": 3600,
      "refresh_rotation": true,
      "issuer": "https://auth.example.com",
      "audience": "my-mcp-server"
    },
    "rate_limit": 1000
  }
}
```

### Python OAuth Middleware

```python
# src/auth/oauth.py
from functools import wraps
from typing import Callable
import jwt
from datetime import datetime, timezone

class OAuthValidator:
    """OAuth 2.1 token validator for MCP servers."""

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: str,
        max_token_age_seconds: int = 3600
    ):
        self.issuer = issuer
        self.audience = audience
        self.jwks_url = jwks_url
        self.max_token_age = max_token_age_seconds

    async def validate_token(self, token: str) -> dict:
        """Validate OAuth 2.1 access token."""
        try:
            # Decode and validate JWT
            payload = jwt.decode(
                token,
                options={"verify_signature": True},
                issuer=self.issuer,
                audience=self.audience,
                algorithms=["RS256"]
            )

            # Check token age (short-lived requirement)
            iat = payload.get("iat", 0)
            age = datetime.now(timezone.utc).timestamp() - iat
            if age > self.max_token_age:
                raise ValueError("Token too old")

            return payload

        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")

def require_auth(scopes: list[str] = None):
    """Decorator to require OAuth authentication for tools."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Token validation happens at transport layer
            # This checks scopes for fine-grained access control
            context = kwargs.get("_context", {})
            token_scopes = context.get("scopes", [])

            if scopes:
                missing = set(scopes) - set(token_scopes)
                if missing:
                    raise AuthorizationError(f"Missing scopes: {missing}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Resource Indicators (RFC 8707)

```python
# src/auth/resource_indicators.py
"""
Resource Indicators prevent token mis-redemption attacks.
Tokens are bound to specific MCP servers.
"""

from dataclasses import dataclass

@dataclass
class ResourceIndicator:
    """RFC 8707 Resource Indicator."""
    uri: str  # Server URI
    scopes: list[str]  # Allowed scopes for this resource

def validate_resource_indicator(token: dict, expected_resource: str) -> bool:
    """Validate token is intended for this resource server."""
    token_resources = token.get("aud", [])
    if isinstance(token_resources, str):
        token_resources = [token_resources]

    return expected_resource in token_resources
```

### Scope-Based Access Control

```python
# Define tool scopes
TOOL_SCOPES = {
    "read_data": ["data:read"],
    "write_data": ["data:write"],
    "admin_operation": ["admin:full"],
}

@mcp.tool()
@require_auth(scopes=["data:read"])
async def read_data(id: str) -> dict:
    """Read data - requires data:read scope."""
    return await fetch_data(id)

@mcp.tool()
@require_auth(scopes=["data:write"])
async def write_data(id: str, data: str) -> dict:
    """Write data - requires data:write scope."""
    return await save_data(id, data)

@mcp.tool()
@require_auth(scopes=["admin:full"])
async def admin_operation(action: str) -> dict:
    """Admin operation - requires admin:full scope."""
    return await execute_admin(action)
```

## Transport Security

### Transport Deprecation Notice

**SSE Transport Deprecated** (June 2025)

The Server-Sent Events (SSE) transport is **deprecated** and replaced by **Streamable HTTP**.

| Transport | Status | Use Case |
|-----------|--------|----------|
| STDIO | Recommended | Local development, Claude Desktop |
| Streamable HTTP | Recommended | Production networked deployment |
| SSE | **Deprecated** | Do NOT use in new projects |

### Transport Selection Pattern

```python
# src/__main__.py
import os
import sys
import logging

logger = logging.getLogger(__name__)

def get_transport_config():
    """Get transport configuration with security checks."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "sse":
        logger.warning(
            "SSE transport is DEPRECATED as of June 2025. "
            "Use STDIO for local development or Streamable HTTP for production."
        )

    if transport in ("http", "streamable_http"):
        # HTTP transport requires OAuth
        if not os.getenv("OAUTH_ISSUER"):
            logger.error("HTTP transport requires OAuth configuration")
            sys.exit(1)

    return transport
```

## Secrets Management

### NEVER Echo Secrets

**CRITICAL**: Never echo secrets in tool results or elicitation messages.

```python
# WRONG - exposes secrets
@mcp.tool()
async def debug_config() -> dict:
    return {
        "api_key": os.getenv("API_KEY"),  # NEVER DO THIS!
        "database_url": os.getenv("DATABASE_URL")  # NEVER!
    }

# CORRECT - mask sensitive values
@mcp.tool()
async def debug_config() -> dict:
    return {
        "api_key": "***" if os.getenv("API_KEY") else None,
        "database_url": mask_connection_string(os.getenv("DATABASE_URL"))
    }

def mask_connection_string(url: str) -> str:
    """Mask credentials in connection strings."""
    if not url:
        return None
    # postgresql://user:pass@host:port/db -> postgresql://***@host:port/db
    import re
    return re.sub(r'://[^:]+:[^@]+@', '://***:***@', url)
```

### Secure Configuration Loading

```python
# src/config.py
import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SecureConfig:
    """Configuration with secure secret handling."""

    # Secrets - loaded from environment only
    _api_key: Optional[str] = field(default=None, repr=False)
    _database_url: Optional[str] = field(default=None, repr=False)

    # Non-sensitive config
    log_level: str = "INFO"

    @property
    def api_key(self) -> str:
        """Get API key - raises if not set."""
        if not self._api_key:
            raise ValueError("API_KEY not configured")
        return self._api_key

    @classmethod
    def from_env(cls) -> "SecureConfig":
        return cls(
            _api_key=os.getenv("API_KEY"),
            _database_url=os.getenv("DATABASE_URL"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )

    def __repr__(self):
        """Safe repr that doesn't expose secrets."""
        return f"SecureConfig(log_level={self.log_level!r})"
```

### Input Validation

```python
from pydantic import BaseModel, field_validator
import re

class SecureInput(BaseModel):
    """Validated input model with security checks."""

    user_input: str

    @field_validator("user_input")
    @classmethod
    def validate_no_injection(cls, v: str) -> str:
        """Prevent common injection patterns."""
        # Check for SQL injection patterns
        sql_patterns = [
            r";\s*DROP",
            r";\s*DELETE",
            r"UNION\s+SELECT",
            r"--\s*$"
        ]
        for pattern in sql_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid input: potential injection detected")

        return v

@mcp.tool()
async def process_input(data: str) -> dict:
    """Tool with input validation."""
    validated = SecureInput(user_input=data)
    return await process_safely(validated.user_input)
```

## Rate Limiting

```python
# src/security/rate_limit.py
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps

class RateLimiter:
    """Simple rate limiter for MCP tools."""

    def __init__(self, requests_per_minute: int = 60):
        self.limit = requests_per_minute
        self.requests = defaultdict(list)

    def check(self, client_id: str) -> bool:
        """Check if request is allowed."""
        now = datetime.now(timezone.utc)
        minute_ago = now.timestamp() - 60

        # Clean old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if t > minute_ago
        ]

        if len(self.requests[client_id]) >= self.limit:
            return False

        self.requests[client_id].append(now.timestamp())
        return True

rate_limiter = RateLimiter(requests_per_minute=100)

def rate_limited(func):
    """Decorator to apply rate limiting."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        context = kwargs.get("_context", {})
        client_id = context.get("client_id", "anonymous")

        if not rate_limiter.check(client_id):
            return {
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests",
                    "retry_after": 60
                }
            }

        return await func(*args, **kwargs)
    return wrapper
```

## Security Checklist

When implementing MCP servers:

- [ ] Use OAuth 2.1 for HTTP transport
- [ ] Enable PKCE for all clients
- [ ] Set token TTL to 15-60 minutes
- [ ] Implement refresh token rotation
- [ ] Use Resource Indicators (RFC 8707)
- [ ] Define scopes for each tool
- [ ] Never echo secrets in responses
- [ ] Validate and sanitize all inputs
- [ ] Implement rate limiting
- [ ] Log security events to stderr
- [ ] Use STDIO or Streamable HTTP (not SSE)
- [ ] Run as non-root user in containers

## References

- [MCP Specification June 2025 - Security](https://modelcontextprotocol.io/specification/2025-11-25)
- [OAuth 2.1 for MCP](https://auth0.com/blog/mcp-specs-update-all-about-auth/)
- [RFC 8707 Resource Indicators](https://datatracker.ietf.org/doc/html/rfc8707)
- [OWASP Security Guidelines](https://owasp.org/www-project-web-security-testing-guide/)
