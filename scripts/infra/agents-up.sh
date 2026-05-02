#!/usr/bin/env bash
# agents-up.sh — Bring up the agents tier (extension hook).
#
# Currently a no-op. The future task that wires this in will start
# specialist-agent containers and (eventually) jarvis itself.
#
# Sourced by ../infra-up.sh; must be sourceable (no `exit`) and must respect
# `set -euo pipefail` from the caller.

echo "  [hook] agents-up.sh — TODO: implemented by future task"
return 0 2>/dev/null || true
