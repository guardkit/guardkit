# Decision Review: TASK-REV-AUTM

**How should `/feature-plan` handle tasks autobuild cannot satisfy?**

| Field | Value |
|---|---|
| Review mode | decision |
| Review depth | standard |
| Reviewer | software-architect / architectural-reviewer (synthesis) |
| Date | 2026-05-03 |
| Decision | **Shape D (hybrid: plan-time detector + `task_type: operator_handoff` enforcement)** |
| Score | 78 / 100 (recommendation strength; 22 points withheld for residual detector-accuracy risk and prompt-engineering uncertainty in Wave 1) |
| Findings | 6 |
| Recommendations | 7 follow-up tasks |

## Executive Summary

`/feature-plan` regularly emits acceptance criteria whose verification predicate
is `observed_at_runtime(real_world)` rather than `present_in_codebase(artifact)`.
Player and Coach cannot satisfy these by construction. The only safe outcomes are
(1) don't generate the task in autobuild-shaped form, or (2) tag it so autobuild
declines to attempt it. We recommend doing both — plan-time detection (cheap, catches
most cases at the lowest-cost moment) plus an `operator_handoff` task_type the
orchestrator hard-skips (safety net for cases the detector misses). This is
**Shape D** in the task's decision space.

The two-layer pattern is already validated in this codebase: the sibling workstream
`feature-plan-smoke-gate-validation/` adopts the same shape (L3a/b/c/d at the plan +
generation + validate boundaries, L4 as load-time defence-in-depth) for Class A
(invented paths) and Class B (temporal mis-sequencing) defects of `/feature-plan`.
Class C (task-design mismatch — this review) is the third defect in the same family
and should consolidate into the same workstream folder.

## AC-AUTM-01 — Decision and rationale

### Decision: Shape D

**Plan-time detector (Shape C) PLUS task-type enforcement (Shape A).**

### Why D over A (enforcement only)

Shape A as a standalone solves the symptom but doesn't help the user write better
plans in the first place. The cost of fixing a misclassified task at plan time
(one prompt round-trip, ~30 seconds of attention) is roughly 60× cheaper than
catching it at run time (one full Player↔Coach turn-budget burn, ~10–15 minutes
of SDK budget × the average 5-turn cap = ~50–75 minutes per missed task; FEAT-FD32
empirically cost ~110 minutes across two such tasks). The detector pays for itself
on the first prevented incident. Adding the detector on top of A is incremental
work, not redundant.

### Why D over B (per-AC labelling)

Both real-world reproducers had **6–7 of 7–8 ACs as manual** — the mixed-mode case
B optimises for is theoretical, not observed. The single autobuild-suitable AC in
each (a lint pass) is small relative to the implementation complexity of an AC
parser extension, prompt rule, Coach marker handling, summary surface, and tests.
Shape B is also strictly more complex than A — it needs every detection mechanism
A needs (otherwise the author forgets to tag), so the per-AC granularity is purely
additive cost. The right time to revisit B is when a feature genuinely shows a
4-of-8 mixed-mode pattern; the current evidence is 7-of-8 + 6-of-7, both of which
fit "fully operator" cleanly.

### Why D over C alone (detection without enforcement)

A missed detection in Shape C reproduces today's failure mode exactly: the task
enters autobuild, Coach can't verify the AC, Player burns the turn budget, the
orchestrator reports `max_turns_exceeded`. The cost of the enforcement layer
(`operator_handoff` task_type + ~1h orchestrator skip) is small relative to even
one recurring incident. The two-layer model (detect early, enforce late) is the
same pattern used by the sibling Class A/B workstream and by
`coach-validator-ac-id-matching/` (parser fix + bidirectional matching fallback).
Defence-in-depth is cheap when the layers are independent.

### Why D over E (Coach-side fuzzy understanding) — concurring with task author

E puts the intelligence in the wrong place. "Coach is smart enough to forgive
Player when the task is impossible" is a backdoor: Player can claim every task is
deferred. The right answer is "don't generate this kind of task for autobuild."
Coach should remain a deterministic file-existence and test-passing checker.
Rejected, no dissent.

