# Code Review — TASK-HMIG-006

**Reviewer:** code-reviewer agent (strict intensity)
**Date:** 2026-05-20
**Verdict:** APPROVED_WITH_RECOMMENDATIONS
**Overall score:** 87/100

---

## Per-area scores

| Area | Score | Notes |
|---|---|---|
| SOLID | 88/100 | Thin boundary, clean DIP; one OCP/ISP flag |
| DRY | 85/100 | One minor duplication; no significant drift |
| YAGNI | 90/100 | Well-scoped; `_translate_kwargs_for_langgraph` borderline but justified |
| Security | 84/100 | Fail-closed dispatch; one case-insensitivity concern; relative path risk |

---

## Issues by severity

### must-fix

None. All blocking concerns from the architectural review were addressed in Plan v3 (D-4 ValueError normalisation, D-6 single-use harness, AC-004 non-empty fixture surface).

### should-fix

**S-1 — `__init__.py` eagerly imports `ClaudeSDKHarness`; breaks the lazy-import contract on the SDK path**
`guardkit/orchestrator/harness/__init__.py` lines 18-19:

```python
from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness
from guardkit.orchestrator.harness.selector import select_harness
```

`sdk_harness.py` does NOT import `claude_agent_sdk` at module load (the import is deferred into `invoke()`), so this does not currently cause an ImportError. However `selector.py` at its own module load imports `AgentInvocationError` and `HarnessAdapter` — both of which resolve cleanly. The real risk is if any future change to `sdk_harness.py` lifts the lazy import to module level: the entire `guardkit.orchestrator.harness` package would then require `claude_agent_sdk` to be installed, breaking the lazyness promise documented in AC-003 and the module docstring. The selector was deliberately put in its own module (OQ-3) to keep `__init__.py` free of `os` — but `__init__.py` still eagerly pulls in `ClaudeSDKHarness`. At minimum, the `__init__.py` docstring should note that `ClaudeSDKHarness` is safe to import only because `sdk_harness.py` defers the `claude_agent_sdk` import, and future contributors must preserve that contract. Better: move the `ClaudeSDKHarness` re-export behind the same lazy-import pattern used by `selector.py` (`TYPE_CHECKING` guard or omit from `__init__` entirely and import from `sdk_harness` directly at call sites).

**S-2 — `_translate_kwargs_for_langgraph` uses silent drop; no warning when `resume_session_id` is non-None**
`guardkit/orchestrator/harness/selector.py` lines 37-79. The translator silently drops `resume_session_id` even when it is truthy. The orchestrator correctly emits the AC-007 warning at `agent_invoker.py:2512-2518` when `harness.supports_resume is False`. However the warning fires AFTER `select_harness()` returns — so if someone calls `select_harness(resume_session_id="abc")` directly (a future test or helper), the resume intent is silently dropped with zero user signal. The translator docstring documents this ("resume_session_id — LangGraph does not support session resume in the Wave-2 skeleton") but the code itself gives no runtime signal. Suggest adding a `logger.debug` inside `_translate_kwargs_for_langgraph` when `resume_session_id` is truthy, so callers who bypass the orchestrator wrapper get at least a debug-level trace of the drop.

**S-3 — `invoke()` return-type annotation is `AsyncIterator[HarnessEvent]` but the function is an async generator**
`guardkit/orchestrator/harness/sdk_harness.py` line 162:

```python
async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds) -> AsyncIterator[HarnessEvent]:
```

The ABC in `adapter.py` line 144 declares the same `-> AsyncIterator[HarnessEvent]` return annotation, and uses the `raise NotImplementedError; yield` trick to make the abstract method an async generator. The concrete `ClaudeSDKHarness.invoke()` is a real async generator (it uses `yield`), so the annotation is semantically compatible. The mismatch is that `AsyncIterator` is correct here, but `AsyncGenerator[HarnessEvent, None]` would be more precise and is what mypy actually infers. This is a minor type-annotation accuracy issue — no runtime consequence, but worth aligning for type-checking clarity. Matches `adapter.py`'s own annotation; file as a single follow-up change to both files.

### consider

