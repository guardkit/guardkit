# Review Report: TASK-REV-F3D7 — forge-run-3 autobuild failure after stall-resilience fixes

- **Mode**: Architectural Review
- **Depth**: Deep
- **Transcript under review**: [forge-run-3.md](./forge-run-3.md) (1272 lines)
- **Implementation guide**: [autobuild-sdk-stall-resilience/IMPLEMENTATION-GUIDE.md](../../tasks/backlog/autobuild-sdk-stall-resilience/IMPLEMENTATION-GUIDE.md)
- **Date**: 2026-04-24

## Executive Summary

The feature failed because **one critical fix — `TASK-FIX-7A08` (Player system-prompt
mandates Task-tool invocation) — was promised by the `coach_agent_invocations_stall`
classifier's remediation text but never filed as a subtask in the IMPLEMENTATION-GUIDE**.

All seven shipped subtasks (`TASK-FIX-7A01` through `TASK-FIX-7A07`, plus `TASK-DOC-7A06`)
landed correctly and fire as designed. The classifier, enriched feedback, bootstrap
gate, venv wiring, and SDK pin all work. What they *don't* fix — and were never
designed to fix — is the *behaviour* the classifier names: the Player completes
`task-work` mode tasks inline instead of invoking `test-orchestrator`,
`code-reviewer`, and the stack-specific Phase-3 specialist via the Task tool.

This review also identified **one scope gap** (7A03's defensive stream handling does
not cover the Coach independent-test SDK path), one **policy question**
(auto-downgrade on repeated identical missing-phases rejections), and one **cosmetic
gap** (`context_pollution_stall_no_checkpoint` mechanically co-fires every time
`coach_agent_invocations_stall` is primary, adding diagnostic noise).

**Root cause classification**: **scope** (7A07 classifies the failure and names
7A08 as the fix; 7A08 was never filed). The feature cannot ship without 7A08.

---

## 1. Timeline (cited)

| Time (UTC) | Line | Event |
|---|---|---|
| 17:05:27 | 2-5 | Orchestrator starts; feature FEAT-FORGE-002, 11 tasks, 5 waves, max_turns=30 |
| — | 56-62 | `pip install -e .` fails — `nats-core<0.3,>=0.2.0` unavailable (Requires-Python >=3.13 mismatch) |
| — | 87 | `Environment bootstrap partial: 0/1 succeeded` — run continues (default `bootstrap_failure_mode: warn`) |
| — | 88-90 | Coach pytest interpreter wired to bootstrap venv (TASK-FIX-7A05 ✅ delivered) |
| 17:05:27 | 100-101 | Wave 1 start: NFI-001 + NFI-002 (both `implementation_mode: direct`) |
| 17:08:56 | 218-223 | First SDK stream failure: `claude_agent_sdk._internal.query: Fatal error in message reader: Command failed with exit code 1` — NOT caught by 7A03 (Coach independent-test SDK path, not `_invoke_with_role`) |
| — | 224-229 | Subprocess-pytest fallback; `classification=collection_error`; **conditional approval** fires (`docker_available=True, all_gates_passed=True`) |
| 17:10:27 | 345 | Wave 1 PASSED 2/2 (direct-mode tasks not affected by agent-invocations gate) |
| 17:10:29 | 356-361 | Wave 2 start: NFI-003, NFI-006, NFI-007 (all `implementation_mode: task-work`) |
| 17:19:37 | 604-606 | NFI-003 turn 1: 47 tool uses, inline completion; BDD skipped (pytest-bdd not importable); doc-level warning (8 files > 2 max) |
| 17:19:38 | 664 | **Coach agent-invocations gate rejects NFI-003: missing phases 4, 5** (TASK-FIX-7A07 ✅ fires correctly) |
| 17:19:38 | 667 | Enriched feedback: `"1 of 3 required agent invocations"` (TASK-FIX-7A07 ✅) |
| 17:19:38 | 737 | NFI-006 conditional approval (same collection_error + docker path) |
| 17:20:41 | 817 | Coach rejects NFI-007 turn 1: missing phases 4, 5 |
| 17:22:41 | 897 | Turn 2 NFI-003: rejection repeats (missing phases 4, 5) |
| 17:26:15 | 1062 | Turn 3 NFI-003: third identical rejection |
| 17:26:15 | 1075-1077 | **Context-pollution stall detected + no passing checkpoint → `unrecoverable_stall`** |
| 17:26:15 | 1095-1111 | Summary block emits `coach_agent_invocations_stall` as primary with hardcoded "`see TASK-FIX-7A08`" advice text, co-fired `context_pollution_stall_no_checkpoint` |
| 17:26:58 | 1156 | Turn 3 NFI-007 rejection (missing phases 3, 5 — stack specialist + code-reviewer) |
| 17:26:58 | 1171-1205 | NFI-007 same unrecoverable_stall outcome |
| 17:26:58 | 1222-1223 | Wave 2 failed 1/3; `stop_on_failure=True` halts execution |
| — | 1226-1270 | Feature FAILED, 3/11 tasks completed, review summary written |

