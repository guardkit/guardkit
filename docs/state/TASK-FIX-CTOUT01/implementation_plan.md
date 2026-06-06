# TASK-FIX-CTOUT01 — Implementation Plan

**Branch:** `fix/ctout01-coach-cancellation-race`
**Task:** Coach cancellation race in autobuild orchestrator
**Generated:** 2026-06-05
**Fix shape:** Option 2 (harness.cancel() abstraction + keep Layer 4 grace), AC-001 reproducer first

---

## 0. Investigation findings that change the plan shape

Three discoveries during planning-phase code exploration that the parent investigation did not surface:

1. **Layer 4's candidate-dirs walk is structurally correct for worktree-backed runs.** `_autobuild_candidate_dirs` (`feature_orchestrator.py:3131-3163`) iterates `self.repo_root/.guardkit/worktrees/*/.guardkit/autobuild/<task_id>` for EVERY worktree dir. For run-3 (FEAT-AOF), Coach writes via `worktree.path/.guardkit/autobuild/<task_id>/coach_turn_N.json` (`autobuild.py:5706-5708`). These match. **Hypothesis (a) "wrong directory" is therefore unlikely under the simple case.** The remaining risk is a **path-canonicalisation mismatch** — e.g., the worktree manager constructs paths via `path.resolve()` while `self.repo_root` was constructed differently, so the candidate dir doesn't equal Coach's actual write dir. AC-001 must verify this with `os.path.realpath` parity.

2. **Layer 4's `_check_late_approval` swallows EVERY exception silently at DEBUG level** (`feature_orchestrator.py:3237-3241`). This is the named "silent-swallow" bonus from the brief — but it is even worse than the brief states: `json.JSONDecodeError`, `OSError` from a transient stat, `AttributeError` from a malformed coach JSON without `decision` key, even `KeyError` if `.get` is replaced by `[]` in some refactor — all are caught and demoted to DEBUG. **Hypothesis (b) is therefore the more likely cause** and lines up with the "INFO-level log capture would have hidden it" observation. AC-001 must keep this as a primary suspect.

3. **`worktree.path` may resolve through a parent symlink under macOS or under nested canary runs.** The repo contains both `.guardkit/worktrees/FEAT-AOF/` AND `.guardkit/canary-worktrees/TASK-GLI-004/.guardkit/worktrees/TASK-GLI-004/...`. The `_autobuild_candidate_dirs` walk does NOT look inside `canary-worktrees` — only `worktrees`. If a future canary run hit the race, Layer 4 would silently miss. Not in scope for CTOUT01, but worth a follow-up issue.

These findings move the prior probability mass: **hypothesis (b) "swallowed exception" ≫ hypothesis (a) "wrong directory."** The fix plan is sequenced to make the (b) path the first thing to land (low-risk, narrow blast radius), then validate via AC-001 whether (a) also surfaces.

---

## 1. Step-by-step file changes (execution order)

Sequencing is structured so the test suite is green after each step. AC-001 reproducer lands FIRST per the operator brief (non-negotiable). Layer 4 fix lands SECOND, in shape (b) by default. Harness `cancel()` abstraction lands LAST.

### Step 1 — AC-001 reproducer (NEW test files)

**1a. `tests/orchestrator/test_ctout01_cancellation_race_repro.py`** (NEW, ~250 LOC)

Three scenarios:

- `test_langgraph_coach_completes_within_grace_reclassifies_as_approved_late`: builds a `FeatureOrchestrator` with `task_timeout=2`, monkeypatches `_execute_task` to (a) sleep 3s, (b) write a `coach_turn_2.json` with `decision="approve"` ~1s after start (i.e., before `task_timeout`, but the sleep continues so `asyncio.wait_for` raises `TimeoutError`). The async invocation surface mirrors `test_timeout_with_late_approval_reclassifies_as_approved_late` (test_feature_orchestrator.py:3941-4006) — that test is the structural template; the new test uses it almost verbatim but with the timing flipped so the Coach write happens **after** `time.time()` (positive `mtime_offset_s`), proving the |delta| absolute-value branch is honoured. **This is the green-on-current-main asserting the existing path WORKS when the Coach write actually happens.** It establishes the baseline.
- `test_langgraph_coach_completes_within_grace_but_layer4_silently_swallows_returns_timeout`: builds the same orchestrator, writes a valid `coach_turn_2.json` with `decision="approve"`, then monkeypatches `_latest_coach_turn_path` to raise `OSError("simulated stat failure")` so `_check_late_approval` hits the bare `except Exception` clause at line 3237. **Expected on current main:** result is `FAILED/timeout` with NO `APPROVED_LATE` log line (silent swallow). **Expected after the line-3237 fix:** the same result for the data, BUT a WARNING log line surfaces the exception. This test FAILS on current main (no WARNING) and PASSES after the line-3237 change — proving (b) was invisible.
- `test_langgraph_coach_decision_key_missing_returns_none_with_warning`: writes `{"NOTdecision": "approve"}` (missing `decision` key). Current behaviour: `dict.get("decision")` returns None, no warning. This test asserts the WARNING upgrade does NOT spam logs for a legitimate None — i.e., the upgrade must only fire on actual exceptions, not on the None return path.

