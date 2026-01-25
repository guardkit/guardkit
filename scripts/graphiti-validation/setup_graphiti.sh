#!/bin/bash
#
# Graphiti MCP Quick Setup Script
# 
# This script sets up and starts Graphiti MCP server with FalkorDB locally.
#
# Prerequisites:
# - Docker and Docker Compose installed
# - OpenAI API key
#
# Usage:
#   ./setup_graphiti.sh              # Interactive (prompts for API key)
#   OPENAI_API_KEY=xxx ./setup_graphiti.sh  # Non-interactive
#

set -e

GRAPHITI_DIR="${GRAPHITI_DIR:-$HOME/graphiti-mcp}"
COMPOSE_URL="https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/docker/docker-compose.yml"

echo "========================================"
echo "Graphiti MCP Setup for GuardKit"
echo "========================================"
echo

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "Error: Docker is not running"
    exit 1
fi

echo "✓ Docker is available"

# Create directory
echo
echo "Setting up in: $GRAPHITI_DIR"
mkdir -p "$GRAPHITI_DIR"
cd "$GRAPHITI_DIR"

# Download docker-compose.yml
echo "Downloading docker-compose.yml..."
curl -fsSL -o docker-compose.yml "$COMPOSE_URL"
echo "✓ Downloaded docker-compose.yml"

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f .env ] && grep -q "OPENAI_API_KEY" .env; then
        echo "✓ Found existing .env with API key"
    else
        echo
        echo "Enter your OpenAI API key (or press Enter to skip):"
        read -r api_key
        
        if [ -z "$api_key" ]; then
            echo "Warning: No API key provided. You'll need to add it to .env"
        else
            OPENAI_API_KEY="$api_key"
        fi
    fi
fi

# Create .env file
if [ ! -f .env ] || [ -n "$OPENAI_API_KEY" ]; then
    cat > .env << EOF
OPENAI_API_KEY=${OPENAI_API_KEY:-your-openai-api-key-here}
FALKORDB_PASSWORD=
GRAPHITI_GROUP_ID=guardkit
GRAPHITI_TELEMETRY_ENABLED=false
EOF
    echo "✓ Created .env file"
fi

# Start containers
echo
echo "Starting Docker containers..."
docker compose up -d

echo
echo "Waiting for services to be ready..."
sleep 5

# Health check
echo "Checking health..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ MCP server is healthy"
else
    echo "⚠ MCP server not responding yet (may need more time)"
fi

echo
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo
echo "Services running:"
echo "  - FalkorDB:      redis://localhost:6379"
echo "  - FalkorDB UI:   http://localhost:3000"
echo "  - MCP Server:    http://localhost:8000/mcp/"
echo "  - Health Check:  http://localhost:8000/health"
echo
echo "Next steps:"
echo "  1. Run validation tests:"
echo "     cd $(dirname "$0")"
echo "     pip install httpx"
echo "     python test_graphiti_connection.py"
echo
echo "  2. View logs:"
echo "     cd $GRAPHITI_DIR && docker compose logs -f"
echo
echo "  3. Stop services:"
echo "     cd $GRAPHITI_DIR && docker compose down"
echo