---

## 2. Subtask Gate Assessment (7A01 – 7A07)

| Subtask | What it shipped | Fired in this run? | Verdict |
|---|---|---|---|
| **TASK-FIX-7A01** — Pin SDK + version log | `claude_agent_sdk` version log at startup; pin in pyproject/requirements | ✅ Line 110: `claude-agent-sdk version: 0.1.66` | **fired correctly** |
| **TASK-FIX-7A02** — Player-invocation-stall classification | Distinct `player_invocation_stall` decision label | Not exercised — this run's failure was Coach-side, not Player-invocation timeout | **not exercised by this scenario** |
| **TASK-FIX-7A03** — Defensive SDK message handling | Per-message try/except in `_invoke_with_role`; `error_class` field on `AgentInvocationError` | Lines 218-223, 288-293, 727-729 show the protected exception class occurring *on a path 7A03 does not cover* (Coach independent-test SDK path at `coach_validator.py:1375`, not `_invoke_with_role`) | **fired correctly in its scope; scope gap** |
| **TASK-FIX-7A04** — Bootstrap hard-fail gate | `_maybe_hardfail_bootstrap` + requires-python pre-check, both gated by `bootstrap_failure_mode`; default `"warn"` | Lines 59-87: both pre-check and post-install gate ran in default `warn` mode, logged, fell through. Code worked; defaults preserved current behaviour as AC specified (`TASK-FIX-7A04.md:46-47`) | **fired correctly (design — default is `warn`)** |
| **TASK-FIX-7A05** — Wire venv to Coach pytest | Coach interpreter selected from `BootstrapResult.venv_python` | ✅ Lines 88-90, 352: `Coach pytest interpreter set from bootstrap venv: .../venv/bin/python` | **fired correctly** |
| **TASK-DOC-7A06** — Runbook + graph seed | `docs/guides/autobuild-instrumentation-guide.md` + Graphiti seed | Not directly exercised; meta-artefact | **fired correctly** (doc only) |
| **TASK-FIX-7A07** — `coach_agent_invocations_stall` classifier | New stall sub-type; enriched feedback naming Phase 3/4/5 specialists; summary-renderer branch with remediation advice | ✅ Lines 664, 817, 897, 1062, 1156 (gate fires); 1098-1109 (summary block with phase/specialist block). Matches all 8 ACs | **fired correctly** |

---

## 3. Hypothesis Classes — Confirmed / Refuted

### H1 — Missing subtask: `TASK-FIX-7A08` — **CONFIRMED** (root cause)

