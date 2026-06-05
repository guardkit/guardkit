# Feature-run analysis — TASK-HMIG-010

> Companion to
> [`.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-results.json)
> and [`.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-target.json).
> Separate from [`canary-analysis.md`](canary-analysis.md) for clarity (per AC-009).
> This file is the **human-authored audit narrative** capturing *why*
> the feature run produced the verdict it did and what follow-up work it triggers.

## 0. Status (2026-06-04, post-run-1)

- [x] Scaffolded by `/task-work TASK-HMIG-010` (2026-06-04)
- [x] AC-001 — Feature target picked: FEAT-AOF (autobuild-observability-fixes, all 3 tasks)
- [⛔] AC-002 — Feature run end-to-end **BLOCKED**: run 1 aborted after 28s at Player turn 1 of Wave 1 / TASK-FIX-IA03 with LangGraphHarnessError (auth). See §6 / I-001 (F9).
- [〜] AC-003 — Run 1 recorded in feature-results.json:task_outcomes (1 entry, non_recoverable=true). No substrate-quality data yet.
- [ ] AC-004 — First-pass-success rate: not computable from run 1 (CLI-plumbing fail, not substrate fail).
- [ ] AC-005 — No `--resume` attempted: same auth error would fire every turn until LGFM lands.
- [x] AC-006 — F9 documented in [feature-run-incidents.md](feature-run-incidents.md) as I-001 (severity: high).
- [ ] AC-007 — Merge not reached.
- [ ] AC-008 — Falsifier verdict deferred until LGFM lands and a clean run 2 produces data.
- [〜] AC-009 — This analysis document carries the run-1 narrative (§§0, 6); §§1-5, 7-8 pending real data.

## Status header (2026-06-05T09:00Z)

**TASK-HMIG-010 BLOCKED on TASK-FIX-CTOUT01** (verdict-blocker for AC-008).

- Run 1 (pre-LGFM): F9 → fixed by LGFM (commit `683823cc`)
- Run 2 (post-LGFM): F10 → fixed by LGFM2; F11 → fixed by 002R-SUMM-ROOT + 002R-MODEL-PROFILE in guardkitfactory
- Run 3 (post-LGFM2+SUMM-ROOT+MODEL-PROFILE, 2026-06-05): **first real autobuild data**.
  - **2/3 tasks reached APPROVED** (IA03 turn 1, TP05 turn 1)
  - **GD02 verdict AMBIGUOUS** due to F14 cancellation race (outer says timeout, inner Coach says approved within ~48s of cancellation)
  - **F12** (4th instance of model-threading class) — `coach_test` role missing model. Soft-fails to subprocess. → TASK-FIX-LGFM3.
  - **F13** (substrate-quality) — test-orchestrator hits SPECHANG 600s cap on qwen36-workhorse. Not code-fixable; recorded as substrate finding.
  - **F14** (harness asymmetry) — cancellation doesn't propagate to LangGraph harness. Blocks AC-008 computation. → TASK-FIX-CTOUT01, **the one that re-blocks 010**.
  - **F15** (substrate-quality) — GD02 took 50min for complexity-6 multi-turn work. Recorded as substrate finding; possibly mitigated by `--task-timeout` bump on run 4.
  - **F16** (cosmetic) — Graphiti FalkorDB teardown race. Defer. → TASK-FIX-FALK01.

After CTOUT01 lands (and ideally LGFM3 too for clean audit signal), re-run with `--fresh`. AC-008 verdict will then be computable from run-4 evidence.

### Run-3 outcomes table

| Task | Verdict (outer) | Verdict (inner) | Turns | Wall clock | Notes |
|---|---|---|---|---|---|
| TASK-FIX-IA03 | ✓ APPROVED | ✓ APPROVED | 1 | ~14min | Soft-fail F12 (coach_test); F13 (specialist SPECHANG timeout) didn't prevent approval |
| TASK-FIX-TP05 | ✓ APPROVED | ✓ APPROVED | 1 | (Wave 2) | Cleanest pass; canonical substrate-working data point |
| TASK-FIX-GD02 | ⏱ TIMEOUT | ✓ APPROVED | 2 | 50min (capped) | **F14 ambiguity** + F15 (substrate slow on complexity-6) |

## Pattern emerging across runs 1+2

Three F-numbered findings (F9, F10, F11) plus three precursor findings
(F1, F4, NOVMODE) all share the same meta-shape:

> **A configuration / threading contract closed for some invocation
> sites but missed for others on the same migration boundary.**

