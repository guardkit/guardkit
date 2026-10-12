#!/bin/sh
# Tear the fixture down as a SEPARATELY RECORDED command. The receipt names the
# acting build (GUARDKIT_RUN_OWNER) and the command's start and end times, so a
# removal event can be matched to this teardown and to nothing else.
# Usage: ./teardown.sh <receipt.json>
set -eu
here=$(cd "$(dirname "$0")" && pwd)
exec python -m guardkit.orchestrator.container_attribution record-teardown \
    --receipt "$1" -- docker compose -f "$here/compose.yaml" down
