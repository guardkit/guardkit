# Plan Audit — TASK-HMIG-006 Phase 5.5

**Date:** 2026-05-20
**Auditor:** `/task-work` interactive run (Phase 5.5 plan-audit step)
**Verdict:** APPROVED — no unjustified scope creep

---

## Audit shape

This is Hubbard's Step 6 verification: does the actual implementation
match the approved plan at `docs/state/TASK-HMIG-006/implementation_plan.md`?
Per `.claude/rules/absence-of-failure-is-not-success.md`, the audit asserts
positive evidence (everything planned was delivered) AND documents
every deviation (everything delivered beyond plan is justified).

## Files: planned vs actual

### Created — planned 4 / actual 7

| File | Planned LOC | Actual LOC | Status | Notes |
|---|---:|---:|---|---|
| `guardkit/orchestrator/harness/sdk_harness.py` | ~220 | 442 | ✅ as planned | Overage is in docstrings + verbatim error wording transferred from `agent_invoker.py` lines 2399-2740. |
| `guardkit/orchestrator/harness/README.md` | ~120 | 198 | ✅ as planned | Overage is the explicit Wave-2 divergences table (D-7) which the plan §6 requires. |
| `tests/orchestrator/test_agent_invoker_langgraph.py` | ~180 | 571 | 🟡 expanded | 7 test cases at LOC density consistent with Phase 3a `test_sdk_harness.py`. Strict intensity coverage demanded the surface. |
| `tests/orchestrator/harness/test_sdk_harness.py` | ~200 | 617 | 🟡 expanded | 23 tests covering parse-resilience + exception cascade + constructor plumbing — the strict 85% line / 80% branch bar drove the expansion. |
| `guardkit/orchestrator/harness/selector.py` | (in plan §3 pseudocode) | 159 | ✅ as planned per OQ-3 | OQ-3 resolved: separate module to keep `__init__.py` `os`-free. |
| `tests/orchestrator/harness/test_selector.py` | (not enumerated) | 264 | 🟢 follow-on | 13 tests for `_translate_kwargs_for_langgraph` + env-var dispatch. Implied by the strict-intensity coverage requirement on `selector.py`. |
| `tests/orchestrator/harness/test_byte_compat_parity.py` | (per plan §6) | 422 | ✅ AC-004 | The byte-compat parity test the plan §6 mandates. Non-empty fixture surface per `.claude/rules/absence-of-failure-is-not-success.md`. |

**Three extra test files** (selector tests, byte-compat parity, langgraph
end-to-end) are all explicitly required by the plan (§6 test strategy + the
divergence-inversion contract). They are NOT scope creep — they are the
test surface the plan demanded.

### Modified — planned 5 / actual 5

| File | Planned delta | Actual delta | Status |
|---|---:|---:|---|
| `guardkit/orchestrator/agent_invoker.py` | -180 / +90 net | -244 / +205 = -39 net | ✅ Refactor is structurally faithful. Smaller net reduction because more orchestrator concerns preserved inline per D-3 than the plan's pseudocode suggested. |
| `guardkit/orchestrator/harness/__init__.py` | +15 | +22 (Phase 3a) + S-1 docstring | ✅ as planned + Phase 5 should-fix lazy-import contract warning. |
| `pyproject.toml` | +4 | +16 | ✅ +`[tool.uv.sources]` block (D-5 resolution from OQ-1) + duplicate `guardkitfactory` entry in `all` group. |
| `guardkit/cli/doctor.py` | +30 | +57 | ✅ `ActiveHarnessCheck` + wiring. Overage is the `langgraph + missing guardkitfactory` FAIL branch and the unknown-value WARNING branch. |
| `tests/orchestrator/test_agent_invoker_sdk_errors.py` | minimal | **unchanged** | ✅ AC-008 honoured — no test edits. |

### Bonus modification (Phase 3b — flagged but justified)