**C-1 — OCP: `select_harness()` has hardcoded `if name == "sdk" / if name == "langgraph"` dispatch**
`guardkit/orchestrator/harness/selector.py` lines 116-139. Adding a third harness requires modifying `select_harness()`. The plan acknowledges this explicitly ("acceptable for two-substrate scope"). This is a justified YAGNI decision at Wave 2; however the comment at the top of `selector.py` documenting the known values should include a note pointing to the README for extension instructions. Currently the only extension guidance lives in `README.md`; without a cross-reference in `selector.py` a future contributor may not know where to look.

**C-2 — `test_default_does_not_import_guardkitfactory` test is weakened by sys.modules cache**
`tests/orchestrator/harness/test_selector.py` lines 139-171. The test's own comment acknowledges the weakness: "If it's already cached in sys.modules from a previous test, we can't observe imports against it." The test falls back to asserting the return type only. This is acceptable for the current suite but creates a gap where a future regression (eager import of `guardkitfactory` in the SDK branch) would be invisible if another test loaded `guardkitfactory.harness` first. A more robust approach is to run this test in isolation with `importlib` reloading `selector` in a subprocess (expensive) or to use a monkeypatch that replaces `sys.modules["guardkitfactory.harness"]` with a sentinel before calling `select_harness` on the SDK path and verifying the sentinel was never accessed. The current approach is accepted at this intensity level; document the gap.

**C-3 — `pyproject.toml` `[tool.uv.sources]` block creates a resolution gap for non-uv users**
`pyproject.toml` lines 88-96. The `[tool.uv.sources]` stanza is `uv`-specific. A developer using plain `pip install -e ".[autobuild]"` in an environment where `../guardkitfactory` exists on disk will get a `pip` resolution failure because `pip` does not read `[tool.uv.sources]`. They must manually `pip install -e ../guardkitfactory` first. The README documents `pip install -e ../guardkitfactory && pip install -e .[autobuild]` as the manual path; the `pyproject.toml` comment (lines 92-93) also names it. This is an acceptable trade-off for a fleet that standardises on `uv`, but the install failure mode for `pip`-only users will be cryptic ("No matching distribution found for guardkitfactory>=0.1"). Suggest adding a note to `docs/guides/portfolio-python-pinning.md` on the `pip`-path fallback, and mentioning it in the harness README under "Cross-repo dependency".

**C-4 — `asyncio.sleep(0.05)` in LangGraph tests couples assertions to real time**
`tests/orchestrator/test_agent_invoker_langgraph.py` lines 289, 383, 430, 527. The `await asyncio.sleep(0.05)` calls after `_invoke_with_role` give the fire-and-forget `_safe_emit` task time to complete before the assertion reads `emitter.events`. This pattern is fragile on slow CI runners where 50ms may not be enough. The existing instrumentation tests in the broader suite apparently use the same pattern (the test file references `test_llm_call_events.py` as its model). If the suite later sees intermittent failures on the `events` assertion, the fix is to either flush pending tasks explicitly or make `NullEmitter` synchronous in its capture path. Log as a known flake risk.

**C-5 — `ResultMessageEvent.raw` ABC addition (Phase 3b) was additive but should be tracked as a TASK-HMIG-001A addendum**
`guardkit/orchestrator/harness/adapter.py` lines 97-102. The `raw: object | None = None` field was added to the `ResultMessageEvent` dataclass during Phase 3b. The class is frozen and the field has a default, so it is backwards-compatible. However TASK-HMIG-001A is the authoritative owner of `adapter.py`. The implementation plan records this as an "additive ABC change" (Phase 3b note) but does not create a task-level audit trail against TASK-HMIG-001A. When TASK-HMIG-001A's owner reviews the ABC surface later, the origin of `raw` may be unclear. Recommend adding a comment on the field: `# Added TASK-HMIG-006 Phase 3b — see sdk_harness.py docstring for rationale.` (one line is enough). The field docstring at lines 91-96 is thorough; the traceability comment just needs to appear on the field itself.

---

## SOLID evaluation (detail)

**SRP (strong):** The three modules each have exactly one axis of change. `adapter.py` is pure protocol. `sdk_harness.py` owns only SDK translation. `selector.py` owns only env-var dispatch. `agent_invoker.py` retains heartbeat, latency, cancellation, and event emission — all orchestrator concerns, none substrate-specific (D-3). No leakage observed.

