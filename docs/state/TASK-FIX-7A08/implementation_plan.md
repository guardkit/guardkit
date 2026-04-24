# TASK-FIX-7A08 — Implementation Plan

## Summary

Mandate `Task(subagent_type=...)` invocation for Phase 3/4/5 in every Player
execution-protocol prompt (three `.md` files + the legacy Python inline
builder), sourcing specialist names from `phase_specialists.py` via
placeholder substitution at render time.

## Architecture Decisions

### Source-of-truth consumption

The three `.md` files carry `{phase_3_specialist}`, `{phase_4_specialist}`,
`{phase_5_specialist}` placeholders. Both Python builders
(`_build_autobuild_implementation_prompt`, `_build_inline_implement_protocol`)
substitute these at render time using `phase_specialists.py` constants:

- Phase 3 → `phase_3_specialist_for_stack(detect_stack_template(worktree_path))`
  (falls back to `GENERIC_PHASE_3_FALLBACK` when stack undetected)
- Phase 4 → `STATIC_PHASE_SPECIALISTS["4"]` (`test-orchestrator`)
- Phase 5 → `STATIC_PHASE_SPECIALISTS["5"]` (`code-reviewer`)

No hardcoded specialist strings land in the rendered-prompt-producing code.
Renaming a specialist in `phase_specialists.py` automatically propagates.

### Prompt prose shape

For each of Phase 3, 4, 5, the "how to execute" block is **replaced** (not
appended to) with:

```
## Phase N: <Title>

Do NOT run <inline command> inline. Invoke the <specialist> via the Task tool:

    Task(subagent_type="<specialist>", description="...", prompt="...")

Wait for the specialist's report before proceeding.
```

Inline `pytest`/`npm test`/`dotnet test` commands are removed. Quality-gate
thresholds remain (they're what the specialist must achieve, not what the
Player runs itself).

### Test strategy

1. **New** `tests/unit/test_player_prompt_mandate.py` — AC-4 assertions:
   for every production prompt path (full, medium, slim load + inline
   builder in standard/tdd/bdd modes), the rendered prompt contains
   `subagent_type="test-orchestrator"` and `subagent_type="code-reviewer"`.
   For each, also assert NO inline test-runner command (`pytest tests/`,
   `npm test`, `dotnet test`) is present in the Phase 4 section.

2. **Extended** `tests/unit/test_coach_agent_invocations_stall_classification.py`
   — Add a `test_post_fix_replay_*` pair using a minimised fixture
   (`tests/fixtures/forge_run_3_replay/`) that simulates a Player which
   followed the new mandate. Assert:
   - `agent_invocations_validation.status == "passed"`
   - `agent_invocations_validation.actual_invocations == 3`
   - `CoachValidator.verify_quality_gates` doesn't produce an
     `agent_invocations_violation` feedback.
   - `classify_stall` over 3 such turns produces no
     `coach_agent_invocations_stall`.

## Files to change

| File | Change |
|---|---|
| `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` | Replace Phase 3/4/5 "how-to" blocks + add `{phase_N_specialist}` placeholders |
| `guardkit/orchestrator/prompts/autobuild_execution_protocol_medium.md` | Same shape |
| `guardkit/orchestrator/prompts/autobuild_execution_protocol_slim.md` | Same shape |
| `guardkit/orchestrator/agent_invoker.py` | Substitute placeholders in both builders; inline-builder Phase 3/4/5 rewritten |
| `tests/unit/test_player_prompt_mandate.py` | **new** — mandate assertions |
| `tests/unit/test_coach_agent_invocations_stall_classification.py` | Extend with post-fix replay |
| `tests/fixtures/forge_run_3_replay/nfi_003_turn_1_post_fix.json` | **new** fixture |
| `tests/fixtures/forge_run_3_replay/nfi_007_turn_1_post_fix.json` | **new** fixture |

## Risk & complexity

- Complexity: 4/10 (frontmatter)
- Risk: Low — no runtime logic changes, prompt-string edits + test additions
- LOC estimate: ~300 added (mostly tests), ~80 modified (protocol md's)
- Coverage target: changed Python lines ≥ 80%

## Non-goals

- Do NOT relax the Coach agent-invocations gate (per AC)
- Do NOT preserve inline-execution as a fallback (per AC — that IS the defect)
- Do NOT add a new test directory `tests/orchestrator/` — the repo's layout
  uses `tests/unit/`; AC's `tests/orchestrator/test_stall_classification.py`
  path is adapted to actual-layout equivalents.
