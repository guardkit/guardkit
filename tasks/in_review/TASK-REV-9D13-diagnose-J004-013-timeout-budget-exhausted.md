---
id: TASK-REV-9D13
title: Diagnose Jarvis FEAT-J004-702C run-2 TASK-J004-013 timeout_budget_exhausted
status: review_complete
task_type: review
review_mode: diagnostic
review_depth: comprehensive
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: high
tags: [autobuild, review, diagnostic, sdk-ceiling, timeout-budget, specialist-invocations, complexity, FEAT-J004-702C, post-player-specialist-stall]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
related_reviews:
  - TASK-REV-FA04  # Langchain trapdoor diagnosis (closed) — Waves 1-2 of FEAT-ABSR-9C6E
related_features:
  - FEAT-ABSR-9C6E  # autobuild-stall-resilience — Waves 3-5 added 2026-04-28
review_results:
  mode: diagnostic
  depth: comprehensive
  decision: implement
  bugs_identified: 8  # A through H, see report v2 §0
  remediations_proposed: 7  # R1-R7
  report_path: .claude/reviews/TASK-REV-9D13-report.md
  report_revisions: 2  # v1 superseded by v2 after deeper code archaeology
  completed_at: 2026-04-28T00:00:00Z
implementation_subtasks:
  - TASK-ABSR-CEIL  # R1: skip Phase 4/5 on sdk_ceiling_hit (CRITICAL, Wave 3)
  - TASK-ABSR-WALL  # R2: cap specialist sdk_timeout at remaining wall (CRITICAL, Wave 3)
  - TASK-ABSR-FRSH  # R3: refresh remaining_budget post-Player (HIGH, Wave 3)
  - TASK-ABSR-DIAG  # R6.b: heartbeat label fix (MED, Wave 3)
  - TASK-ABSR-MAXT  # R4: complexity-scale TASK_WORK_SDK_MAX_TURNS (MED, Wave 4)
  - TASK-ABSR-MTBC  # R5: env-overridable MIN_TURN_BUDGET_SECONDS (LOW, Wave 4)
  - TASK-ABSR-CMPL  # R6.a: Phase-2.5 effective-complexity heuristic (MED, Wave 5)
spawned_review_tasks:
  - TASK-REV-COSE  # R7: Coach SDK-test-execution opaque-stderr (sidequest, separate review)
---

# Diagnose Jarvis FEAT-J004-702C run-2 TASK-J004-013 timeout_budget_exhausted

## Context

This is a follow-up review to [TASK-REV-FA04](../../.claude/reviews/TASK-REV-FA04-report.md). FA04 diagnosed the langchain-0.x/1.x version-skew + Python-3.14 trapdoor that produced a 33-min stall on Jarvis FEAT-J004-702C run 1. The remediation (ADR-ARCH-010 rev2: relax `requires-python` to `>=3.11`, pin langchain ecosystem to coherent 1.x with `<2` caps, plus the GuardKit-side `bootstrap_failure_mode=block` smart default and `environment_stall` sub-type) was committed to Jarvis's main and validated end-to-end via a [F]resh autobuild — **run 2**.

**Run 2 result: massive improvement, single distinct failure on the very last attempted task.**

Run 2 outcome (see `jarvis/docs/history/autobuild-FEAT-J004-702C-run-2-history.md` and `jarvis/.guardkit/autobuild/FEAT-J004-702C/review-summary.md`):

| Wave | Tasks | Outcome | Notes |
|------|-------|---------|-------|
| 1 | 4 | ✓ all approved (1 turn each) | Bootstrap green — FA04 fix confirmed |
| 2 | 5 | ✓ all approved (1-2 turns) | Inter-wave bootstrap green |
| 3 | 1 | ✓ approved (1 turn) | |
| 4 | 2 | ✓ approved (1 turn each) | |
| 5 | 1 | **✗ TASK-J004-013 timeout_budget_exhausted (1 turn)** | This review's subject |

12/20 tasks completed in 129 min 34 s. First-attempt pass rate 77%. Quality metrics: task success rate 92%, first-turn approvals 10/13. **The langchain trapdoor is closed.** The new failure is a different class of problem.

## Subject task: TASK-J004-013 (lifecycle startup and shutdown wiring)

