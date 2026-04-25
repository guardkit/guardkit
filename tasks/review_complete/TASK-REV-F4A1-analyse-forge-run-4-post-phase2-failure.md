---
id: TASK-REV-F4A1
title: Analyse forge+jarvis autobuild regressions after phase-2 stall-resilience fixes (last-chance review before revert)
status: review_complete
created: 2026-04-24T20:30:00Z
updated: 2026-04-24T23:30:00Z
priority: critical
task_type: review
review_mode: architectural
review_depth: deep
decision_required: true
tags: [autobuild, review, stall-analysis, forge, jarvis, post-fix-regression, code-review, decision-point, phase2-verification, blocks-all-progress, revert-candidate, cross-repo]
complexity: 0
related_to:
  - TASK-REV-F3D7
  - TASK-REV-JMBP
  - TASK-FIX-7A08
  - TASK-FIX-7A09
  - TASK-FIX-7A0A
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: deep
  decision_awaiting_user: true
  recommendation: revert
  revert_scope_commits:
    - 7f8f14ba
    - 86688fc6
  revert_scope_tasks:
    - TASK-FIX-7A08
  keep_tasks:
    - TASK-FIX-7A01
    - TASK-FIX-7A02
    - TASK-FIX-7A03
    - TASK-FIX-7A04
    - TASK-FIX-7A05
    - TASK-DOC-7A06
    - TASK-FIX-7A07
    - TASK-FIX-7A09
  hypothesis_verdicts:
    H-A_resume_state: refuted_as_primary_confirmed_as_secondary
    H-B_prompt_ineffective: confirmed
    H-C_classifier_regression: refuted
    H-D_7A09_changes: refuted_not_regression_cause
    H-E_7A0A_ci_lint: not_applicable_no_commit
    H-F_jarvis_degradation: confirmed
    H-G_player_capability_wall: strongly_confirmed
  root_cause_classification:
    - architecture
    - code
  followups_proposed:
    - TASK-DIAG: preserve rendered prompt + SDK stream under sdk_debug/ (complexity 3)
    - TASK-FEAT: feature-plan orchestrator-side specialist invocation H-G(b) (complexity 8-12)
    - TASK-FIX: pollution-detector resume hygiene H-A secondary (complexity 3)
  revert_acceptance_test: jarvis-FEAT-J002-run-3 completes at least 14/23; J002-009 and J002-014 pass in 1 turn
  report_path: docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md
  completed_at: 2026-04-24T23:30:00Z
---

# Task: Analyse forge+jarvis autobuild regressions after phase-2 stall-resilience fixes (last-chance review before revert)

## ⚠️ Escalation

**This is the final fix-attempt review before we consider reverting the entire
week's changes.** All AutoBuild progress is now completely blocked by these
regressions on both forge and jarvis. If this review cannot identify a
minimum-footprint, behaviourally-verifiable fix, the recommended decision is
**[R]evert** — unwind TASK-FIX-7A08 + TASK-FIX-7A09 + TASK-FIX-7A0A (and
potentially the full phase-1 bundle 7A01–7A07) to the last known passing
baseline, re-evaluate the problem from scratch, and file a fresh feature plan.

Scope is now **cross-repo**: the same signature fails on both forge (fresh
baseline) and jarvis (previously passing).

## Description

AutoBuild run **FEAT-FORGE-002 (NATS Fleet Integration)** was re-executed
three times after all three phase-2 subtasks landed in `completed/`
(TASK-FIX-7A08, TASK-FIX-7A09, TASK-FIX-7A0A — the remediation bundle spawned
by TASK-REV-F3D7). The feature fails on every iteration.

**Three transcripts are in scope for this review:**

1. [docs/reviews/bdd-acceptance-wired-up/forge-run-4.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md)
   — first post-phase-2 re-run on forge, executed via `[R]esume` from run-3's
   partially-completed worktree. Hit turn-1 `unrecoverable_stall` on Wave 2
   (NFI-003, NFI-007). Summary block shows *generic* context-pollution text
   (no `coach_agent_invocations_stall` primary classifier, no `TASK-FIX-7A08`
   reference, no phase-specialist block).
