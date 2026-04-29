#!/usr/bin/env bash
# llama-swap-healthcheck.sh
#
# Weekly health check for the llama-swap stack on promaxgb10-41b1.
# Audits the last 7 days of journal data and writes a structured report.
#
# Designed to run from a systemd timer once a week. Companion files:
#   scripts/llama-swap-healthcheck.service
#   scripts/llama-swap-healthcheck.timer
#
# Filed under TASK-OPS-7CB1 follow-up — replaces the scheduled remote
# agent that would have done this from the cloud (a remote agent has no
# way to reach this host). See VALIDATION-OPS-7CB1-9F2A-results.md for
# context.
#
# Reports go to /opt/llama-swap/logs/healthcheck-YYYYMMDD.log, structured
# in five sections (timer state, keep-alive runs, revival events, model
# crashes, current state), plus a final summary.
#
# Exit codes:
#   0  HEALTHY    — timer firing, no fresh crashes (or only those the
#                   keep-alive recovered cleanly), all four models up
#   1  ATTENTION  — revivals happened in the window (recovered fine, but
#                   worth a glance), or VRAM drifted, or one-off journal
#                   gap
#   2  CRITICAL   — timer not firing on schedule, llama-swap unreachable,
#                   models missing, or repeated keep-alive failures

set -u
set -o pipefail

LLAMA_SWAP_URL="${LLAMA_SWAP_URL:-http://localhost:9000}"
WINDOW="${WINDOW:-7 days ago}"
LOG_DIR="${LOG_DIR:-/opt/llama-swap/logs}"
TODAY="$(date +%Y%m%d)"
REPORT_FILE="${REPORT_FILE:-$LOG_DIR/healthcheck-$TODAY.log}"

# Tolerance: how many missed timer fires we accept before flagging
# (5min interval × 7d = 2016 expected fires; allow up to 5% missed)
MISS_TOLERANCE_PCT=5

mkdir -p "$LOG_DIR" 2>/dev/null || true

# =============================================================================
# Helpers
# =============================================================================

EXIT_CODE=0
escalate() {
    # Take max of current and proposed exit code. 2 > 1 > 0.
    local proposed=$1
    if (( proposed > EXIT_CODE )); then
        EXIT_CODE=$proposed
    fi
}

# Capture both stdout and the report file; cleaner than `tee`.
exec > >(tee "$REPORT_FILE")
exec 2>&1

# =============================================================================
# Header
# =============================================================================

echo "=========================================================================="
echo " llama-swap-keepalive Health Check Report"
echo "=========================================================================="
echo " Date:       $(date -Iseconds)"
echo " Window:     last 7 days (since $(date -d "$WINDOW" -Iseconds 2>/dev/null || echo "$WINDOW"))"
echo " Host:       $(hostname)"
echo " Report:     $REPORT_FILE"
echo "=========================================================================="
echo ""

# =============================================================================
# Section 1: Keep-alive timer state
# =============================================================================

echo "[1] Keep-alive timer state"
echo "----------------------------------------------------------------------"
TIMER_ENABLED=$(systemctl is-enabled llama-swap-keepalive.timer 2>&1)
TIMER_ACTIVE=$(systemctl is-active  llama-swap-keepalive.timer 2>&1)
echo "  enabled:    $TIMER_ENABLED"
echo "  active:     $TIMER_ACTIVE"

if [[ "$TIMER_ENABLED" != "enabled" ]]; then
    echo "  ⚠ Timer is not enabled — won't survive reboots"
    escalate 2
fi
if [[ "$TIMER_ACTIVE" != "active" ]]; then
    echo "  ⚠ Timer is not active right now"
    escalate 2
fi

# Last fire and next scheduled fire
TIMER_LIST=$(systemctl list-timers llama-swap-keepalive.timer --no-pager --all 2>&1 | sed -n '2p')
echo "  schedule:   ${TIMER_LIST:-(unable to query)}"
echo ""

# =============================================================================
# Section 2: Keep-alive run statistics (last 7 days)
# =============================================================================

echo "[2] Keep-alive runs (last 7 days)"
echo "----------------------------------------------------------------------"
JOURNAL_TMP=$(mktemp)
journalctl -u llama-swap-keepalive.service --since "$WINDOW" --no-pager > "$JOURNAL_TMP" 2>&1 || true

# Use awk piped from grep -F to avoid the grep-c-returns-1-on-zero-matches
# trap. grep -c always prints a number, but its non-zero exit interacts
# badly with `|| echo 0` (which would then produce "0\n0"). Just use
# `|| true` and trust grep -c's stdout.
TOTAL_FIRES=$(grep -c "Starting llama-swap-keepalive.service" "$JOURNAL_TMP" || true)
NOOP_RUNS=$(grep -c "All configured models are ready; nothing to revive" "$JOURNAL_TMP" || true)
REVIVAL_RUNS=$(grep -cE "\[llama-swap-keepalive\] Reviving:" "$JOURNAL_TMP" || true)
FAILED_REVIVALS=$(grep -c "revive FAILED" "$JOURNAL_TMP" || true)
SERVICE_FAILURES=$(grep -c "llama-swap-keepalive.service: Failed" "$JOURNAL_TMP" || true)