**1b. `tests/orchestrator/test_ctout01_path_canonicalisation_repro.py`** (NEW, ~120 LOC)

Three scenarios specifically targeting hypothesis (a):

- `test_check_late_approval_finds_coach_when_worktree_path_resolves_via_symlink`: creates a symlink farm where `repo_root` points to a real path but the worktree was written under a symlink-resolved path. Asserts the candidate-dirs walk still finds the file via `Path.resolve()` parity. Currently NO `resolve()` normalisation is done. If this test FAILS, hypothesis (a) is real and needs a separate fix.
- `test_check_late_approval_finds_coach_when_repo_root_uses_realpath`: same idea but the reverse direction (`repo_root` is a symlink, `worktree.path` is canonical).
- `test_check_late_approval_skips_nonmatching_worktree_dirs`: regression — irrelevant `worktrees/SOME_OTHER_TASK/.guardkit/autobuild/TASK-FIX-GD02/` does NOT exist, so iteration is benign. Just ensures the walk doesn't accidentally pick up cross-task files.

**Test infrastructure already present and reusable:**
- `TestLateApprovalReconciliation._write_coach_turn` / `_write_coach_turn_in_worktree` / `_write_turn_state` helpers at `tests/unit/test_feature_orchestrator.py:3642-3697` are direct reuse candidates.
- `test_timeout_with_late_approval_reclassifies_as_approved_late` (line 3941) is the structural template for the async-gather + late-approval flow.
- `mock_worktree`, `mock_worktree_manager`, `temp_repo`, `parallel_feature` fixtures (used at line 3941) provide all the orchestrator scaffolding needed.
- `tests/orchestrator/test_agent_invoker_langgraph.py` provides `FakeMessagesListChatModel` stub harness pattern for any future LangGraph-level test, though AC-001 itself works at the feature_orchestrator layer (the failure is in the cancellation contract, not in DeepAgents).

**Coverage focus:** entirely on `feature_orchestrator._check_late_approval`, `_latest_coach_turn_path`, `_autobuild_candidate_dirs`, and the `TimeoutError → APPROVED_LATE` branch at line 2402-2473.

**Run AC-001:** `pytest tests/orchestrator/test_ctout01_cancellation_race_repro.py -v` — both reproducer tests MUST run on current main and the silent-swallow one MUST be a clear demonstration of the bug (failing or showing the missing WARNING).

---

### Step 2 — Layer 4 silent-swallow upgrade (`feature_orchestrator.py:3237-3241`)

**File:** `guardkit/orchestrator/feature_orchestrator.py`
**LOC delta:** +4 / -3 (net +1)
**Risk:** Negligible — already returns None on every exception path, only the log level changes plus `exc_info`.

```python
# Before (lines 3237-3241):
except Exception as exc:
    logger.debug(
        f"[{task_id}] _check_late_approval skipped: {exc}"
    )
    return None

# After:
except Exception as exc:
    # TASK-FIX-CTOUT01: Promote from DEBUG to WARNING with exc_info.
    # Silent swallowing here is how Layer 4 failed invisibly in run-3
    # (TASK-HMIG-010 run 3, TASK-FIX-GD02 wave summary divergence).
    logger.warning(
        f"[{task_id}] _check_late_approval failed: {exc}",
        exc_info=exc,
    )
    return None
```

