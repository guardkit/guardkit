"""Pytest Configuration.

Shared fixtures and configuration for all tests.
"""

import os
import sys
import pytest

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def mock_env_oauth(monkeypatch):
    """Mock OAuth environment variables."""
    monkeypatch.setenv("OAUTH_ISSUER", "https://auth.example.com")
    monkeypatch.setenv("OAUTH_AUDIENCE", "https://mcp.example.com")
    monkeypatch.setenv("OAUTH_CLIENT_ID", "test-client")
    monkeypatch.setenv("MCP_RESOURCE_INDICATOR", "https://mcp.example.com")


@pytest.fixture
def sample_jwt_claims():
    """Sample JWT claims for testing."""
    from datetime import datetime, UTC, timedelta

    return {
        "iss": "https://auth.example.com",
        "sub": "user123",
        "aud": ["https://mcp.example.com"],
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "scope": "mcp:read mcp:tools"
    }