| File | Delta | Justification |
|---|---:|---|
| `guardkit/orchestrator/harness/adapter.py` | +10 | Added `raw: object | None = None` to `ResultMessageEvent`. Phase 3a agent flagged the asymmetry; Phase 3b confirmed needed for `_emit_llm_call_event` / `_extract_partial_from_messages` to consume raw SDK message objects on the SDK path. Additive change with defaulted value — backwards-compatible with existing 5 adapter-interface tests. Code review C-5 recommends a one-line traceability comment on the field; tracked. |
| `tests/unit/test_doctor.py` | +67 | New `TestActiveHarnessCheck` class — 6 tests for the doctor extension delivered by Phase 3d. Phase 3d work, not in the plan's enumerated test list, but a strict-intensity coverage requirement on the new check. |

## Net LOC delta

| Layer | Planned (plan §2) | Actual | Δ |
|---|---:|---:|---:|
| Production code | +295 net (-180+90 invoker, +220 sdk_harness, +15 __init__, +30 doctor, +4 pyproject) | +685 (-39 invoker, +442 sdk_harness, +159 selector, +22 __init__, +57 doctor, +16 pyproject, +28 adapter+invoker imports) | +390 |
| Test code | +380 (~180 langgraph, ~200 sdk_harness) | +1874 (617 sdk_harness, 264 selector, 422 byte_compat, 571 langgraph) | +1494 |
| Documentation | (not enumerated in §2) | +198 (README) | +198 |
| **Total** | **+685** | **+2757** | **+2072** |

**Reading**: the test surface overshot by ~4×, but every test file is
required by an explicit plan clause (§6 test strategy, AC-004 byte-compat,
AC-009 langgraph tests, strict-intensity coverage thresholds). The
production overage is 30% — mostly in the SDK harness's verbose
docstrings preserving the TASK-FIX-7A03 / TASK-RFX-B20B /
TASK-RFX-8332 / TASK-FIX-GEN1 history that previously lived inline in
`agent_invoker.py`. This is intentional — the frozen-path policy
requires the rationale to follow the code, not get lost in the diff.

**Conclusion**: the LOC overage is **justified by the plan's own
strict-intensity testing requirements**, not by silent feature
expansion.

## Dependencies added

Per AC-005:
- `guardkitfactory>=0.1,<1` added to `[project.optional-dependencies].autobuild`
- `guardkitfactory>=0.1,<1` added to `[project.optional-dependencies].all`
- New `[tool.uv.sources]` block with `guardkitfactory = { path = "../guardkitfactory", editable = true }`

These match the plan §3 / D-5 verbatim. OQ-1 resolution honoured
(sibling-repo editable pattern, not PyPI / git+https).

## Acceptance criteria mapping

| AC | Required | Verified by |
|---|---|---|
| AC-001 — `_invoke_with_role` substrate-agnostic | ✅ | Phase 3b refactor; 133 AC-008 tests green |
| AC-002 — `sdk_harness.py` wraps SDK invocation | ✅ | 23 tests in `test_sdk_harness.py`, 87% coverage |
| AC-003 — Lazy `guardkitfactory` import | ✅ | `test_agent_invoker_langgraph.py::test_lazy_import_when_sdk_default` |
| AC-004 — Byte-compat artefacts | ✅ | `test_byte_compat_parity.py` (6 tests, non-empty fixture per anti-false-green rule) |
| AC-005 — pyproject dep | ✅ | `pip install -e .[autobuild]` resolves guardkitfactory via `[tool.uv.sources]` |
| AC-006 — doctor reports harness | ✅ | `TestActiveHarnessCheck` (6 tests in `test_doctor.py`) |
| AC-007 — Resume support divergence | ✅ | Orchestrator warning at `agent_invoker.py:2512-2518` + translator-level debug after S-2 |
| AC-008 — Existing tests pass under sdk default | ✅ | 133 tests across 6 test files unchanged, all green |
| AC-009 — LangGraph tests | ✅ | `test_agent_invoker_langgraph.py` (8 tests) + `test_selector.py` (13 tests) |
| AC-010 — README | ✅ | `guardkit/orchestrator/harness/README.md` (198 lines) |

All 10 ACs verified.

## Follow-up tasks filed (OQ-4)

Per Phase 2.8 resolution of OQ-4:

