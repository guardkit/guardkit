#!/usr/bin/env bash
# infra-up.sh — Bring up the local infrastructure tiers on the GB10.
#
# Tiers (top-down):
#   1. LLM tier        — llama-swap on :9000 (managed by systemd timers,
#                         only consumed here, never started/stopped/modified
#                         by this script — see AC-10 of TASK-INFRA-001).
#   2. Graphiti tier   — graphiti-mcp + FalkorDB precondition checks
#                         (graphiti-stack-up.sh).
#   3. NATS tier       — sourced from scripts/infra/nats-up.sh (no-op stub
#                         until a future task fills it in).
#   4. Agents tier     — sourced from scripts/infra/agents-up.sh (no-op stub
#                         until a future task fills it in).
#
# Preconditions:
#   - llama-swap-keepalive.timer is enabled and running (it is by default;
#     this script will trigger the keepalive service one-shot if llama-swap
#     is not currently responding on :9000).
#   - The graphiti-mcp-standalone:local image exists locally.
#
# Postconditions on success:
#   - llama-swap is responding at http://localhost:9000/v1/models.
#   - graphiti-mcp container is running and `healthy`.
#   - Per-component pass/fail lines have been printed.
#   - Idempotent: re-running on an already-up stack exits 0.
#
# Exit codes:
#   0  all in-scope tiers up; per-component status reported
#   2  llama-swap unreachable after best-effort revive
#   3+  delegated from graphiti-stack-up.sh (see that script for codes)
#
# Usage:
#   ./scripts/infra-up.sh
#   ./scripts/infra-up.sh --no-graphiti     # skip the graphiti tier
#
# Companion scripts:
#   ./scripts/infra-down.sh
#   ./scripts/infra-status.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/infra"

LLAMA_SWAP_URL="${LLAMA_SWAP_URL:-http://localhost:9000}"
WAIT_LLAMA_SECONDS="${WAIT_LLAMA_SECONDS:-30}"

SKIP_GRAPHITI=0
for arg in "$@"; do
  case "$arg" in
    --no-graphiti) SKIP_GRAPHITI=1 ;;
    -h|--help)     sed -n '2,40p' "$0"; exit 0 ;;
    *)             echo "ERROR: unknown arg: $arg" >&2; exit 1 ;;
  esac
done

echo ""
echo "════════════════════════════════════════════════════"
echo "  GB10 infrastructure — bringing up"
echo "════════════════════════════════════════════════════"

# --- Tier 1: llama-swap (consume only, do not start/stop) ---
echo ""
echo "── Tier 1: llama-swap (LLM + embed) ──"
probe_llama() {
  curl -fsS --max-time 3 "$LLAMA_SWAP_URL/v1/models" 2>/dev/null \
    | grep -q '"qwen-graphiti"' \
    && curl -fsS --max-time 3 "$LLAMA_SWAP_URL/v1/models" 2>/dev/null \
    | grep -q '"nomic-embed"'
}

if probe_llama; then
  echo "  ✓ llama-swap up at $LLAMA_SWAP_URL with qwen-graphiti + nomic-embed"
else
  echo "  ⚠  llama-swap not responding on $LLAMA_SWAP_URL; triggering keepalive..."
  if systemctl start llama-swap-keepalive.service 2>/dev/null; then
    echo "    keepalive triggered; waiting up to ${WAIT_LLAMA_SECONDS}s..."
    start="$(date +%s)"
    while true; do
      if probe_llama; then
        end="$(date +%s)"
        echo "  ✓ llama-swap recovered after $((end - start))s"
        break
      fi
      end="$(date +%s)"
      if [ $((end - start)) -ge "$WAIT_LLAMA_SECONDS" ]; then
        echo "  ✗ llama-swap still not serving qwen-graphiti + nomic-embed after ${WAIT_LLAMA_SECONDS}s" >&2
        echo "    Logs:  journalctl -u llama-swap-keepalive.service --since '5 min ago'" >&2
        exit 2
      fi
      sleep 1
    done
  else
    echo "  ✗ failed to trigger llama-swap-keepalive.service (sudo required?)" >&2
    echo "    Try:  sudo systemctl start llama-swap-keepalive.service" >&2
    exit 2
  fi
fi

# --- Tier 2: graphiti-mcp + FalkorDB precondition ---
echo ""
echo "── Tier 2: Graphiti (FalkorDB precondition + graphiti-mcp) ──"
if [ "$SKIP_GRAPHITI" = "1" ]; then
  echo "  (skipped — --no-graphiti)"
else
  bash "$SCRIPT_DIR/graphiti-stack-up.sh"
fi

# --- Tier 3: NATS (extension hook, no-op) ---
echo ""
echo "── Tier 3: NATS ──"
# shellcheck source=scripts/infra/nats-up.sh
source "$HOOKS_DIR/nats-up.sh"

# --- Tier 4: agents (extension hook, no-op) ---
echo ""
echo "── Tier 4: agents ──"
# shellcheck source=scripts/infra/agents-up.sh
source "$HOOKS_DIR/agents-up.sh"

echo ""
echo "════════════════════════════════════════════════════"
echo "  Infrastructure up"
echo "════════════════════════════════════════════════════"
echo "  Status:  ./scripts/infra-status.sh"
echo "  Stop:    ./scripts/infra-down.sh"
