# Run-15 / Run-16 / Run-17 recipe — AC-3 falsifier (31B as Coach)

> ## ▶ RUN-18 (current) — minimal fleet + ctx 98304
> Run-17 (minimal fleet, ctx 65536) cleared the OOM (F23A) but hit **F20 context
> overflow**: the 41-file Player payload made a **66,687-token** Coach prompt >
> the 65536 cap (HTTP 400). Fix for run-18: **g31 `--ctx-size` 65536 → 98304**
> (covers it with margin; memory-safe now that qg is gone — verified GPU ~50 GB,
> ~62 GB headroom). Run-18 command is identical to run-17 below (just change the
> log filename to `run-18-stdout.log`). Keepalive stays OFF; `--no-context` stays.
> If a stochastic 71-file outlier payload (~115 K tokens) re-triggers F20, the
> real fix is capping the Coach prompt (code), not more ctx.
>
> ## ▶ RUN-17 — minimal GPU fleet, keep the 31B
> Runs 15+16 OOM'd because the **coach31 fleet's GPU/unified memory** (esp.
> `qwen-graphiti` ~25.6 GB) left no headroom for g31's KV on a big Coach prompt
> (run-16: 71-file payload). Fix for run-17 (operator chose: prove the 31B first,
> get evals before trying the 12B):
> - **`coach31` set trimmed to `qw & g31`** (Player + Coach only) — frees ~26 GB.
>   Verified on the GB10: GPU ~49 GB, ~62 GB headroom for g31 KV growth.
> - **MUST add `--no-context`** so the orchestrator skips Graphiti (qg/ne) — both
>   retrieval and per-turn writes are gated by `enable_context`, so no set thrash.
> - g31 ctx 65536 (sufficient for IA03-class prompts); keepalive OFF.
>
> ```bash
> GUARDKIT_HARNESS=langgraph \
>   OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
>   OPENAI_API_KEY=llama-swap-local-key \
>   guardkit autobuild feature FEAT-AOF \
>     --fresh --model qwen36-workhorse --coach-model gemma4:31b \
>     --no-context \
>     --task-timeout 4800 --sdk-timeout 3600 \
>     2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-17-stdout.log
> ```
> If run-17 completes ≥1 Coach turn with a valid verdict AND finishes the wave,
> AC-3 is met and we have 31B evals to compare a later 12B-QAT run against.



> **Run-15 ran 2026-06-08: F24 BROKEN** (turn-1 real verdict) but **turn-2
> OOM-killed (F23A)**. See [run-15-artifacts GB10 resolution](../../TASK-REV-HMIG/run-15-artifacts/README.md).
> This recipe now drives **run-16** (the re-run with the OOM fix).
>
> **Run-16 deltas vs run-15:**
> 1. g31 route `--ctx-size 98304 → 65536` (already applied; cuts KV ~1/3).
> 2. **Quiesce the GB10** before launching (the bigger lever — see Preconditions):
>    close VS Code + firefox; `docker stop vllm-docling vllm-granite-vision
>    vllm-granite-vision-3-3-2b 2>/dev/null`; stop the forge autobuild runner;
>    avoid a heavy GB10-side session during the run.
> 3. Keepalive stays OFF; check `free -g` shows comfortable headroom after g31
>    loads on turn 1. If it still OOMs → ctx 49152 or the 12B dense QAT.

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
