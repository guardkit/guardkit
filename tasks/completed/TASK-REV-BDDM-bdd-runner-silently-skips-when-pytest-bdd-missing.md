---
id: TASK-REV-BDDM
title: 'Review: BDD runner silently skips tagged scenarios when pytest-bdd is missing from project env'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
previous_state: review_complete
state_transition_reason: 'User selected [I]mplement after revision-2 regression analysis. 11 follow-up tasks created in tasks/backlog/bdd-runner-silent-bypass-fix/ across 3 waves.'
priority: high
complexity: 0
task_type: review
review_mode: architectural
review_depth: comprehensive
tags: [bdd, autobuild, quality-gates, silent-bypass, env-config]
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: comprehensive
  score: 58
  findings_count: 9
  recommendations_count: 7
  decision: refactor
  report_path: .claude/reviews/TASK-REV-BDDM-review-report.md
  completed_at: '2026-04-25T00:00:00Z'
  revision: 2
  revision_reason: 'User requested regression-safety re-analysis. Added: full call-graph trace, 4 C4 diagrams, per-test impact matrix (50 tests inventoried, 1 affected), 7 regression-vector stress-tests. R3 upgraded SHOULD_FIX → MUST_FIX as cost-protection invariant.'
---

# Review: BDD runner silently skips tagged scenarios when pytest-bdd is missing from project env

## Symptom

AutoBuild logs from the **jarvis** project (run on this MacBook) show repeated INFO lines, one per task per turn:

```
INFO:guardkit.orchestrator.quality_gates.bdd_runner:BDD runner: pytest-bdd not importable; skipping N candidate feature file(s) for TASK-J002-014.
```

Same pattern in:
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J002-history.md` (~10+ occurrences across J002-008..019)
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J003-history-cancelled.md` (~10+ occurrences across J003-007..022)

The same code path running on the **GB10** for the **forge** project does NOT log this. Logs checked:
- `forge/docs/history/autobuild-FEAT-FORGE-003-history.md`
- `forge/docs/history/autobuild-FEAT-FORGE-004-history.md`
- `forge/docs/history/autobuild-FEAT-FORGE-005-history.md`

## Root cause (provisional, to be confirmed in review)

`forge/pyproject.toml` declares `pytest-bdd>=8.1,<9` as a project dependency, so the worktree venv has it. `jarvis/pyproject.toml` does not declare it.

