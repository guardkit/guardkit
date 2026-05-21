# Implementation Plan: TASK-HMIG-008R

**Restore LLM Coach as primary decision-maker + refactor CoachValidator into CoachEvidenceBundle supplier**

Revision 3 architectural correction. Operator-approved 2026-05-20. Commit messages must cite review §14.9.

---

## 1. Architecture Overview

The 2025-12-30 Option D decision (TASK-REV-0414) made `CoachValidator.validate()` the primary Coach path, relegating the LLM Coach to a bare `except` clause. This task inverts that order. The corrected per-turn flow is:

1. Player turn completes (unchanged).
2. `CoachValidator.gather_evidence(...)` runs all existing deterministic gate logic and returns a `CoachEvidenceBundle` instead of a decision.
3. `CoachVerifier.verify_player_report(player_report)` runs honesty checks, producing `HonestyVerification` (Layer 1 / Layer 3' already in place).
4. `_build_coach_prompt(...)` renders both the bundle and the honesty result as structured JSON sections, including four verbatim absence-of-failure guards.
5. The LLM Coach is invoked unconditionally via `self._agent_invoker.invoke_coach(...)` which dispatches through `HarnessAdapter` (already landed, TASK-HMIG-006).
6. The Coach writes `coach_turn_N.json`. Decision parsing is unchanged.
7. If `GUARDKIT_COACH_LEGACY=1`: `CoachValidator.validate()` shim runs instead; LLM Coach is the `except` branch (legacy).

```mermaid
sequenceDiagram
    participant AB as autobuild._invoke_coach
    participant CV as CoachValidator
    participant CVF as CoachVerifier
    participant AI as AgentInvoker.invoke_coach
    participant HA as HarnessAdapter
    participant LC as LLM Coach (guardkitfactory.LangGraphHarness)

    AB->>AB: Check GUARDKIT_COACH_LEGACY
    alt GUARDKIT_COACH_LEGACY=1 (legacy path)
        AB->>CV: validate(task_id, turn, task, ...)
        CV-->>AB: CoachValidationResult (decision)
        Note over AB: Same as today; LLM Coach is except-branch
    else default (primary path)
        AB->>CV: gather_evidence(task_id, turn, task, ...)
        CV-->>AB: CoachEvidenceBundle
        AB->>CVF: verify_player_report(player_report)
        CVF-->>AB: HonestyVerification (with resolved_paths)
        AB->>AI: invoke_coach(task_id, turn, requirements, player_report, evidence_bundle)
        AI->>AI: _build_coach_prompt(... evidence_bundle, honesty_verification)
        AI->>HA: invoke(role="coach", prompt, tools=[Read,Bash,Grep,Glob])
        HA->>LC: dispatch (GUARDKIT_HARNESS=langgraph → LangGraphHarness)
        LC-->>HA: stream events
        HA-->>AI: HarnessEvent stream
        AI->>AI: load coach_turn_N.json, validate_coach_decision
        AI-->>AB: AgentInvocationResult
    end
```

`GUARDKIT_COACH_LEGACY=1` is the emergency revert: it activates the exact current code path with zero code removal. The legacy path is preserved structurally so a one-line env var flip is sufficient.

---

## 2. CoachEvidenceBundle Schema (Part A, ACs 001–004)

### Namespace hygiene

Module name `coach_evidence` does not shadow any PyPI top-level package. `pip show coach-evidence` and `pip show coach_evidence` return nothing. Safe to proceed.

### File

`guardkit/orchestrator/quality_gates/coach_evidence.py`

### Dataclass vs Pydantic decision

**Use dataclass.** This is an internal value object passed between `coach_validator.py` and `agent_invoker.py`. It never crosses an external API boundary, requires no field-level validation constraints, and is serialised by `json.dumps(dataclasses.asdict(...))`. Using Pydantic here would introduce the `pydantic` import boundary into the quality_gates package for no gain. Consistent with `.claude/rules/patterns/dataclasses.md`: "Use dataclass when: simple internal state containers, no validation needed, need asdict() for JSON."

### Field list

Each field named below maps to an existing intermediate value computed inside `CoachValidator.validate()`.

```python
@dataclass
class CoachEvidenceBundle:
    """Structured evidence gathered by CoachValidator for the LLM Coach.

    All fields are the deterministic gate outputs that the legacy
    validate() method previously consumed internally to make a decision.
    The LLM Coach reads this bundle plus the honesty result and makes
    the final decision.

    Deprecated: validate() still runs this logic via gather_evidence()
    and then applies decision logic. Use gather_evidence() directly.
    """

    # Gate results (from verify_quality_gates; lines 1700-1829)
    quality_gates: Optional[QualityGateStatus]   # QualityGateStatus dataclass
    # Coverage details beyond the boolean (from quality_gates dict, lines 1736-1745)
    coverage_details: Optional[Dict[str, Any]]   # raw quality_gates dict slice

    # Plan audit findings (from task_work_results["plan_audit"], lines 1764-1803)
    plan_audit: Optional[Dict[str, Any]]

    # BDD plugin output (from task_work_results["bdd_results"], lines 4825-4835)
    # None when bdd_results key absent; is_zero_cardinality is the load-bearing property
    bdd: Optional[BDDRunResult]

    # Honesty result (from _verify_honesty + _honesty_issues_from; lines 5312-5560)
    # Carries resolved_paths (Layer 1) and should_fix hints (Layer 2 demotion)
    honesty: HonestyVerification

    # Architectural review (from task_work_results["code_review"], lines 1756-1762)
    arch_review: Optional[Dict[str, Any]]   # {"score": int, ...}

    # Test results (from quality_gates dict; lines 1703-1734)
    tests: Optional[Dict[str, Any]]   # {"tests_passed": bool, "tests_run": int, ...}

    # Severity recommendations derived from demotion logic in _honesty_issues_from
    # (lines 5430-5460). These are hints to the LLM Coach, not decisions.
    # Format: list of dicts, each with "recommendation" str and "rule" str.
    severity_recommendations: List[Dict[str, str]]

    # Independent test result when available (from run_independent_tests)
    independent_tests: Optional[IndependentTestResult]

    # Task type and profile used for evidence gathering
    task_type: Optional[str]
    profile_name: Optional[str]

    # Status of evidence gathering — disambiguates `None` fields for the
    # LLM Coach. "complete" means all fields populated successfully.
    # "partial_*" means gathering was aborted; the Coach must treat any
    # `None` field as ABSENT SIGNAL per the absence-of-failure guards.
    # Added per Phase 2.5 review finding #2 (resolves null-field ambiguity).
    gathering_status: Literal[
        "complete",
        "partial_honesty_abort",
        "partial_gate_abort",
        "partial_exception",
    ]
```

### `severity_recommendations` derivation

The existing `_honesty_issues_from()` method (lines 5430–5560) contains Layer 2 demotion logic: when `len(non_audit) == 1 and non_audit[0].claim_type == "file_existence"`, the severity is demoted from `must_fix` to `should_fix`. Under the new design this logic still runs inside `_honesty_issues_from`, but `gather_evidence` additionally materialises the *hint* as a structured recommendation so the LLM Coach can read and apply it explicitly:

```python
# Inside gather_evidence, after calling _honesty_issues_from:
severity_recommendations = []
if demote_condition_was_met:
    severity_recommendations.append({
        "recommendation": (
            "A single file_existence discrepancy was suppressed by Layer-1 "
            "identity resolution (state_bridge canonical_path_for). "
            "Treat as should_fix, not must_fix. Continue AC evaluation."
        ),
        "rule": "path-string-mismatch-is-not-dishonesty (Layer 2 demotion)"
    })
```

The demotion condition is: `len(non_audit) == 1 and non_audit[0].claim_type == "file_existence"` — extracted from `_honesty_issues_from` lines 5456–5460.

### `gather_evidence` signature

```python
def gather_evidence(
    self,
    task_id: str,
    turn: int,
    task: Dict[str, Any],
    skip_arch_review: bool = False,
    context: Optional[str] = None,
) -> CoachEvidenceBundle:
```

This signature is identical to `validate()` (lines 779–813). The implementation runs the same sequence of calls as `validate()` up through the evidence-gathering phase, but instead of applying decision logic, packages the intermediates into a `CoachEvidenceBundle` and returns it. Where `validate()` currently short-circuits on honesty failures or gate failures, `gather_evidence` continues to populate remaining fields as `None` — the LLM Coach makes the decision.

### `validate()` backward-compat shim

`validate()` becomes:

```python
def validate(
    self,
    task_id: str,
    turn: int,
    task: Dict[str, Any],
    skip_arch_review: bool = False,
    context: Optional[str] = None,
) -> CoachValidationResult:
    """
    DEPRECATED: Legacy decision-making entry point.

    Calls gather_evidence() and applies the original deterministic
    decision logic. Used only when GUARDKIT_COACH_LEGACY=1 or by
    direct callers that have not migrated to the LLM-Coach-primary
    flow (autobuild._invoke_coach with GUARDKIT_COACH_LEGACY=1).

    For the primary flow, call gather_evidence() and pass the bundle
    to AgentInvoker.invoke_coach().
    """
    bundle = self.gather_evidence(task_id, turn, task, skip_arch_review, context)
    return self._apply_legacy_decision_logic(bundle, task_id, turn, context)
```

`_apply_legacy_decision_logic` encapsulates the current decision tree from `validate()` lines 918–1612 (honesty short-circuit → gate failure → independent tests → requirements → zero-test → seam tests → approval).

### Call sites that still hit `validate()` directly

From grep of the codebase:

- `autobuild.py:5301` — migrates to `gather_evidence()` under the non-legacy path (Part B).
- `autobuild.py` legacy branch (new, under `GUARDKIT_COACH_LEGACY=1`) — stays on `validate()`.
- Any test fixtures calling `validator.validate(...)` directly — covered by AC-004 (run with `GUARDKIT_COACH_LEGACY=1` or unchanged since shim preserves interface).

---

## 3. Inverted `_invoke_coach` Flow (Part B, ACs 005–007)

### File and line range

`guardkit/orchestrator/autobuild.py` lines 5281–5401 (current `try/except` block).

### Pseudocode

```python
def _invoke_coach(self, task_id, turn, requirements, player_report, ...):
    # ... existing pre-amble (context retrieval, start_time) unchanged ...

    legacy_mode = os.environ.get("GUARDKIT_COACH_LEGACY") == "1"

    if legacy_mode:
        logger.info(
            "Using CoachValidator (legacy, GUARDKIT_COACH_LEGACY=1) "
            "for %s turn %s", task_id, turn
        )
        # Existing code verbatim (lines 5282-5350)
        coach_cfg = self._load_coach_config()
        validator = CoachValidator(...)
        validation_result = validator.validate(...)
        # ... save_decision, append command_results, return AgentInvocationResult ...
    else:
        logger.info(
            "Using LLM Coach (primary) for %s turn %s", task_id, turn
        )
        # New primary path
        coach_cfg = self._load_coach_config()
        validator = CoachValidator(
            str(worktree.path),
            task_id=task_id,
            coach_test_execution=coach_cfg.get("test_execution", "sdk"),
            matching_strategy=coach_cfg.get("matching_strategy", "auto"),
            wave_size=wave_size,
            turn=turn,
            peer_changed_files=peer_changed_files,
        )
        # Step 1: gather evidence bundle
        evidence_bundle = validator.gather_evidence(
            task_id=task_id,
            turn=turn,
            task={
                "acceptance_criteria": acceptance_criteria or [],
                "task_type": task_type,
                "requires_infrastructure": requires_infrastructure or [],
                "_docker_available": validator._is_docker_available(),
                "consumer_context": consumer_context or [],
                "description": requirements or "",
            },
            skip_arch_review=skip_arch_review,
            context=context_prompt if context_prompt else None,
        )

        # Step 2: invoke LLM Coach with evidence bundle via AgentInvoker
        # NOTE: Use asyncio.run() rather than the deprecated get_event_loop()
        # pattern from the current fallback. The primary path runs on every
        # turn; the deprecated pattern emits DeprecationWarning in 3.12+.
        # (Phase 2.5 review should-address #4.)
        import asyncio
        result = asyncio.run(
            self._agent_invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements=requirements,
                player_report=player_report,
                remaining_budget=remaining_budget,
                evidence_bundle=evidence_bundle,   # new parameter
            )
        )
        return result
```

### Exception handling for `gather_evidence` (revised per Phase 2.5 review)

The original §11.2 proposal — wrap `gather_evidence()` in try/except and fall back to `validate()` on exception — was **rejected** by the architectural review. It contradicts falsifier #1: "the path `autobuild._invoke_coach -> CoachValidator.validate()` for the decision is GONE." A try/except fallback to `validate()` reactivates exactly the path the falsifier requires to be gone, bypassing the `GUARDKIT_COACH_LEGACY` emergency-revert mechanism.

The corrected behaviour: `gather_evidence` MUST NOT raise to its caller under normal operation. Internal failures (gate failures, honesty failures) populate partial bundles with the appropriate `gathering_status` (e.g. `"partial_gate_abort"`). If a truly unexpected exception escapes, `_invoke_coach` catches it and writes a `coach_turn_N.json` with `decision: "feedback"` and `rationale: "Evidence gathering failed: <exception>"`. The Coach is never bypassed by a deterministic-validator fallback in the primary path. `GUARDKIT_COACH_LEGACY=1` remains the sole, intentional, operator-driven mechanism for reactivating `validate()`.

```python
# Inside the primary (non-legacy) branch of _invoke_coach, after Step 2:
try:
    evidence_bundle = validator.gather_evidence(...)
except Exception as exc:
    logger.error("gather_evidence raised; emitting feedback decision: %s", exc)
    # Write a synthetic coach_turn_N.json with feedback decision
    self._write_feedback_decision(
        task_id, turn,
        rationale=f"Evidence gathering failed: {exc}",
    )
    return AgentInvocationResult(...)  # turn produces feedback, not approve
```

### Logging verbatim (AC-007)

- Primary path: `"Using LLM Coach (primary) for %s turn %s"`
- Legacy path: `"Using CoachValidator (legacy, GUARDKIT_COACH_LEGACY=1) for %s turn %s"`

### On-disk contract

`coach_turn_N.json` schema is unchanged. Under the primary path, the LLM Coach writes it directly (same as the existing `invoke_coach` fallback path). Under the legacy path, `validator.save_decision(validation_result)` writes it (same as today). Downstream consumers in `autobuild.py` (`_display_criteria_progress`, `_count_criteria_passed`) are unaffected.

### Downstream callers of `CoachValidator.validate()`

Direct callers outside `autobuild.py`:

- Tests under `tests/orchestrator/` that construct `CoachValidator` and call `validate()` — preserved by the shim, unchanged API. AC-004 requires they pass under `GUARDKIT_COACH_LEGACY=1`; the shim makes them pass without the env var as well (shim always delegates to `gather_evidence` + legacy logic).
- No other non-test call sites found in the codebase.

---

## 4. Coach Prompt Extension (Part C, ACs 008–010)

### File and location

`guardkit/orchestrator/agent_invoker.py`. `invoke_coach` signature (lines 1843–1878) gains a new parameter `evidence_bundle: Optional[CoachEvidenceBundle] = None`. `_build_coach_prompt` (lines 2174–2323) is extended with a new `evidence_bundle` parameter.

### Honesty channel unification (revised per Phase 2.5 review finding #3)

The existing `invoke_coach` already accepts a `honesty_verification` parameter and renders an honesty section in the prompt (lines 2174-2210). Under the new flow, `evidence_bundle.honesty` carries the same `HonestyVerification` value. To avoid duplicate honesty sections in the prompt, the bundle's honesty field is **the single source of truth**: the legacy `honesty_verification` parameter on `invoke_coach` is deprecated in this task, marked with a docstring note, and `_build_coach_prompt` ignores it when `evidence_bundle is not None`. Callers (other than `_invoke_coach`) that still pass `honesty_verification` directly fall through to the legacy rendering path. This avoids breaking the existing signature while consolidating the channel.

### New prompt structure

The extended prompt adds two new sections between the Player Report and the Responsibilities block. The `<honesty_verification>` section is sourced exclusively from `evidence_bundle.honesty` when the bundle is present:

```
## Original Requirements
{requirements}

## Player's Report
{json.dumps(player_report, indent=2)}

## Deterministic Evidence Bundle
<evidence_bundle>
{json.dumps(evidence_bundle_as_dict, indent=2)}
</evidence_bundle>

## Honesty Verification
<honesty_verification>
{json.dumps(asdict(evidence_bundle.honesty), indent=2)}
</honesty_verification>

<absence_of_failure_guards>
CRITICAL READING RULES — apply before any approval decision:
1. If evidence.bdd is not null AND evidence.bdd.scenarios_attempted == 0: treat as ABSENT SIGNAL.
   Do NOT approve based on absence of BDD failures. Surface as feedback: "BDD oracle ran zero
   scenarios — no evidence of passing behaviour."
2. If evidence.tests is not null AND evidence.tests.tests_run == 0: treat as ABSENT SIGNAL.
   Do NOT approve. Surface as feedback: "No tests ran — cannot verify correctness."
3. If evidence.honesty.discrepancies contains entries with severity=critical AND
   category != "file_existence": you MUST reject the turn. These are sophisticated lies
   (test_result, test_count, promise_file_existence fabrications). Structural rejection
   is mandatory — do not evaluate ACs.
4. If evidence.honesty.discrepancies contains exactly ONE entry with claim_type=file_existence
   AND evidence.honesty.resolved_paths is non-empty: this discrepancy was Layer-1-resolved
   by state_bridge identity lookup (orchestrator moved the task file, not Player dishonesty).
   Demote to should_fix and continue AC evaluation.
5. If evidence.gathering_status != "complete": evidence collection aborted before all
   fields were populated. Treat any null/None field as ABSENT SIGNAL — do NOT approve.
   Surface as feedback with the gathering_status value verbatim in the rationale so
   operators can diagnose which stage failed.
</absence_of_failure_guards>

## Your Responsibilities
...
```

### AC-009 guard sentences (verbatim, assigned to prompt section `<absence_of_failure_guards>`)

The four guards from the task spec are:

1. `"If evidence.bdd.scenarios_attempted == 0, treat as ABSENT SIGNAL — do NOT approve based on absence of failure. Surface as feedback."`
2. `"If evidence.tests.tests_run == 0, treat as ABSENT SIGNAL — do NOT approve."`
3. `"If evidence.honesty.discrepancies contains entries with severity=critical AND category != file_existence, you MUST reject the turn (these are sophisticated lies; structural rejection)."`
4. `"If evidence.honesty.discrepancies contains a single file_existence discrepancy that was Layer-1-resolved (resolved_paths non-empty), demote to should_fix and continue evaluation."`
5. `"If evidence.gathering_status != 'complete': treat any None field as ABSENT SIGNAL — do NOT approve. Surface as feedback citing the gathering_status value."` (Added per Phase 2.5 review finding #2.)

These are enclosed in `<absence_of_failure_guards>...</absence_of_failure_guards>` XML-like tags so the Coach can locate them precisely.

### Token budget

The evidence bundle serialised via `dataclasses.asdict()` could be large because:
- `BDDRunResult.discoveries` and `BDDRunResult.errors` are unbounded lists.
- `HonestyVerification.discrepancies` may have dozens of entries in degenerate cases.

Truncation rules applied during `_build_coach_prompt`:
- `evidence_bundle.bdd.discoveries`: keep first 20 entries, append `"... and N more"` when truncated.
- `evidence_bundle.bdd.errors`: keep first 10 entries, append `"... and N more"`.
- `evidence_bundle.honesty.discrepancies`: keep first 20 entries, append count when truncated.
- All other fields: no truncation (they are bounded by design).

### Read-only tool surface (AC-010 / existing)

`agent_invoker.py:1901` specifies `allowed_tools=["Read", "Bash", "Grep", "Glob"]`. Under `GUARDKIT_HARNESS=langgraph`, this dispatches through `guardkitfactory.LangGraphHarness` with `LocalShellBackend` configured to the read-only built-in tool surface. No new tools are needed.

---

## 5. Honesty Layer 1 / Layer 3' Wired Through New Flow (Part D, ACs 011–013)

### AC-011: CoachVerifier._verify_files_exist consults state_bridge

Confirmed at `guardkit/orchestrator/coach_verification.py` lines 326–400. The method conditionally resolves `self.state_bridge.canonical_path_for()` (line 364) and appends to `self._resolved_paths` (line 374) when the canonical path exists. This is the existing TASK-FIX-1B4A fix.

Under the new primary path, `gather_evidence()` calls `_verify_honesty()` (lines 5312–5387), which constructs `CoachVerifier` with `task_id=self.task_id` and `state_bridge=TaskStateBridge(...)` (lines 5332–5345). The `resolved_paths` list flows through to `HonestyVerification.resolved_paths` (line 5376), which flows into `CoachEvidenceBundle.honesty`. The LLM Coach receives it in the prompt's `<honesty_verification>` section. No new wiring is required for AC-011 — the existing wire just needs verification that it reaches the new primary path.

Key lines (coach_verification.py):
- `self._resolved_paths` populated: lines 374–380
- `HonestyVerification(resolved_paths=list(self._resolved_paths))`: line 289
- `canonical_path_for()` call: line 364

### AC-012: Layer 3' orchestrator-induced path subtraction

Confirmed at `guardkit/orchestrator/agent_invoker.py` lines 164–170 (`_ORCHESTRATOR_MANAGED_PATH_PATTERNS`) and the `_strip_orchestrator_managed_paths` method (referenced via TASK-FIX-PCN). Additionally, `_create_player_report_from_task_work` consults `state_transitions.json` (TASK-FIX-1B4C). This subtraction runs before `player_report` reaches `invoke_coach`. No new wiring required.

### AC-013: Regression test scenario

The regression test in `tests/orchestrator/test_coach_zero_cardinality_guard.py` (or a separate `test_coach_layer1_honesty.py`) must:

1. Set up a fixture that simulates a state-bridge move during turn 1: `tasks/backlog/TASK-X-foo.md` → `tasks/design_approved/TASK-X-foo.md`.
2. Construct a Player report where `files_modified` includes the pre-move path `tasks/backlog/TASK-X-foo.md`.
3. Run `gather_evidence()` on this fixture; assert `bundle.honesty.resolved_paths` is non-empty.
4. Run `invoke_coach()` with a `FakeHarnessAdapter` (see §6) that captures the prompt.
5. Assert the prompt contains the Layer-1 demotion guard sentence (absence_of_failure_guards point 4).
6. Assert the fake LLM Coach returns `decision: approve` when the 16 ACs are all verified (the path discrepancy was resolved, not surfaced as must_fix).

---

## 6. Test Plan (Part E, ACs 014–017)

### AC-014: `tests/orchestrator/test_coach_evidence_bundle.py`

**Purpose**: Verify `CoachValidator.gather_evidence()` returns a populated `CoachEvidenceBundle`.

**Fixtures to reuse**:
- Existing `autobuild` fixtures in `tests/orchestrator/` that produce a populated `task_work_results.json` with `quality_gates`, `code_review`, and `plan_audit` keys.
- If no suitable fixture exists, create a minimal `PassingTurnFixture` that writes a valid `task_work_results.json` to a temp worktree.

**Mocking strategy**: No LLM involvement. `gather_evidence()` is purely deterministic. Mock `CoachVerifier` if it requires a live worktree for `_verify_claims_were_staged` (which calls `git status`).

**Assertions**:
- `bundle.quality_gates` is a `QualityGateStatus` with expected values.
- `bundle.bdd` is `None` when `bdd_results` absent from `task_work_results`.
- `bundle.honesty` is a `HonestyVerification` with `verified=True` for a clean fixture.
- `bundle.severity_recommendations` is `[]` for a clean fixture.
- When fixture includes a state-bridge move: `bundle.honesty.resolved_paths` is non-empty and `bundle.severity_recommendations` contains the Layer-1 demotion hint.
- `dataclasses.asdict(bundle)` is JSON-serialisable (no unserializable fields).

### AC-015: `tests/orchestrator/test_llm_coach_primary.py`

**Purpose**: Verify the routing decision in `autobuild._invoke_coach`.

**Fixtures to reuse**: Existing `AutoBuild` / `FeatureOrchestrator` unit test fixtures that produce a minimal worktree with a valid player report.

**Mocking strategy**:
- Patch `self._agent_invoker.invoke_coach` with a coroutine spy (`AsyncMock`).
- Patch `CoachValidator.gather_evidence` with a stub returning a minimal `CoachEvidenceBundle`.
- Patch `CoachValidator.validate` with a spy to detect unexpected calls.

**Assertions**:
- **Default flow** (`GUARDKIT_COACH_LEGACY` unset or `"0"`):
  - `agent_invoker.invoke_coach` was called exactly once.
  - `CoachValidator.validate` was NOT called.
  - Logger emitted `"Using LLM Coach (primary)"`.
- **Legacy flow** (`GUARDKIT_COACH_LEGACY=1`):
  - `CoachValidator.validate` was called exactly once.
  - `agent_invoker.invoke_coach` was NOT called (unless via the `except` fallback, which should not fire here).
  - Logger emitted `"Using CoachValidator (legacy, GUARDKIT_COACH_LEGACY=1)"`.

### AC-016: `tests/orchestrator/test_coach_zero_cardinality_guard.py`

**Purpose**: Verify the LLM-layer absence-of-failure guard (Pattern 2 fixture).

**Fixture strategy**: The test must simulate a real BDD evidence path without a live LLM. Use a `FakeHarnessAdapter` that:
- Receives the prompt.
- Asserts the prompt contains the four `<absence_of_failure_guards>` sentences.
- Returns a canned `decision: feedback` response when `evidence.bdd.scenarios_attempted == 0` is present in the prompt (i.e., simulate the Coach following the guard).

Alternatively: parse the rendered prompt directly and assert it contains the guard sentences. Then separately assert that a real LLM Coach (in a contract test, not unit test) would follow them. For the unit test, asserting the prompt contains the guards is sufficient.

For the "real BDD plugin" requirement: construct a `BDDRunResult` with `scenarios_attempted=0, scenarios_failed=0` directly (it is a simple dataclass from `guardkitfactory`). Do not require the full pytest-bdd runner to produce it.

**Mocking strategy**:
- `FakeHarnessAdapter` implementing `HarnessAdapter` ABC. Its `invoke()` method:
  1. Stores the received prompt.
  2. Writes a `coach_turn_N.json` with `decision: feedback` and `rationale: "BDD oracle ran zero scenarios — absent signal"`.
  3. Yields a `ResultMessageEvent`.
- Patch `select_harness` to return the `FakeHarnessAdapter`.

**Assertions**:
- Prompt contains `"scenarios_attempted == 0"` and `"ABSENT SIGNAL"`.
- `coach_turn_N.json` decision is `"feedback"` (not `"approve"`).
- `AgentInvocationResult.report["decision"] == "feedback"`.

**Limitation note (must appear as module docstring in the test file)**:
This test asserts the absence-of-failure guard sentences are correctly
*wired into the prompt*. It does NOT assert that a real LLM Coach
follows them. The behavioural assertion (that an LLM would actually
return `feedback` on a zero-cardinality bundle) is the falsifier for
Wave 3 canary observability (TASK-HMIG-009), not this unit test. Per
Phase 2.5 review should-address #5.

### AC-017: `tests/orchestrator/test_coach_zero_cardinality_guard.py` (Pattern 3 regression)

Reuse the existing TASK-FIX-1B4A regression test fixture (Pattern 3: state-bridge move). Parametrize or extend to assert the test passes under both:
- `GUARDKIT_COACH_LEGACY` unset (primary LLM path via `FakeHarnessAdapter`).
- `GUARDKIT_COACH_LEGACY=1` (legacy CoachValidator path).

The legacy path test already exists; the new test confirms the primary path does not regress Pattern 3.

---

## 7. File-by-File Change Summary

| File | Change type | Lines (approx) | Reason |
|---|---|---|---|
| `guardkit/orchestrator/quality_gates/coach_evidence.py` | new | ~120 | `CoachEvidenceBundle` dataclass + module docstring |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | modify | ~160 | `gather_evidence()` method + `_apply_legacy_decision_logic()` refactor + `validate()` shim + import `CoachEvidenceBundle` |
| `guardkit/orchestrator/autobuild.py` | modify | ~65 | Invert `_invoke_coach` with `GUARDKIT_COACH_LEGACY` branch; update logging |
| `guardkit/orchestrator/agent_invoker.py` | modify | ~90 | `invoke_coach` gains `evidence_bundle` param; `_build_coach_prompt` gains bundle sections + absence-of-failure guards + truncation |
| `tests/orchestrator/test_coach_evidence_bundle.py` | new | ~130 | AC-014 |
| `tests/orchestrator/test_llm_coach_primary.py` | new | ~160 | AC-015 |
| `tests/orchestrator/test_coach_zero_cardinality_guard.py` | new | ~140 | AC-016 + AC-017 |

**Total new/modified lines**: ~865

---

## 8. Risks and Mitigations

### R-13: LLM Coach too lenient (primary risk under Revision 3)

Source: review §9. An LLM Coach may approve turns where the deterministic path would reject (e.g. zero BDD scenarios, zero tests run, gate failure).

**Mitigations**:
1. **AC-009 guards** — four absence-of-failure sentences are required reading in the prompt; the Coach is explicitly instructed to reject on zero-cardinality signals. These are the LLM-layer equivalent of the structural guards in `.claude/rules/absence-of-failure-is-not-success.md`.
2. **AC-016 test** — Pattern 2 fixture asserts the prompt is correctly constructed and that `FakeHarnessAdapter` returns `feedback` on zero-cardinality BDD. This is a regression test for the guard wiring, not a contract test of the LLM's reasoning.
3. **Emergency revert** — `GUARDKIT_COACH_LEGACY=1` immediately re-activates the deterministic-primary path with no code changes. Document in `guardkit doctor` output (AC-006 requirement).

The deterministic evidence bundle remains available to the Coach as JSON. If the LLM Coach proves systematically lenient in Wave 3 canary (TASK-HMIG-009), the failure mode is observable (Coach approves where gates fail) and the revert is one env var.

### Token-budget blowup

A large wave with many BDD scenarios could produce a `discoveries` array of hundreds of entries, inflating the prompt.

**Mitigation**: Truncation rules in `_build_coach_prompt` (§4): first 20 `discoveries`, first 10 `errors`, first 20 honesty `discrepancies`, with explicit `"... and N more"` tail. The bundle's non-list fields are bounded by the existing gate computations.

### Existing CoachValidator tests under the shim (AC-004)

The shim calls `gather_evidence()` then `_apply_legacy_decision_logic()`. Any test that directly calls `validator.validate()` will now go through two methods instead of one. The behavioural contract is identical, but there is a risk of subtle differences in edge paths (e.g. operator_handoff short-circuit, missing results short-circuit).

**Mitigation**: The short-circuit paths (operator_handoff, missing results, invalid task_type) must be preserved identically in `_apply_legacy_decision_logic`. They do not call `gather_evidence()` — they return early before evidence gathering is meaningful. This is explicit in the design: `_apply_legacy_decision_logic` runs the decision tree against a `CoachEvidenceBundle` that may have `None` fields from an early-exit `gather_evidence`. The test to validate AC-004:

```bash
GUARDKIT_COACH_LEGACY=1 pytest tests/orchestrator/quality_gates/test_coach_validator.py -v
```

This invocation is not strictly required for the shim to work (it works without the env var too), but documents the intended backward-compat surface.

### Frozen-path touches

`coach_validator.py`, `agent_invoker.py`, `autobuild.py` were under the TASK-REV-ABST freeze (2026-05-11 → 2026-05-17). The freeze closed 2026-05-17 — no override required. All commit messages must cite: `"Revision 3 architectural correction per TASK-REV-HMIG §14.9 (operator-approved 2026-05-20). Restores LLM Coach as primary decision-maker per Block adversarial-cooperation paper."`.

---

## 9. Estimates

| Part | Description | Hours |
|---|---|---|
| A | New `coach_evidence.py` + `gather_evidence()` + shim | 3.5h |
| B | Invert `_invoke_coach` in `autobuild.py` | 1.5h |
| C | Extend `_build_coach_prompt` + `invoke_coach` signature | 2h |
| D | Verify Layer 1/3' wiring + regression trace | 1h |
| E | Three new test files (AC-014, AC-015, AC-016+AC-017) | 4h |

**Total**: 12 effort-hours (matches frontmatter).

**LOC**: ~865 lines across 7 files.

### Phase split for `--implement-only`

The recommended implementation sequence, each phase independently mergeable:

1. **Part A**: `coach_evidence.py` + `CoachValidator.gather_evidence()` + `validate()` shim. All existing tests must pass. No behaviour change.
2. **Part B**: Invert `_invoke_coach`. Requires Part A. Verify with `GUARDKIT_COACH_LEGACY=1` running CI.
3. **Part C**: Extend `_build_coach_prompt`. Requires Part B. Token-budget test can be run without a live LLM.
4. **Part D**: Verify Layer 1/3' wiring (read-only; mostly confirmation + AC-013 regression test structure).
5. **Part E**: Three test files. Requires Parts A–C. AC-015 and AC-016 require `FakeHarnessAdapter`.

---

## 10. Out of Scope

This task does NOT:
- Change `BDDPlugin`, `BDDRunResult`, or any `guardkitfactory.bdd.*` module (TASK-HMIG-007's concern).
- Change `HarnessAdapter`, `ClaudeSDKHarness`, `select_harness`, or `LangGraphHarness` dispatch (TASK-HMIG-006's concern).
- Migrate CLI entrypoints, direct-mode entrypoints, or the `guardkit autobuild task` CLI to use `LangGraphHarness` (TASK-HMIG-006.1, .2, .3).
- Flip the `GUARDKIT_HARNESS` default from `"sdk"` to `"langgraph"` (TASK-HMIG-009's concern).
- Remove or rewrite the existing `CoachValidator.validate()` logic. It is preserved in full inside `_apply_legacy_decision_logic`.
- Change `coach_turn_N.json` on-disk schema.
- Change `player_turn_N.json` on-disk schema or the Player prompt.

---

## 11. Open Questions

None that cannot be resolved from the code. The following were considered and resolved:

1. **Should `gather_evidence` still run `run_independent_tests`?**
   Yes. The independent test result is load-bearing evidence — the LLM Coach needs it to apply the `tests_run == 0` guard and to evaluate infrastructure-conditional approval. `gather_evidence` runs `run_independent_tests` and places the result in `bundle.independent_tests`. The LLM Coach reads it; `_apply_legacy_decision_logic` also reads it for the legacy path.

2. **What if `gather_evidence` raises?** *(Revised per Phase 2.5 review finding #1.)*
   `gather_evidence` MUST NOT fall back to `validate()` on exception — that would reactivate the path falsifier #1 requires to be GONE and bypass the `GUARDKIT_COACH_LEGACY=1` operator-controlled revert. Instead:
   - Internal failures (gate failure, honesty short-circuit) populate partial bundles with `gathering_status="partial_gate_abort"` / `"partial_honesty_abort"` and return normally.
   - Unexpected exceptions are caught in `_invoke_coach` (NOT inside `gather_evidence`); the orchestrator writes a synthetic `coach_turn_N.json` with `decision: "feedback"` and `rationale: "Evidence gathering failed: <exc>"`. The Coach is never bypassed by a deterministic fallback in the primary path.
   - `GUARDKIT_COACH_LEGACY=1` remains the sole operator-controlled mechanism for reactivating `validate()` as the decision maker. See §3 "Exception handling for gather_evidence" for the pseudocode.

3. **Does `invoke_coach` need a new public signature in `HarnessAdapter`?**
   No. `HarnessAdapter` dispatches on `(role, prompt, tools)`. The evidence bundle is serialised into the prompt text by `_build_coach_prompt` before `invoke_coach` calls the harness. The harness sees a longer prompt, not a new parameter.

4. **Is `BDDRunResult` importable in `coach_evidence.py` at the top level?**
   `guardkitfactory` is an optional dependency. Use a `TYPE_CHECKING` guard:
   ```python
   from __future__ import annotations
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from guardkitfactory.bdd.plugin import BDDRunResult
   ```
   At runtime, `bdd: Optional["BDDRunResult"]` — the field holds the object when guardkitfactory is installed; `None` otherwise. The JSON serialisation via `dataclasses.asdict()` works regardless because `BDDRunResult` is itself a dataclass.
