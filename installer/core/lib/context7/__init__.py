"""
Context7 Documentation Client Package

This package provides GuardKit's client for Upstash's Context7 MCP server
(library documentation retrieval), plus the general-purpose MCP request/response
monitoring utilities used across GuardKit's MCP integrations.

The package was previously named ``installer.core.lib.mcp``. It was renamed to
``installer.core.lib.context7`` under TASK-FIX-MCPS.3 to eliminate a namespace
collision with Anthropic's ``mcp`` PyPI package (the Model Context Protocol
SDK, a transitive dependency of ``claude-agent-sdk``). See
``.claude/rules/namespace-hygiene.md``.

Exports:
    - DetailLevel: Enum for controlling documentation detail level
    - Context7Client: Client for Context7 MCP server (Upstash)
    - MCPMonitor: Monitor for tracking MCP request/response metrics
    - MCPRequest: Dataclass representing an MCP request
    - MCPResponse: Dataclass representing an MCP response
    - count_tokens: Utility function for estimating token count
"""

from .detail_level import DetailLevel
from .monitor import MCPMonitor, MCPRequest, MCPResponse
from .utils import count_tokens
from .context7_client import Context7Client

__all__ = [
    "DetailLevel",
    "Context7Client",
    "MCPMonitor",
    "MCPRequest",
    "MCPResponse",
    "count_tokens",
]
