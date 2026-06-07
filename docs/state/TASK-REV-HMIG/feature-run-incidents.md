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

## I-011 (F22): SPECHANG hang-detection cascades into 120s Coach grace-period, structurally incompatible with gemma4 Coach reasoning time

- **Task**: TASK-FIX-IA03 (run 10, Wave 1, turn 1 Coach validation)
- **Wave / parallel group**: Wave 1
- **Symptom**: Turn-1 Player succeeded (40 created, 1 modified in 382s). Turn-1 test-orchestrator specialist made several successful HTTP 200s then hit the new SPECHANG watchdog: `WARNING:guardkit.orchestrator.specialist_invocations:[TASK-FIX-IA03] run_specialist(test-orchestrator): hang detected (no model activity for 150s) — terminating before the 600s duration cap` ([run-10 line 214](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L214)). The hang-detection set the task-level `cancellation_event`. The orchestrator then took the TASK-ABFIX-004 Player-succeeded branch: `Cancellation detected for TASK-FIX-IA03 between Player and Coach at turn 1, but Player succeeded — granting Coach grace period (120s)` ([line 218](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L218)). Coach SDK timeout was therefore capped at `budget_cap=120s` ([line 250](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L250)). Coach independent tests consumed 84.6s of that window (TASK-FIX-COACHPYENV pinning correctly applied); the LLM invocation got ~80s before CTOUT01 cancelled cleanly with **0 text blocks extracted** ([line 253](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L253)). Total wall: 10m 20s.
- **Attempts made**: First observation. The interaction surfaced as soon as both features composed in production: TASK-FIX-SPECHANG hang-watchdog (specialist_invocations.py:113) + TASK-ABFIX-004 Coach grace period (autobuild.py:3077-3087) + `COACH_GRACE_PERIOD_SECONDS=120` (autobuild.py:191).
- **Root cause**: Two defensive features composed badly. SPECHANG's hang-detection reuses the shared `cancellation_event` to abort the in-flight specialist (correct for CTOUT01 in-flight LangGraph cleanup). But that event is also the trigger the orchestrator uses to detect *task-level* cancellation between Player and Coach, so the Player-succeeded grace branch fires. The 120s constant baked into that branch is irreconcilable with the run-9 empirical evidence (gemma4 Coach turn 1 took 944s under `--reasoning off`); even with `--reasoning auto` in run 10, a Coach validation needs more than 120s once independent tests consume ~85s of the window.
- **Class-of-defect**: code-side **cascade defect** — distinct from F1/F4/F10 (migration-boundary defects) and F17/F20 (substrate-quality defects). Two reasonable defensive mechanisms compose into an architectural impossibility.
- **Severity**: **HIGH** — blocks AC-006 / AC-009 evaluation. Coach never gets enough budget to emit anything, so we can't tell whether `--reasoning auto` solves F17. AC-009 surface remains untested after run 10.
- **Resolution**: [TASK-FIX-SPECCOCH01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-SPECCOCH01-decouple-specialist-hang-from-coach-grace.md). Two-shape fix with backstop:
  - **Shape A (primary)**: Specialist-hang detection does NOT set the task-level `cancellation_event` — only aborts the specialist. Orchestrator continues normally; specialist failure already injects `validation=violation` records via `_inject_specialist_records_into_task_work_results` ([run-10 line 217](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L217)), so downstream consumers see a graceful failure not a missing record.
  - **Shape B (defensive backstop)**: Make `COACH_GRACE_PERIOD_SECONDS` env-tunable (`GUARDKIT_COACH_GRACE_PERIOD_SECONDS`, default raised to 1500 to cover run-9's 944s + 50% headroom). Same env-tuning pattern as `GUARDKIT_TASK_TIMEOUT_SECONDS` from TASK-FIX-AOFBUDG. Cheap belt-and-braces even with Shape A.
- **Follow-up task**: [TASK-FIX-SPECCOCH01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-SPECCOCH01-decouple-specialist-hang-from-coach-grace.md) filed 2026-06-07. **Blocks TASK-HMIG-010** as the verdict-blocker for run 11.
- **Notes**:
  - **F20 + F21 still RESOLVED** in run 10 — zero `HTTP 400` / `exceed_context_size_error` anywhere in the log. The §9.13 n_ctx bump remains validated.
  - **Other architecture wins from concurrent task landings** ALL confirmed in run 10: TASK-FIX-AOFBUDG (4800s task_timeout effective at [line 11](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L11)); TASK-FIX-COACHPYENV (Coach independent tests pinned to bootstrap venv, 84.6s vs 200s+ previously, [line 237](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L237)); TASK-OPS-AOFENV (FalkorDB up, Graphiti context loaded at [lines 220-234](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-10.md#L220-L234)); SPECHANG watchdog itself fired correctly (the cascade is the bug, not the detection).
  - **AC-009 NOT exercised** — gemma4-coach was flipped to `--reasoning auto` for this run but the Coach was cancelled before producing any output, so we still don't know if `reasoning_content` channel populates with the fenced verdict. Run 11 with SPECCOCH01 landed will be the actual AC-009 test.

## I-010 (F21): turn-2 Coach hard-stall under gemma4-coach (substrate quality, downstream of F20) — **RESOLVED 2026-06-07 (run 9)**

> **Status update 2026-06-07**: Run 9 did not reproduce the F21 zero-HTTP hang. Turn-2 Coach validation in run 9 was cancelled by CTOUT01 at the legitimate 3000s task-timeout boundary (time-budget exhaustion, not substrate hang) after the prior phases consumed the budget. The cancellation log line is identical to run 8 (`TASK-FIX-CTOUT01: Cancellation event detected during coach invocation`) but the cause is different: run-9 Coach ran ~80s before cancel, with two HTTP 200s observed (lines 464-468 + 472 of run-9 log); run-8 Coach ran 990s+ with zero HTTP calls. This confirms the run-8 hypothesis that F21 was a KV-corruption / model-swap deadlock downstream of the F20 HTTP 400, and removing F20 removed F21.



- **Task**: TASK-FIX-IA03 (run 8, Wave 1, turn 2 Coach validation)
- **Wave / parallel group**: Wave 1
- **Symptom**: After the code-reviewer specialist failed with F20 (HTTP 400 context overflow at line 376), Coach validation began at 16:43:33 ([autobuild-FEAT-AOF-run-8.md:378](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-8.md#L378)). The 30s-interval progress counter ran from 30s through 990s elapsed ([line 394-426](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-8.md#L394-L426)) with **zero successful HTTP requests** in the entire window (no `POST /v1/responses HTTP/1.1 200 OK` between line 392 and line 427). Task-level 3000s timeout fired at 17:03:37; CTOUT01's cancellation event detected and `harness.cancel()` propagated correctly ([line 430](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-8.md#L430)). Task moved to CANCELLED cleanly.
- **Attempts made**: First observation. Single turn-2 invocation hung for the full task-timeout window.
- **Root cause hypothesis**: Almost certainly downstream of F20 (gemma4-coach `n_ctx=65536` too small). Coach validation prompt for turn 2 carries cumulative state (turn-1 feedback context + 46-file turn-2 diff + 10 cumulative ACs), likely arrives at ≥65k tokens. Either llama-swap silently wedges on oversized input instead of returning 400 (race condition after the prior 400 corrupted KV state), or llama.cpp's gemma4-coach instance is mid-reload after the prior specialist call evicted it. The zero-HTTP-call stall pattern matches a model-swap deadlock more than a slow inference path.
- **Class-of-defect**: **substrate-quality**, downstream consequence of F20. The architecture-side response was correct: CTOUT01 Layer 3 (harness.cancel) fired exactly as designed at the 3000s task-timeout boundary, bounding the failure window. The stall itself is observable but not architecturally blocking.
- **Severity**: **MEDIUM** — masks any signal we'd otherwise get from turn-2 Coach validation, but contained by CTOUT01. Goes away when F20 is fixed (no oversized payloads → no KV-state corruption → no stall).
- **Resolution**: Same operator-side fix as F20 (bump gemma4-coach `n_ctx` to 98304 or 131072 in llama-swap). No code change. Re-validation will confirm whether F21 is purely-downstream-of-F20 or has its own substrate stall surface.
- **Follow-up task**: None filed. Substrate-quality finding tracked here for AC-008 evidence; revisit after F20 mitigation.

## I-009 (F20): gemma4-coach `n_ctx=65536` too small for Coach + specialist payloads — **RESOLVED 2026-06-07 (run 9)**

> **Status update 2026-06-07**: Operator landed the §9.13 n_ctx bump on llama-swap and re-ran (run 9). Zero `HTTP 400`, zero `exceed_context_size_error`, zero `n_prompt_tokens > n_ctx` log lines anywhere in [autobuild-FEAT-AOF-run-9.md](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-9.md) (confirmed by grep). Turn-1 code-reviewer specialist — the exact run-8 failure point — completed cleanly with 18+ successful HTTP 200s over ~480s. F21 (the run-8 turn-2 Coach hang) also did not recur, confirming the run-8 hypothesis that F21 was purely downstream of F20. Architecture invariants from runs 1-8 all still working. F20 closed; F17 (substrate F2 at Coach level under `--reasoning off`) is now the dominant load-bearing constraint, exercised in run 9 with the COACHBUDG01 AC-009 `--reasoning auto` experiment as the next step.



- **Task**: TASK-FIX-IA03 (run 8, Wave 1, turn 2 code-reviewer specialist)
- **Wave / parallel group**: Wave 1
- **Symptom**: `code-reviewer` specialist invocation (under Coach role, routed to `gemma4:26b` per `--coach-model` flag) made several successful HTTP 200 calls then failed with HTTP 400 ([autobuild-FEAT-AOF-run-8.md:375-376](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-8.md#L375-L376)): `LangGraphHarness: agent.ainvoke failed for role='coach' model='openai:gemma4:26b': Error code: 400 - {'error': {'code': 400, 'message': 'request (69174 tokens) exceeds the available context size (65536 tokens), try increasing it', 'type': 'exceed_context_size_error', 'n_prompt_tokens': 69174, 'n_ctx': 65536}}`. Run-8 was the first run to actually reach the gemma4-coach Coach payload at depth (runs 5-6 hit qwen36-workhorse F17; run 7 hit the selector colon-alias bug closed by `d526bf0f`).
- **Attempts made**: First observation. Reproduced once; runs 1-7 used qwen36-workhorse Coach (different sizing envelope).
- **Root cause**: §9.13 of [AUTOBUILD-ON-LLAMA-SWAP-findings.md](../../research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md#L1943) registered the gemma4-coach llama-swap entry with `n_ctx=65536` (half of qwen36-workhorse's 131072). guardkitfactory's `MODEL_CONTEXT_WINDOWS["gemma4:26b"]["max_input_tokens"]=65536` correctly threads this to deepagents (`model_config.py:188-194`), so summarisation *should* fire at `fraction × 65536 ≈ 55,705`. But code-reviewer specialist's tool-use loop grew context fast enough between summarisation rounds that one HTTP call landed at 69174 tokens — over the limit, no summarisation window remaining. The registry contract is honoured; the substrate is just too small for this codebase's Coach payload shape under multi-specialist turns.
- **Class-of-defect**: **substrate-sizing / operator-policy**, not architecture. Sibling of canary F6 (substrate-quality, recorded not coded) but with a cheap operator-side fix available. Distinct from F11 (which was a path-routing defect, code-fixable in guardkitfactory).
- **Severity**: **HIGH** — blocks AC-006 verdict. Without code-reviewer specialist completing, Coach can't see review feedback, and turn 2 was the recovery turn for turn 1's COACHSF01-routed feedback. Triggers cascade into F21 (turn-2 Coach stall). Cutover-deadline-critical because TASK-HMIG-013 AC-006 falsifier (`Coach verdict-emission rate ≥95% across 6+ Coach turns`) cannot be evaluated while turn 2 hangs.
- **Resolution**: Operator-side llama-swap config change. No code edit. Three paths in increasing risk/reward:
  - **(A) Bump `n_ctx` to 98304 (1.5×)** — preferred first step. Headroom against the observed 69174-token failure point ≈33%. KV-cache delta ≈ +2.5-5 GB (current GB10 footprint 111/128 GB used → projected 113.5-116 GB used, ≥12 GB headroom). Re-run smoke with `--fresh --coach-model gemma4:26b`.
  - **(B) Bump `n_ctx` to 131072 (2×)** — matches qwen36-workhorse. KV delta ≈ +5-10 GB → 116-121 GB used, 7-12 GB headroom. Acceptable but watch `free -h` / `nvidia-smi` during the first model reload for transient peaks.
  - **(C) Wait for 2nd GB10 + register `nemotron-3-super:120b-a12b`** as Coach (128k native ctx). Better long-term answer but doesn't fit the 2026-06-15 cutover deadline.
  - guardkitfactory `MODEL_CONTEXT_WINDOWS["gemma4:26b"]["max_input_tokens"]` must be updated to match the new `n_ctx` so the summarisation threshold scales accordingly.
- **Follow-up task**: None filed (operator-side config change, not a code defect). Operator runbook addendum landing in [§9.13 of the findings doc](../../research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md#L1943). **Blocks TASK-HMIG-013 AC-006** until run 9 confirms the bump unblocks Coach verdict-emission.
- **Notes**:
  - The selector colon-alias fix (`d526bf0f`) and `--coach-model` plumbing (`d07a4209`) both worked correctly — the LangGraph error explicitly carries `role='coach' model='openai:gemma4:26b'`, confirming F19 (selector) closed and the Coach routing is honoured end-to-end.
  - F17 (COACHSF01) ALSO fired correctly on turn 1 (Coach emitted 4898 chars content + 0 reasoning, no fenced JSON → synthetic feedback emitted → Player got turn 2 with feedback). The architecture invariants are all intact. F20 is purely a substrate-sizing finding.
  - AC-009 (parser robustness with `--reasoning auto`) was NOT exercised — run 8 ran gemma4-coach with `--reasoning off` per §9.13. The 4898-char prose response was the existing COACHSF01-handled shape, not the AC-009 surface.

## I-008 (F18): pip-cache ghost-path filter gap

- **Task**: TASK-FIX-IA03 (run 4)
- **Wave / parallel group**: Wave 1
- **Symptom**: Player's `files_modified` list in `turn_state_turn_1.json` contains 40+ entries under `Library/Caches/pip/http-v2/...` alongside the real Player change (`tests/orchestrator/test_doc_level_exclusion.py`). The orchestrator's ghost-path filter at [`agent_invoker.py:200`](../../../guardkit/orchestrator/agent_invoker.py) caught 4 known paths (bootstrap_state.json, GD02/TP05 backlog files, IA03 design_approved path) but didn't filter the pip-cache writes that the environment bootstrap leaves in the worktree's git detection.
- **Attempts made**: First observation in audit.
- **Root cause**: The ghost-path filter has a hardcoded allow-list of orchestrator-induced paths; pip cache wasn't in it. Bootstrap installs Python deps into the worktree's venv, which populates `Library/Caches/pip/http-v2/` with HTTP response cache files; git detection later sees these as "files modified during the Player's turn".
- **Class-of-defect**: noise leak in the orchestrator's ghost-path filter contract. Doesn't affect substantive outcomes (Coach was about to handle this fine).
- **Severity**: **LOW (cosmetic)** — doesn't affect runs. Could affect future tooling that consumes `files_modified` (e.g. test-impact analysis, scope-creep detection). Worth tightening but not blocking.
- **Resolution**: Extend the ghost-path filter to include `Library/Caches/pip/` and similar bootstrap-output patterns. One-line change. Not filed as a separate task — fold into next ghost-path-related work.
- **Follow-up task**: None filed. Recorded here for the next person who touches `_filter_orchestrator_induced_ghost_paths` (or equivalent).

## I-007 (F17): Coach LLM completes but doesn't emit verdict file (canary F2 at Coach level)

- **Task**: TASK-FIX-IA03 (run 4, Wave 1 Coach turn 1)
- **Wave / parallel group**: Wave 1, ungrouped
- **Symptom**: After Player succeeded (41 files created, 5 promises + 5 ACs recovered) and specialists completed (`merged=2` in task_work_results.json), Coach LLM ran for ~140s with 12 successful `POST /v1/responses HTTP/1.1 200 OK` responses, then the orchestrator raised `Coach decision not found: .guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/coach_turn_1.json`. Run-4 log line 297. The verdict file was never written.
- **Attempts made**: Single turn. Hard-failed without recovery.
- **Root cause (diagnosed by source inspection)**:
  - Coach's contract requires writing the verdict via a Bash heredoc tool call ([`agent_invoker.py:2393-2394`](../../../guardkit/orchestrator/agent_invoker.py) prompt) because Coach's `allowed_tools = ["Read", "Bash", "Grep", "Glob"]` ([`agent_invoker.py:1959`](../../../guardkit/orchestrator/agent_invoker.py)) — no `Write` tool.
  - qwen36-workhorse Coach reasoned about the verdict for 140s but never emitted the structured Bash tool call. This is **canary F2 manifesting at Coach level**: "model discusses tool calls in prose but no actual tool_use blocks are emitted" (canary-analysis.md §3.F2 documents the same behaviour for Player).
  - Why this didn't fire in run 3 but did in run 4: run 3's Coach saw a SYNTHETIC Player report (from the F10 recovery path) → simpler Coach reasoning → tool call succeeded. Run 4's Coach saw a REAL Player report with 63 pre-existing test failures → complex reasoning → drift into prose response.
  - **The orchestrator already has a fix mechanism** ([`autobuild.py:5663`](../../../guardkit/orchestrator/autobuild.py) `_invoke_coach_primary`'s except Exception → `_emit_synthetic_coach_feedback`) but the safety net only fires on raised exceptions. `invoke_coach` catches `CoachDecisionNotFoundError` internally at [`agent_invoker.py:1987-1997`](../../../guardkit/orchestrator/agent_invoker.py) and returns `success=False`, which bypasses the safety net. The downstream consumer sees `coach_decision="error"` and Wave 1 hard-fails.
- **Class-of-defect**: dual-finding —
  - **Substrate quality** (qwen36-workhorse + Coach Bash-heredoc contract is unreliable) — canary F2 confirmed at Coach scope. This is foundational and won't be "fixed" without prompt/model changes (out of scope).
  - **Load-bearing inconsistency** between `invoke_coach`'s success=False return shape and `_invoke_coach_primary`'s except-Exception safety net — fixable. The safety net was designed for "Coach invocation failed unexpectedly" but the file-not-found case looks like that, just routed through a different control-flow path.
- **Severity**: **HIGH** — blocks AC-008 verdict. Until the safety net is wired, every task where Coach has to reason about non-trivial evidence will produce a hard-fail at run-4-style verdict-emission. Player's substantive work was correct (14/14 doc-level exclusion tests pass in this run) but the orchestrator can't record the verdict, so AC-008 can't progress.
- **Resolution**: Wire the safety net. Fix-shape (a) per the run-4 investigation: in `_invoke_coach_primary`, after `asyncio.run(invoke_coach(...))` returns, if `result.success == False` AND `"Coach decision not found"` in `result.error`: call `_emit_synthetic_coach_feedback(rationale=...)` and return. Other `success=False` outcomes pass through unchanged. ~15 lines + regression test.
- **Follow-up task**: [TASK-FIX-COACHSF01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-COACHSF01-coach-soft-fail-on-decision-not-found.md) filed 2026-06-05. **Blocks TASK-HMIG-010** as the verdict-blocker for run 5.
- **Notes**:
  - After COACHSF01 lands, F17 converts from hard-blocker to soft-fail telemetry. The orchestrator records "Coach verdict-emission failed, emitting synthetic feedback" → Player gets turn 2 to retry with feedback → eventually either substrate succeeds or orchestrator exhausts max_turns with a clean "feedback after N turns" verdict.
  - The substantive Player work in run 4 confirms qwen36-workhorse + LangGraph + the migration stack CAN produce correct implementation output. Only the Coach verdict-emission step is unreliable. This is a positive substrate signal for cutover.
  - Out-of-scope follow-on: longer-term, Coach's verdict-emission contract should not depend on the model executing a multi-line Bash heredoc. Options include (1) reducing Coach prompt to a structured-output format the orchestrator parses from the response text, or (2) granting Coach a constrained `Write` tool limited to coach_turn_*.json paths. Either is a bigger architectural decision — file as TASK-REV-COACH-OUTPUT-CONTRACT post-cutover.

## I-006 (F16): Graphiti FalkorDB teardown race — `no running event loop` at process exit

- **Task**: process-wide (post-feature-orchestration cleanup)
- **Wave / parallel group**: n/a (process exit)
- **Symptom**: `ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: no running event loop` followed by traceback ending `RuntimeError: no running event loop`. Run-3 log lines 1638–1686.
- **Attempts made**: First observation. Doesn't affect run outcomes (process is already exiting).
- **Root cause**: A Graphiti `edge_fulltext_search` coroutine is in-flight when the event loop closes — characteristic fire-and-forget pattern. The traceback's "Exception ignored while closing generator" confirms CPython is suppressing the actual error.
- **Class-of-defect**: async teardown hygiene. Not a migration-class defect.
- **Severity**: **LOW** — cosmetic; doesn't affect outcomes; may hide real teardown issues if/when they appear.
- **Resolution**: Code edit in `guardkit.knowledge.autobuild_context_loader` or `graphiti_client`. Either await the offending call or register a process-exit handler.
- **Follow-up task**: [TASK-FIX-FALK01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md) filed 2026-06-05. Does NOT block TASK-HMIG-010 — deferrable to Wave 4 cleanup.

## I-005 (F14): Coach cancellation race — task-level timeout fires but Coach continues to approval

- **Task**: TASK-FIX-GD02 (Wave 2 of FEAT-AOF, run 3, turn 2 Coach)
- **Wave / parallel group**: Wave 2, ungrouped within wave
- **Symptom**: At 07:45:26, feature_orchestrator fires `task_timeout=3000s expired` for TASK-FIX-GD02 (run-3 lines 1555–1556). `TASK-FIX-ASPF-004: Cancellation event detected during coach invocation, terminating SDK subprocess` (line 1559). But 5+ subsequent `POST /v1/responses` calls succeed (lines 1560–1564), and at 07:46:14 Coach reaches APPROVED (line 1565). Final bookkeeping diverges: outer feature_orchestrator marks `Wave 2 ✗ FAILED: 1 passed, 1 failed` (line 1601); inner autobuild summary marks `Status: APPROVED ... Coach approved implementation after 2 turn(s)` (lines 1579–1595).
- **Attempts made**: First observation. The race is between the cancellation event and the in-flight LangGraph `agent.ainvoke` async operation; cancellation didn't propagate.
- **Root cause hypothesis**: ASPF-004's cancellation handler is SDK-subprocess-specific (`terminating SDK subprocess`). Under the LangGraph harness, there's no subprocess — the in-flight call is `async agent.ainvoke(...)` on the orchestrator's event loop. The cancellation flag is set but doesn't propagate to LangGraph's pregel loop or the in-flight `langchain_anthropic._async_client.messages.create(...)` HTTP request.
- **Class-of-defect**: **harness asymmetry** — a contract honoured by the SDK harness (process termination) but not by the LangGraph harness (which needs `asyncio.CancelledError` propagation instead). Distinct from the model-threading class but a sibling shape (something the migration was supposed to translate didn't get translated).
- **Severity**: **HIGH** — blocks AC-008 falsifier computation because GD02's true verdict is ambiguous. If counted as failure: 2/3 = 67%, falsifier fails. If counted as success: 3/3 = 100%, falsifier passes. The cutover decision swings on this one task's ground-truth verdict, which the orchestrator can't currently report.
- **Resolution**: Code edit + regression test. See [TASK-FIX-CTOUT01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-CTOUT01-coach-cancellation-timeout-race.md) for the full investigation plan. Cancellation must propagate to the LangGraph harness's `invoke(...)` async iteration within a bounded window (≤30s), and the outer verdict (cancellation) must dominate the inner verdict (approval-after-cancellation).
- **Follow-up task**: [TASK-FIX-CTOUT01](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-CTOUT01-coach-cancellation-timeout-race.md) filed 2026-06-05. **Blocks TASK-HMIG-010** (AC-008 verdict-blocker).

## I-004 (F12): `coach_test` role missing model threading (4th instance of class)

- **Task**: TASK-FIX-IA03 and TASK-FIX-GD02 (CoachValidator's SDK test execution path, fired for every Coach turn)
- **Wave / parallel group**: every Coach turn across both waves
- **Symptom**: `ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution failed (error_class=LangGraphHarnessError): LangGraphHarness: agent.ainvoke failed for role='coach_test' model=None: "Could not resolve authentication method..."` (run-3 line 313 and similar at 1540). Immediately followed by `WARNING: SDK test execution failed (error_class=LangGraphHarnessError), falling back to subprocess.` (line 314, 1541).
- **Attempts made**: Fires on every Coach turn. Fallback to subprocess works — runs aren't blocked, just noisy.
- **Root cause**: Same as F1/F9/F10: a migration boundary closed for some invocation sites but missed for one more. The CoachValidator's SDK test execution path (`coach_test` role) constructs the harness without passing `model=`.
- **Class-of-defect**: **4th instance of the model-threading class** (F1, F9, F10, F12). The cadence is no longer accidental.
- **Severity**: **MEDIUM** — soft-fails to subprocess fallback, so runs continue. But every Coach turn pays a logged ERROR + fallback overhead, and the LangGraph code path is dead. Audit-log noise affects AC-008 evidence-clarity.
- **Resolution**: One-line code edit + regression test. Mirror [`agent_invoker.py:5756`](../../../guardkit/orchestrator/agent_invoker.py) (the LGFM2 pattern). Probably in `guardkit/orchestrator/quality_gates/coach_validator.py`.
- **Follow-up task**: [TASK-FIX-LGFM3](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-LGFM3-coach-test-role-model-threading.md) filed 2026-06-05. Does NOT block TASK-HMIG-010 (subprocess fallback works), but should land before AC-008 verdict for clean signal.
- **Class-of-defect rule-seeding**: At 4 instances, a `.claude/rules/` rule is warranted post-cutover. Proposal in LGFM3 and feature-run-analysis.md §6.

## I-003 (F11): DeepAgents conversation-history offload writes to read-only host root

- **Task**: TASK-FIX-IA03 (Wave 1 of FEAT-AOF, run 2, test-orchestrator specialist)
- **Wave / parallel group**: Wave 1, ungrouped (surfaced during specialist invocation, not main Player)
- **Symptom**: `deepagents.middleware.summarization:Failed to offload conversation history to /conversation_history/session_7b9e811b.md (60 messages): Error writing file '/conversation_history/session_7b9e811b.md': [Errno 30] Read-only file system: '/conversation_history'` (run-2 line 342). Because offload fails, summarization can't trim message history; the test-orchestrator specialist's 9th LLM call carries 569,665 tokens of accumulated context against qwen36-workhorse's 131,072-token window. llama-swap returns HTTP 400 `exceed_context_size_error` (run-2 line 350).
- **Attempts made**: This is the first observation. Cannot be retried without filesystem reconfiguration in guardkitfactory.
- **Root cause**: DeepAgents' `summarization.py` middleware constructs offload paths from a config that defaults to absolute host-root `/conversation_history/`. The guardkitfactory LangGraph harness setup didn't override this to a writable per-worktree path. Sibling-of-NOVMODE: the same class of defect TASK-HMIG-002R-NOVMODE addressed for `virtual_mode=False`'s path-doubling — DeepAgents assumes a virtualised filesystem but lands on a real one.
- **Class-of-defect**: sibling-of-NOVMODE. DeepAgents configuration that assumes a non-host filesystem but lands on the host. NOVMODE was paths under `/`; F11 is paths under `/conversation_history/`.
- **Severity**: **HIGH** — qwen36-workhorse's 131k context is much smaller than Sonnet's ~200k. Without offload working, any non-trivial conversation hits the limit fast. Meets AC-006's non-recoverable definition (requires code edits to guardkitfactory).
- **Resolution**: Code edits in guardkitfactory. Landed 2026-06-05 as a pair:
  - **TASK-HMIG-002R-SUMM-ROOT**: `backend_config.py` now returns `CompositeBackend(default=LocalShellBackend(...), routes={}, artifacts_root=str(worktree))`. Empty routes preserves NOVMODE semantics (everything falls through to LocalShellBackend); the wrapper's only job is to expose `artifacts_root` to `_DeepAgentsSummarizationMiddleware`, which now computes the offload prefix as `<worktree>/conversation_history/` instead of literal `/conversation_history/`.
  - **TASK-HMIG-002R-MODEL-PROFILE**: New `model_config.py` exposes `resolve_autobuild_model()` and `MODEL_CONTEXT_WINDOWS = {"qwen36-workhorse": 131072}`. `langgraph_harness.py` calls it per-invoke inside `_resolve_model_for_invoke`, attaching `model.profile = {"max_input_tokens": 131072}` when the registry knows the model. With the profile, deepagents' `compute_summarization_defaults` switches from the no-profile fallback `("tokens", 170000)` to `("fraction", 0.85)` — summarisation fires at ~111k tokens, well inside qwen's 131k window. Lazy + failure-tolerant; sentinel strings still pass through for tests.
  - 92 tests passing, 0 failures across `test_backend_config.py`, `test_model_config.py`, `test_langgraph_harness.py`.
  - **Deferred (documented in `model_config.py` docstring)**: belt-and-braces message-count trigger (`[("fraction", 0.85), ("messages", 50)]`) — would need overriding `create_summarization_middleware`'s SDK auto-default factory, a bigger structural change. Wait for empirical validation of SUMM-ROOT + MODEL-PROFILE before adding.
- **Follow-up task (filed but superseded)**: [TASK-FIX-CHO01](../../../tasks/completed/2026-06/TASK-FIX-CHO01-deepagents-conversation-history-offload-path.md) filed 2026-06-04 as GuardKit-side tracking. Superseded by the 002R-SUMM-ROOT + 002R-MODEL-PROFILE pair (better factoring — selector.py-keeps-the-bridge invariant preserved). Moved to completed/ 2026-06-05.
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
- **Follow-up task**: [TASK-FIX-LGFM2](../../../tasks/completed/2026-06/TASK-FIX-LGFM2-inline-implement-model-threading.md) filed 2026-06-04, **landed 2026-06-05** (`model=self._model_name` threaded; 2 regression tests in `TestTaskWorkHarnessMigration`). HMIG-010 remains blocked on F11 (CHO01) before run 3 can fire.

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
