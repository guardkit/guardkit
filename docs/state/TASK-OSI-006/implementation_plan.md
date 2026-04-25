# TASK-OSI-006 — Implementation Plan (LIGHT mode)

## Insertion location
- File: `guardkit/orchestrator/autobuild.py`
- Method: `AutoBuildOrchestrator._execute_turn` (def at line 2308; sync, not async)
- Insert: between line 2623 (end of "Cumulative requirements_addressed" log) and line 2625 (cancellation check before Coach)
- Rationale: Player has fully returned, command-execution and synthetic-report processing finished, before Coach phase; matches the data-flow diagram in `tasks/backlog/orchestrator-side-specialist-invocation/IMPLEMENTATION-GUIDE.md` §3.1.

## Block structure (real method/var names)

```python
# ===== Orchestrator-side Phase 4/5 (FEAT-AB59 / TASK-OSI-006) =====
# Replaces the Player's discretionary specialist invocations with
# orchestrator-driven calls. Skipped for direct-mode tasks.
if player_result.success and self._agent_invoker is not None:
    # AC#8 defensive: import inside the block so a missing module
    # in some hypothetical future packaging error skips Phase 4/5
    # rather than breaking the turn.
    try:
        from guardkit.orchestrator import specialist_invocations as _si
    except ImportError:
        _si = None
        logger.warning(
            f"[{task_id}] specialist_invocations import failed; "
            "skipping orchestrator-side Phase 4/5"
        )

    if _si is not None:
        impl_mode = self._agent_invoker._get_implementation_mode(task_id)

        # Coarse budget guard (AC#6) — if the start-of-turn budget was
        # already below MIN_TURN_BUDGET_SECONDS, skip specialists and
        # write a `specialist_skipped` phase_4 block so the gate still
        # produces a well-formed validation block.
        budget_ok = (
            remaining_budget is None
            or remaining_budget >= MIN_TURN_BUDGET_SECONDS
        )

        if impl_mode == "direct":
            logger.info(
                f"[{task_id}] Skipping orchestrator Phase 4/5 (direct mode)"
            )
        elif not budget_ok:
            logger.info(
                f"[{task_id}] Skipping orchestrator Phase 4/5 "
                f"(remaining_budget={remaining_budget}s < "
                f"{MIN_TURN_BUDGET_SECONDS}s)"
            )
            specialist_results_path = (
                Path(worktree.path) / ".guardkit" / "autobuild" / task_id
                / "specialist_results.json"
            )
            _si._merge_specialist_block(
                specialist_results_path,
                "phase_4",
                {
                    "status": "skipped",
                    "duration_seconds": 0.0,
                    "error": "specialist_skipped: budget exhausted",
                    **_si._PHASE_4_AGENT_FIELD_DEFAULTS,
                },
            )
            try:
                self._agent_invoker._inject_specialist_records_into_task_work_results(
                    task_id
                )
            except Exception as exc:
                logger.warning(
                    f"[{task_id}] _inject_specialist_records_into_task_work_results "
                    f"raised after budget-skip: {exc}"
                )
        else:
            # Reuse / create a loop just like _invoke_player_safely does.
            try:
                _loop = asyncio.get_event_loop()
                if _loop.is_closed():
                    raise RuntimeError("loop closed")
            except RuntimeError:
                _loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_loop)

            # Phase 4: test-orchestrator
            phase4_result = _loop.run_until_complete(
                _si.invoke_test_orchestrator(
                    worktree_path=worktree.path,
                    task_id=task_id,
                    sdk_timeout=self.sdk_timeout,
                    agent_invoker=self._agent_invoker,
                    cancellation_event=self._cancellation_event,
                    turn=turn,
                )
            )

            # Phase 5: code-reviewer (only if Phase 4 passed)
            if phase4_result.status == "passed":
                _loop.run_until_complete(
                    _si.invoke_code_reviewer(
                        worktree_path=worktree.path,
                        task_id=task_id,
                        phase4_result=phase4_result,
                        sdk_timeout=self.sdk_timeout,
                        agent_invoker=self._agent_invoker,
                        cancellation_event=self._cancellation_event,
                        turn=turn,
                    )
                )
            else:
                # Phase 4 failed/skipped — write a phase_5 skipped block.
                specialist_results_path = (
                    Path(worktree.path) / ".guardkit" / "autobuild" / task_id
                    / "specialist_results.json"
                )
                _si._merge_specialist_block(
                    specialist_results_path,
                    "phase_5",
                    {
                        "status": "skipped",
                        "duration_seconds": 0.0,
                        "error": f"phase_4 status={phase4_result.status}",
                        **_si._PHASE_5_AGENT_FIELD_DEFAULTS,
                    },
                )

            # Gate-credit injection (TASK-OSI-002)
            try:
                self._agent_invoker._inject_specialist_records_into_task_work_results(
                    task_id
                )
            except Exception as exc:
                logger.warning(
                    f"[{task_id}] _inject_specialist_records_into_task_work_results "
                    f"raised: {exc}"
                )
# ===== End orchestrator-side Phase 4/5 =====
```

