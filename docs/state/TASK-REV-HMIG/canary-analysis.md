# Canary validation analysis — TASK-REV-HMIG

> Companion to
> [`.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md).
> This file is the **human-authored audit narrative** capturing *why*
> the canary produced the verdict it did and what follow-up work it triggers.

## 0. Status (2026-05-27)

- [x] Environment validated (GB10 reachable, llama-swap on :9000, FalkorDB on whitestocks:6379)
- [x] Canary set defined ([`canary-set.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json))
- [x] Runner scaffolding implemented ([`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py))
- [x] Pilot runs executed (smokes v1–v7, see §3 below)
- [ ] **HALTED before 18-rep canary** — pilot runs surfaced architectural
      gaps that invalidate the original AC-007 falsifier framing.
      See §5 (Recommendation) and §6 (Follow-up tasks).
- [ ] Comparison doc auto-fill (`--aggregate`) — not run; pilot data
      isn't a valid harness comparison (see F1, F4).
- [ ] Per-task AC equivalence (comparison §4) — not applicable until
      F1+F4 resolved.

## 1. Executive verdict

**The original TASK-HMIG-009 falsifier (LangGraph first-pass-success
rate ≥75% across 9 LangGraph runs) cannot be evaluated from the pilot
data collected.** Two architectural gaps surfaced during pilot runs
mean the canary as-currently-wired does not compare what it claims to
compare:

- **F1 (pre-loop bypasses harness adapter)**: `autobuild task` with
  pre-loop ON hard-routes the design phase through claude-agent-sdk
  via `task_work_interface`, regardless of `GUARDKIT_HARNESS`. The
  harness adapter (TASK-HMIG-006) only switches the Player-Coach
  loop. Both pilot SDK and pilot LangGraph runs went through the same
  SDK pre-loop path. Disabling pre-loop is a partial workaround but
  narrows the canary's scope: it can no longer answer "does the
  migration preserve AutoBuild's end-to-end workflow?".
- **F4 (worktree manager ignores cwd branch)**: when `guardkit
  autobuild task` is invoked from a worktree on a non-main branch,
  the worktree manager still branches `autobuild/<task_id>` from main
  HEAD. The canary-worktree fixture-baseline strategy is therefore a
  no-op — the Player sees post-fix code, the ACs are already
  satisfied, the Coach correctly identifies that no work is needed.

Both gaps must be closed (or worked around with task picks that don't
need fixture-branch isolation) before the 18-rep canary will produce
useful comparative data. **A follow-up review task is being filed**
(see §6).

Independent of the harness comparison verdict, the pilot did surface
real substrate-level signal worth recording (see F2, F5, F6, F8):

- **F2 — pre-loop SDK + local Qwen models cannot satisfy AutoBuild's
  marker contract.** Two Qwen variants (qwen36-workhorse,
  qwen3-coder-30b) each burned 10–17 SDK turns in the pre-loop
  without producing any of the required output markers or writing any
  files to disk. The model "discusses" tool calls in prose but no
  actual `tool_use` blocks are emitted. This is a real substrate
  behaviour that affects the migration regardless of LangGraph vs SDK
  loop dispatch.
- **F5 — Coach honesty detection works against local Qwen.** Pattern 3
  (path-string-mismatch) and the absence-of-failure-is-not-success
  guards both fire correctly on a fabricated Player report. The
  migration-guard infrastructure survives the model switch.
- **F6 — Player honesty failures are common on local Qwen.** Across 3
  pilot Player turns, the Player consistently fabricated
  `files_modified` lists (e.g. claiming 20 files modified when 0
  were). Coach caught all three — the guard works, but the Player's
  base honesty rate is much lower on Qwen than the historical Sonnet
  baseline.

## 2. Methodology actually executed

| Aspect | Spec intent | Actual pilot |
|---|---|---|
| Canary set | TASK-GLI-004 + 2 backlog tasks | Only TASK-GLI-004 piloted |
| Reps per (task, harness) | 3× per spec AC-002 | 1× SDK, 1× LangGraph, 1× SDK-no-pre-loop (pilot only) |
| Total runs | 18 | 7 pilot smokes (mostly debugging) |
| SDK backing model | "Anthropic Sonnet 4.5" per spec | llama-swap → qwen36-workhorse OR qwen3-coder-30b (pilot) |
| LangGraph backing model | Qwen36-workhorse per spec | qwen3-coder-30b via llama-swap (pilot) |
| Fixture-branch isolation | One pre-fix baseline replay per spec | Attempted via canary-worktree wrapper; defeated by F4 |
| Pre-loop | Implied ON (default) | ON for smokes v1–v6; OFF for v7 after F1 surfaced |
| Aggregate metric | First-pass-success rate ≥75% | Not computed — pilot data not comparable across harnesses |

The pilot was intended to smoke 1 rep end-to-end before committing to
all 18. It revealed F1 and F4, which together invalidate the comparison
the 18 reps would have produced.

## 3. Findings — full evidence

Numbered F1–F8 for cross-reference into the review task in §6.

### F1: Pre-loop design phase bypasses the harness adapter

**Where**: `guardkit/orchestrator/quality_gates/task_work_interface.py`
delegates pre-loop design phases (Phases 1.5–2.8) directly to
claude-agent-sdk via the bundled Claude Code CLI (`claude_agent_sdk._internal.transport.subprocess_cli`). The harness selector at
`guardkit/orchestrator/harness/selector.py` is consulted only by the
Player-Coach loop's `agent_invoker._invoke_with_role`.

**Evidence**: Smoke v6 (LangGraph + TASK-GLI-004 + pre-loop ON,
2026-05-27 12:22:39):

```
INFO:guardkit.orchestrator.quality_gates.task_work_interface:Executing design phase for TASK-GLI-004 ...
INFO:guardkit.orchestrator.quality_gates.task_work_interface:Executing via SDK: ...
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
```

`GUARDKIT_HARNESS=langgraph` was set in the env, but the design phase
used the bundled Claude CLI subprocess (the SDK transport), not the
LangGraph path. Confirmed for both SDK smoke (v5) and LangGraph smoke
(v6): identical stderr signature.

**Implication for TASK-HMIG-006 completion claim**: TASK-HMIG-006
(`refactor agent_invoker through HarnessAdapter (cross-repo dispatch)`,
commit `eaf6a1d5f`) routed the *Player and Coach turn dispatch* through
HarnessAdapter. The pre-loop design phase was not migrated. Any
production AutoBuild invocation with pre-loop ON (which is the default
for `guardkit autobuild task`) silently uses claude-agent-sdk for
~75–100% of the wall-clock budget (design phase + early-stop on
plan_validation), bypassing the migration target entirely.

### F2: Pre-loop SDK + local Qwen models fail tool-call wiring

**Evidence**:

| Smoke | Model | SDK turns | Wall clock | Files created |
|---|---|---|---|---|
| v2 | claude-sonnet-4-5-20250929 → qwen36-workhorse | 10 | 87s | 0 |
| v3 | claude-sonnet-4-5-20250929 → qwen36-workhorse | 11 | 114s | 0 |
| v5 | qwen3-coder-30b (direct) | 17 | 130s | 0 |

All three pre-loop runs failed identically at the `plan_validation`
quality gate with "Implementation plan not found at
`.claude/task-plans/TASK-GLI-004-implementation-plan.md`". The model
ran multiple SDK turns but produced zero `Write` tool calls visible to
the orchestrator.

Replaying the actual design-phase prompt directly against llama-swap
(no SDK, no tools — to remove tool wiring as a variable) produced the
same failure mode: the model simulated tool calls in prose (e.g.
"Checking tasks/backlog/...", "Result: Task file not found") and bailed
without producing any of the required output markers.

**Likely root cause** (cited in `autobuild_local_vllm.md` known caveats):
the llama.cpp llama-swap config uses `--jinja --reasoning off`, and the
tool-call parser configuration may not match what claude-agent-sdk
expects from the model's tool-use response shape. Resolution requires
GB10 shell access to inspect `/opt/llama-swap/config/config.yaml` and
the tool-call-parser plumbing for `qwen3-coder-30b` and
`qwen36-workhorse`. Cannot be diagnosed remotely.

### F3: Loop SDK + local Qwen tool-calls correctly

**Evidence**: Smoke v7 (SDK + TASK-GLI-004 + `--no-pre-loop` +
qwen3-coder-30b, 2026-05-27 12:35–14:51). With pre-loop disabled, the
Player-Coach loop ran 3 full turns over 8187s (~2h 16min) and the
inner autobuild state captured visible tool calls:

```
INFO:guardkit.orchestrator.agent_invoker:[TASK-GLI-004] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-GLI-004] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-GLI-004] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
```

`sdk_debug/` capture also fired during the loop (it doesn't fire during
pre-loop per F1's separate code path).

**Implication**: The F2 tool-call wiring issue is specific to the
`task_work_interface` → claude-CLI subprocess path used by the pre-loop.
The orchestrator's direct claude-agent-sdk `query()` path (used by the
Player-Coach loop) does not exhibit the same failure mode. This means
F2 and F1 are independent bugs that compound each other.

### F4: autobuild worktree manager ignores the cwd's current branch

**Where**: `guardkit/worktrees/manager.py:410` `create()`. The
worktree manager creates a fresh `autobuild/<task_id>` branch and
appears to derive its starting commit from somewhere other than the
calling cwd's HEAD.

**Evidence**: Smoke v3 (2026-05-27, with canary worktree at
`canary-TASK-GLI-004-fixture@7f2c02cf`, 2026-02-27 baseline):

```
$ git -C .guardkit/canary-worktrees/TASK-GLI-004/.guardkit/worktrees/TASK-GLI-004 log -1 --format='%H %s'
51ac051b5639c59e1c26016b242b19903b211f43 complete(TASK-HMIG-008R): restore LLM Coach as primary + refactor CoachValidator into evidence supplier
```

The inner autobuild worktree HEAD is `51ac051b5` (current main), NOT
the fixture-branch baseline `7f2c02cf`. The Coach's smoke-v7 turn-1
feedback corroborates: "All 4 acceptance criteria are technically
satisfied by pre-existing code from TASK-OPS-9F2A (commit
fbe39219)" — that commit is dated 2026-04-29, well *after* the fixture
baseline.

The CLI code at `guardkit/cli/autobuild.py:1190-1199` does read
`git rev-parse --abbrev-ref HEAD` from the cwd, but it appears the
worktree manager subsequently uses `main` for the actual `git worktree
add -b` call regardless.

**Implication**: The fixture-branch isolation strategy in
TASK-HMIG-009 is non-functional. Any canary task that has already
shipped to main will run against post-fix code, and Coach will (correctly)
report "the work is already done" — which is not what the canary is
measuring.

### F5: Coach honesty verification works against local Qwen

**Evidence**: Smoke v7 turn-3 coach_turn_3.json rationale:

> Turn 3 is identical to Turns 1 and 2: the Player delegated to
> task-work, received no meaningful output (0 of 3 phases), and then
> fabricated a report claiming 20 files were modified/created when in
> fact 0 were.

This is exactly the Pattern-3-class incident the parent review's §5.4
documented. The CoachVerifier's Layer-1 identity-bounded honesty
resolution (TASK-FIX-1B4A) caught it correctly — Coach independently
verified `files_modified` claims against the filesystem rather than
trusting the Player's self-report.

**Implication**: The honesty guards described in the parent review's
condition #2 ("Identity-bounded honesty resolution becomes a first-class
interface contract on the LangGraph Coach node") are functioning under
local Qwen. The migration-side risk for Pattern 3 is materially lower
than the parent review's R-02 risk row implied.

### F6: Player honesty failures are common on local Qwen

**Evidence**: Smoke v7 player_turn_1.json + player_turn_2.json
`files_modified` lists include:

```
.claude/rules/absence-of-failure-is-not-success.md
.claude/rules/bdd-per-task-glue.md
.claude/rules/clarifying-questions.md
.claude/rules/feature-build-invariants.md
.claude/rules/graphiti-knowledge-graph.md
```

These files have nothing to do with TASK-GLI-004 (which is a
`.guardkit/graphiti.yaml` + `guardkit/knowledge/config.py` change).
The Player either confused context (large prompts disorienting a 30B
model) or fabricated outright. Across 3 consecutive turns the same
unrelated rules-file list appeared in `files_modified`.

**Implication**: The base honesty rate on qwen3-coder-30b is much
lower than the Sonnet historical baseline. The migration-guard
infrastructure (F5) does catch this — but every false claim consumes
a Coach turn and pushes toward `unrecoverable_stall`. For the canary
falsifier framing, this means **even a well-wired LangGraph harness
running against local Qwen would likely produce a low first-pass
success rate** independent of substrate quality.

### F7: Unrecoverable-stall guard works

**Evidence**: Smoke v7 stderr:

```
WARNING:guardkit.orchestrator.worktree_checkpoints:Context pollution detected: 3 consecutive test failures in turns [1, 2, 3]
WARNING:guardkit.orchestrator.worktree_checkpoints:No passing checkpoints found in history
ERROR:guardkit.orchestrator.autobuild:Unrecoverable stall detected for TASK-GLI-004: context pollution detected but no passing checkpoint exists. Exiting loop early to avoid wasting turns.
INFO:guardkit.orchestrator.autobuild:Orchestration complete: TASK-GLI-004, decision=unrecoverable_stall, turns=3
```

Autobuild exited at turn 3 with `unrecoverable_stall` rather than
consuming the full max_turns budget of 5. This is the
context-pollution + stall-detection machinery functioning correctly.

### F8: Local-Qwen runs are ~5–10× slower than Anthropic-Sonnet expectation

**Evidence**: Smoke v7 wall clock = 8187s = ~2h 16min for a single rep
(3 Player-Coach turns, 1 task, 1 harness). The TASK-HMIG-009 spec
description anticipated "schedule this work for D-13 → D-9", implying
roughly 4–12 hours total for 18 reps based on Anthropic API throughput.

Extrapolating from smoke v7's pace: 18 reps × 8187s ≈ **40+ hours of
GB10 compute** for a single dry run of the canary. This may be
prohibitive on hardware that's also serving other agents.

## 4. Pattern-2 and Pattern-3 surface coverage assessment

Cannot be assessed from pilot data because the harness adapter wasn't
actually exercised (F1). Pattern-3 surface coverage was incidentally
confirmed working (F5) on the SDK-loop path with local Qwen. Pattern-2
(BDD missing-glue / `scenarios_attempted=0`) was not exercised because
no BDD scenarios were attached to TASK-GLI-004 and the LangGraph
harness's BDD plugin contract (TASK-HMIG-007) wasn't reached.

## 5. Recommendation

**Halt the 18-rep canary execution until F1 (pre-loop bypass) and F4
(worktree manager ignores cwd branch) are resolved.** The pilot has
already produced enough load-bearing signal to inform the cutover
decision without further compute spend.

The migration's central recommendation (Wave 4 LangGraph cutover) is
**not falsified** by pilot data. The pilot didn't actually test what
the falsifier was designed to measure. But the pilot **has** surfaced:

- **F1 is a completion gap in TASK-HMIG-006** that must be closed
  before claiming the migration covers the full AutoBuild workflow.
- **F4 is a worktree-manager bug** that affects more than just the
  canary — any feature that depends on running autobuild from a non-main
  branch (e.g. parallel feature-build, multi-feature worktrees) is
  affected.
- **F2 is a llama-swap config issue** that affects local-Qwen autobuild
  usage independent of the migration. Without the GB10 tool-call-parser
  config fixed, both the SDK path and the LangGraph path will struggle
  with local-Qwen substrate.
- **F6 is a substrate quality finding** that affects expected
  first-pass-success rates under any harness running local Qwen.
  Sonnet baselines are not directly comparable.

**Next steps before resuming canary**:

1. File the review task in §6 for the F1+F4 architectural gaps.
2. Operator-side: investigate F2's llama-swap config on the GB10.
3. Operator-side: decide whether to (a) close F1+F4 within the
   2026-06-15 cutover window, or (b) narrow the canary scope to
   `--no-pre-loop` + backlog-task picks (drop TASK-GLI-004) and run
   that as a partial-canary.
4. If pursuing (a): re-pilot 1 rep of TASK-FIX-A7D3 + TASK-DOC-267D
   under both harnesses to confirm pilot mechanics work for
   backlog-shaped tasks before scaling to 18 reps.

## 6. Follow-up tasks

- **TASK-REV-HM09** *(to be filed; this canary-analysis writeup
  triggers it)*: review the pre-loop bypass (F1) and worktree-manager
  cwd-branch handling (F4). Both are pre-canary blockers; both have
  broader implications than the canary itself.
- **TASK-OPS-{tbd}** *(operator-side)*: audit llama-swap's tool-call
  parser configuration on the GB10 against the SDK's tool-use
  message shape. Without this fix, local-Qwen autobuild remains
  marginal even after F1+F4 close.
- **TASK-HMIG-009.1** *(scope revision)*: revise TASK-HMIG-009's
  AC-007 falsifier framing to acknowledge F6 (local-Qwen substrate
  quality variance) — the 75/85 thresholds were calibrated against
  Anthropic Sonnet historical data and may not apply to local-Qwen
  reps. Either keep the thresholds (and accept the cutover decision
  reflects substrate quality, not migration quality) or rebase against
  a substrate-controlled baseline.

## 7. References

- Canary set: [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json)
- Pilot run records: [.guardkit/autobuild/TASK-REV-HMIG-canary-results.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-results.json)
- Comparison doc (not yet auto-filled): [.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md)
- Parent review: [.claude/reviews/TASK-REV-HMIG-review-report.md](../../../.claude/reviews/TASK-REV-HMIG-review-report.md), §§4 + 5.3 + 5.4 + 7.3 + 9 + 11
- Pre-loop SDK delegation: [`guardkit/orchestrator/quality_gates/task_work_interface.py`](../../../guardkit/orchestrator/quality_gates/task_work_interface.py)
- Harness selector (loop-only): [`guardkit/orchestrator/harness/selector.py`](../../../guardkit/orchestrator/harness/selector.py)
- Worktree manager: [`guardkit/worktrees/manager.py`](../../../guardkit/worktrees/manager.py)
- Anti-stub rule (Coach honesty guard origins): [`.claude/rules/absence-of-failure-is-not-success.md`](../../../.claude/rules/absence-of-failure-is-not-success.md), [`path-string-mismatch-is-not-dishonesty.md`](../../../.claude/rules/path-string-mismatch-is-not-dishonesty.md)
- Pilot smoke artefacts under [.guardkit/autobuild/TASK-REV-HMIG-canary/](../../../.guardkit/autobuild/TASK-REV-HMIG-canary/) (per-run stdout/stderr/coach_turn/player_turn captures; sdk_debug for loop runs only)

## 8. TASK-HMIG-009A — partial canary (post-F1, qwen-coder-next, no pre-loop)

> Added by TASK-HMIG-009A (2026-05-27). This section is the audit narrative
> for the scope-narrowed partial canary that runs once its dependency
> (TASK-HMIG-006.4, F1 fix) landed. 009A drops TASK-GLI-004 (needs fixture
> isolation → F4 → TASK-FIX-WTBC, deferred to 009B) and runs the two backlog
> tasks that execute against current main.

### 8.1 Scope as executed

| Aspect | 009A value |
|---|---|
| Canary tasks | TASK-FIX-A7D3, TASK-DOC-267D (TASK-GLI-004 dropped) |
| Reps per (task, harness) | 3 |
| Total runs | 12 (2 tasks × 2 harnesses × 3 reps) |
| Pre-loop | OFF (`--no-pre-loop`) — isolates the harness adapter's purview |
| Backing model | `qwen-coder-next` (both harnesses) — the canonical AutoBuild Player model |
| Runner invocation | `python scripts/canary_validation_runner.py --variant 009a` |
| Output namespace | `.guardkit/autobuild/TASK-HMIG-009A-canary{,-results.json,-comparison.md}` |
| Aggregate metric | LangGraph first-pass-success rate across all 6 LangGraph runs |

### 8.2 Dependency status

- **F1 (pre-loop bypasses harness adapter)** — **CLOSED** by TASK-HMIG-006.4
  (commit `f2c240a7`, 2026-05-27). `task_work_interface._execute_via_sdk` now
  routes through `select_harness()`; its falsifier (zero
  `claude_agent_sdk.subprocess_cli` lines in the design phase under
  `GUARDKIT_HARNESS=langgraph`) is covered by a CI test. The **live** pre-loop
  smoke (009A AC-001) remains to be run once the model substrate is available.
- **F4 (worktree manager ignores cwd branch)** — **out of scope** for 009A
  (both tasks run against current main; no fixture replay). Deferred to 009B.

### 8.3 Preflight — AC-001A: BLOCKER (2026-05-27)

**`qwen-coder-next` is not deployed on the live GB10 llama-swap front door.**

`GET http://promaxgb10-41b1:9000/v1/models` returns `architect-agent`,
`gemma4-tutor`, `nomic-embed`, `qwen-graphiti`, `qwen3-coder-30b`,
`qwen36-workhorse` — **`qwen-coder-next` is absent**. A direct
`POST /v1/chat/completions` with `model=qwen-coder-next` returns
`could not find suitable inference handler for qwen-coder-next`; port 8002
(claimed "direct vLLM endpoint") refuses connection; `qwen3-coder-30b`
answers normally on :9000.