Task profile (from `tasks/design_approved/TASK-J004-013-lifecycle-startup-and-shutdown-wiring.md` in the worktree):

- `complexity: 6` (medium)
- `task_type: feature`
- `implementation_mode: task-work`
- 7 explicit dependencies on prior wave tasks (-006 through -012)
- 9 acceptance criteria covering startup wiring, soft-fail logic for NATS/Graphiti, shutdown ordering invariant, idempotency, and lint/format
- 3 declared `consumer_context` interfaces (NATS_CLIENT_API, CAPABILITIES_REGISTRY_PROTOCOL, ROUTING_HISTORY_WRITER_API)

This is a *real* integration task — not a trivial wiring. The Player needed to compose work from -006/-007/-008/-009/-010/-011/-012 and produce the lifecycle module with explicit startup/shutdown ordering, soft-fail paths, and bounded waits. The 9 ACs and 3 consumer interfaces give a sense of the surface area.

## Preliminary Evidence (do not stop here — verify and look beyond)

From the run-2 history, in the order events fired:

### 1. Player SDK invocation hit the ceiling without producing phase 3/4/5 specialists

```
INFO:guardkit.orchestrator.agent_invoker:[TASK-J004-013] Player invocation in progress... (30s elapsed)
... [40 identical heartbeat lines, one per 30s] ...
INFO:guardkit.orchestrator.agent_invoker:[TASK-J004-013] Player invocation in progress... (1200s elapsed)
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-J004-013: SDKTimeoutError: Agent invocation exceeded 1200s timeout
```

Twenty minutes of 30-second "still running" heartbeats with **zero internal progress visibility**, then a SDK timeout on the test-orchestrator specialist. The Player's task-work invocation was apparently producing tool calls (we see `7 files created, 6 modified, 1 tests (failing)` later in the Player report) but didn't return within budget.

### 2. Phase 3, 4, 5 specialist invocations all missing

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Agent-invocations advisory for TASK-J004-013: missing phases 3, 4, 5 (non-blocking; outcome gates will run)
```

Neither the stack-specific Phase-3 specialist (`python-api-specialist` for langchain-deepagents per `phase_specialists.py`), nor `test-orchestrator` (Phase 4 — explicitly timed out per the warning above), nor `code-reviewer` (Phase 5) appear as completed invocations in the agent_invocations validation. The advisory fires non-blockingly per the F3c policy (post-RWOP1.3.1), but it points at a real underlying problem: the Player didn't reach the points where it would invoke them.

### 3. Player gates all green, but Coach detected unmet ACs

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), arch=True (required=False), audit=True (required=True), ALL_PASSED=True
```

