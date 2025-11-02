#!/bin/bash

# Debug script to check template installation

echo "=== Template Debug ==="
echo "User: $(whoami)"
echo "Home: $HOME"
echo ""

# Check for Taskwright installation
if [ -d "$HOME/.agentecflow" ]; then
    AGENTECFLOW_HOME="$HOME/.agentecflow"
    echo "✓ Found: $AGENTECFLOW_HOME"
else
    echo "✗ No .agentecflow directory found"
    exit 1
fi

echo ""
echo "=== Templates Directory ==="
if [ -d "$AGENTECFLOW_HOME/templates" ]; then
    echo "✓ Templates directory exists"
    echo ""
    echo "Available templates:"
    ls -la "$AGENTECFLOW_HOME/templates/"
else
    echo "✗ Templates directory NOT found"
fi

echo ""
echo "=== Checking dotnet-microservice ==="
if [ -d "$AGENTECFLOW_HOME/templates/dotnet-microservice" ]; then
    echo "✓ dotnet-microservice template found"
    ls -la "$AGENTECFLOW_HOME/templates/dotnet-microservice/"
else
    echo "✗ dotnet-microservice template NOT found"
fi