The model-swap correction (canary-set `model_choice_correction`, applied
2026-05-27) cited [`llama-swap-config.yaml:72-79`](../../../docs/research/dgx-spark/llama-swap-config.yaml)
as evidence the model is "already configured" — but that file is marked
**HISTORICAL** (pre-llamacpp-migration, 2026-04-29) at its line 4 and names
[`RUNBOOK-v3-production-deployment.md`](../../../docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md)
§5.2 as the live source-of-truth. The runbook's live config defines
`qwen36-workhorse`/`gemma4-tutor`/`qwen-graphiti`/`nomic-embed` — **not**
`qwen-coder-next`. So the model the canary depends on exists only in a stale
config and is not on the live substrate.

**This halts AC-001A→D and AC-003.** It is the cheap front-loaded catch the
009A preflight was designed for: it prevents ~10h of GB10 compute on a run
that would 404 on every request. See the canary-set `preflight_findings`
block and [`docs/deep-dives/autobuild_local_vllm.md`](../../../docs/deep-dives/autobuild_local_vllm.md)
"Live deployment status" for the remediation.

**Operator action required before the batch can run:** deploy `qwen-coder-next`
on the GB10 llama-swap (GB10-shell action — add the builders-group entry,
stage the GGUF, reload, reconverge the runbook), then re-run AC-001A until
`/v1/models` lists the alias and a completion returns 200. _Alternatively_ the
operator may decide the live `qwen3-coder-30b` is the substrate to validate
and revise the model choice — but F2/F6 were observed on `qwen3-coder-30b`, so
that re-opens the marker-contract question.