…but…

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Requirements not met for TASK-J004-013: missing [
  'Startup wiring matches design §8 sequence **exactly**.',
  'DDR-021 soft-fail**: NATSClient.connect returning None does NOT block startup; ...',
  'DDR-019 soft-fail**: GraphitiClient.connect failure does NOT block startup; ...',
  'AppState gains the four new fields (frozen dataclass — order preserved).',
  'assemble_tool_list accepts and propagates the three new kwargs to tools/dispatch.py module attributes.',
  "Shutdown order** matches the 8-step sequence above; ordering enforced by TASK-J004-018's invariant test.",
  'Each shutdown step is independently failure-tolerant — a single failed step (WARN-logged) does not skip later steps.',
  "Heartbeat task cancellation produces no traceback (handled by heartbeat_loop's CancelledError contract).",
  'All modified files pass project-configured lint/format checks with zero errors.'
]
```

9 of 10 ACs are unmet — the Player ran out of SDK turns before completing the work. Coach correctly issues `feedback` (would normally go to turn 2 for a fix-loop).

### 4. Coach's own SDK test-execution path errored, fell back to subprocess

```
ERROR:claude_agent_sdk._internal.query:Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution failed (error_class=Exception): Command failed with exit code 1 (exit code: 1)
WARNING:guardkit.orchestrator.quality_gates.coach_validator:SDK test execution failed (error_class=Exception), falling back to subprocess.
INFO:guardkit.orchestrator.quality_gates.coach_validator:Independent tests passed in 3.3s
```

The Coach's SDK-mediated pytest run errored opaquely (`Command failed with exit code 1` with no captured stderr). The subprocess fallback worked correctly. **This is a separate orchestrator behaviour** — the SDK error path eats the actual stderr — worth noting but not the primary cause here.

### 5. Turn 2 cannot start — wall budget exhausted

```
INFO:guardkit.orchestrator.autobuild:Coach provided feedback on turn 1
INFO:guardkit.orchestrator.autobuild:Timeout budget exhausted for TASK-J004-013 at turn 2: remaining=21.2s < min=600s
```

The orchestrator declines to start turn 2 because remaining wall budget (21.2 s) is below the `min=600s` threshold — the gate's reasoning is sound (turn 2 won't be productive in 21.2 s), but it terminates the task. Final decision: `timeout_budget_exhausted`.

### 6. The arithmetic — and the missing 1180 s

Per-task timeout was `task_timeout=2400s` (40 min, default per the CLI invocation). Visible accounting:

- Player SDK invocation: ~1200 s (hit ceiling)
- Coach context loading: ~1 s (Graphiti, FalkorDB-workaround log entries)
- Coach validation (incl. agent-invocations advisory + quality-gate eval): ~10 s
- Coach SDK test execution attempt + error: ~5 s
- Coach subprocess test execution: 3.3 s
- Coach decision write + checkpoint: ~1 s

Total visible: ~1220 s. **Remaining wall budget should have been ~1180 s, not 21.2 s.**

**Where did the missing ~1160 s go?** The orchestrator reported `remaining=21.2s` — meaning some other clock consumed ~1160 s that isn't captured in the per-event log lines. Hypotheses: prior wave's wall time bleeding into this task's budget? Worktree checkpoint replay? Graphiti context loading at the start of Player invocation (we see only Coach-side Graphiti logs in the tail)? This is a key thread to pull on.

## Goal

Produce a diagnostic report identifying:

1. **Why the Player didn't complete in 1200 s** — was it task complexity, SDK rate-limiting, recursion, or genuine work that needed more budget?
2. **Why phase 3/4/5 specialists never invoked** — was the Player still in earlier phases (Phase 2/2.5) when the ceiling hit, or did the orchestrator skip the specialist hand-offs?
3. **Where the missing ~1160 s of wall budget went** — reconstruct full wall-clock accounting from `events.jsonl` and per-turn timestamps.
4. **Whether the per-task `task_timeout` should auto-scale by complexity** — TASK-J004-013 has complexity=6 and 7 dependencies; smaller tasks needed nowhere near 1200 s.
5. **Whether the `min=600s` turn-2 gate should be context-aware** — terminating a task whose first turn ate the ceiling forecloses *any* recovery, even one that a single small fix-turn could provide.
6. **Whether TASK-J004-013 should have been split pre-flight** — Phase 2.5 complexity evaluation is supposed to flag oversized tasks; if it ran here, why didn't it fire?
7. **Side observation: the Coach SDK-test-execution opaque-stderr issue** — file separately if confirmed.

A prioritised remediation plan should follow, scoped to GuardKit. **No changes proposed to Jarvis** — fixes must live in GuardKit so all consumers benefit (same constraint as TASK-REV-FA04).

## Source Artefacts (read these first)

### Run-2 evidence
- Failing run history: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J004-702C-run-2-history.md` (3105 lines, 516 KB)
- Run-2 review summary: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-J004-702C/review-summary.md`
- Wall-clock event stream: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl` (canonical timing source)
- TASK-J004-013 task definition: `.guardkit/worktrees/FEAT-J004-702C/tasks/design_approved/TASK-J004-013-lifecycle-startup-and-shutdown-wiring.md`

### TASK-J004-013 turn artefacts (under `.guardkit/worktrees/FEAT-J004-702C/.guardkit/autobuild/TASK-J004-013/`)
- `player_turn_1.json` — what the Player actually produced (file lists, agent invocations, tools used)
- `coach_turn_1.json` — Coach decision JSON (criteria_verification, requirements, validation_results)
- `task_work_results.json` — task-work delegation report (workflow_mode, agent_invocations_validation, ac_promises)
- `specialist_results.json` — orchestrator-side specialist invocation records (Phase 4/5)
- `turn_context.json` — context provided to Player at turn start
- `turn_state_turn_1.json` — turn-state snapshot
- `checkpoints.json` — worktree checkpoints