### Cost validation

The Shape A subtask estimate (3–4 small tasks) is consistent with the existing
`TaskType` enum extension cost — examination of `guardkit/models/task_types.py`
shows the enum already has the right shape for adding `OPERATOR_HANDOFF` with a
no-tests/no-arch-review profile. The Shape C subtask estimate (~2 tasks) is
consistent with the existing `/feature-plan` agent prompt surface, which already
has a Task Type Assignment Rules table that just needs a new row plus an
interactive confirmation step. Shape D = A + C minus shared infrastructure ≈ 6
tasks ≈ 11 hours, which matches the proposal in the task description.

## AC-AUTM-02 — Detection rules

### Strong signals (auto-flag)

A single match triggers the operator-handoff prompt at plan time.

| Category | Patterns |
|---|---|
| Live infrastructure | `FalkorDB at <host>`, `Redis at <host>`, hostnames like `whitestocks`, `promaxgb10-*`, `localhost:<port>` paired with "live" or "production", URLs to non-local services, "real LLM", "real OpenAI", "MCP query against running" |
| Human verbs | "conduct", "drive [N] turns", "observe", "human-in-the-loop", "operator", "Claude Desktop session", "open ChatGPT", "review the dashboard", "watch for", "monitor", "tutoring session" |
| Wall-clock language | "p50", "p95", "wall-clock", "latency over a N-minute run", "30 minutes of operation", "soak", "burn-in", "Expected ~30 min" |
| Author self-disclosure | Test Requirements (or equivalent) section contains "There is no automated test harness for ...", "manual verification required", "operator runs the script and pastes the result", "cannot be satisfied by autobuild" |

### Weak signals (require pairing)

Only flag when paired with at least one strong signal.

- "verify", "ensure", "check" (often autobuild-suitable on their own)
- references to "running" something (could be unit test or live run)
- references to specific user names ("Lilymay", "test-user-123")
- references to specific dataset names that may or may not exist on disk

### False-positive guard

A weak signal alone does NOT trigger. Strong signals always trigger. Mixed
(1 strong + N weak) trigger. The detector flags; the human is the final
arbiter via interactive confirmation.

### Testability against the two FEAT-FD32 reproducers (required by AC-AUTM-02)

**TASK-GR-SEED — AC-SEED-01 verbatim**:
> *"`python scripts/seed_student_model.py` runs successfully against
> live FalkorDB at whitestocks:6379 ... All 25 entity writes succeed
> without 401s, timeouts, or GroupIdValidationError failures."*

Strong signals matched:
- `live FalkorDB at whitestocks:6379` → live infrastructure (hostname + port + "live")
- `25 entity writes succeed` → wall-clock observation
- `~30 min` (AC-SEED-07) → wall-clock language

**Verdict: ✓ flagged. Multiple strong signals.**

**TASK-GR-DEMO — AC-DEMO-01 verbatim**:
> *"A live MCP tutor session is conducted from Claude Desktop with the
> user as the human-in-the-loop. Sequence: 5–7 × tutor_turn(...) exchanges
> with at least one Coach revision ..."*

Strong signals matched:
- `live MCP tutor session` → live infrastructure
- `conducted from Claude Desktop` → human verb + Claude Desktop session
- `human-in-the-loop` → explicit author disclosure
- `5–7 × tutor_turn(...) exchanges` → wall-clock observation
- `p50 and p95 of tutor_turn wall-clock` (AC-DEMO-04) → wall-clock language

**Verdict: ✓ flagged. Strong signals on three independent dimensions.**

Both reproducers are caught by the rules. AC-AUTM-02 is satisfied.

### False-positive risk assessment

Three benign-looking ACs that should NOT trigger:

1. *"All unit tests pass with `pytest tests/ -v`."* — verb `pass` is weak; no
   strong signals. Not flagged. Correct.
2. *"`SettingsClass.from_env()` reads `FALKORDB_HOST` from environment and
   constructs a valid client config."* — mentions FalkorDB but as a config
   string, not a live target. Verb `reads` is weak. Not flagged. Correct.
