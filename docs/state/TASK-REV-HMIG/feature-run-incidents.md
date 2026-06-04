# Feature-run incidents — TASK-HMIG-010

> Per AC-006: this file records non-recoverable failures from the
> TASK-HMIG-010 feature-level LangGraph validation run, with root-cause
> analysis. "Non-recoverable" means: Coach rejection surviving 3
> task-work attempts, orchestrator crash, state-bridge corruption, or
> any failure the operator cannot resolve without code edits to the
> harness itself.
>
> Recoverable failures (first-pass-fail recovered by `--resume`) go in
> `feature-results.json:task_outcomes[*].notes`, not here.

## 0. Status

- Scaffolded by `/task-work TASK-HMIG-010` (2026-06-04)
- Empty until incidents occur

## Incident schema

Each incident gets its own `## I-NNN: <title>` section with:

- **Task**: which task in the feature triggered it
- **Wave / parallel group**: orchestration context
- **Symptom**: what the operator/orchestrator observed
- **Attempts made**: list of task-work attempts (1, 2, 3 + resume)
- **Root cause**: post-mortem analysis
- **Severity**: low | medium | high (high = blocks cutover; medium = file follow-up task)
- **Resolution**: code edit | spec revision | accepted-as-substrate-quality | other
- **Follow-up task**: TASK-FIX-* or TASK-REV-* filed (if any)

## Incidents

## I-001 (F9): `guardkit autobuild feature` doesn't thread `--model` to LangGraph harness

- **Task**: TASK-FIX-IA03 (Wave 1 of FEAT-AOF, run 1)
- **Wave / parallel group**: Wave 1, ungrouped
- **Symptom**: Player turn 1 raises `LangGraphHarnessError: ... agent.ainvoke failed for role='player' model=None: "Could not resolve authentication method. Expected either api_key or auth_token to be set..."`. Full traceback in [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md`](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md) line 134.
- **Attempts made**: Turn 1 only. The orchestrator's state-recovery + synthetic-report fallback fired correctly (5 git-detected file changes from bootstrap, synthetic promises generated), but Coach turn 1 then hit the **same** LangGraphHarnessError on `role='coach'` (line 319). Run terminated after 28s with feature `Status: ERROR`. `--resume` is technically possible but pointless — the same auth error will fire every turn.
- **Root cause**: The `guardkit autobuild feature` CLI subcommand has no `--model` option and doesn't thread a model name through `FeatureOrchestrator → AutoBuildOrchestrator → AgentInvoker → LangGraphHarness`. With `model=None` reaching the harness, DeepAgents' default model factory instantiates the Anthropic provider (`langchain_anthropic`), which then validates `ANTHROPIC_API_KEY` headers and fails. The operator's `OPENAI_BASE_URL` + `OPENAI_API_KEY` env vars (correct for llama-swap) are never consulted because no OpenAI-style chat model is instantiated.
- **Why it survived earlier validation**: 009A's 12-run batch only ran the `guardkit autobuild task` subcommand (via `scripts/canary_validation_runner.py`). The `task` subcommand DOES have `--model` (added by TASK-FIX-MODELPLUMB at [`guardkit/cli/autobuild.py:206-555`](../../../guardkit/cli/autobuild.py)). The 010 run is the first time anyone has executed `guardkit autobuild feature` under LangGraph.
- **Class-of-defect**: Sibling-of-F1 (canary-analysis.md §3.F1). Same shape: a migration path closed for one CLI entry point but missed for its sibling entry point. F1 was pre-loop vs Player-Coach loop; F9 is task subcommand vs feature subcommand.
- **Severity**: **HIGH** — blocks the cutover (per AC-008, any non-recoverable failure halts Wave 4). Meets AC-006's non-recoverable definition: *"any failure the operator cannot resolve without code edits to the harness itself."*
- **Resolution**: Code edit. Add `--model` to the feature subcommand and thread through. Mechanical fix (~1h) mirroring TASK-FIX-MODELPLUMB.
- **Follow-up task**: [TASK-FIX-LGFM](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-LGFM-feature-subcommand-model-threading.md) filed 2026-06-04. Blocks TASK-HMIG-010.
- **Validation orchestrator behaviour**: Notable that despite the immediate Player failure, the state-recovery machinery still functioned (captured 5 git-detected file changes from environment bootstrap, generated synthetic promises, advanced to Coach). This is correct behaviour for one-off Player crashes, but in this case the Coach hits the same error on the same code path — so the recovery loop is structurally unable to make progress. Not a Coach bug, just a noted artefact of the failure.

---

## References

- Parent task: [TASK-HMIG-010](../../../tasks/in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Sibling analysis: [feature-run-analysis.md](feature-run-analysis.md)
- Canary findings precedent: [canary-analysis.md §3](canary-analysis.md) (F1–F8 numbering convention)
