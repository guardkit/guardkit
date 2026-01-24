"""OAuth 2.1 Authentication Module.

OAUTH BEST PRACTICES (2025-2026):
- OAuth 2.1 with PKCE is MANDATORY for all MCP clients (March 2025 spec)
- MCP servers are classified as OAuth Resource Servers (June 2025 spec)
- Short-lived access tokens: 15-60 minutes recommended
- Refresh token rotation with automatic revocation
- Integration with identity providers (Auth0, Keycloak, Okta)

This module is for HTTP/SSE transport ONLY.
STDIO transport inherits host process credentials - no OAuth needed.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, UTC
import httpx

logger = logging.getLogger(__name__)


class TokenValidationError(Exception):
    """Raised when token validation fails."""
    pass


@dataclass
class OAuth2Config:
    """OAuth 2.1 Configuration.

    Attributes:
        issuer: OAuth issuer URL (e.g., https://auth.example.com)
        audience: Expected audience claim for this MCP server
        jwks_uri: URI for JSON Web Key Set (auto-derived from issuer if not set)
        token_endpoint: Token endpoint for refresh (auto-derived if not set)
        client_id: OAuth client ID for this MCP server
        scopes: Required scopes for MCP operations
    """
    issuer: str
    audience: str
    jwks_uri: Optional[str] = None
    token_endpoint: Optional[str] = None
    client_id: Optional[str] = None
    scopes: tuple = ("mcp:read", "mcp:tools")

    def __post_init__(self):
        if not self.jwks_uri:
            self.jwks_uri = f"{self.issuer.rstrip('/')}/.well-known/jwks.json"
        if not self.token_endpoint:
            self.token_endpoint = f"{self.issuer.rstrip('/')}/oauth/token"

    @classmethod
    def from_env(cls) -> "OAuth2Config":
        """Create configuration from environment variables.

        Environment Variables:
            OAUTH_ISSUER: OAuth issuer URL (required)
            OAUTH_AUDIENCE: Expected audience (required)
            OAUTH_CLIENT_ID: Client ID (optional)
            OAUTH_SCOPES: Comma-separated scopes (optional)
        """
        issuer = os.getenv("OAUTH_ISSUER")
        audience = os.getenv("OAUTH_AUDIENCE")

        if not issuer or not audience:
            raise ValueError(
                "OAUTH_ISSUER and OAUTH_AUDIENCE environment variables required"
            )

        scopes_str = os.getenv("OAUTH_SCOPES", "mcp:read,mcp:tools")
        scopes = tuple(s.strip() for s in scopes_str.split(","))

        return cls(
            issuer=issuer,
            audience=audience,
            client_id=os.getenv("OAUTH_CLIENT_ID"),
            scopes=scopes
        )


async def validate_token(
    token: str,
    config: OAuth2Config,
    required_scopes: Optional[list[str]] = None
) -> dict:
    """Validate OAuth 2.1 access token.

    Performs the following validations:
    1. Token signature verification using JWKS
    2. Expiration check (tokens should be 15-60 minutes)
    3. Issuer validation
    4. Audience validation
    5. Scope validation

    Args:
        token: The Bearer token to validate
        config: OAuth2 configuration
        required_scopes: Specific scopes required for this operation

    Returns:
        Decoded token claims if valid

    Raises:
        TokenValidationError: If token is invalid or expired
    """
    try:
        # In production, use a proper JWT library like python-jose or PyJWT
        # This is a template showing the validation flow

        # 1. Fetch JWKS for signature verification
        async with httpx.AsyncClient() as client:
            jwks_response = await client.get(config.jwks_uri)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

        # 2. Decode and verify token (placeholder - use real JWT library)
        # Example with python-jose:
        # from jose import jwt
        # claims = jwt.decode(
        #     token,
        #     jwks,
        #     algorithms=["RS256"],
        #     audience=config.audience,
        #     issuer=config.issuer
        # )

        # Placeholder claims for template
        claims = _decode_token_placeholder(token)

        # 3. Validate expiration
        exp = claims.get("exp", 0)
        if datetime.fromtimestamp(exp, tz=UTC) < datetime.now(UTC):
            raise TokenValidationError("Token expired")

        # 4. Validate issuer
        if claims.get("iss") != config.issuer:
            raise TokenValidationError(f"Invalid issuer: {claims.get('iss')}")

        # 5. Validate audience
        aud = claims.get("aud", [])
        if isinstance(aud, str):
            aud = [aud]
        if config.audience not in aud:
            raise TokenValidationError(f"Invalid audience: {aud}")

        # 6. Validate scopes
        token_scopes = set(claims.get("scope", "").split())
        required = set(required_scopes or config.scopes)
        if not required.issubset(token_scopes):
            missing = required - token_scopes
            raise TokenValidationError(f"Missing required scopes: {missing}")

        logger.debug(f"Token validated for subject: {claims.get('sub')}")
        return claims

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise TokenValidationError(f"JWKS fetch failed: {e}")

    except TokenValidationError:
        raise

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise TokenValidationError(f"Token validation failed: {e}")


def _decode_token_placeholder(token: str) -> dict:
    """Placeholder token decoder for template.

    In production, replace with proper JWT decoding using:
    - python-jose: `from jose import jwt`
    - PyJWT: `import jwt`

    Example:
        from jose import jwt, JWTError
        try:
            claims = jwt.decode(token, jwks, algorithms=["RS256"])
        except JWTError as e:
            raise TokenValidationError(str(e))
    """
    # This is a placeholder - always raises in template mode
    raise TokenValidationError(
        "Token validation not implemented. "
        "Install python-jose or PyJWT and implement proper JWT decoding."
    )


# FastAPI/Starlette middleware integration example
def create_oauth_middleware(config: OAuth2Config):
    """Create OAuth middleware for FastAPI/Starlette.

    Example usage with FastAPI:
        from fastapi import FastAPI, Depends
        from fastapi.security import HTTPBearer

        app = FastAPI()
        security = HTTPBearer()
        oauth_config = OAuth2Config.from_env()

        @app.get("/mcp/tools")
        async def list_tools(credentials = Depends(security)):
            claims = await validate_token(credentials.credentials, oauth_config)
            return {"tools": [...]}
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    class OAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Skip auth for health checks
            if request.url.path in ["/health", "/ready"]:
                return await call_next(request)

            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    {"error": "Missing or invalid Authorization header"},
                    status_code=401
                )

            token = auth_header[7:]  # Remove "Bearer " prefix
            try:
                claims = await validate_token(token, config)
                request.state.user_claims = claims
            except TokenValidationError as e:
                return JSONResponse(
                    {"error": str(e)},
                    status_code=401
                )

            return await call_next(request)

    return OAuthMiddleware
