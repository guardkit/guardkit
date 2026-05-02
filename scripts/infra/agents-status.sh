#!/usr/bin/env bash
# agents-status.sh — Status of the agents tier (extension hook).
#
# Currently a stub. The future task that wires this in will probe each
# specialist-agent container and emit per-agent state lines.
#
# Sourced by ../infra-status.sh.

echo "  agents:      not yet managed by infra-* scripts (TODO: future task)"
return 0 2>/dev/null || true