| Finding | Boundary | Path closed | Path missed |
|---|---|---|---|
| F1 (canary) | claude-agent-sdk → LangGraph | Player-Coach loop | Pre-loop design phase |
| F4 (canary) | worktree manager → cwd branch | Most calls | Calls from a non-main worktree |
| NOVMODE | DeepAgents virtual_mode | Most paths | Path-doubling worktree paths |
| F9 (010 run 1) | CLI `--model` → orchestrator | task subcommand | feature subcommand |
| F10 (010 run 2) | AgentInvoker model → harness | `_invoke_with_role` | `_invoke_task_work_implement` |
| F11 (010 run 2) | DeepAgents path config | virtual_mode paths | conversation_history paths |

010's job is to surface exactly these. The cadence (6 instances over
the migration's lifecycle) suggests a `.claude/rules/` seeding is
warranted post-cutover: *audit ALL invocation sites of any contract
boundary touched by a migration, not just the ones the migration's
stated scope covers*. Proposed in TASK-FIX-LGFM2 Notes section.

## 1. Executive verdict

_Pending run 2 (post-LGFM-fix). Run 1 produced no substrate-quality
data — the failure was a CLI-plumbing gap, not a model/Coach/Player
behaviour finding._

## 2. Methodology actually executed

| Aspect | Spec intent | Actual |
|---|---|---|
| Target feature | ≥3 tasks, ≥2 waves, BDD-gated, state-bridge, ≤8h | _pending operator pick_ |
| Harness | langgraph | _pending_ |
| Model | qwen36-workhorse (same as 009A) | _pending_ |
| First-pass attempt | per-task | _pending_ |
| Resume policy | on any first-pass failure | _pending_ |
| Merge attempt | `guardkit autobuild complete` | _pending_ |

## 3. Findings — per-task summary

_Table to be filled task-by-task from `feature-results.json:task_outcomes`._

| Task | Wave | First-pass | Resume needed | Final | Turns | Wall-clock | Notes |
|---|---|---|---|---|---|---|---|
| _TBD_ | | | | | | | |

## 4. Aggregate metrics + 009A baseline comparison

_To be computed once `feature-results.json:aggregate_metrics` is filled._

| Metric | This run (010) | 009A baseline | Delta | Significance |
|---|---|---|---|---|
| First-pass success rate | _pending_ | 67% | | AC-004 threshold: >10pp drop = investigate |
| Approval rate (incl. resume) | _pending_ | 83.3% | | |
| Mean turns to approve | _pending_ | ~1.5 | | |
| Mean wall-clock per task | _pending_ | ~21min | | |

## 5. Falsifier evaluation (AC-008)

Threshold: ≥80% first-pass-success AND zero non-recoverable failures → proceed to Wave 4 cutover.

_Verdict: pending data._

## 6. Substrate-level findings worth recording

_The canary-analysis.md F1–F8 numbering continues here. F9 is recorded
below; F10+ will be appended after run 2 (post-LGFM)._

### F9 (2026-06-04): `guardkit autobuild feature` doesn't thread `--model` to the LangGraph harness

**Where**: `guardkit/cli/autobuild.py` — the `feature` subcommand
(definition starting at line 813) has no `--model` click option and
its function signature does not accept a `model` parameter. By
contrast, the sibling `task` subcommand at line 196 does (`--model`
option at line 206, parameter at line 334, threaded to
`AutoBuildOrchestrator` at line 555 with the load-bearing
TASK-FIX-MODELPLUMB comment).

**Evidence**: TASK-HMIG-010 run 1 stdout
[`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md`](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md)
line 134:

```
LangGraphHarness: agent.ainvoke failed for role='player' model=None:
"Could not resolve authentication method. Expected either api_key
or auth_token to be set..."
```

Traceback resolves to `langchain_anthropic/chat_models.py:1532` →
`anthropic._base_client._build_headers._validate_headers`. So with
`model=None` reaching the LangGraph harness, DeepAgents instantiates
its default provider (Anthropic), which demands `ANTHROPIC_API_KEY`
— but the operator's env was `OPENAI_BASE_URL` + `OPENAI_API_KEY`
for llama-swap routing.

**Class-of-defect**: sibling-of-F1. F1 was *pre-loop bypasses harness
adapter*: the migration closed the Player-Coach-loop entry point but
missed the pre-loop entry point. F9 is *task subcommand migrated, feature
subcommand missed*: the same sibling-entry-point oversight, one layer up
in the CLI surface.