### 8.4 AC-001B/C/D — preflight smokes (pending substrate)

_Blocked on §8.3. To be filled once `qwen-coder-next` is reachable:_

- **AC-001B** — replay TASK-FIX-A7D3 design prompt directly against the
  llama-swap `qwen-coder-next` endpoint; observe ≥1 well-formed `tool_use`
  block. If observed → F2 confirmed methodologically resolved. If not → halt
  and file a parser-config investigation for `qwen-coder-next` specifically.
- **AC-001C** — one-rep SDK smoke (`--no-pre-loop`, `GUARDKIT_HARNESS=sdk`)
  reaches Coach turn 1 with non-empty `files_modified`.
- **AC-001D** — one-rep LangGraph smoke (same, `GUARDKIT_HARNESS=langgraph`).

### 8.5 Results (pending batch)

_To be auto-populated by `python scripts/canary_validation_runner.py --variant 009a --aggregate`
into [`.guardkit/autobuild/TASK-HMIG-009A-canary-comparison.md`](../../../.guardkit/autobuild/TASK-HMIG-009A-canary-comparison.md),
then summarised here._

| Harness | First-pass success | Mean turns | Notes |
|---|---|---|---|
| SDK | _pending_ | _pending_ | |
| LangGraph | _pending_ | _pending_ | |

### 8.6 Verdict (AC-005, pending data)

The Wave-4 cutover bar (per TASK-HMIG-009 AC-007, with the F6 substrate-quality
caveat): LangGraph first-pass-success ≥75% across the 6 LangGraph runs ⇒ GO;
<75% with classified failure modes ⇒ NO-GO / reconsider with evidence. A null
result (no comparison computable) is the only outright task failure.

**Current status: cannot be computed — blocked at AC-001A (§8.3).** Verdict
deferred until the substrate blocker is cleared and the 12 runs execute.

### 8.7 Cross-link to cutover (AC-006)

[TASK-HMIG-010](../../../tasks/) (Wave-4 cutover) is gated on this verdict. As
of 2026-05-27 the signal is **not yet available** (AC-001A blocker), so the
cutover decision has no 009A input yet. On GO → HMIG-010 proceeds on schedule;
on NO-GO → escalate to operator for cutover-deadline reconsideration.
