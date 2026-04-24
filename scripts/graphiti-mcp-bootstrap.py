#!/usr/bin/env python3
"""Bootstrap wrapper for graphiti-mcp-server that disables MCP DNS rebinding protection.

Why this exists
---------------
graphiti-mcp-server calls ``FastMCP('Graphiti Agent Memory', ...)`` with no
``host`` argument. FastMCP's default host is ``"127.0.0.1"``, which triggers an
auto-enable of DNS rebinding protection with an allow-list of only
``["127.0.0.1:*", "localhost:*", "[::1]:*"]``. graphiti then mutates
``mcp.settings.host = "0.0.0.0"`` to bind the listener to all interfaces — but
the ``transport_security`` object is already frozen with the localhost-only
allow-list. Result: uvicorn accepts the TCP connection on every interface, but
the MCP middleware returns ``421 Invalid Host header`` for any ``Host`` value
other than localhost (e.g. a Tailscale hostname like ``promaxgb10-41b1:8004``).

The GuardKit deployment is intentionally multi-host: Claude Code on a Mac and
Claude Code on the GB10 both hit ``http://promaxgb10-41b1:8004/mcp``. Neither
of them sends ``Host: localhost:8004``, so every non-loopback client sees 421.

Fix
---
Patch ``mcp.server.transport_security.TransportSecurityMiddleware`` to no-op
the ``_validate_host`` / ``_validate_origin`` checks before graphiti's main()
imports FastMCP. The MCP server is reachable only over Tailscale (not the
public internet) and the rebinding-protection threat model — a browser on a
user's machine being tricked into making same-origin requests to a
localhost-bound MCP — does not apply here.

Mounted at /app/mcp/bootstrap.py by scripts/graphiti-mcp.sh and invoked via
``uv run --no-sync bootstrap.py`` in place of the image's default main.py.
"""

import sys
from pathlib import Path

from mcp.server import transport_security as _ts

_ts.TransportSecurityMiddleware._validate_host = lambda self, host: True
_ts.TransportSecurityMiddleware._validate_origin = lambda self, origin: True

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from graphiti_mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
