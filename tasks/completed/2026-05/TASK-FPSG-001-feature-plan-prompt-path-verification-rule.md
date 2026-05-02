---
id: TASK-FPSG-001
title: "/feature-plan.md: add 'Path verification — REQUIRED' rule before smoke-gate authoring (L3a)"
status: completed
created: 2026-05-02T13:30:00Z
updated: 2026-05-02T00:00:00Z
completed: 2026-05-02T00:00:00Z
priority: high
task_type: enhancement
implementation_mode: direct
tags:
  - feature-plan
  - prompt-engineering
  - smoke-gate
  - cross-repo-followup
  - feature-plan-smoke-gate-validation
complexity: 2
estimated_minutes: 60
parent_review: appmilla_github/forge/TASK-REV-DEA8
parent_feature: feature-plan-smoke-gate-validation
wave: 1
dependencies: []
refinement_count: 1
last_refinement: 2026-05-02T00:00:00Z
---

# Task: /feature-plan.md prompt — require path verification before authoring smoke gates

## Description

The `/feature-plan` Plan agent currently invents pytest paths in §6
"Smoke gates" of the produced plan and in per-task implementation
notes, without any requirement to verify those paths against the
target repo's actual `tests/` tree. The
`installer/core/commands/feature-plan.md` prompt explicitly forbids
auto-generation of gate commands ("Authors know their stack") but
does not require path verification by the agent.

This task adds a positive companion rule.

**Real-world incident**: forge FEAT-DEA8 Run 2, 2026-05-02 — the Plan
agent invented `tests/cli/` (a guardkit-shaped path) for a forge
feature; pytest exited 4; 10/11 tasks blocked. Full diagnosis:
[TASK-REV-DEA8 review report](../../../../forge/.claude/reviews/TASK-REV-DEA8-review-report.md).

## Acceptance Criteria

- [ ] **Edit applied** to
      `installer/core/commands/feature-plan.md`. A new "Path
      verification — REQUIRED" subsection is inserted **above** the
      existing "Non-goals" subsection at lines 2311-2321 (the smoke
      gates schema reference section).
- [ ] **Rule content** — the new subsection MUST:
      - Require the agent to verify any path written inside
        `smoke_gates.command` (positional pytest argv) and any test
        file path referenced in per-task notes against the target
        repo via Read or Bash `ls tests/` before writing the YAML.
      - Forbid copying `tests/<group>/` paths from another repo's
        template (this is the exact failure mode from TASK-REV-DEA8 —
        guardkit-shaped `tests/cli/` pasted into a forge-shaped spec).
      - State that smoke-gate paths must reference test **roots**
        (existing directories), not specific files-to-be-created.
      - Reference TASK-REV-DEA8 by name as the prior incident.
- [ ] **Contract test** added at
      `tests/unit/commands/test_feature_plan_prompts.py` (or extends
      an existing test there) asserting the prompt file contains the
      new subsection heading and a verbatim "MUST verify" / "MUST be
      verified" string.
- [ ] **Schema reference unchanged** — the canonical smoke_gates
      schema example block (lines 2278-2288) remains exactly as-is;
      this task only adds a new subsection.
- [ ] **No re-architecture** — does not change the "do not
      auto-generate" non-goal. Authors still author; this rule only
      requires they verify what they author.

## Implementation Notes

- The "Non-goals" subsection currently starts:
  > **Non-goals (do NOT do any of these):**
  > - Do not auto-generate smoke-gate commands. ...

  Insert the new subsection immediately above it.

- Suggested heading: `**Path verification — REQUIRED before authoring.**`

- Include a concrete example of the failure mode:
  > Example failure (TASK-REV-DEA8): the agent wrote
  > `pytest tests/cli tests/forge -x -k "..."` for a forge feature.
  > `tests/cli/` does not exist in forge; pytest exited 4; the entire
  > 11-task feature run was blocked after Wave 1.

## Test Requirements

- [ ] Contract test passes: prompt file contains the new subsection.
- [ ] No regression in existing `test_feature_plan_prompts.py` /
      `test_smoke_gates_nudge.py` tests.

## Files

- `installer/core/commands/feature-plan.md` — primary edit
- `tests/unit/commands/test_feature_plan_prompts.py` — contract test
  (create if absent)

## Refinement History

### Refinement 1 — 2026-05-02
**Description**: Extend the new subsection with an `after_wave`
temporal-sequencing rule (Class B) alongside the original spatial
path-verification rule (Class A). Originally only Class A was in
scope; reviewer flagged Class B as a sibling failure mode worth
pinning in the same prompt section rather than landing as a
follow-up task.

**Outcome**: SUCCESS — task remains in `in_review`.

**Changes**:
- Added `**after_wave temporal-sequencing — REQUIRED.**` paragraph
  inside the `Path verification — REQUIRED` subsection of
  `installer/core/commands/feature-plan.md`. Cites the study-tutor
  FEAT-FD32 Run 2 chicken-and-egg incident (TASK-GR-SMOK,
  AC-SMOK-01) as prior art.
- Updated the closing "positive companion" paragraph to call out
  both spatial and temporal verification.
- Extended `tests/unit/commands/test_feature_plan_prompts.py` with
  4 new assertions: temporal-sequencing heading present,
  `must be ≥ that creation task's wave` imperative present,
  FEAT-FD32 / TASK-GR-SMOK / AC-SMOK-01 references present,
  and temporal heading sits between the path-verification heading
  and the smoke_gates "Non-goals" anchor.

**Tests**: 35/35 passing
(9 `test_feature_plan_prompts.py` + 26 `test_smoke_gates_nudge.py`).

**Files modified**:
- `installer/core/commands/feature-plan.md`
- `tests/unit/commands/test_feature_plan_prompts.py`
