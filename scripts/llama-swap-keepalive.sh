#!/usr/bin/env bash
# llama-swap-keepalive.sh
#
# Probes llama-swap's admin endpoint and revives any configured-but-not-running
# model with a single one-shot OpenAI-compatible request that returns
# immediately, so it does not hold a concurrencyLimit slot.
#
# Designed to run from a systemd timer every ~5 minutes. Companion files:
#   scripts/llama-swap-keepalive.service
#   scripts/llama-swap-keepalive.timer
#
# Filed under TASK-OPS-7CB1 — see the task file for context (one observed
# overnight four-way crash where llama-swap parent survived but all four
# llama-server children exited unexpectedly, leaving the workhorse and tutor
# DOWN until manually re-requested).
#
# Exit codes:
#   0  all configured models running (revived where needed)
#   1  llama-swap admin endpoint unreachable
#   2  unexpected response shape from admin endpoint
#   3  one or more revival attempts failed

set -u
set -o pipefail

LLAMA_SWAP_URL="${LLAMA_SWAP_URL:-http://localhost:9000}"
REVIVE_TIMEOUT="${REVIVE_TIMEOUT:-300}"   # seconds; cold start of the largest model is ~3-4 min
PROBE_TIMEOUT="${PROBE_TIMEOUT:-5}"        # seconds; admin endpoints answer in <100ms
LOCK_FILE="${LOCK_FILE:-/var/lock/llama-swap-keepalive.lock}"
LOG_TAG="llama-swap-keepalive"

# Per-model probe shape: chat | embed
# Hardcoded against /opt/llama-swap/config/config.yaml. If config.yaml grows a
# new model, add an entry here. Wrong endpoint produces a 4xx and still revives
# the model (llama-swap loads on first request regardless), so a missing entry
# is degraded but not broken.
#
# 2026-05-30: swapped gemma4-tutor → architect-agent to match the rotated
# preload set in config.yaml. Tutor is now on-demand via the `tutor` matrix
# set and MUST NOT be probed here (it would auto-load every 5 min and defeat
# the on-demand intent). architect-agent uses gemma4-thinking.jinja — its
# thinking-mode output is truncated at max_tokens=1 in the probe, which is
# harmless. See findings §9.9.
#
# 2026-06-06 (TASK-HMIG-013): swapped architect-agent → gemma4-coach to
# match the next rotated preload set. gemma4-coach (base Gemma 4 26B-A4B-IT
# UD-Q4_K_XL) takes the always-on slot to close the F17 Coach verdict-
# emission gap before the 2026-06-15 cutover; architect-agent moves to
# on-demand via the new `arch` matrix.set and MUST NOT be probed here for
# the same reason tutor isn't probed (probing would defeat the on-demand
# intent). gemma4-coach uses the model's embedded IT chat template (no
# .jinja file) — its single-token probe output is harmless. See findings
# §9.13.
# 2026-06-21: swapped gemma4-coach → coach-ft-v3 to match the rotated preload
# set in config.yaml (the fine-tuned bundle-format Coach took the always-on slot;
# memory-neutral — same 26B-A4B family). The deployed /usr/local/bin copy was
# already updated; this repo copy was lagging. MODEL_PROBE_KIND MUST equal
# hooks.on_startup.preload in config.yaml. See RESULTS-coach-v3.md.
declare -A MODEL_PROBE_KIND=(
    [qwen-graphiti]=chat
    [nomic-embed]=embed
    [qwen36-workhorse]=chat
    [coach-ft-v3]=chat
)

log() {
    # Single-line journald-friendly logging; systemd-cat tags it.
    echo "[$LOG_TAG] $*"
}

# Acquire a non-blocking exclusive lock so overlapping timer fires can't pile up
# (a slow cold-start could otherwise trigger 3-4 concurrent revives).
exec 9>"$LOCK_FILE" 2>/dev/null || {
    log "WARN: cannot open lock file $LOCK_FILE; running without lock"
}
if [[ -e /proc/$$/fd/9 ]]; then
    if ! flock -n 9; then
        log "Another keep-alive run is in progress; exiting."
        exit 0
    fi
fi

