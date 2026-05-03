---
id: TASK-REV-AUTM
title: "Decide how /feature-plan should handle tasks autobuild cannot satisfy (operator-supervision / live-infra / human-in-the-loop)"
status: review_complete
created: 2026-05-03T11:30:00Z
updated: 2026-05-03T12:30:00Z
priority: high
task_type: review
review_mode: decision
review_depth: standard
review_results:
  mode: decision
  depth: standard
  score: 78
  findings_count: 6
  recommendations_count: 7
  decision: implement
  shape_chosen: D
  report_path: .claude/reviews/TASK-REV-AUTM-review-report.md
  follow_up_feature: FEAT-AUTM
  follow_up_folder: tasks/backlog/feature-plan-defects/class-c-task-design-mismatch/
  completed_at: 2026-05-03T12:30:00Z
tags:
  - feature-plan
  - autobuild
  - task-taxonomy
  - operator-handoff
  - architecture-decision
  - cross-repo-followup
complexity: 6
estimated_minutes: 90
related_completed_tasks:
  - TASK-CVAC-001  # parser fix (compound + markdown-bold AC IDs) — completed 2026-05-02
  - TASK-CVAC-002  # bidirectional matching fallback — completed 2026-05-03
related_open_features:
  - feature-plan-smoke-gate-validation  # Classes A + B of /feature-plan defects (path validation, temporal mis-sequencing)
related_incidents:
  - appmilla_github/study-tutor FEAT-FD32 TASK-GR-SEED — 5/5 turns 0/8 verified, all ACs are live-infra runtime claims
  - appmilla_github/study-tutor FEAT-FD32 TASK-GR-DEMO — 5/5 turns 0/7 verified, 6/7 ACs are human-in-the-loop Claude Desktop session
context_files:
  - appmilla_github/study-tutor/.guardkit/features/FEAT-FD32.yaml  # carries multi-line provenance comments on both manually-completed tasks
  - appmilla_github/study-tutor/tasks/backlog/graphiti-runtime-integration-repair/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
  - appmilla_github/study-tutor/tasks/backlog/graphiti-runtime-integration-repair/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md
  - appmilla_github/study-tutor/docs/history/autobuild-FEAT-FD32-failed-after-raising-floor-history.md  # SEED reproducer
  - appmilla_github/study-tutor/docs/history/autobuild-FEAT-FD32-failed-yet-again-history.md  # DEMO reproducer
  - installer/core/commands/feature-plan.md
  - guardkit/orchestrator/quality_gates/coach_validator.py
  - guardkit/orchestrator/feature_loader.py
---

# Review: How should /feature-plan handle tasks autobuild cannot satisfy?

## Problem Statement

`/feature-plan` routinely produces tasks whose acceptance criteria
**no autobuild agent can ever satisfy**, because the verification
predicate is `observed_at_runtime(real_world)` rather than
`present_in_codebase(artifact)`. Coach grades by file-existence and
test-passing, which can never produce evidence for a runtime-observed
claim. Player can scaffold for the observation but not perform it.

The result is wasted SDK budget, false orchestrator failures, fatigued
operators, and an erosion of trust in autobuild as a reliable
execution channel.

### Reproducers (from study-tutor FEAT-FD32, 2026-05-02 → 2026-05-03)

**TASK-GR-SEED — 7 of 8 ACs require live infrastructure**:

> AC-SEED-01 — `python scripts/seed_student_model.py` runs successfully
> against live FalkorDB at whitestocks:6379 ... All 25 entity writes
> succeed without 401s, timeouts, or GroupIdValidationError failures.
> AC-SEED-02 — `mcp__graphiti__search_nodes(query="Lilymay") returns
> the Student entity with the expected attributes ...
> AC-SEED-07 — Wall-clock for the seed run captured. Expected ~30 min ...

Outcome: 5 turns, 0/8 verified, `max_turns_exceeded`. Player wrote
~22 files of legitimate scaffolding work. The seed has to be run by a
human against the real FalkorDB — and that's exactly what the task
text *says*.

**TASK-GR-DEMO — 6 of 7 ACs require human-in-the-loop**:

> AC-DEMO-01 — A live MCP tutor session is conducted from Claude Desktop
> with the user as the human-in-the-loop. Sequence: 5–7 × tutor_turn(...)
> exchanges with at least one Coach revision ...
> AC-DEMO-04 — Turn-level latency captured. Record p50 and p95 of
> tutor_turn wall-clock across all 5–7 turns ...

Outcome: 5 turns, 0/7 verified, `max_turns_exceeded`. Player honestly
self-reported `status: incomplete` with the evidence string *"Cannot
be satisfied by autobuild. There is no automated test harness for
Claude Desktop performs a 5–7 turn tutoring session with a real LLM
at the back."*

### Cumulative cost in this single feature

| Metric | Value |
|---|---|
| SDK budget burned on tasks autobuild could never finish | ~110 minutes (5+5 turns × ~10-15 min each) |
| Tasks that needed manual YAML completion to bypass | 2 of 5 (40%) |
| Operator interventions required to unblock | 4 separate `--resume` cycles + 2 manual completions |
| Incident-debugging time | ~3 hours of conversation across 2 days |

This is not a one-off — the same pattern will reappear on every
feature with operationally-flavoured ACs (re-seeds, live demos,
production validation, integration verification with external
systems). It scales with feature count, not with task quality.

### Why TASK-CVAC-001/002 are necessary but not sufficient

The `coach-validator-ac-id-matching/` workstream fixed a real bug
(Player and Coach disagreeing on AC ID format) that masked the
underlying problem in some incidents. With CVAC-001 + CVAC-002 in
place, the AC-matching contract is robust in both directions. But
that just *unmasks* the deeper issue: even with perfect matching,
ACs of the runtime-observed kind still produce `status: incomplete`
honestly because the work genuinely cannot be done by Player.

This review is about the **next** layer: stop generating these tasks
in autobuild-shaped form in the first place, OR mark them so
autobuild knows to skip them.

## Decision Space

Four shapes for the fix, each with different costs, surface area, and
enforcement strength. The review is to pick one (or a documented
hybrid).

### Shape A — New `task_type: operator_handoff` (task-level)

Add a new value to the existing `task_type` taxonomy
(`feature` / `review` / `research` / `docs` / `declarative` →
`feature` / `review` / `research` / `docs` / `declarative` / `operator_handoff`).

**Behaviour**:
- `/feature-plan` recognises operator-shaped tasks at plan time and
  tags them with this type.
- `/feature-build` (autobuild) skips tasks of this type entirely;
  they don't enter the Player↔Coach loop.
- `feature_loader._parse_feature` validates the type.
- `feature_orchestrator` reports them in the wave summary as
  "DEFERRED — operator handoff" rather than running them.
- `/feature-complete` surfaces them in the merge summary as a
  required operator follow-up checklist.

**Cost**: ~3-4 small subtasks (taxonomy update, plan-side detection,
orchestrator skip, feature-complete summary). One source of truth at
the task level.

**Coarse-grained**: A task is either fully autobuild OR fully
operator. If a task has 1 autobuild-suitable AC and 6 operator ACs,
it gets the operator type and the autobuild work is lost.

**Real-world fit**: TASK-GR-SEED (7/8 manual) and TASK-GR-DEMO (6/7
manual) — both genuinely fit "fully operator" once you include the
sequential dependencies. The 1 autobuild-suitable AC in each (lint
pass) is trivial compared to the 6-7 operator ACs that make the
task's primary deliverable real. Loss is acceptable.

### Shape B — Per-AC labelling

Tag individual ACs as manual using a syntactic marker:
`**[manual]** AC-FOO-03 — ...` or
`- [ ] **AC-FOO-03** *(operator)* — ...`.

**Behaviour**:
- Coach's AC parser reads the tag.
- Tagged ACs are auto-marked `verified` with evidence "deferred to
  operator" — they don't block Player approval.
- `/feature-complete` lists tagged ACs in the operator follow-up
  checklist.

**Cost**: ~5-6 subtasks (AC parser extension, Coach marker handling,
prompt rule for /feature-plan, summary surface, taxonomy doc, tests).
More granular but more complex.

**Granular**: Mixed-mode tasks (some autobuild ACs, some manual)
ship cleanly. Player gets credit for the autobuild work.

**Risk**: Authors must remember to tag every operator AC. Easy to
forget, and silent failures look like the current incidents
(autobuild grinds through 5 turns rejecting an untagged manual AC).
Detection at plan-time is still required to be reliable, which means
this isn't strictly simpler than A — it's A + per-AC granularity.

### Shape C — `/feature-plan`-side detection only (no taxonomy change)

`/feature-plan` detects high-risk patterns at plan time and either:

- (c1) Refuses to commit the plan until the user manually splits
  operator work into a separate `## Out-of-band Operator Tasks`
  appendix that doesn't enter the wave plan.
- (c2) Warns the user with a list of suspect ACs and asks for
  per-AC confirmation: *"AC-FOO-03 looks like it requires live
  runtime verification. Include in autobuild scope? [y/N]"*.

**Behaviour**:
- No changes to autobuild, Coach, or task_type.
- `/feature-plan` is the single chokepoint.

**Cost**: ~2 subtasks (detector + interactive prompt extension).
Lowest-impact.

**Risk**: Relies entirely on detection accuracy. False negatives
(operator ACs that slip through detection) reproduce today's
incidents with no other safety net. False positives (autobuild ACs
flagged as operator) cost user attention but not orchestrator
budget — relatively benign.

