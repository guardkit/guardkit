---
id: TASK-ARCH-COACHSMOKE01
title: Fold a runtime/CLI smoke check into the Coach evidence bundle, fail-closed
status: backlog
task_type: feature
created: 2026-06-11T00:00:00Z
updated: 2026-06-11T00:00:00Z
priority: high
complexity: 6
effort_hours: 8
parent_feature: autobuild-harness-migration
related: [TASK-FIX-COACHFG01, TASK-SMK-F703A, TASK-TSJ-001]
implementation_mode: task-work
intensity: standard
falsifier: "Replay the FEAT-9DDE run-1 scenario (unit tests pass via pytest sys.path magic, CLI invocation dies with ModuleNotFoundError). PASS = the Coach's turn-1 verdict is FEEDBACK with a must_fix issue citing the smoke evidence, so the Player gets a turn-2 fix opportunity. FAIL = Coach approves and the bug is only caught by the post-approval wave gate (the run-1 behaviour)."
---

# Task: Smoke evidence in the Coach bundle (retro 2026-06-11 recommendation #1)

## Why this task exists

FEAT-9DDE run-1: the Coach was honest, criteria_verification was 10/10 with
real evidence, the independent oracle ran (3.7s) — and it **approved code that
does not run** (`python3 installer/core/commands/lib/task_status_json.py` →
`ModuleNotFoundError: No module named 'installer'`). The wave-level smoke gate
caught it in ~1s, **post-approval**, halting the feature instead of feeding the
Player a fix turn.

The Block paper's g3 coach catches exactly this class by *running the
deliverable itself* ("RUN the application yourself…"); its ablation shows the
no-runtime-check failure mode verbatim ("claimed to have implemented and
tested everything, but was basically not functioning"). The Coach's
bug-detection is bounded by its evidence — so put the runtime evidence **in
the bundle**, where a failure becomes turn-1 feedback rather than a
post-approval halt.

## Spec

1. **New bundle leg.** Add a `smoke` slice to `CoachEvidenceBundle`
   (`guardkit/orchestrator/quality_gates/coach_evidence.py:75-191`) populated
   by `CoachValidator.gather_evidence`
   (`guardkit/orchestrator/quality_gates/coach_validator.py:1723-2135`):
   command, exit code, duration, stdout/stderr tails, and a `signal_absent`
   analogue (`not_configured` / `not_runnable`).
2. **Command source.** Reuse the existing `SmokeGates` config surface
   (`guardkit/orchestrator/feature_loader.py:321-393`) — a per-task smoke
   command from task frontmatter (`autobuild.smoke_command`) falling back to
   the feature YAML's `smoke_gates.command`. Execution mechanics shared with
   `guardkit/orchestrator/smoke_gates.py:126-279` (subprocess, worktree cwd,
   venv PATH prepend, timeout) — factor, don't fork.
3. **Fail-closed in CODE, same shape as COACHFG01.** A failed smoke result
   must override an LLM `approve` to `feedback` deterministically in
   `AgentInvoker` (pattern: `_reconcile_absent_independent_test_signal`,
   `guardkit/orchestrator/agent_invoker.py:5083-5190`), inject a `must_fix`
   issue with `category: "runtime_smoke"`, and re-persist `coach_turn_N.json`.
   Never delegate this guard to the prompt (run-19 proved the LLM ignores
   prompt-only guards).
4. **Absence semantics (per `absence-of-failure-is-not-success`).** No smoke
   command configured ⇒ surface `not_configured` as an **advisory** in the
   verdict, never a silent green and never a hard fail (documentation-only
   tasks legitimately have nothing to smoke). A configured command that cannot
   execute (transport/timeout) ⇒ `signal_absent` ⇒ feedback, mirroring
   COACHFG01.
5. **Do NOT move or remove the wave-level gate.** The between-waves placement
   invariant is pinned by tests
   (`tests/unit/orchestrator/test_autobuild_smoke_placement.py`) and Graphiti
   decisions (smoke gates fire between WAVES, not tasks). This task adds a
   *Coach-evidence leg*; the wave gate stays as the composition-level
   defence-in-depth. Same command may serve both.

## Acceptance Criteria

- [ ] **AC-001** — `CoachEvidenceBundle.smoke` leg exists with
      configured/not_configured/signal_absent states and is populated by
      `gather_evidence` under its never-raise contract.
- [ ] **AC-002** — Deterministic code override: failed smoke ⇒ approve→feedback
      with `must_fix` `category: "runtime_smoke"`, coach_turn re-persisted on
      disk (Layer-4 reconciliation cannot resurrect the stale approve).
- [ ] **AC-003** — `not_configured` is advisory-only; regression test covers a
      docs-only task approving cleanly with no smoke command.
- [ ] **AC-004** — Falsifier test: FEAT-9DDE-class test/runtime divergence
      (importable under pytest, dead as a script) produces turn-1 feedback.
- [ ] **AC-005** — Wave-placement invariant tests still green; no second wave
      concept introduced (TASK-SMK-F703A non-goal preserved).
- [ ] **AC-006** — B-min synthesis prompt includes the smoke slice so the LLM
      verdict can cite it in `criteria_verification` evidence.

## References

- Retro: `docs/retro/coach-arc-journey-and-state-2026-06-11.md` §7 #1 (highest leverage)
- Incident: `docs/state/FEAT-9DDE/run-1-artifacts/README.md` (forward-work section
  already sketches this), `docs/reviews/autobuild-migration/autobuild-FEAT-9DDE-run-1.md`
- Pattern to copy: TASK-FIX-COACHFG01 (`agent_invoker.py:5083-5190`)
- Rule: `.claude/rules/absence-of-failure-is-not-success.md`
