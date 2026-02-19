# Review Report: TASK-REV-F248 (Revised)

## Executive Summary

TASK-RK01-003 (Create Graphiti configuration template) stalled because the **direct mode invocation path does not produce `completion_promises` or `requirements_met` data**, causing the Coach validator to see 0/4 acceptance criteria met on every turn. The two succeeding tasks used task-work delegation, which produces agent-written player reports with rich `completion_promises` data. This is a **systematic gap in the direct mode pipeline**, not a one-off failure.

**This is the Q1 bug from the SFT-001 diagnostic diagrams** ([autobuild-diagnostic-diagrams.md:513](docs/reviews/feature-build/autobuild-diagnostic-diagrams.md#L513)) confirmed in the wild — the "direct mode + Coach rejection" path was flagged as untested and probable-buggy, and this RequireKit failure is its first production manifestation.

## Review Details

- **Mode**: Diagnostic Review
- **Depth**: Deep (revised after second-opinion challenge)
- **Scope**: FEAT-498F Wave 1 failure analysis (RequireKit v2 Refinement Commands)
- **Files Analysed**: `coach_validator.py`, `autobuild.py`, `agent_invoker.py`, `generate_feature_yaml.py`, full autobuild log, SFT-001 review report, diagnostic diagrams

---

## Finding 1: Root Cause — Direct Mode Synthetic Reports Have Empty `requirements_met`

**Severity**: Critical
**Evidence**: [agent_invoker.py:1789-1801](guardkit/orchestrator/agent_invoker.py#L1789-L1801)

When the direct mode SDK invocation completes, the Player agent does not write a `player_turn_N.json` report. The invoker detects this and calls `_create_synthetic_direct_mode_report()`, which creates a report with:

```python
"requirements_addressed": [],
"requirements_remaining": [],
```

This synthetic report has **no `completion_promises`** and **no `requirements_met`** data.

### The Data Flow That Fails

1. `_invoke_player_direct()` calls SDK — Player does work but doesn't write `player_turn_N.json`
2. Invoker detects missing report, calls `_create_synthetic_direct_mode_report()` (line 2607)
3. Synthetic report has empty `requirements_addressed` and no `completion_promises`
4. `_write_direct_mode_results()` writes `task_work_results.json` — no `_synthetic` flag, no promises
5. Coach reads `task_work_results.json`, finds no promises, falls back to text matching
6. Text matching against empty `requirements_met: []` → 0/4 criteria verified
7. Identical feedback produced every turn → stall detection after 3 turns

### Log Evidence

```
WARNING: Criteria verification 0/4 - diagnostic dump:
  AC text: Config file exists at `installer/global/config/graphiti.yaml`
  requirements_met: []
  completion_promises: (not used)
  matching_strategy: text
  _synthetic: False
```

The `_synthetic: False` is the smoking gun — the direct mode results file doesn't set this flag, so the Coach never enters the file-existence verification path that was specifically designed for this scenario.

## Finding 2: Two Separate Synthetic Report Paths — Only One Is Complete

**Severity**: Critical (upgraded from High — see Revision Notes)
**Evidence**: Compare [agent_invoker.py:1771-1827](guardkit/orchestrator/agent_invoker.py#L1771-L1827) vs [autobuild.py:2220-2354](guardkit/orchestrator/autobuild.py#L2220-L2354)

There are **two different synthetic report builders** in the codebase:

| Property | `agent_invoker._create_synthetic_direct_mode_report()` | `autobuild._build_synthetic_report()` |
|---|---|---|
| Sets `_synthetic: True` | No | Yes |
| Generates `completion_promises` | No | Yes (for scaffolding) |
| Uses file-existence matching | No | Yes |
| Accepts `acceptance_criteria` | No | Yes |
| Accepts `task_type` | No | Yes |
| Used by | Direct mode normal path | State recovery path |

The autobuild state recovery path (`_build_synthetic_report`) has all the scaffolding-aware intelligence (TASK-ASF-006), including file-existence promise generation. But the direct mode path in `agent_invoker` predates this work and was never updated.

**This is the same class of architectural fragility as dual implementations that diverge over time.** Every improvement to `_build_synthetic_report()` (TASK-ASF-006, TASK-ACR-004) was silently not applied to `_create_synthetic_direct_mode_report()`. The R4 recommendation from the SFT-001 review was implemented only on the recovery path, leaving the direct mode path broken.

## Finding 3: `_synthetic` Flag Alone Does Not Fix the Problem (Second-Opinion Confirmation)

**Severity**: Critical
**Evidence**: [coach_validator.py:1499-1515](guardkit/orchestrator/quality_gates/coach_validator.py#L1499-L1515)

The second opinion correctly identified that **R1 without R2 is useless**. Code tracing confirms:

```python
# coach_validator.py lines 1472-1515
is_synthetic = task_work_results.get("_synthetic", False)
if is_synthetic:
    completion_promises = self._load_completion_promises(task_work_results, turn)
    if completion_promises:
        # Path A: Match by promises → this is the happy path
        validation = self._match_by_promises(acceptance_criteria, completion_promises)
        return validation
    # Path B: No promises → ALL CRITERIA MARKED UNMET
    logger.warning("Synthetic report has no completion_promises — all criteria marked unmet")
    return self._build_all_unmet(acceptance_criteria)  # ← Still 0/4
```

Setting `_synthetic: True` (R1) without generating `completion_promises` (R2) simply changes the failure from "matching_strategy: text, 0/4" to "matching_strategy: synthetic (no promises), 0/4". The outcome is identical — UNRECOVERABLE_STALL.

**R1 and R2 must be treated as one atomic fix.**

## Finding 4: Task-Work Delegation vs Direct Mode — Structural Asymmetry

**Severity**: Medium
**Evidence**: Log comparison

| Aspect | task-work (TASK-RK01-001, 002) | direct (TASK-RK01-003) |
|---|---|---|
| Player report source | Agent-written | Synthetic (git detection) |
| `completion_promises` | 6-7 promises recovered | 0 promises |
| `requirements_addressed` | 6-7 items | Empty |
| Coach matching strategy | promises → hybrid | text (empty fallback) |
| Result | APPROVED (1 turn) | UNRECOVERABLE_STALL (3 turns) |

The task-work delegation path uses `inline implement protocol` which instructs the Claude Code agent to write a structured player report including completion promises. Direct mode invokes the SDK with a simpler prompt that doesn't instruct report writing.

## Finding 5: Scaffolding Task Type Was Correct But Starved of Data

**Severity**: Low
**Evidence**: Log line 168: `Using quality gate profile for task type: scaffolding`

The `scaffolding` profile correctly relaxed quality gates (tests not required, coverage not required, arch review not required). All gates passed. The failure was exclusively in the **requirements verification** step — the profile relaxation was appropriate but irrelevant to the actual failure mode.

## Finding 6: Player Was Actually Doing Work

**Severity**: Informational
**Evidence**: Log lines 162, 231, 399

- Turn 1: 22 files created, 1 modified
- Turn 2: 5 files created, 4 modified
- Turn 3: 1 file created

The Player was actively creating files (likely including `installer/global/config/graphiti.yaml`), but the Coach had no mechanism to verify this since:
1. No `completion_promises` were generated
2. No `_synthetic` flag meant no file-existence check
3. Text matching against empty `requirements_met` always returned 0/4

## Finding 7: Mode Assignment Ignores Acceptance Criteria Count (NEW)

**Severity**: Medium
**Evidence**: [generate_feature_yaml.py:268-269](installer/core/commands/lib/generate_feature_yaml.py#L268-L269)

The mode assignment logic in `generate_feature_yaml.py` is:

```python
# Line 268-269
if complexity <= 3:
    mode = "direct"
else:
    mode = "task-work"
```

And the runtime auto-detection in `_auto_detect_direct_mode()` ([agent_invoker.py:2411-2469](guardkit/orchestrator/agent_invoker.py#L2411-L2469)) uses the same complexity<=3 heuristic.

**Neither considers the number of acceptance criteria.** TASK-RK01-003 had 4 acceptance criteria but complexity 3, so it was assigned direct mode. Direct mode has no mechanism to verify acceptance criteria (synthetic reports are empty), so **any direct mode task with acceptance criteria will stall** unless the Player happens to write its own report.

This is a systemic issue. The question isn't just "why did TASK-RK01-003 fail?" but "why does the mode assignment allow tasks with acceptance criteria to enter a path where criteria can never be verified?"

## Finding 8: This Is Q1 from the Diagnostic Diagrams (NEW)

**Severity**: Confirmatory
**Evidence**: [autobuild-diagnostic-diagrams.md:513](docs/reviews/feature-build/autobuild-diagnostic-diagrams.md#L513)

The SFT-001 diagnostic diagrams explicitly flagged this as an untested path:

```
Q1: "direct mode + Coach rejection → Does feedback loop work
     without task_work_results.json?"
```

The diagrams marked Q1 as a "probable bug" (yellow). This RequireKit failure confirms it's a **confirmed bug** (red). The path was never exercised because previous direct mode tasks either:
- Had no acceptance criteria (trivial scaffolding)
- Succeeded on the first turn without Coach rejection
- Were manually reclassified to task-work before running

TASK-RK01-003 is the first production case of: direct mode + Coach rejection + scaffolding task type + multiple acceptance criteria.

---

## Root Cause Summary

```
generate_feature_yaml assigns implementation_mode=direct (complexity 3 ≤ threshold)
    ↓
_invoke_player_direct() calls SDK
    ↓
Player does work (22+ files created) but doesn't write player_turn_N.json
    ↓
agent_invoker._create_synthetic_direct_mode_report()
    - No _synthetic flag
    - No completion_promises
    - Empty requirements_addressed
    ↓
_write_direct_mode_results() writes task_work_results.json
    - No _synthetic flag → Coach doesn't enter file-existence path
    - No completion_promises → Coach falls back to text matching
    ↓
Coach._match_by_text() with empty requirements_met → 0/4 criteria verified
    ↓
Identical feedback every turn → UNRECOVERABLE_STALL after 3 turns
```

**Why the fix in autobuild.py didn't help**: The TASK-ASF-006 fix (file-existence promises in `_build_synthetic_report()`) was applied to the **state recovery** path in autobuild.py. Direct mode uses a **separate synthetic report builder** in agent_invoker.py that was never updated.

---

## Recommendations (Revised)

### R1+R2 (Atomic): Generate file-existence promises in direct mode synthetic reports AND propagate `_synthetic` flag (Critical)

**These must be implemented together. R1 alone changes the error message but not the outcome.**

**Fix**: Enhance `_create_synthetic_direct_mode_report()` ([agent_invoker.py:1771](guardkit/orchestrator/agent_invoker.py#L1771)) to:
1. Accept `acceptance_criteria` and `task_type` parameters
2. Set `_synthetic: True` in the report
3. Generate `completion_promises` using the same file-existence matching logic as `_build_synthetic_report()` in autobuild.py

Then update `_write_direct_mode_results()` ([agent_invoker.py:2767](guardkit/orchestrator/agent_invoker.py#L2767)) to:
1. Accept and propagate the `_synthetic` flag
2. Include `completion_promises` from the report

**Call chain change**:
```
_invoke_player_direct()
    → _create_synthetic_direct_mode_report(task_id, turn, acceptance_criteria, task_type)
    → _write_direct_mode_results(task_id, report, success=True, synthetic=True)
```

### R3: Unify the two synthetic report builders (Critical — upgraded from Medium)

**Fix**: Consolidate `_create_synthetic_direct_mode_report()` (agent_invoker) and `_build_synthetic_report()` (autobuild) into a single shared function with consistent behaviour.

**Rationale**: The second opinion correctly identifies this as the same class of architectural fragility that causes divergence bugs. Every improvement to one builder silently skips the other. This has already happened once (TASK-ASF-006 applied to autobuild but not agent_invoker), and will happen again if R1+R2 is implemented as a point fix without unification.

**Implementation**: Extract into `guardkit/orchestrator/synthetic_report.py`:
```python
def build_synthetic_report(
    task_id: str,
    turn: int,
    work_state: WorkState,
    acceptance_criteria: Optional[List[str]] = None,
    task_type: Optional[str] = None,
    source: str = "direct_mode",  # or "state_recovery"
) -> Dict[str, Any]:
```

Both `_create_synthetic_direct_mode_report()` and `_build_synthetic_report()` become thin wrappers that delegate to this shared function.

### R4: Add acceptance criteria count to mode assignment heuristic (Medium)

**Fix**: Update the mode assignment in both locations:
- [generate_feature_yaml.py:268](installer/core/commands/lib/generate_feature_yaml.py#L268) (planning time)
- [agent_invoker.py:2446](guardkit/orchestrator/agent_invoker.py#L2446) (runtime auto-detection)

**Change**: Tasks with >=2 acceptance criteria should default to `task-work` regardless of complexity, because direct mode currently cannot verify criteria. Alternatively, this guard can be removed once R1+R2+R3 are implemented and direct mode can actually verify criteria.

**Rationale**: This addresses the systemic question: why does the system allow tasks into a path where their acceptance criteria can never be verified?

### R5: Add direct mode criteria matching integration test (Medium)

**Fix**: Add a test that exercises: direct mode invocation → synthetic report → Coach validation for a scaffolding task with file-existence acceptance criteria.

**Rationale**: This code path was untested (confirmed by Q1 in the diagnostic diagrams), which allowed the gap to persist across multiple TASK-ASF and TASK-ACR improvements.

### R6: Consider upgrading direct mode to include report-writing instructions (Low)

**Fix**: Modify the direct mode player prompt (`_build_player_prompt()`) to instruct the SDK agent to write a `player_turn_N.json` report, similar to what the inline implement protocol does.

**Rationale**: This would eliminate the need for synthetic reports entirely in the direct mode path, providing the same data quality as task-work delegation. However, this is a larger change that may affect Player behaviour and SDK turn counts.

---

## Decision: Re-Run Configuration

**Immediate action**: Change TASK-RK01-003's `implementation_mode` from `direct` to `task-work` in the feature YAML and re-run. This is a 5-minute config change that routes through the proven task-work path.

**Proper fix**: Implement R1+R2+R3 as one atomic change, then R4+R5.

**Priority ordering**:
1. Switch to task-work and re-run (5 min, unblocks now)
2. R1+R2+R3: Unified synthetic report builder with file-existence promises (1-2 days)
3. R4: Mode assignment guard for tasks with acceptance criteria (0.5 day)
4. R5: Integration test coverage (0.5 day)
5. R6: Direct mode report-writing instructions (future, optional)

---

## Revision Notes

Changes from initial review based on second-opinion challenge:

| Change | Rationale |
|--------|-----------|
| R1+R2 merged as atomic | Coach code trace confirms R1 alone hits `_build_all_unmet()` — same 0/4 result |
| R3 upgraded to Critical | Dual builders are an architectural fragility class — TASK-ASF-006 already proved they diverge |
| Finding 7 added (mode assignment) | `generate_feature_yaml.py` assigns direct mode purely on complexity, ignoring AC count |
| Finding 8 added (Q1 confirmation) | Links to SFT-001 diagnostic diagrams that predicted this exact bug class |
| R4 added (mode assignment guard) | Addresses systemic root cause, not just the symptom |

---

## Appendix

### Acceptance Criteria Verification

- [x] Root cause of TASK-RK01-003 stall identified with evidence (Findings 1, 3, 8)
- [x] Direct mode vs task-work delegation gap documented (Findings 2, 4, 7)
- [x] Criteria matching strategy evaluated for scaffolding tasks (Findings 3, 5)
- [x] Actionable recommendations for GuardKit improvements provided (R1-R6)
- [x] Decision on whether to re-run with different configuration (see Decision section)

### File References

| File | Key Lines | Relevance |
|------|-----------|-----------|
| [agent_invoker.py](guardkit/orchestrator/agent_invoker.py) | 1771-1827, 2411-2469, 2539-2726, 2728-2806 | Direct mode invocation, auto-detection, synthetic report |
| [autobuild.py](guardkit/orchestrator/autobuild.py) | 2220-2354, 2356-2428 | State recovery synthetic report + file-existence promises |
| [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) | 1440-1565, 1499-1515, 1810-1890 | Criteria matching (promises vs text vs synthetic-no-promises) |
| [generate_feature_yaml.py](installer/core/commands/lib/generate_feature_yaml.py) | 268-269, 503 | Mode assignment (complexity-only heuristic) |
| [autobuild-diagnostic-diagrams.md](docs/reviews/feature-build/autobuild-diagnostic-diagrams.md) | 513 | Q1 prediction of this bug class |
| [TASK-REV-SFT1-review-report.md](.claude/reviews/TASK-REV-SFT1-review-report.md) | Finding 2, R4 | Prior identification of synthetic report gap |

### Cross-References

- **SFT-001 review**: First identified synthetic reports can't satisfy Coach criteria (Finding 2)
- **TASK-ASF-006**: Implemented file-existence promises — but only on state recovery path
- **TASK-ACR-004**: Implemented git-analysis promises — but only on state recovery path
- **Q1 diagnostic diagram**: Predicted "direct mode + Coach rejection" as probable bug