**Implication**: 009A's clean GO verdict was real — but it only
exercised `guardkit autobuild task` (via the canary runner). The
feature subcommand had never been exercised under LangGraph until
2026-06-04. The cutover GO was based on a substrate that's verified
for the task path only; the feature path needs LGFM before parity is
restored.

**Resolution path**: [TASK-FIX-LGFM](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-LGFM-feature-subcommand-model-threading.md)
filed 2026-06-04. ~1h fix. Mirrors TASK-HMIG-006.4's pattern for F1
(code edit + regression test asserting the falsifier).

**Cutover-deadline impact**: minimal. ~1h fix + ~1h re-run = ~2h.
Deadline 2026-06-15, current date 2026-06-04. Comfortable.

### F10 (2026-06-04, run 2): sibling-of-F9 inside AgentInvoker

**Where**: [`guardkit/orchestrator/agent_invoker.py:5730-5751`](../../../guardkit/orchestrator/agent_invoker.py) (the `_invoke_task_work_implement` `select_harness(...)` call site). Compare with [`agent_invoker.py:2855-2875`](../../../guardkit/orchestrator/agent_invoker.py) (the working `_invoke_with_role` site) which passes `model=model` with a `_model_name` fallback from line 2847.

**Evidence**: Run-2 stdout log split signature:

```
line 139: role='player' model=None        (main inline-implement Player — fails auth)
line 350: role='player' model='openai:qwen36-workhorse'  (test-orchestrator specialist — routes correctly)
```

The discrepancy is the smoking gun. Same `role='player'`, different model value, different code path. The specialist routes through `run_specialist → _invoke_with_role` (which has model threading). The main Player routes through `_invoke_task_work_implement` (which doesn't).

**Class-of-defect**: sibling-of-F9 (which was sibling-of-F1). Migration boundary closed for some invocation sites but missed for the main Player path.

**Resolution**: [TASK-FIX-LGFM2](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-LGFM2-inline-implement-model-threading.md). One-line code edit.

### F11 (2026-06-04, run 2): DeepAgents conversation-history offload to read-only host root

**Where**: DeepAgents' `summarization.py` middleware, configured by the guardkitfactory `LangGraphHarness` wrapper. Offload path defaults to absolute host-root `/conversation_history/...`.

**Evidence**: Run-2 stdout log:

```
line 342: Failed to offload conversation history to
            /conversation_history/session_7b9e811b.md (60 messages):
            [Errno 30] Read-only file system: '/conversation_history'
line 346: Offloading conversation history to backend failed during
            summarization. Older messages will not be recoverable.
... 8 LLM calls accumulating context ...
line 350: 'request (569665 tokens) exceeds the available context size
            (131072 tokens), try increasing it'
```

The summarization middleware tries to trim history → can't write to host root → can't trim → conversation accumulates uncapped → llama-swap returns 400 once context exceeds qwen36-workhorse's 131k window.

**Class-of-defect**: sibling-of-NOVMODE. DeepAgents configuration assuming a virtualised filesystem but landing on the host. NOVMODE was paths under `/`; F11 is paths under `/conversation_history/`.

**Why it didn't surface in 009A**: 009A only exercised the `task` subcommand, which makes one specialist invocation per task (test-orchestrator), then exits. The 010 feature path invokes specialists per task across multiple waves; the longer conversation lifecycle is what surfaces the offload failure.

**Resolution**: [TASK-FIX-CHO01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-CHO01-deepagents-conversation-history-offload-path.md). Configure offload directory at `<worktree>/.guardkit/conversation_history/` and/or set a hard message-count cap on the summarization middleware. Likely lives in `guardkitfactory.harness.langgraph_harness.LangGraphHarness`.

### F12 (2026-06-05, run 3): `coach_test` role missing model — 4th instance of model-threading class

**Where**: `guardkit/orchestrator/quality_gates/coach_validator.py`, the SDK test-execution path (`coach_test` role harness construction). Mirror of F10's missing `model=` kwarg, in a different file.

**Evidence**: Run-3 log line 313 (and recurring per-Coach-turn):

```
ERROR: SDK coach test execution failed: LangGraphHarness: agent.ainvoke failed
  for role='coach_test' model=None: "Could not resolve authentication method..."
WARNING: falling back to subprocess.
```

**Soft-fail**: subprocess fallback works (line 314+). Run 3 isn't blocked by this — but the LangGraph code path for `coach_test` is dead, and every Coach turn pays a logged ERROR.

**Class-of-defect**: 4th instance of the model-threading class (F1, F9, F10, F12). At 4 instances over the migration's lifecycle, a `.claude/rules/` meta-rule is now strongly motivated.

**Resolution**: [TASK-FIX-LGFM3](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-LGFM3-coach-test-role-model-threading.md). One-line code edit + regression test.

### F13 (2026-06-05, run 3): test-orchestrator SPECHANG cap is hit but no context overflow

**Where**: `guardkit/orchestrator/specialist_invocations.py` test-orchestrator invocation, capped at 600s by TASK-FIX-SPECHANG safety guard.

**Evidence**: Run-3 log lines 211 + 289:

```
[TASK-FIX-IA03] test-orchestrator sdk_timeout capped from 2340s to 600s (TASK-FIX-SPECHANG)
[...]
run_specialist(test-orchestrator) failed for TASK-FIX-IA03: SDKTimeoutError:
  Agent invocation exceeded 600s timeout
```

**Important distinction from run-2's F11**: This is NOT context-window failure. The MODEL-PROFILE summarization (002R-MODEL-PROFILE) IS firing — there's no `exceed_context_size_error` from llama-swap in run 3 despite the specialist running for 600s. Instead, the specialist made 80+ successful HTTP calls and **still couldn't complete its task** within the SPECHANG cap. F11 is empirically closed; F13 is a different (substrate-quality) problem layered behind it.

**Class-of-defect**: **substrate-quality finding**. Mirrors canary's F6 (Player honesty collapse / multi-turn iteration drift on local Qwen) but manifests through SPECHANG instead of context overflow. Same root substrate behaviour, different symptom because the orchestrator's safety nets have improved.

**Why IA03 still got approved despite F13**: The orchestrator's synthetic-report path fired when the specialist failed (test-orchestrator's role is to verify, not to gate). Coach approved on the synthetic report + Graphiti context + Quality-gate checks (ALL_PASSED=True). So F13 is *visible* but didn't prevent first-pass success here.

