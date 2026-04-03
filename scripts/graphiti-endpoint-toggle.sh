#!/usr/bin/env bash
# Toggle Graphiti LLM endpoint between GB10 and MacBook
# Usage: source scripts/graphiti-endpoint-toggle.sh [gb10|macbook]
#
# This sets the LLM_API_URL environment variable. The MCP server config
# (config-guardkit.yaml) uses ${LLM_API_URL:...} with env var fallback,
# so restarting the MCP server (or Claude Code) after setting this is sufficient.
#
# Note: This only affects the LLM endpoint. The embedding model always
# stays on GB10 (promaxgb10-41b1:8001).

case "${1:-}" in
  gb10)
    export LLM_API_URL="http://promaxgb10-41b1:8000/v1"
    echo "Graphiti LLM -> GB10 (promaxgb10-41b1:8000, vLLM)"
    ;;
  macbook)
    export LLM_API_URL="http://richards-macbook-pro.tailebf801.ts.net:8000/v1"
    echo "Graphiti LLM -> MacBook (richards-macbook-pro.tailebf801.ts.net:8000, Ollama)"
    ;;
  *)
    echo "Usage: source $0 [gb10|macbook]"
    echo "  gb10    - Point Graphiti LLM at GB10 (vLLM, FP8)"
    echo "  macbook - Point Graphiti LLM at MacBook Pro M2 Max (Ollama, Q4_K_M)"
    echo ""
    echo "Current LLM_API_URL: ${LLM_API_URL:-<not set>}"
    ;;
esac
