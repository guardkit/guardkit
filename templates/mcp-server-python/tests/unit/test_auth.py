"""Unit Tests for OAuth Authentication.

Tests for OAuth 2.1 and RFC 8707 Resource Indicator validation.
"""

import os
import pytest
from unittest.mock import patch, AsyncMock


class TestOAuth2Config:
    """Tests for OAuth2Config."""

    def test_config_auto_derives_urls(self):
        """Test that JWKS and token URLs are auto-derived from issuer."""
        from src.auth.oauth import OAuth2Config

        config = OAuth2Config(
            issuer="https://auth.example.com",
            audience="https://mcp.example.com"
        )

        assert config.jwks_uri == "https://auth.example.com/.well-known/jwks.json"
        assert config.token_endpoint == "https://auth.example.com/oauth/token"

    def test_config_custom_urls(self):
        """Test that custom URLs override auto-derived ones."""
        from src.auth.oauth import OAuth2Config

        config = OAuth2Config(
            issuer="https://auth.example.com",
            audience="https://mcp.example.com",
            jwks_uri="https://custom.example.com/jwks",
            token_endpoint="https://custom.example.com/token"
        )

        assert config.jwks_uri == "https://custom.example.com/jwks"
        assert config.token_endpoint == "https://custom.example.com/token"

    def test_config_from_env(self):
        """Test configuration from environment variables."""
        from src.auth.oauth import OAuth2Config

        with patch.dict(os.environ, {
            "OAUTH_ISSUER": "https://auth.example.com",
            "OAUTH_AUDIENCE": "https://mcp.example.com",
            "OAUTH_SCOPES": "mcp:read,mcp:write"
        }):
            config = OAuth2Config.from_env()

            assert config.issuer == "https://auth.example.com"
            assert config.audience == "https://mcp.example.com"
            assert config.scopes == ("mcp:read", "mcp:write")

    def test_config_from_env_missing_required(self):
        """Test that missing required env vars raise error."""
        from src.auth.oauth import OAuth2Config

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OAUTH_ISSUER"):
                OAuth2Config.from_env()


class TestResourceIndicators:
    """Tests for RFC 8707 Resource Indicators."""

    def test_get_resource_indicator(self):
        """Test getting resource indicator from environment."""
        from src.auth.resource_indicators import get_resource_indicator

        with patch.dict(os.environ, {
            "MCP_RESOURCE_INDICATOR": "https://mcp.example.com"
        }):
            indicator = get_resource_indicator()
            assert indicator == "https://mcp.example.com"

    def test_get_resource_indicator_missing(self):
        """Test error when resource indicator not configured."""
        from src.auth.resource_indicators import (
            get_resource_indicator,
            ResourceIndicatorError
        )

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ResourceIndicatorError, match="not set"):
                get_resource_indicator()

    def test_get_resource_indicator_invalid_uri(self):
        """Test error for invalid resource indicator URI."""
        from src.auth.resource_indicators import (
            get_resource_indicator,
            ResourceIndicatorError
        )

        with patch.dict(os.environ, {
            "MCP_RESOURCE_INDICATOR": "not-a-valid-uri"
        }):
            with pytest.raises(ResourceIndicatorError, match="Invalid"):
                get_resource_indicator()

    def test_validate_resource_indicator_success(self):
        """Test successful resource indicator validation."""
        from src.auth.resource_indicators import validate_resource_indicator

        result = validate_resource_indicator(
            token_audience=["https://mcp.example.com", "https://other.com"],
            expected_resource="https://mcp.example.com"
        )

        assert result is True

    def test_validate_resource_indicator_string_audience(self):
        """Test validation with string audience (not list)."""
        from src.auth.resource_indicators import validate_resource_indicator

        result = validate_resource_indicator(
            token_audience="https://mcp.example.com",
            expected_resource="https://mcp.example.com"
        )

        assert result is True

    def test_validate_resource_indicator_mismatch(self):
        """Test error when resource indicator doesn't match."""
        from src.auth.resource_indicators import (
            validate_resource_indicator,
            ResourceIndicatorError
        )

        with pytest.raises(ResourceIndicatorError, match="not valid"):
            validate_resource_indicator(
                token_audience=["https://other.example.com"],
                expected_resource="https://mcp.example.com"
            )

    def test_build_authorization_url(self):
        """Test building OAuth authorization URL with resource indicator."""
        from src.auth.resource_indicators import build_authorization_url

        with patch.dict(os.environ, {
            "MCP_RESOURCE_INDICATOR": "https://mcp.example.com"
        }):
            url = build_authorization_url(
                authorization_endpoint="https://auth.example.com/authorize",
                client_id="test-client",
                redirect_uri="https://app.example.com/callback",
                scopes=["mcp:read", "mcp:write"],
                state="random-state",
                code_challenge="challenge123"
            )

            assert "response_type=code" in url
            assert "client_id=test-client" in url
            assert "resource=https%3A%2F%2Fmcp.example.com" in url
            assert "code_challenge=challenge123" in url


class TestTokenValidation:
    """Tests for token validation."""

    @pytest.mark.asyncio
    async def test_validate_token_placeholder_raises(self):
        """Test that placeholder validation raises error."""
        from src.auth.oauth import validate_token, OAuth2Config, TokenValidationError

        config = OAuth2Config(
            issuer="https://auth.example.com",
            audience="https://mcp.example.com"
        )

        # The placeholder implementation should raise
        with pytest.raises(TokenValidationError, match="not implemented"):
            await validate_token("fake-token", config)
