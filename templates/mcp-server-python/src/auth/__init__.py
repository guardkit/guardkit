"""OAuth 2.1 Authentication Package.

Implements OAuth 2.1 with PKCE for HTTP/SSE transport MCP servers.
Note: STDIO transport (local MCP) doesn't require OAuth - inherits host credentials.

Key Standards:
- OAuth 2.1 with PKCE (mandatory as of March 2025)
- RFC 8707 Resource Indicators
- Short-lived access tokens (15-60 minutes)
- Refresh token rotation
"""

from src.auth.oauth import (
    validate_token,
    OAuth2Config,
    TokenValidationError
)
from src.auth.resource_indicators import (
    validate_resource_indicator,
    ResourceIndicatorError
)

__all__ = [
    "validate_token",
    "OAuth2Config",
    "TokenValidationError",
    "validate_resource_indicator",
    "ResourceIndicatorError"
]