**Blast-radius decision:** only the **bare-`Exception`** swallow at line 3237 is upgraded. The narrower `OSError`-only swallows in the file-walk helpers (`feature_orchestrator.py:3159-3162`, `:3180-3183`, `:3188-3191`) stay DEBUG because they're legitimate "file not there" cases. This keeps logs quiet on the common case while making the bookkeeping failure mode loud.

**Tests:** Step 1's `test_langgraph_coach_completes_within_grace_but_layer4_silently_swallows_returns_timeout` flips from FAIL to PASS. Add one new test:

- `test_check_late_approval_warns_with_exc_info_on_exception` in the existing `TestLateApprovalReconciliation` class — patches `_latest_coach_turn_path` to raise, asserts `caplog.records[-1].levelno == logging.WARNING` and `caplog.records[-1].exc_info is not None`.

---

### Step 3 — Layer 4 path-canonicalisation fix (CONDITIONAL on AC-001 result)

**Only execute if Step 1b's symlink tests FAIL** — i.e., if hypothesis (a) is confirmed empirically.

**File:** `guardkit/orchestrator/feature_orchestrator.py`
**Target function:** `_autobuild_candidate_dirs` (lines 3131-3163)
**LOC delta:** +6 / -2 (net +4)
**Risk:** Low — adds `.resolve()` normalisation; existing tests that build paths under `tmp_path` already use canonical paths.

```python
candidates: list[Path] = [
    (self.repo_root / ".guardkit" / "autobuild" / task_id).resolve(strict=False),
]
worktrees_root = (self.repo_root / ".guardkit" / "worktrees").resolve(strict=False)
if worktrees_root.exists():
    try:
        for wt_dir in worktrees_root.iterdir():
            if not wt_dir.is_dir():
                continue
            candidates.append(
                (wt_dir / ".guardkit" / "autobuild" / task_id).resolve(strict=False)
            )
    except OSError as exc:
        ...
return candidates
```

**Tests:** Step 1b's three tests flip from FAIL to PASS. Existing `test_check_late_approval_finds_coach_in_worktree_autobuild` (line 3819) and `test_check_late_approval_prefers_latest_across_candidate_dirs` (line 3847) must still pass.

**If Step 1b's tests PASS on current main:** skip Step 3 entirely. Document in the AC-001 evidence section that hypothesis (a) is empirically ruled out, and move straight to Step 4.

---

### Step 4 — `HarnessAdapter.cancel()` abstraction interface

**File:** `guardkit/orchestrator/harness/adapter.py`
**LOC delta:** +35 (one new method + docstring)
**Risk:** Low — interface-only addition; non-abstract default delegates to no-op so existing subclasses (test fakes) don't break.

```python
async def cancel(self) -> None:
    """Request termination of any in-flight :meth:`invoke` call.

    Contract: an in-flight ``invoke(...)`` MUST honour cancellation
    within 30s (CTOUT01_CANCEL_DEADLINE_S, env-overridable via
    GUARDKIT_HARNESS_CANCEL_DEADLINE), even if a mid-call LLM response
    is pending. The default implementation is a no-op; concrete
    harnesses override.

    Called from :meth:`AgentInvoker._cancel_monitor` when the
    orchestrator's ``cancellation_event`` (TASK-ASF-007 / TASK-ABFIX-006)
    fires during a Coach or Player invocation.

    See ``.claude/rules/harness-cancellation-contract.md`` for the
    full multi-layer cancellation taxonomy.
    """
    return None
```

**Tests:** `tests/orchestrator/harness/test_adapter_interface.py` gains `test_cancel_default_is_noop_on_abstract_base`.

---

### Step 5 — `ClaudeSDKHarness.cancel()` implementation

**File:** `guardkit/orchestrator/harness/sdk_harness.py`
**LOC delta:** +25 (one method)
**Risk:** Low.

```python
async def cancel(self) -> None:
    """SDK-side cancel: close the active query() generator + drop session.

    Existing SIGTERM-to-subprocess path
    (:meth:`AgentInvoker._kill_child_claude_processes`) continues to
    own OS-level escalation; this method handles the in-Python
    cooperative side so the generator no longer yields after cancel.
    """
    if self._active_gen is not None:
        gen, self._active_gen = self._active_gen, None
        with suppress(Exception):
            try:
                async with asyncio.timeout(5):
                    await gen.aclose()
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
```

