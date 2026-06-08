# Run-15 autobuild artifacts snapshot

> **Purpose**: snapshot the `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`
> artifacts from run 15 to a tracked path so the GB10 Claude session can
> pick them up for diagnosis. Same pattern as
> [`../run-13-artifacts/`](../run-13-artifacts/) and
> [`../run-14-artifacts/`](../run-14-artifacts/).
>
> **Source**: live worktree artifacts copied 2026-06-08T20:25Z from
> `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`.
> **Run log**: [`autobuild-FEAT-AOF-run-15.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-15.md)
> (committed in the same change as this snapshot).

## 🎉 BREAKTHROUGH — Turn 1 Coach emitted a real, schema-valid verdict (first time in 15 runs)

Open [`TASK-FIX-IA03/coach_turn_1.json`](TASK-FIX-IA03/coach_turn_1.json) — it
contains a **real Coach verdict**, NOT a COACHSF01 synthetic-feedback
fallback. No `coach_primary_synthetic_feedback: true` flag.

```json
{
  "task_id": "TASK-FIX-IA03",
  "turn": 1,
  "decision": "feedback",
  "issues": [{
    "type": "test_failure",
    "severity": "critical",
    "description": "The claimed test file `tests/unit/test_doc_level_constraint.py` does not exist on disk.",
    "requirement": "Add test coverage for the filtering logic",
    "suggestion": "Actually create and run the tests claimed in the report."
  }],
  "rationale": "The Player claimed to have implemented and verified the requirements using a specific test file, but that file is missing from the filesystem. This is a critical honesty discrepancy and prevents verification of the implementation."
}
```

This is **gemma4-coach actually doing the Coach job**:
- Schema-valid fenced JSON (required fields `task_id`, `turn`, `decision` all present)
- Substantive honesty-discrepancy detection (caught a real Player lie)
- Concrete actionable feedback (Player must actually create the test file)
- Player turn-2 acted on the feedback: created the test file + 62 modifications, independent tests passed (line 624: `Independent tests passed in 4.2s`)

**Two changes landed between run 14 and run 15** (one or both is the
cause of the breakthrough):

1. **Model switched from `gemma4:26b` to `gemma4:31b`** — note the run-15
   log references `model='openai:gemma4:31b'` ([line 621, 629](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-15.md#L621)).
   The larger model appears to handle the structured-output contract
   substantially better.
2. **Coach SDK timeout was set to 3600s via CLI override** ([line 587](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-15.md#L587)):
   `SDK timeout: 3600s (CLI override, skipping dynamic calculation)`.

Even with the larger budget, **turn 1 Coach was efficient** — emitted
in ~10 min vs the 21-45 min seen on 26b. The larger model is faster at
converging on the verdict, not just more reliable.

## ❌ Turn 2 failed with F23-style substrate Connection error on the new model

Coach emitted on turn 1 → Player produced turn-2 with substantive
recovery (62 modified, including the missing test file the Coach
flagged) → independent tests passed → **turn-2 Coach hit HTTP 502 Bad
Gateway** ([line 618](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-15.md#L618))
and then `Connection error` ([line 621, 629](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-15.md#L621)).

```
HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 502 Bad Gateway"
ERROR: SDK coach test execution failed (error_class=LangGraphHarnessError):
  LangGraphHarness: agent.ainvoke failed for role='coach_test' model='openai:gemma4:31b': Connection error.
WARNING: SDK test execution failed, falling back to subprocess.
INFO: Independent tests passed in 4.2s
...
Coach failed: SDK invocation failed for coach (LangGraphHarnessError):
  LangGraphHarness: agent.ainvoke failed for role='coach' model='openai:gemma4:31b': Connection error.
```

This is **F23 recurring on gemma4:31b**. F23 was previously classified
as F23D (transient) in run 12 on gemma4:26b. Run 15 shows it firing
again on the larger model — could be:

- **F23A (substrate-sizing on the bigger model)** — gemma4:31b has a
  larger weight footprint than 26b; the KV-cache + weights combination
  may have pushed past the GB10 RAM/VRAM envelope when Coach prompt
  gets large
- **F23C (llama.cpp instability under the larger model)** — bigger
  model = more compute per token = longer single-call duration =
  more opportunity for connection-level issues
- **F23B (llama-swap eviction race)** — if 31b takes a different swap
  slot than 26b, the eviction policy may differ
- **F23D (transient again)** — just a coincidence, single-event blip

The four hypotheses + forensic commands from the original run-11 F23
handoff at
[`../run-11-f23-forensics-handoff.md`](../run-11-f23-forensics-handoff.md) §3
are reusable here — just bump the time window to 19:21-19:26 UTC for
the run-15 502 window.

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Wave 1 / IA03 start | 19:01:31 | task budget 4800s (per-task frontmatter override) |
| **Turn 1 Player** | → 19:07:00 (~329s) | ✓ 30 created, 0 modified, 1 test claimed (but missing!) |
| Turn 1 test-orchestrator | SPECHANG 150s, contained by SPECCOCH01 | ✓ as designed |
| **Turn 1 Coach** | → 19:17:09 (~10 min) | **✓ REAL VERDICT** — `decision: feedback`, caught Player honesty discrepancy |
| **Turn 2 Player** | → 19:18:50 (~100s) | ✓ 0 created, 62 modified — created the missing test file + recovery |
| Turn 2 test-orchestrator | SPECHANG, contained | ✓ as designed |
| Coach independent tests | subprocess fallback after 502 | ✓ passed in 4.2s |
| **Turn 2 Coach** | → 19:25:56 | **✗ F23-style HTTP 502 → Connection error** |
| FEATURE | FAILED | total 23m 40s |

## What this means for TASK-HMIG-013 AC-006 / AC-009

**AC-009 surface is now CONFIRMED operational**: gemma4 + the right
substrate config + the Path 1B prompt tightening + the model size
upgrade → real fenced-JSON Coach verdicts with all required fields,
caught a real honesty discrepancy. The COACHBUDG01 parser, COACHSF01
safety net, and feedback→Player loop all worked exactly as designed.

**AC-006 (≥95% emission rate across ≥6 turns)** is not yet met — but
the gap shape changed completely. Before run 15: structured-emission
unreliability under gemma4:26b. After run 15: substrate-stability
question under gemma4:31b. These are different problems.

## Diagnostic hypotheses for the GB10 session

1. **The model change to gemma4:31b is the load-bearing improvement.**
   Compare run-14 (26b, 49,720-char reasoning blowup, no fenced JSON)
   vs run-15 (31b, terse + valid verdict in ~10 min). Strongly suggests
   model size, not prompt or grammar, is the lever.

2. **The 31b model has a different substrate-stability envelope.**
   Turn 2's 502 may not be transient. Verify with run-11's F23
   forensics recipe (`dmesg | grep oom`, `journalctl -u llama-swap`,
   `tailscale status` for the **19:21-19:26 UTC** window). Action depends
   on which F23 sub-class fires:
   - F23A (OOM): reduce 31b n_ctx OR accept that 31b can't survive
     turn-2 Coach payload on the current GB10
   - F23B (eviction): pin 31b TTL=0, tune keepalive
   - F23C (crash): file substrate-escalation, AC-007 path

3. **The "test_doc_level_constraint.py does not exist" Coach finding may
   itself be wrong.** Verify by checking the run-15 turn-1
   [`task_work_results.json`](TASK-FIX-IA03/task_work_results.json) and
   [`player_turn_1.json`](TASK-FIX-IA03/player_turn_1.json) for what
   Player ACTUALLY claimed vs what Coach saw on disk. If Player's claim
   was valid but Coach hallucinated, this is the
   [`path-string-mismatch-is-not-dishonesty.md`](../../../.claude/rules/path-string-mismatch-is-not-dishonesty.md)
   shape (false-red false-fail) — different bug class.

4. **The COACHSCHEMA + 31b combination may have over-corrected toward
   issuing `feedback` decisions.** Coach emitted feedback on turn 1
   even though Player legitimately succeeded on much of the work.
   Whether the Coach is being TOO strict (issuing feedback when approve
   was warranted) is a meta-question worth checking once enough turns
   accumulate.

## What's in this snapshot

| File | Size | What | Useful for |
|---|---:|---|---|
| **`coach_turn_1.json`** | **668 B** | **REAL Coach verdict — schema-valid fenced JSON** | The breakthrough datapoint |
| `coach_feedback_for_turn_2.json` | 450 B | Feedback bundled for turn-2 Player | What turn-2 Player saw as input |
| `player_turn_1.json` | 6654 B | Coach input — turn-1 Player output | What Coach validated (the "missing test file" claim) |
| `player_turn_2.json` | 9838 B | Coach input — turn-2 Player output | The recovery (62 modifications) |
| `turn_state_turn_1.json` | 3751 B | Orchestrator's post-turn-1 snapshot | State record incl. Coach verdict |
| `turn_state_turn_2.json` | 6912 B | Orchestrator's post-turn-2 snapshot | State record incl. Coach error |
| `task_work_results.json` | 12397 B | Player's enriched task-work output | Specialist + Player full state |
| `specialist_results.json` | 540 B | test-orchestrator SPECHANG (contained both turns) | Specialist failure mode |
| `checkpoints.json` | 401 B | Per-turn checkpoint pointers | Recovery lineage |
| `turn_context.json` | 763 B | Per-thread context loader state | Graphiti / loader inspection |
| `state_transitions.json` | 708 B | state_bridge mutations log | Ghost-path filter / state-bridge inspection |

## What's NOT in this snapshot

- **`coach_turn_2.json`** — doesn't exist. Turn-2 Coach hit Connection
  error before emitting. This is the run-11-F23 shape recurring.
- The full Coach LLM bodies. The orchestrator records the verdict
  fenced block but not the surrounding reasoning_content. Full bodies
  in **llama-swap / llama.cpp logs on `promaxgb10-41b1`** at:
  - **Turn 1 Coach (success)**: 2026-06-08T19:07:00 → 19:17:09 UTC
  - **Turn 2 Coach (502 failure)**: 2026-06-08T19:21:20 → 19:25:56 UTC

## Cross-reference

- **Run-11 F23 forensics recipe** (reusable for this run's 502):
  [`../run-11-f23-forensics-handoff.md`](../run-11-f23-forensics-handoff.md) §3
- **Run-13 grammar no-op finding**:
  [`../run-13-artifacts/README.md`](../run-13-artifacts/README.md)
- **Run-14 Path-1B prompt-tightening evidence**:
  [`../run-14-artifacts/README.md`](../run-14-artifacts/README.md) —
  Path 1B alone (on gemma4:26b) was insufficient; 31b appears to be
  what made the difference
- **F24 paragraph** in
  [`../feature-run-analysis.md`](../feature-run-analysis.md) §6 — needs
  status update post-run-15 to record this breakthrough
- **TASK-HMIG-013 AC-007 (escalation path)** — `nemotron-3-super:120b-a12b`
  was the planned escalation. Run-15 evidence suggests the lighter
  escalation step (gemma4:26b → 31b) may have already done much of the
  work; the cutover decision now hinges on whether the F23-on-31b
  substrate issue is transient or systemic.

## ✅ RESOLVED on the GB10 (2026-06-08) — turn-2 502 is **F23A (global OOM)**

The GB10 session (TASK-OPS-COACH31B) discriminated the run-15 turn-2 502 against
the four hypotheses in the commit message. **It is F23A — substrate sizing /
global OOM.** Decisive evidence from the GB10 kernel + llama-swap logs (which the
Mac session cannot see):

**1. llama-swap proxy log** (`/opt/llama-swap/logs/llama-swap.log`):
```
[WARN] non-200 response ... status=502, path=/v1/responses
[INFO] Request 100.111.236.109 "POST /v1/responses HTTP/1.1" 502 0 ... 4m25.5s
[WARN] matrix: running gemma4-31b exited: [gemma4-31b] shutdown
```
The 502s are `dial tcp 127.0.0.1:5801: connect: connection refused` — i.e. the
**gemma4-31b llama-server (port 5801) had died**, so the proxy had nothing to
forward to. The only matrix set-switches in the log are the GB10 session's own
AC-2 warm-loads (restore-to-gc, then the Mac run's turn-1 g31 load) — **no
eviction during the run → NOT F23B**, and the keepalive timer was confirmed
**OFF** for the whole run (no `llama-swap-keepalive.service` runs in the window).

**2. Kernel OOM-killer** (`journalctl -k`, 20:25:47–20:25:49 BST):
```
forge invoked oom-killer ... constraint=CONSTRAINT_NONE ... global_oom
Out of memory: Killed process 3007736 (llama-server)
   total-vm:109300624kB, anon-rss:28703536kB   ← gemma4-31b on :5801, ~28.7 GB
llama-swap.service: Failed with result 'oom-kill'
NVRM: ... Out of memory [NV_ERR_NO_MEMORY]      (unified memory exhausted)
```
The kill (20:25:49 BST) lands **7 s before** the orchestrator recorded the
turn-2 Coach `error` (20:25:56 BST / 19:25:56 UTC). Cause and effect confirmed.

**3. Why it OOM'd:** the OOM process table shows the GB10 was running, at once,
the model fleet (g31 ~28.7 GB + qw + qg + ne) **plus** dockerd + a vLLM container
(`python3` under a `docker-*.scope`) + the `forge` runner + a large VS Code (many
`code`/`node` procs) + firefox + the GB10-side session. The dense 31B's KV growth
on the turn-2 Coach prompt (the larger `player_turn_2.json`) tipped total memory
past the ~121 GB ceiling → kernel killed the biggest process (g31). Same shape as
run-11 F23A, now on the bigger model — exactly the `§9.4 freeze-near-the-ceiling`
hazard the route comment warned about.

### What this means for the run-15 verdict
- **F24 (verdict-emission wall) is BROKEN by the substrate swap.** Turn-1 proves
  it: a real, schema-valid Coach verdict that independently caught a Player
  honesty discrepancy (claimed test file absent on disk), `coach_primary_synthetic_feedback`
  absent. This matches the AC-2 single-shot prediction (the dense 31B converges
  and emits valid verdicts; the MoE spiralled). **The model swap (26B-A4B MoE →
  31B dense), not prompt/grammar, is the load-bearing fix** — consistent with
  runs 12–14 ruling out grammar (Path 1A), prompt (Path 1B), and more time.
- **The remaining blocker is a DIFFERENT, narrower problem: F23A memory sizing**,
  not structured-emission. The gap shape changed (the commit's AC-006/AC-009
  note is correct), and F23A is the more tractable, closer-to-cutover problem.

### Fix applied (GB10, 2026-06-08) + run-16 recipe
- **Config:** `gemma4-31b` route `--ctx-size 98304 → 65536` (task pre-authorised:
  "if the cold load OOMs, drop to 65536"). Hot-reloaded. Backup:
  `config.yaml.bak-2026-06-08-pre-coach31b-ctx65k`. Cuts g31 KV ~1/3.
- **Before run-16, QUIESCE the GB10** (the bigger lever — ctx alone may not
  clear a 28.7 GB process under this load): close desktop GUI apps (VS Code,
  firefox), stop docker vLLM containers (`docker stop vllm-docling
  vllm-granite-vision*`), stop the `forge` autobuild runner, and avoid a heavy
  GB10-side session during the run. (Run-11 F23A recipe.)
- **Keep the keepalive timer OFF** for run-16 (as in run-15).
- If 65536 + quiesce still OOMs → drop to 49152, or fall to the **12B dense QAT**
  (~7 GB, 12B active — still 3× the MoE) per the TASK-OPS-COACH31B escalation.
- **AC-3 status:** the convergence/F24 bar is met on turn 1; the "≥4 turns,
  ≥80% valid" bar was not reached because the OOM ended the run at turn 2. Re-run
  (run-16) with the fix to complete AC-3.