**No enforcement**: If a user clicks past the warning or the
detector misses, autobuild still gets a non-runnable task. Same
failure mode as today, just less frequent.

### Shape D — Hybrid (A + C)

`/feature-plan` detects (Shape C) AND new `task_type: operator_handoff`
enforces (Shape A).

**Behaviour**:
- Plan-time: `/feature-plan` flags suspect ACs and proposes splitting
  the task or marking the whole task as `operator_handoff`. User
  confirms.
- Run-time: autobuild respects `task_type: operator_handoff` and
  skips. Coach is never invoked. Feature summary surfaces.
- If the detector misses and the user doesn't notice, autobuild still
  hits the failure (same as today). But the rate drops because the
  detector catches most cases.

**Cost**: ~5-6 subtasks (sum of A's task-side + C's plan-side, minus
some shared infrastructure). Most thorough.

**Strongest defence**: Two layers (detector + enforcer). Either
catches a Class C; both must miss for a failure.

### Shape E (rejected from this review's scope, documented for posterity)

**Coach-side fuzzy understanding** of "I cannot satisfy this AC" /
"deferred to operator" in Player's evidence text. Coach reads the
evidence string, recognises Player's honest "Cannot be satisfied by
autobuild" surrender, and either approves the task or escalates to
the user. **Rejected** because: (a) relies on natural-language
intent detection in Coach which is fragile, (b) creates a backdoor
for Player to claim everything as deferred, (c) the right place to
solve this is at plan-time, not validation-time.

## Decision Matrix

| Criterion | Shape A | Shape B | Shape C | Shape D | Shape E |
|---|---|---|---|---|---|
| Solves the headline incident pattern | ✓ | ✓ (if tagged) | ◐ (if detected) | ✓✓ | ◐ |
| Coarse vs granular | Coarse | Granular | N/A | Coarse | N/A |
| Cost (subtasks) | 3-4 | 5-6 | 2 | 5-6 | 2 |
| Two-layer defence | ✗ | ✗ | ✗ | ✓ | ✗ |
| Failure mode if missed | Same as today | Same as today | Same as today | Same as today (rare) | Backdoor risk |
| Friction at plan time | None | None | Medium (interactive) | Medium | None |
| Implementation risk | Low | Medium | Low | Medium | High |
| Recommended | | | | **★** | (rejected) |

## Detection Rules (applies to Shapes A, C, D)

The detector is the hard part. Whichever shape is chosen, these
patterns flag a probable Class C / operator-shaped AC.

### Strong signals (high-confidence flag)

- **Live-infra references**: "FalkorDB at <host>", "live", "production",
  "real LLM", "real OpenAI", "MCP query against running",
  "AWS / GCP / Azure", explicit hostnames, ports, URLs to non-local services.
- **Human verbs**: "conduct", "drive [N] turns", "observe",
  "human-in-the-loop", "operator", "Claude Desktop session",
  "open ChatGPT", "review the dashboard", "watch for", "monitor".
- **Wall-clock language**: "p50/p95", "wall-clock", "latency over a
  N-minute run", "30 minutes of operation", "soak", "burn-in".
- **Test Requirements section says so**: "There is no automated test
  harness for ...", "manual verification required", "operator runs
  the script and pastes the result".

### Weak signals (low-confidence; flag only when paired with strong)

- "verify", "ensure", "check" (often autobuild-suitable on their own)
- references to "running" something (could be a unit test or a live run)
- references to specific user names ("Lilymay", "test-user-123")

### False-positive guard

A weak signal alone does NOT trigger a flag. Strong signals always
trigger. Mixed (1 strong + N weak) trigger. The `/feature-plan` agent
asks the human to confirm when triggered; the human is the final
arbiter for marginal cases.

## Acceptance Criteria

For this review to be COMPLETE:

- [ ] **AC-AUTM-01** — One shape (A / B / C / D) is selected with a
      written rationale. The rationale explicitly addresses why the
      OTHER shapes were rejected, not just why the chosen shape is
      good.
- [ ] **AC-AUTM-02** — Detection rules are agreed: which signals
      trigger automatically, which require human confirmation, what
      the false-positive tolerance is. The rules MUST be testable
      against the two FEAT-FD32 reproducers (TASK-GR-SEED,
      TASK-GR-DEMO) — both should be flagged by the chosen rules.
- [ ] **AC-AUTM-03** — A list of follow-up implementation tasks is
      drafted, sized, and prioritised. Naming + folder placement
      decided (sibling to `feature-plan-smoke-gate-validation/`?
      same folder, renamed? new folder?).