**Tests:** `tests/orchestrator/harness/test_sdk_harness.py` gains `test_cancel_closes_active_generator_under_timeout` and `test_cancel_is_noop_when_no_active_invoke`.

---

### Step 6 — `LangGraphHarness.cancel()` implementation (cross-repo)

**File:** `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`
**LOC delta:** +40
**Risk:** **Medium** — cross-repo seam.

```python
async def invoke(self, ...):
    ...
    self._ainvoke_task = asyncio.create_task(agent.ainvoke(input_data))
    try:
        result = await self._ainvoke_task
    except asyncio.CancelledError:
        # TASK-FIX-CTOUT01: re-raise as LangGraphHarnessError so the
        # orchestrator's catch cascade recognises this as a cancel,
        # not an arbitrary failure.
        raise LangGraphHarnessError(
            f"LangGraphHarness: agent.ainvoke cancelled for "
            f"role={role!r} model={self.model!r}"
        ) from None
    finally:
        self._ainvoke_task = None
    ...

async def cancel(self) -> None:
    """LangGraph cancel: propagate asyncio.CancelledError into ainvoke task."""
    task = self._ainvoke_task
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            try:
                async with asyncio.timeout(
                    int(os.environ.get(
                        "GUARDKIT_HARNESS_CANCEL_DEADLINE", "30"))):
                    await task
            except asyncio.TimeoutError:
                logger.warning(
                    "LangGraphHarness.cancel: ainvoke task did not honour "
                    "cancellation within deadline — leaking task to GC."
                )
```

**Critical concern:** the change from `await agent.ainvoke(input_data)` to `asyncio.create_task(...)` + `await self._ainvoke_task` must preserve the exception-translation contract at langgraph_harness.py:296-302. Existing tests in `tests/orchestrator/test_agent_invoker_langgraph.py` (lines 444-571 — `TestLangGraphHarnessErrorOnFailure`) verify the wrap-and-reraise. They must remain green.

**Tests (in guardkitfactory):** `guardkitfactory/tests/harness/test_langgraph_cancel.py` with:
- `test_cancel_propagates_to_ainvoke_task`
- `test_cancel_when_no_active_invoke_is_noop`
- `test_cancel_honours_deadline_env_var`

---

### Step 7 — `AgentInvoker._cancel_monitor` refactor

**File:** `guardkit/orchestrator/agent_invoker.py`
**Target:** lines 2820-2838 (`_cancel_monitor` closure)
**LOC delta:** +12 / -2 (net +10)
**Risk:** **Medium** — `agent_invoker.py` is ~9000 LOC and `_invoke_with_role` is the central agent-execution path.

```python
async def _cancel_monitor() -> None:
    """Poll cancellation event and dispatch harness-aware cancel + SIGTERM."""
    while True:
        await asyncio.sleep(2)
        if self._cancellation_event and self._cancellation_event.is_set():
            logger.info(
                f"TASK-FIX-CTOUT01: Cancellation event detected during "
                f"{agent_type} invocation; calling harness.cancel() "
                f"and terminating any SDK subprocess."
            )
            # New harness-aware path (works for LangGraph + SDK).
            try:
                await harness.cancel()
            except Exception as exc:
                logger.warning(
                    f"TASK-FIX-CTOUT01: harness.cancel() raised "
                    f"{type(exc).__name__}: {exc} — falling through "
                    f"to subprocess kill."
                )
            # Legacy SDK-subprocess path (no-op on LangGraph).
            self._kill_child_claude_processes()
            return
```

**Sequencing constraint:** `harness` is defined ~line 2855 (after the `_cancel_monitor` closure is declared but before `monitor` is started). The closure captures `harness` by name. **The closure must be defined AFTER the `harness = select_harness(...)` line.** Cleanest fix: move the `_cancel_monitor` def + `monitor = asyncio.create_task(...)` BLOCK to just after the `select_harness` call (i.e., relocate from line 2824 to ~line 2876).

**Tests in `tests/unit/test_agent_invoker.py`:**
- `test_cancel_monitor_calls_harness_cancel`
- `test_cancel_monitor_falls_through_to_kill_on_harness_cancel_failure`

---

### Step 8 — Cancellation contract documentation (AC-006)

**File:** `.claude/rules/harness-cancellation-contract.md` (NEW)
**LOC:** ~80
**Risk:** None.

