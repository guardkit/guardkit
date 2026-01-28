---
paths: "**/.mcp.json", "**/pyproject.toml", "**/.env", "**/config.py", "**/config/*.py"
---

# MCP Configuration Patterns

Configuration patterns for FastMCP servers, including Claude Desktop integration, environment variables, and project setup.

## Absolute Path Requirements

MCP configuration MUST use absolute paths. Relative paths cause server startup failures.

### Claude Desktop Configuration (.mcp.json)

```json
{
  "mcpServers": {
    "my-server": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/absolute/path/to/project",
      "env": {
        "PYTHONPATH": "/absolute/path/to/project",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### WRONG - Relative Paths

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "src"],
      "cwd": "./project"
    }
  }
}
```

## PYTHONPATH Configuration

Always set PYTHONPATH to ensure module imports work correctly.

### In .mcp.json

```json
{
  "mcpServers": {
    "my-server": {
      "command": "/Users/user/project/.venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/Users/user/project",
      "env": {
        "PYTHONPATH": "/Users/user/project"
      }
    }
  }
}
```

### In pyproject.toml

```toml
[project]
name = "my-mcp-server"
version = "1.0.0"
description = "MCP server for XYZ functionality"
requires-python = ">=3.11"

dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Environment Variables

### .env File Structure

```bash
# .env - Environment configuration

# Logging
LOG_LEVEL=INFO

# API Keys (never commit to git!)
API_KEY=your-api-key-here
EXTERNAL_SERVICE_KEY=service-key-here

# Database (if applicable)
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Feature flags
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600

# OAuth (for HTTP transport)
OAUTH_ISSUER=https://auth.example.com
OAUTH_AUDIENCE=my-mcp-server
```

### Loading Environment Variables

```python
# src/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """MCP server configuration."""

    # Logging
    log_level: str = "INFO"

    # API Keys
    api_key: Optional[str] = None

    # Feature flags
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            api_key=os.getenv("API_KEY"),
            enable_caching=os.getenv("ENABLE_CACHING", "true").lower() == "true",
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
        )

# Singleton instance
config = Config.from_env()
```

### Using python-dotenv

```python
# src/__main__.py
import sys
import logging
from pathlib import Path

# Load .env file before other imports
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from mcp.server.fastmcp import FastMCP
from .config import config

logging.basicConfig(
    stream=sys.stderr,
    level=getattr(logging, config.log_level),
)
```

## MCP Server Configuration Patterns

### Transport Configuration

```python
# src/__main__.py
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="my-server",
    version="1.0.0",
)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "http":
        # HTTP transport requires additional setup
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=int(os.getenv("MCP_PORT", "8000"))
        )
```

### Server Metadata

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="my-mcp-server",
    version="1.0.0",
    # Additional metadata for discovery
)

# Add server info for clients
@mcp.resource("info://server")
async def get_server_info() -> dict:
    """Server information resource."""
    return {
        "name": "my-mcp-server",
        "version": "1.0.0",
        "capabilities": ["tools", "resources"],
        "transport": "stdio"
    }
```

## Configuration Validation

### Pydantic Settings

```python
# src/config.py
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Validated MCP server settings."""

    # Required
    api_key: str

    # Optional with defaults
    log_level: str = "INFO"
    cache_ttl_seconds: int = 3600

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        if v < 0:
            raise ValueError("cache_ttl_seconds must be non-negative")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Multi-Environment Configuration

### Development vs Production

```python
# src/config.py
import os
from dataclasses import dataclass

@dataclass
class BaseConfig:
    log_level: str = "INFO"

@dataclass
class DevelopmentConfig(BaseConfig):
    log_level: str = "DEBUG"
    enable_debug_tools: bool = True

@dataclass
class ProductionConfig(BaseConfig):
    log_level: str = "WARNING"
    enable_debug_tools: bool = False

def get_config():
    """Get configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development")

    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
    }

    return configs.get(env, DevelopmentConfig)()

config = get_config()
```

### Environment-Specific .mcp.json

```json
{
  "mcpServers": {
    "my-server-dev": {
      "command": "/Users/user/project/.venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/Users/user/project",
      "env": {
        "PYTHONPATH": "/Users/user/project",
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "DEBUG"
      }
    },
    "my-server-prod": {
      "command": "/opt/mcp/my-server/.venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/opt/mcp/my-server",
      "env": {
        "PYTHONPATH": "/opt/mcp/my-server",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

## Secrets Management

### Never Commit Secrets

```gitignore
# .gitignore
.env
.env.*
secrets/
*.key
*.pem
```

### Use Environment Variables for Secrets

```python
# CORRECT - secrets from environment
api_key = os.environ["API_KEY"]  # Raises if not set

# WRONG - hardcoded secrets
api_key = "sk-1234567890"  # Never do this!
```

### Secret Validation on Startup

```python
# src/__main__.py
import os
import sys

def validate_secrets():
    """Validate required secrets are set."""
    required = ["API_KEY"]
    missing = [k for k in required if not os.getenv(k)]

    if missing:
        print(f"Error: Missing required environment variables: {missing}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    validate_secrets()
    mcp.run(transport="stdio")
```

## References

- [MCP Configuration Spec](https://modelcontextprotocol.io/docs/configure)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