- [ ] **AC-AUTM-04** — Backwards-compatibility plan: existing
      features in flight (study-tutor FEAT-FD32 already half-shipped,
      forge FEAT-DEA8 already shipped) — what, if anything, needs
      retroactive labelling? My read: nothing — the manually-completed
      YAML provenance comments in FEAT-FD32 are sufficient
      historical record. But this should be explicit.
- [ ] **AC-AUTM-05** — Documentation update plan: where do the new
      rules go? `installer/core/commands/feature-plan.md`,
      `CLAUDE.md`, a new `docs/feature-plan-task-classification.md`?
      Plus the README of whichever folder the implementation tasks
      land in.
- [ ] **AC-AUTM-06** — Decision report written to
      `.claude/reviews/TASK-REV-AUTM-review-report.md` with the chosen
      shape, rationale, detection rules, and follow-up task plan.

## Recommendation (for the reviewer to confirm or revise)

**Shape D (hybrid A + C)** with the detection rules as outlined,
follow-up tasks slotted into a renamed
`feature-plan-task-classification/` folder (consolidating with
`feature-plan-smoke-gate-validation/` since both are `/feature-plan`
defect classes — Class A path validation, Class B temporal
sequencing, Class C task-design mismatch — and the implementations
share infrastructure).

Rationale for D over A: Shape A on its own enforces but doesn't help
the user write better feature plans in the first place. Shape D's
detector catches issues at plan time when the cost of fixing is
lowest (a prompt back-and-forth, not 30+ min of wasted SDK budget).
The enforcement layer (`task_type: operator_handoff`) is the safety
net for cases the detector misses.

Rationale against B (per-AC granularity): real-world incidents had
6-7 of 7-8 ACs as manual. The 1 autobuild-suitable AC in each is
typically trivial (lint pass) — losing it costs less than the
implementation complexity of per-AC labelling. Revisit if a future
feature shows a 4-out-of-8 mixed pattern.

Rationale against C alone (no enforcement): without `task_type`
enforcement, a missed detection still produces today's failure mode.
The cost of the enforcement layer is small compared to the cost of
recurring incidents.

Rationale against E (Coach-side detection): puts intelligence in the
wrong place. The right answer is "don't generate this kind of task
for autobuild," not "make Coach smart enough to forgive Player when
the task is impossible."

## Out of Scope

- **Implementation**. This is a decision review. Implementation tasks
  spawn from AC-AUTM-03's follow-up plan.
- **Per-feature retroactive cleanup of existing operator-shaped tasks
  in study-tutor / forge / etc.** Not needed; the manual completions
  + YAML comments are sufficient historical record.
- **Changes to Coach validator AC matching**. TASK-CVAC-001 (parser)
  and TASK-CVAC-002 (bidirectional matching) are complete and orthogonal.
- **The feature-plan-smoke-gate-validation/ Classes A and B**. Those
  are narrow technical defects with concrete fixes already drafted in
  TASK-FPSG-001..005. This review may *consolidate* the workstreams
  (rename the folder), but does not block on their completion.

## Files

- New: `tasks/backlog/TASK-REV-AUTM-decide-how-feature-plan-handles-autobuild-unsuitable-tasks.md` (this file)
- Decision report (post-review): `.claude/reviews/TASK-REV-AUTM-review-report.md`
- Likely affected by chosen implementation:
  - `installer/core/commands/feature-plan.md`
  - `guardkit/orchestrator/feature_loader.py` (task_type taxonomy)
  - `guardkit/orchestrator/feature_orchestrator.py` (skip behaviour)
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (skip awareness)
  - `installer/core/commands/feature-complete.md` (operator-handoff summary)
  - Possibly: `installer/core/commands/lib/generate_feature_yaml.py` (validate task_type)

## Cross-Repo Provenance

- **Sibling complete**: TASK-CVAC-001 (parser, commit 5192fc60) +
  TASK-CVAC-002 (bidirectional matching, completed 2026-05-03 by
  user). Both in `tasks/completed/2026-05/coach-validator-ac-id-matching/`.
- **Sibling in flight**: `tasks/backlog/feature-plan-smoke-gate-validation/`
  (Classes A + B of /feature-plan defects).
- **Real-world incidents driving this review**:
  - study-tutor FEAT-FD32 TASK-GR-SEED — manually completed 2026-05-03
  - study-tutor FEAT-FD32 TASK-GR-DEMO — manually completed 2026-05-03
  - Both have detailed provenance comments in
    [appmilla_github/study-tutor/.guardkit/features/FEAT-FD32.yaml](../../../study-tutor/.guardkit/features/FEAT-FD32.yaml).
- **Suggested consolidation target**: rename
  `feature-plan-smoke-gate-validation/` → `feature-plan-task-classification/`
  (or similar) once this review's implementation tasks land, so all
  three defect classes (A path validation, B temporal sequencing,
  C task-design mismatch) live as one workstream.