Documents the four-layer cancellation taxonomy:
- **Layer 1:** `asyncio.wait_for` + `asyncio.to_thread` — wrapper-only cancel, thread keeps running.
- **Layer 2:** Cooperative `timeout_event` / `cancellation_event` checkpoints.
- **Layer 3:** `_cancel_monitor` + `harness.cancel()` (NEW). 30s deadline.
- **Layer 4:** `LATE_APPROVAL_GRACE_S` reclassification. 60s window.
- **Conflict resolution:** AC-003 revised wording.

---

### Step 9 — Task file revision (AC-003 wording)

**File:** `tasks/in_progress/autobuild-harness-migration/TASK-FIX-CTOUT01-coach-cancellation-timeout-race.md`
**LOC delta:** +5 / -2 (net +3)
**Risk:** None.

Replace current AC-003 with:
> "Outer cancellation wins UNLESS inner Coach completes within LATE_APPROVAL_GRACE_S of timer fire, in which case the inner approval is honoured as `approved_late` with `success=True`. This preserves the existing LATE_APPROVAL_GRACE_S design (TASK-ATR-003) while ensuring under-grace approvals are no longer silently lost."

---

## 2. Test strategy

### AC-001 reproducer test infrastructure

**Already exists (reuse, do NOT rewrite):**
- `tests/unit/test_feature_orchestrator.py:3631-3937` `TestLateApprovalReconciliation` — full helper toolbox.
- `tests/unit/test_feature_orchestrator.py:3941-4006` `test_timeout_with_late_approval_reclassifies_as_approved_late` — exact structural template.
- `tests/orchestrator/test_agent_invoker_langgraph.py:90-117` `_make_stub_model` / `_make_stub_langgraph_harness`.
- `tests/orchestrator/harness/test_selector.py:151-431` `TestSelectHarnessDispatch`.

### AC-004 cross-substrate regression coverage

`tests/orchestrator/test_ctout01_cross_substrate_cancellation.py` (NEW, ~200 LOC):
- `test_sdk_harness_cancellation_during_coach_produces_consistent_bookkeeping`
- `test_langgraph_harness_cancellation_during_coach_produces_consistent_bookkeeping`
- `test_both_harnesses_honour_late_approval_grace_when_coach_writes_before_cancel_propagates`

### Coverage targets per intensity profile (standard)

- Line coverage: ≥80% across the touched modules.
- Branch coverage: ≥75%.
- Function-level: 100% line/branch on `_check_late_approval`, `_cancel_monitor`, `HarnessAdapter.cancel` + both concrete overrides.

---

## 3. Risks + sequencing

### Blast radius

**Highest-risk: Step 6 (LangGraphHarness cancel).** Cross-repo + converts `await ainvoke` to `create_task + await task` pattern. Exception-translation contract at langgraph_harness.py:296-302 must be preserved.

**Second-highest: Step 7 (agent_invoker `_cancel_monitor`).** `agent_invoker.py` is central; closure-capture sequencing requires moving the def to after `harness = select_harness(...)`.

**Lowest-risk: Steps 1, 2, 4, 8, 9.** Pure additions / log-level upgrade / documentation.

### Right order to land changes

1. **Step 1 (AC-001 reproducer)** — RED test on current main.
2. **Step 2 (line-3237 silent-swallow upgrade)** — RED → GREEN.
3. **Step 9 (AC-003 task-file revision)** — wording-only.
4. **(Conditional) Step 3 (path-canonicalisation)** — only if Step 1b fails.
5. **Step 8 (cancellation contract docs)** — drafted now, finalised after Step 6.
6. **Step 4 (HarnessAdapter.cancel interface)** — additive.
7. **Step 5 (SDK harness cancel)**.
8. **Step 7 (agent_invoker `_cancel_monitor` refactor)** — wires the new contract.
9. **Step 6 (LangGraphHarness cancel)** — cross-repo, lands LAST.

After each step the test suite MUST be green.

### AC-002 "30s" — env-tunable

**Recommend env-tunable**, matching `LATE_APPROVAL_GRACE_S`:
- Constant: `int(os.environ.get("GUARDKIT_HARNESS_CANCEL_DEADLINE", "30"))`
- Documented in cancellation contract rule file (Step 8).

---

