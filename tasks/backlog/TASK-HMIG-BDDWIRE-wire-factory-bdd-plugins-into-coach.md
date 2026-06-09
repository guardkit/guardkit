---
id: TASK-HMIG-BDDWIRE
title: Wire the guardkitfactory BDD plugin subsystem into the autobuild Coach evidence path
status: backlog
task_type: feature
created: 2026-06-09T00:00:00Z
updated: 2026-06-09T00:00:00Z
priority: medium
complexity: 6
parent_task: TASK-HMIG-007
related: [TASK-HMIG-007, TASK-HMIG-011, TASK-ARCH-COACHSPLIT]
implementation_mode: task-work
---

# Task: Wire the factory BDD plugin subsystem into the Coach

## Why this task exists

`guardkitfactory/src/guardkitfactory/bdd/` (TASK-HMIG-007) is a **complete,
tested, multi-stack BDD-oracle plugin subsystem** that **nothing in the
orchestrator consumes**:

- `BDDPlugin` ABC + `BDDRunResult` shared contract (`plugin.py`)
- contract-gated `loader.py` — a plugin cannot `register` unless its C1–C6
  `contract_tests` pass (the §5 failure-pattern guards from TASK-REV-HMIG,
  enforced in the type system)
- three stacks: `pytest_bdd_plugin.py` (Python, 630 lines, JUnit-XML
  parse, per-task marker filter, dep-probe `discover()`),
  `reqnroll_plugin.py` (.NET), `cucumber_js_plugin.py` (JS)
- 42 tests (loader + contracts + end-to-end)

A grep of `guardkit/` for `guardkitfactory.bdd` / `BDDPlugin` /
`BDDRunResult` returns **zero hits**. The Coach's BDD evidence today comes
from the **legacy** `guardkit/orchestrator/quality_gates/bdd_runner.py` plus
the Player-reported `task_work_results['bdd_results']` (the
`scenarios_failed > 0` gate at `coach_validator.py:1617`, feeding
`bundle.bdd`). Consequence: `/feature-spec` Gherkin is verified **only on
Python**; the **.NET (reqnroll) and JS (cucumber-js)** verification exists
in code but is **unreachable from a run**.

So: the component is done, the integration is missing. This task closes that
gap — the factory plugins are the intended replacement for the legacy
`bdd_runner` under the harness migration (staged with the LangGraph cutover
TASK-HMIG-011, but not switched on).

## The design

Replace (or front) the legacy BDD oracle with the factory plugin discovery
inside the Coach evidence path:

- In `CoachValidator` / `coach_evidence.py`, where `bundle.bdd` is
  populated and `_check_bdd_results` runs, **discover the plugin for the
  detected stack** via `guardkitfactory.bdd.discover(stack_profile)` and
  invoke it to get a `BDDRunResult`, mapping that into the existing
  `bundle.bdd` shape (`scenarios_attempted` / `scenarios_failed` /
  `scenarios_passed` / failures / feature_files).
- **Preserve** the existing contracts: the per-task glue naming
  (`.claude/rules/bdd-per-task-glue.md`, the `GUARDKIT_BDD_TASK_ID` env +
  the per-task `test_<slug>__<TASK-ID>.py` lookup), the absence-of-failure
  guard (`scenarios_attempted == 0` ⇒ ABSENT SIGNAL, not pass — Pattern-2 of
  `.claude/rules/absence-of-failure-is-not-success.md`), and the
  `scenarios_failed > 0` rejection gate.
- guardkit already depends on guardkitfactory (the harness import), so the
  cross-repo consume is structurally available; respect
  `.claude/rules/namespace-hygiene.md` for the import.

## Acceptance criteria

- [ ] **AC-1**: The Coach evidence path discovers and invokes the
  `guardkitfactory.bdd` plugin for the detected stack and maps its
  `BDDRunResult` into `bundle.bdd` — verified end-to-end on a Python
  (pytest-bdd) project.
- [ ] **AC-2 (multi-stack reachability)**: a .NET project routes to
  `ReqnrollPlugin` and a JS project to `CucumberJSPlugin` — the paths that
  are currently dead code become reachable. Tests assert plugin selection
  per stack profile.
- [ ] **AC-3 (absence-of-failure preserved)**: `scenarios_attempted == 0`
  still surfaces as ABSENT SIGNAL (feedback), never a silent pass; the
  zero-cardinality guard in the Coach prompt still fires.
- [ ] **AC-4 (per-task glue contract preserved)**: the
  `GUARDKIT_BDD_TASK_ID` per-task lookup + the legacy `test_<slug>.py`
  fallback continue to work (no race regression — parent rule
  `bdd-per-task-glue.md`).
- [ ] **AC-5**: the legacy `bdd_runner.py` is either removed or demoted to
  an explicit fallback with a single documented switch; no two oracles
  silently disagree.
- [ ] **AC-6**: integration tests covering plugin discovery, the
  `BDDRunResult → bundle.bdd` mapping, and the `scenarios_failed > 0`
  rejection gate through the Coach.

## Notes / sequencing

- Coordinate with **TASK-HMIG-011** (LangGraph cutover) — this is part of
  the same migration; ideally land before or with the cutover so the new
  default harness uses the new BDD oracle.
- Cross-repo change (guardkit consumes guardkitfactory.bdd); the factory
  subsystem is already contract-gated, so wiring risk is mostly in the
  discovery + mapping + preserving the per-task glue + absence-of-failure
  semantics, not in the plugins themselves.
- Surfaced while reviewing the BDD-verification status against
  `/feature-spec` Gherkin generation (2026-06-09).
