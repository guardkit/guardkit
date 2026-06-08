# Run-15 recipe — AC-3 falsifier (31B as Coach)

> **Deferred** (operator decision 2026-06-08) until AC-2 single-shot results
> justify the multi-hour spend. This is the *real* test: the tool-bound agentic
> Coach, not a single-shot probe.

## Falsifier bar (AC-3)
With the 31B as Coach, across ≥4 Coach turns: ≥1 turn **converges** (emits a
valid fenced-JSON verdict AND finishes within the SDK timeout) and ≥80% of
Coach turns emit a valid verdict. This is the convergence bar run-14 failed.

## Preconditions
1. Keepalive paused: `sudo systemctl stop llama-swap-keepalive.timer`
   (else gc revives on top of g31 → OOM). Restart after the run.
2. 31B route live + cold-load verified (AC-1 serve-check).
3. Coach slot served by `coach31` set (requesting `gemma4:31b` switches to it,
   evicting gc). Confirm `free -m` headroom before launch.
4. FalkorDB (graphiti) + dotnet fixtures reachable (per TASK-OPS-AOFENV) from
   wherever the run is launched.

## Command (task spec — from the Mac, langgraph harness)
```bash
GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
  OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-AOF \
    --fresh --model qwen36-workhorse --coach-model gemma4:31b \
    --task-timeout 4800 --sdk-timeout 3600 \
    2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-15-stdout.log
```

## Alternative (from the GB10, localhost)
Same env but `OPENAI_BASE_URL=http://localhost:9000/v1`. Note: ties up the box's
Coach slot for the whole run and needs the FEAT-AOF env deps present locally.

## What to capture
- `coach_turn_*.json` per turn: decision, char-by-channel counts, finish_reason.
- Convergence count: how many of N Coach turns emitted a valid fenced verdict.
- Net time-to-verdict per converged turn (AC-4 — dense is slower per token but
  may converge in far fewer tokens).
- Final wave status vs run-14's `TIMEOUT_BUDGET_EXHAUSTED`.

## Optional sub-experiments (per task notes)
- `--reasoning off` for the Coach (the run-14 ramble suggests less reasoning, not
  more, aids convergence; parser reads both channels per COACHBUDG01 → safe). To
  try: add `--reasoning off` to the `gemma4-31b` route cmd (one-line edit,
  hot-reloads) and re-probe / re-run.
- If 31B converges but is verbose: re-introduce **decisiveness-only** prompt
  guidance (NOT the run-14 self-check clause, the suspected loop cause).
- If 31B converges but too slow: try the smaller dense **12B QAT** (~7 GB, 12B
  active — still 3× the MoE) or distill (TASK-DATA-COACHHARVEST).
