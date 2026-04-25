---
title: "Lessons learned — forge-run-6 process-vs-outcome short-circuit"
date: 2026-04-25
review: TASK-REV-F6E1
fix: F3c (coach_validator.py:645-769)
outcome: forge-run-7 = 11/11 green (first-ever green forge run)
---

# Lessons learned — forge-run-6 process-vs-outcome short-circuit

## TL;DR

A single Coach gate-ordering decision (commit `7c14c01d`, 2026-04-23 08:00,
`TASK-FIX-RWOP1.3.1`) wired a process-check at position 1 with early-return
semantics. For the next 2 days every forge run hit `unrecoverable_stall`
on Wave 2 because the Coach never reached its AC verification (positions
2-4). Three review iterations narrowed in on the diagnostic; the
breakthrough came from the user re-framing the problem space — not from
the reviews themselves. Fix was 30 minutes of code (F3c). Result:
forge-run-7 = 11/11 tasks green, ~95 of 99 ACs verified turn-1.

The most important lesson is **about the diagnostic process**, not the bug.

## What actually happened

### The four-day arc

| Date | Event | What it taught us |
|---|---|---|
| 2026-04-22 | Recent BDD-AC bridge work begins | Goal: bridge the "unit tests pass × N tasks → integration breaks" gap by leveraging feature-spec → BDD AC verification in the Coach |
| 2026-04-23 08:00 | `7c14c01d` (RWOP1.3.1): wire `agent_invocations_validation` into the producer | Gate becomes load-bearing for the first time |
| 2026-04-24 12:32 | forge-run-1: infrastructure error (rate_limit_event SDK message) | False alarm |
| 2026-04-24 ~11:32 | forge-run-2: `authentication_failed` | False alarm |
| 2026-04-24 (3 runs) | forge-run-3/4/5: stalls on Phase 4/5 missing-invocation | Real signal — diagnosed as Phase 4/5 prompt-class fragility |
| 2026-04-24 19:25 | TASK-FIX-7A08 lands (mandate Task-tool invocation in Player prompt) | Refuted same day, reverted |
| 2026-04-25 09:30 → 10:41 | FEAT-AB59 / OSI-001..006 lands (orchestrator-side specialist invocation for Phases 4 & 5) | Verified working in production via forge-run-6 incidental live-SDK evidence |
| 2026-04-25 11:22 | forge-run-6: Phase 3 unrecoverable_stall on Wave 2 (0/3) | The next variant of the same defect family — same shape as Phases 4/5 had |
| 2026-04-25 13:00 | TASK-REV-F6E1 review starts (decision mode, 23:00 deadline) | Three revisions to land the right diagnostic |
| 2026-04-25 14:55 | F3c implementation lands | 30-60 min targeted code change |
| 2026-04-25 16:07 | forge-run-7 completes 11/11 green | First-ever green forge run |

Total elapsed from RWOP1.3.1 to first green run: **3 days**, not 3 weeks
as the v1 review wrongly framed.

### What the bug actually was

`coach_validator.py:720` returned early with feedback when
`agent_invocations_validation.status == "violation"`. Positions 2 (quality
gates), 3 (independent test verification), and 4 (criteria/AC matching)
**never executed** when this gate fired. The Coach was rejecting on
*process* without ever measuring *outcome*.

The fix (F3c): demote the gate from blocker to feedback-enricher. Capture
the same enriched description as a non-blocking advisory (`severity=warning`,
`category=agent_invocations_advisory`); thread it through every downstream
return path; let positions 2-4 produce the actual decision.

### The numerical contrast

Same task (TASK-NFI-003), same Player work, same Coach, same gate firing:

- **run-6 turn 1**: 32 files created, 6 modified, 1 test passing, **0/12 criteria verified** → feedback
- **run-6 turn 2**: 4 files created, 47 modified, **0/12** → feedback
- **run-6 turn 3**: 2 files created, 62 modified, **0/12** → unrecoverable_stall
- **run-7 turn 1**: same Player work, **12/12 criteria verified** → APPROVED

The Player implementation was meeting all 12 ACs the whole time. The gate
was preventing the Coach from looking at them.

## Lessons

### 1. The user's reframing was the actual breakthrough

The review went through three revisions:

- **v1** recommended F2' (per-task `implementation_mode: direct` bypass).
  Tactical, sidestepped the structural issue. Wrong because it hid the
  signal rather than fixing the gate.
