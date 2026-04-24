---
id: TASK-REV-JMBP
title: Analyse jarvis FEAT-J002 autobuild failure on MacBook Pro — Coach agent-invocations gate stall (sibling of TASK-REV-E4F5)
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
decision_required: true
created: 2026-04-24T00:00:00Z
updated: 2026-04-24T14:30:00Z
previous_state: in_progress
state_transition_reason: "Review complete, [I]mplement executed — TASK-FIX-7A07 created, TASK-FIX-7A04 amended, Graphiti seeded"
review_results:
  mode: architectural
  depth: standard
  findings_count: 12
  recommendations_count: 4
  decision: D1_expand_7A0x_scope
  decision_checkpoint: implement
  report_path: docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md
  preamble_path: docs/reviews/TASK-REV-JMBP-graphiti-preamble.md
  completed_at: 2026-04-24T14:30:00Z
  artefacts_produced:
    - "tasks/backlog/autobuild-sdk-stall-resilience/TASK-FIX-7A07-coach-agent-invocations-stall-classification.md (new)"
    - "tasks/backlog/autobuild-sdk-stall-resilience/TASK-FIX-7A04-bootstrap-hardfail-gate.md (amended with AC-REQPY-PRECHECK)"
    - "tasks/backlog/autobuild-sdk-stall-resilience/README.md (updated)"
    - "tasks/backlog/autobuild-sdk-stall-resilience/IMPLEMENTATION-GUIDE.md (updated with W2-3)"
  graphiti_seeded:
    - "guardkit__project_decisions: Review findings: TASK-REV-JMBP (architectural)"
    - "guardkit__task_outcomes: Review outcome: TASK-REV-JMBP"
    - "guardkit__project_decisions: AutoBuild implementation_mode bimodal routing rule"
priority: high
complexity: 6
tags: [architecture-review, autobuild, coach-validation, agent-invocations-gate, feedback-stall, context-pollution, macbook-pro, jarvis, sibling-to-e4f5, stall-analysis]
related_to: TASK-REV-E4F5
parent_review: TASK-REV-E4F5
related_tasks:
  - TASK-REV-E4F5
  - TASK-REV-MCPS
  - TASK-FIX-7A01
  - TASK-FIX-7A02
  - TASK-FIX-7A03
  - TASK-FIX-7A04
  - TASK-FIX-7A05
  - TASK-DOC-7A06
  - TASK-FIX-7A07
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse jarvis FEAT-J002 autobuild failure on MacBook Pro

## Context

Run artefact: [docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md](../../docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md) (3326 lines of captured DEBUG log).

Sibling runs on **GB10** (`promaxgb10-41b1`): [forge-run-1.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-1.md), [forge-run-2.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-2.md). Those were reviewed in [TASK-REV-E4F5](../in_review/TASK-REV-E4F5-analyse-forge-autobuild-failures-gb10.md) (report at [.claude/reviews/TASK-REV-E4F5-review-report.md](../../.claude/reviews/TASK-REV-E4F5-review-report.md)) and produced the yet-unimplemented [autobuild-sdk-stall-resilience](autobuild-sdk-stall-resilience/README.md) feature folder (TASK-FIX-7A01 through TASK-DOC-7A06).

This run is **on a different host (MacBook Pro, Python 3.14.2) and a different project (jarvis FEAT-J002)** but produced an `UNRECOVERABLE_STALL` summary shape that superficially resembles the GB10 failures. A focused review is needed to determine whether:

1. This is the **same class-of-defect** as TASK-REV-E4F5 (and the 7A0x fixes would address it), or
2. A **different class** (Coach `agent-invocations` gate systematically rejecting Player output that is otherwise successful), or
3. A **compound** of both, requiring additional scope beyond the stall-resilience feature.

## Problem Statement

On 2026-04-24, `guardkit autobuild feature FEAT-J002 --verbose --max-turns 30` was run from `/Users/richardwoollcott/Projects/appmilla_github/jarvis` on Richards-MBP.

### Two-phase run: what actually happened

