#!/usr/bin/env bash
# graphiti-stack-down.sh — Stop the Graphiti stack on the GB10.
#
# Preconditions:
#   - None. Safe to run from any state (stack up, stack down, never started).
#
# Postconditions on success:
#   - The graphiti-mcp container is stopped and removed (if it existed).
#   - Re-running this script against the already-down state is a no-op
#     (idempotent — exits 0 with no error output).
#
# Exit codes:
#   0  graphiti-mcp not running, or successfully stopped + removed
#   1  unknown CLI argument
#
# What this script does NOT touch:
#   - llama-swap on :9000. It is managed by systemd timers
#     (llama-swap-keepalive.timer, llama-swap-healthcheck.timer) and is
#     deliberately shared by graphiti-mcp, jarvis, autobuild, and others.
#     Stop it via systemd if you really mean to (rare; see RUNBOOK-INFRA-ORCHESTRATION).
#   - FalkorDB on whitestocks:6379. It is on the NAS, not local to the GB10.
#
# Usage:
#   ./scripts/graphiti-stack-down.sh
#
# History:
#   Pre-2026-04-29 this script also stopped vllm-graphiti (port 8000) and
#   vllm-embedding (port 8001). Those were superseded by llama-swap on :9000
#   (managed by systemd, never by this script) and removed from teardown.

set -euo pipefail

for arg in "$@"; do
  case "$arg" in
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $arg" >&2
      exit 1
      ;;
  esac
done

stop_container() {
  local name="$1"
  if docker ps -aq --filter "name=^${name}$" | grep -q .; then
    echo "  Stopping $name..."
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

echo ""
echo "Stack down."
echo "  (llama-swap on :9000 is managed by systemd and was not touched.)"
echo "  (FalkorDB on whitestocks:6379 lives on the NAS and was not touched.)"
