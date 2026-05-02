#!/usr/bin/env bash
# infra-down.sh — Tear down the local infrastructure tiers on the GB10.
#
# Tiers (top-down, intentionally torn down in reverse-startup order):
#   1. Agents tier     — sourced from scripts/infra/agents-down.sh (no-op stub).
#   2. NATS tier       — sourced from scripts/infra/nats-down.sh (no-op stub).
#   3. Graphiti tier   — graphiti-stack-down.sh (stops graphiti-mcp).
#   4. LLM tier        — llama-swap is INTENTIONALLY NOT TOUCHED. It is shared
#                         with autobuild and other consumers and is managed by
#                         systemd timers. The only legitimate reason to stop
#                         llama-swap is a kernel reboot (DGX OS update); see
#                         RUNBOOK-INFRA-ORCHESTRATION.md.
#
# Preconditions:
#   - None. Safe to run from any state (stack up, stack down, never started).
#
# Postconditions on success:
#   - graphiti-mcp container stopped and removed (if it existed).
#   - llama-swap and FalkorDB-on-NAS untouched.
#   - Idempotent: re-running on an already-down stack exits 0.
#
# Exit codes:
#   0  graphiti-mcp not running, or successfully stopped + removed
#   1  unknown CLI argument
#
# Usage:
#   ./scripts/infra-down.sh
#   ./scripts/infra-down.sh --stop-llama-swap   # ALSO stops llama-swap-keepalive
#                                                # (rare; for DGX OS update only)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/infra"

STOP_LLAMA_SWAP=0
for arg in "$@"; do
  case "$arg" in
    --stop-llama-swap) STOP_LLAMA_SWAP=1 ;;
    -h|--help)         sed -n '2,30p' "$0"; exit 0 ;;
    *)                 echo "ERROR: unknown arg: $arg" >&2; exit 1 ;;
  esac
done

echo ""
echo "════════════════════════════════════════════════════"
echo "  GB10 infrastructure — bringing down"
echo "════════════════════════════════════════════════════"

# --- Tier 1: agents (extension hook, no-op) ---
echo ""
echo "── Tier 1: agents ──"
# shellcheck source=scripts/infra/agents-down.sh
source "$HOOKS_DIR/agents-down.sh"

# --- Tier 2: NATS (extension hook, no-op) ---
echo ""
echo "── Tier 2: NATS ──"
# shellcheck source=scripts/infra/nats-down.sh
source "$HOOKS_DIR/nats-down.sh"

# --- Tier 3: Graphiti ---
echo ""
echo "── Tier 3: Graphiti (graphiti-mcp) ──"
bash "$SCRIPT_DIR/graphiti-stack-down.sh"

# --- Tier 4: LLM (llama-swap) — opt-in only ---
echo ""
echo "── Tier 4: llama-swap ──"
if [ "$STOP_LLAMA_SWAP" = "1" ]; then
  echo "  --stop-llama-swap was passed; stopping llama-swap-keepalive..."
  if sudo systemctl stop llama-swap-keepalive.timer llama-swap-keepalive.service 2>/dev/null; then
    echo "  ✓ llama-swap-keepalive timer + service stopped"
    echo "  ⚠  the underlying llama-swap process may still be running."
    echo "     Find and kill it manually if you really need it down:"
    echo "       pgrep -af llama-swap"
  else
    echo "  ✗ failed to stop llama-swap-keepalive (sudo required)"
  fi
else
  echo "  llama-swap left running (managed by systemd timers; pass"
  echo "  --stop-llama-swap to also stop it — rarely needed)."
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "  Infrastructure down"
echo "════════════════════════════════════════════════════"
echo "  Status:  ./scripts/infra-status.sh"
echo "  Start:   ./scripts/infra-up.sh"
