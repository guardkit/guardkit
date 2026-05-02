#!/usr/bin/env bash
# agents-down.sh — Tear down the agents tier (extension hook).
#
# Currently a no-op. The future task that wires this in will stop the
# specialist-agent containers and (eventually) jarvis itself.
#
# Sourced by ../infra-down.sh; must be sourceable (no `exit`) and must respect
# `set -euo pipefail` from the caller.

echo "  [hook] agents-down.sh — TODO: implemented by future task"
return 0 2>/dev/null || true
