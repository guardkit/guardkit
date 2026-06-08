#!/usr/bin/env bash
# TASK-OPS-COACH31B — safe cold-load of the Gemma 4 31B dense QAT Coach.
#
# PRECONDITION: the keepalive timer MUST be paused first, else it revives
# gemma4-coach ON TOP of gemma4-31b within 5 min → OOM/freeze:
#     sudo systemctl stop llama-swap-keepalive.timer
#
# This script requests the `gemma4:31b` alias, which makes llama-swap switch
# to the `coach31` matrix set (qg & ne & qw & g31 & dl) — evicting gemma4-coach
# and cold-loading the dense 31B. It polls /running until g31 is ready and
# prints `free -m` before/during/after so an OOM trend can be caught early.
set -u
URL=http://localhost:9000
echo "=== keepalive timer state (should be inactive) ==="
systemctl is-active llama-swap-keepalive.timer 2>/dev/null || echo "(inactive — good)"
echo "=== free -m BEFORE ==="; free -m | sed -n '1,2p'
echo "=== /running BEFORE ==="; curl -sS --max-time 5 $URL/running | python3 -c "import sys,json;[print(' ',m['model'],m['state']) for m in json.load(sys.stdin)['running']]"

echo "=== triggering coach31 set load (warm-up request to gemma4:31b) ==="
# Fire-and-forget warm-up; the set-switch + cold load happens server-side.
curl -sS --max-time 600 -X POST $URL/v1/chat/completions \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer llama-swap-local-key' \
  -d '{"model":"gemma4:31b","messages":[{"role":"user","content":"ready?"}],"max_tokens":1,"temperature":0.1}' \
  > /tmp/g31-warmup.json 2>/tmp/g31-warmup.err &
WARM=$!

echo "=== polling /running + free -m (up to ~6 min) ==="
for i in $(seq 1 72); do
  sleep 5
  STATE=$(curl -sS --max-time 5 $URL/running 2>/dev/null | python3 -c "import sys,json
try:
    r=json.load(sys.stdin)['running']
    g=[m for m in r if m['model']=='gemma4-31b']
    print(g[0]['state'] if g else 'absent')
except Exception as e:
    print('err')" 2>/dev/null)
  FREE=$(free -m | awk '/^Mem:/{print $7}')
  echo "  t=$((i*5))s g31=$STATE free_avail=${FREE}MB"
  if [ "$STATE" = "ready" ]; then echo "  -> g31 READY"; break; fi
  if [ -n "$FREE" ] && [ "$FREE" -lt 2000 ]; then echo "  !! LOW MEMORY ($FREE MB) — abort risk"; fi
done
wait $WARM 2>/dev/null
echo "=== warm-up response ==="; cat /tmp/g31-warmup.json 2>/dev/null | head -c 400; echo
echo "=== free -m AFTER load ==="; free -m | sed -n '1,2p'
echo "=== /running AFTER ==="; curl -sS --max-time 5 $URL/running | python3 -c "import sys,json;[print(' ',m['model'],m['state']) for m in json.load(sys.stdin)['running']]"
