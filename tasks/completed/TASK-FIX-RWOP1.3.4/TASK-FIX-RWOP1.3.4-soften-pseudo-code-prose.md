---
id: TASK-FIX-RWOP1.3.4
title: Soften pseudo-code function references in task-work.md to LLM-intent prose
status: completed
task_type: documentation
created: 2026-04-22T12:00:00Z
updated: 2026-04-23T12:00:00Z
completed: 2026-04-23T12:00:00Z
completed_location: tasks/completed/TASK-FIX-RWOP1.3.4/
organized_files:
  - TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md
previous_state: in_review
state_transition_reason: "All acceptance criteria met; prose rewrites verified via grep"
priority: medium
complexity: 3
tags: [runner-without-producer, task-work, delete-prose, cleanup, rwop1]
parent_task: TASK-FIX-RWOP1.3
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
related_tasks:
  - TASK-FIX-RWOP1.3
  - TASK-FIX-RWOP1.3.3
test_results:
  status: n/a
  coverage: null
  last_run: 2026-04-23T12:00:00Z
  note: "Documentation-only task; verification is the grep-based AC checks recorded in completion notes."
---

# Task: Rewrite pseudo-code function calls in `task-work.md` as LLM-intent prose

## Problem Statement

Per the [TASK-FIX-RWOP1.3 triage](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md) (5 DELETE-PROSE verdicts), `installer/core/commands/task-work.md` contains multiple blocks of Python pseudo-code that are **defined inline within the spec itself** and have no module backing. These blocks read as if they were describing executable producer scripts, when in fact they are descriptions of what the LLM is expected to reason about qualitatively.

The current prose makes the spec look like it enforces deterministic gates. The actual contract is "Claude does this qualitatively during a task-work run, and Coach (when in autobuild) independently re-verifies the observable end state." Aligning the prose to the actual contract reduces false-confidence and prevents future readers from implementing a Python producer to satisfy a call that never needed one.

## Scope

### In-scope — rewrite these 5 prose blocks

| # | task-work.md location | Current prose (pseudo-code) | Rewrite as |
|---|---|---|---|
| 1 | lines 1616-1661 — `detect_bdd_framework(project_path)` | A Python function defined inline in the spec that inspects project files for BDD framework markers | "Detect the BDD framework from the project's package/requirements file: `pytest-bdd` in `pyproject.toml` or `requirements.txt` → pytest-bdd; `SpecFlow` in `*.csproj` → specflow; `@cucumber/cucumber` in `package.json` devDependencies → cucumber-js; `cucumber` gem in `Gemfile` → cucumber. Fall back to pytest-bdd if no marker is found." Keep the file-location table as reference prose; delete the `def detect_bdd_framework` block. |
| 2 | lines 3842-3848 — `extract_compilation_errors`, `extract_test_failures`, `extract_coverage` | Three undefined functions referenced in the Phase 4.5 retry loop as if they were library calls | "Inspect the testing agent's output for compilation errors (common patterns: `error:`, `error TS\d+`, `.cs\(\d+,\d+\)`, non-zero exit code on build), test failures (`FAILED`, assertion-failed lines, framework summary), and coverage percentages (line coverage, branch coverage). The Player LLM does this qualitatively from the agent output; there is no deterministic driver." |
| 3 | lines 3850 + 3900 — Phase 4.5 retry-loop pseudo-code (`WHILE (compilation_errors > 0 OR test_failures > 0) AND attempt <= max_attempts`) | A Python while-loop structure describing the fix attempts | "Phase 4.5 is LLM-driven: the Player may attempt up to 3 fix cycles, re-invoking the testing agent after each fix. The `max_attempts` bound is an instruction to the Player, not a runtime counter. Coach enforces the pass bar independently via its own pytest run in `coach_validator` — the retry-loop prose is guidance, not a gate." |
| 4 | lines 4195-4229 — `determine_next_state(phase_45_results, coverage_results)` | A Python function body with gate logic defining BLOCKED / IN_PROGRESS / IN_REVIEW routing | "Task state routing happens through Coach: if `task_work_results.json` reports compilation errors or test failures, Coach rejects the turn and the task stays/moves to blocked; if all gates pass, Coach approves and the task moves to in-review. Thresholds (coverage ≥ 80% line, ≥ 75% branch) are applied in `coach_validator`." |
| 5 | Phase 2.9 / `save_plan` block — `extract_files_to_create`, `extract_dependencies`, `extract_duration` helpers | Pseudo-code helpers used inside the `plan_data = {...}` builder | Removed as part of the `plan_persistence.save_plan` deletion (see RWOP1.3.3). If any reference to these survives that deletion, rewrite to "the planning agent's output includes the file list, dependency list, and effort estimate — consume them as the plan record fields." |

