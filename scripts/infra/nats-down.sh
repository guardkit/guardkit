#!/usr/bin/env bash
# nats-down.sh — Tear down the NATS infrastructure tier (extension hook).
#
# Currently a no-op. The future task that wires this in will live in the
# nats-infrastructure repo at ~/Projects/appmilla_github/nats-infrastructure/.
#
# Sourced by ../infra-down.sh; must be sourceable (no `exit`) and must respect
# `set -euo pipefail` from the caller.

echo "  [hook] nats-down.sh — TODO: implemented by future task"
return 0 2>/dev/null || true