3. *"Documentation explains how an operator can run the seed script."* — verb
   "operator" is strong. **Flagged**. False positive — but acceptable: the
   prompt asks "is this a runtime claim?" and the author answers "No, it's a
   docs task," and the workflow continues. The cost is one prompt confirmation,
   not a turn-budget burn.

The false-positive cost (operator-attention) is bounded by the number of strong
signals per plan; the false-negative cost (turn-budget burn) is unbounded. Bias
the detector toward false positives.

## AC-AUTM-03 — Follow-up implementation tasks

### Folder placement

**Recommendation: rename `tasks/backlog/feature-plan-smoke-gate-validation/` →
`tasks/backlog/feature-plan-defects/`** and consolidate three sub-features:

```
feature-plan-defects/
  README.md  (rewritten to cover three classes)
  IMPLEMENTATION-GUIDE.md
  class-a-invented-paths/        # existing TASK-FPSG-002, 003 + drafts for 001, 004, 005
  class-b-temporal-sequencing/   # existing TASK-FPSG-002, 003, 004, 005 share helpers with A
  class-c-task-design-mismatch/  # NEW — this review's output
    TASK-FPTC-001-feature-plan-detector-and-prompt.md
    TASK-FPTC-002-task-type-operator-handoff-enum.md
    TASK-FPTC-003-orchestrator-skip-operator-handoff.md
    TASK-FPTC-004-validator-and-loader-awareness.md
    TASK-FPTC-005-feature-complete-operator-checklist.md
    TASK-FPTC-006-detector-tests-against-reproducers.md
    TASK-FPTC-007-docs-and-folder-consolidation.md
```

