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

## Status header (2026-06-04T21:00Z)

**TASK-HMIG-010 BLOCKED on TASK-FIX-LGFM2 AND TASK-FIX-CHO01.**

- Run 1 (pre-LGFM): F9 → fixed by LGFM (commit `683823cc`)
- Run 2 (post-LGFM): two new blockers surfaced:
  - **F10**: sibling-of-F9 inside AgentInvoker — `_invoke_task_work_implement` (main inline-implement Player path) doesn't pass `model=` to `select_harness`, while `_invoke_with_role` (Coach + specialists) does. → TASK-FIX-LGFM2, ~30 min fix.
  - **F11**: sibling-of-NOVMODE in guardkitfactory — DeepAgents summarization middleware writes conversation_history offload to read-only host root `/conversation_history/`, the offload fails, summarization can't trim, prompts overflow qwen36-workhorse's 131k context window. → TASK-FIX-CHO01, ~2h fix.

After BOTH land, re-run with `--fresh` and resume the AC checklist from AC-002.

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

### F2, F5, F6, F7 (canary-analysis.md) at feature scale

_Pending data from run 3+ (post-F10+F11). Runs 1 and 2 did not reach
the Player-LLM step on the main path, so no substrate-quality finding
could be observed yet._

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
