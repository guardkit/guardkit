#!/usr/bin/env bash
# graphiti-endpoint-toggle.sh — DEPRECATED
#
# This script toggled the Graphiti LLM endpoint via shell env vars when the
# MCP server ran as a stdio subprocess per-session. Since the HTTP/Docker
# migration (2026-04-24), env must reach the container, not the shell — so
# toggling happens at container start.
#
# Replacement: ./scripts/graphiti-stack-up.sh --llm=gb10|mac|custom
# See:         docs/guides/graphiti-gb10-deployment.md (Training-mode switchover)

cat <<'EOF' >&2
This script is deprecated.

To route the Graphiti LLM somewhere other than the GB10's local vLLM:

  ./scripts/graphiti-stack-up.sh --llm=mac        # MacBook Ollama
  ./scripts/graphiti-stack-up.sh --llm=custom     # Gemini/Anthropic/etc.
                                                  # (set GRAPHITI_LLM_API_URL +
                                                  #  GRAPHITI_LLM_MODEL first)

Or, if the MCP container is already running and you just want to point its
LLM somewhere else, restart it with env overrides:

  LLM_API_URL=http://<host>:<port>/v1 \
  LLM_MODEL=<model-name> \
  ./scripts/graphiti-mcp.sh

Full documentation: docs/guides/graphiti-gb10-deployment.md
EOF

exit 1
