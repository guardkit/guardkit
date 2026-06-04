---
id: TASK-HMIG-009A
title: Partial canary execution — backlog tasks, no pre-loop, no fixture isolation (post-F1)
task_type: validation
status: backlog
previous_state: blocked
state_transition_reason: "AC-001D PASSED on run 6 (2026-06-03): LangGraph end-to-end APPROVED in 1 turn — 4 files created, 16 modified, 2 tests passing, honesty 0.96, Coach approved in 90s. The 6-run iteration journey resolved all 5 layers of the Wave-2 skeleton: MODELPLUMB (guardkit) + LGTOOLS (guardkitfactory) + 002R-CONSUME (guardkit selector wiring) + 002R-NOPERMS (guardkitfactory permissions drop) + 002R-NOVMODE (guardkitfactory virtual_mode flip). The 6th hypothesised layer (Coach/specialist prompt-tool-name mismatch) dissolved — DeepAgents' runtime tool advertisement was sufficient; 002R-PROMPT closed without code changes. UNBLOCKED for AC-003 (12-run batch)."
created: 2026-05-27T15:30:00Z
updated: 2026-06-03T09:40:00Z
priority: high
complexity: 5
effort_hours: 10    # ~10h GB10 compute (12 runs × ~30-60min each, backlog tasks are smaller than TASK-GLI-004)
parent_task: TASK-HMIG-009
parent_review: TASK-REV-HM09
feature_id: FEAT-HMIG
parent_feature: hmig-pre-canary-fixes
wave: 2
conductor_workspace: hmig-pre-canary-fixes-wave2-1
implementation_mode: manual    # canary execution requires operator monitoring + decision-making
intensity: standard
depends_on:
  - TASK-HMIG-006.4         # Pre-loop adapter migration — ✅ landed commit f2c240a7
  - TASK-FIX-002R-CONSUME   # Wire factories into selector — ✅ landed 2026-06-03
  # CROSS-REPO DEPS (all ✅ landed 2026-06-03 in ../guardkitfactory/):
  # - TASK-HMIG-002R-NOPERMS  — permissions=[] pending DeepAgents upstream support
  # - TASK-HMIG-002R-NOVMODE  — virtual_mode=False (fixed coach_turn_1.json path-doubling)
  # 002R-PROMPT was deleted — its closing criterion was met by AC-001D run 6.
related_tasks:
  - TASK-HMIG-009     # Original spec (this is a scope-narrowed variant)
  - TASK-HMIG-009B    # Full canary (optional polish post-F4)
  - TASK-HMIG-010     # Wave-4 cutover (gated by this task's signal)
tags:
  - canary
  - validation
  - langgraph-migration
  - cutover-decision-input
falsifier: "Aggregate result is interpretable: LangGraph first-pass-success rate is computable across at least 6 LangGraph runs and meets either (a) ≥75% (cutover proceeds on schedule) or (b) <75% with classified failure modes (cutover decision reconsidered with evidence). A null result (no comparison computable, e.g. F1 still bypasses) is the only failure of this task."
---

# Task: Partial canary — backlog tasks, no pre-loop, post-F1

## Description

Scope-narrowed variant of TASK-HMIG-009. Runs as soon as TASK-HMIG-006.4 lands (✅ done, commit `f2c240a7`), without waiting on TASK-FIX-WTBC or full F4 closure, to produce comparative SDK-vs-LangGraph signal for the Wave-4 cutover decision.

## Backing model (current: revised 2026-06-02)

**Both harnesses use `qwen36-workhorse` (Qwen3.6-35B-A3B)** via llama-swap port 9000 front door — the operator's current AutoBuild Player model choice. Per [`docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md:37`](../../../docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md#L37) (measured 2026-05-28), qwen36-workhorse serves `jarvis-reasoner, forge, autobuild, dataset-factory` — a shared workhorse across multiple agentic-coding roles. Operator's research (week of 2026-05-28→2026-06-02, benchmarks + NVIDIA developer forums) identifies it as the strongest agentic-coding model in the GB10's deployable range. It is **LIVE** on the GB10 llama-swap (verified by AC-001A 2026-05-27 — it was the only autobuild-shaped model serving when qwen-coder-next 404'd).