# Probe the admin endpoint. /running returns the currently-loaded models;
# /v1/models returns everything configured. Diff them.
running_json=$(curl -sS --max-time "$PROBE_TIMEOUT" "$LLAMA_SWAP_URL/running") || {
    log "ERROR: cannot reach $LLAMA_SWAP_URL/running"
    exit 1
}
configured_json=$(curl -sS --max-time "$PROBE_TIMEOUT" "$LLAMA_SWAP_URL/v1/models") || {
    log "ERROR: cannot reach $LLAMA_SWAP_URL/v1/models"
    exit 1
}

# Only revive models on the ALWAYS-ON allowlist (the MODEL_PROBE_KIND keys).
# On-demand models (qwen3-coder-30b, granite-docling, gemma4-tutor) are
# INTENTIONALLY not-running between uses — they must NOT be revived. Reviving
# them previously loaded the 77 GB qwen-coder-next and thrashed the GPU's
# exclusive coder sets every 5 min, spiking unified memory past 121 GB → hard
# freeze (2026-05-29). The MODEL_PROBE_KIND map is the source of truth for
# "keep warm"; add an entry there to manage a new always-on model.
# See docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md §9.4 + §9.9.
ALWAYS_ON="${!MODEL_PROBE_KIND[*]}"

# Parse with python3 (always present on this host) rather than jq (not
# guaranteed in stripped systemd environments). We treat any allowlisted model
# whose /running entry is missing OR whose state is not "ready" as needing a
# revive; non-allowlisted (on-demand) models are ignored.
mapfile -t TO_REVIVE < <(python3 - "$running_json" "$configured_json" "$ALWAYS_ON" <<'PY'
import json, sys
running_raw, configured_raw, allow_raw = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    running = json.loads(running_raw).get("running", [])
    configured = json.loads(configured_raw).get("data", [])
except (ValueError, AttributeError) as e:
    print(f"ERROR: parse: {e}", file=sys.stderr)
    sys.exit(2)

allow = set(allow_raw.split())
ready = {entry["model"] for entry in running if entry.get("state") == "ready"}
configured_ids = [m["id"] for m in configured]

for mid in configured_ids:
    if mid in allow and mid not in ready:
        print(mid)
PY
) || {
    rc=$?
    log "ERROR: admin endpoint returned unexpected JSON shape (python rc=$rc)"
    exit 2
}

if [[ ${#TO_REVIVE[@]} -eq 0 ]]; then
    log "All configured models are ready; nothing to revive."
    exit 0
fi

log "Reviving: ${TO_REVIVE[*]}"

# Fire one-shot revive requests in parallel — they all just return as soon as
# the model is loaded and answers a 1-token request, releasing the slot.
declare -a PIDS=()
declare -a NAMES=()
declare -a RCS=()

for model in "${TO_REVIVE[@]}"; do
    kind="${MODEL_PROBE_KIND[$model]:-chat}"
    if [[ "$kind" == "embed" ]]; then
        body=$(printf '{"model":"%s","input":"keepalive"}' "$model")
        endpoint="$LLAMA_SWAP_URL/v1/embeddings"
    else
        body=$(printf '{"model":"%s","max_tokens":1,"messages":[{"role":"user","content":"k"}]}' "$model")
        endpoint="$LLAMA_SWAP_URL/v1/chat/completions"
    fi
    (
        curl -sS --max-time "$REVIVE_TIMEOUT" \
            -H "Content-Type: application/json" \
            -d "$body" \
            -o /dev/null \
            -w "%{http_code}" \
            "$endpoint" \
            > "/tmp/llama-keepalive-$model.code" 2>"/tmp/llama-keepalive-$model.err"
    ) &
    PIDS+=("$!")
    NAMES+=("$model")
done

# Reap and report.
fail=0
for i in "${!PIDS[@]}"; do
    wait "${PIDS[$i]}" || true
    code=$(cat "/tmp/llama-keepalive-${NAMES[$i]}.code" 2>/dev/null || echo "")
    err=$(cat "/tmp/llama-keepalive-${NAMES[$i]}.err" 2>/dev/null || echo "")
    rm -f "/tmp/llama-keepalive-${NAMES[$i]}.code" "/tmp/llama-keepalive-${NAMES[$i]}.err"
    if [[ "$code" =~ ^2 ]]; then
        log "  ${NAMES[$i]}: revived (HTTP $code)"
    else
        log "  ${NAMES[$i]}: revive FAILED (HTTP ${code:-none}; err=${err:-none})"
        fail=1
    fi
done

if (( fail )); then
    exit 3
fi
exit 0