Confirmed signatures:
- `invoke_test_orchestrator(worktree_path, task_id, sdk_timeout, agent_invoker, cancellation_event=None, *, turn=None)` — async, never raises (specialist_invocations.py:608)
- `invoke_code_reviewer(worktree_path, task_id, phase4_result, sdk_timeout, agent_invoker, cancellation_event=None, *, turn=None)` — async; raises ValueError if `phase4_result.status != "passed"` (specialist_invocations.py:686). The wire-up only calls it when status == "passed".
- `AgentInvoker._get_implementation_mode(self, task_id) -> str` — returns "direct" | "task-work" (agent_invoker.py:3649)
- `AgentInvoker._inject_specialist_records_into_task_work_results(self, task_id) -> Optional[Path]` — single arg (agent_invoker.py:5672); never raises but the call site wraps defensively
- `_merge_specialist_block` and `_PHASE_4_AGENT_FIELD_DEFAULTS` / `_PHASE_5_AGENT_FIELD_DEFAULTS` are module-level helpers in specialist_invocations.py.

`asyncio` is already imported at module top of autobuild.py; `Path` is already imported (used elsewhere in same method).

## Persistence decision
Use the existing parallel file `.guardkit/autobuild/{task_id}/specialist_results.json` (already written by the runners). DO NOT extend `TurnRecord`. This matches `task_work_results.json`'s per-task semantics; the merge helper is idempotent and the gate consumes only the latest turn.

## Files to modify
| File | Change | LOC |
|---|---|---|
| `guardkit/orchestrator/autobuild.py` | Insert ~80-line block in `_execute_turn` between L2623 and L2625 | +85 / -0 |
| `tasks/in_progress/TASK-OSI-006-turn-loop-wiring.md` | Tick AC checkboxes, record persistence decision in Notes | +5 / -5 |

No changes to `agent_invoker.py` or `specialist_invocations.py`.

## Test impact
Existing `tests/unit/test_autobuild_*.py` and `tests/integration/test_autobuild_*.py` should remain green. The new block short-circuits when `self._agent_invoker is None` (some unit-test fixtures construct an orchestrator without one) AND when `_get_implementation_mode` returns "direct". If a test fixture mocks `_agent_invoker` but does not stub `_get_implementation_mode`, that test may exercise the new block — guard by either making the test set the mock's `_get_implementation_mode.return_value = "direct"` OR ensuring the test's task fixture has `implementation_mode: direct` in frontmatter. Behavioural assertions for the new block live in TASK-OSI-007 (stub-SDK harness), not here.

## Risks
- `specialist_invocations` ImportError → handled by local `try/except ImportError`; logs and skips block.
- `_inject_specialist_records_into_task_work_results` raises → wrapped in try/except; logs and falls through to existing gate state.
- Cancellation mid-Phase-4 → `run_specialist` honours `cancellation_event`, returns `status="failed"` with cleanup; wire-up takes the "skip phase_5, write skipped block" path; subsequent cancellation check at L2627 still fires.
- `asyncio.get_event_loop()` deprecation → reuse the same pattern as `_invoke_player_safely` (line 4399-4406) for consistency.

## Lint/format
Use `python3 -m py_compile` on changed Python files (no ruff/black configured at project root). Run focused tests:
```
pytest tests/unit/test_autobuild_orchestrator.py tests/unit/test_autobuild_timeout_budget.py -x
```