**Resolution**: Not a code blocker. Possible levers:
- **Bump SPECHANG cap** from 600s → 900s/1200s (config edit) — gives the specialist more iteration runway
- **Investigate specialist prompt** for qwen36-workhorse efficiency (separate work)
- **Accept and document** as the qwen36-workhorse iteration-speed envelope

Not filing as a blocker task — recorded here for AC-008 evidence.

### F14 (2026-06-05, run 3): cancellation race — outer timeout fires, inner Coach completes anyway

**Where**: `guardkit.orchestrator.feature_orchestrator` (task-level timeout firing) interacting with `guardkit.orchestrator.autobuild` (Coach turn invocation) under `guardkitfactory.harness.langgraph_harness.LangGraphHarness.invoke()` (in-flight async iteration).

**Evidence**: Run-3 log lines 1555–1601 (GD02 timeline):

```
07:45:26  WARNING: TIMEOUT (feature-level): task_timeout=3000s expired
07:45:26  TASK-FIX-ASPF-004: Cancellation event detected during coach invocation,
          terminating SDK subprocess
07:45:30+ httpx: POST .../v1/responses "HTTP/1.1 200 OK"   (×5, cancellation IGNORED)
07:46:14  ✓ Coach approved - ready for human review
          Wave 2 ✗ FAILED                         ← outer
          Status: APPROVED ... Coach approved      ← inner
```

The "TASK-FIX-ASPF-004 ... terminating SDK subprocess" log is sibling of F1: ASPF-004's cancellation handler is **SDK-subprocess-specific** (it terminates a subprocess). Under the LangGraph harness, there's no subprocess — the in-flight call is `async agent.ainvoke(...)` on the orchestrator's event loop. The cancellation flag is set but doesn't propagate to LangGraph's pregel loop or its in-flight HTTP request.

**Class-of-defect**: **harness asymmetry** — a contract the SDK harness honoured (process termination) that the LangGraph harness doesn't honour (needs `asyncio.CancelledError` propagation instead). Distinct from the model-threading class but shares the migration meta-shape: *the migration translated some contracts behind the substrate boundary, missed this one*.

**Why this matters for AC-008**: GD02's outer verdict (timeout/failed) and inner verdict (approve) directly contradict. The cutover decision swings on whether GD02 is counted as success or failure:
- Counted as failure: 2/3 = 67% first-pass success → **HALT cutover** per AC-008
- Counted as success (Coach DID approve): 3/3 = 100% (eventually), 0 non-recoverable → **PROCEED with cutover**