# Expected fires scaled by how long the timer has been active. The
# original 2016 = 5min × 12/hr × 24h × 7d assumes a full 7-day window.
# If the timer was installed yesterday, we should expect ~288 fires not
# 2016. Read the timer's ActiveEnterTimestamp and clamp.
TIMER_ENABLED_TS=$(systemctl show llama-swap-keepalive.timer -p ActiveEnterTimestamp \
    --value 2>/dev/null)
TIMER_ENABLED_EPOCH=$(date -d "$TIMER_ENABLED_TS" +%s 2>/dev/null || echo 0)
NOW_EPOCH=$(date +%s)
WINDOW_START_EPOCH=$(date -d "$WINDOW" +%s 2>/dev/null || echo 0)
EFFECTIVE_START=$(( TIMER_ENABLED_EPOCH > WINDOW_START_EPOCH ? TIMER_ENABLED_EPOCH : WINDOW_START_EPOCH ))
EFFECTIVE_SECS=$(( NOW_EPOCH - EFFECTIVE_START ))
EXPECTED=$(( EFFECTIVE_SECS / 300 ))   # one fire per 5min = 300s
MISS_TOLERANCE=$(( EXPECTED * MISS_TOLERANCE_PCT / 100 ))
THRESHOLD=$(( EXPECTED - MISS_TOLERANCE ))

echo "  effective window:  $(( EFFECTIVE_SECS / 86400 ))d $(( (EFFECTIVE_SECS % 86400) / 3600 ))h (since timer install or 7d ago, whichever is sooner)"
echo "  total fires:       $TOTAL_FIRES (expected ~$EXPECTED, threshold ≥$THRESHOLD)"
echo "  clean no-op runs:  $NOOP_RUNS"
echo "  revival runs:      $REVIVAL_RUNS"
echo "  failed revivals:   $FAILED_REVIVALS"
echo "  service failures:  $SERVICE_FAILURES"

# Only escalate on missed fires once the window has accumulated a
# meaningful sample (>1 hour). Below that, a freshly-installed timer
# would always look bad.
if (( EFFECTIVE_SECS > 3600 )) && (( TOTAL_FIRES < THRESHOLD )); then
    MISSED=$(( EXPECTED - TOTAL_FIRES ))
    echo "  ⚠ $MISSED fires below threshold (>$MISS_TOLERANCE_PCT% tolerance) — timer may have stalled"
    escalate 2
fi
if (( FAILED_REVIVALS > 0 )); then
    echo "  ⚠ $FAILED_REVIVALS revive attempts returned non-2xx HTTP"
    escalate 1
fi
if (( SERVICE_FAILURES > 0 )); then
    echo "  ⚠ Service unit failed $SERVICE_FAILURES times in window"
    escalate 1
fi
echo ""

# =============================================================================
# Section 3: Recent revival events
# =============================================================================

echo "[3] Revival events (last 7 days)"
echo "----------------------------------------------------------------------"
if (( REVIVAL_RUNS > 0 )); then
    grep -E "Reviving:|revived \(HTTP|revive FAILED" "$JOURNAL_TMP" | tail -50
    if (( REVIVAL_RUNS > 0 )); then
        echo ""
        echo "  ⚠ Keep-alive recovered children $REVIVAL_RUNS times in 7 days."
        echo "    This is the keep-alive doing its job — but if the count is high"
        echo "    or trending up, root-cause the underlying crashes."
        escalate 1
    fi
else
    echo "  No revival events. All keep-alive runs were clean no-ops."
fi
echo ""

# =============================================================================
# Section 4: Model crash events from llama-swap log
# =============================================================================

echo "[4] llama-swap child-process exit events"
echo "----------------------------------------------------------------------"
LLAMA_LOG=/opt/llama-swap/logs/llama-swap.log
# State file: track exit-event count between health check runs so we
# can report deltas instead of cumulative counts (llama-swap.log lacks
# per-line timestamps, so we can't filter by date).
STATE_DIR="${STATE_DIR:-$LOG_DIR/healthcheck-state}"
STATE_FILE="$STATE_DIR/last_exit_count"
mkdir -p "$STATE_DIR" 2>/dev/null || true

