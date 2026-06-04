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

## I-003 (F11): DeepAgents conversation-history offload writes to read-only host root

- **Task**: TASK-FIX-IA03 (Wave 1 of FEAT-AOF, run 2, test-orchestrator specialist)
- **Wave / parallel group**: Wave 1, ungrouped (surfaced during specialist invocation, not main Player)
- **Symptom**: `deepagents.middleware.summarization:Failed to offload conversation history to /conversation_history/session_7b9e811b.md (60 messages): Error writing file '/conversation_history/session_7b9e811b.md': [Errno 30] Read-only file system: '/conversation_history'` (run-2 line 342). Because offload fails, summarization can't trim message history; the test-orchestrator specialist's 9th LLM call carries 569,665 tokens of accumulated context against qwen36-workhorse's 131,072-token window. llama-swap returns HTTP 400 `exceed_context_size_error` (run-2 line 350).
- **Attempts made**: This is the first observation. Cannot be retried without filesystem reconfiguration in guardkitfactory.
- **Root cause**: DeepAgents' `summarization.py` middleware constructs offload paths from a config that defaults to absolute host-root `/conversation_history/`. The guardkitfactory LangGraph harness setup didn't override this to a writable per-worktree path. Sibling-of-NOVMODE: the same class of defect TASK-HMIG-002R-NOVMODE addressed for `virtual_mode=False`'s path-doubling — DeepAgents assumes a virtualised filesystem but lands on a real one.
- **Class-of-defect**: sibling-of-NOVMODE. DeepAgents configuration that assumes a non-host filesystem but lands on the host. NOVMODE was paths under `/`; F11 is paths under `/conversation_history/`.
- **Severity**: **HIGH** — qwen36-workhorse's 131k context is much smaller than Sonnet's ~200k. Without offload working, any non-trivial conversation hits the limit fast. Meets AC-006's non-recoverable definition (requires code edits to guardkitfactory).
- **Resolution**: Code edit in guardkitfactory. Either point offload at `<worktree>/.guardkit/conversation_history/` or disable offload + set a message-count cap on the summarization middleware. RECOMMENDED: both.
- **Follow-up task**: [TASK-FIX-CHO01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-CHO01-deepagents-conversation-history-offload-path.md) filed 2026-06-04. Blocks TASK-HMIG-010.
- **Note on visibility**: F11 was only visible in run 2 because F10 (below) didn't kill execution outright — the orchestrator's synthetic-report path kept the turn alive long enough to invoke the test-orchestrator specialist, which then exposed F11. Without F10's "soft" failure mode, F11 would have lurked behind the immediate auth fail.

## I-002 (F10): `_invoke_task_work_implement` doesn't pass `model=` to `select_harness`

- **Task**: TASK-FIX-IA03 (Wave 1 of FEAT-AOF, run 2, main inline-implement Player)
- **Wave / parallel group**: Wave 1, ungrouped
- **Symptom**: Identical to F9 — `LangGraphHarnessError: ... agent.ainvoke failed for role='player' model=None: "Could not resolve authentication method..."` (run-2 line 139). Same DeepAgents-defaults-to-Anthropic chain because the model name doesn't reach the harness construction site.
- **Attempts made**: Run 2 turns 1 and 2, both fail identically at the main Player invocation (lines 139 and 448). The recovery loop is structurally unable to make progress on this code path.
- **Root cause**: TASK-FIX-MODELPLUMB threaded the model through one of `AgentInvoker`'s two `select_harness()` call sites — the `_invoke_with_role` path used by Coach and specialists ([`agent_invoker.py:2855`](../../../guardkit/orchestrator/agent_invoker.py)) — but not the other, the `_invoke_task_work_implement` path used for the main inline-implement Player ([`agent_invoker.py:5730`](../../../guardkit/orchestrator/agent_invoker.py)). Run 2's split signature confirms: line 139 main Player has `model=None`, line 350 specialist has `model='openai:qwen36-workhorse'`.
- **Class-of-defect**: sibling-of-F9 (which was itself sibling-of-F1). Same shape: a migration path closed for some invocation sites but missed for others. F1 was Player-Coach-loop vs pre-loop. F9 was task vs feature CLI subcommand. F10 is `_invoke_with_role` vs `_invoke_task_work_implement`. **Three instances of the same defect-class** — worth a `.claude/rules/` seeding (proposal at the bottom of TASK-FIX-LGFM2).
- **Severity**: **HIGH** — blocks the main Player path entirely. Meets AC-006's non-recoverable definition (requires code edits).
- **Resolution**: One-line code edit: add `model=self._model_name,` to the `select_harness(...)` call at `agent_invoker.py:5730`. Mechanical.
- **Follow-up task**: [TASK-FIX-LGFM2](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-LGFM2-inline-implement-model-threading.md) filed 2026-06-04. Blocks TASK-HMIG-010.

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
