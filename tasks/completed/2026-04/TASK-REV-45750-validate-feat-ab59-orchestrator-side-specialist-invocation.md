---
id: TASK-REV-45750
title: "Validate FEAT-AB59 orchestrator-side specialist invocation works end-to-end"
status: completed
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T12:05:00Z
completed: 2026-04-25T12:05:00Z
follow_up_task: TASK-VAL-7C2E
priority: critical
task_type: review
review_mode: code-quality
review_depth: comprehensive
parent_feature: FEAT-AB59
parent_review: TASK-REV-119C1
tags: [autobuild, validation, post-implementation-review, c4-diagrams, FEAT-AB59, F4A1-followup, critical-path]
related_to:
  - TASK-REV-119C1
  - TASK-REV-F4A1
  - TASK-OSI-001
  - TASK-OSI-002
  - TASK-OSI-003
  - TASK-OSI-004
  - TASK-OSI-005
  - TASK-OSI-006
  - TASK-OSI-007
  - TASK-DIAG-F4A2
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-25T12:00:00Z
review_results:
  mode: code-quality
  depth: comprehensive
  findings_count: 6
  recommendations_count: 1
  decision: implement
  report_path: docs/reviews/feat-ab59-validation/TASK-REV-45750-validation-report.md
  tests_run: 31
  tests_passed: 31
---

# Task: Validate FEAT-AB59 orchestrator-side specialist invocation works end-to-end

## Why this task exists

FEAT-AB59 (orchestrator-side invocation of `test-orchestrator` and
`code-reviewer` for AutoBuild Phases 4 and 5) has shipped all 7 subtasks
(TASK-OSI-001 through TASK-OSI-007), with completed task files moved to
`tasks/completed/2026-04/` and commits landed for at least 6 of them. This
was the third F4A1 follow-up after TASK-DIAG-F4A2 and TASK-FIX-F4A3 — the
load-bearing structural fix that replaced the refuted prompt-class fix-class
(TASK-FIX-7A08, reverted across three commits).

**The problem**: AutoBuild has been failing for weeks. Three runs across
two repos (forge-run-3, forge-run-5, jarvis-FEAT-002-run-2) showed zero
specialist invocations and stalled on `coach_agent_invocations_stall`.
TASK-FIX-7A08's prompt fix was reverted because three independent runs
proved it insufficient. FEAT-AB59 was the structural fix. We now need to
**verify it actually works end-to-end** before re-running the expensive
forge/jarvis acceptance suite.

**The cost trap**: Running `guardkit autobuild feature forge-FEAT-FORGE-002`
or `jarvis-FEAT-J002` to verify the fix burns ~hours of wall-clock and
significant API spend per run. Three weeks of failed runs have already
consumed substantial budget. **We cannot afford another failed live run
without first proving the wiring is correct via a tighter validation loop.**

## Task type

This is a **`review`** task. Per `/task-review` decision-mode flow, it ends
in a decision checkpoint:
- **[A]ccept** — fix verified, proceed to live forge/jarvis runs
- **[R]evise** — gaps found in this review, escalate
- **[I]mplement** — generate a follow-up feature with **a single
  task-work task** that's a tight canonical validation case
  (cheaper than running on the forge feature)
- **[C]ancel** — abandon (unlikely)

The user explicitly indicated that the [I]mplement path should generate
**one task only** — a focused validation task — rather than re-running
the full forge/jarvis acceptance suite.

## Reasoning rigour required

The user has explicitly directed: **"use extra thinking/tokens to ensure
we can start making progress with autobuild once again"** and **"Trace
execution flows across system/technological boundaries and create C4
sequence diagrams to validate thinking/reasoning — I find 9 out of 10
times this changes the initial analysis."**

This is a critical-path task. The reviewer MUST:

1. **Trace boundaries explicitly**. Every transition between technological
   layers is a candidate for failure:
   - Python `AutoBuildOrchestrator` → `claude_agent_sdk.query` (Python →
     SDK shim → subprocess)
   - SDK subprocess stdin → bundled Claude CLI
   - Claude CLI → Anthropic HTTPS API (network)
   - Anthropic API → Player LLM inference (the layer F4A1 proved is
     stochastic and prompt-resistant)
   - Player LLM tool-use decision → emitted `Task(...)` block
   - SDK message stream → `task_work_results.json` writer
   - `task_work_results.json` → `_inject_specialist_records_into_task_work_results`
   - merged `task_work_results.json` → Coach SDK invocation
   - Coach output → next-turn decision

2. **Produce C4-style sequence diagrams** (Mermaid `sequenceDiagram`)
   showing the actual call sequence across these boundaries, with
   particular emphasis on:
   - Where the new orchestrator-side specialist invocations sit relative
     to existing Player/Coach calls
   - What state is committed to the worktree filesystem at each step
   - Where the gate-credit merge happens vs. where the Coach reads from
   - The `implementation_mode: direct` skip path

