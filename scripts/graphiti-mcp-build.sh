#!/usr/bin/env bash
# graphiti-mcp-build.sh — Build the standalone graphiti-mcp Docker image on GB10.
#
# Run this ONCE after cloning guardkit to a new machine (or after the fork
# tag bumps and you want to ship the new bug-fix patches). It clones the
# guardkit/graphiti fork at $GRAPHITI_TAG (read-only, never modified) and
# builds docker/Dockerfile.standalone into a local image tagged
# `graphiti-mcp-standalone:local`.
#
# The fork carries appmilla bug-fix patches against upstream getzep/graphiti
# 0.29.0 — see ~/Projects/appmilla_github/graphiti/FORK-NOTES.md for details.
#
# Design: the graphiti fork is a vendored dependency — we clone it but treat
# it as read-only. All GuardKit-specific config lives in this scripts/ dir
# (graphiti-mcp-config.yaml) so there is never any need to edit files inside
# the graphiti checkout.
#
# Usage:
#   ./scripts/graphiti-mcp-build.sh              # Clone-or-checkout-tag, then build
#   ./scripts/graphiti-mcp-build.sh --no-cache   # Force clean docker build
#
# Env overrides:
#   GRAPHITI_REPO_URL  fork URL                 (default: guardkit/graphiti)
#   GRAPHITI_TAG       tag to check out         (default: v0.29.5-guardkit.1)
#   GRAPHITI_REPO_DIR  local checkout location  (default: ~/Projects/appmilla_github/graphiti)
#   GRAPHITI_MCP_IMAGE local docker image tag   (default: graphiti-mcp-standalone:local)

set -euo pipefail

# --- Configuration ---
IMAGE_TAG="${GRAPHITI_MCP_IMAGE:-graphiti-mcp-standalone:local}"
GRAPHITI_REPO_DIR="${GRAPHITI_REPO_DIR:-$HOME/Projects/appmilla_github/graphiti}"
GRAPHITI_REPO_URL="${GRAPHITI_REPO_URL:-https://github.com/guardkit/graphiti.git}"
GRAPHITI_TAG="${GRAPHITI_TAG:-v0.29.5-guardkit.1}"

DO_NO_CACHE=0
for arg in "$@"; do
  case "$arg" in
    --no-cache) DO_NO_CACHE=1 ;;
    -h|--help)
      sed -n '2,26p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg"
      exit 1
      ;;
  esac
done

# --- Ensure graphiti fork is present at $GRAPHITI_TAG ---
if [ ! -d "$GRAPHITI_REPO_DIR/.git" ]; then
  echo "Cloning graphiti fork → $GRAPHITI_REPO_DIR (tag: $GRAPHITI_TAG)"
  mkdir -p "$(dirname "$GRAPHITI_REPO_DIR")"
  git clone --depth 1 --branch "$GRAPHITI_TAG" "$GRAPHITI_REPO_URL" "$GRAPHITI_REPO_DIR"
else
  echo "Fetching tags and checking out $GRAPHITI_TAG → $GRAPHITI_REPO_DIR"
  git -C "$GRAPHITI_REPO_DIR" fetch --tags origin
  git -C "$GRAPHITI_REPO_DIR" checkout "$GRAPHITI_TAG"
fi

DOCKERFILE="$GRAPHITI_REPO_DIR/mcp_server/docker/Dockerfile.standalone"
BUILD_CONTEXT="$GRAPHITI_REPO_DIR/mcp_server"

if [ ! -f "$DOCKERFILE" ]; then
  echo "ERROR: Dockerfile not found at $DOCKERFILE" >&2
  echo "       Is the graphiti repo fully cloned?" >&2
  exit 1
fi

# --- Build ---
echo ""
echo "========================================"
echo "  Building graphiti-mcp (standalone)"
echo "========================================"
echo "  Image:        $IMAGE_TAG"
echo "  Context:      $BUILD_CONTEXT"
echo "  Dockerfile:   $DOCKERFILE"
echo "========================================"
echo ""

BUILD_FLAGS=()
if [ "$DO_NO_CACHE" = "1" ]; then
  BUILD_FLAGS+=(--no-cache)
fi

docker build \
  "${BUILD_FLAGS[@]}" \
  -f "$DOCKERFILE" \
  -t "$IMAGE_TAG" \
  "$BUILD_CONTEXT"

echo ""
echo "Built: $IMAGE_TAG"
echo ""
echo "Next: start the full stack with ./scripts/graphiti-stack-up.sh"