## 4. Split recommendation logic

**Split CTOUT01-a out (land independently) IF AND ONLY IF all three conditions hold:**
1. AC-001 Step 1b confirms hypothesis (a) — path canonicalisation issue measurable on current main.
2. The path-canonicalisation fix is < 30 LOC.
3. Step 1b's three tests provide standalone regression coverage independent of the harness `cancel()` changes.

**Do NOT split (land as single CTOUT01) IF:**
- Step 1b shows hypothesis (a) is empirically ruled out.

**Probability assessment:** Hypothesis (b) is more likely. Most-likely path: AC-001 surfaces the silent-swallow bug, hypothesis (a) ruled out, CTOUT01 lands as a single task with Steps 1+2+4+5+6+7+8+9.

---

## 5. Estimate

### Total LOC delta breakdown

| Step | File | LOC delta | Notes |
|------|------|-----------|-------|
| 1a | `tests/orchestrator/test_ctout01_cancellation_race_repro.py` | +250 | NEW |
| 1b | `tests/orchestrator/test_ctout01_path_canonicalisation_repro.py` | +120 | NEW |
| 2 | `feature_orchestrator.py` (line 3237) | +4 / -3 | WARNING upgrade |
| 3 (cond.) | `feature_orchestrator.py` (3147-3158) | +6 / -2 | `.resolve()` |
| 4 | `harness/adapter.py` | +35 | `cancel()` method |
| 4-tests | `tests/orchestrator/harness/test_adapter_interface.py` | +15 | Default-noop |
| 5 | `harness/sdk_harness.py` | +25 | SDK `cancel()` |
| 5-tests | `tests/orchestrator/harness/test_sdk_harness.py` | +60 | 2 tests |
| 6 | `guardkitfactory/.../langgraph_harness.py` | +40 | LG `cancel()` |
| 6-tests | `guardkitfactory/tests/harness/test_langgraph_cancel.py` | +120 | NEW |
| 7 | `agent_invoker.py` (2820-2838) | +12 / -2 | `_cancel_monitor` |
| 7-tests | `tests/unit/test_agent_invoker.py` | +80 | 2 tests |
| 8 | `.claude/rules/harness-cancellation-contract.md` | +80 | NEW docs |
| 9 | task file | +5 / -2 | AC-003 wording |
| AC-004 | `tests/orchestrator/test_ctout01_cross_substrate_cancellation.py` | +200 | NEW |

**Total (no split):** ~+1042 / -7 (~+1035 net). ~+845 tests/docs; ~+190 production code.
**CTOUT01-a only (split):** ~+255. ~+10 production code.

### Duration estimate

| Phase | Effort | Calendar |
|-------|--------|----------|
| Steps 1a + 1b (AC-001 reproducer) | 1.5h | Day 1 AM |
| Step 2 + 9 (silent-swallow + task wording) | 0.5h | Day 1 AM |
| **CTOUT01-a stopping point** | **2h** | **Day 1 lunch** |
| Step 3 (conditional) | 0.5h | Day 1 PM |
| Steps 4 + 5 + 7 | 1.5h | Day 1 PM |
| Step 6 (cross-repo LG cancel) | 1.5h | Day 2 AM |
| Step 8 (docs) | 0.5h | Day 2 AM |
| AC-004 cross-substrate regression | 1h | Day 2 AM |
| Run AC-005 (re-run HMIG-010 wave) | (parallel, separate) | Day 2 PM |

**Total CTOUT01:** ~7h, calendar ~1.5 days. Matches falsifier window (deadline 2026-06-15).
**CTOUT01-a only (split):** ~2h, half-day. Unblocks AC-008 today.

### Complexity verification

Task says `complexity: 5`. Verdict: **correct.** Cross-repo + central-path + multi-layer cancellation contract justifies it.

---

## Critical Files

Most load-bearing, in update-frequency order:

- `guardkit/orchestrator/feature_orchestrator.py`
- `guardkit/orchestrator/agent_invoker.py`
- `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`
- `guardkit/orchestrator/harness/adapter.py`
- `guardkit/orchestrator/harness/sdk_harness.py`

Test files:
- `tests/unit/test_feature_orchestrator.py`
- `tests/orchestrator/test_agent_invoker_langgraph.py`
- `tests/orchestrator/harness/test_selector.py`
