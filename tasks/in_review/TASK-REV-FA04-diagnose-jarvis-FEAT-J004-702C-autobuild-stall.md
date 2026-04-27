---
id: TASK-REV-FA04
title: Diagnose Jarvis FEAT-J004-702C autobuild unrecoverable_stall
status: review_complete
task_type: review
review_mode: diagnostic
review_depth: comprehensive
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
priority: high
tags: [autobuild, review, diagnostic, coach, environment-bootstrap, stall-detection]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: diagnostic
  depth: comprehensive
  revision: 2
  findings_count: 11
  recommendations_count: 7
  primary_cause: "Trapdoor: declarative task + task-work mode + broken bootstrap (Python 3.14 vs Jarvis-only requires-python='>=3.12,<3.13') + a regression test that imports jarvis. Bootstrap has been silently broken on Mac for ALL Jarvis runs since 3.14 became default; J002 survived via direct mode."
  contributing_causes:
    - "bootstrap_failure_mode defaults to 'warn' (silent continue past requires-python mismatch)"
    - "EnvironmentBootstrapper has no interpreter-discovery path for requires-python mismatches (PEP668 path exists but is irrelevant)"
    - "Coach falls back to sys.executable (3.14) when bootstrap venv_python is None"
    - "Coach has no conditional-approval branch for infrastructure/ambiguous + all-gates-passed"
    - "Feedback-stall detector emits misleading 'Review task_type classification' hint"
    - "Phase-3 specialist advisory fires on declarative tasks where no specialist is meaningful"
    - "Jarvis is the only sibling LangChain DeepAgents project with a tight Python pin (every other uses >=3.11); pin rationale (sibling nats-core resolution) is six months old and worth re-evaluating"
  report_path: .claude/reviews/TASK-REV-FA04-report.md
---

# Diagnose Jarvis FEAT-J004-702C autobuild unrecoverable_stall

## Context

`guardkit autobuild feature FEAT-J004-702C --verbose --max-turns 30` against the
Jarvis repo terminated with `UNRECOVERABLE_STALL` after Wave 1 of 7. Three of four
Wave-1 tasks succeeded in a single turn; **TASK-J004-004** (declarative Pydantic
routing-history schema) ran 3 Player+Coach turns producing identical Coach feedback
(signature `9c6e2dee`) with 0 criteria passing, then was killed by the feedback-stall
detector.

AutoBuild is otherwise healthy:

- Forge `docs/history/` contains multiple successful runs (FEAT-FORGE-001/003/004/005,
  FEAT-8D10, FEAT-CBDE)
- Jarvis FEAT-J002 succeeded
- This is an isolated, environment- and task-classification-correlated failure

**Source artefacts (read these first):**

- Failing run history: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J004-702C-history.md`
- Coach decision JSON (turn 1): `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-J004-702C/.guardkit/autobuild/TASK-J004-004/coach_turn_1.json`
- Player report: `.../TASK-J004-004/player_turn_*.json` and `task_work_results.json`
- Comparison: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J002-history.md` (success on same repo)
- Comparison: `/Users/richardwoollcott/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-FORGE-005-history-after-bdd-fixes.md` (success on different repo)

## Preliminary Evidence (do not stop here — verify and look beyond)

1. **Environment bootstrap silently continued after fatal mismatch.** Bootstrap log:

   ```
   WARNING: Python 3.14.2 does not satisfy requires-python='>=3.12,<3.13' for ...pyproject.toml
   ERROR: Package 'jarvis' requires a different Python: 3.14.2 not in '<3.13,>=3.12'
   ⚠ Environment bootstrap partial: 0/1 succeeded
   ```

   Orchestrator proceeded into Wave execution despite zero successful installs.