When the jarvis worktree env lacks `pytest_bdd`, [bdd_runner.has_pytest_bdd()](guardkit/orchestrator/quality_gates/bdd_runner.py#L172-L193) returns False, and [run_bdd_for_task()](guardkit/orchestrator/quality_gates/bdd_runner.py#L466-L473) returns `None` after logging an INFO message. The Coach receives no BDD result and approves on `scenarios_failed == 0` (vacuously true).

## Why this matters — silent BDD bypass

This is the same *class* of defect as TASK-FIX-F584 (synthetic-failure surfacing for pytest runner errors), but for a different cause:

| Cause                                     | bdd_runner behaviour today                  | Coach effect                       |
|-------------------------------------------|---------------------------------------------|------------------------------------|
| pytest exits non-zero with no testcases   | Synthesises FailureDetail (TASK-FIX-F584)   | ✅ Coach blocks                     |
| **pytest-bdd not importable in env**      | **INFO log + return None**                  | **❌ Coach silently approves**      |

The jarvis logs prove this is not a hypothetical: every J002 / J003 task with a `@task:<TASK-ID>` tagged feature file ran the autobuild loop with **no BDD verification at all**, and Coach saw nothing wrong because the runner had never produced a result.

The bdd_runner module docstring is explicit that the three-state model exists precisely to prevent BDD scaffolding looking like "BDD broke the build" — but it does not address the inverse failure mode (BDD silently doing nothing when the runner is missing).

## Why the divergence between jarvis and forge

- **forge** is a Python project authored after `/feature-spec` BDD became standard — `pytest-bdd` was added to its pyproject as part of project setup, so the worktree venv installed it.
- **jarvis** is older and/or used a project template that does not include `pytest-bdd`. The project picked up `/feature-spec` BDD scaffolding (feature files exist with `@task` tags) but never gained the runtime dependency.
- This is an env-divergence problem, NOT a per-machine (MacBook vs GB10) problem. The "I see it on MacBook but not GB10" framing is a red herring — the difference is the project, not the host.

## Open questions for the review

1. **Severity escalation** — Should `pytest_bdd not importable` AND `find_feature_files_with_tag` returning a non-empty list be treated as a **runner error** (synthetic FailureDetail, Coach blocks) rather than a silent skip? The conditions are isomorphic to TASK-FIX-F584's "tests exist but cannot run" case.

2. **Logging level** — At minimum, should this log be WARNING (not INFO)? Currently it's invisible at default verbosity. The forge logs prove it never fires when the env is correct, so promoting it would not be noisy in healthy projects.

3. **/feature-spec contract** — Does `/feature-spec` (which scaffolds the `.feature` files) take any responsibility for ensuring the project declares `pytest-bdd`? If a project gets feature files scaffolded but the pyproject is never updated, the silent-bypass is structural, not accidental.

4. **AutoBuild env preflight** — Should `guardkit autobuild task` perform a preflight that detects tagged feature files and warns / fails fast if `pytest_bdd` is not importable in the worktree venv, before burning Player turns?

5. **Documentation gap** — The bdd_runner module docstring says BDD is "by artefact presence (a `features/*.feature` file containing the task's `@task:<TASK-ID>` tag)". It does not document the additional implicit prereq that `pytest_bdd` must be installed. Should the BDD workflow guide call this out?

6. **Backfill question** — Should jarvis's pyproject add `pytest-bdd` and FEAT-J002 / FEAT-J003 be re-run, or is the BDD verification gap acceptable for those features in retrospect?

7. **Scope of the silent-skip pattern** — Are there other quality gates (security scan, coverage tooling, type-checker) that follow the same "if tool missing, return None, Coach approves" shape? If so, this review should generalise to a meta-rule about gate-tool absence.

## Proposed review scope

**Mode:** architectural · **Depth:** comprehensive

Investigate:
- a) Does the silent-bypass risk warrant a code change in `bdd_runner.run_bdd_for_task()`? (Likely yes — make "tagged scenarios exist + pytest-bdd absent" a synthetic FailureDetail, mirroring TASK-FIX-F584.)
- b) Should `/feature-spec` modify the project's pyproject.toml / requirements to add `pytest-bdd` when scaffolding the first `.feature` file?
- c) Should AutoBuild perform a preflight env check?
- d) Should this become a Graphiti `architecture_decisions` rule ("quality-gate tool absence must not silently skip — synthesise a failure"), generalising beyond BDD?
- e) Does jarvis (and any other downstream projects) need a backfill task to add `pytest-bdd` and re-verify the affected FEAT-J002 / FEAT-J003 tasks?

## Acceptance criteria for the review

- [ ] Confirm the root cause (jarvis pyproject lacks `pytest-bdd`; forge has it)
- [ ] Decide whether `bdd_runner` should surface a synthetic FailureDetail in this case (yes/no with rationale)
- [ ] Decide whether `/feature-spec` should auto-update pyproject (yes/no with rationale)
- [ ] Decide whether AutoBuild needs a preflight env check (yes/no with rationale)
- [ ] Identify any other quality gates with the same silent-skip pattern
- [ ] If any of the above are "yes", produce concrete follow-up TASK recommendations
- [ ] Update the BDD workflow guide to call out the `pytest-bdd` install prereq
- [ ] Decide on jarvis backfill (re-run affected features, or accept the gap)

## Evidence files

- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J002-history.md` — multiple "pytest-bdd not importable" lines (search: `BDD runner: pytest-bdd not importable`)
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J003-history-cancelled.md` — same pattern
- `/Users/richardwoollcott/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-FORGE-003-history.md` — clean (no occurrences)
- `/Users/richardwoollcott/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-FORGE-004-history.md` — clean
- `/Users/richardwoollcott/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-FORGE-005-history.md` — clean
- [bdd_runner.py:172-193](guardkit/orchestrator/quality_gates/bdd_runner.py#L172-L193) — `has_pytest_bdd()`
- [bdd_runner.py:466-473](guardkit/orchestrator/quality_gates/bdd_runner.py#L466-L473) — silent-skip site
- [bdd_runner.py:507-530](guardkit/orchestrator/quality_gates/bdd_runner.py#L507-L530) — TASK-FIX-F584 synthetic-failure precedent (the pattern this review may extend)
- [agent_invoker.py:5509-5512](guardkit/orchestrator/agent_invoker.py#L5509-L5512) — caller in autobuild loop

## Related prior art

- **TASK-FIX-F584** — Pytest runner-error surfacing as synthetic FailureDetail. Same meta-shape; this review proposes extending the same protection to "runner not installed".
- **bdd_runner.py module docstring** — Documents the three-state pending/passed/failed model and explicitly motivates *not* collapsing pending into failed. Silent-bypass on missing runner is the inverse asymmetry not yet addressed.

## Next step

`/task-review TASK-REV-BDDM --mode=architectural --depth=comprehensive`