2. [docs/reviews/bdd-acceptance-wired-up/forge-run-5.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-5.md)
   — `--fresh` baseline on forge. Wave 1 passed 2/2; Wave 2 failed 3/3
   (NFI-003, NFI-006, NFI-007) with the **enriched `coach_agent_invocations_stall`
   classifier block firing correctly** (TASK-FIX-7A08 + Phase 4/5 specialist
   names present at [forge-run-5.md:965-967](../../docs/reviews/bdd-acceptance-wired-up/forge-run-5.md#L965)
   and repeated at `:1241-1243, :1415-1417`). **Same missing-phases signature
   as run-3 and run-4**: `missing phases 4, 5` and `3, 5`. This is the
   load-bearing evidence that 7A08's prompt mandate **did not change Player
   behaviour** — the feature fails identically on a clean slate.
3. [docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT-002-run-2.md](../../docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT-002-run-2.md)
   — **jarvis FEAT-J002** post-phase-2. Wave 2 failed 4/9 tasks
   (J002-008, J002-009, J002-013, J002-014) with the **identical signature**
   as forge: `Agent-invocations gate rejected ... missing phases 4, 5` /
   `3, 5`. Feature completed 12/23 tasks.
4. [docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md](../../docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md)
   — **jarvis FEAT-J002 pre-phase-2 baseline** (this is the run TASK-REV-JMBP
   was derived from). Wave 2 failed 2/9 tasks; feature completed 14/23.
   Jarvis was **partially failing before** the phase-2 fixes — not passing.
   The comparison that matters is **degree of failure**:
   pre-phase-2 → post-phase-2 went from **14/23 tasks completed to 12/23**,
   and from **2 Wave-2 failures to 4**. Gate-rejection count in transcript
   went from 8 to 14. The phase-2 fixes did not restore jarvis; they made
   the jarvis run measurably worse.

### Outcome summary

**forge-run-4 (resume of run-3 worktree):**

| Task | Result | Turns | Decision |
|------|--------|-------|----------|
| TASK-NFI-001 | ⏭ SKIPPED | — | `already_completed` (from run-3) |
| TASK-NFI-002 | ⏭ SKIPPED | — | `already_completed` (from run-3) |
| TASK-NFI-003 | ✗ FAILED | **1** | `unrecoverable_stall` (missing phases 4, 5; 33 SDK turns) |
| TASK-NFI-006 | ⏭ SKIPPED | — | `already_completed` (from run-3) |
| TASK-NFI-007 | ✗ FAILED | **1** | `unrecoverable_stall` (missing phases 3, 5; 24 SDK turns) |
| **Wave 2** | ✗ FAILED | — | **3/11 tasks completed**, 8m 12s |

**forge-run-5 (`--fresh` baseline):**

| Task | Result | Turns | Decision |
|------|--------|-------|----------|
| TASK-NFI-001 | ✓ PASSED | 1 | `approved` (Wave 1) |
| TASK-NFI-002 | ✓ PASSED | 1 | `approved` (Wave 1) |
| TASK-NFI-003 | ✗ FAILED | 3 | `coach_agent_invocations_stall` (missing 4,5 then 3,5 then 4,5) |
| TASK-NFI-006 | ✗ FAILED | 3 | `coach_agent_invocations_stall` (missing 4,5 repeatedly + 3,5) |
| TASK-NFI-007 | ✗ FAILED | 3 | `coach_agent_invocations_stall` (missing 4,5 repeatedly) |
| **Wave 2** | ✗ FAILED | — | **2/11 tasks completed**, ~31m |

**jarvis-FEAT-002 pre-phase-2 (jarvis-FEAT002-run-1.md — baseline):**

| Task group | Result |
|------------|--------|
| Wave 1 (7 tasks) | ✓ PASSED 7/7 |
| Wave 2 (9 tasks) | ✗ FAILED: **7 passed, 2 failed** |
| **Feature** | ✗ FAILED, **14/23 tasks completed** |

**jarvis-FEAT-002 post-phase-2 (jarvis-FEAT-002-run-2.md):**

| Task | Result | Decision |
|------|--------|----------|
| Wave 1 (7 tasks) | ✓ PASSED | 7/7 approved |
| TASK-J002-008 | ✗ FAILED | `coach_agent_invocations_stall` (missing 4,5 / 3,5) |
| TASK-J002-009 | ✗ FAILED | `coach_agent_invocations_stall` (missing 4,5 x4) |
| TASK-J002-013 | ✗ FAILED | `coach_agent_invocations_stall` (missing 3,5 / 4,5) |
| TASK-J002-014 | ✗ FAILED | `coach_agent_invocations_stall` (missing 4,5 x3) |
| **Feature** | ✗ FAILED | **12/23 tasks completed** (4 failed in Wave 2) |

**Degradation**: 14/23 → 12/23 completed; 2 → 4 Wave-2 failures; 8 → 14 gate
rejections in transcript. The phase-2 fixes did not restore jarvis — they
made it worse.

### What the three transcripts tell us together

1. **The fresh run (forge-run-5) fails identically to the resume run (forge-run-4)**:
   same missing-phases signature (4,5 / 3,5), same classifier output. The
   turn-1 vs turn-3 shape change in run-4 was an artefact of resume-state
   checkpoint loading, not a root cause. → **H-A (resume-state interaction)
   is REFUTED as a primary factor** — though it *is* a real secondary defect
   that made run-4 less diagnosable and should still be filed separately.
2. **7A08's prompt mandate produced no observable Player behaviour change**:
   across three fresh runs on two repos, the Player keeps invoking **1 of 3**
   required agents. Missing phases are always Phase 4 (`test-orchestrator`),
   Phase 5 (`code-reviewer`), or Phase 3 (stack specialist) — exactly the
   phases 7A08 was supposed to mandate. → **H-B (7A08 prompt change didn't
   work) is CONFIRMED.**
3. **7A07's enriched classifier DOES fire correctly on fresh runs**
   (forge-run-5 lines 958-969, 1234-1245, 1408-1419; jarvis-run-2 lines
   3227-3238, 3394-3405, 3477-3488, 3577-3588). → **H-C (classifier regression)
   is REFUTED as a persistent problem** — the run-4 "generic text" observation
   was a resume-state symptom, not code regression.
4. **Jarvis FEAT-J002 degraded, not "regressed from passing"**: the pre-phase-2
   run (jarvis-FEAT002-run-1.md) completed 14/23 tasks with 2 Wave-2 failures
   — jarvis was **partially failing already** (this is where TASK-REV-JMBP's
   data came from). The post-phase-2 run completes **12/23 with 4 Wave-2
   failures**, and all four failing tasks hit the identical agent-invocations
   signature that forge exhibits. → **H-F: the phase-2 fixes delivered net
   regression on jarvis — more failed tasks, more gate rejections, same
   blocking signature.** Not as strong a revert signal as "was passing, now
   broken" would have been, but still a measurable worsening on the
   prior-reference environment. Combined with forge being fully blocked on
   Wave 2 across runs 3, 4, and 5, this supports revert consideration.

### What's new / different from run-3 (signals worth investigating)

1. **Turn-1 exit, not turn-3**: both Wave 2 tasks hit `unrecoverable_stall`
   after **one** turn, not three. Run-3 took three turns to exhaust the same
   signal. This is a major shape change and likely the single most load-bearing
   clue.
2. **Pre-loaded checkpoints from run-3**:
   - [forge-run-4.md:92](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md#L92)
     `Loaded 3 checkpoints from .../TASK-NFI-007/checkpoints.json`
   - [forge-run-4.md:100](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md#L100)
     `Loaded 3 checkpoints from .../TASK-NFI-003/checkpoints.json`

   These are the three failing checkpoints each task created during run-3. On
   the fresh turn 1, the worktree-checkpoints pollution detector sees N=3 prior
   failures + 1 new failure → triggers `context pollution detected` AND
   `no passing checkpoint exists` immediately.
3. **Classifier output shape regressed** (vs. run-3): the summary block is now
   a generic *"Context pollution detected but no passing checkpoint existed to
   roll back to — review the Player's early turns for regression patterns."*
   ([forge-run-4.md:361-362](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md#L361)).
   No `coach_agent_invocations_stall` primary classifier. No `TASK-FIX-7A08`
   reference. No phase-specialist block. Either (a) 7A07's enriched branch
   isn't reached because context_pollution short-circuits first, or (b) 7A08's
   prompt changes inadvertently routed through a different classifier branch.
4. **Player agent-invocations shape unchanged**:
   - NFI-007 turn 1: `Agent-invocations gate rejected: missing phases 3, 5`
     ([forge-run-4.md:246](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md#L246))
   - NFI-003 turn 1: `Agent-invocations gate rejected: missing phases 4, 5`
     ([forge-run-4.md:328](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md#L328))

   These are **the same missing phases as run-3** — which strongly suggests
   TASK-FIX-7A08's prompt-mandate changes either didn't land observable
   behaviour-change, or landed but the Player is still ignoring them.
5. **Player SDK turn count remains high**: NFI-003 used 33 SDK turns and
   NFI-007 used 24 in a single orchestrator turn — so the Player is still
   spending real effort; it is not stalling on its end. It simply isn't
   invoking the specialists.

### What to verify (hypothesis classes — updated after run-5 + jarvis-run-2)

Based on the three-transcript evidence, H-A and H-C are partially resolved
already; the review's job is to confirm those verdicts and then focus on
H-B and H-F — the load-bearing ones for the revert decision.

1. **H-A — Resume-state interaction**: **LIKELY REFUTED as root cause**
   (forge-run-5 fresh run fails identically). Remaining work: confirm the
   turn-1 vs. turn-3 shape change in run-4 was checkpoint-loading-induced;
   file as a secondary defect if so (pollution-detector should not count
   prior-run checkpoints on resume). Cite:
   [forge-run-4.md:92, :100](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md#L92)
   (checkpoints loaded) vs. forge-run-5 Wave 2 which runs the full 3-turn
   cycle.
2. **H-B — 7A08 prompt change didn't alter Player behaviour**: **STRONGLY
   CONFIRMED** across three fresh runs on two repos. Review work:
   (a) verify the prompt text actually reached the Player by inspecting a
   rendered prompt from this run's `.guardkit/autobuild/TASK-NFI-*/` artefacts;
   (b) determine whether prompt landed in all three templates (full / medium
   / slim) or only one;
   (c) check `_build_inline_implement_protocol` in `agent_invoker.py` to
   confirm it actually consumes the amended `.md` file;
   (d) confirm via artefact inspection whether the Player is calling `Task`
   with the wrong `subagent_type` (gate wouldn't count it) or not calling
   `Task` at all.
3. **H-C — Classifier regression**: **REFUTED**. Forge-run-5 shows enriched
   block firing correctly at lines 958-969, 1234-1245, 1408-1419; jarvis-run-2
   lines 3227, 3394, 3477, 3577. Review should still note the run-4
   generic-text artefact as H-A evidence, not H-C.
4. **H-D — 7A09 Coach-path changes**: No SDK stream failures in runs 4/5 or
   jarvis-run-2 (grep-able absence across all three transcripts). 7A09
   didn't cause a regression but also wasn't exercised. Not a revert
   candidate on its own.
5. **H-E — 7A0A CI lint**: With 7A08 landed the dead-reference is now live.
   Confirm the CI test passes; if it doesn't, log separately.
6. **H-F — Cross-repo degradation (jarvis)**: The phase-2 bundle delivered
   net-negative outcomes on the reference environment (14/23 → 12/23,
   2 → 4 Wave-2 failures, 8 → 14 gate-rejections). Review work: compare the
   specific tasks that PASSED in run-1 but FAILED in run-2 — why? Did the
   prompt mandate actively break something that was previously limping
   through? (e.g. tasks that were inline-completing successfully before are
   now hitting the strengthened gate without the Player understanding the
   new directive.) This is the single biggest argument for revert if
   confirmed.
7. **H-G — Gate is correct; Player capability is the wall (NEW)**: It is
   worth *naming* the possibility that no amount of prompt-mandate wording
   will reliably cause the Player to invoke sub-agents in this orchestrator
   shape. If the Player model (Claude Sonnet/Opus in SDK subprocess) has a
   strong prior to complete work inline when it has `Bash`/`Write`/`Edit`
   tools available, the fix class "improve the prompt" may be fundamentally
   insufficient. Alternative fix classes to consider:
   (a) **remove `Bash` from `allowed_tools`** during the Player inline
   protocol so it cannot run tests inline (forcing `Task(test-orchestrator)`);
   (b) **auto-invoke the specialists orchestrator-side** after the Player
   completes Phase 3, rather than asking the Player to do so;
   (c) **relax the agent-invocations gate** for some task classes so the
   orchestrator can progress on tasks where the Player's inline completion
   is adequate;
   (d) **revert to a pre-phase-2 baseline** and redesign the problem from
   scratch.

## Why this is a review task, not a /task-work

The three-transcript evidence shows that **the phase-2 bundle did not deliver
its stated outcome and degraded the jarvis reference environment**. That is a
revert-candidate finding — but revert is destructive and expensive. One more
review pass is warranted to either (a) identify a small, high-confidence
follow-up fix that closes the gap, or (b) confirm that the revert is the
right call and file it as a concrete task. Picking a direction without the
review risks either wasting another fix-cycle or prematurely reverting a
foundation (7A09, 7A0A) that did not actively cause the regression.

Possible fix shapes depending on what the review finds:

- **If H-B confirms the prompt is landing but being ignored**: move to a
  structural fix (H-G alternatives (a) `allowed_tools` shrink, or (b)
  orchestrator-side specialist invocation). These are meaningfully larger than
  prompt-editing and warrant explicit design-phase scoping.
- **If H-B confirms the prompt didn't actually reach the Player** (prompt
  amended in `.md` but `_build_inline_implement_protocol` didn't consume it,
  or only one template was amended): a small fix-up task to 7A08 may close
  the gap. Still verify cross-repo before celebrating.
- **If H-F shows jarvis tasks that previously passed now fail specifically
  because of the strengthened gate**: relaxing the gate for certain task
  classes (H-G(c)) may partially restore jarvis without a full revert.
- **If no small fix is credible and the strategic direction is unclear**:
  revert the phase-2 bundle (plus potentially the phase-1 gate-tightening in
  7A07 that enables the rejection loop), and redesign the problem with a
  clearer hypothesis about Player capability.

A review pass produces: a timeline, each hypothesis confirmed/refuted with
citations, a minimum-footprint remediation set OR an explicit revert
recommendation, and a ranked task list for `/task-review [I]mplement`
or `[R]evert`.

## Required Diagnostic Method: Cross-Boundary Execution Flow Tracing

**This is the method the review MUST use — not an optional enhancement.** Every
prior review iteration has attempted to verify theories via code-read plus
log-inspection and each has produced a fix that passed unit tests but failed
in live behaviour. The structural problem is that the execution flow crosses
at least **four technology boundaries** in both directions for every Player
invocation, and "the prompt looks right in `autobuild_execution_protocol.md`"
does not entail "the LLM actually saw that prompt text and chose to act on
it." Without tracing the data flow across those boundaries, every hypothesis
remains a guess.

In the reviewer's accumulated experience, producing
**C4-style sequence diagrams annotated with what crosses each boundary**
has a ~9/10 success rate at sharpening root-cause analysis on this class
of multi-process defect. We are out of cheap alternatives; this is the
method.

### Boundaries to diagram

Each hop is a place where 7A08's intended prompt change could have been
silently lost, mis-rendered, or consumed differently than the `.md` file
suggests:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Boundary 1 — Filesystem → Python package                                │
│   prompts/*.md → _build_inline_implement_protocol → str                │
├─────────────────────────────────────────────────────────────────────────┤
│ Boundary 2 — Python orchestrator → claude_agent_sdk Python API         │
│   AgentInvoker._invoke_with_role → sdk.query(prompt, options)          │
│   (allowed_tools, system prompt, task prompt composition here)         │
├─────────────────────────────────────────────────────────────────────────┤
│ Boundary 3 — claude_agent_sdk Python → bundled CLI subprocess (Node)   │
│   stdin JSON → CLI process → HTTP to Anthropic API                     │
│   (where the system/user prompts are actually serialized to the wire)  │
├─────────────────────────────────────────────────────────────────────────┤
│ Boundary 4 — Anthropic API → LLM inference → tool-use decisions        │
│   (where the Player either invokes Task or runs Bash inline)           │
├─────────────────────────────────────────────────────────────────────────┤
│ Boundary 5 — LLM response → CLI subprocess → SDK stream → Python       │
│   (message JSONL back; 7A03 touches this return path)                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Boundary 6 — Python → task_work_results.json on disk                   │
│   (what Coach's agent-invocations gate actually reads)                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### Required diagrams

Produce at least **four** diagrams in the analysis report. Mermaid inline is
acceptable; PlantUML or Structurizr also fine. Each diagram must label
boundaries explicitly and annotate what data crosses each hop.

1. **C4 Container view (Level 2)** — the overall cross-boundary landscape:
   guardkit CLI, `FeatureOrchestrator`, `AutoBuildOrchestrator`,
   `AgentInvoker`, `claude_agent_sdk` (Python), bundled Claude CLI
   subprocess (Node.js), Anthropic API, Coach validator, FalkorDB
   (Graphiti), vLLM (embeddings), target worktree filesystem. Show which
   containers live in which process/runtime, and which communicate over
   which protocol (stdin/stdout JSONL, HTTP, Cypher, filesystem).
2. **Sequence diagram — Player invocation end-to-end** (Wave 2 `task-work`
   mode): from `AutoBuildOrchestrator` turn-loop entry all the way through
   `_build_inline_implement_protocol` → `AgentInvoker._invoke_with_role` →
   `sdk.query(...)` → bundled CLI subprocess launch → first user message
   → LLM tool-use decision → first `ToolUseBlock` event back → …  →
   `ResultMessage` received → `task_work_results.json` written. At each
   hop, annotate:
   - **Prompt content carried**: what portion of the `.md` templates is in
     the serialized prompt at this point? Quote the actual substring
     (from artefacts preserved under
     `.guardkit/autobuild/TASK-NFI-*/`) where possible.
   - **Tool set at this hop**: exact `allowed_tools` value.
   - **Lossy or lossless**: does this hop drop/rewrite information?
3. **Sequence diagram — Coach agent-invocations gate**: `CoachValidator`
   reads `task_work_results.json` → parses `agent_invocations_validation`
   block → computes expected specialist set from
   `phase_specialists.STACK_TO_PHASE_3_SPECIALIST` + `test-orchestrator`
   + `code-reviewer` → diffs → emits `missing_phases`. Annotate each hop
   with **what the Coach sees vs. what the Player actually did**.
   Specifically: the `task_work_results.json`'s
   `agent_invocations_validation` field is populated by whom, from what
   source of truth? Is a `Task(subagent_type="test-orchestrator")`
   invocation in the Player's SDK stream actually recorded there, and if
   not, where does that information get lost?
4. **Sequence diagram — jarvis run-1 vs run-2 delta**: same Player-
   invocation sequence, but with two parallel swim-lanes: the pre-phase-2
   prompt (from `jarvis-FEAT002-run-1.md`-era code) and the post-phase-2
   prompt (current `autobuild_execution_protocol.md`). Highlight the
   specific hops where the two flows diverge. This directly answers H-F —
   if the diagrams show the divergence is entirely in prompt text and the
   LLM is taking the same tool-use decision in both cases, we know prompt-
   level fixes cannot solve this. If the divergence is in `allowed_tools`
   or some other structural change, we have a different problem.

### What each diagram should reveal

- **Diagram 2** should answer H-B definitively: is the amended
  `autobuild_execution_protocol.md` text present verbatim in the prompt
  delivered to the LLM? If yes → H-B is *prompt-landed-but-ignored*
  (structural fix needed, H-G). If no → there's a rendering bug between
  the `.md` file and the composed prompt (small fix viable).
- **Diagram 3** should answer whether `Task(subagent_type=...)`
  invocations that do happen in the SDK stream are being correctly
  recorded in `task_work_results.json`. If the Player is invoking the
  specialists but the Coach isn't seeing them (recording gap), that's a
  different fix entirely from "Player isn't invoking specialists at all."
- **Diagram 4** should answer whether reverting the phase-2 bundle
  structurally *can* restore pre-phase-2 jarvis behaviour, or whether
  phase-1's gate-tightening (7A07) is itself load-bearing for the
  failure (in which case the revert must go further back).

### Minimum evidence bar for any [I]mplement or [R]evert recommendation

The review **shall not** recommend [I]mplement or [R]evert without having
produced at least diagrams 1, 2, and 3. The cost of another mis-scoped
fix, or a revert that removes the wrong thing, is higher than the cost of
producing diagrams. If the diagrams cannot be produced because preserved
artefacts are missing (e.g. the rendered-prompt JSON from run-5's Wave 2
was not captured), the review should name that as a separate remediation
— "preserve rendered prompt + SDK message stream per task under
`.guardkit/autobuild/<task>/sdk_debug/`" — and defer the
[I]mplement/[R]evert decision until a diagnostic-enabled rerun is done.

## Acceptance Criteria

- [ ] **Cross-boundary sequence diagrams produced** — at least Diagrams 1, 2,
      and 3 above, inline in the analysis report (Mermaid / PlantUML /
      Structurizr — text-based, committed with the report). Diagram 4
      (jarvis pre/post delta) required for the [R]evert path and strongly
      encouraged regardless.
- [ ] **Boundary annotations** — for every hop in Diagram 2 and 3, a quoted
      substring or JSON field from a preserved artefact (not
      reasoning-by-code-read) showing what data crosses the boundary.
- [ ] **Cross-transcript traversal** of all four transcripts in scope
      (forge-run-4, forge-run-5, jarvis-FEAT-002-run-2, jarvis-FEAT002-run-1)
      producing a unified timeline + a pre-phase-2 vs. post-phase-2 delta for
      jarvis (with specific task IDs that changed outcome).
- [ ] Each of the three phase-2 subtasks (7A08 / 7A09 / 7A0A) evaluated for
      whether its landed change fired observably in these runs:
      **fired correctly**, **fired but ineffective**, **did not fire but
      should have**, **not exercised by this scenario**, or **regressed**.
- [ ] The seven hypothesis classes above (H-A resume-state, H-B prompt
      ineffective, H-C classifier regression, H-D 7A09 unexercised, H-E 7A0A
      CI lint, H-F cross-repo degradation, H-G Player capability wall) each
      marked as confirmed / refuted / partial with citations from the
      transcripts and the current
      `guardkit/orchestrator/autobuild.py`,
      `agent_invoker.py`,
      `coach_validator.py`,
      `worktree_checkpoints.py`,
      `guardkit/orchestrator/prompts/autobuild_execution_protocol{,_medium,_slim}.md`.
- [ ] **Rendered-prompt artefact inspection**: retrieve an actual rendered
      Player prompt from this run's
      `.guardkit/worktrees/FEAT-FORGE-002/.guardkit/autobuild/TASK-NFI-*/`
      (if preserved) or by re-rendering `_build_inline_implement_protocol`
      against the task file. **Quote the actual Phase-3/4/5 text**. Confirm
      presence or absence of the literal `subagent_type="test-orchestrator"`
      / `subagent_type="code-reviewer"`. This is the single most diagnostic
      artefact for H-B.
- [ ] **Jarvis pre/post delta**: identify which specific J002-0XX tasks
      passed in `jarvis-FEAT002-run-1.md` but failed in
      `jarvis-FEAT-002-run-2.md`, and which failed in run-1 but passed in
      run-2. For the regression set, quote the run-1 vs. run-2 agent-
      invocations output side-by-side.
- [ ] Ranked recommendation: either a minimal-footprint remediation set
      (0–N follow-up tasks, each sized 1–10 with hypothesis-class tag) OR
      an explicit **revert plan** naming the tasks to unwind, the
      commits/PRs to revert, the acceptance test for the revert
      (= jarvis-FEAT002-run-3 reaches ≥14/23 completed), and a clean
      problem-restart framing.
- [ ] **Decision checkpoint** (updated for this review's stakes):
      - **[A]ccept** — findings as-is, archive; file follow-ups later by hand.
      - **[I]mplement** — small-bounded follow-up remediation (must justify
        why yet another fix-attempt is credible given the cross-repo
        evidence). Requires the review to name a specific, verifiable
        hypothesis that the new work would test.
      - **[R]evert** — unwind the phase-2 bundle (and optionally phase-1
        gate-tightening if the review concludes 7A07's anti-fraud posture is
        itself the blocking mechanism). Revert plan must be concrete: which
        commits, in what order, with what acceptance test.
      - **[R2]evise** — deeper analysis of a specific hypothesis (rendered-
        prompt inspection only, or cross-repo diff only) before final
        decision.
      - **[C]ancel** — run was non-representative (unlikely given three
        transcripts across two repos, but named for completeness).
- [ ] Root cause classification: **code** (phase-2 fix is broken/partial),
      **scope** (prompt-class fix fundamentally cannot solve this problem),
      **regression** (phase-2 made pre-existing partial-working worse),
      **configuration** (fix is live but defaults/flags neutralised it),
      or **architecture** (orchestrator's Player-completes-inline-with-Bash
      shape is load-bearing for the failure class).
- [ ] Review report saved under
      [docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md)
      — include all four transcripts + the revert-vs-fix recommendation
      with explicit rationale.

## Key References

- **Transcripts in scope** (analyse all four):
  - [docs/reviews/bdd-acceptance-wired-up/forge-run-4.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md)
    (post-phase-2 resume, turn-1 exit — H-A evidence)
  - [docs/reviews/bdd-acceptance-wired-up/forge-run-5.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-5.md)
    (post-phase-2 `--fresh` baseline, Wave 2 0/3 — H-B primary evidence)
  - [docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT-002-run-2.md](../../docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT-002-run-2.md)
    (post-phase-2 jarvis, 12/23 completed — H-F evidence)
  - [docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md](../../docs/reviews/bdd-acceptance-wired-up/jarvis-FEAT002-run-1.md)
    (pre-phase-2 jarvis baseline, 14/23 completed — H-F comparison point)
- **Prior review** (spawned the phase-2 remediation):
  [TASK-REV-F3D7](TASK-REV-F3D7-analyse-forge-run-3-autobuild-failure.md)
- **Prior analysis** (root cause of run-3):
  [docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md)
- **Run-3 transcript** (shape comparison):
  [docs/reviews/bdd-acceptance-wired-up/forge-run-3.md](../../docs/reviews/bdd-acceptance-wired-up/forge-run-3.md)
- **Earlier jarvis review** (for TASK-REV-JMBP context — this was the
  classifier-derivation input):
  [TASK-REV-JMBP](../completed/TASK-REV-JMBP*/TASK-REV-JMBP*.md)
  (may live under `tasks/completed/`; grep for the ID if path differs)
- **Phase-2 completed tasks** (revert candidates):
  - `tasks/completed/TASK-FIX-7A08/` — Player prompt mandate (primary revert
    target if decision is revert)
  - `tasks/completed/TASK-FIX-7A09/` — Coach-path defensive handling
    (low-risk, not a revert target on its own)
  - `tasks/completed/TASK-FIX-7A0A/` — CI lint for dead task-ID refs
    (orthogonal, keep even if phase-2 reverts)
- **Phase-1 completed tasks** (potential broader-revert candidates):
  - `tasks/completed/TASK-FIX-7A01/` through `TASK-FIX-7A07/` plus
    `TASK-DOC-7A06/` — the gate-tightening bundle from FEAT-7A00. 7A07 is
    the specific classifier that enables the Wave-2 rejection loop; if the
    review decides the gate itself is load-bearing for the failure,
    reverting 7A07 may be part of the revert plan.
- **Orchestrator code in scope**:
  - `guardkit/orchestrator/autobuild.py` (classifier, stall-detector, summary)
  - `guardkit/orchestrator/agent_invoker.py` (`_build_inline_implement_protocol`,
    `_invoke_with_role`, `allowed_tools` — relevant to H-G(a))
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (agent-invocations
    gate — relevant to H-G(c) relaxation path)
  - `guardkit/orchestrator/worktree_checkpoints.py` (pollution detector —
    H-A secondary-defect scope)
  - `guardkit/orchestrator/prompts/autobuild_execution_protocol{,_medium,_slim}.md`
    (H-B primary target)
  - `guardkit/orchestrator/phase_specialists.py` (specialist-name truth source)
- **Related runbook**:
  [docs/guides/autobuild-instrumentation-guide.md](../../docs/guides/autobuild-instrumentation-guide.md#if-autobuild-stalls-immediately)

## Notes

- **Fresh-worktree sanity-check already done**: forge-run-5 is the `--fresh`
  baseline. It reproduces the failure. H-A is no longer load-bearing.
- **Framing for this review — this is the one that gets it fixed.** Prior
  iterations have stayed inside the code + logs, produced plausible-looking
  fixes, and shipped them without a behavioural verification method that
  could have caught the "landed but ineffective" failure. That pattern
  ends here. The diagrams are the method; they force us to confront
  what's *actually* crossing each boundary rather than what we assume is
  crossing it. The central questions are:
  1. "Did 7A08's prompt mandate actually reach the LLM verbatim?" —
     answered by Diagram 2 with a preserved-artefact quote.
  2. "If yes, is the Player (LLM) ignoring it, or is the Coach not
     recording the invocations that do happen?" — answered by Diagram 3.
  3. "Is a revert back to pre-phase-2 structurally sufficient to restore
     the jarvis baseline?" — answered by Diagram 4.
- **Revert is a real option here, not a rhetorical one.** The user has
  flagged all autobuild progress as blocked across two repos. Spending
  another fix-cycle on a hypothesis that can't be verified before merge
  is expensive. The review should not default to `[I]mplement` just because
  [I]mplement was the last review's answer — if the diagrams say revert,
  file the revert.
- **The diagrams subsume the "rendered-prompt artefact inspection" AC from
  the prior revision** — Diagram 2 IS that inspection, formalised as a
  labelled sequence with quoted evidence at each hop. If a diagram hop
  cannot be annotated because the artefact was not preserved, that is
  itself a finding: file a separate small task to preserve the
  rendered-prompt + SDK message stream under
  `.guardkit/autobuild/<task>/sdk_debug/` for next run.
- **Design-phase consideration for [I]mplement bundle**: if the review
  proposes another fix-attempt, the proposed fix must include a
  **pre-merge behavioural verification test** that actually invokes the
  SDK with the amended prompt and asserts `agent_invocations_validation`
  returns `3/3 required`. The specific failure mode this review
  investigates is "fix looked right in review and unit tests, but did
  not change live behaviour" — so the next fix must have a test that
  would have caught that. Diagram 2 *is* the reference model that test
  is verifying against: what actually crosses each boundary in a
  passing scenario.
- **It is time to get this fixed.** Three fix-review cycles have now shipped
  without unblocking the autobuild path. This review either produces the
  diagrams, lands the definitive root-cause verdict, and either (a)
  specifies a fix with a pre-merge live-behaviour test, or (b) produces a
  concrete revert plan with an explicit restore target
  (jarvis-FEAT002-run-3 completes ≥14/23 tasks). No fourth fix-then-verify
  cycle from code-read alone.

---

## Next Steps

1. Execute review: `/task-review TASK-REV-F4A1 --mode=architectural --depth=deep`
2. At the checkpoint, choose from:
   - **[A]ccept** — archive findings, file follow-ups later
   - **[I]mplement** — small-bounded remediation with pre-merge behavioural
     verification (must justify credibility)
   - **[R]evert** — unwind phase-2 (and optionally phase-1 gate-tightening)
     to a known-working-at-partial baseline
   - **[R2]evise** — deeper targeted analysis before final decision
3. If [I]mplement, the review spawns sized follow-up tasks that extend
   `autobuild-sdk-stall-resilience-phase2/`.
4. If [R]evert, the review spawns a `TASK-REVERT-*` task plus a
   `TASK-RESTART-*` task for clean-slate re-planning.
5. Complete: `/task-complete TASK-REV-F4A1`.
