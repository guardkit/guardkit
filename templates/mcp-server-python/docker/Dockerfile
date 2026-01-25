# MCP Server Dockerfile
#
# CRITICAL PATTERN #10: Docker Deployment Patterns
# - Non-root user for security
# - Slim image for smaller footprint
# - PYTHONUNBUFFERED=1 for proper logging
# - Claude Code Docker configuration support

FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

# Ensure Python output is sent straight to terminal
# Critical for MCP protocol communication
ENV PYTHONUNBUFFERED=1

# Default environment variables
ENV LOG_LEVEL=INFO

# Health check (for orchestration tools)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run MCP server
CMD ["python", "-m", "src"]