### Comparison: tasks that succeeded across run 2
- TASK-J004-011 / TASK-J004-012 (Wave 4) — both `task-work` mode, 1-turn approvals, SDK turns 91/92 each
- TASK-J004-006 (Wave 2) — 50 SDK turns, 1-turn approval
- TASK-J004-009 (Wave 3) — 66 SDK turns, 1-turn approval

What did successful Wave 2-4 tasks have that TASK-J004-013 didn't? AC count? Dependency count? Stack-specific specialist invocation pattern? The artefacts under each `*/...-013/` and `*/...-009/` etc. let you compare.

### Prior review (closed)
- TASK-REV-FA04 report: `.claude/reviews/TASK-REV-FA04-report.md`
- TASK-REV-FA04 task file: `tasks/in_review/TASK-REV-FA04-diagnose-jarvis-FEAT-J004-702C-autobuild-stall.md`
- Wave-1 implementation feature: `tasks/backlog/autobuild-stall-resilience/` (FEAT-ABSR-9C6E) — most subtasks completed

### Prior conversation context to integrate (per task brief)

This review must inherit the broader context from the FA04 conversation — specifically:

1. **Portfolio Python pinning**: forge / study-tutor / agentic-dataset-factory / specialist-agent are also LangChain-DeepAgents projects. We've not yet validated that the langchain 1.x rebaseline applies cleanly to them — that work was paused mid-survey when run 2's failure surfaced. The recommendation in this new review may need to factor in whether sibling repos exhibit similar complex-task timeout patterns.
2. **Verified langchain ecosystem**: jarvis run 2 confirms `langchain-core>=1.3,<2`, `langchain>=1.2,<2`, `langgraph>=1.1,<2`, `langchain-anthropic>=1.4,<2`, `langchain-openai>=1.2,<2`, `langchain-google-genai>=4.2,<5` resolves coherently on Python 3.14. nats-core PyPI confirmed broadened to `>=3.10`. Portfolio guide at `docs/guides/portfolio-python-pinning.md` exists.
3. **GuardKit-side TASK-REV-FA04 remediations now in place**: TASK-ABSR-A1B2 (smart-default `block`), TASK-ABSR-C3D4 (`environment_stall` sub-type), TASK-ABSR-E5F6 (DeepAgents template canonical pin + portfolio guide + `template-validate` rule), TASK-ABSR-7890 (Player↔Coach test-divergence investigation). TASK-ABSR-2468 (Coach env-class conditional approval) and TASK-ABSR-1357 (declarative phase-3 advisory suppression) were in progress at last check.
4. **The new review's failure mode is orthogonal to the FA04 fix**: it's a complexity-vs-budget mismatch, not an environment-vs-pin mismatch.

## Investigation Scope

### Primary threads (follow the evidence)

1. **Wall-clock reconstruction**. Read `events.jsonl` for FEAT-J004-702C/TASK-J004-013. Tabulate every event's timestamp and compute deltas. Identify the segment(s) that consumed the missing ~1160 s. Likely candidates: pre-flight context loading, worktree checkpoint operations, prior-wave tasks bleeding wall time into this task's accounting, Player Graphiti context loading.

2. **Player turn 1 forensics**. Read `player_turn_1.json` and `task_work_results.json`. Determine:
   - How many SDK turns did the Player actually consume? (run-2 history shows `101 HIT` for J004-013 in the SDK Turns column — this is the SDK *ceiling* hit count, not work units)
   - What tool calls did it make? (the run-2 log shows only `ToolUseBlock Write input keys` events — does the player_turn_1.json record more granular tool invocations?)
   - Did the Player attempt to invoke phase-3/4/5 specialists at all? (the agent-invocations advisory says "missing phases 3, 4, 5" — confirm against `task_work_results.agent_invocations_validation`)
   - Was the Player stuck in a planning-phase loop (Phase 2/2.5 re-runs) or in implementation (Phase 3) work?

