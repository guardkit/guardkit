Thanks please review the implementation task creation summary to check we have captured ALL the work that is required to get Autobuild working once and for all:
Implementation Structure Created

tasks/backlog/autobuild-stall-fixes/
├── README.md
├── IMPLEMENTATION-GUIDE.md
├── TASK-ASF-001-switch-sft001-direct-mode.md      (Phase 1, complexity 1)
├── TASK-ASF-002-preflight-falkordb-check.md        (Phase 1, complexity 2)
├── TASK-ASF-003-include-missing-criteria-feedback.md (Phase 2, complexity 3)
├── TASK-ASF-004-synthetic-report-observability.md  (Phase 2, complexity 2)
├── TASK-ASF-005-scope-test-detection.md            (Phase 3, complexity 4)
├── TASK-ASF-006-synthetic-report-enrichment.md     (Phase 3, complexity 5)
├── TASK-ASF-007-cooperative-thread-cancellation.md (Phase 4, complexity 6)
└── TASK-ASF-008-dynamic-sdk-timeout.md             (Phase 4, complexity 3)
Execution Strategy
PhaseTasksRiskDescription1ASF-001 + ASF-002ZeroUnblock FEAT-AC1A re-run (YAML change + pre-flight check)2ASF-003 + ASF-004LowFix feedback specificity + add synthetic report logging3ASF-005 then ASF-006MediumScope tests (R5) then enrich synthetic reports (R4-full)4ASF-007 + ASF-008Medium-HighCooperative thread cancellation + dynamic SDK timeout
Key Design Decisions from Your Diagrams
1. R4 split into R4-lite (ASF-004) and R4-full (ASF-006) — Diagram 4 showed synthetic reports feed two consumers; phased approach reduces risk
2. R5 before R4-full — Diagram 5 caught the false approval interaction risk
3. Cancellation checks in both Player AND Coach phases — Diagram 6 state machine showed the gap
4. Ghost thread interference (Q8) addressed by both ASF-002 (pre-flight) and ASF-007 (cancellation)
5. Fast-fail for synthetic reports baked into ASF-006's Coach validation path
Next Steps
1. Review IMPLEMENTATION-GUIDE.md for interaction risks and verification steps
2. Start Phase 1: /task-work TASK-ASF-001 (1 line YAML change) + /task-work TASK-ASF-002
3. Re-run FEAT-AC1A after Phase 1 to validate the immediate fix
4. Continue with Phase 2-4 across subsequent sessions

Show less
10:18

Identified five critical gaps in implementation task coverage












Good instinct to pause and verify completeness before executing. Let me cross-reference systematically.


Identified six critical gaps in implementation tasks requiring attention














Now let me do a systematic cross-reference — findings → recommendations → tasks → diagram paths — to find gaps.

I've mapped everything out. Here's my assessment:

The 8 tasks cover all 6 findings and all 7 original recommendations. The phasing and interaction risks from the diagrams are properly captured. But I've found 4 gaps — ranging from "potential re-run blocker" to "will bite you next month."

Gap 1 (Potential Re-Run Blocker): Direct mode Coach validation path is untested

ASF-001 switches SFT-001 to implementation_mode: direct. This was identified as Q1 in Diagram 7. The entire review traced the task-work path. The direct mode path uses _invoke_player_direct() which sends a custom prompt — but does it produce task_work_results.json with completion_promises? If not, you'll hit the exact same F2 failure (synthetic-like report → Coach can't match criteria → stall) just via a different route.

SFT-002 completed in direct mode, so it CAN work — but SFT-002 might be a simpler task where text-matching was sufficient. For SFT-001 with 10 acceptance criteria, the text fallback might still fail.

Recommendation: Add a verification step to ASF-001's acceptance criteria: "Confirm that direct mode output for SFT-001 produces either completion_promises or populated requirements_met that the Coach can match against." This isn't a new task — it's a missing acceptance criterion on the existing task.

Gap 2 (Will Recur): No task for worktree cleanup automation

The re-run checklist says rm -rf .guardkit/worktrees/FEAT-AC1A manually. ASF-007 adds cancellation, but the state machine (Diagram 6) shows four terminal states: COMPLETED, FAILED, FAILED_EXTERNAL, MERGE_FAILED. Only COMPLETED has a cleanup step (merge + remove). The other three leave orphan worktrees.

Over time, these accumulate. More critically, if the next run creates a worktree with the same name as an orphan, git will error and the task will fail immediately.

Recommendation: Add worktree cleanup as an acceptance criterion on ASF-007 (it's already touching the lifecycle code), or create a small ASF-009 task: "Add worktree cleanup to all terminal states in _loop_phase and to feature orchestrator's finally block." Complexity 2.

Gap 3 (Efficiency Drain): Graphiti context fetch-then-discard not addressed

Diagram 4 (data flow) shows this clearly: _capture_turn_state() writes to Graphiti every turn, context_loader.get_coach_context() reads it, but the result is discarded before reaching CoachValidator. None of the ASF tasks wire this connection. It's the exact "write-without-read" bug pattern FEAT-DG-001 was created to prevent.

This isn't causing stalls, but it's adding 5-10 seconds of wasted Graphiti latency per turn (especially after F6 kicks in with retry backoff). For an 8-turn run, that's over a minute of pure waste.

Recommendation: This is a backlog item, not an ASF blocker. But note it in the IMPLEMENTATION-GUIDE.md as a known inefficiency and future task. Possibly a Phase 5 item alongside the broader Graphiti ROI work.

Gap 4 (Meta-Risk): No regression tests for the autobuild fixes themselves

The supreme irony: the seam testing feature failed at the seams, and now we're creating 8 fix tasks that will be implemented by the same autobuild system that has a ~50% failure rate. Each ASF task should include test verification, but there's no task for creating a lightweight autobuild integration test that exercises the fixed paths.

At minimum, after Phase 2 (ASF-003 + ASF-004), you should be able to run a "canary task" — a known-simple task through autobuild to verify the feedback loop produces specific criteria text and that synthetic reports are logged with warnings.

Recommendation: Add to IMPLEMENTATION-GUIDE.md: "After each phase, manually run a canary autobuild task to verify the fix before proceeding to next phase." This doesn't need a separate task — it's a verification gate between phases. But explicitly document what the canary task should be and what to look for in the output.

Minor observations (not gaps, but worth confirming are captured in the task specs):

The session preamble overhead (F1 root cause) isn't addressed by any task — ASF-001 works around it and ASF-008 increases the timeout, but neither investigates why the task-work session preamble consumes 1800s. For Wave 2 tasks (complexity 4-6) that must use task-work mode, this will recur. Worth noting as a backlog item.

ASF-005 (scoped test detection) needs to consider what happens when test_paths is not specified in task frontmatter — the default must remain whole-worktree to avoid silently losing regression coverage. Confirm the task spec includes "default to whole-worktree when no test_scope specified."

Overall though, the task structure is solid. The phasing is right, the interaction risks from the diagrams are captured in the ordering, and the R4 split into ASF-004/ASF-006 is exactly what the data flow diagram called for. With the four gaps addressed (particularly Gap 1 before the re-run), this should be a comprehensive fix plan.

