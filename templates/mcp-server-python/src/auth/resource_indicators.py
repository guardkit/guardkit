"""RFC 8707 Resource Indicators Module.

RFC 8707 Resource Indicators are REQUIRED for MCP server token validation
as of June 2025. This ensures tokens are only valid for the intended
MCP server resource.

Key Concepts:
- Resource Indicator: URI identifying the MCP server (e.g., https://mcp.example.com)
- Token must include `aud` claim matching the Resource Indicator
- Prevents token replay attacks across different MCP servers
"""

import os
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ResourceIndicatorError(Exception):
    """Raised when resource indicator validation fails."""
    pass


def get_resource_indicator() -> str:
    """Get the Resource Indicator URI for this MCP server.

    The Resource Indicator should be:
    - A valid URI identifying this specific MCP server
    - Used as the `resource` parameter in OAuth authorization requests
    - Matched against the `aud` claim in access tokens

    Environment Variable:
        MCP_RESOURCE_INDICATOR: The URI for this MCP server

    Returns:
        Resource Indicator URI

    Raises:
        ResourceIndicatorError: If not configured
    """
    indicator = os.getenv("MCP_RESOURCE_INDICATOR")
    if not indicator:
        raise ResourceIndicatorError(
            "MCP_RESOURCE_INDICATOR environment variable not set. "
            "This is required per RFC 8707 for token validation."
        )

    # Validate it's a proper URI
    parsed = urlparse(indicator)
    if not parsed.scheme or not parsed.netloc:
        raise ResourceIndicatorError(
            f"Invalid Resource Indicator URI: {indicator}. "
            "Must be a valid absolute URI (e.g., https://mcp.example.com)"
        )

    return indicator


def validate_resource_indicator(
    token_audience: list[str] | str,
    expected_resource: Optional[str] = None
) -> bool:
    """Validate that token audience matches expected Resource Indicator.

    Per RFC 8707, the access token's `aud` claim must include the
    Resource Indicator that was used in the authorization request.

    Args:
        token_audience: The `aud` claim from the access token
        expected_resource: Expected Resource Indicator (defaults to env var)

    Returns:
        True if validation passes

    Raises:
        ResourceIndicatorError: If validation fails
    """
    if expected_resource is None:
        expected_resource = get_resource_indicator()

    # Normalize audience to list
    if isinstance(token_audience, str):
        audiences = [token_audience]
    else:
        audiences = list(token_audience)

    # Check if expected resource is in audience
    if expected_resource not in audiences:
        logger.warning(
            f"Resource Indicator mismatch. Expected: {expected_resource}, "
            f"Got: {audiences}"
        )
        raise ResourceIndicatorError(
            f"Token not valid for this resource. "
            f"Expected audience to include: {expected_resource}"
        )

    logger.debug(f"Resource Indicator validated: {expected_resource}")
    return True


def build_authorization_url(
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    state: str,
    code_challenge: str,
    code_challenge_method: str = "S256"
) -> str:
    """Build OAuth 2.1 authorization URL with Resource Indicator.

    Includes the `resource` parameter per RFC 8707 to request
    tokens scoped to this specific MCP server.

    Args:
        authorization_endpoint: OAuth authorization endpoint
        client_id: OAuth client ID
        redirect_uri: Callback URI after authorization
        scopes: Required OAuth scopes
        state: CSRF protection state parameter
        code_challenge: PKCE code challenge
        code_challenge_method: PKCE method (default: S256)

    Returns:
        Complete authorization URL with all parameters
    """
    from urllib.parse import urlencode

    resource_indicator = get_resource_indicator()

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        # RFC 8707: Resource Indicator
        "resource": resource_indicator
    }

    return f"{authorization_endpoint}?{urlencode(params)}"


def build_token_request(
    token_endpoint: str,
    client_id: str,
    code: str,
    redirect_uri: str,
    code_verifier: str
) -> dict:
    """Build OAuth 2.1 token request with Resource Indicator.

    Args:
        token_endpoint: OAuth token endpoint
        client_id: OAuth client ID
        code: Authorization code from callback
        redirect_uri: Same redirect URI used in authorization
        code_verifier: PKCE code verifier

    Returns:
        Dictionary with token request parameters
    """
    resource_indicator = get_resource_indicator()

    return {
        "url": token_endpoint,
        "data": {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            # RFC 8707: Resource Indicator
            "resource": resource_indicator
        }
    }
