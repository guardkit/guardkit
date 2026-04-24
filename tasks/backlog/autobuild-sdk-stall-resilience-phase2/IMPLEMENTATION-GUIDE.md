# Implementation Guide: AutoBuild SDK Stall Resilience — Phase 2 (FEAT-F3D7)

## Quick Reference

- **Waves**: 2
- **Parallelism**: Wave 1 has 2 disjoint-file subtasks → both run in parallel
  Conductor workspaces. Wave 2 has 1 subtask that depends on the existence of
  the 7A08 file for the lint check to find it.
- **Testing depth**: `default-by-complexity`. Concretely:
  - Complexity 1 → minimal (compile + smoke)
  - Complexity 3–4 → standard (≥80% coverage on changed lines + arch review)

## Wave 1 — Parallel, disjoint files

### W1-1 · TASK-FIX-7A08 — Player prompt mandates Task-tool invocation

- Workspace: `autobuild-sdk-stall-resilience-phase2-w1-1`
- Command: `/task-work TASK-FIX-7A08`
- Touches:
  - `guardkit/orchestrator/prompts/autobuild_execution_protocol.md`
  - `guardkit/orchestrator/prompts/autobuild_execution_protocol_medium.md`
  - `guardkit/orchestrator/prompts/autobuild_execution_protocol_slim.md`
  - `guardkit/orchestrator/agent_invoker.py` (`_build_inline_implement_protocol`
    around lines 4479–4644)
  - `guardkit/orchestrator/phase_specialists.py` (consume for prompt rendering —
    source-of-truth for specialist names)
  - `tests/orchestrator/test_player_prompt_mandate.py` (new)
  - `tests/orchestrator/test_stall_classification.py` (extend with replay fixture)
- Gate:
  - Rendered prompt for every non-`direct` task-type contains the literal
    `subagent_type="test-orchestrator"` for Phase 4 and
    `subagent_type="code-reviewer"` for Phase 5.
  - Replay of minimised forge-run-3 NFI-003/NFI-007 fixture produces
    `agent_invocations_validation: 3/3 required` on turn 1.
- **Important**: preserve the phase-4/5 specialist names in
  `phase_specialists.STACK_TO_PHASE_3_SPECIALIST` / `GENERIC_PHASE_3_FALLBACK`.
  The prompt must consume them, not re-define them.

### W1-2 · TASK-FIX-7A09 — Extend defensive SDK handling to Coach independent-test path

- Workspace: `autobuild-sdk-stall-resilience-phase2-w1-2`
- Command: `/task-work TASK-FIX-7A09`
- Touches:
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (`_run_tests_via_sdk`
    around line 1375; fallback-log site around line 1732–1736)
  - `guardkit/orchestrator/exceptions.py` only if `AgentInvocationError.error_class`
    needs surfacing upstream for the test path
  - `tests/orchestrator/test_coach_sdk_stream_resilience.py` (new)
- Gate:
  - Simulated `ProcessError(exit_code=1, stderr="...")` produces a fallback log
    line that contains the exit code and stderr substring (not opaque `{e}`).
  - Simulated per-message `MessageParseError` / `ValueError` are skipped and
    logged but do not abort the SDK path.
- **Important**: this is the symmetric fix to TASK-FIX-7A03 — reuse its
  try/except cascade shape where applicable; prefer code reuse over
  reimplementation.

## Wave 2 — Depends on 7A08 file existing

### W2-1 · TASK-FIX-7A0A — CI lint: hardcoded TASK-ID literals resolve

- Workspace: `autobuild-sdk-stall-resilience-phase2-w2-1`
- Command: `/task-work TASK-FIX-7A0A` (direct mode; simple scan)
- Depends on: W1-1 (TASK-FIX-7A08 task file must exist for the lint to find it —
  its existence is the literal test fixture)
- Touches:
  - `tests/rules/test_no_dead_task_id_references.py` (new)
  - Optionally: `pyproject.toml` / CI config if the new test needs discovery
- Gate:
  - Test greps orchestrator source files (`guardkit/orchestrator/**/*.py`) for
    `TASK-(FIX|REV|DOC)-[A-Z0-9]+` literals and asserts each resolves to a file
    in `tasks/backlog/**/`, `tasks/in_progress/**/`, `tasks/completed/**/`,
    or `docs/state/**/`.
  - Test passes with 7A08 filed; would fail if the reference were removed again.

## Wave Structure

```
Time ─────────────────────────────────────────────►

Wave 1:  ├──W1-1 (7A08 · prompts + agent_invoker.py)──┤  ← parallel Conductor
         ├──W1-2 (7A09 · coach_validator.py)─────────┤     workspaces

Wave 2:                                                 ├──W2-1 (7A0A · CI lint)──┤
                                                          (requires 7A08 file)
```

## Rollback / Risk Management

- **TASK-FIX-7A08** is the riskiest — prompt wording changes are load-bearing.
  Mitigation: (a) add the prompt-mandate unit test before merging; (b) keep the
  phase-4/5 narrative sections — only *replace* the inline-bash commands and
  *add* the mandate language; (c) dry-run against the forge-run-3 replay fixture
  in CI.
- **TASK-FIX-7A09** preserves the subprocess fallback path — any exception not
  handled by the new try/except still falls through to subprocess pytest with
  an improved log line.
- **TASK-FIX-7A0A** is a pure test addition. Risk: low.

## Completion

When all three subtasks are in `completed/`:

```bash
/task-complete TASK-REV-F3D7
```

…and update the review task `status: review_complete → completed`, plus capture
feature-level outcome to Graphiti under `guardkit__task_outcomes` (FEAT-F3D7).
The completion episode should cite the empirical re-run verification (replay
fixture + live GB10 re-run of FEAT-FORGE-002 Wave 2 reaching approved) as
evidence the remediation landed.

## Live GB10 Verification (after all three land)

Re-run `guardkit autobuild feature FEAT-FORGE-002 --verbose --max-turns 30` on
GB10 and confirm:

1. Wave 2 tasks (NFI-003, NFI-007) pass the agent-invocations gate on **turn 1**
   (Player invokes `test-orchestrator` and `code-reviewer` via Task).
2. No `coach_agent_invocations_stall` summary appears.
3. Any residual `ProcessError` on the Coach independent-test path surfaces
   with stderr in the fallback log line.
4. `context_pollution_stall_no_checkpoint` does not co-fire (it only fires when
   no turn ever passes tests — which should no longer be the case).
