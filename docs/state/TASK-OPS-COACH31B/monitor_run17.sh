#!/usr/bin/env bash
# GB10-side monitor for run-17 (TASK-OPS-COACH31B). Samples health every 20s,
# exits EARLY (rc=7) on a NEW kernel OOM-kill so the operator session is
# notified immediately. Otherwise runs ~40 min then exits (rc=0) for a periodic
# check-in. Tracks: memory headroom, g31 GPU footprint, loaded set (thrash),
# Mac request activity (IP 100.111.236.109), and 502 count.
set -u
LOG=/opt/llama-swap/logs/llama-swap.log
OUT=/home/richardwoollcott/Projects/appmilla_github/guardkit/docs/state/TASK-OPS-COACH31B/probes/run17-monitor.log
SINCE="${1:-2026-06-09 06:36:00}"
BASE_502="${2:-752}"
ITERS="${3:-120}"   # 120 * 20s = 40 min

echo "=== run-17 monitor start $(date '+%H:%M:%S') since='$SINCE' base502=$BASE_502 ===" >> "$OUT"
for i in $(seq 1 "$ITERS"); do
  TS=$(date '+%H:%M:%S')
  AVAIL=$(free -m | awk '/^Mem:/{print $7}')
  GPU=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits 2>/dev/null | sort -rn | head -1)
  RUNNING=$(curl -sS --max-time 4 http://localhost:9000/running 2>/dev/null | python3 -c "import sys,json;print('+'.join(sorted(m['model']+':'+m['state'] for m in json.load(sys.stdin)['running'])))" 2>/dev/null)
  MAC=$(grep -ac "100.111.236.109" "$LOG" 2>/dev/null)
  N502=$(grep -ac "status=502" "$LOG" 2>/dev/null)
  OOM=$(journalctl -k --since "$SINCE" --no-pager 2>/dev/null | grep -c "Killed process")
  FLAG=""
  [ "$N502" -gt "$BASE_502" ] && FLAG="$FLAG NEW-502(+$((N502-BASE_502)))"
  echo "$TS avail=${AVAIL}MB gpu_top=${GPU}MiB set=[$RUNNING] mac_reqs=$MAC oom=$OOM$FLAG" >> "$OUT"
  if [ "$OOM" -gt 0 ]; then
    echo "!!! $TS NEW OOM-KILL DETECTED ($OOM) — run-17 hit F23A again. Exiting." >> "$OUT"
    journalctl -k --since "$SINCE" --no-pager 2>/dev/null | grep "Killed process" | tail -3 >> "$OUT"
    exit 7
  fi
  sleep 20
done
echo "=== run-17 monitor check-in $(date '+%H:%M:%S') (no OOM in window) ===" >> "$OUT"
exit 0
