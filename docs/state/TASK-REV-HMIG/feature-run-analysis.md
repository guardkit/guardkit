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

## Status header (2026-06-07T10:20Z, post-run-10)

**TASK-HMIG-010 BLOCKED on F22 — SPECHANG hang-detection cascades into 120s Coach grace-period.** New code-side defect (not substrate). Filed as TASK-FIX-SPECCOCH01. AC-009 / `--reasoning auto` still not actually tested — Coach was killed before producing any output.

Run 10 (2026-06-07T10:09, 10m 20s, post-`--reasoning auto` + `task_timeout=4800s` + TASK-FIX-COACHPYENV + TASK-OPS-AOFENV):

- **F20 + F21 still RESOLVED ✓** — zero `HTTP 400` / `exceed_context_size_error` in run 10 (grep-confirmed). §9.13 n_ctx bump still validated.
- **All concurrent task landings empirically validated**:
  - TASK-FIX-AOFBUDG ✓ — `task_timeout=4800s` effective ([run-10:11](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L11))
  - TASK-FIX-COACHPYENV ✓ — Coach independent tests pinned to bootstrap venv ran in 84.6s vs 200s+ previously ([run-10:237](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L237))
  - TASK-OPS-AOFENV ✓ — FalkorDB up, Graphiti context loaded (7 categories, 3210/5200 tokens, 1.0s load — [run-10:220-234](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L220-L234))
  - TASK-FIX-SPECHANG watchdog ✓ — detected an actual specialist hang at the 150s no-model-activity threshold ([run-10:214](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L214)); detection correct, the cascade is the bug
  - TASK-ABFIX-004 Player-succeeded grace-period branch ✓ — the mechanism fires as designed when `cancellation_event` is set and Player succeeded ([run-10:218](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L218)); the 120s constant value is what's wrong
- **F22 (NEW, code-side cascade defect)**: SPECHANG hang-detection reuses the shared `cancellation_event` to abort the in-flight specialist (correct for CTOUT01 in-flight cleanup). But that event is also the trigger the orchestrator uses to detect *task-level* cancellation between Player and Coach — so the Player-succeeded grace branch fires with `COACH_GRACE_PERIOD_SECONDS=120`. 120s is structurally insufficient given run-9's empirical 944s Coach turn 1. In run-10 the Coach LLM got ~80s after Graphiti context + independent tests consumed 85s of the 120s window. CTOUT01 cancelled cleanly with **0 text blocks**. Recorded as I-011. Filed as [TASK-FIX-SPECCOCH01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-SPECCOCH01-decouple-specialist-hang-from-coach-grace.md).
- **AC-006 / AC-009 NOT exercised** — Coach never emitted any output, so we still don't know whether `--reasoning auto` solves F17 by populating `reasoning_content` with the fenced verdict.

After SPECCOCH01 lands, re-run with same invocation (`--reasoning auto` already configured; same `GUARDKIT_TASK_TIMEOUT_SECONDS=4800` or per-task frontmatter). Run 11 will be the actual AC-009 / AC-006 test.

## Status header (2026-06-07T00:16Z, post-run-9)

**TASK-HMIG-010 BLOCKED on F17 persistence under `--reasoning off`** — operator-side llama-swap reasoning-mode flip is the next experiment (AC-009 / COACHBUDG01 surface). F20 + F21 from run 8 are both RESOLVED empirically.

Run 9 (2026-06-06T21:24, 51m 51s, post-llama-swap `n_ctx` bump from 65536 → operator-set value):