3. **Validate against the implementation, not against the plan**. The
   review report (TASK-REV-119C1) and the IMPLEMENTATION-GUIDE.md
   describe what *should* exist. This review must read the actual code
   that shipped and confirm it matches — or surface every divergence.

4. **Hunt for the failure modes the original plan flagged**. Risk register
   from TASK-REV-119C1 §7:
   - Player phase-marker double-count (mitigated by source-tag dedup +
     prompt trim) — **verify the dedup actually fires**
   - `implementation_mode: direct` regression — **verify the guard is
     placed correctly relative to the merge call**
   - Stub-SDK drift — **verify the stub's invocation contract matches
     the real SDK shape used by `_invoke_with_role`**
   - Specialist session leak on failure — **verify try/finally with
     `_kill_child_claude_processes` is in place**
   - Test artefact propagation gap — **verify `code-reviewer` actually
     receives Phase 4 summary in its prompt**
   - Gate-credit silent failure — **verify the merge step writes the
     gate block even when `specialist_results.json` is absent**

5. **Surface anything the diagram trace reveals that the prose missed**.
   The user's claim that "9 out of 10 times this changes the initial
   analysis" is the operational rule: **draw the diagram first, write
   the conclusion second**. Don't anchor on the implementation plan.

## Description

Conduct a comprehensive post-implementation review of FEAT-AB59. The
review must validate that the structural fix landed correctly and that
the autobuild Phase 4/5 specialist invocation now works end-to-end. The
review's deliverable is a decision-ready report with C4 sequence diagrams
that either confirms the fix is ready for live acceptance runs OR
identifies specific gaps that need fixing first.

### Scope (in)

1. **Read every shipped artefact**:
   - `guardkit/orchestrator/specialist_invocations.py` (new module —
     TASK-OSI-001)
   - `guardkit/orchestrator/agent_invoker.py` — specifically:
     - `_inject_specialist_records_into_task_work_results` (new method,
       TASK-OSI-002)
     - `_compute_agent_invocations_validation` (modified, TASK-OSI-002)
     - `get_expected_phases` (modified for `direct` mode, TASK-OSI-002)
     - any other touched code from `git diff a0c08fb8^ a0c08fb8`
   - `guardkit/orchestrator/autobuild.py` — specifically the
     `_loop_phase` modification (TASK-OSI-006) where the orchestrator-
     side specialist invocation is wired in
   - `guardkit/orchestrator/prompts/autobuild_execution_protocol*.md`
     (Phase 4/5 trim, TASK-OSI-003)
   - `tests/integration/test_autobuild_phase_4_5_orchestration.py` (new
     stub-SDK behavioural tests, TASK-OSI-007)
   - Any unit tests in `tests/orchestrator/` covering OSI changes

2. **Verify TASK-OSI-003 actually shipped**. The git log shows commits
   for TASK-OSI-001/002/004/005/006/007 but I did not see a dedicated
   TASK-OSI-003 commit on first inspection. Either:
   - It was bundled into another commit (verify which one),
   - The protocol files were edited but the commit is named differently,
   - The trim did not actually happen and the Player still receives
     Phase 4/5 instructions.
   This is a load-bearing dedupe question — if the Player is still being
   instructed to claim Phase 4/5, the source-tag dedup carries more
   weight than planned.

3. **Run the stub-SDK behavioural tests locally** and confirm they pass:
   ```bash
   pytest tests/integration/test_autobuild_phase_4_5_orchestration.py -v
   pytest tests/orchestrator/ -v -k specialist
   ```
   Capture output. Note any tests that fail, are skipped, or are
   marked xfail.

4. **Trace the actual turn loop** by reading `_loop_phase` and listing
   the exact sequence of calls for:
   - A non-`direct` mode task (full Phase 3 → 4 → 5 → merge → Coach)
   - A `direct` mode task (Phase 3 only, gates relaxed, no merge)
   - A turn where `test-orchestrator` fails (Phase 4 = failed, Phase 5
     skipped, merge still runs, Coach sees partial state)
   - A turn where `code-reviewer` fails after passing `test-orchestrator`
     (Phase 4 preserved, Phase 5 = failed, merge runs)

5. **Produce C4-style sequence diagrams** (Mermaid) for each of the
   four scenarios above. Use `sequenceDiagram` with participants for
   `Orchestrator`, `AgentInvoker`, `specialist_invocations`, `SDK`,
   `Worktree FS`, `Coach`. Mark every cross-boundary transition.

6. **Validate against the data flow diagram in
   `tasks/backlog/orchestrator-side-specialist-invocation/IMPLEMENTATION-GUIDE.md` §3.1**.
   Either confirm the implementation matches OR enumerate divergences.

### Scope (out)

- Running the full forge-FEAT-FORGE-002 or jarvis-FEAT-J002 acceptance
  suite. That is the **post-review action** if [A]ccept is chosen.
- Modifying any FEAT-AB59 code. This is a review, not a fix. If gaps
  are found, they get filed as a follow-up.
- Re-debating the architectural decisions from TASK-REV-119C1. Those
  are locked in. The review is *implementation-vs-plan*, not
  *plan-revision*.

