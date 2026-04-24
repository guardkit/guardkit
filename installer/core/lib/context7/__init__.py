"""
MCP (Model Context Protocol) Integration Package

This package provides utilities for interacting with MCP servers, including:
- Context7 client for library documentation
- Progressive disclosure for token optimization
- Response monitoring and token tracking
- Design patterns integration

Exports:
    - DetailLevel: Enum for controlling documentation detail level
    - Context7Client: Client for Context7 MCP server
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
