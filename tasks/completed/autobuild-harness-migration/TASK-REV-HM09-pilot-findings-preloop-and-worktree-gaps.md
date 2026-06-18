---
id: TASK-REV-HM09
title: Review pre-loop harness bypass (F1) + worktree-manager cwd-branch gap (F4) surfaced by TASK-HMIG-009 pilot
task_type: review
status: completed
resolution: delivered
completed: 2026-06-18
completed_location: tasks/completed/autobuild-harness-migration/
created: 2026-05-27T14:55:00Z
updated: 2026-06-18T16:15:00Z
priority: critical
complexity: 6
deadline: 2026-06-10
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-009
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
decision_required: true
review_results:
  mode: architectural
  depth: focused
  findings_count: 2          # F1 + F4 (8 supporting findings cross-referenced from parent canary-analysis)
  recommendations_count: 4   # F1(i), F4(i), HMIG-009 split A/B  (F2 reframed inline as model-swap, no separate task)
  decision: refactor
  report_path: .claude/reviews/TASK-REV-HM09-review-report.md
  recommended_tasks:
    - TASK-HMIG-006.4    # F1 fix — pre-loop adapter migration (5-7h)
    - TASK-FIX-WTBC      # F4 fix — cwd-HEAD CLI plumbing (3-4h, landed 2026-05-27)
    - TASK-HMIG-009A     # partial canary, post-F1 (includes F2-resolution preflight)
    - TASK-HMIG-009B     # full canary, post-all (optional)
  recommended_path: partial-close    # Path 2 from §8 (post-correction)
  correction_history:
    - applied: 2026-05-27
      summary: "v1: F2 reframed from parser-config audit to model-swap incident. Canary-set edited in-place to revert qwen3-coder-30b → qwen-coder-next. TASK-OPS-LSPC deleted; verification folded into TASK-HMIG-009A preflight ACs 001A-001D."
      outcome: "Preflight AC-001A (2026-05-27) caught that qwen-coder-next was documented but not deployed on live GB10 llama-swap. Cheap preflight worked as designed."
    - applied: 2026-06-02
      summary: "v2: After ~1 week of operator llama-swap reconfig + benchmark/forum research, model choice revised to qwen36-workhorse (already LIVE, serves jarvis-reasoner/forge/autobuild/dataset-factory per gb10-memory-budget-and-macbook-offload.md:37). Canary-set model_choice_correction_v2 block added; TASK-HMIG-009A unblocked."
      outcome: "TASK-HMIG-009A status backlog (unblocked); preflight ACs reframed against qwen36-workhorse; AC-001B is the new load-bearing post-reconfig gate."
    - applied: 2026-06-03
      summary: "v3: AC-001D's 3 iterations exposed that the LangGraph Wave-2 harness is a skeleton (never integration-tested). Layers 1+2 fixed (MODELPLUMB + LGTOOLS); layers 3+4 require TASK-HMIG-002R (named in parent review on 2026-05-19 but never filed) + new TASK-HMIG-002R-PROMPT (prompt adaptation, surfaced by AC-001D run 3)."
      outcome: "TASK-HMIG-009A status blocked on 002R + 002R-PROMPT. Cutover margin collapsed; operator decision per 2026-06-03 is to push 002R+002R-PROMPT this week."
    - applied: 2026-06-03
      summary: "v3.1 (correction-of-correction): Operator caught a cross-repo coordination error in v3. TASK-HMIG-002R has been COMPLETE in guardkitfactory since 2026-05-20 (factories build_autobuild_backend + build_autobuild_permissions exist + exported + tested). Actual gap is consumer-side wiring in guardkit's selector.py. Fix scope collapsed 12h → ~1h. Filed TASK-FIX-002R-CONSUME. Deleted duplicate TASK-HMIG-002R from guardkit/backlog. Re-scoped TASK-HMIG-002R-PROMPT to speculative."
      outcome: "TASK-HMIG-009A blocked on TASK-FIX-002R-CONSUME instead. Cutover margin restored to comfortable (~1h dev + 10h compute against 12-day window). Process gap noted: check ../guardkitfactory/tasks/{completed,backlog}/ before filing cross-repo tasks."
    - applied: 2026-06-03
      summary: "v3.2 (success): AC-001D run 6 PASSED — LangGraph end-to-end APPROVED in 1 turn (4 files created, 16 modified, 2 tests passing, honesty 0.96, ~13.5min total — ~35% faster than SDK). The 6-run iteration journey resolved 5 layers (MODELPLUMB + LGTOOLS + 002R-CONSUME + 002R-NOPERMS + 002R-NOVMODE); the predicted 6th layer (Coach/specialist prompt-tool-name mismatch) dissolved because DeepAgents' runtime tool advertisement was sufficient. TASK-HMIG-002R-PROMPT deleted."
      outcome: "TASK-HMIG-009A unblocked; ready for AC-003 (12-run batch). Cutover-decision feasible against 2026-06-15. Three quality signals to track in batch: LLM-Coach-override-of-honesty-oracle, Criteria-Progress-0-with-Coach-approval, /v1/responses retries."