3. **Specialist-invocation timing**. The warning explicitly says `run_specialist(test-orchestrator) failed for TASK-J004-013: SDKTimeoutError: Agent invocation exceeded 1200s timeout`. This means the orchestrator DID try to invoke test-orchestrator (Phase 4) but the SDK call timed out at 1200 s. Was this SDK call started *during* or *after* the Player invocation? Is the 1200 s ceiling shared between Player and specialists, or per-invocation?
   - File: `guardkit/orchestrator/specialist_invocations.py` — read `run_specialist` to see the timeout configuration.
   - Cross-ref with the Player ceiling at `guardkit/orchestrator/agent_invoker.py:[TASK-J004-013] SDK timeout: 2399s (base=1200s, mode=task-work x1.5, complexity=4 x1.4, budget_cap=2399s)` — wait, the run-1 log showed `SDK timeout: 2399s` for J004-004 with `complexity=4`. Run 2's J004-013 has `complexity=6` — what timeout was actually used? Confirm in run-2 history near the `SDK invocation starting` line for J004-013.

4. **Compare against the SDK Turns table** in run-2 review-summary:
   - J004-011: 91 SDK turns, 1-turn approval
   - J004-012: 92 SDK turns, 1-turn approval
   - J004-013: 101 SDK turns + ceiling HIT, FAILED

   The SDK ceiling default is `max_turns=30` for the orchestrator's outer loop, but the Player's *internal* `task-work` SDK invocation has its own `max_turns: 100` (per the run-1 history line `[TASK-J004-013] Max turns: 100`). 101 hits means the Player ran 100 SDK turns and the 101st triggered the ceiling. Is 100 SDK turns enough for a complex integration task? Compare against tasks that succeeded with 91/92 — TASK-J004-013 didn't have *that* much more work to do, so why couldn't it finish?

5. **Phase 2.5 complexity evaluation**. TASK-J004-013 has `complexity: 6`. Per `installer/core/commands/lib/agent_invocation_validator.py` and `guardkit/models/task_types.py`, complexity 6 should be in the QUICK_OPTIONAL review band — not flagged for split. **Should it have been higher?** The task has 7 dependencies and 9 ACs. Was complexity scoring too lenient? Did Phase 2.5 actually run for this task during the design phase, or was it skipped because the feature was generated by `/feature-plan` from review TASK-REV-22CF?

6. **Turn-2 gate (`min=600s`)**. Locate the gate in `guardkit/orchestrator/autobuild.py` (search for `min=600s` or `min_remaining`). Determine:
   - Is 600 s a hard-coded constant or configurable?
   - What's the rationale for that specific minimum?
   - Could the gate be relaxed to "if remaining > 0 and Coach has actionable feedback, attempt turn 2"?
   - Is there a way to extend the per-task budget when turn 1 hit the SDK ceiling but produced significant partial work?

7. **The Coach SDK-test-execution opaque-stderr issue (sidequest)**. `Command failed with exit code 1 (exit code: 1) Error output: Check stderr output for details` is uninformative. The subprocess fallback worked (3.3 s, tests passed). Is the SDK execution path actually broken on the Mac/3.14 path? Worth filing TASK-REV-* if confirmed — but secondary to this review's main thread.

### Secondary thread: cross-task budget bleed

Wave 2 of run 2 completed in some duration with TASK-J004-005, -006, -007, -008, -010 in parallel. Wave 5 only had TASK-J004-013. Wave 4 ended; Wave 5 started; TASK-J004-013 wall budget started counting. **Did anything between Wave 4 ending and Wave 5 task execution starting consume time charged to TASK-J004-013?** Worktree state operations, between-wave bootstrap, checkpoint manager init — all happen between waves. Read `events.jsonl` for the Wave 4 → Wave 5 transition.

### Tertiary thread: between-wave bootstrap stress

Each between-wave bootstrap re-runs `_bootstrap_environment` (per `feature_orchestrator.py:1855`). With the new `bootstrap_failure_mode=block` smart default, every wave entry gates on `requires-python` precheck. This is fine and fast, but: does the bootstrap call do any expensive work (pip install) on Wave 5 entry that didn't happen on Wave 1? Wave 2 work likely added the `nats-py` and `graphiti-core` dependencies to the worktree's pyproject.toml; Wave 3+ would see new manifest content and trigger a fresh install pass. Was Wave 5's bootstrap install fast or slow? Read run-2 history for the Wave 4→5 boundary.

## Acceptance Criteria