The existing FPSG-001..005 retain their IDs (don't churn task IDs); only the
folder layout changes.

Rationale: all three classes are `/feature-plan` defects, share the
`generate_feature_yaml` / `feature_loader._parse_feature` validator surface, and
are best understood as one workstream. The CVAC workstream (parser + matching)
is correctly a separate folder because it lives at the validator / runtime
boundary, not the planning boundary.

### Subtasks

| ID | Layer | Task | Effort | Wave |
|---|---|---|---|---|
| **TASK-FPTC-001** | Plan (L3a) | Add detector to `/feature-plan` agent prompt + interactive confirmation step. Strong-signal grep + LLM judgement gate. When triggered, show the user the AC text and ask "Mark task as `operator_handoff` and skip autobuild? [Y/n]". On Y: emit `task_type: operator_handoff` in the task frontmatter and append a `Required operator follow-up` block to the task body listing the runtime ACs verbatim. | 2h | 1 |
| **TASK-FPTC-002** | Taxonomy | Add `OPERATOR_HANDOFF = "operator_handoff"` to `guardkit/models/task_types.py::TaskType`. Register `QualityGateProfile(arch_review_required=False, arch_review_threshold=0, coverage_required=False, tests_required=False, ...)` in `DEFAULT_PROFILES`. Update aliases if any. Update `feature-plan.md` Task Type Assignment Rules table with a new row. Update `feature_loader._validate_task_type_in_file` to accept the new value. | 1h | 1 |
| **TASK-FPTC-003** | Runtime | `guardkit/orchestrator/feature_orchestrator.py`: at task dispatch, if `task_type == operator_handoff`, mark task as `DEFERRED` (new state, parallel to `BLOCKED`/`COMPLETED`), record reason "operator follow-up — runtime verification required", do NOT enter Player↔Coach loop. Wave summary lists deferred tasks distinctly from completed/failed. | 2h | 2 |
| **TASK-FPTC-004** | Validator | `guardkit/orchestrator/quality_gates/coach_validator.py`: skip AC matching for `operator_handoff` tasks. `feature_loader._parse_feature`: accept tasks of this type without requiring ACs to be coach-verifiable. Add contract test asserting an operator-handoff task with all-runtime ACs loads cleanly. | 1.5h | 2 |
| **TASK-FPTC-005** | Surface | `installer/core/commands/feature-complete.md` + merge-summary code path: surface a "Required operator follow-up" checklist in the merge report, listing all deferred tasks with their ACs verbatim. Operator can tick them off post-merge. Also surface in `/feature-plan` plan summary so the user sees the count before approving the plan. | 1.5h | 3 |
| **TASK-FPTC-006** | Tests | End-to-end tests using TASK-GR-SEED and TASK-GR-DEMO ACs as fixtures. Both must be flagged by detector. False-positive guard tested with the three benign-looking ACs in §AC-AUTM-02. Plus a fixture for a happy-path autobuild-suitable AC ("Calling `parse_yaml(s)` returns the expected dict with key `version=1`") which must NOT be flagged. | 2h | 3 |
| **TASK-FPTC-007** | Docs | Rename folder, rewrite consolidated README, update `installer/core/commands/feature-plan.md` Task Type Assignment Rules and add a "Detection Rules" subsection, add a `docs/guides/feature-plan-task-classification.md` describing the three defect classes, cross-link from CLAUDE.md → "Feature Planning & Build" section. | 1h | 3 |

**Total: 11 hours / 7 tasks.**

### Wave plan

```
Wave 1 (parallel): FPTC-001 (detector+prompt), FPTC-002 (taxonomy)
Wave 2 (parallel): FPTC-003 (orchestrator skip), FPTC-004 (validator/loader)   ← both consume FPTC-002
Wave 3 (parallel): FPTC-005 (feature-complete), FPTC-006 (tests), FPTC-007 (docs)
```

FPTC-001 and FPTC-002 are independent. Wave 2 needs the new enum value to exist.
Wave 3 needs the runtime behaviour to be in place before docs/tests can land.

### Priority ordering (independent of waves)

1. FPTC-002 (cheapest, unblocks Wave 2).
2. FPTC-001 (highest value: prevents new bad plans from being authored).
3. FPTC-003 + FPTC-004 (enforcement layer — pair them).
4. FPTC-005 (operator UX — needed before any operator-handoff task is shipped).
5. FPTC-006 (tests — needed for confidence).
6. FPTC-007 (docs — last because docs follow code).

## AC-AUTM-04 — Backwards compatibility

**Recommendation: no retroactive labelling.** Confirming the task author's read.

- **study-tutor FEAT-FD32** — both TASK-GR-SEED and TASK-GR-DEMO were manually
  completed 2026-05-03 with detailed provenance comments in
  `appmilla_github/study-tutor/.guardkit/features/FEAT-FD32.yaml`. The
  comments explain why autobuild couldn't satisfy the ACs and what the
  operator did instead. That is sufficient historical record. Adding
  `task_type: operator_handoff` retroactively would be a no-op (autobuild
  is no longer running on those tasks) and would lose the diagnostic value
  of the original `incomplete` markers.
- **forge FEAT-DEA8** — already shipped 11/11 after the Class A path-validation
  fix. No operator-handoff tasks in scope retroactively.
- **In-flight features** — none currently. If one starts before FPTC-001 ships,
  the operator simply marks tasks `manual` as today.

The boundary is clear: this rule applies to `/feature-plan` runs after FPTC-001
ships. Existing artifacts are frozen.

## AC-AUTM-05 — Documentation update plan

| Surface | Update |
|---|---|
| `installer/core/commands/feature-plan.md` | (a) Add `operator_handoff` row to Task Type Assignment Rules table around line 1311. (b) New section "Detection Rules — when to mark a task `operator_handoff`" with strong/weak signal taxonomy. (c) Step-by-step description of the interactive prompt. |
| `installer/core/commands/feature-complete.md` | New section "Operator follow-up checklist" describing how deferred tasks are surfaced in the merge summary. |
| `installer/core/commands/lib/generate_feature_yaml.py` | Validate that `task_type` field accepts `operator_handoff`. (Mostly a one-liner if it currently uses an enum/whitelist; currently it appears not to validate, see TASK-FPSG-002 scope — coordinate with that task.) |
| `guardkit/models/task_types.py` | Enum + profile (TASK-FPTC-002). |
| `.claude/rules/task-workflow.md` | Add `operator_handoff` to the Status Transitions / States table. Document the new `DEFERRED` task state if introduced (FPTC-003). |
| `.claude/rules/clarifying-questions.md` | No update — not a clarifying-question feature. |
| `docs/guides/feature-plan-task-classification.md` | NEW — describe the three defect classes (A/B/C), the detection rules, the operator-handoff escape hatch, and the philosophy of "plan-time prevention beats runtime detection." Cross-linked from CLAUDE.md "Feature Planning & Build" section. |
| `CLAUDE.md` (root) | One-line cross-ref under "Feature Planning & Build" section pointing at the new guide. |
| `tasks/backlog/feature-plan-defects/README.md` | Rewritten to cover Classes A, B, C (this is part of FPTC-007). |

## AC-AUTM-06 — Decision report ✓

This document is the decision report. Written to
`.claude/reviews/TASK-REV-AUTM-review-report.md`.

## Findings

| # | Finding | Severity |
|---|---|---|
| F1 | The 7-task taxonomy in `guardkit/models/task_types.py` already supports the no-tests/no-arch-review profile shape needed for `OPERATOR_HANDOFF` (similar to `DOCUMENTATION`, `DECLARATIVE`); cost estimate of 1h for FPTC-002 is accurate. | informational |
| F2 | Two parallel `task_type` taxonomies exist: the orchestrator's `TaskType` enum (8 values, used for quality gate profiles) and the plan-side conventions in `feature-plan.md` (which adds "review"). The new `operator_handoff` value must be added to BOTH. The plan-side surface lives at `feature-plan.md` lines 1311–1340. | medium — easy to miss one half |
| F3 | The sibling workstream `feature-plan-smoke-gate-validation/` (Classes A and B) uses the same multi-layer defence pattern (L3a/b/c/d + L4) recommended here for Class C. Consolidating folders improves discoverability and shares the validator infrastructure. | low |
| F4 | TASK-CVAC-001 + TASK-CVAC-002 close the validator-side AC-matching contract, which means there is no longer a confounding bug masking Class C symptoms. The diagnostic baseline is clean. This is the right time to ship Shape D. | informational |
| F5 | The detection rules' false-positive cost is bounded (one operator confirmation per flagged AC) while the false-negative cost is unbounded (full turn-budget burn). Detector should bias toward false positives, which the strong/weak/pairing rules already do. | informational |
| F6 | No retroactive labelling needed for existing features — manual completion provenance comments in `FEAT-FD32.yaml` are sufficient historical record, and forge `FEAT-DEA8` shipped clean post-Class-A fix. | informational |

## Context Used

Review informed by:
- **Task description** (TASK-REV-AUTM frontmatter and body) — full Decision Space, Decision Matrix, Detection Rules, Acceptance Criteria, and Recommendation already drafted by author. This review confirmed/refined rather than re-derived.
- **Sibling workstream** `tasks/backlog/feature-plan-smoke-gate-validation/README.md` — confirmed multi-layer defence pattern is established practice in this codebase. Validates Shape D's two-layer architecture and informs folder consolidation recommendation.
- **Sibling completed** `tasks/completed/2026-05/coach-validator-ac-id-matching/` (CVAC-001, CVAC-002) — confirmed validator-side AC-matching is settled, so Class C is no longer confounded by validator bugs.
- **Source-of-truth code reads**:
  - `guardkit/models/task_types.py` — confirmed enum + profile shape; sized FPTC-002 at 1h.
  - `guardkit/orchestrator/feature_loader.py` — confirmed validator extension point at `_validate_task_type_in_file`.
  - `installer/core/commands/feature-plan.md` lines 1290–1340 — confirmed plan-side `task_type` taxonomy and Task Type Assignment Rules table location.
- **Graphiti knowledge graph** — searched `architecture_decisions`, `guardkit__project_decisions`, `guardkit__task_outcomes`, `command_workflows`. No prior decision on `operator_handoff`. Closest related fact (uuid `47f3493b`): *"Tasks with the type 'task_type:review' may require verification work as part of their acceptance criteria"* — same shape of mismatch we're solving for here. No conflicting prior decisions.

## Decision Matrix (refined)

Refinement of the matrix in the task body, with quantitative cost columns:

| Criterion | Shape A | Shape B | Shape C | Shape D | Shape E |
|---|---|---|---|---|---|
| Solves headline incident pattern | ✓ | ✓ if tagged | ◐ if detected | ✓✓ | ◐ |
| Coarse vs granular | Coarse | Granular | N/A | Coarse | N/A |
| Subtask count | 3-4 | 5-6 | 2 | 7 (revised) | 2 |
| Effort estimate | ~6h | ~9h | ~3h | ~11h | ~3h |
| Cost-per-prevented-incident (FEAT-FD32 baseline: 110 SDK min + 3h debug = ~5h equivalent) | break-even at 2 prevented | break-even at 2 prevented | break-even at 1 prevented (if detection works) | break-even at 3 prevented | unsafe; backdoor risk |
| Two-layer defence | ✗ | ✗ | ✗ | ✓ | ✗ |
| Failure mode if missed | Same as today | Same as today | Same as today | Rare; both layers must miss | Backdoor: Player can claim everything as deferred |
| Friction at plan time | None | None | Medium (interactive prompt) | Medium (interactive prompt) | None |
| Implementation risk | Low | Medium | Low | Medium-low (proven pattern) | High (NLP intent detection in Coach) |
| **Recommended** | | | | **★ this review** | (rejected) |

Break-even reasoning: each prevented incident in this codebase costs ~5h equivalent
(FEAT-FD32 baseline: 110 minutes of SDK + ~3 hours of operator debugging). Shape D
breaks even at 3 prevented incidents over its lifetime. The pattern recurs on every
feature with operationally-flavoured ACs; given two such tasks in a single
study-tutor feature already, the trigger rate is well above the break-even point.

## Recommendations summary

1. **Adopt Shape D**.
2. **Consolidate folders**: `feature-plan-smoke-gate-validation/` → `feature-plan-defects/` with sub-feature folders for Classes A, B, C.
3. **Implement in 3 waves** as described in §AC-AUTM-03.
4. **Bias detector toward false positives** — they cost one operator confirmation; false negatives cost a turn-budget burn.
5. **Test detector against the two FEAT-FD32 reproducers** as a hard gate (both must be flagged).
6. **No retroactive labelling** of historical features.
7. **Documentation centralised** in a new `docs/guides/feature-plan-task-classification.md` cross-linked from CLAUDE.md and `feature-plan.md`.

## Out of scope (explicitly)

- Implementation of any of the FPTC-* tasks. This review's output is the decision and the task list; implementation lands via `/task-create` for each FPTC-* task and execution under the existing `/task-work` or `/feature-build` flows.
- Per-feature retroactive cleanup of operator-shaped tasks in study-tutor / forge / etc. The manual completions plus YAML provenance comments are sufficient.
- Changes to Coach validator AC matching. CVAC-001 and CVAC-002 are complete and orthogonal.
- The Class A and Class B subtasks (FPSG-001..005). They retain their IDs and effort; only the folder layout changes (this is FPTC-007's responsibility).

## Status

All six acceptance criteria satisfied:

- [x] **AC-AUTM-01** — Shape D selected with rationale; alternatives A/B/C/E explicitly addressed.
- [x] **AC-AUTM-02** — Detection rules drafted; both FEAT-FD32 reproducers verified as caught.
- [x] **AC-AUTM-03** — 7 follow-up tasks sized (~11h total), waved, prioritised; folder consolidation decided.
- [x] **AC-AUTM-04** — Backwards compatibility: no retroactive labelling needed.
- [x] **AC-AUTM-05** — Documentation update plan covers feature-plan.md, feature-complete.md, task_types.py, task-workflow.md, a new task-classification guide, and CLAUDE.md cross-ref.
- [x] **AC-AUTM-06** — This report.
