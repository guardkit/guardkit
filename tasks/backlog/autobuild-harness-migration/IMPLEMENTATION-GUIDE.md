# Implementation Guide: AutoBuild Harness Migration

> Companion to [README.md](./README.md) and the parent review's [implementation guide](../../../.claude/reviews/TASK-REV-HMIG-implementation-guide.md).
> **Scope of this file**: the cross-repo execution plan and the guardkit-side wave breakdown. For the guardkitfactory-side, see `~/Projects/appmilla_github/guardkitfactory/tasks/backlog/autobuild-harness-migration/`.

## Cross-repo execution overview

| Wave | guardkit tasks | guardkitfactory tasks | Composite falsifier |
|---|---|---|---|
| **Wave 1** (D-27 → D-20) | TASK-HMIG-001A | TASK-HMIG-000R, TASK-HMIG-001B, TASK-HMIG-002R | Cross-repo import smoke: `pip install -e ../guardkitfactory` in guardkit/.venv resolves, `from guardkitfactory import LangGraphHarness` works, agent.invoke against a fixture worktree writes the expected `player_turn_1.json` |
| **Wave 2** (D-20 → D-13) | TASK-HMIG-006, **TASK-HMIG-008R** *(Revision 3)* | TASK-HMIG-007 | Composite: (1) an FFC3-style state-bridge move fixture run under `GUARDKIT_HARNESS=langgraph` produces the same outcome as the post-fix SDK — LLM Coach evaluates 16 ACs, no short-circuit; (2) a zero-cardinality-BDD-oracle fixture (scenarios_attempted=0) produces `feedback` not `approve` under the new LLM Coach prompt; (3) `GUARDKIT_COACH_LEGACY=1` reactivates the legacy deterministic Coach path as emergency revert |
| **Wave 3** (D-13 → D-7) | TASK-HMIG-009, TASK-HMIG-010 | — | Aggregate first-pass-success rate for LangGraph across 9 canary runs + 1 feature run ≥75% (central recommendation falsifier from review §11) |
| **Wave 4** (D-7 → D-0) | (operational: flip `GUARDKIT_HARNESS` default; cutover; canary observation) | — | No regression vs Wave 3 baseline during D-2 → D-0 |

## Parallelism notes

- Wave 1's three guardkitfactory tasks (000R + 001B + 002R) can run sequentially in one Conductor workspace OR split: 000R first, then 001B + 002R in parallel.
- TASK-HMIG-001A (guardkit-side ABC) is independent of guardkitfactory work and can start immediately.
- Wave 2's TASK-HMIG-006 depends on both TASK-HMIG-001A (guardkit ABC) AND TASK-HMIG-001B (guardkitfactory LangGraphHarness) being complete. **TASK-HMIG-008R** *(Revision 3)* depends on TASK-HMIG-006 AND TASK-HMIG-007 — it needs both the harness dispatch path AND the BDD plugin interface in place so the CoachEvidenceBundle can carry structured BDD output and the LLM Coach can be routed through guardkitfactory's LangGraphHarness.
- Wave 2's TASK-HMIG-007 (guardkitfactory BDD plugin) is independent of guardkit-side Wave 2 work.

## Acceptance contract

Each task in this folder includes:

- An `id`, `title`, `wave`, `parallel_group`, `effort_hours`, `depends_on` in YAML frontmatter
- A `falsifier` field with the test that decides task completion
- A `cross_repo` field listing the files touched in the other repo (if applicable)
- Acceptance criteria as a `[ ]` checklist
- A links section pointing to the relevant review section(s)

## Reading order for new contributors

1. [README.md](./README.md) — what / why
2. This file — how (waves + parallelism)
3. [`.claude/reviews/TASK-REV-HMIG-review-report.md`](../../../.claude/reviews/TASK-REV-HMIG-review-report.md) — full architectural rationale + 11 decision points + 8 failure patterns
4. Individual task files in this folder + the guardkitfactory mirror

## Operator handoff

When starting a task with `/task-work TASK-HMIG-XXX`:

- For guardkit-side tasks (001A, 006, 008, 009, 010): run from `~/Projects/appmilla_github/guardkit/`.
- For guardkitfactory-side tasks (000R, 001B, 002R, 007): run from `~/Projects/appmilla_github/guardkitfactory/`.
- For tasks that touch both repos (001A pairs with 001B; 006 imports from guardkitfactory): ensure both worktrees are in sync; if using Conductor, pin both to the same migration branch convention.