**First invocation** (log line 7): failed instantly with the GB10-unrelated namespace-collision symptom:

```
Error: Claude Agent SDK not available
AutoBuild requires the Claude Agent SDK.
```

This is the TASK-REV-MCPS bug (internal `installer/core/lib/mcp/` shadowing Anthropic's `mcp` PyPI package via the `greenfield_qa_session.py` / `spec_drift_detector.py` `sys.path.insert` anti-pattern). After the user implemented the [TASK-FIX-MCPS.{1,2,3} subtasks](mcps-namespace-collision/README.md), the re-invocation at log line 22 started successfully.

**Second invocation** (log line 22+): ran to completion but terminated as `FEATURE RESULT: FAILED` after 43m 2s with 14/23 tasks completed, 2 failed.

### Failure shape (what distinguishes this from GB10)

- **Wave 1 (7 tasks)** — all 7 approved in 1 turn each.
- **Wave 2 (9 tasks)** — 7 approved in 1 turn, **2 failed with `UNRECOVERABLE_STALL`**:
  - `TASK-J002-008` (Implement read-file tool) — 6 turns, 10 SDK turns, Feedback-stall exit.
  - `TASK-J002-013` (Implement dispatch-by-capability tool) — 3 turns, 50 SDK turns (near ceiling), context-pollution exit.

**Critical observation**: unlike the GB10 runs, the **Player DID execute successfully on every turn** (creating 53-92 files per turn, 1 test passing on some turns). The stall is entirely inside the **Coach** layer:

```
WARNING:guardkit.orchestrator.quality_gates.coach_validator:
  Agent-invocations gate rejected TASK-J002-008: missing phases 4, 5
WARNING:guardkit.orchestrator.quality_gates.coach_validator:
  Agent-invocations gate rejected TASK-J002-013: missing phases 3, 5
```

The rejection is **identical across turns** (feedback signature `c6bb0e9b` stable for J002-008 across 3 turns). The feedback-stall detector fires correctly (`"identical feedback with no criteria progress"`), but the summary renders with the same misleading hint as the GB10 runs:

```
Suggested action: Review task_type classification and acceptance criteria.
```

This is the **same misattribution** that TASK-FIX-7A02 (player_invocation_stall classification) is supposed to fix — except here the Player DID run. The rejection is a *legitimate* Coach disagreement with Player's evidence, not an SDK-layer failure. So the misclassification is arguably *worse* here: it blames the task classification when the real signal is "Coach's agent-invocations gate is rejecting 2/16 task-work results for substantive reasons that the stall classifier cannot distinguish from an SDK-never-started stall."

### Secondary signal: Python / bootstrap mismatch

Lines 70-86:

```
INFO:guardkit.orchestrator.environment_bootstrap:Running install for python (pyproject.toml):
    /usr/local/bin/python3 -m pip install -e .
WARNING:guardkit.orchestrator.environment_bootstrap:Install failed for python (pyproject.toml)
    with exit code 1:
stderr: ERROR: Package 'jarvis' requires a different Python: 3.14.2 not in '<3.13,>=3.12'
...
⚠ Environment bootstrap partial: 0/1 succeeded
```

The MBP's `/usr/local/bin/python3` is Python 3.14.2; jarvis's `pyproject.toml` pins `<3.13,>=3.12`. Bootstrap fails cleanly with 0/1 succeeded, then **the orchestrator proceeds anyway** — exactly the latent hazard TASK-FIX-7A04 (bootstrap hard-fail gate, `bootstrap_failure_mode=block`) is designed to prevent.

The orchestrator didn't fall back to a PEP 668 virtualenv the way the GB10 forge run did (log line 57 of [forge-run-2.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-2.md)) — presumably because the MBP host isn't PEP 668-marked. So on MBP the 0/1 failure is accepted silently and whatever Python ends up on PATH is what Coach's `pytest` invocations will use. TASK-FIX-7A05 (wire bootstrap venv into Coach pytest) is clearly relevant here.

### Why this deserves its own review

TASK-REV-E4F5 closed at [I]mplement with Full-scope (subtasks 7A01-7A06). Those remain unimplemented. This run provides **independent corroboration of the bootstrap-gate hazard (R4a/F6)** and the **summary-hint misattribution (R2/F3+F4)**, but it also surfaces **a new failure class** (Coach agent-invocations gate systematic rejection) that the 7A0x fixes do not address. The two possibilities are:

- **(A) Superset**: this run is evidence the 7A0x scope is right and needs expanding to include a "Coach feedback-stall classification subtype" rule (distinguish "SDK never started" stall from "Coach rejects consistently" stall from "Coach accepts but tests fail" stall).
- **(B) Parallel**: the Coach-gate issue is a separate review/fix track. The 7A0x tasks should ship as-is; this review opens a new feature folder (proposed: `coach-validation-stall-root-cause`).

The reviewer must pick one.

## Scope

**User intent for this task** (captured verbatim from the /task-create invocation): *"please create a review task to analyse the failing autobuild run for the jarvis feature on this macbook pro … note the other reviews in the same directory are from autobuild runs on the GB10, a review TASK-REV-E4F5 has created associated tasks … which are not yet implemented."*

That framing binds the review to explicit comparison with TASK-REV-E4F5, and explicit recognition that the 7A0x tasks have not yet landed. Any recommendation here must reason about the counterfactual: *would 7A01-7A06, once implemented, have changed this run's outcome?*

### In-Scope

**Workstream A — Graphiti preamble (mandatory, same shape as TASK-REV-MCPS Workstream A):**

Before any remediation proposal, query Graphiti for what the graph already knows. Minimum queries:

```
mcp__graphiti__search_nodes("Coach agent-invocations gate missing phases",
    group_ids=["guardkit__project_decisions", "guardkit__project_architecture"])

mcp__graphiti__search_memory_facts("feedback stall identical feedback signature",
    group_ids=["guardkit__project_decisions", "guardkit__task_outcomes"])

mcp__graphiti__search_nodes("task-work results phases missing agent invocations",
    group_ids=["guardkit__project_decisions", "guardkit__task_outcomes"])

mcp__graphiti__search_nodes("context pollution no passing checkpoint unrecoverable stall",
    group_ids=["guardkit__project_decisions"])

mcp__graphiti__search_nodes("environment bootstrap PEP 668 venv Coach pytest interpreter",
    group_ids=["guardkit__project_decisions"])
```

Record findings in `docs/reviews/TASK-REV-JMBP-graphiti-preamble.md` **before** Workstreams B-E. Absence-of-knowledge is itself a finding.

**Workstream B — Reproduce the two distinct failure modes from the log:**

1. `TASK-J002-008` — **feedback-stall** exit: 3 consecutive turns of identical `agent-invocations` rejection signature (`c6bb0e9b`) → `autobuild.py` feedback-stall detector fires after turn 3 (actually exits after turn 6 per the summary).
2. `TASK-J002-013` — **context-pollution** exit: 3 consecutive test-fail checkpoints with no passing checkpoint → `worktree_checkpoints.py` exits the loop.

For each failure, extract from the log:
- The exact Coach feedback text (not just the truncated summary) from the `coach_turn_N.json` files in `.guardkit/autobuild/TASK-J002-{008,013}/` in the preserved jarvis worktree.
- The `task_work_results.json` shape that Coach's `agent-invocations` gate evaluated.
- Which specific `missing phases` (3, 4, 5) were reported per turn.

Produce a compare-and-contrast table of J002-008 and J002-013 against the 7 Wave-2 tasks that *were* approved in 1 turn (J002-006, 009, 010, 011, 014, 016, 018). Differentiating factors likely include: task complexity, number of ACs, involvement of Phase 3+4+5 agents (stack specialist, test-orchestrator, code-reviewer), presence/absence of tests in the task, evidence format.

**Workstream C — Root-cause the Coach `agent-invocations` gate false-positive vs true-positive:**

For both failing tasks, decide: is the Coach correct?

- **If correct** (Phases 4/5 truly were not invoked by Player): the fix is in the **Player** side (task-work orchestrator) and/or the SDK-level prompt that tells Player which phases to run. The gate is doing its job; Player is the defect.
- **If false-positive** (agent invocations happened but the gate's detection missed them): the fix is in the **gate** (detection logic or evidence format compatibility).
- **If ambiguous** (gate requires evidence Player never emits for legitimate reasons — e.g., a declarative task doesn't need Phase 4 agents): the fix is in the **quality gate profile** — the gate should be scoped by task_type and skip phases that don't apply.

Code to examine:
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `agent-invocations` gate implementation.
- `guardkit/orchestrator/agent_invoker.py` — how Player reports agent invocations in `task_work_results.json` (look for evidence shape mismatch).
- Coach's quality gate profile for `task_type: feature` (the profile log line `Using quality gate profile for task type: feature` fires for both failing tasks).

**Workstream D — Decide: does this run change the 7A0x scope, or open a new feature?**

For each of TASK-FIX-7A01 through TASK-DOC-7A06, answer:

| Task | Would landing it have changed this run's outcome? | Rationale |
|---|---|---|
| TASK-FIX-7A01 (pin SDK + log version) | ? | SDK ran successfully here — likely no impact |
| TASK-FIX-7A02 (player_invocation_stall classification) | ? | **Likely partial**: gives a better hint, but this isn't a player-invocation-stall — Player ran. A NEW classification may be needed: `coach_gate_stall` or `coach_feedback_stall` |
| TASK-FIX-7A03 (defensive SDK message handling) | ? | SDK messages landed cleanly — no impact |
| TASK-FIX-7A04 (bootstrap hard-fail gate) | ? | **Relevant**: would have stopped the run at 0/1 bootstrap failure before Wave 1 even started |
| TASK-FIX-7A05 (wire venv into Coach pytest) | ? | **Possibly relevant**: the 0/1 bootstrap means Coach pytest was running on whatever Python was on PATH (3.14) against a 3.12-pinned project |
| TASK-DOC-7A06 (runbook + graph seed) | ? | Documentation; adjacent but not determinative |

Conclude with one of three decision shapes:

- **D1: Expand the 7A0x scope** — add a sibling task (e.g., `TASK-FIX-7A07 — coach_feedback_stall classification` + gate-profile refinement per task_type) to the same feature folder. Rationale: the failure mode is a sibling of the misattribution problem 7A02 addresses.
- **D2: Separate feature** — open `coach-validation-stall-root-cause` (working title `FEAT-CVSR`) as a sibling feature. Rationale: the Coach-gate root-cause is orthogonal to the stall-resilience feature; mixing them would muddy review and slow both.
- **D3: Implement 7A0x first, then re-review** — the 7A0x tasks are in the queue and will land soon; defer this review's remediation decision until after they've landed and we can see whether the residual failure is still present.

**Workstream E — Python 3.14 / bootstrap interaction assessment:**

Separate from the Coach-gate root cause, decide:

- Does the MBP `/usr/local/bin/python3 → 3.14.2` mismatch need user-level remediation (install Python 3.12 via `pyenv` or similar) *independent* of TASK-FIX-7A04 landing?
- Would TASK-FIX-7A04 + TASK-FIX-7A05, once landed, have failed this run cleanly at the bootstrap step with a good error message? Or would they still have allowed the run to proceed?
- Is there a case for a pre-flight `--doctor`-style check that warns on Python mismatch *before* the bootstrap attempt, rather than relying on pip's error text?

**Workstream F — Classification of the "run completed with partial failure" shape:**

Unlike the GB10 runs (which exited at Wave 1 with total failure after 3 turns), this run completed **Wave 1 clean (7/7)** and reached Wave 2 before hitting 2 task-level stalls. With `stop_on_failure=True`, Wave 2's 2 failures triggered overall feature failure, but **14 of 23 tasks succeeded**. Evaluate:

- Is the user-facing feature-level "FAILED" verdict accurate given this partial success? Or should the final summary distinguish `all_stalled` from `mixed_partial`?
- Should `--resume` from this point re-run only the failed tasks, or replay their surrounding context? The feature logged `Next Steps: guardkit autobuild feature FEAT-J002 --resume` — is resume expected to handle this state?
- The two failing tasks have distinct stall exit paths (feedback-stall vs context-pollution). Does the review-summary `.guardkit/autobuild/FEAT-J002/review-summary.md` capture this distinction, or merge both into "unrecoverable_stall"?

### Out-of-Scope

- Implementing any Coach-gate fix in this review. Fix execution spawns from the [I]mplement checkpoint (per Workstream D decision).
- Re-running the 7A0x planning itself — those are decided; this review only evaluates counterfactual impact.
- Deep refactor of `coach_validator.py` — if a fix is scoped, it goes to its own subtask with its own architectural review.
- Python 3.14 compatibility work for jarvis — that's a jarvis-side concern, not a guardkit-side fix. In-scope only to the extent of "should guardkit fail fast vs warn-and-proceed".
- The MCP namespace collision itself (closed by TASK-REV-MCPS + TASK-FIX-MCPS.{1,2,3}). Confirmed not the root cause here since the re-run succeeded.

## Acceptance Criteria

- [ ] Workstream A complete: Graphiti preamble filed at `docs/reviews/TASK-REV-JMBP-graphiti-preamble.md` with ≥5 targeted queries. Absence-of-knowledge findings explicitly called out.
- [ ] Workstream B complete: for both J002-008 and J002-013, the exact Coach feedback text, `task_work_results.json` shape, and `missing phases` per turn are documented in the main review report. Compare-and-contrast table against the 7 Wave-2 tasks that approved.
- [ ] Workstream C complete: root-cause classification (correct / false-positive / ambiguous) decided per failing task with evidence. If any fix is proposed against `coach_validator.py` or `agent_invoker.py`, include risk table + test matrix + Graphiti pre-flight + post-flight plan per TASK-REV-MCPS format.
- [ ] Workstream D complete: per-7A0x-task counterfactual table filled in. Decision D1 / D2 / D3 chosen with explicit rationale.
- [ ] Workstream E complete: explicit recommendation on whether MBP Python 3.14 → 3.12 remediation is a user-side prerequisite or whether TASK-FIX-7A04/7A05 adequately handle it.
- [ ] Workstream F complete: decision on partial-success summary classification and resume semantics.
- [ ] Main review report filed at `docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md` with per-workstream sections.
- [ ] On [A]ccept: Graphiti seeded with (a) the Coach-feedback-stall classification pattern (if Workstream D picks D1 or D2), (b) retrospective episode linking this review to TASK-REV-E4F5 and TASK-REV-MCPS under a shared "autobuild stall taxonomy" theme.
- [ ] On [I]mplement: subtask shape depends on Workstream D decision. If D1: one or two additional tasks added to `autobuild-sdk-stall-resilience/`. If D2: new feature folder created with appropriate Wave structure. If D3: no subtasks; this review gets revisited after 7A0x lands.
- [ ] Decision block recorded: does this review block TASK-COH-RUN1 or any other downstream work? (Likely no — TASK-COH-RUN1 runs on GB10, not MBP; this run's MBP-specific issues don't gate it.)

## Implementation Notes

### Working hypothesis (confirm or revise in Workstream C)

- The Coach `agent-invocations` gate is almost certainly **correctly** detecting that Player did not invoke Phase 4 (test-orchestrator) and Phase 5 (code-reviewer) agents for J002-008 and J002-013. Evidence: 7 other Wave-2 tasks approved in 1 turn, suggesting the gate accepts valid output when agents genuinely are invoked.
- The question is **why** Player skipped those phases on those specific tasks. Likely candidates:
  - Task complexity pushes the SDK toward its turn ceiling (J002-013 used 50 SDK turns, near the 104-turn max seen in J002-014). Player may be compressing workflow to fit within budget.
  - Task-work's internal phase routing (`--mode=tdd` configured at the orchestrator) may skip phases under certain conditions (declarative? scaffolding?) — and the task_type classification may be wrong.
  - The task spec itself may not declare the phases in a shape the Player follows.

The summary hint *"Review task_type classification and acceptance criteria"* may accidentally be correct here — but only as a side-effect of the misattribution bug. Worth calling out explicitly.

### Cross-reference with TASK-FIX-7A02 specifically

TASK-FIX-7A02 was drafted for *SDK-never-started* stalls (Player never ran → summary should say `player_invocation_stall`, not `task_type`). Here the *opposite* situation applies: Player DID run, but Coach's gate produced identical feedback for 3+ turns without giving Player an actionable correction path. A complementary classification (`coach_feedback_stall` or `coach_gate_disagreement`) might be needed, with its own hint text like:

> *"Coach's agent-invocations gate rejected 3 consecutive turns with identical feedback. Inspect coach_turn_N.json for the specific missing-phases signal and either (a) verify Player is invoking all required phase agents or (b) adjust the quality gate profile for this task_type."*

This is a candidate scope expansion for TASK-FIX-7A02, or a new sibling task under the same feature.

### Cross-reference with TASK-REV-MCPS

The first CLI invocation (log line 8) hit the MCP namespace-collision symptom. The re-invocation succeeded. This is **empirical confirmation that TASK-FIX-MCPS.1 + TASK-FIX-MCPS.2 fixes are in effect on the MBP** — use this as evidence in the namespace-hygiene rule's post-flight Graphiti episode (TASK-FIX-MCPS.3 can cite this as a corroborating live run).

### Why a review and not a direct fix task

Three reasons:

1. **Ambiguity on correct vs false-positive**: whether `coach_validator.py` or `agent_invoker.py` is the defect hinges on reading the actual `coach_turn_N.json` files — which requires investigative work before any code change.
2. **Decision on scope (D1 / D2 / D3)**: whether to expand the 7A0x feature or open a sibling is a judgement call that needs explicit evidence gathering.
3. **Sibling-review pattern**: TASK-REV-MCPS + TASK-REV-STKB established a pattern where independent incidents trigger independent reviews that then cross-reference each other via shared meta-rules. Following that pattern keeps the knowledge graph coherent.

## Related

- **Sibling review (GB10 equivalent)**: [TASK-REV-E4F5](../in_review/TASK-REV-E4F5-analyse-forge-autobuild-failures-gb10.md) / [review report](../../.claude/reviews/TASK-REV-E4F5-review-report.md). Six tasks filed in [autobuild-sdk-stall-resilience/](autobuild-sdk-stall-resilience/README.md), **not yet implemented**.
- **Namespace collision (first-run blocker)**: [TASK-REV-MCPS](TASK-REV-MCPS-mcp-namespace-collision-diagnostic-and-fix-plan.md), subtasks in [mcps-namespace-collision/](mcps-namespace-collision/README.md). Fixes confirmed in effect for MBP by the re-invocation success at log line 22.
- **Namespace-hygiene rule**: [.claude/rules/namespace-hygiene.md](../../.claude/rules/namespace-hygiene.md).
- **Run log (primary evidence)**: [docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md](../../docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md).
  - Key lines: 70-86 (bootstrap 0/1), 2292-3092 (Coach agent-invocations rejections), 3092-3095 (feedback-stall fire), 3096-3125 (first UNRECOVERABLE_STALL summary, J002-008), 3210-3240 (second summary, J002-013), 3268-3326 (final feature summary).
- **Sibling GB10 runs**: [forge-run-1.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-1.md), [forge-run-2.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-2.md).
- **Prior related incident**: TASK-REV-8A08 (FEAT-486D / TASK-AD-004 stall, 2026-04-13) — first incident of the "SDK API error" hint branch, predecessor to the TASK-REV-E4F5 misattribution bug.
- **Preserved worktree for forensic inspection**: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-J002/` — contains `coach_turn_N.json` and `task_work_results.json` per failing task.
- **Graphiti integration reference**: [.claude/rules/graphiti-knowledge-graph.md](../../.claude/rules/graphiti-knowledge-graph.md).