**OCP (acceptable with note):** `select_harness()` is hardcoded for two values; extending to three requires modification. This was a deliberate YAGNI call documented in the plan. Flag C-1 applies. Score held because the plan explicitly bounds scope to two substrates.

**LSP (strong):** `ClaudeSDKHarness` and `_StubLangGraphHarness` (in tests) both honour the `HarnessAdapter` contract. The divergences (`supports_resume=False`, lossy events) are documented as part of the contract (D-7 table in README) rather than smuggled in. The abstract `invoke()` method uses the `raise NotImplementedError; yield` pattern to declare the return type as `AsyncIterator` at the language level — this is a known Python trick for abstract async generators and is correct.

**ISP (acceptable):** The `HarnessAdapter` surface has three members (`invoke`, `session_id`, `supports_resume`). Both concrete impls use all three. No unnecessary members are imposed. The `session_id` and `supports_resume` properties have concrete defaults on the ABC so test fakes don't need to override them — that is an intentional ergonomics decision, not an ISP violation.

**DIP (strong):** `agent_invoker.py` now depends only on `HarnessAdapter`, `HarnessEvent`, `AssistantMessageEvent`, `ResultMessageEvent`, and `select_harness`. No SDK types leak past the harness boundary in the refactored path. The `response_messages` list holds `event.raw` (which is `object | None` at the ABC level), so the duck-typing downstream consumers technically depend on the concrete SDK shape being in `raw`, but this is documented as a Wave-2 interim state (D-1) and the follow-up TASK-HMIG-006.2 is filed to migrate those consumers.

---

## DRY evaluation (detail)

One duplication observed: the SDK import diagnostic message at `sdk_harness.py:198-208` is a near-identical copy of the diagnostic that previously lived in `agent_invoker.py`. This is correct behaviour — the diagnostic is meant to be inside the harness, not the orchestrator. The net effect is that the orchestrator's import diagnostic was removed (the old site was the duplicated form); the harness now owns the single copy. No DRY violation.

The `MessageParseError` sentinel pattern (try-import, fall back to a local exception class) appears only once (in `sdk_harness.py`). No duplication with tests — tests import the real `MessageParseError` from `claude_agent_sdk._errors` directly.

Test fixture helpers (`_make_harness`, `_sdk_kwargs`, `_make_stub_langgraph_harness`, `_make_invoker`) are local to their test files. There is some structural similarity between the `_build_mock_sdk` helper in `test_agent_invoker_langgraph.py` and similar helpers in `test_llm_call_events.py`, as the test file itself acknowledges ("Mirrors the fixture in..."). This is acceptable documentation of conscious reuse; extracting a shared conftest would be worth considering as the LangGraph test surface grows.

---

## YAGNI evaluation (detail)

`_translate_kwargs_for_langgraph` (selector.py:37-79) warrants scrutiny as a potential over-engineering site. The function is 42 lines including comments; the logic is exactly `return {"model": harness_kwargs.get("model")}` (2 lines). The surrounding 40 lines are exhaustive documentation of every dropped kwarg. This documentation earns its space: without it, a future maintainer dropping `ClaudeAgentOptions`-specific kwargs would have no record of why. The verbosity is intentional transparency, not feature-creep. Score is high.

The `sdk_debug_dir` constructor arg to `ClaudeSDKHarness` is marked "accepted for forward-compat; the orchestrator owns sdk_debug instrumentation in Phase 3a." The arg is stored as `self._sdk_debug_dir` but never used inside the harness. The orchestrator passes `_sdk_debug_dir` to `select_harness()`, which passes it through to `ClaudeSDKHarness.__init__`, where it sits inert. This is mild YAGNI — the arg exists for a future use case that may belong in the orchestrator anyway (per D-3). Flag: if `sdk_debug_dir` is never used inside the harness, consider removing it from `ClaudeSDKHarness.__init__` and having the orchestrator own the path entirely. The docstring comment ("Currently accepted for forward-compat") is honest about this.

---

## Security evaluation (detail)

**Env-var input validation (strong):** `select_harness()` correctly fails closed — unknown values raise `AgentInvocationError` naming the bad value rather than silently falling through to a default. This honours the "fail-closed" principle.