related_tasks:
  - TASK-HMIG-006   # Wave-2 dispatch refactor that left pre-loop unmigrated
  - TASK-HMIG-009   # Canary that surfaced the gaps
  - TASK-REV-PL01   # Earlier review about whether to keep pre-loop at all
tags:
  - review
  - autobuild
  - langgraph-migration
  - harness-adapter
  - pre-loop
  - worktree-manager
  - pre-canary-blocker
falsifier: "After fix: a smoke run of `guardkit autobuild task TASK-GLI-004` with `GUARDKIT_HARNESS=langgraph` invoked from a worktree on `canary-TASK-GLI-004-fixture` shows (a) no claude_agent_sdk.subprocess_cli log line during the design phase, AND (b) the inner autobuild worktree's HEAD matches the canary worktree's branch tip (7f2c02cf), not main HEAD. Both conditions verifiable in a single ~5min smoke."
---

# Review: Pre-loop harness bypass + worktree-manager cwd-branch gap (TASK-HMIG-009 pilot)

## Description

The TASK-HMIG-009 canary pilot (2026-05-27, smokes v1–v7) surfaced two
architectural gaps that block the canary from producing meaningful
comparative data and have implications beyond the canary itself:

- **F1: Pre-loop design phase bypasses the harness adapter.** `autobuild
  task` with pre-loop ON hard-routes the design phase through
  claude-agent-sdk via `task_work_interface`, regardless of
  `GUARDKIT_HARNESS`. TASK-HMIG-006 migrated the Player-Coach loop
  dispatch but not the pre-loop path. With pre-loop default-ON
  for `guardkit autobuild task`, every production AutoBuild invocation
  silently uses claude-agent-sdk for the design phase, bypassing the
  migration target.

- **F4: Worktree manager ignores the cwd's current branch.** When
  `guardkit autobuild task` is invoked from a git worktree on a
  non-main branch, the worktree manager still creates the
  `autobuild/<task_id>` branch from main HEAD (verified by inspecting
  the inner worktree's HEAD vs the canary worktree's branch tip).
  This defeats the fixture-baseline strategy in TASK-HMIG-009 and
  affects any caller that depends on running autobuild from a non-main
  branch (e.g. parallel feature-build).

Both findings, plus six supporting findings (F2–F8: substrate
tool-call wiring, Coach honesty verification working under local
Qwen, Player honesty failures common under local Qwen, etc.) are
documented in [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md)
§3.

This review's purpose: decide whether to (a) close F1+F4 within the
2026-06-15 cutover window, or (b) narrow the canary scope to
`--no-pre-loop` + backlog-task picks and accept a partial-canary
verdict.

## Acceptance Criteria

- [ ] **AC-001** — Diagnose F1's exact code path: confirm
      `guardkit/orchestrator/quality_gates/task_work_interface.py`
      does NOT consult `guardkit/orchestrator/harness/selector.py` for
      pre-loop design-phase dispatch. Capture the dispatch chain from
      `autobuild.py:_pre_loop_phase` → ... → `subprocess_cli` in a
      sequence diagram annotated with the missing adapter seam.
- [ ] **AC-002** — Diagnose F4's exact code path: trace
      `guardkit/worktrees/manager.py:create()` to determine why the
      inner `autobuild/<task_id>` branch is created from main HEAD
      rather than from the calling cwd's HEAD. Identify whether this
      is a bug, an intentional design choice (and if so, document the
      rationale), or an interaction between the CLI's base_branch
      detection and the manager's `git worktree add` invocation.