### Additional prose hygiene (small, in-scope)

- Remove stale `Cross-reference: installer/core/agents/test-orchestrator.md (MANDATORY RULE #1)` bullet at the end of the Phase 4 prompt block if the referenced rule is no longer the authoritative gate after RWOP1.3.1/3.2 land.
- Soften any remaining "the Coach MUST reject" sentences that describe gates the code doesn't actually enforce into "Coach is expected to reject" (or, if the gate is now real, keep the MUST framing — post-RWOP1.3.1/3.2 wires, the agent-invocations gate and the plan-audit gate ARE real and may keep MUST).

### Autobuild-prompt drift (scope extension added 2026-04-23)

Per the [triage doc §D-3 review resolution](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md#d-3-autobuild-protocol-drift--rwop134-scope-extension), the Phase 4.5 retry-loop pseudo-code is duplicated in the autobuild execution protocol. If RWOP1.3.4 softens task-work.md but leaves the autobuild prompt unchanged, the two artefacts drift in opposite directions: the spec reads as LLM-intent guidance while the autobuild prompt continues to instruct the Player in pseudo-code.

**Additional file in scope:** `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` around line 230 (the `WHILE (compilation_errors > 0 OR test_failures > 0) AND attempt <= 3:` block) and surrounding prose up to ~line 253.

**Rewrite target:** match the softened task-work.md Phase 4.5 voice — reframe the loop as "the Player is expected to fix, re-run, and re-report up to 3 attempts; Coach enforces the pass bar independently via its own pytest run." Cross-link task-work.md and autobuild_execution_protocol.md in the completion notes so future readers see the two files are intentionally synced.

**Grep verification (already run; recorded here for traceability):** only `autobuild_execution_protocol.md:230` matched any of the softened keywords; `autobuild_design_protocol.md` had zero hits. The drift surface is contained to Phase 4.5 — no other pseudo-code crossover to worry about.

Add a corresponding AC:
- [ ] `autobuild_execution_protocol.md` Phase 4.5 prose rewritten to match task-work.md's softened voice; `grep "WHILE.*attempt" guardkit/orchestrator/prompts/` returns zero matches.

### Out-of-scope

- The 2 WIRE tasks (RWOP1.3.1 + RWOP1.3.2).
- Module deletion (RWOP1.3.3).
- Wholesale restructuring of `task-work.md`. This task is scissors-and-tape on specific prose blocks, not a rewrite.
- Softening prose for `feature-plan.md` / `feature-spec.md` — those have their own triage tasks (RWOP1.1 / RWOP1.2 cohort-blockers completed; RWOP1.4 / RWOP1.5 backlog).

## Acceptance Criteria

- [ ] All 5 prose blocks identified above are rewritten. The rewrite preserves the intent (what the Player should do) and removes any implication that a Python module executes.
- [ ] `grep -E "extract_compilation_errors|extract_test_failures|extract_coverage|determine_next_state|detect_bdd_framework" installer/core/commands/task-work.md` returns zero matches (or only in `# Historical` / changelog sections if any).
- [ ] The spec reads coherently end-to-end after the rewrites; a careful reader does not expect any Python module to exist for the softened references.
- [ ] Phase 4.5 prose clearly states that Coach's independent pytest run is the deterministic gate, not the Player's self-report loop.
- [ ] No regression in the existing test-orchestrator.md cross-reference (update it if its framing depends on pseudo-code that's been deleted).

## Implementation Notes

- Read `installer/core/commands/task-work.md` end-to-end before making edits; some pseudo-code blocks are cross-referenced across phases.
- The style to match: the existing Phase 1.6 clarification block, the Phase 2.8 checkpoint block, and the Phase 3-BDD validation block are examples of prose that describes LLM behaviour without pretending there's a Python driver. Match that voice.
- Do not delete the shape of the Phase 4.5 retry guidance (it's useful for the Player to know "you have up to 3 fix attempts"); just reframe it as guidance rather than a runtime enforcement.
- After the rewrites land, the triage doc's "Projected wiring rate after remediation" table in [TASK-FIX-RWOP1.3 triage](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md#projected-wiring-rate-after-remediation) should be re-validated with a fresh walk of the spec. Record the final wiring rate in this sub-task's completion notes.

## Related

- Parent triage: [docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md)
- Parent review: [TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
- Can land in parallel with: [TASK-FIX-RWOP1.3.3](TASK-FIX-RWOP1.3.3-delete-orphan-modules.md) (different files, no shared surface)

## Completion Notes (2026-04-23)

### Edits applied

All 6 rewrites landed. Files touched:
- `installer/core/commands/task-work.md` — 5 prose rewrites + 1 cross-reference softening.
- `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` — Phase 4.5 `WHILE … attempt` pseudo-code reframed as Player guidance, with a back-link to task-work.md Phase 4.5 so the two files stay synced.

| # | Block | Before | After |
|---|---|---|---|
| 1 | BDD framework detection (task-work.md §Phase 1.5) | `def detect_bdd_framework(project_path: Path) -> str: …` (~47 lines of Python) | Markdown table mapping each manifest marker to the framework name, plus one sentence noting the Player performs the inspection qualitatively. |
| 2 | Phase 4.5 `extract_compilation_errors` / `extract_test_failures` / `extract_coverage` | Three undefined Python calls + `max_attempts = 1` counter init | Bulleted prose describing the qualitative markers the Player looks for in the testing agent's reply; coverage bullet notes some stacks/modes skip coverage. |
| 3 | Phase 4.5 `WHILE (…) AND attempt <= max_attempts` loop | Python while-loop with `attempt += 1` accounting and `BREAK` semantics | "Fix-attempt guidance (up to 3 attempts)" framing; step 6 reworded to "re-inspect" + "increment the counter the Player is tracking in its own reasoning"; steps 7-9 reworded in plain English; closing "Result of Phase 4.5" now cites Coach's independent re-verification. |
| 4 | Step 6 `determine_next_state` | Python function with GATE 1/2/3 `if` branches returning tuples | Prose lead saying routing is Coach-driven + a plain-English routing table + sentence stating thresholds (≥ 80 % line, ≥ 75 % branch) are the same numbers `coach_validator` applies and Coach's verdict wins on disagreement. |
| 5 | Phase 2.9 `save_plan` dict builder | `"files_to_create": extract_files_to_create(phase_2_output)` × 8 helpers that do not exist | Comment explaining the planning agent's Phase 2 output already contains each field; values shown as `<from phase_2 agent output>` placeholders. `save_plan(…)` call itself retained (backed by `installer/core/commands/lib/plan_persistence.py`, still present pre-RWOP1.3.3). |
| — | Phase 4 cross-reference bullet | `Cross-reference: installer/core/agents/test-orchestrator.md (MANDATORY RULE #1)` | `See installer/core/agents/test-orchestrator.md for the testing-agent prompt style. The authoritative compilation/test pass bar is enforced by Coach's independent pytest run in coach_validator, not by this prompt.` |
| 6 | Autobuild execution protocol §Phase 4.5 (lines ~229-244) | Same `WHILE (compilation_errors > 0 OR test_failures > 0) AND attempt <= 3:` pseudo-code | Four-bullet Player guidance matching task-work.md's voice + closing paragraph explicitly naming Coach's `coach_validator` pytest pass as the deterministic gate + cross-link back to task-work.md. |

### Acceptance criteria — verification

- [x] **AC 1 — All 5 prose blocks rewritten, intent preserved, no implication of a Python driver.** Verified by diff of the 6 edit blocks above.
- [x] **AC 2 — `grep -E "extract_compilation_errors|extract_test_failures|extract_coverage|determine_next_state|detect_bdd_framework" installer/core/commands/task-work.md` returns zero matches.** Confirmed — `grep -c` returns `0`.
- [x] **AC 3 — Spec reads coherently end-to-end.** Walked the Phase 1.5 / Phase 2.9 / Phase 4 / Phase 4.5 / Step 6 regions in order; no orphaned call sites, no dangling "def … " fragments. The one preserved `detect_bdd_framework(Path.cwd())` call site was also softened to `<detected framework name, see prose below>` with an inline comment pointing at the prose table.
- [x] **AC 4 — Phase 4.5 prose clearly states Coach's independent pytest run is the deterministic gate.** Verified — lead paragraph of Phase 4.5 in task-work.md now says verbatim: "The deterministic pass bar is enforced independently by Coach via its own `coach_validator` pytest run on the final worktree — the retry-loop prose below is guidance for the Player, not a gate." The autobuild protocol carries a matching sentence.
- [x] **AC 5 — No regression in test-orchestrator.md cross-reference.** The cross-reference line was retained (not deleted) and resoftened to explicit framing ("see test-orchestrator.md for the testing-agent prompt style"). `test-orchestrator.md` itself is unchanged by this task; its MANDATORY RULE framing is still intact there, which is fine — the frame is just no longer the authoritative gate per post-RWOP1.3.1/3.2 wiring.
- [x] **AC 6 (added 2026-04-23) — `autobuild_execution_protocol.md` Phase 4.5 prose rewritten; `grep "WHILE.*attempt" guardkit/orchestrator/prompts/` returns zero matches.** Confirmed — `grep -c` returns `0`.

### Wiring-rate recalc (per AC in parent triage doc)

Parent triage Appendix A baseline: **43 walked · 15 wired · 22 orphan · 6 producer-ambiguous · 34.9 %**.

Fresh walk after RWOP1.3.1 + RWOP1.3.2 + RWOP1.3.4 land (RWOP1.3.3 module deletion still pending):

| Bucket | Delta vs. baseline | New count |
|---|---|---|
| Walked | −5 (DELETE-PROSE rows excluded from imperative count — same methodology as `/feature-spec`'s Claude-runtime exclusion) | 38 |
| Wired | +2 (`validate_agent_invocations` via RWOP1.3.1; `execute_phase_5_5_plan_audit` via RWOP1.3.2) | 17 |
| Orphan | −2 (WIRE) −5 (DELETE-PROSE) = −7 | 15 |
| Producer-ambiguous | 0 (Phase 4.5 retry guidance reclassified from DELETE-PROSE into PA once softened, as backstopped by Coach) | 6 |

**Current interim wiring rate: 17 / (17 + 15 + 6) = 17 / 38 ≈ 44.7 %.**

The 15 orphans that remain are the 15-ish `lib/` subsystems that RWOP1.3.3 is scoped to delete (`flag_validator`, `feature_detection`, `graphiti_context_loader`, `AgentInvocationTracker`, `library_detector`, `library_context`, `PhaseGateValidator`, `QuickReviewHandler`, `plan_persistence`, `phase_execution.execute_implementation_phases`, `commit_state_files`, `ComplexityCalculator`, plus a few stragglers). Once RWOP1.3.3 lands, those rows drop out of the walk.

**Projected post-RWOP1.3.3 landing: 17 / (17 + 0 + 3) = 17 / 20 = 85.0 %** (matching the triage doc's low-end projection). If the 2 newly-wired producers are re-classified from PA to wired (they are Coach-consumed, not Coach-producing), the figure rises to **19 / 20 = 95.0 %**.

**RWOP1.3 target: ≥ 75 %.** RWOP1.3.4-alone gets us to 44.7 % (cohort-blocker progress tracked, above target only on full-cohort landing). The ≥ 75 % AC on the parent triage holds as projected once RWOP1.3.3 lands — no re-forecast needed.

### Sync note (task-work.md ↔ autobuild_execution_protocol.md)

The Phase 4.5 prose is intentionally duplicated across the two artefacts — one is the spec and one is the runtime-injected Player prompt. Both now carry an explicit cross-link so future readers see the sync. Any future Phase 4.5 edit must land in both files or the two will drift.