**Case-insensitive matching (acceptable with note):** `GUARDKIT_HARNESS=LangGraph` (mixed case) routes to the LangGraph harness. The plan explicitly calls this out as a known behaviour ("GUARDKIT_HARNESS=LangGraph works; is that OK?"). The `doctor.py` check also lowercases before comparison, so the two surfaces are consistent. This is acceptable; the env var is an operator-facing knob. No credentials or untrusted input touches this path.

**Relative path in `pyproject.toml`:** `guardkitfactory = { path = "../guardkitfactory", editable = true }` is relative to the package root. In a wheel-build CI context the sibling directory will not exist and `uv` will fail if it tries to resolve the source. However `[tool.uv.sources]` is `uv`-specific and is not used by `pip`'s wheel-build machinery; the `>=0.1,<1` version constraint in `[project.optional-dependencies]` is what a PyPI-sourced wheel would use. The risk is CI runs that use `uv` and expect to build a wheel from a checkout that does not have the sibling at `../guardkitfactory`. This is the same risk the jarvis/nats-core pattern carries; it is a fleet-convention trade-off, not a guardkit-specific defect. Document in `docs/guides/portfolio-python-pinning.md` that CI matrix builds should use `pip install` (not `uv sync`) or ensure the sibling is checked out.

**No hardcoded secrets, no SQL, no XSS surface** — not applicable to this change.

---

## Frozen-path discipline

The freeze on `guardkit/orchestrator/agent_invoker.py` closed 2026-05-17; the refactor starts 2026-05-20. No override was required. The implementation plan notes this at §1 and requires the commit message to reference review §10.

The refactored `_invoke_with_role` preserves all orchestrator-side concerns (D-3 checklist is fully honoured in the implementation). The AC-008 surface (133 tests) passes unchanged. This was the primary risk; it is mitigated.

The AC-004 byte-compat test honours `.claude/rules/absence-of-failure-is-not-success.md`: the `TestNonEmptyFixtureSurface` class at `tests/orchestrator/harness/test_byte_compat_parity.py:386-422` asserts `text_block_count >= 1` and `tool_call_count >= 1` for the SDK fixture, preventing a zero-cardinality false-green. The `TestDocumentedDivergences` class asserts each Wave-2 divergence explicitly and names the follow-up task, so the inversion when TASK-HMIG-006.2 lands will be unambiguous. This is model-level compliance with the rule.

No `sys.path.insert` was introduced. The new `guardkit.orchestrator.harness.sdk_harness` module name does not shadow any PyPI package (`.claude/rules/namespace-hygiene.md` — no collision found).

The `.claude/rules/anti-stub.md` rule is satisfied: `ClaudeSDKHarness.invoke()` contains 200+ LOC of real implementation logic; `select_harness()` contains real dispatch logic. No stub bodies.

---

## Strengths

1. The `event.raw` channel (D-1) is the key architectural insight: it eliminates the need to migrate all duck-typed downstream consumers in one wave while still establishing a clean abstract event taxonomy. The comment trail through `adapter.py`, `sdk_harness.py`, `agent_invoker.py`, and `README.md` is exceptionally clear.

2. The `ClaudeSDKHarness` module docstring (lines 1-51) precisely lists every behaviour preserved verbatim by task ID (`TASK-FIX-7A03`, `TASK-RFX-B20B`, `TASK-RFX-8332`). This is the right level of traceability for a refactor of a frozen, load-bearing module.

3. The `TestNonEmptyFixtureSurface` class in `test_byte_compat_parity.py` is a textbook implementation of the `absence-of-failure-is-not-success` rule. Most teams document this rule; few actually write the positive-evidence guard test alongside the parity test.

4. The `_translate_kwargs_for_langgraph` documentation is verbose by design — every dropped kwarg is named and explained. This prevents the "where did my parameter go?" debugging session when someone passes `resume_session_id` on the LangGraph path.

5. The `README.md` Wave-2 divergence table with explicit "Fixed in TASK-HMIG-006.X" columns is the correct way to communicate deliberate technical debt. Future contributors can see what degrades, why, and when it will be fixed. The self-referential comment ("When TASK-HMIG-006.2 lands, the divergence assertions invert") creates a machine-readable gate on the migration completion.