2. **Coach gate/independent-test contradiction.** From `coach_turn_1.json`:

   ```
   quality_gates.all_gates_passed = true        (tests=True, coverage=True, arch=True, audit=True)
   independent_tests.tests_passed = false
     test_output: "AssertionError: `import jarvis` regressed under the Phase 2 pins."
                  "1 failed, 124 passed" — failure is "import jarvis" (no editable install)
   failure_classification = infrastructure
   failure_confidence = ambiguous
   decision = feedback   ← issue category includes a must_fix entry, but...
   ```

   Resulting feedback string is the same advisory ("2 of 3 expected agent invocations,
   missing phases 3") plus an infrastructure must-fix note. Player has no actionable
   path: it cannot fix `import jarvis` (the environment is broken), and it cannot
   summon the missing Phase-3 specialist on a `declarative` task. Both turns 2 and 3
   reproduce the identical signature → `feedback_stall` → `unrecoverable_stall`.

3. **Why three sibling tasks succeeded in 1 turn.**

   - TASK-J004-001: classified `documentation` → independent test verification **skipped**
   - TASK-J004-002: classified `scaffolding` → independent test verification **skipped**
   - TASK-J004-003: extends `JarvisConfig` (succeeded — verify how it dodged the import)
   - TASK-J004-004: `declarative` (Pydantic schema) **runs** the independent pytest
     verification, which imports `jarvis` and fails on the broken env

   So the failure correlates with `task_type=declarative` + broken bootstrap, not with
   the schema work itself.

4. **Two interlocking advisory issues** (from `coach_turn_1.json`):

   - `agent_invocations_advisory` — "missing phases 3 (Implementation)" — non-blocking.
     Worth checking whether this advisory is correctly suppressed for `declarative`
     tasks (Pydantic schemas don't need a stack-specific Phase-3 specialist).
   - `test_verification` (must_fix) — the actual blocker.

   Both contribute to the identical-feedback signature that triggers the stall.

## Goal

Produce a diagnostic report that identifies **all** root causes (environmental,
orchestration-logic, coach-policy, task-classification, stall-detector) and a
prioritised remediation plan with concrete code/config changes scoped to GuardKit.
Do **not** propose changes to Jarvis — fixes must live in GuardKit so all consumers
benefit.

## Investigation Scope

Investigate at least these dimensions (not exhaustive — follow the evidence):

1. **Environment bootstrap policy** — Should `Environment bootstrap partial: 0/1
   succeeded` proceed or hard-fail? Is `bootstrap_failure_mode` configurable, and what
   is its default? If a Python interpreter mismatch is detected, can GuardKit pick a
   compatible interpreter (e.g., `pyenv` lookup, `uv venv`, `python3.12`) instead of
   using `/usr/local/bin/python3` (3.14)?

2. **Coach decision logic for `infrastructure` + `ambiguous` confidence** — In
   `guardkit/orchestrator/quality_gates/coach_validator.py` the path
   `conditional_approval check: failure_class=infrastructure, confidence=ambiguous,
   ..., wave_size=4` produces `feedback` (advisory). With `wave_size>1` the
   conditional-approval branch appears not to fire. Is this intentional? What should
   happen when ALL quality gates pass *and* independent tests fail on infrastructure
   ambiguously?

3. **Feedback-stall detector** — Is exiting on identical-feedback-with-zero-criteria
   the right behaviour when the stall cause is environmental? Should it surface a
   distinguished `environment_stall` decision with actionable next steps instead of a
   generic `unrecoverable_stall`?

4. **Agent-invocations advisory for declarative tasks** — Should the "missing Phase-3
   specialist" advisory fire at all for `task_type=declarative`? Confirm against the
   quality-gate profile config.

5. **Why does the orchestrator's preflight not surface the Python mismatch?** Bootstrap
   warning is logged, but Wave execution starts immediately. Should there be a
   preflight gate that aborts before consuming SDK budget on a doomed run?

6. **Comparison anchors** — Read at least one successful Jarvis run (FEAT-J002) and
   one successful Forge run (FEAT-FORGE-005). Identify *what is different* in the
   environment, the task_type distribution, and the coach decision path.

7. **Reproducibility & detection** — Can this stall pattern be detected pre-flight?
   What logging/instrumentation gap let it consume 33 minutes of wall time before
   surfacing? The "Suggested action: Review task_type classification" hint at the end
   is misleading because task_type is not the actual cause.

## Acceptance Criteria

- [ ] Root cause(s) identified with file:line evidence in the GuardKit codebase
      (e.g., `guardkit/orchestrator/environment_bootstrap.py:NN`,
      `guardkit/orchestrator/quality_gates/coach_validator.py:NN`,
      `guardkit/orchestrator/autobuild.py:NN` for stall detection)
- [ ] Distinguish primary cause from contributing causes; rank them
- [ ] Explanation of why TASK-J004-001/002/003 succeeded while -004 stalled, grounded
      in the coach validator's task-type-routed test policy
- [ ] Comparison against ≥1 successful Jarvis run and ≥1 successful Forge run that
      isolates which factor changed
- [ ] Remediation proposals, each scoped to a discrete TASK with:
      - Affected file(s)
      - Approximate change shape (no need for full diffs)
      - Risk and blast radius
      - Whether it requires a behaviour change vs config change vs new feature
- [ ] Identify whether the misleading "Suggested action: Review task_type" message
      should be replaced with environment-aware guidance
- [ ] Recommendation on whether `bootstrap_failure_mode` should default to `strict`
      (abort on partial bootstrap) for Python projects with version constraints
- [ ] No changes to the Jarvis repo are proposed (fixes must live in GuardKit)
- [ ] Report saved to `.claude/reviews/TASK-REV-FA04-report.md` (or per `/task-review`
      convention)

## Out of Scope

- Implementing any of the fixes — that comes via follow-up `/task-create` +
  `/task-work` tasks generated from the review's recommendations
- Refactoring the Coach validator beyond what is needed to address this stall class
- Touching the Jarvis repo's Python version constraints (the user can do this
  separately; the diagnosis must remain valid for any consumer)

## Suggested Workflow

```bash
/task-review TASK-REV-FA04 --mode=diagnostic
# Read the artefacts listed under "Source artefacts" first.
# Use Grep/Read across guardkit/orchestrator/{environment_bootstrap,autobuild,
#   feature_orchestrator}.py and guardkit/orchestrator/quality_gates/coach_validator.py.
# Cross-reference with the successful comparison runs.
# Produce the report; surface checkpoint for [A]ccept / [I]mplement / [R]evise.
```