- **F20 RESOLVED ✓**: zero `HTTP 400` / `exceed_context_size_error` anywhere in run-9 (grep-confirmed). Turn-1 code-reviewer specialist — the run-8 failure point — completed cleanly with 18+ successful HTTP 200s over ~480s. §9.13 operator runbook validated.
- **F21 RESOLVED ✓** (was purely downstream of F20): turn-2 Coach in run-9 was cancelled by CTOUT01 at legitimate 3000s task-timeout boundary (time-budget exhaustion after 600s SPECHANG on test-orchestrator), NOT a substrate hang. Two HTTP 200s observed in the ~80s Coach window vs run-8's 990s with zero HTTP calls.
- **F17 persistence under `--reasoning off`** is now the dominant constraint. Turn-1 Coach produced **25,211 chars content + 0 chars reasoning_content** (vs run-8's 4898 chars — 5.1× longer), still no fenced JSON. COACHSF01 fired correctly. The bigger n_ctx let deepagents feed Coach a richer prompt, gemma4 responded with proportionally longer prose, but didn't converge on the JSON contract. Substrate is using the extra budget for *more prose*, not *structured emission*.
- **F13 SPECHANG compounding effect**: turn-2 test-orchestrator hit 600s cap (vs ~250s on turn 1) because Player turn-2 diff was much larger (45 modified files vs 1+2). Compounds with Coach-turn-1 wall time (944s) to exhaust the 3000s task budget before turn-2 Coach can complete. Time-budget arithmetic suggests `--task-timeout 4500` would absorb this variance.
- **AC-006 still not met**: 0 natural verdict emissions / 2 attempts = 0%. Need ≥95% across ≥6 Coach turns.
- **AC-009 (COACHBUDG01 parser robustness with `--reasoning auto`) NOT exercised**: run 9 deliberately ran `--reasoning off`. **Next experiment** is run 10 with `--reasoning auto` + `--task-timeout 4500` to test AC-009 empirically AND absorb SPECHANG variance.

If run 10 produces ≥95% Coach verdict-emission rate under `--reasoning auto`, AC-006/AC-009 victory and TASK-HMIG-011 cutover unblocks. If not, escalation per TASK-HMIG-013 AC-007 is `nemotron-3-super:120b-a12b` (gated on 2nd GB10 + ConnectX-7 arrival).

## Status header (2026-06-06T17:03Z)

**TASK-HMIG-010 BLOCKED on F20 (gemma4-coach n_ctx sizing)** — operator-side llama-swap config bump, not a code defect. AC-008 verdict still deferred; AC-006 of TASK-HMIG-013 cannot pass until Coach turns complete reliably.

Run 8 (2026-06-06T16:13, 50min, post-`d526bf0f` selector colon-alias + `d07a4209` `--coach-model` plumbing + guardkitfactory `e8350bd` MODEL_CONTEXT_WINDOWS per-role registry):

- **Architecture invariants all confirmed working**: COACHSF01 (turn 1 synthetic feedback fired exactly as designed when Coach emitted 4898 chars + 0 reasoning, no fenced JSON), CTOUT01 (turn 2 hard-stall bounded by `harness.cancel()` at 3000s task-timeout), LGFM3 / ghost-path filter / SUMM-ROOT / MODEL-PROFILE all silent. The `d526bf0f` colon-alias and `d07a4209` `--coach-model` plumbing fixes both work end-to-end (LangGraph error message carries `role='coach' model='openai:gemma4:26b'`).
- **Two new substrate findings, both class-of-defect substrate-sizing/quality, NOT architecture**:
  - **F20** (HIGH, operator-fixable) — gemma4-coach's `n_ctx=65536` is too small for Coach + specialist payloads in this codebase. code-reviewer specialist hit HTTP 400 `exceed_context_size_error` at 69174 tokens > 65536 ctx. Operator fix: bump llama-swap `n_ctx` to 98304 (1.5×, recommended first step) or 131072 (2×, matches qwen36-workhorse). No code change. Recorded as I-009.
  - **F21** (MEDIUM, substrate quality) — turn-2 Coach validation hung for 990s+ with zero successful HTTP calls after the F20 specialist failure. CTOUT01's `harness.cancel()` bounded the failure cleanly at the 3000s task-timeout boundary. Likely downstream consequence of F20 (KV-state corruption after the 400, or model-swap reload deadlock). Goes away when F20 is fixed. Recorded as I-010.
- **AC-006 (TASK-HMIG-013)**: NOT met. Coach verdict-emission rate this run = 0% natural (1 synthetic-feedback emission via COACHSF01, 1 hard-stall cancelled). Required ≥95% across ≥6 Coach turns.
- **AC-009 (TASK-FIX-COACHBUDG01)**: NOT exercised. Substrate ran with `--reasoning off` per §9.13 default; the 4898-char prose response on turn 1 is the existing COACHSF01-handled shape, not the AC-009 surface (which fires under `--reasoning auto`).

After F20 is operator-mitigated (n_ctx bump), re-run with `--fresh --model qwen36-workhorse --coach-model gemma4:26b`. Run 9 will produce the first usable AC-006 signal under the new substrate posture.

## Status header (2026-06-05T17:30Z)

**TASK-HMIG-010 BLOCKED on TASK-FIX-COACHSF01** (verdict-blocker for AC-008).

- Run 4 (2026-06-05T16:05, 13m30s, post-CTOUT01+LGFM3+SUMM-ROOT+MODEL-PROFILE):
  - **Substantive Player work succeeded**: IA03 turn 1 produced 14/14 doc-level exclusion tests passing, 517/580 suite tests passed (63 pre-existing failures honestly disclosed). This is the cleanest qwen36-workhorse Player result of the migration — `phase_4_summary.json` is well-formed and accurate.
  - **Coach LLM hard-failed at verdict emission**: 140s of Coach reasoning, 12 successful HTTP 200s, but no Bash-heredoc tool call to write `coach_turn_1.json`. **F17: canary F2 manifesting at Coach level.**
  - **Orchestrator safety-net inconsistency**: `_invoke_coach_primary` has `_emit_synthetic_coach_feedback` for exception cases, but `invoke_coach` converts `CoachDecisionNotFoundError` to `success=False` instead of letting it propagate. Safety net never fires for this failure mode. → TASK-FIX-COACHSF01.
  - **CTOUT01 + LGFM3 fixes empirically validated**: no model=None on coach_test (LGFM3 ✓), no F14 cancellation race observed (CTOUT01 not exercised this run — no Coach approval to race), no SPECHANG timeout (F13 didn't fire), no FalkorDB teardown error (F16 not observed in run 4).
  - **F18 (cosmetic)**: 40+ pip-cache paths leaked into Player's files_modified list. Recorded as I-008.

After COACHSF01 lands, F17 converts from hard-blocker to soft-fail telemetry. Run 5 should produce a usable AC-008 signal.

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

### F17 (2026-06-05, run 4): Coach LLM completes but doesn't emit verdict file — canary F2 at Coach level

**Where**: `guardkit/orchestrator/agent_invoker.py` Coach contract (lines 1959 allowed_tools, 2393 prompt) interacting with `guardkit/orchestrator/autobuild.py:5663` `_invoke_coach_primary` safety net.

**Evidence**: Run-4 log + worktree inspection at `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`:
- Coach LLM ran 140s with 12 successful `POST /v1/responses HTTP/1.1 200 OK`
- `phase_4_summary.json` exists and is well-formed (Player+specialists' aggregated state)
- `turn_state_turn_1.json` exists (orchestrator's record)
- **`coach_turn_1.json` does NOT exist** — Coach LLM never emitted the Bash-heredoc to create it
- Orchestrator raises `Coach decision not found: ...coach_turn_1.json` (run-4 line 297)

**Class-of-defect**: dual.
1. **Substrate quality** — qwen36-workhorse Coach reasoning + Bash-heredoc structured-emission contract is unreliable for non-trivial verdicts. This is canary F2 ("model discusses tool calls in prose without emitting actual tool_use blocks") confirmed at Coach scope. Confirmed by the diff between run 3 (synthetic Player report → simpler Coach reasoning → tool call succeeded) and run 4 (real Player report with 63 pre-existing test failures → complex Coach reasoning → drift into prose response).
2. **Orchestrator load-bearing inconsistency** — the orchestrator's safety net at `autobuild.py:5663` (`_emit_synthetic_coach_feedback` on `except Exception`) was designed exactly for this case but doesn't fire because `invoke_coach` catches `CoachDecisionNotFoundError` internally at `agent_invoker.py:1987-1997` and returns `success=False` instead of raising. The safety net only watches for exceptions.

**Why this matters for AC-008**: hard-fails Wave 1 before the falsifier can even evaluate. With COACHSF01's safety-net wiring, F17 becomes a soft-fail feedback turn — the substantive Player work (which was correct in run 4!) gets recorded and the orchestrator can produce a usable verdict signal.

**Resolution**: [TASK-FIX-COACHSF01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-COACHSF01-coach-soft-fail-on-decision-not-found.md). ~15-line change in `_invoke_coach_primary`: after `asyncio.run(invoke_coach(...))` returns, if `result.success=False` AND `"Coach decision not found"` in `result.error`: emit synthetic feedback. ~1.5h fix.

**Out-of-scope longer-term work**: Coach's verdict-emission contract depending on Bash-heredoc is the substrate-asymmetry root cause. Two options for the post-cutover review:
- (a) Reduce Coach to structured-output format that the orchestrator parses from response text (eliminates the tool-call dependency entirely)
- (b) Grant Coach a constrained Write tool limited to `coach_turn_*.json` paths (removes the contract complexity but mildly violates the read-only invariant — a controlled exception is plausible)

File as TASK-REV-COACH-OUTPUT-CONTRACT post-cutover.

### F22 (2026-06-07, run 10, code-side cascade defect): SPECHANG hang-detection cascades into 120s Coach grace-period, structurally incompatible with gemma4 Coach reasoning time

**Where**:
- [`specialist_invocations.py:113`](../../../guardkit/orchestrator/specialist_invocations.py#L113) — `_WATCHDOG_HANG_REASON_TEMPLATE = "hang detected (no model activity for {seconds}s)"` (150s threshold)
- [`autobuild.py:191`](../../../guardkit/orchestrator/autobuild.py#L191) — `COACH_GRACE_PERIOD_SECONDS: int = 120`
- [`autobuild.py:3077-3087`](../../../guardkit/orchestrator/autobuild.py#L3077-L3087) — the Player-succeeded → Coach grace-period branch (TASK-ABFIX-004)

**Evidence**: Run-10 sequence ([autobuild-FEAT-AOF-run-10.md:214-253](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L214-L253)):

```
Line 214: WARNING:guardkit.orchestrator.specialist_invocations:[TASK-FIX-IA03]
          run_specialist(test-orchestrator): hang detected (no model activity for 150s) —
          terminating before the 600s duration cap
Line 218: INFO:guardkit.orchestrator.autobuild: Cancellation detected for TASK-FIX-IA03
          between Player and Coach at turn 1, but Player succeeded —
          granting Coach grace period (120s)
Line 250: INFO:guardkit.orchestrator.agent_invoker: [TASK-FIX-IA03] SDK timeout: 120s
          (base=1200s, mode=task-work x1.5, complexity=3 x1.3, budget_cap=120s)
Line 252: INFO:guardkit.orchestrator.agent_invoker: TASK-FIX-CTOUT01: Cancellation event
          detected during coach invocation; calling harness.cancel() and terminating any
          SDK subprocess.
Line 253: INFO:guardkit.orchestrator.agent_invoker: Extracted partial data from 0 events:
          0 text blocks, 0 tool calls, 0 file mods
```

The Coach SDK timeout is capped to `COACH_GRACE_PERIOD_SECONDS=120s`. Coach independent tests (TASK-FIX-COACHPYENV-pinned interpreter, running pytest in 84.6s) consumed most of that window. The LLM invocation got ~80s before CTOUT01 cancelled cleanly with **zero text blocks extracted**.

**Class-of-defect**: code-side **cascade defect** — two reasonable defensive features compose into an architectural impossibility. Distinct from F1/F4/F10 (migration-boundary defects) and F17/F20 (substrate-quality defects). Each feature in isolation is correct:
- SPECHANG watchdog needs to abort the in-flight specialist (correct for CTOUT01 LangGraph cleanup contract — see `.claude/rules/harness-cancellation-contract.md`)
- TASK-ABFIX-004 Coach grace-period needs to fire when task-level cancellation hits between Player and Coach (so Player's successful work can still be validated)

The architectural mismatch: the same `cancellation_event` is the abort signal AND the task-level-cancellation detector. The orchestrator can't distinguish "specialist hang requires cleanup" from "task budget exhausted, give Coach grace". Both shapes trip the same condition.

**Why this didn't surface earlier**:
- TASK-FIX-SPECHANG hang-watchdog landed recently (post run 9)
- Run-9 Coach turn 1 took 944s under `--reasoning off` — the empirical Coach-cost evidence that 120s is structurally insufficient was generated by run 9 itself
- Run 10 was the first run to exercise both features together: hang-watchdog fires + Player succeeded + grace period activates + Coach LLM cannot complete inside the constant

**Resolution** — [TASK-FIX-SPECCOCH01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-SPECCOCH01-decouple-specialist-hang-from-coach-grace.md) (~1-2h, complexity 3):

| Shape | Change | Pros | Cons |
|---|---|---|---|
| **A (primary)** | Specialist-hang detection does NOT set the task-level `cancellation_event` — only aborts the specialist. Orchestrator continues normally; specialist failure already injects `validation=violation` records gracefully. | Cleaner separation. Specialist failures are already non-fatal. Doesn't bake in a magic-number budget. | Touches the SPECHANG watchdog wiring; need to verify it doesn't break the in-flight LangGraph cleanup the cancellation-event currently triggers (the abort path can use a specialist-local event instead of the shared one). |
| **B (defensive backstop)** | Make `COACH_GRACE_PERIOD_SECONDS` env-tunable (`GUARDKIT_COACH_GRACE_PERIOD_SECONDS`, default raised to 1500). Same env-tuning pattern as `GUARDKIT_TASK_TIMEOUT_SECONDS` from TASK-FIX-AOFBUDG. | One-line change. Preserves TASK-ABFIX-004 contract. Cheap belt-and-braces even with Shape A. | Doesn't address the architectural confusion. Magic number drifts as substrates change. |

Recommend **A + B as backstop**. The architectural split is what TASK-ABFIX-004 was originally trying to express ("Player-succeeded near a *timeout boundary*"); a SPECHANG hang isn't the same shape as a task-timeout boundary, so it shouldn't take the same code path.

**Severity**: **HIGH** — blocks AC-006 / AC-009 evaluation. Coach never gets enough budget to emit anything, so we can't tell whether `--reasoning auto` solves F17. AC-009 surface still untested.

Recorded as I-011. **Blocks TASK-HMIG-010** as the verdict-blocker for run 11.

### F20 (2026-06-06, run 8, substrate-sizing) — **RESOLVED 2026-06-07 (run 9)**: gemma4-coach `n_ctx=65536` too small for Coach + specialist payloads

> **Status update 2026-06-07**: Operator landed the §9.13 n_ctx bump on llama-swap and re-ran. Run 9 produced zero HTTP 400 / `exceed_context_size_error` across all phases including the turn-1 code-reviewer specialist which was the run-8 failure point (480s + 18 successful HTTP 200s). F20 is closed as a substrate-sizing finding; the bumped n_ctx is the new steady-state operator config for gemma4-coach.


**Where**: llama-swap config for `gemma4-coach` (§9.13 of [AUTOBUILD-ON-LLAMA-SWAP-findings.md](../../research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md#L1943)) registered with `--ctx-size 65536`; guardkitfactory `MODEL_CONTEXT_WINDOWS["gemma4:26b"]["max_input_tokens"]=65536` (`model_config.py:188-194`) correctly mirrors it; deepagents summarisation threshold computes as `0.85 × 65536 ≈ 55,705`.

**Evidence**: Run-8 log [line 375-376](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-8.md#L375-L376):

```
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 400 Bad Request"
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(code-reviewer) failed
  for TASK-FIX-IA03: AgentInvocationError: SDK invocation failed for coach
  (LangGraphHarnessError): LangGraphHarness: agent.ainvoke failed for role='coach'
  model='openai:gemma4:26b': Error code: 400 - {'error': {'code': 400,
  'message': 'request (69174 tokens) exceeds the available context size (65536 tokens),
  try increasing it', 'type': 'exceed_context_size_error',
  'n_prompt_tokens': 69174, 'n_ctx': 65536}}
```

The code-reviewer specialist (running under Coach role, routed to `gemma4:26b` via `--coach-model`) made several successful HTTP 200s during its tool-use loop, then one call landed at 69174 tokens — 5% over the 65536 ctx. Deepagents summarisation fires between turns, not on a single oversized input, so no recovery was possible.

**Class-of-defect**: **substrate-sizing / operator-policy**, not architecture. The registry contract is honoured top-to-bottom; the substrate is simply too small for this codebase's Coach payload shape under multi-specialist turns. Sibling-of-canary-F6 (substrate-quality recorded not coded) but with an operator-side fix available, unlike F6.

**Why this didn't surface earlier**: runs 1-6 used qwen36-workhorse for Coach (131072 ctx, larger envelope). Run 7 failed at the selector colon-alias bug before reaching Coach payload depth. Run 8 was the first run to actually exercise gemma4-coach Coach validation against a real codebase payload.

**Resolution** — operator-side llama-swap config bump, no code change. Three paths in increasing risk/reward:

| Path | n_ctx | KV delta | Projected GB10 footprint | Time to next signal |
|---|---:|---:|---|---|
| **A (recommended)** | 98304 (1.5×) | +2.5-5 GB | 113.5-116 GB / 128 GB (≥12 GB headroom) | Same day after reload |
| **B** | 131072 (2×) | +5-10 GB | 116-121 GB / 128 GB (7-12 GB headroom) | Same day, watch transient peaks |
| **C** | wait for 2nd GB10 + nemotron-3-super:120b-a12b | n/a | n/a | ~next week |

Recorded as I-009. **Blocks AC-006 of TASK-HMIG-013** until run 9 confirms the bump unblocks Coach verdict-emission.

### F21 (2026-06-06, run 8, substrate-quality) — **RESOLVED 2026-06-07 (run 9)**: turn-2 Coach hard-stall (downstream of F20)

> **Status update 2026-06-07**: Run 9 did not reproduce. Turn-2 Coach cancellation in run 9 was time-budget exhaustion (3000s task-timeout fired after legitimate phase consumption: 944s Coach turn 1 + 600s SPECHANG turn-2 test-orchestrator + 320s turn-2 Player + ~80s turn-2 Coach start), not a substrate hang. Two successful HTTP 200s observed in the ~80s Coach window. Confirms the run-8 hypothesis: F21 was a KV-corruption / model-swap deadlock downstream of the F20 HTTP 400, and removing F20 removed F21. No residual substrate-stall surface to file separately as TASK-FIX-COACHSTALL01.


**Where**: gemma4-coach inference path on llama-swap, observed at `agent_invoker.py` Coach invocation in [autobuild-FEAT-AOF-run-8.md:394-426](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-8.md#L394-L426).

**Evidence**: Turn-2 Coach validation started at 16:43:33; CTOUT01 cancellation event fired at the 3000s task-timeout (17:03:37). In the 990+ second window between Coach start and cancellation, the 30s-interval progress counter advanced from 30s through 990s but **zero `POST /v1/responses HTTP/1.1 200 OK` log lines appear** (compare to turn-1 Coach which produced ~14 successful HTTP 200s in the same elapsed range). The Coach invocation never made a single successful LLM call.

**Class-of-defect**: **substrate-quality**, almost certainly downstream consequence of F20. Two plausible mechanisms:
1. The turn-2 Coach validation prompt itself was already over `n_ctx=65536` (carrying turn-1 feedback context + 46-file turn-2 diff + cumulative 10 ACs), and llama-swap wedged on the oversized input instead of returning 400.
2. The prior F20 400 corrupted gemma4-coach's KV-cache state or triggered a model-swap reload that deadlocked.

Either way, the architecture-side response was correct: CTOUT01 Layer 3 (`harness.cancel()`) fired exactly as designed at the 3000s boundary, bounded the failure window, and surfaced `TASK-FIX-CTOUT01: Cancellation event detected during coach invocation` ([line 430](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-8.md#L430)).

**Why this matters for AC-008**: masks any signal we'd otherwise get from turn-2 Coach validation. Expected to disappear when F20 is operator-mitigated.

**Resolution**: Same operator-side fix as F20 (bump gemma4-coach `n_ctx`). No code change. Re-validation on run 9 will confirm whether F21 is purely-downstream-of-F20 or has its own residual substrate stall surface; if the latter, file separately as TASK-FIX-COACHSTALL01.

Recorded as I-010.

### F18 (2026-06-05, run 4, cosmetic): pip-cache ghost-path filter gap

**Where**: `agent_invoker.py:200` ghost-path filter has a hardcoded allow-list.

**Evidence**: Worktree's `turn_state_turn_1.json` `files_modified` list contains 40+ `Library/Caches/pip/http-v2/...` entries alongside the legitimate `tests/orchestrator/test_doc_level_exclusion.py`.

**Resolution**: extend ghost-path filter to include pip cache + similar bootstrap-output patterns. Cosmetic; folded into incidents log (I-008), not filed as a separate task.

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