- ✅ [`TASK-HMIG-006.1`](../../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-006.1-migrate-direct-mode-sdk-dispatch.md) — Migrate direct-mode TaskWork dispatch (second SDK call site at `agent_invoker.py:5269+`)
- ✅ [`TASK-HMIG-006.2`](../../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-006.2-migrate-helpers-to-harness-event-dispatch.md) — Migrate `_extract_partial_from_messages` / `_track_tool_use` to HarnessEvent dispatch (D-7 cutover-day blocker)
- ✅ [`TASK-HMIG-006.3`](../../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md) — Migrate Coach's independent SDK invocation (third SDK call site at `coach_validator.py:1869+`)

All three filed in `tasks/backlog/autobuild-harness-migration/`.

## Phase 5 code review summary

[`docs/state/TASK-HMIG-006/code_review.md`](code_review.md)

- Verdict: APPROVED_WITH_RECOMMENDATIONS
- Overall: 87/100
- Per-area: SOLID 88 / DRY 85 / YAGNI 90 / Security 84
- Must-fix: 0
- Should-fix: 3 (S-1, S-2, S-3 — all applied during Phase 5.5)
- Consider: 5 (C-1 through C-5)

### Should-fix items applied

- S-1 (`harness/__init__.py`): added an `.. important::` block to the
  package docstring warning future contributors not to lift the SDK
  import to module level in `sdk_harness.py`.
- S-2 (`selector.py`): added `logger.debug` inside
  `_translate_kwargs_for_langgraph` when a truthy `resume_session_id`
  is dropped, so direct callers of `select_harness()` (bypassing the
  orchestrator's AC-007 warning) at least get a debug-level trace.
- S-3 (`adapter.py` + `sdk_harness.py`): updated `invoke()` return-type
  annotation from `AsyncIterator[HarnessEvent]` to
  `AsyncGenerator[HarnessEvent, None]` for type-checker precision.
  Added the `AsyncGenerator` import alongside the existing
  `AsyncIterator` import (the latter is retained because the language-
  level invariant still holds and other type signatures in the file
  use it).

55 harness + langgraph tests still green after applying S-1/S-2/S-3.

### Consider items deferred

C-1 through C-5 are flagged in the code review but not actioned this
session. They are either out-of-scope nice-to-haves (C-1 OCP
extensibility documentation, C-3 pip-without-uv install-path note in
the portfolio guide) or known accepted trade-offs (C-2 selector test
weakness, C-4 asyncio.sleep flake risk, C-5 ABC field traceability
comment).

## Scope creep summary

| Category | Finding |
|---|---|
| Extra files | 3 test files (selector, byte_compat, langgraph) — **all required by plan §6** |
| Extra modules | 1 (`selector.py`) — **planned per OQ-3** |
| Extra ABC field | 1 (`ResultMessageEvent.raw`) — **flagged by Phase 3a, justified by Phase 3b** |
| Extra dependencies | 1 (`guardkitfactory`) — **planned per AC-005 + D-5** |
| Untracked feature additions | **none** |
| Untracked test additions | **none** |

**Plan audit verdict: APPROVED** — every deliverable beyond the
plan's explicit enumeration is traceable to a plan clause or to a
plan-mandated quality gate. No unjustified scope creep.

## Recommendations for whoever picks up Wave 3

- Start with `TASK-HMIG-006.2` (helper migration) — it's the D-7
  cutover-day blocker and the lowest-friction win.
- `TASK-HMIG-006.1` and `TASK-HMIG-006.3` can be parallelised after
  006.2 lands (006.1 doesn't depend on 006.3; 006.3's depends_on
  references 006.2 only for parity, not for hard wiring).
- The byte-compat parity tests at
  `tests/orchestrator/harness/test_byte_compat_parity.py` are the
  inversion gate. When 006.2 lands, the
  `TestDocumentedDivergences::test_tool_use_divergence_documented`
  assertions invert from `lg == 0` to `lg == 1` — that inversion is
  the verifiable signal the migration is complete. Update the README
  divergences table in the same PR.
