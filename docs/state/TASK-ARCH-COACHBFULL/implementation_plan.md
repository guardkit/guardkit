# Implementation Plan — TASK-ARCH-COACHBFULL (B-full investigating Coach)

> Strict intensity · complexity 7 · feature · parent TASK-ARCH-COACHSPLIT
> Decisions (Phase 1.6): `GUARDKIT_COACH_GATHER` default **OFF (opt-in)**;
> AC-3 proven **both** ways (deterministic CI test + one-off live gemma run).

## Goal

Chain a tool-using **Phase-A gather** before the existing toolless **Phase-B
synthesis** in the AutoBuild Coach, so the Coach can *investigate* (read changed
files, run focused tests, check ACs) and feed *findings text* into the
grammar-constrained verdict — restoring the Block-paper investigating Coach
**without** regressing B-min's reliable verdict emission. Gated behind
`GUARDKIT_COACH_GATHER` (default OFF). Any gather failure degrades to B-min.

## Architecture (where the two calls live)

`invoke_coach` ([agent_invoker.py:1919](../../../guardkit/orchestrator/agent_invoker.py#L1919))
already computes `synthesis_enabled = _coach_synthesis_enabled() and bundle is not None`
and dispatches one toolless `_invoke_with_role(synthesis=True, grammar=…)`.

B-full inserts, *before* that call, an optional Phase-A:

```
invoke_coach
 ├─ honesty = bundle.honesty (unchanged)
 ├─ synthesis_enabled = _coach_synthesis_enabled() and bundle is not None
 ├─ NEW: gather_findings = None
 │   if synthesis_enabled and _coach_gather_enabled():
 │       gather_findings = await _invoke_coach_gather(...)   # Phase A, tool-bound
 ├─ prompt = _build_coach_prompt(..., synthesis=synthesis_enabled,
 │                                acceptance_criteria=ac_structured,   # AC-4
 │                                gather_findings=gather_findings)     # AC-1
 └─ Phase-B synthesis call (unchanged)
```

Phase A reuses the existing `_invoke_with_role` plumbing, so it inherits the
per-call cancel monitor ([agent_invoker.py:3220](../../../guardkit/orchestrator/agent_invoker.py#L3220))
**for free** (AC-5 cancellation) and the read-only Coach tool set
`[Read, Bash, Grep, Glob]` (FB-004 / feature-build-invariants preserved — Coach
still has no Write/Edit, and never emits the verdict; the orchestrator parses
Phase B).

## Changes

### 1. `guardkit/orchestrator/agent_invoker.py`

**(a) Gate helper** (beside `_coach_synthesis_enabled`, ~L549). Default **OFF**:
```python
_COACH_GATHER_ENABLED_VALUES = frozenset({"1", "true", "yes", "on"})
def _coach_gather_enabled() -> bool:
    raw = os.environ.get("GUARDKIT_COACH_GATHER")
    return False if raw is None else raw.strip().lower() in _COACH_GATHER_ENABLED_VALUES
```

**(b) Budget-split constants** (module level, AC-5):
```python
_COACH_GATHER_BUDGET_FRACTION = 0.4   # Phase A ≤ 40% of effective Coach timeout
_COACH_GATHER_BUDGET_MIN_S = 60       # floor so a tight budget still gathers
```
Phase A capped at `min(max(60, 0.4·effective), effective)`; Phase B keeps the
**full** effective timeout (never starve the load-bearing synthesis). Combined
wall-clock bound ≤ **1.4× effective** — bounded + documented as the opt-in cost.
(Tighter `≤1×` by subtracting gather-spend was considered and rejected: it risks
synthesis timeouts on the slow substrate; revisit under P-5/TASK-PERF-COACHSYNTH.)

**(c) `_invoke_coach_gather(...) -> Optional[str]`** — Phase A. Sets
`sdk_timeout_seconds = gather_timeout` (restored in `finally`), builds the gather
prompt, calls `_invoke_with_role(allowed_tools=[Read,Bash,Grep,Glob],
synthesis=False, return_events=True)`, extracts findings via
`_collect_assistant_text` (fallback `_collect_assistant_reasoning`). Returns the
findings string or `None`. **`except Exception → return None`** (strict
dominance, AC-2) — `CancelledError` is `BaseException` so genuine cancel
propagates (AC-5), never silently degrades.

**(d) `_build_coach_gather_prompt(...)`** — investigation prompt. Reuses
`_render_evidence_bundle_section` + honesty + a structured AC checklist. Explicit
instruction: **investigate and emit per-AC findings (✅/❌ + notes), NOT a fenced
JSON verdict.** No `Decision Format` section, no grammar.

**(e) `invoke_coach` signature** — add `acceptance_criteria: Optional[List[Dict[str,str]]] = None`.
Thread into both the gather prompt and `_build_coach_prompt` (AC-4 root-cause
fix: today `invoke_coach` calls `_build_coach_prompt` with **no** ACs, so the
"verify EACH criterion" section + example are empty → run-19 `criteria_verification: []`).

**(f) `_build_coach_prompt` signature** — add `gather_findings: Optional[str] = None`.
When present, render a `## Coach Investigation Findings (Phase A)` section before
`## Decision Format`, framed as advisory evidence to ground the per-AC verdict.

### 2. `guardkit/orchestrator/autobuild.py`

`_invoke_coach_primary` ([autobuild.py:5533](../../../guardkit/orchestrator/autobuild.py#L5533)):
normalize its `acceptance_criteria: List[str]` → `List[{id,text}]` (extract a
leading `AC-\d+` if present, else generate `AC-001…`) and pass via the
signature-probe block (same `inspect.signature` guard already used for
`evidence_bundle`/`coach_context`, so a partial rollout never breaks).

### 3. Tests

- `tests/unit/orchestrator/test_coach_gather.py`
  - AC-1: gather enabled ⇒ two `_invoke_with_role` calls (one tool-bound
    `synthesis=False`, one toolless `synthesis=True`); findings reach the
    synthesis prompt.
  - AC-2: gather raises / empty / timeout ⇒ exactly one synthesis call, valid
    verdict, turn not failed (degrade-to-B-min).
  - AC-2/AC-5: gather raises `CancelledError` ⇒ propagates (not swallowed).
  - AC-5: budget — Phase A `sdk_timeout_seconds` ≤ slice; restored to effective
    for Phase B.
  - flag OFF (default) ⇒ zero gather calls (pure B-min) — regression guard.
- `tests/integration/orchestrator/test_coach_bfull_falsifier.py`
  - **AC-3 deterministic**: fake harness whose Phase-A "investigates" and reports
    a stubbed AC ⇒ B-full returns `feedback`; same green bundle with gather OFF
    (B-min) ⇒ `approve`. The empirical proof.
- AC-6: empty gather + minimal/absent-signal bundle ⇒ **not** auto-approve
  (existing absence-of-failure guards; assert verdict ≠ unconditional approve).
- AC-4: synthesis prompt contains the per-AC checklist + example when ACs threaded.

### 4. AC-3 live confirmation (the "both")

One-off `GUARDKIT_COACH_GATHER=1` autobuild run of a seeded falsifier task vs the
real gemma4:31b coach on GB10; capture verdict + llama-swap log (two g31 calls/turn)
to `docs/state/TASK-ARCH-COACHBFULL/ac3-live-confirmation.md`. Non-CI, evidential.

## Risk / invariants

- **FB-004 / read-only Coach**: Phase A tools = `[Read,Bash,Grep,Glob]`; Coach
  never writes the verdict. Preserved.
- **harness-cancellation-contract**: per-call monitor covers Phase A; cancel
  propagates. Test asserts it.
- **absence-of-failure**: findings are advisory; absent findings ⇒ B-min, never a
  new false-green. Synthesis guards unchanged.
- **Strict dominance**: every Phase-A failure mode degrades to today's behaviour.
- **Default OFF**: zero behaviour change until `GUARDKIT_COACH_GATHER=1`.

## Phase 2.5B architectural assessment

- **SOLID** ~90: additive, single-responsibility gather method; `invoke_coach`
  orchestrates, `_invoke_with_role` unchanged. **DRY** ~88: reuses evidence/honesty
  renderers + `_collect_assistant_text`; AC-normalizer is the only new helper.
  **YAGNI** ~92: one opt-in flag, no speculative config. No new substrate coupling.
- Verdict: **approve** — surgical, gated, reversible.

## Out of scope

Promotion to default ON (separate dated commit after P-1…P-5); resident-g31
latency work (TASK-PERF-COACHSYNTH); grammar changes (criteria_verification stays
prompt-driven per coach-verdict.gbnf design notes — no over-constraining).
