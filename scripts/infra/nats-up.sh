#!/usr/bin/env bash
# nats-up.sh — Bring up the NATS infrastructure tier (extension hook).
#
# Currently a no-op. The future task that wires this in will live in the
# nats-infrastructure repo at ~/Projects/appmilla_github/nats-infrastructure/
# and will compose-up that tier's docker-compose.yml.
#
# Sourced by ../infra-up.sh; must be sourceable (no `exit`) and must respect
# `set -euo pipefail` from the caller.

echo "  [hook] nats-up.sh — TODO: implemented by future task"
echo "         see ~/Projects/appmilla_github/nats-infrastructure/docker-compose.yml"
return 0 2>/dev/null || true
