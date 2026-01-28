---
paths: "**/Dockerfile", "**/docker-compose.yml", "**/docker-compose.yaml"
---

# Docker Patterns for MCP Servers

Container patterns for deploying FastMCP servers securely and reliably.

## Non-Root User Pattern

Always run MCP servers as a non-root user for security.

```dockerfile
FROM python:3.11-alpine

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ ./src/

# Create non-root user (SECURITY REQUIREMENT)
RUN adduser -D -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Run MCP server
CMD ["python", "-m", "src"]
```

## PYTHONUNBUFFERED Requirement

Set `PYTHONUNBUFFERED=1` to ensure logs appear immediately in container logs.

```dockerfile
FROM python:3.11-alpine

# Critical for MCP logging visibility
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src/ ./src/

RUN adduser -D mcpuser
USER mcpuser

CMD ["python", "-m", "src"]
```

## Complete Production Dockerfile

```dockerfile
# Multi-stage build for smaller image
FROM python:3.11-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

COPY pyproject.toml ./
RUN pip wheel --no-cache-dir --wheel-dir=/wheels .

# Production stage
FROM python:3.11-alpine

# Environment configuration
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install runtime dependencies only
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy source
COPY src/ ./src/

# Security: non-root user
RUN adduser -D -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app
USER mcpuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import src; print('healthy')" || exit 1

# Expose no ports - MCP uses stdio or configured transport
# EXPOSE is only needed if using HTTP transport

CMD ["python", "-m", "src"]
```

## Docker Compose for Development

```yaml
# docker-compose.yml
version: "3.9"

services:
  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mcp-server
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=DEBUG
    volumes:
      # Mount source for development hot reload
      - ./src:/app/src:ro
    # For stdio transport, use stdin_open and tty
    stdin_open: true
    tty: true
    # Security settings
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp

  # Optional: Redis for caching/sessions
  redis:
    image: redis:7-alpine
    container_name: mcp-redis
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

## Claude Code Docker Configuration

Configure Claude Code to use Docker-based MCP servers via `.mcp.json`.

### STDIO Transport with Docker

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--security-opt", "no-new-privileges:true",
        "--read-only",
        "my-mcp-server:latest"
      ],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Docker Compose Integration

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "docker",
      "args": [
        "compose",
        "-f", "/absolute/path/to/docker-compose.yml",
        "run",
        "--rm",
        "-T",
        "mcp-server"
      ],
      "cwd": "/absolute/path/to/project"
    }
  }
}
```

## Entry Point Patterns

### Simple Entry Point

```dockerfile
# Basic entry point
CMD ["python", "-m", "src"]
```

### Entry Point with Arguments

```dockerfile
# Entry point allowing transport override
ENTRYPOINT ["python", "-m", "src"]
CMD ["--transport", "stdio"]
```

### Shell Entry Point for Environment Setup

```dockerfile
# entrypoint.sh for complex setup
COPY --chmod=755 entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/bin/sh
# entrypoint.sh

# Set default log level
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# Validate required environment variables
if [ -z "$API_KEY" ]; then
    echo "Warning: API_KEY not set" >&2
fi

# Run MCP server
exec python -m src "$@"
```

## HTTP Transport Configuration

For production HTTP deployment:

```dockerfile
FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir . uvicorn

COPY src/ ./src/

RUN adduser -D mcpuser
USER mcpuser

# HTTP transport exposes port
EXPOSE 8000

# Use uvicorn for HTTP transport
CMD ["uvicorn", "src.http_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml for HTTP transport
version: "3.9"

services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - AUTH_REQUIRED=true
      - OAUTH_ISSUER=https://auth.example.com
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

## Security Best Practices

### Resource Limits

```yaml
# docker-compose.yml
services:
  mcp-server:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.1'
          memory: 64M
```

### Network Isolation

```yaml
services:
  mcp-server:
    networks:
      - mcp-internal
    # No external network access unless needed

networks:
  mcp-internal:
    internal: true
```

### Secrets Management

```yaml
services:
  mcp-server:
    secrets:
      - api_key
    environment:
      - API_KEY_FILE=/run/secrets/api_key

secrets:
  api_key:
    file: ./secrets/api_key.txt
```

## References

- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Python Docker Images](https://hub.docker.com/_/python)
- [Alpine Linux](https://www.alpinelinux.org/)
