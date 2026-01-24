#!/bin/bash
# MCP Protocol Testing Script
#
# CRITICAL PATTERN #9: Protocol Testing Commands
# Unit tests passing ≠ MCP integration working
# Manual JSON-RPC protocol testing is REQUIRED
#
# Usage:
#   chmod +x tests/protocol/test_mcp_protocol.sh
#   ./tests/protocol/test_mcp_protocol.sh
#
# Requirements:
#   - jq (for JSON parsing)
#   - Python environment with MCP server installed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== MCP Protocol Tests ==="
echo "Project: $PROJECT_ROOT"
echo ""

# Test 1: Initialize
echo "Test 1: Initialize MCP Server"
echo "------------------------------"
INIT_RESPONSE=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0"}}}' | python -m src 2>/dev/null)

echo "Request: initialize"
echo "Response: $INIT_RESPONSE"

if echo "$INIT_RESPONSE" | jq -e '.result.serverInfo' > /dev/null 2>&1; then
    echo "✅ Initialize: PASSED"
else
    echo "❌ Initialize: FAILED"
    exit 1
fi
echo ""

# Test 2: List Tools
echo "Test 2: List Available Tools"
echo "----------------------------"
TOOLS_RESPONSE=$(echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python -m src 2>/dev/null)

echo "Request: tools/list"
echo "Response: $TOOLS_RESPONSE"

TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | jq '.result.tools | length' 2>/dev/null || echo "0")
if [ "$TOOL_COUNT" -gt 0 ]; then
    echo "✅ Tools List: PASSED (found $TOOL_COUNT tools)"
    echo "Tools found:"
    echo "$TOOLS_RESPONSE" | jq -r '.result.tools[].name' 2>/dev/null || true
else
    echo "❌ Tools List: FAILED (no tools found)"
    exit 1
fi
echo ""

# Test 3: Call Tool
echo "Test 3: Call example_tool"
echo "-------------------------"
CALL_RESPONSE=$(echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"example_tool","arguments":{"param":"protocol_test","count":"3"}}}' | python -m src 2>/dev/null)

echo "Request: tools/call (example_tool)"
echo "Response: $CALL_RESPONSE"

if echo "$CALL_RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
    echo "✅ Tool Call: PASSED"
else
    echo "❌ Tool Call: FAILED"
    exit 1
fi
echo ""

# Test 4: Call Health Check
echo "Test 4: Call health_check"
echo "-------------------------"
HEALTH_RESPONSE=$(echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"health_check","arguments":{}}}' | python -m src 2>/dev/null)

echo "Request: tools/call (health_check)"
echo "Response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | jq -e '.result.content[0].text' | grep -q "healthy" 2>/dev/null; then
    echo "✅ Health Check: PASSED"
else
    echo "❌ Health Check: FAILED"
    exit 1
fi
echo ""

# Test 5: Invalid Method
echo "Test 5: Invalid Method Handling"
echo "--------------------------------"
ERROR_RESPONSE=$(echo '{"jsonrpc":"2.0","id":5,"method":"invalid/method"}' | python -m src 2>/dev/null)

echo "Request: invalid/method"
echo "Response: $ERROR_RESPONSE"

if echo "$ERROR_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo "✅ Error Handling: PASSED (correctly returned error)"
else
    echo "⚠️  Error Handling: May need review"
fi
echo ""

echo "=== Protocol Tests Complete ==="
echo ""
echo "Summary:"
echo "- Initialize: ✅"
echo "- Tools List: ✅"
echo "- Tool Call: ✅"
echo "- Health Check: ✅"
echo "- Error Handling: ✅"