- [ ] **AC-003** — For F1, recommend one of three remediations with
      a defensibility argument:
      (i) extend TASK-HMIG-006's adapter coverage to the pre-loop
      design phase (architectural completion);
      (ii) document the limitation as out-of-scope and adjust
      TASK-HMIG-009's falsifier framing accordingly;
      (iii) deprecate the pre-loop entirely (cross-link with
      TASK-REV-PL01).
- [ ] **AC-004** — For F4, recommend one of two remediations with a
      defensibility argument:
      (i) fix the worktree manager to honour the cwd's HEAD when
      creating the inner branch;
      (ii) leave behaviour and document the limitation in the canary
      methodology, with the canary set narrowed to backlog tasks that
      don't need fixture-branch isolation.
- [ ] **AC-005** — For each recommended remediation in AC-003 and
      AC-004, estimate effort to landed-and-tested in hours, identify
      the SDK/LangGraph regression-test surface that needs to come
      with the fix, and identify the single owner.
- [ ] **AC-006** — Cross-reference F2 (pre-loop SDK + local Qwen
      tool-call failure) to the GB10-side llama-swap tool-call parser
      config audit. This review does not fix F2 (operator-side
      infrastructure), but it must surface the dependency so the
      review owner knows the pre-loop fix alone is necessary-but-
      not-sufficient for local-Qwen autobuild to work.
- [ ] **AC-007** — Recommend a TASK-HMIG-009 scope revision (or
      cancellation, or split into HMIG-009A/B) reflecting which
      remediations land before the 2026-06-15 cutover deadline.
      Cross-link with TASK-HMIG-010 readiness.
- [ ] **AC-008** — Produce a one-page decision brief for the operator
      summarising the F1+F4 closure cost/benefit vs the partial-canary
      alternative, with a recommended path.

## Inputs

- [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md)
  §3 (full F1–F8 evidence with smoke-run pointers)
- Pilot smoke artefacts at
  `.guardkit/autobuild/TASK-REV-HMIG-canary/sdk/TASK-GLI-004/run_1/`
  and `.guardkit/autobuild/TASK-REV-HMIG-canary/langgraph/TASK-GLI-004/run_1/`
  (stderr.log, coach_turn_*.json, player_turn_*.json, sdk_debug/ — last
  one only for v7's loop run)
- Parent review: [`.claude/reviews/TASK-REV-HMIG-review-report.md`](../../../.claude/reviews/TASK-REV-HMIG-review-report.md),
  §§4 (touch-point map), 5.3+5.4 (Pattern 2 + Pattern 3), 7.3 (Wave 3
  sequencing), 11 (falsifier)
- TASK-HMIG-006 completed task file: `tasks/completed/2026-05/TASK-HMIG-006-refactor-agent-invoker-cross-repo-dispatch.md`
  (what was migrated; conversely, what was left behind)
- TASK-REV-PL01: [`tasks/backlog/TASK-REV-PL01-preloop-architecture-review.md`](../TASK-REV-PL01-preloop-architecture-review.md)
  (earlier review about whether to keep pre-loop)

## Out of Scope

- **F2 (llama-swap tool-call parser config on GB10)** — this is an
  operator-side infrastructure issue requiring GB10 shell access.
  File as a separate operator task. This review surfaces the
  dependency in AC-006 but doesn't fix it.
- **F6 (Player honesty failure rate on local Qwen)** — substrate
  quality finding; not actionable here beyond noting it in AC-007's
  scope revision.
- **The 18-rep canary execution itself** — paused by definition until
  this review's AC-003 + AC-004 close.

## Notes

- This review's outputs (AC-003, AC-004, AC-007, AC-008) directly
  inform the operator's go/no-go decision for the 2026-06-15 Wave 4
  cutover. The deadline on this review is 2026-06-10 to preserve
  a 5-day validation margin per the parent review §1.4.
- The single biggest scope question is AC-003 choice (i) vs (ii):
  is the pre-loop in-scope for the LangGraph migration or not? If
  (i), HMIG-006's "complete" claim is contested. If (ii), the
  migration explicitly leaves the design phase on claude-agent-sdk
  and the cutover plan has to account for that.
- AC-002's worktree-manager diagnosis may also touch
  `guardkit/cli/autobuild.py:1190-1199` (the `git rev-parse
  --abbrev-ref HEAD` call) and `guardkit/orchestrator/autobuild.py`
  call sites around `_setup_phase`. The bug surface is small but the
  blast radius (every non-main-branch autobuild invocation) is large.
