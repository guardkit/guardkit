#!/usr/bin/env bash
# graphiti-stack-down.sh — Stop the Graphiti-on-GB10 stack.
#
# Stops in reverse order (MCP → embed → LLM) so clients see the MCP server
# disappear first and don't issue requests into a half-torn-down stack.
#
# Usage:
#   ./scripts/graphiti-stack-down.sh
#   ./scripts/graphiti-stack-down.sh --keep-llm     # leave vllm-graphiti running
#   ./scripts/graphiti-stack-down.sh --keep-embed   # leave vllm-embedding running

set -euo pipefail

KEEP_LLM=0
KEEP_EMBED=0
for arg in "$@"; do
  case "$arg" in
    --keep-llm)   KEEP_LLM=1 ;;
    --keep-embed) KEEP_EMBED=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg"
      exit 1
      ;;
  esac
done

stop_container() {
  local name="$1"
  if docker ps -aq --filter "name=^${name}$" | grep -q .; then
    echo "Stopping $name..."
    docker stop "$name" >/dev/null 2>&1 || true
    docker rm "$name" >/dev/null 2>&1 || true
    echo "  ✓ $name removed"
  else
    echo "  $name not running — skipping"
  fi
}

echo ""
echo "════════════════════════════════════════"
echo "  Graphiti stack — stopping"
echo "════════════════════════════════════════"

stop_container "graphiti-mcp"

if [ "$KEEP_EMBED" = "0" ]; then
  stop_container "vllm-embedding"
else
  echo "  vllm-embedding — KEPT (--keep-embed)"
fi

if [ "$KEEP_LLM" = "0" ]; then
  stop_container "vllm-graphiti"
else
  echo "  vllm-graphiti — KEPT (--keep-llm)"
fi

echo ""
echo "Stack down."