if [[ -r "$LLAMA_LOG" ]]; then
    EXIT_EVENTS=$(grep -c "process exited but not StateStopping" "$LLAMA_LOG" || true)
    LAST_SEEN=0
    if [[ -r "$STATE_FILE" ]]; then
        LAST_SEEN=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
        # Sanity guard: if log was rotated/recreated, LAST_SEEN may exceed
        # current count. Treat that as a fresh baseline.
        if (( LAST_SEEN > EXIT_EVENTS )); then
            LAST_SEEN=0
        fi
    fi
    NEW_EVENTS=$(( EXIT_EVENTS - LAST_SEEN ))
    echo "  cumulative since llama-swap started: $EXIT_EVENTS"
    echo "  new since last health-check run:     $NEW_EVENTS"
    if (( NEW_EVENTS > 0 )); then
        echo "  Last 10 exit events (most recent at bottom):"
        grep "process exited but not StateStopping" "$LLAMA_LOG" | tail -10 | sed 's/^/    /'
        # 4+ new exits in a week implies the underlying crash hasn't
        # been root-caused. Escalate to ATTENTION (not CRITICAL) so the
        # operator notices without being paged.
        if (( NEW_EVENTS >= 4 )); then
            echo ""
            echo "  ⚠ $NEW_EVENTS new unexpected exits since last check — this is the"
            echo "    TASK-OPS-7CB1 failure mode recurring. Keep-alive is recovering"
            echo "    them, but the root cause is unsolved. Investigate the cgroup"
            echo "    hosting llama-swap (Phase 10.2 VS-Code-scope warning)."
            escalate 1
        fi
    fi
    # Persist the current count for next run
    echo "$EXIT_EVENTS" > "$STATE_FILE" 2>/dev/null || true
else
    echo "  $LLAMA_LOG: not readable (skipping)"
    # Don't escalate — this happens cleanly on hosts where llama-swap
    # logs to stderr/journal rather than the file path.
fi
echo ""

# =============================================================================
# Section 5: Current model state
# =============================================================================

echo "[5] Current model state"
echo "----------------------------------------------------------------------"
RUNNING_JSON=$(curl -sS --max-time 5 "$LLAMA_SWAP_URL/running" 2>/dev/null || echo "")
if [[ -z "$RUNNING_JSON" ]]; then
    echo "  ⚠ llama-swap admin endpoint $LLAMA_SWAP_URL/running unreachable"
    escalate 2
else
    READY_COUNT=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
except Exception as e:
    print('PARSE-ERROR:' + str(e), file=sys.stderr)
    sys.exit(1)
ready = [e for e in d.get('running', []) if e.get('state') == 'ready']
for e in ready:
    print(f\"  {e['model']:20s} state={e['state']:10s} ttl={e['ttl']}\")
print(f'__ready_count__={len(ready)}')" <<< "$RUNNING_JSON")
    echo "$READY_COUNT" | grep -v '__ready_count__'
    READY=$(echo "$READY_COUNT" | grep '__ready_count__' | cut -d= -f2)
    if (( READY < 4 )); then
        echo "  ⚠ Only $READY/4 models loaded; keep-alive will revive on next fire"
        escalate 1
    fi
fi

# VRAM total
VRAM_TOTAL=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits 2>/dev/null | \
    awk '{sum += $1} END {printf "%.2f", sum/1024}')
echo "  Total VRAM: ${VRAM_TOTAL:-?} GiB (expected ~65 GiB)"
if [[ -n "$VRAM_TOTAL" ]]; then
    # bash can't do float comparison, use bc
    DEVIATES=$(echo "$VRAM_TOTAL < 60 || $VRAM_TOTAL > 75" | bc 2>/dev/null || echo 0)
    if (( DEVIATES )); then
        echo "  ⚠ VRAM total outside expected band [60, 75] GiB"
        escalate 1
    fi
fi
echo ""

rm -f "$JOURNAL_TMP"

# =============================================================================
# Summary
# =============================================================================

echo "=========================================================================="
case "$EXIT_CODE" in
    0) STATUS="HEALTHY" ;;
    1) STATUS="ATTENTION" ;;
    2) STATUS="CRITICAL" ;;
    *) STATUS="UNKNOWN" ;;
esac
echo " Summary: $STATUS  (exit $EXIT_CODE)"
echo "=========================================================================="
echo ""
echo " Cross-references:"
echo "   - TASK-OPS-7CB1: tasks/completed/2026-04/TASK-OPS-7CB1-investigate-overnight-llama-server-crashes.md"
echo "   - Validation:    docs/research/dgx-spark/VALIDATION-OPS-7CB1-9F2A-results.md"
echo "   - Runbook:       docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md (Phase 5.6, 5.7)"
echo ""
echo " Next run:"
systemctl list-timers llama-swap-healthcheck.timer --no-pager 2>/dev/null | sed -n '2p' | sed 's/^/   /'
echo ""

exit "$EXIT_CODE"