- **v2** recommended F3c after the user corrected the timeline ("3-4 days
  not 3 weeks") and the strategy ("we have time for a real fix").
  Right diagnostic, but framed iteration plan around 1.5 h cycles.
- **v3** finalised F3c after the user clarified that test runs are
  30-40 min, AutoBuild itself has been solid for weeks, and the real
  next workstream is QA-Tester / feature-level integration via a
  separate `/feature-spec` + `/feature-plan` combo.

The reviewer (me) reasoned at the wrong level of abstraction in v1/v2.
**The user's re-anchoring was the corrective signal that no amount of
log-tracing could substitute for.** Specifically:

- "AutoBuild has been working well — solid for a good few weeks" — this
  immediately ruled out the "architectural debt" framing the reviewer
  was leaning into.
- "All this work was supposed to do is leverage BDD A/C which weren't
  being checked" — this re-named the goal and made it obvious what the
  short-circuit was preventing.
- "I don't know if this work has been made overly complex for some
  reason?" — this is the meta-signal the reviewer should have flagged
  itself but didn't; the user surfaced it.

**Practical implication for future reviews**: when a reviewer is on
iteration 2+ and the user volunteers a re-framing, weight that
re-framing heavily — it's almost always carrying signal the reviewer
hasn't reached. Listen for "I don't understand why X is hard"
specifically — that's the cleanest sign the reviewer is reasoning
above or below the right layer.

### 2. Process gates vs outcome gates — the meta-pattern

Coach validation at the time of run-6 had four gate stages:

| Position | Gate | Type |
|---|---|---|
| 1 | `agent_invocations_validation` | **PROCESS** — did the Player follow the prescribed delegation pattern? |
| 2 | `verify_quality_gates` | OUTCOME |
| 3 | `independent_test_verification` | OUTCOME |
| 4 | criteria-matching against ACs | OUTCOME |

When a process gate is positioned in front of outcome gates with
*early-return* semantics, it converts process drift into task fatality.
That's the full bug.

**Rule of thumb for new gates**:

- Outcome gates can short-circuit (if tests genuinely fail, no point
  matching ACs).
- **Process gates should not short-circuit by default.** Add them as
  feedback-enrichers; promote to blocker only when evidence shows the
  process drift correlates with outcome quality drops.
- New gates should default to advisory (severity=warning) for at
  least two runs of evidence before being promoted.
- The promotion criterion needs to be explicit: "promote to blocker
  when (specific signal) AND (correlation evidence)".

The F3c comment in `coach_validator.py` documents this for the gate
that just landed:

> Promote back to blocker only after evidence shows the advisory-mode
> signal is being systematically ignored AND that absence correlates
> with quality drops in AC verification.

### 3. The diagnostic pattern: "is the iteration loop running the verification step you think it's running?"

Three forge runs (3, 4, 5, 6) iterated on what looked like four different
problems. They were the same problem. The loop kept measuring "did the
Player invoke a specialist via Task tool?" — never measuring "did the
implementation meet the AC?". Each turn produced the same feedback,
which is what triggered the unrecoverable_stall classifier (3 turns of
identical feedback → "no progress").

**Future pattern**: when iteration-without-convergence persists across
2+ turns or 2+ runs, the first thing to check is whether the
verification step is actually executing. Coach early-return on a
position-1 gate looks identical to "Player can't make progress" from
the outside. Both produce the same `unrecoverable_stall` outcome. The
distinguishing signal is `Criteria Progress (Turn N): 0/N verified
(0%)` with `0 rejected, N pending` — that means matching never ran,
not that matching rejected.

### 4. AutoBuild is solid; the BDD-AC bridge is small and recent

Important reframe from the user that the v1/v2 reviewer was missing:
**don't conflate "recent BDD-AC bridge work" with "AutoBuild quality"**.
AutoBuild has been delivering green runs for weeks across nats-core,
nats-infrastructure, and other projects (last green: 2026-04-13 23:01,
nats-infrastructure FEAT-7B86). The recent 3-4 days of pain was
isolated to one targeted feature (BDD AC verification in the Coach
loop).

The right framing is: **a small new feature regressed a stable system
because it landed an over-eager gate**. The fix is targeted unblocking,
not architectural rewrite.

## Roadmap — continuing AutoBuild evolution

The user named the right next workstream: **higher-level test
coordination**, deferred to a future `/feature-spec` + `/feature-plan`
combo, not today.

### Near-term (next 1-2 weeks): observe F3c in the wild

- **Observability**: across forge / jarvis / sibling-repo runs, count
  `agent_invocations_advisory` firings vs `Coach approved` outcomes
  on the same tasks. If the advisory fires and the task still
  approves with high AC verification, the gate is correctly
  non-load-bearing — promotion would be premature.
- **Promotion criterion**: only promote `agent_invocations_advisory`
  back to blocker if evidence emerges of the form "advisory fired
  AND AC verification quality dropped systematically". Today's
  evidence is the opposite — advisory fired 9 times in run-7 and AC
  verification ran cleanly on every task.

### Medium-term: address the actual "we get 80% complete" gap

Today's work fixed a gate-ordering bug. The user's deeper observation
("oftentimes the testing was isolated and when put together components
failed") is **still a real gap** — F3c didn't fix it, it just unblocked
the Coach machinery that was being prevented from running.

Where the residual 80%-complete pattern lives:

- **AC matching quality**: Coach's `validate_requirements` matches the
  Player's `completion_promises` against AC text using fuzzy/synonym
  matching. False negatives here turn into "tests pass but Coach
  rejects" feedback loops. False positives turn into the 80%-complete
  pattern (Coach approves, but the implementation doesn't actually
  satisfy the AC under integration). Run-7's 95/99 = 96%
  turn-1-approval rate is a strong signal but not proof — the 4
  unverified ACs across 11 tasks need spot-checking against actual
  behaviour to calibrate the matcher.
- **Synthetic-report path**: when Player reports lack
  `completion_promises`, Coach falls back to file-existence verification
  (rejects all criteria). Producer-side fix in
  `agent_invoker._write_task_work_results` — make
  `completion_promises` extraction more robust so fewer reports go
  synthetic.
- **BDD oracle integration**: NFI-011 (BDD scenario pytest wiring) just
  approved cleanly, which is the first proof point that BDD scenario
  AC verification is reachable end-to-end. Spot-check the `bdd_runner`
  output to confirm scenario-level rejection actually fires when a
  Player implementation fails its BDD spec.

### Longer-term: feature-level integration coordination

The user's named next workstream — **a forge orchestrator or QA-Tester
agent that can invoke `/task-review` and `/task-work` to run integration
and e2e tests after a feature's individual tasks complete**. This is
the actual answer to "we only get 80% complete":

- Today's F3c gets *task-level* AC verification running.
- Tomorrow's QA-Tester gets *feature-level* integration verification
  running.
- The gap between unit-test-passes and integration-passes is the
  pre-existing pain that the BDD-AC bridge was *designed* to address;
  F3c just removed the gate that was preventing the bridge from
  delivering its signal.

Likely shape:
- New agent role with `Bash` permission to invoke `guardkit` CLI
  commands.
- Coach-equivalent for feature-level verification, runs after all
  tasks in a feature pass.
- E2e phase in the AutoBuild feature orchestrator.

This belongs in a fresh `/feature-spec` + `/feature-plan` combo, not
shoehorned into the AutoBuild orchestrator. The orchestrator should
remain stable; the new agent role should layer on top of it.

### Anti-patterns to avoid

Specifically called out by today's experience:

1. **"Add a new gate to compensate for an existing gate's weakness"** —
   if Coach AC matching is at 80%, don't compensate by adding an
   agent_invocations process gate; improve the AC matcher itself. The
   compensating gate becomes its own load-bearing system and can't
   be retired.
2. **"Mirror the previous structural fix"** — F1 (FEAT-AB60: mirror
   FEAT-AB59 to Phase 3) was a tempting recommendation in v1/v2 of
   the review precisely because FEAT-AB59 had just succeeded for
   Phases 4/5. The right answer was that Phase 3 didn't *need* a
   structural fix — the gate didn't have to be load-bearing.
   **Past structural fixes don't prove the next problem needs the
   same shape.**
3. **"The cheap fix didn't work, the expensive fix is the answer"** —
   TASK-FIX-7A08 was the cheap prompt-class fix, refuted. FEAT-AB59
   was the expensive structural fix for Phases 4/5, succeeded. But
   the next variant (Phase 3) didn't need *either* fix — it needed
   a gate-ordering correction. The fix shape doesn't follow a
   monotonic ladder.

## What to keep doing

- **C4 diagrams and execution traces.** Today's fix was 30 minutes of
  code precisely because the C4/sequence diagrams from prior reviews
  had isolated the relevant module (`coach_validator.py`) and the
  gate-ordering chain. Without that prior work, the v3 diagnostic
  would have taken hours not minutes. The diagrams aren't waste —
  they are the substrate that makes a 30-min fix possible.
- **Three-revision review process.** v1 was wrong; v2 was directionally
  right but missed structure; v3 was right and cheap to land. Going
  through the revisions is the cost of arriving at the correct
  framing. **Don't try to skip to v3.**
- **Knowledge-graph capture on every review acceptance.** The
  `mcp__graphiti__add_memory` writes for TASK-REV-F6E1 (findings,
  outcome, F3c result) mean future reviews of the Coach gate stack
  will not need to rediscover today's lessons.
- **Preserve worktrees per AutoBuild policy.** The 11 task
  implementations in `autobuild/FEAT-FORGE-002` are in human-
  reviewable shape, ready to merge.