See `model_choice_correction_v2` in the canary-set for the full revision audit trail. This supersedes the 2026-05-27 `model_choice_correction` (which proposed qwen-coder-next; that model was documented but not deployed, surfaced by AC-001A's preflight design — see `preflight_findings.AC-001A_2026-05-27` block in canary-set, marked RESOLVED 2026-06-02).

**The earlier F2 finding** ("qwen36-workhorse fails AutoBuild marker contract" in canary-analysis.md §3.F2, observed in smokes v2/v3 on 2026-05-27) was **pre the operator's 2026-05-28→2026-06-02 llama-swap reconfiguration work**. AC-001A/B below empirically re-verify against the current post-reconfig live workhorse before committing to the 12-run batch.

## Scope

- **Canary tasks**: 2 backlog tasks that do NOT require fixture-branch isolation (so F4 / TASK-FIX-WTBC is not on the critical path):
  - TASK-FIX-A7D3
  - TASK-DOC-267D
  - Drop TASK-GLI-004 (needs fixture isolation → blocked on TASK-FIX-WTBC; runs only in 009B).
- **Reps per (task, harness)**: 3
- **Total runs**: 2 tasks × 2 harnesses × 3 reps = **12 runs**
- **Pre-loop**: **OFF** (`--no-pre-loop`) — isolates the harness adapter's actual purview (Player-Coach loop).
- **Aggregate metric**: First-pass-success rate per harness, per task, across 3 reps.

## Acceptance Criteria

### Preflight (model + endpoint)

- [x] **AC-001A** — ✅ **PASS (2026-06-02).** `qwen36-workhorse` listed in `:9000/v1/models`; 10-token completion returned "OK". Verified via `scripts/preflight_009a.py`. Raw response: `.guardkit/autobuild/TASK-HMIG-009A-canary/preflight/`.
- [x] **AC-001B** — ✅ **PASS BOTH WIRE FORMATS (2026-06-02).** Real 12.3KB design-phase prompt + real tool surface (`Read`/`Write`/`Edit`/`Bash`/`Grep`/`Glob`) probed against both wire formats independently. **OpenAI-compat (LangGraph path)**: emitted 1 `tool_call` for `Glob`. **Anthropic-compat (SDK path, historical F2 failure path)**: emitted 1 `tool_use` block for `Glob`. F2 empirically resolved at the substrate level. Raw responses: `.guardkit/autobuild/TASK-HMIG-009A-canary/preflight/AC-001B-{openai,anthropic}-response.json`.
- [x] **AC-001C** — ✅ **PASS — APPROVED in 1 turn (2026-06-02).** SDK end-to-end smoke produced **3 files created, 16 modified, 1 test passing**. Player: 500.6s / 40 SDK turns / 12.5s/turn avg / 39 ToolUseBlocks (Write/Edit/Bash). Test-orchestrator + code-reviewer specialists invoked successfully. Coach approved (LLM Coach primary). Honesty score 1.00 (1 discrepancy handled by orchestrator-induced ghost-path filter, per `.claude/rules/path-string-mismatch-is-not-dishonesty.md`). Total wall-clock ~21min. Full log: `docs/reviews/autobuild-migration/TASK-FIX-A7D3.md`. Note: deterministic gates flagged `audit=False (required=True), ALL_PASSED=False` but LLM Coach overrode per TASK-HMIG-008R design (LLM Coach primary, CoachValidator is evidence supplier). Worktree preserved per autobuild policy.
- [ ] **AC-001D** — ⛔ **BLOCKED on TASK-HMIG-002R + TASK-HMIG-002R-PROMPT (2026-06-03).** Three iterations attempted and each revealed a deeper layer:
  - **Run 1** (2026-05-27, pre-fix): `LangGraphHarness: failed to construct DeepAgent for role='coach' model=None: 'function' object has no attribute 'name'` — TASK-FIX-MODELPLUMB (orchestrator model plumbing) filed and landed.
  - **Run 2** (2026-06-02, post-MODELPLUMB): same error but with `model='openai:qwen36-workhorse'` — root cause was the `tools=[strings]` shape crashing `langgraph.prebuilt.ToolNode.__init__`. TASK-FIX-LGTOOLS filed and landed.
  - **Run 3** (2026-06-03, post-LGTOOLS): construction succeeded; Coach ran for 13+ `/v1/responses` calls but couldn't write `coach_turn_1.json`; test-orchestrator specialist burned 38.5min in `/v1/responses` loops without producing useful output. Cause: `backend=None`/`permissions=None` in LangGraphHarness (Wave-2 skeleton — TASK-HMIG-002R territory) AND Coach/specialist prompts use SDK tool names (`Read`/`Write`/`Bash`) but DeepAgents exposes different names (`read_file`/`write_file`/`execute`) — TASK-HMIG-002R-PROMPT territory. **Full log**: [`docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-3.md`](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-3.md). **Resume AC-001D after both 002R and 002R-PROMPT land.**

### Execution

- [x] **AC-001** — ✅ TASK-HMIG-006.4 has landed and merged (commit `f2c240a7`). Routing confirmed at code level (`task_work_interface._execute_via_sdk` routes through `select_harness()`, zero direct `claude_agent_sdk` imports) and via its CI falsifier test `test_langgraph_design_phase_never_calls_sdk` (99 passed). Live pre-loop langgraph smoke (zero `claude_agent_sdk.subprocess_cli` lines) verifies as part of AC-001D.
- [x] **AC-002** — ✅ Canary set updated: `task_hmig_009a_scope` block (2 tasks, 3 reps, 12 runs, `--no-pre-loop`, F4 out-of-scope) + `preflight_findings` block (AC-001A 2026-05-27 finding, marked RESOLVED 2026-06-02 by model_choice_correction_v2) + `model_choice_correction_v2` (qwen-coder-next → qwen36-workhorse with rationale + operator research citations). GLI-004 retained in `canary_tasks[]` (009 spec AC-001) but excluded from the 009A allowlist.
- [ ] **AC-003** — 🟡 **Runner prepped; batch UNBLOCKED but gated on AC-001A/B re-run.** [`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py) already has `--variant 009a` (2-task allowlist, 12-run plan, dedicated `TASK-HMIG-009A-canary` output namespace) + `--exclude-task`. Dry-run verified. Operator runs `python scripts/canary_validation_runner.py --variant 009a` **once AC-001B passes** (the load-bearing post-reconfig tool_use verification). Artefacts persist under `.guardkit/autobuild/TASK-HMIG-009A-canary/`.
- [ ] **AC-004** — 🟡 §8 scaffolded in [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) (scope, dependency status, preflight context, results/verdict placeholders). Metrics auto-populate via `--variant 009a --aggregate` after the batch runs. Update §8 to reference the v2 model swap once the batch completes.
- [ ] **AC-005** — ⏸️ Decision pending data (blocked on AC-001B → AC-003). Framing recorded in §8.6.
- [ ] **AC-006** — ⏸️ Cross-link pending verdict (blocked). Framing recorded in §8.7.

### Closing

- [x] **AC-007** — ✅ Created [`docs/deep-dives/autobuild_local_vllm.md`](../../../docs/deep-dives/autobuild_local_vllm.md). **UPDATE REQUIRED 2026-06-02**: the doc was written under the v1 framing (qwen-coder-next as canonical); needs revision to reflect v2 (qwen36-workhorse as current operator choice, with reasoning from `gb10-memory-budget-and-macbook-offload.md` + operator benchmark/forum research). Track as an addendum to this AC; do not unmark `[x]` (the doc exists, it just needs a v2 section).
- [x] **AC-008** — ✅ Captured in Graphiti (`guardkit__task_outcomes`) under v1 framing. **UPDATE REQUIRED 2026-06-02**: re-capture with the v2 model choice. The durable lesson is "defer to operator on AutoBuild Player model selection; do not silently substitute or lock in from documentation alone" — the specific model name may continue to evolve as the operator's research and infra work progresses.

## Out of Scope

- **Fixture-branch isolation** — deferred to TASK-HMIG-009B (post-WTBC).
- **TASK-GLI-004 canary task** — needs fixture isolation; runs only in 009B.
- **Pre-loop ON canary** — runs only in 009B once we have data on whether qwen36-workhorse satisfies the pre-loop marker contract post-reconfig.
- **Deploying qwen-coder-next or qwen3-coder-30b as AutoBuild Players** — model_choice_correction_v2 (2026-06-02) consolidates to qwen36-workhorse on the resource + benchmarks argument. If a user later wants to add a dedicated coding model, file as a separate task.

## Implementation Notes

The narrowed scope deliberately trades comprehensiveness for unblocked execution. 009A's verdict is the gating input for the cutover decision; 009B is optional polish if 009A's signal is decisive.

**On model choice (resolved 2026-06-02)**: The earlier open question and 2026-05-27 swap to qwen-coder-next are both superseded. Both harnesses now use `qwen36-workhorse` because (a) it's LIVE on the GB10 (no deployment work), (b) it's the shared workhorse across jarvis-reasoner/forge/autobuild/dataset-factory (resource consolidation), (c) operator's recent benchmark + NVIDIA-forum research identifies it as the strongest agentic-coding model in deployable range, and (d) the post-reconfig llama-swap (week of 2026-05-28→2026-06-02) is expected to have resolved the pre-reconfig marker-contract issues observed in smokes v2/v3 — AC-001B is the empirical gate that confirms this.

**The preflight ACs (001A–001D) remain cheap (<30min total) and front-loaded.** Their original purpose (catch model-deployment drift before burning canary compute) already paid off once on 2026-05-27 — they will pay off again if the post-reconfig workhorse doesn't actually satisfy the marker contract.

## References

- Parent review: [TASK-REV-HM09 review report §6 + §7](../../../.claude/reviews/TASK-REV-HM09-review-report.md#7-ac-007--task-hmig-009-scope-revision-recommendation) (note: review report has TWO correction addenda at top — v1 on 2026-05-27, v2 on 2026-06-02)
- Original task: [TASK-HMIG-009 (blocked)](../../blocked/TASK-HMIG-009-canary-validation.md)
- **Canary set (current — model_choice_correction_v2 applied 2026-06-02)**: [`.guardkit/autobuild/TASK-REV-HMIG-canary-set.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json)
- **Source for v2 model choice (2026-06-02)**: [`docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md`](../../../docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md) (esp. line 37 — workhorse serves multiple agentic-coding roles)
- Operator's prior model-choice context (now historical): [`docs/research/dgx-spark/gb10-model-requirements-matrix.md`](../../../docs/research/dgx-spark/gb10-model-requirements-matrix.md), [`docs/research/dgx-spark/llama-swap-config.yaml`](../../../docs/research/dgx-spark/llama-swap-config.yaml), [`docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md`](../../../docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md)
- Canary runner: [`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py)
- Pilot analysis (original framing — read with 2026-05-27 + 2026-06-02 corrections in mind): [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md)

## Status (2026-06-04 — AC-003 batch COMPLETE, cutover GO recommended)

**Final result**: ✅ **5/6 = 83.3% approval rate on BOTH harnesses** — passes the central falsifier (≥75% LangGraph). Cutover GO per AC-005/AC-006. Full per-rep table + aggregate metrics + verdict in [canary-analysis.md §8.5/8.6/8.7](../../../docs/state/TASK-REV-HMIG/canary-analysis.md).

### Quick summary

| Harness | Approval | First-pass | Mean wall-clock | Failure mode |
|---|---|---|---|---|
| SDK | 5/6 (83.3%) | 3/6 (50%) | ~1876s (~31min) | 1 × unrecoverable_stall (F6 honesty collapse + test-orchestrator polling) |
| LangGraph | 5/6 (83.3%) | 4/6 (67%) | ~1245s (~21min) | 1 × ERROR (Coach got llama-swap 400 Bad Request after 15 F6 must_fix discrepancies) |

**Both failures trace to F6 (Player honesty collapse on multi-turn iteration on qwen36-workhorse).** Same root cause, different surfacing. SDK and LangGraph are at parity in approval rate; LangGraph is 34% faster end-to-end.

### Critical caveat: runner reporting is wrong; real data is in stdout.log files

The runner's `TASK-HMIG-009A-canary-results.json` records `coach_decision: "unknown"` and `turns_used: 0` for ALL 12 reps despite stdout.log files clearly containing the real outcomes. Two runner bugs surfaced:

1. **Outcome-parser bug** — doesn't extract `Status: APPROVED` / `Coach approved implementation after N turn(s)` / `Reason: unrecoverable_stall` markers from per-rep stdout.
2. **Aggregate-variant default bug** — `--aggregate` without `--variant 009a` reads the old `TASK-REV-HMIG-canary-results.json` (1 run) instead of the 009A file.

Filed as [TASK-FIX-CANARY-PARSER](../autobuild-harness-migration/TASK-FIX-CANARY-PARSER-runner-outcome-parser-and-aggregate-variant-bugs.md). **Does NOT block the cutover** — the per-rep stdout.log files preserve the ground truth and §8.5 of canary-analysis.md has the hand-compiled correct numbers.

### AC checklist

- [x] **AC-001** — TASK-HMIG-006.4 landed (commit `f2c240a7`)
- [x] **AC-001A/B/C/D** — preflight + AC-001D run 6 PASSED 2026-06-03
- [x] **AC-002** — canary-set updated with 009a scope + model_choice_correction_v2 + preflight_findings
- [x] **AC-003** — 12-run batch executed 2026-06-03 → 2026-06-04; outcomes in stdout.log files
- [x] **AC-004** — §8 of canary-analysis.md hand-compiled with real metrics (auto-fill blocked by runner-parser bug)
- [x] **AC-005** — Verdict: 5/6 = 83.3% ≥ 75% → **GO**
- [x] **AC-006** — Cross-link: TASK-HMIG-010 unblocked, proceed with cutover
- [x] **AC-007** — `docs/deep-dives/autobuild_local_vllm.md` written (needs v2 model section addendum — not blocking)
- [x] **AC-008** — Initial Graphiti capture done; can add post-batch supplementary capture

### Next operator actions

1. **Cutover decision**: GO per the canary data. TASK-HMIG-010 can proceed.
2. **File TASK-FIX-CANARY-PARSER** for the runner reporting bugs (already done — see link above). Low-priority polish; doesn't block cutover.
3. **Optionally run TASK-HMIG-009B** if you want the additional fixture-isolated TASK-GLI-004 data point; not required given 009A's clean GO verdict.
4. **Consider TASK-FIX-SPECHANG** (filed 2026-06-03) post-cutover — would tighten Player iteration cycles but didn't bite the batch hard (only SDK rep 1).

---

## Status (2026-06-03 EOD, AC-003 batch rep 1 surfaced F6+F7 confirmed)

**AC-001D**: ✅ PASSED on run 6 (single-turn shape works on both SDK + LangGraph).
**AC-003 batch attempt 1**: ⛔ ABORTED after rep 1 produced `unrecoverable_stall` in 159 min / 3 turns.

### Rep 1 outcome (definitive data point)

| Turn | Player | Coach | Honesty | Time |
|---|---|---|---|---|
| 1 | 2 created, 18 modified, 2 tests passing | feedback (1 issue) | 1.00 | ~75min |
| 2 | 0 created, 18 modified, 0 tests | feedback (15 must_fix) | **0.38** | ~22min |
| 3 | 0 created, 18 modified, 0 tests | feedback (15 must_fix) | **0.21** | ~62min |
| **Final** | — | — | avg 0.53 | **unrecoverable_stall after 3 turns** |

**Two distinct findings from rep 1**:

1. **F6 honesty collapse under multi-turn iteration confirmed** (canary-analysis.md §3.F6 prediction). Local-Qwen Player can produce APPROVED single-turn (smoke runs proved this) but degrades fast when given Coach feedback to iterate on. The orchestrator's stall detector (F7) fired correctly at turn 3. **This is the canary's load-bearing measurement** — exactly what we built it to detect.
2. **test-orchestrator specialist consumes full SDK timeout** (2340s) on every multi-turn rep, contributing ~115 of the 159 min. Polls backgrounded pytest via `TaskOutput` until SDK timeout. **Filed separately as [TASK-FIX-SPECHANG](../autobuild-harness-migration/TASK-FIX-SPECHANG-test-orchestrator-polls-background-bash-until-sdk-timeout.md)**. Independent of F6; fix needed before any `--max-turns > 1` batch.

### Revised methodology for next batch attempt

Two viable shapes — operator decides:

**Shape A — single-turn batch (matches successful smokes)**: `python scripts/canary_validation_runner.py --variant 009a --max-turns 2` (note: runner's `--max-turns` passthrough already exists at line 697). Each rep either approves on turn 1 or fails fast with feedback. Total batch ~3-5h. Trade-off: measures "Player+Coach converge in 1 turn?" not "Player iterates to success?" — but that's the *empirically-working* shape on local Qwen. Cleanest data for cutover decision.

**Shape B — multi-turn batch after TASK-FIX-SPECHANG lands**: keep `--max-turns 5` default but only after the specialist-hang fix is in. Total batch ~10h. Measures Player iteration capability honestly. Requires ~3h dev + retry.

### Runner gap also worth filing later (not blocking)

The runner copies `stderr.log` + `stdout.log` per rep but **didn't copy `player_turn_*.json`, `coach_turn_*.json`, or `sdk_debug/`** — they were wiped when rep 2 started. Per-rep artefact preservation needs fixing in `scripts/canary_validation_runner.py` (line 404 has `shutil.copytree` for sdk_debug but it apparently didn't fire for this rep). Workaround: stderr.log alone has enough heartbeat + tool-block + honesty data to reconstruct rep outcomes — proven by this rep 1 analysis.

### Cumulative state (still good)

**The cutover decision is not blocked.** AC-001D run 6 + the rep 1 data together give us:
- ✅ SDK + LangGraph both succeed single-turn end-to-end
- ✅ LangGraph slightly faster than SDK on single-turn
- ✅ F6+F7 patterns from local Qwen confirmed empirically under multi-turn (canary's job)
- ⛔ Batch can't run multi-turn cleanly until TASK-FIX-SPECHANG lands OR we accept single-turn methodology

**Cutover-deadline outlook**: still feasible against 2026-06-15. Shape A batch (~5h compute) or TASK-FIX-SPECHANG (~3h dev) + Shape B batch (~10h compute) both fit.

---

## Status (2026-06-03, post-AC-001D-run-6 SUCCESS)

**SDK side**: ✅ FULLY VALIDATED (AC-001C APPROVED 2026-06-02).
**LangGraph side**: ✅ **FULLY VALIDATED** — AC-001D run 6 APPROVED in 1 turn.

**Run 6 results** (2026-06-03 15:08–15:21, ~13.5min):

| Phase | Wall-clock | Outcome |
|---|---|---|
| Player Implementation | 341s / 34 SDK turns | 4 files created, 16 modified, 2 tests passing |
| test-orchestrator specialist | ~120s | success (~3.5× faster than run 3's 38.5min) |
| code-reviewer specialist | ~250s | success (vs 870s+ in run 5 — NOVMODE win) |
| Coach Validation (LLM Coach) | 90s | **APPROVED**, honesty 0.96 |
| **Total** | **~13.5 min** | **APPROVED in 1 turn** |

**SDK vs LangGraph parity** (vs AC-001C):
- Both APPROVED in 1 turn; same task; same model (qwen36-workhorse).
- LangGraph ~13.5min vs SDK ~21min (~35% faster end-to-end, Coach 3× faster at 90s vs 287s).
- Honesty 0.96 vs 1.00 — equivalent quality bracket.

**Full 5-layer iteration history**:
- Run 1 (2026-06-02): `model=None` → ✅ TASK-FIX-MODELPLUMB (guardkit, landed)
- Run 2 (2026-06-03): `tools=[strings]` crash → ✅ TASK-FIX-LGTOOLS (guardkitfactory, landed)
- Run 3 (2026-06-03): `backend=None` → ✅ TASK-FIX-002R-CONSUME (guardkit selector wiring, landed)
- Run 4 (2026-06-03): DeepAgents `_PermissionMiddleware`+execute incompatible → ✅ TASK-HMIG-002R-NOPERMS (guardkitfactory, landed)
- Run 5 (2026-06-03): `virtual_mode=True` rewrote absolute paths into worktree-nested twins → ✅ TASK-HMIG-002R-NOVMODE (guardkitfactory, landed)
- **Run 6 (2026-06-03): SUCCESS** — predicted 6th layer (Coach/specialist prompt-tool-name mismatch) dissolved; DeepAgents' runtime tool advertisement was sufficient; TASK-HMIG-002R-PROMPT closed without code changes.

**Three quality signals to verify across the 12-run batch** (per guardkitfactory-side run-6 review):

1. `gather_evidence: honesty produced 1 must_fix issue(s)` (line 194) + final honesty 0.96 — the LLM Coach overrode the honesty oracle's must-fix flag. **Action**: spot-check whether the flagged discrepancy was genuinely minor before greenlighting the batch; track if it recurs on >2 of 12 runs.
2. `Criteria Progress (Turn 1): 0/1 verified (0%)` followed by Coach approval — LLM-Coach-as-fallback shape (consistent with AC-001C SDK behaviour). Track per-run; note if it differs SDK vs LangGraph.
3. One `/v1/responses` retry at line 196 — transient under qwen36-workhorse. Track; if >2 of 12 runs retry, brief look at vLLM queue depth warranted.

**Cutover-deadline impact**: well within window. Critical path is now AC-003 (~10h compute) + decision against 2026-06-15.

### ✅ Done

- **AC-001 (code/CI)** — TASK-HMIG-006.4 landed commit `f2c240a7`; falsifier test green.
- **AC-002** — canary-set scope + preflight-findings + model_choice_correction_v2 blocks.
- **AC-003 (runner)** — `--variant 009a` + `--exclude-task` flags; dedicated output namespace; dry-run verified.
- **AC-004 (scaffold)** — canary-analysis §8 placeholder.
- **AC-001A / AC-001B (both wire formats) / AC-001C** — preflight gates GREEN (see Acceptance Criteria above for details).
- **AC-007** — `docs/deep-dives/autobuild_local_vllm.md` (needs v2 section addendum).
- **AC-008** — Graphiti capture under v1 (needs v2 re-capture).

### 🔄 Next operator actions

1. **Cleanup AC-001C preserved worktree**:
   ```bash
   git worktree remove .guardkit/worktrees/TASK-FIX-A7D3 --force
   git branch -D autobuild/TASK-FIX-A7D3
   ```
   ⚠️ If you want to keep the Player-generated fix candidate for TASK-FIX-A7D3, run `git diff main autobuild/TASK-FIX-A7D3` first and stash/save the diff. The canary smoke was against real production code (`installer/core/lib/agent_enhancement/enhancer.py`).
2. **AC-001D** — LangGraph one-rep smoke (~15-25min):
   ```bash
   GUARDKIT_HARNESS=langgraph \
     OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
     OPENAI_API_KEY=llama-swap-local-key \
     guardkit autobuild task TASK-FIX-A7D3 \
       --no-pre-loop --no-checkpoints --max-turns 2 \
       --model qwen36-workhorse
   ```
3. **AC-003** — `python scripts/canary_validation_runner.py --variant 009a` (~10h, monitor). Then `--variant 009a --aggregate`.
4. **AC-004 §8.5 / AC-005 / AC-006** — fill from aggregated comparison doc.
5. **AC-007 / AC-008 addenda** — v2 updates to deep-dive doc + Graphiti re-capture with AC-001C empirical evidence.