- `TASK-FIX-7A08` is referenced as a hardcoded string literal at:
  - [guardkit/orchestrator/autobuild.py:5078](../../guardkit/orchestrator/autobuild.py#L5078): `f"(see TASK-FIX-7A08). Required specialists:\n"`
  - [guardkit/orchestrator/feature_orchestrator.py:1616](../../guardkit/orchestrator/feature_orchestrator.py#L1616): `"Task-tool invocation for the missing phases (TASK-FIX-7A08), "`
- The task was coined in `TASK-FIX-7A07.md:76,241,281` and `TASK-REV-JMBP-jarvis-autobuild-mbp-review.md:359,375` as a proposed follow-on, **never filed**. Verified: `tasks/completed/TASK-FIX-7A0*/` contains `01/02/03/04/05/07` plus `TASK-DOC-7A06` and `TASK-FIX-7A3E`. No 7A08 anywhere in the tree.
- The Player execution protocol prompts do not mandate Task-tool invocation:
  - `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` (full) — zero matches for `"subagent_type"`, `"test-orchestrator"`, `"code-reviewer"`, `"MUST invoke"`, `"Task tool"`
  - Same for `_medium.md` and `_slim.md`
  - `_build_inline_implement_protocol` at [agent_invoker.py:4479-4644](../../guardkit/orchestrator/agent_invoker.py#L4479) — narrative phase descriptions only
- Phase 4 in the full protocol literally instructs the Player to `pytest tests/ -v` inline ([autobuild_execution_protocol.md:146-188](../../guardkit/orchestrator/prompts/autobuild_execution_protocol.md#L146)), inviting exactly the behaviour the Coach gate rejects.
- Only `phase_specialists.py` names specialists — and it is used **only** by Coach *feedback* (post-violation remediation text), never in the Player's initial prompt ([coach_validator.py:713](../../guardkit/orchestrator/quality_gates/coach_validator.py#L713)).
- `Task` *is* in `allowed_tools` ([agent_invoker.py:4745](../../guardkit/orchestrator/agent_invoker.py#L4745)). The capability exists; the direction does not.

**Classification**: This is a **specification defect in the Player prompt**. Same shape as the `anti-stub` meta-pattern captured in `.claude/rules/anti-stub.md`. **Code-level**, not config, not scope.

### H2 — Bootstrap gate configuration drift — **REFUTED** (design, not defect)

- TASK-FIX-7A04 landed correctly. `_maybe_hardfail_bootstrap` at [feature_orchestrator.py:1211-1247](../../guardkit/orchestrator/feature_orchestrator.py#L1211) raises `FeatureOrchestrationError` when `mode=="block"` AND `installs_failed == installs_attempted` AND essential stack. Re-raised at `:1202-1205`.
- Requires-python pre-check is wired *before* `pip install` at [feature_orchestrator.py:1157](../../guardkit/orchestrator/feature_orchestrator.py#L1157), implemented at `:1249-1300`. In `warn` mode (default), it logs and falls through — as designed.
- Default `bootstrap_failure_mode: "warn"` at [feature_orchestrator.py:224](../../guardkit/orchestrator/feature_orchestrator.py#L224), CLI flag defaults to `None` at [cli/autobuild.py:644-655](../../guardkit/cli/autobuild.py#L644). AC on `TASK-FIX-7A04.md:46-47` explicitly mandated this default "to preserve existing behaviour".
- The run proceeded exactly because the operator did not pass `--bootstrap-failure-mode block` and no `.guardkit/config.yaml` entry set it. **`BootstrapResult.success = False`** (lines 59-87 — `installs_failed=1`, `installs_attempted=1`, `overall_success = installs_failed == 0`). The gate was asked the right question and got the correct answer.

**Classification**: **config default** (not code). Optionally worth revisiting as a policy decision — filed below as optional `TASK-CFG-7A0C`.

### H3 — SDK stream handling completeness — **CONFIRMED PARTIAL** (scope)

- 7A03's defensive stream handling lives in `_invoke_with_role` at [agent_invoker.py:2257-2321](../../guardkit/orchestrator/agent_invoker.py#L2257) and wraps outer `Exception` with `error_class=type(e).__name__` at `:2413-2423`.
- The Coach independent-test path uses a **separate SDK call** at [coach_validator.py:1375](../../guardkit/orchestrator/quality_gates/coach_validator.py#L1375) (`async for message in query(...)`), with no per-message try/except. Its only safety net is a catch-all `except ... as e: ... raise` at `:1474`, with the opaque fallback log at `:1732-1736` (`"SDK test execution failed, falling back to subprocess: {e}"`).
- The exit-code-1 exception is a `ProcessError` from the bundled CLI subprocess — raised *before or between* messages, not inside a message. 7A03's per-message `except (MessageParseError, ValueError)` could not have caught it even if applied to this path.
- Net: **7A03 never scoped the Coach independent-test path**, and the failure shape is a transport-level pre-message event, not a stream parse error. Two orthogonal gaps, both in H3's family.

**Classification**: **scope**. 7A03 didn't fail; it wasn't pointed at this path.

### H4 — Anti-fraud vs direct-mode policy gap — **CONFIRMED** (policy)

- `implementation_mode` appears in `autobuild.py` *only* as human-facing advice text at [autobuild.py:5080](../../guardkit/orchestrator/autobuild.py#L5080); similarly at [feature_orchestrator.py:1617](../../guardkit/orchestrator/feature_orchestrator.py#L1617).
- No branch reads consecutive-rejection counters and mutates `implementation_mode` or retries. After 3 identical rejections, the orchestrator exits — it does not try `direct` mode.
- Additionally, `context_pollution_stall_no_checkpoint` mechanically co-fires every time `coach_agent_invocations_stall` is primary, because the checkpoint-passing criterion is `tests_passed==True` which is always `False` while the gate rejects. See [worktree_checkpoints.py:475-523](../../guardkit/orchestrator/worktree_checkpoints.py#L475) and classifier ordering at [autobuild.py:5020-5107](../../guardkit/orchestrator/autobuild.py#L5020).

**Classification**: **policy gap** (auto-downgrade) + **cosmetic noise** (co-fire). Optional follow-up, not load-bearing for the feature shipping.

---

## 4. Feature-Level Verification — Verdict

From IMPLEMENTATION-GUIDE.md § "Feature-Level Verification" (lines 129-146):

| # | Check | Ran? | Evidence |
|---|---|---|---|
| 1 | **Transcript replay pytest** — replay forge-run-1/2 into classifier and assert `player_invocation_stall` is emitted | ❌ No evidence in this run | Not a runtime check; would live in `tests/orchestrator/test_stall_classification.py`. No output line in transcript references this. |
| 2 | **Live GB10 verification** — `guardkit autobuild feature FEAT-FORGE-002 --verbose` | ✅ This run IS that verification | Line 1 invocation matches. Sub-checks: |
| 2a | No `Unknown message type: rate_limit_event` emitted | ✅ True — no such line in transcript | (negative evidence) |
| 2b | Player runs with real output, not synthetic | ✅ True for all Player invocations | e.g. line 616: NFI-003 turn 1 "37 files created, 5 modified" |
| 3 | **Macbook regression check** — rerun `FEAT-J002` on macbook | ❌ Out of scope for forge run | |

**Verdict on point 2**: the shipped fixes *are* proven live — the run demonstrates that 7A07's classifier fires, 7A05's venv wiring is live, 7A03's defensive path keeps the orchestrator from crashing. What it **also** demonstrates is that none of the seven subtasks address the *underlying* behaviour on a path that matters for any `task-work` mode task — exactly the class of failure this feature was supposed to close.

---

## 5. Recommendations (ranked)

**Minimum set to actually close the feature**: #1 + #2. **Recommended bundle**: #1 + #2 + #3. The rest are policy/cosmetic and can be filed independently.

### #1 · TASK-FIX-7A08 — Player prompt mandates Task-tool invocation

- **Hypothesis class**: H1 (missing subtask) — **load-bearing**
- **Complexity**: 4
- **Scope**:
  - Amend `guardkit/orchestrator/prompts/autobuild_execution_protocol{,_medium,_slim}.md` to **mandate** `Task(subagent_type="<specialist>")` for Phase 3 (stack specialist from `phase_specialists.py`), Phase 4 (`test-orchestrator`), Phase 5 (`code-reviewer`).
  - Replace inline-bash instructions (`pytest tests/ -v`, `npm test`, etc.) with prose: *"Invoke `test-orchestrator` via the Task tool. Do NOT run pytest inline."*
  - Reflect the change in `_build_inline_implement_protocol` at `agent_invoker.py:4479-4644` as well.
  - Add prompt-rendering unit test asserting literal `subagent_type="test-orchestrator"` appears in the rendered prompt for every non-direct task type.
- **Gate**: replay a minimised fixture derived from forge-run-3 NFI-003/NFI-007 and assert `agent_invocations_validation` reports `3/3 required` on turn 1.
- **Touches**: `guardkit/orchestrator/prompts/*.md`, `guardkit/orchestrator/agent_invoker.py`, `tests/orchestrator/test_player_prompt_mandate.py` (new).
- **Graph reference**: seed `guardkit__project_decisions` with *"Player prompt must mandate, not describe, Task-tool invocation for specialist phases"* — sibling of the existing 7A07 decision node.

### #2 · TASK-FIX-7A09 — Extend 7A03 defensive handling to Coach independent-test SDK path

- **Hypothesis class**: H3 (SDK stream scope gap)
- **Complexity**: 3
- **Scope**:
  - Wrap the `async for message in query(...)` loop at `coach_validator.py:1375` with the same per-message `(MessageParseError, ValueError)` try/except that 7A03 applied to `_invoke_with_role`.
  - Add explicit `ProcessError` / `CLIJSONDecodeError` catch before the bare `Exception` at `:1474`, populating the fallback log with `e.stderr` instead of the opaque `{e}`.
  - Expose the failure classification upstream so the existing classifier framework (7A02/7A07) can differentiate transport-level CLI failures from message-parse failures.
- **Gate**: unit tests mirroring 7A03's — (a) stream that raises `ProcessError` → subprocess fallback log includes `exit_code` and `stderr`; (b) stream with `MessageParseError` → continues and warns, falls through to subprocess only on terminal failure.
- **Touches**: `guardkit/orchestrator/quality_gates/coach_validator.py`, `tests/orchestrator/test_coach_sdk_stream_resilience.py` (new).

### #3 · TASK-FIX-7A0A — Remove dead `TASK-FIX-7A08` string reference (or tie it to 7A08 once filed)

- **Hypothesis class**: H1 (cleanup)
- **Complexity**: 1
- **Scope**: Once `TASK-FIX-7A08` exists, either (a) leave the hardcoded string, now valid, or (b) refactor the advice text to a config/catalog (`messages/stall_remediation.py`) so future task-ID references are resolvable. Preferred: (a) if we file 7A08 promptly; (b) if we expect more stall sub-types to reference tasks by ID.
- **Gate**: lint/grep check in CI asserting every `TASK-FIX-XXXX` or `TASK-REV-XXXX` literal in `autobuild.py` and `feature_orchestrator.py` resolves to an existing task file (simple, cheap test).
- **Touches**: `guardkit/orchestrator/autobuild.py:5078`, `guardkit/orchestrator/feature_orchestrator.py:1616`, `tests/rules/test_no_dead_task_id_references.py` (new).

### #4 · (Optional policy) TASK-POL-7A0B — Decide auto-downgrade policy on repeated identical stall

- **Hypothesis class**: H4
- **Complexity**: 2 (design) + 3–4 (implementation, if approved)
- **Question**: Should the orchestrator auto-downgrade `implementation_mode: task-work → direct` after N (2? 3?) consecutive identical `coach_agent_invocations_stall` rejections with the same `missing_phases` set?
- **Trade-off**: auto-downgrade silently weakens the specialist pipeline, potentially hiding genuine prompt defects (exactly the class 7A08 fixes). No-auto-downgrade wastes N × task_timeout_budget per stall. Current behaviour leans heavily on operator attention.
- **Recommendation**: hold until 7A08 is in; if 7A08 resolves the behaviour, policy question is moot for this class of failure and can be closed as "no action". If 7A08 is partial, revisit.
- **Output**: either a small policy-impl task or a documented ADR under `.claude/rules/graphiti-knowledge-graph.md`.

### #5 · (Optional config) TASK-CFG-7A0C — Tighten bootstrap defaults for forge/CI

- **Hypothesis class**: H2
- **Complexity**: 2 (doc/config only)
- **Scope**: No code change. Decide whether forge profiles should ship with `autobuild.bootstrap.failure_mode: block` in their `.guardkit/config.yaml`, and whether this should be documented as a recommended default in `docs/guides/autobuild-instrumentation-guide.md`.
- **Recommendation**: document the recommendation, do not flip the global default (`warn` protects local iteration).

### #6 · (Optional cosmetic) TASK-FIX-7A0D — Suppress context_pollution co-fire when coach_agent_invocations is primary

- **Hypothesis class**: H4 (cosmetic)
- **Complexity**: 2
- **Scope**: In the classifier at `autobuild.py:5020-5107`, suppress `STALL_CONTEXT_POLLUTION` from the co-fires suffix when the gate-rejection chain *mechanically* prevents any checkpoint from passing. Add a dedicated marker to distinguish "checkpoint-passing is impossible because of upstream gate rejection" from "passing work degenerated over turns".
- **Recommendation**: low priority; current co-fire is not misleading, just noisy.

---

## 6. Code-vs-Config-vs-Scope Attribution

| Finding | Class | Why |
|---|---|---|
| **7A08 missing → Player prompt does not mandate Task-tool invocation** | **code** | Prompt is a source artefact shipped with the package; the fix requires editing `prompts/*.md` and prompt-building code. |
| 7A03 doesn't cover Coach independent-test SDK path | **scope** | 7A03's scope statement was the streaming loop in `_invoke_with_role`. The Coach independent-test path is a structurally separate SDK call; never in 7A03's scope. |
| Bootstrap run proceeded despite install failure | **config** | Code correct; default (`warn`) preserved by explicit AC of 7A04. Config default is the only knob. |
| Auto-downgrade absent | **scope/policy** | No subtask in the original IMPLEMENTATION-GUIDE committed to implementing auto-downgrade; 7A07 classifier outputs advice only. |
| `context_pollution_stall_no_checkpoint` co-fires | **code (cosmetic)** | Mechanical consequence of two independent detectors both lighting up on the same upstream cause. |

---

## 7. Decision Checkpoint

Please choose one:

- **[A]ccept** — Accept findings as-is. Archive this review; file follow-ups later by hand.
- **[I]mplement** — Spawn the recommended remediation set as subtasks. Recommended bundle:
  - Minimum: `TASK-FIX-7A08` + `TASK-FIX-7A09` (2 tasks; closes the feature behaviourally)
  - Recommended: `TASK-FIX-7A08` + `TASK-FIX-7A09` + `TASK-FIX-7A0A` (3 tasks; closes + cleans up dead reference)
  - Full: all six (adds optional policy + config + cosmetic tasks)
- **[R]evise** — Deeper analysis of a specific hypothesis class (e.g. full audit of every `sys.executable` callsite, or a prompt-rendering regression suite across all nine templates).
- **[C]ancel** — This run was non-representative (e.g. GB10 env drift on the day, or nats-core transient from PyPI). Rerun on a clean environment first before filing any remediation.

Recommended: **[I]mplement** with the **recommended bundle** (7A08 + 7A09 + 7A0A, 3 tasks). Rationale:
1. 7A08 is the load-bearing fix — without it the feature cannot ship regardless of environment.
2. 7A09 closes a genuine scope gap that will continue to mask signal on every run.
3. 7A0A is a 1-pt cleanup that prevents future dead references from accumulating.
4. The three optional tasks (#4/#5/#6) are not load-bearing and can be filed independently after 7A08 lands and we confirm whether the policy question is still live.
