# Coach Runtime Verification — Implementation Guide

## Executive Summary

This feature adds runtime verification capability to the Coach validator, enabling it to verify acceptance criteria that require command execution (not just file-content analysis). The work is split into 4 waves with increasing architectural scope.

## Wave Structure

```
Wave 1 (Immediate Fix)      Wave 2 (Reliability)      Wave 3 (Architecture)      Wave 4 (Future)
+-------------------+       +------------------+       +------------------+       +------------------+
| CRV-412F:         |       | CRV-1540:        |       | CRV-9914:        |       | CRV-7DBC:        |
| Integrate         |       | CancelledError   |       | Extended Coach   |       | MCP Coach        |
| classifier        |       | partial data     |       | validator        |       | integration      |
|                   |       |                  |       |                  |       |                  |
| CRV-537E:         |       | CRV-9618:        |       | CRV-B275:        |       | CRV-3B1A:        |
| Orchestrator      |       | Carry forward    |       | Rate limit fix   |       | SDK sessions     |
| cmd execution     |       | best reqs        |       |                  |       |                  |
+-------------------+       |                  |       +------------------+       +------------------+
                            | CRV-90FB:        |
                            | Align stall      |
                            | detector         |
                            +------------------+
```

## Wave 1: Immediate Fix (Tier 1)

**Goal**: Directly fix the FEAT-2AAA class of failures

**Tasks**:
- **CRV-412F**: Integrate the criteria classifier POC into the Coach validation pipeline
- **CRV-537E**: Add orchestrator-level command execution for `command_execution` criteria

**Parallel execution**: YES — these tasks modify different files (coach_validator.py vs autobuild.py)

**Expected outcome**: Any task with command_execution acceptance criteria will be automatically verified by running the commands in the worktree, with results injected into the synthetic report.

## Wave 2: Reliability Improvements (Tier 2)

**Goal**: Improve reliability of state recovery and stall detection

**Tasks**:
- **CRV-1540**: Extract partial data from `response_messages` in CancelledError handler
- **CRV-9618**: Carry forward best `requirements_addressed` across turns
- **CRV-90FB**: Align stall detector criteria count with Coach

**Parallel execution**: YES — all three tasks modify different code paths

**Expected outcome**: Better state recovery after CancelledError, no regression in requirements_addressed over turns, accurate stall detection thresholds.

## Wave 3: Architecture (Tier 3)

**Goal**: Cleaner architecture with Coach-level runtime verification

**Tasks**:
- **CRV-9914**: Extend CoachValidator with runtime verification methods
- **CRV-B275**: Add rate limit detection to `_invoke_with_role()`

**Parallel execution**: YES — different code areas

**Expected outcome**: Coach validator has first-class runtime verification capability, structured rate limit errors for all SDK invocations.

## Wave 4: Future Capabilities (Tier 4)

**Goal**: Enable advanced verification (UI, API, browser)

**Tasks**:
- **CRV-7DBC**: MCP tool integration for Coach (Playwright, custom verifiers)
- **CRV-3B1A**: SDK sessions for Player resumption after CancelledError

**Parallel execution**: YES — independent subsystems

**Expected outcome**: Coach can verify UI rendering, API responses, and browser behavior. Player can resume from where it was cancelled instead of starting over.

## Implementation Mode Recommendations

| Task | Mode | Rationale |
|------|------|-----------|
| CRV-412F | task-work | Modifying core Coach pipeline, needs quality gates |
| CRV-537E | task-work | Adding execution to autobuild loop, needs quality gates |
| CRV-1540 | task-work | Modifying error handling in agent_invoker, needs quality gates |
| CRV-9618 | task-work | Modifying state tracking, needs quality gates |
| CRV-90FB | task-work | Modifying stall detection, needs quality gates |
| CRV-9914 | task-work | Major Coach enhancement, needs architectural review |
| CRV-B275 | direct | Simple pattern addition, low complexity |
| CRV-7DBC | task-work | New subsystem, needs architectural review |
| CRV-3B1A | task-work | Architectural change to SDK usage, needs review |

## Quick Start: Wave 1

### Prerequisites
```bash
# Verify criteria classifier exists
python -c "from guardkit.orchestrator.quality_gates.criteria_classifier import classify_acceptance_criteria; print('OK')"

# Run classifier tests
pytest tests/unit/test_criteria_classifier.py -v
```

### Implementation Steps
1. Start with CRV-412F (integrate classifier into Coach)
2. In parallel, start CRV-537E (orchestrator command execution)
3. Test with FEAT-2AAA criteria to validate the fix
4. Run full autobuild test suite

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Command execution outside worktree | Low | **Critical** | Defensive `_assert_worktree_path()` check — rejects non-worktree paths |
| Classifier mis-routing file_content criteria | Low | Medium | Routing layer on top (not replacement), conservative default to file_content |
| Pattern matching false positives | Low | Medium | Confidence scoring, fallback to file_content at 0.3 |
| Stale carry-forward requirements | Medium | Medium | Staleness check — re-validate source file existence and content |
| Performance impact on Coach | Low | Low | Commands only run for command_execution criteria |
| CancelledError partial data corruption | Low | Medium | Defensive parsing, validation before use |
| Zombie processes from server lifecycle | Medium | Medium | post_verification cleanup guaranteed (try/finally) |

## Key Design Constraints (from Regression Review)

1. **Worktree path assertion**: Never execute commands outside `.guardkit/worktrees/`
2. **Routing layer, not replacement**: Classifier routes on top of existing Path A/B/C — never replaces
3. **Instance attribute for partial data**: Use `self._last_partial_report`, not exception attributes
4. **Staleness check on carry-forward**: Re-validate previous requirements against current worktree state
5. **Orchestrator owns server lifecycle**: Coach is a pure verifier — never starts/stops services
