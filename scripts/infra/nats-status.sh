#!/usr/bin/env bash
# nats-status.sh — Status of the NATS infrastructure tier (extension hook).
#
# Currently a stub. The future task that wires this in will probe the NATS
# cluster's health endpoints and emit per-node up/down lines.
#
# Sourced by ../infra-status.sh.

echo "  NATS:        not yet managed by infra-* scripts (TODO: future task)"
return 0 2>/dev/null || true
