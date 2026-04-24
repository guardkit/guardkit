#!/usr/bin/env bash
# graphiti-mcp-build.sh — Build the standalone graphiti-mcp Docker image on GB10.
#
# Run this ONCE after cloning guardkit to a new machine (or after pulling a
# graphiti update you want to ship). It clones getzep/graphiti (read-only,
# never modified) and builds docker/Dockerfile.standalone into a local image
# tagged `graphiti-mcp-standalone:local`.
#
# Design: the graphiti repo is a vendored dependency — we clone it but treat
# it as read-only. All GuardKit-specific config lives in this scripts/ dir
# (graphiti-mcp-config.yaml) so there is never any need to edit files inside
# the graphiti checkout.
#
# Usage:
#   ./scripts/graphiti-mcp-build.sh              # Clone if missing, then build
#   ./scripts/graphiti-mcp-build.sh --pull       # git pull first, then rebuild
#   ./scripts/graphiti-mcp-build.sh --no-cache   # Force clean docker build

set -euo pipefail

# --- Configuration ---
IMAGE_TAG="${GRAPHITI_MCP_IMAGE:-graphiti-mcp-standalone:local}"
GRAPHITI_REPO_DIR="${GRAPHITI_REPO_DIR:-$HOME/Projects/appmilla_github/graphiti}"
GRAPHITI_REPO_URL="${GRAPHITI_REPO_URL:-https://github.com/getzep/graphiti.git}"

DO_PULL=0
DO_NO_CACHE=0
for arg in "$@"; do
  case "$arg" in
    --pull)     DO_PULL=1 ;;
    --no-cache) DO_NO_CACHE=1 ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg"
      exit 1
      ;;
  esac
done

# --- Ensure graphiti repo is present ---
if [ ! -d "$GRAPHITI_REPO_DIR/.git" ]; then
  echo "Cloning graphiti repo → $GRAPHITI_REPO_DIR"
  mkdir -p "$(dirname "$GRAPHITI_REPO_DIR")"
  git clone --depth 1 "$GRAPHITI_REPO_URL" "$GRAPHITI_REPO_DIR"
elif [ "$DO_PULL" = "1" ]; then
  echo "Pulling latest graphiti → $GRAPHITI_REPO_DIR"
  git -C "$GRAPHITI_REPO_DIR" pull --ff-only
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
