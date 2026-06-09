#!/usr/bin/env bash
# GB10-side monitor for run-17 (TASK-OPS-COACH31B). Samples health every 20s,
# exits EARLY (rc=7) on a NEW kernel OOM-kill so the operator session is
# notified immediately. Otherwise runs ~40 min then exits (rc=0) for a periodic
# check-in. Tracks: memory headroom, g31 GPU footprint, loaded set (thrash),
# Mac request activity (IP 100.111.236.109), and 502 count.
set -u
LOG=/opt/llama-swap/logs/llama-swap.log
SINCE="${1:-2026-06-09 06:36:00}"
BASE_502="${2:-752}"
ITERS="${3:-120}"   # 120 * 20s = 40 min
OUT="${4:-/home/richardwoollcott/Projects/appmilla_github/guardkit/docs/state/TASK-OPS-COACH31B/probes/run17-monitor.log}"
BASE_400="${5:-0}"   # baseline ctx-overflow (F20) count

echo "=== run-17 monitor start $(date '+%H:%M:%S') since='$SINCE' base502=$BASE_502 ===" >> "$OUT"
for i in $(seq 1 "$ITERS"); do
  TS=$(date '+%H:%M:%S')
  AVAIL=$(free -m | awk '/^Mem:/{print $7}')
  GPU=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits 2>/dev/null | sort -rn | head -1)
  RUNNING=$(curl -sS --max-time 4 http://localhost:9000/running 2>/dev/null | python3 -c "import sys,json;print('+'.join(sorted(m['model']+':'+m['state'] for m in json.load(sys.stdin)['running'])))" 2>/dev/null)
  MAC=$(grep -ac "100.111.236.109" "$LOG" 2>/dev/null)
  N502=$(grep -ac "status=502" "$LOG" 2>/dev/null)
  N400=$(grep -ac "HTTP/1.1\" 400" "$LOG" 2>/dev/null)
  OOM=$(journalctl -k --since "$SINCE" --no-pager 2>/dev/null | grep -c "Killed process")
  FLAG=""
  [ "$N502" -gt "$BASE_502" ] && FLAG="$FLAG NEW-502(+$((N502-BASE_502)))"
  [ "$N400" -gt "$BASE_400" ] && FLAG="$FLAG NEW-400/F20(+$((N400-BASE_400)))"
  echo "$TS avail=${AVAIL}MB gpu_top=${GPU}MiB set=[$RUNNING] mac_reqs=$MAC oom=$OOM n400=$N400$FLAG" >> "$OUT"
  if [ "$OOM" -gt 0 ]; then
    echo "!!! $TS NEW OOM-KILL DETECTED ($OOM) — hit F23A again. Exiting." >> "$OUT"
    journalctl -k --since "$SINCE" --no-pager 2>/dev/null | grep "Killed process" | tail -3 >> "$OUT"
    exit 7
  fi
  if [ "$N400" -gt "$BASE_400" ]; then
    echo "!!! $TS NEW F20 CTX-OVERFLOW (400 count $BASE_400 -> $N400) — Coach prompt exceeded ctx. Exiting." >> "$OUT"
    grep -aE "exceed_context|HTTP/1.1\" 400" "$LOG" 2>/dev/null | tail -3 >> "$OUT"
    exit 8
  fi
  sleep 20
done
echo "=== run-17 monitor check-in $(date '+%H:%M:%S') (no OOM in window) ===" >> "$OUT"
exit 0