6. Single-use harness per D-6 is clean: no shared-state contamination risk across invocations, test fixtures are simpler, and the cleanup-handler installer callback pattern keeps the SDK subprocess lifecycle concern in the orchestrator without the harness depending on `_install_sdk_cleanup_handler` by name.

---

## Open questions addressed

**`ResultMessageEvent.raw` ABC addition (C-5 above):** Additive, backwards-compatible, defaults to `None`. Clean ABC change. TASK-HMIG-001A's owner should be notified; a one-line comment on the field noting its origin is sufficient.

**`_translate_kwargs_for_langgraph` silent drop of `resume_session_id`:** The AC-007 warning in `agent_invoker.py` is the user-facing signal. It fires when `resume_session_id is not None and not harness.supports_resume`. The warning logs the truncated session ID (first 16 chars) and the harness type. This is sufficient for operators. The gap is direct callers of `select_harness()` who bypass the orchestrator — addressed as S-2 above.

**Byte-compat test uses stub harnesses, not real ones:** The stubs are faithful to the event sequences the real harnesses produce (verified by the `_make_stub_langgraph_harness` docstring in `test_agent_invoker_langgraph.py`). The schema-subset contract is tested on real `_extract_partial_from_messages` logic. Integration risk: the real `ClaudeSDKHarness` paths through `_extract_partial_from_messages` are exercised by the existing AC-008 surface (133 tests). The stub-harness approach is appropriate given the goal is schema parity, not LangGraph integration.

**Pre-existing test failures:** Out of scope per the brief. File a separate TASK-FIX for `test_design_context_integration.py` and `instrumentation/test_digest_content.py` if they are not already tracked.

---

## Follow-up task clarity

The README "deferred work" section names TASK-HMIG-006.1 (second SDK call site at `agent_invoker.py:5269+`), TASK-HMIG-006.2 (helper-function migration), and TASK-HMIG-006.3 (Coach's independent SDK invocation). Each entry in the divergence table includes "Fixed in TASK-HMIG-006.X". The file locations and line numbers are specific enough for the next implementer. Recommend also adding the follow-up task IDs to the `tasks/backlog/` stub files so they appear in `guardkit graphiti search` results.

---

## Recommendation list

1. **(should-fix / S-1)** Add a comment to `harness/__init__.py` documenting why eagerly importing `ClaudeSDKHarness` does not break the lazy-import contract (the import is deferred inside `invoke()`), and add a test or lint guard that fails if `sdk_harness.py` ever gains a module-level `claude_agent_sdk` import.

2. **(should-fix / S-2)** Add a `logger.debug` call inside `_translate_kwargs_for_langgraph` when `harness_kwargs.get("resume_session_id")` is truthy, so direct callers of `select_harness` receive a trace of the silent drop.

3. **(should-fix / S-3)** Align the `invoke()` return-type annotation in `sdk_harness.py` and `adapter.py` to `AsyncGenerator[HarnessEvent, None]` for type-checking accuracy, or add a mypy `# type: ignore` with a comment explaining the `AsyncIterator` convention.

4. **(consider / C-1)** Add a cross-reference comment in `selector.py` pointing to `harness/README.md` for extension instructions when adding a third harness substrate.

5. **(consider / C-3)** Extend `docs/guides/portfolio-python-pinning.md` with a `pip`-path fallback note for non-uv users; add a one-liner to the harness README's "Cross-repo dependency" section.

6. **(consider / C-5)** Add a one-line origin comment on `ResultMessageEvent.raw` (`# Added TASK-HMIG-006 Phase 3b`) and notify TASK-HMIG-001A's owner.

7. **(housekeeping)** Remove or comment `self._sdk_debug_dir` from `ClaudeSDKHarness.__init__` if the field will remain unused inside the harness for the lifetime of Wave 2 (or document explicitly that it is reserved for Phase 3b instrumentation migration).

8. **(housekeeping)** File TASK-HMIG-006.1 / 006.2 / 006.3 as concrete `backlog` task stubs under `tasks/backlog/autobuild-harness-migration/` if not already done; the README references them by ID but they need to be discoverable files.