- [ ] Wall-clock budget for TASK-J004-013 reconstructed from `events.jsonl` and matched against `task_timeout=2400s`. The missing ~1160 s identified.
- [ ] Root cause(s) for the Player SDK ceiling hit identified with evidence from `player_turn_1.json` and `task_work_results.json` (genuine task complexity vs. specialist-invocation deadlock vs. context overflow vs. other).
- [ ] Recommendation on whether `task_timeout` should auto-scale with complexity — including the proposed scaling formula (e.g., `task_timeout = base * (1 + complexity/10)` or similar) and the affected file(s) (likely `guardkit/orchestrator/feature_orchestrator.py` and/or `guardkit/orchestrator/autobuild.py`).
- [ ] Recommendation on whether the Player's `max_turns: 100` ceiling should also auto-scale.
- [ ] Recommendation on whether the `min=600s` turn-2 gate should be relaxed/configurable, and the affected file (likely `guardkit/orchestrator/autobuild.py`).
- [ ] Recommendation on whether TASK-J004-013 should have been split pre-flight by Phase 2.5 — and if so, what complexity-evaluation tweak would have caught it.
- [ ] Comparison narrative: TASK-J004-011 / -012 succeeded at 91/92 SDK turns with 1-turn approval. What was structurally different about -013 that made it need more turns?
- [ ] Identification of whether the Coach SDK-test-execution opaque-stderr issue is a real defect (file separate review task if so).
- [ ] Prioritised remediation roadmap with regression analysis for each proposed change (test scope, blast radius, opt-out path).
- [ ] No changes proposed to the Jarvis repo — fixes must live in GuardKit.
- [ ] Report saved to `.claude/reviews/TASK-REV-9D13-report.md` (per `/task-review` convention).

## Out of Scope

- Implementing fixes — that comes via follow-up `/task-create` + `/task-work` tasks generated from this review's recommendations.
- Re-investigating the langchain trapdoor (closed by TASK-REV-FA04 + ADR-ARCH-010-rev2; confirmed working in run-2 Waves 1-4).
- Resuming the Jarvis autobuild — that's a tactical decision the user makes after this review identifies the right remediation. Two plausible paths:
  - **(a)** Apply this review's GuardKit-side fixes, then `[U]pdate` the worktree and resume from Wave 5.
  - **(b)** Split TASK-J004-013 into 2-3 smaller subtasks in Jarvis, commit on the autobuild branch, and resume.
  Either is OK — the review's job is to make the right path obvious.
- Any portfolio-rollout work for the langchain pinning to siblings (forge / study-tutor / agentic-dataset-factory / specialist-agent). That work is paused pending this review; once 9D13 lands, the portfolio rollout proceeds with empirical proof from the full run-2 + 9D13-fixes pipeline.
- Cross-review work on the Coach SDK-test-execution path (file separately if confirmed by this review).

## Suggested Workflow

```bash
/task-review TASK-REV-9D13 --mode=diagnostic
# Read the artefacts under "Source Artefacts" first — events.jsonl is the canonical timing source.
# Cross-reference with player_turn_1.json + coach_turn_1.json + task_work_results.json for TASK-J004-013.
# Compare against TASK-J004-011 / -012 / -006 / -009 (successful task-work-mode tasks) to isolate
# what made -013 different.
# Use Grep/Read across guardkit/orchestrator/{autobuild.py, agent_invoker.py, specialist_invocations.py,
# feature_orchestrator.py} for the timeout / ceiling / turn-2 gate logic.
# Produce the report; surface checkpoint for [A]ccept / [I]mplement / [R]evise.
```

## Notes for the reviewer

- The previous review (TASK-REV-FA04) deliberately kept its scope to "the trapdoor" and explicitly deferred orchestrator complexity/timeout questions. This review picks them up.
- The `autobuild-stall-resilience` feature (FEAT-ABSR-9C6E) is GuardKit's existing landing zone for autobuild-resilience improvements. New tasks generated from this review's recommendations would fit naturally there as Wave 3+.
- Cross-reference `[Graphiti] graphiti-knowledge-graph.md` query patterns when looking for prior similar incidents — the `guardkit__task_outcomes` group may have useful priors.
- This task itself is `task_type: review` and is expected to take ≤2 hours of focused work. If the wall-clock reconstruction reveals the budget bleed is itself a multi-hour rabbit hole, scope down to the actionable subset and file follow-ups.