### Acceptance criteria for THIS review task

- [ ] All 7 OSI subtask deliverables read and inventoried (with line-
      number citations) in the review report.
- [ ] TASK-OSI-003 shipping status confirmed — either citing the commit
      that contains the prompt trim, or flagging that the trim did not
      land.
- [ ] Stub-SDK test suite execution result captured (pass/fail/skipped
      counts, plus a paste of any failure output).
- [ ] At least 4 Mermaid `sequenceDiagram` blocks produced, one per
      scenario above (non-direct happy path, direct mode, Phase 4 fail,
      Phase 5 fail).
- [ ] Each of the 6 risk-register items from TASK-REV-119C1 §7 is
      explicitly addressed: "verified", "not verified — gap is X", or
      "not applicable — reason".
- [ ] A boundary-crossing analysis is produced: a numbered list of every
      technological boundary the turn loop crosses, and whether the
      review found evidence the boundary is correctly handled.
- [ ] Report ends with a decision recommendation:
      - [A]ccept → ready for forge-FEAT-FORGE-002 + jarvis-FEAT-J002
        live runs
      - [R]evise → specific gaps listed, follow-up task(s) named
      - [I]mplement → a *single-task* canonical validation task
        defined (not the full forge feature) — title, scope, files to
        touch, success signal that does not require a multi-hour live
        run
- [ ] Report saved at
      `docs/reviews/feat-ab59-validation/TASK-REV-45750-validation-report.md`.

## Suggested workflow

```bash
# 1. Run this review with extra-rigour mode
/task-review TASK-REV-45750 --mode=code-quality --depth=comprehensive

# The review should:
#   - Read all OSI artefacts
#   - Run the stub-SDK test suite
#   - Trace the turn loop end-to-end
#   - Produce 4+ Mermaid sequenceDiagrams
#   - Address every risk-register item
#   - End with a clear A/R/I/C recommendation

# 2. At the decision checkpoint, the user picks [I]mplement
#    iff the recommended single validation task is well-defined
#    AND cheaper than running the forge feature

# 3. The single validation task (if [I]mplement) should ideally:
#    - NOT require running guardkit autobuild feature on a real feature
#    - Use a minimal canonical AutoBuild task that exercises the full
#      Player → Phase-4 → Phase-5 → merge → Coach loop
#    - Run with GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1 so the
#      messages.jsonl artefact captures real specialist invocations
#      from a live SDK call (TASK-DIAG-F4A2 infrastructure)
#    - Take <10 minutes wall-clock, not hours
#    - Produce a clear pass/fail signal: "messages.jsonl shows
#      orchestrator-issued test-orchestrator and code-reviewer sessions
#      AND task_work_results agent_invocations_validation == passed
#      for phases 4 and 5"
```

## Implementation Notes

- This review IS the gate before re-investing in expensive live runs.
  Treat reviewer time as much cheaper than live SDK time.
- The "9 out of 10 times the diagram changes the analysis" rule applies:
  start with the trace, not the conclusion.
- If the review finds the wiring is broken, that is a finding worth
  surfacing fast — don't soften it because the team has been working
  on this for weeks. False reassurance is worse than a clean rejection.
- If the review finds the wiring is sound, the [I]mplement
  recommendation should be a tight one-task validation that proves it
  with a real SDK call but at minimum cost — NOT a re-run of forge.

## References

- Parent review (architectural decisions): TASK-REV-119C1 →
  `docs/reviews/orchestrator-side-specialist-invocation/TASK-REV-119C1-review-report.md`
- Original diagnostic: TASK-REV-F4A1 →
  `docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md`
- Sibling F4A1 follow-ups: TASK-DIAG-F4A2 (preservation), TASK-FIX-F4A3
  (pollution-detector resume hygiene)
- Refuted fix-class: commits `7f8f14ba`, `86688fc6`, `a8789317`
  (TASK-FIX-7A08 lifecycle)
- Feature folder: `tasks/backlog/orchestrator-side-specialist-invocation/`
- Feature YAML: `.guardkit/features/FEAT-AB59.yaml`
- Implementation guide:
  `tasks/backlog/orchestrator-side-specialist-invocation/IMPLEMENTATION-GUIDE.md`
- All 7 OSI tasks (completed):
  `tasks/completed/2026-04/TASK-OSI-{001..007}-*.md`
- Diagnostic preservation infrastructure:
  `guardkit/orchestrator/sdk_debug.py`
- Producer-side validation gate:
  `guardkit/orchestrator/agent_invoker.py` (`_compute_agent_invocations_validation`)

## Notes

- This is an `review` task. Per `/task-create` automatic detection
  rules, the system suggests using `/task-review` for execution. That
  is the correct command — this task has no implementation phase of
  its own.
- Priority `critical`: autobuild has been broken for weeks; verifying
  the fix is the most important active workstream.
- Reviewer should allocate sufficient context budget — multiple file
  reads, test execution, multi-diagram synthesis. Do not rush.