**The orchestrator can't currently tell us which it is.** This is the verdict-blocker.

**Resolution**: [TASK-FIX-CTOUT01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-CTOUT01-coach-cancellation-timeout-race.md). Propagate cancellation through the LangGraph async path, establish the contract "outer cancellation dominates inner approval". ~3h fix.

### F15 (2026-06-05, run 3): substrate-quality timing on complexity-6 multi-turn iteration

**Where**: qwen36-workhorse + multi-turn Player-Coach iteration loop on complexity-6 tasks.

**Evidence**: Run-3 wall-clock:
- IA03 (complexity 3, 1 turn): ~14 min total
- TP05 (complexity 4, 1 turn): completed within Wave 2's allocation
- GD02 (complexity 6, 2 turns): 50 min (capped — would have continued)

GD02 needed multi-turn iteration because turn 1 Coach gave FEEDBACK on a Player honesty discrepancy (line 1584: "Player reported 6 files as modified but `git status --porcelain` shows none of t..."). Turn 2 Player corrected (line 1585: "0 files created, 6 modified, 0 tests"), Coach approved (line 1586). Each Player or Coach turn on qwen36-workhorse is slow enough that 2-turn convergence eats the 50-min budget.

**Class-of-defect**: **substrate-quality finding**. Mirrors canary's F6 directly — multi-turn iteration is the slow path on local Qwen. Once we account for F14's bookkeeping race, F15 is the load-bearing constraint for AC-008.

**Resolution**: Not code-fixable. Levers:
- **Bump --task-timeout** from 3000s → 4500s (config) gives GD02-class tasks more runway
- **Combine with KV cache bump** (200k context) for a slightly wider summarisation band — modest improvement, not load-bearing for this finding
- **Accept and document** as the qwen36-workhorse envelope for feature-scale autobuild

Recorded here for AC-008 evidence.

### F16 (2026-06-05, run 3): Graphiti FalkorDB teardown race (cosmetic)

Cosmetic process-exit teardown issue. Doesn't affect outcomes. Filed as [TASK-FIX-FALK01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md) — deferrable to Wave 4 cleanup.

### F2, F5, F6, F7 (canary-analysis.md) at feature scale

Run 3 produced the first observations of canary findings at feature scale:

- **F2 (model marker-contract failure)**: NOT reproduced. qwen36-workhorse successfully drove main Player turn for IA03 (40+ files created via Player tool use, structured promise/AC report extracted). MODEL-PROFILE + post-reconfig llama-swap closed F2's surface for the main Player path. Specialist behaviour (F13 SPECHANG) is a separate finding.
- **F5 (Coach honesty verification works on local Qwen)**: REPRODUCED, working as designed. Run-3 GD02 turn-1 Coach feedback caught the Player's honesty discrepancy ("Player reported 6 files as modified but `git status --porcelain` shows none") — exactly the migration-guard surface the parent review described.
- **F6 (Player honesty failures common on local Qwen)**: REPRODUCED at moderate severity. GD02 turn-1 Player fabricated `files_modified`. Coach caught it (per F5). Player turn-2 corrected and Coach approved. So F6 fires once per task on average but the guards work.
- **F7 (unrecoverable-stall guard)**: NOT EXERCISED. F14 blocked the natural stall observation point.

## 7. Recommendation

_To be filled. Two shapes possible:_

- **PROCEED to Wave 4 cutover** (TASK-HMIG-011): falsifier passed. Document any caveats from §6.
- **HALT Wave 4 cutover**: falsifier failed. Document the failure modes and the operator's decision (extend validation, revert, pivot).

## 8. Follow-up tasks

- _Any TASK-FIX-* tasks filed for issues discovered during the run._
- _Any TASK-REV-* tasks if the orchestrator surfaces a class-of-defect worth a review._

## 9. References

- Parent task: [TASK-HMIG-010](../../../tasks/in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Parent review: [TASK-REV-HMIG](../../../.claude/reviews/TASK-REV-HMIG-review-report.md) §11 (falsifier), §7.3 (Wave 3 sequencing), §5.10 (failure-rate asymmetry)
- Canary precedent: [TASK-HMIG-009A](../../../tasks/completed/TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md), [canary-analysis.md](canary-analysis.md) §8
- Feature-target picks: [`.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-target.json)
- Per-task results: [`.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-results.json)
- Incidents log: [feature-run-incidents.md](feature-run-incidents.md)
