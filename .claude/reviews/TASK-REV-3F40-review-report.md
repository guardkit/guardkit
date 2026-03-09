# Review Report: TASK-REV-3F40

## Executive Summary

FEAT-2AAA (Video Info Tool) failed with UNRECOVERABLE_STALL on TASK-VID-001 after 9 turns because **the acceptance criteria require runtime verification (`pip install`, `python -c "import ..."`) that the Coach's synthetic report path cannot verify**. The Coach uses file-existence and text-matching heuristics against `requirements_addressed`, but TASK-VID-001's criteria are command-execution assertions, not file-existence assertions. The Player *did* modify `pyproject.toml` correctly, but the Coach could never confirm the criteria were met.

This is a **Coach verification gap** for runtime-verification acceptance criteria, compounded by the Anthropic SDK CancelledError forcing every turn through the synthetic report path (which lacks the structured `requirements_addressed` data that the Anthropic Agent SDK would normally provide).

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~15 minutes
- **Reviewer**: Manual log analysis

---

## Root Cause Analysis

### Primary Cause: Acceptance Criteria Type Mismatch

TASK-VID-001's acceptance criteria are **runtime verification commands**:

1. `` `yt-dlp>=2024.1.0` added to `dependencies` list in `pyproject.toml` `` (file content check)
2. `` `pip install -e ".[dev]"` succeeds without errors `` (command execution check)
3. `` `python -c "import yt_dlp; print(yt_dlp.version.__version__)"` runs successfully `` (command execution check)

The Coach validator uses a **synthetic report** path because every Player invocation fails with CancelledError (Anthropic SDK timeout). The synthetic report path:

1. Generates `file-existence promises` from git diff
2. Infers `requirements_addressed` from file content analysis
3. Uses `hybrid fallback` text matching to match criteria

**The problem**: Criteria #2 and #3 are command-execution assertions. The synthetic report can only verify file existence and text content. It **cannot execute `pip install` or `python -c`**. These criteria will never match via text matching against file content.

**Evidence**:
- Turn 1: `Inferred 2 requirements_addressed` → Coach matched 2/3 criteria (67%) — criteria #1 matched via file content
- Turn 2: Only `Generated 3 file-existence promises` (no requirements_addressed inferred) → 1/3 (33%)
- Turns 3-9: `0/3 verified (0%)` — zero criteria matched consistently
- The stall detector saw identical feedback signature `fc1ca613` for 5+ turns

### Secondary Cause: CancelledError on Every Turn

Every Player invocation on Anthropic models terminates with `CancelledError: Cancelled via cancel scope`. This forces the system into state recovery → synthetic report → Coach validation. The Player *does work* (git shows files modified), but the structured Player report lacks proper `requirements_addressed` because the SDK stream was cancelled before the agent could produce completion artifacts.

**Timing evidence from FEAT-2AAA**:
| Turn | Player Duration | Outcome |
|------|----------------|---------|
| 1 | ~3 min (150s+ elapsed) | CancelledError |
| 2 | ~1.3 min (60s+ elapsed) | CancelledError |
| 3 | ~1.3 min (60s+ elapsed) | CancelledError |
| 4-9 | ~30-60s each | CancelledError |

The SDK timeout is set to `sdk_timeout=1200s` (20 min), but the CancelledError triggers much earlier (~60-150s). This suggests the cancel comes from the Anthropic async generator pattern, not the SDK timeout.

### Why FEAT-SKEL-001 Succeeded Despite Same CancelledError

FEAT-SKEL-001 had the **exact same CancelledError pattern** on every turn, but succeeded because:

| Factor | FEAT-SKEL-001 (Success) | FEAT-2AAA (Failure) |
|--------|------------------------|---------------------|
| **Criteria type** | File-existence only (e.g., "pyproject.toml exists with correct metadata") | Runtime commands (`pip install`, `python -c "import..."`) |
| **requirements_addressed** | TASK-SKEL-001: 10 inferred → 10/10 matched (turn 1) | TASK-VID-001: 2 inferred → 2/3 matched (turn 1), then 0/3 |
| **Synthetic report** | File-existence promises aligned with criteria | File-existence promises cannot satisfy command-execution criteria |
| **TASK-SKEL-004** | Took 6 turns but criteria were file-existence → eventually 6/6 via text matching | 9 turns, never reached 3/3 |

**Key insight**: TASK-SKEL-004 also took 6 turns with the same CancelledError on every turn, but its criteria were verifiable via file-existence text matching. On turn 6, `Inferred 6 requirements_addressed` → all 6 criteria matched → approved.

### Contributing Factors

1. **Stall detector counted 2 criteria as passing** (line 1037: "2 criteria passing but stuck for 7 turns") but the Coach consistently reported 0/3 verified from turn 3 onwards. This discrepancy suggests the stall detector counts criteria differently from the Coach validator.

2. **Perspective resets at turns 3 and 5** did not help — the Player likely re-did the same file changes, and the Coach still couldn't verify runtime criteria.

3. **48 tests failing** on every turn — tests were already present in the worktree from FEAT-SKEL-001, and the Player was not fixing them. However, tests are `required=False` for scaffolding tasks, so this didn't block Coach validation.

---

## Comparison Matrix

| Dimension | FEAT-SKEL-001 (Success) | FEAT-2AAA (Failure) |
|-----------|------------------------|---------------------|
| Tasks | 4 tasks, 4 waves | 5 tasks, 5 waves |
| Total turns | 9 (across all tasks) | 9 (stuck on task 1) |
| Duration | 24m 42s | 14m 26s |
| CancelledError | Every turn on every task | Every turn |
| State recovery | Always successful | Always successful |
| Synthetic reports | Used for all tasks | Used for all turns |
| Criteria types | All file-existence verifiable | 2/3 runtime-command |
| requirements_addressed (best) | 10 inferred (TASK-SKEL-001) | 2 inferred (turn 1 only) |
| Longest single task | TASK-SKEL-004: 6 turns → approved | TASK-VID-001: 9 turns → stall |
| task_type | scaffolding | scaffolding |
| Graphiti vector mismatch | Yes (non-blocking) | Yes (non-blocking) |

---

## Findings

### Finding 1: Coach Cannot Verify Runtime-Execution Criteria (Critical)

The Coach validator's synthetic report path has no mechanism to verify acceptance criteria that require running commands. The `requirements_addressed` inference analyzes file content for keywords, not command execution results.

### Finding 2: CancelledError Is Systematic on Anthropic Models (High)

Every Player invocation terminates early. State recovery catches the work, but the Player never returns structured `requirements_addressed` or `completion_promises`. This forces 100% of turns through the synthetic report path, which has lower verification fidelity.

### Finding 3: requirements_addressed Inference Degrades Over Turns (Medium)

Turn 1: 2 `requirements_addressed` inferred. Turns 2+: 0 inferred. When the Player makes incremental (not full) changes, the content analysis finds fewer matches. The "best turn" result isn't carried forward.

### Finding 4: Stall Detector Criteria Count Mismatch (Low)

The stall detector reported "2 criteria passing" while the Coach consistently reported 0/3 verified from turn 3 onwards. This may cause the extended threshold (5 turns for partial progress) to apply incorrectly, delaying the stall termination.

---

## Recommendations

### Recommendation 1: Rewrite Task Acceptance Criteria (Immediate Fix)

**Effort**: Low | **Impact**: High | **Risk**: Low

Rewrite TASK-VID-001's acceptance criteria to be file-content-verifiable rather than runtime-command-verifiable:

**Before** (unverifiable by Coach):
```
- [ ] `pip install -e ".[dev]"` succeeds without errors
- [ ] `python -c "import yt_dlp; print(yt_dlp.version.__version__)"` runs successfully
```

**After** (verifiable by Coach):
```
- [ ] `yt-dlp>=2024.1.0` appears in the `dependencies` list in `pyproject.toml`
- [ ] No syntax errors in `pyproject.toml` (valid TOML)
```

This applies to all FEAT-2AAA tasks — audit each task's criteria for runtime-command assertions and convert to file-content assertions.

### Recommendation 2: Add Acceptance Criteria Classification in Coach (GuardKit Fix)

**Effort**: Medium | **Impact**: High | **Risk**: Low

Add a criteria classification step that categorizes each acceptance criterion as:
- `file_content` — verifiable via file existence/content
- `command_execution` — requires running a command
- `manual` — requires human verification

For `command_execution` criteria in the synthetic report path, either:
- a) **Auto-execute the command** and check exit code (preferred)
- b) **Mark as unverifiable** and require fewer verifiable criteria for approval
- c) **Skip unverifiable criteria** and approve if all verifiable criteria pass

### Recommendation 3: Investigate and Fix CancelledError on Anthropic SDK (GuardKit Fix)

**Effort**: High | **Impact**: High | **Risk**: Medium

The CancelledError terminates Player invocations after ~60-150s despite `sdk_timeout=1200s`. This likely relates to the Anthropic async generator cancel scope pattern. Investigate:
- Is the cancel coming from the Anthropic SDK's streaming implementation?
- Can the cancel scope timeout be configured?
- Is there a graceful shutdown path that preserves structured output?

### Recommendation 4: Carry Forward Best requirements_addressed Across Turns (GuardKit Fix)

**Effort**: Low | **Impact**: Medium | **Risk**: Low

When the synthetic report infers fewer `requirements_addressed` than a previous turn, merge with the best previous turn's results. This prevents regression where turn 1 matched 2/3 criteria but turn 2 matched only 1/3.

### Recommendation 5: Align Stall Detector with Coach Criteria Count (GuardKit Fix)

**Effort**: Low | **Impact**: Low | **Risk**: Low

The stall detector reported "2 criteria passing" while Coach reported 0/3. Ensure both use the same criteria verification source to avoid incorrect extended thresholds.

---

## Decision Matrix

| Option | Impact | Effort | Risk | Recommendation |
|--------|--------|--------|------|----------------|
| 1. Rewrite task criteria | High | Low | Low | **Do first** |
| 2. Criteria classification in Coach | High | Medium | Low | **Do second** |
| 3. Fix CancelledError | High | High | Medium | Investigate |
| 4. Carry forward requirements_addressed | Medium | Low | Low | Quick win |
| 5. Align stall detector counts | Low | Low | Low | Quick win |

---

## Decision: Both Task Definitions AND GuardKit Orchestrator

The failure is caused by a combination of:
1. **Task definition issue**: Acceptance criteria use runtime commands that the Coach cannot verify
2. **GuardKit orchestrator issue**: The synthetic report path has no mechanism for runtime-command criteria verification

**Immediate action**: Rewrite FEAT-2AAA task criteria (option 1) and re-run.
**Follow-up**: Implement criteria classification (option 2) to prevent this class of failure for future tasks.
**Investigation**: Track down CancelledError root cause (option 3) — this is the underlying reason the system falls back to synthetic reports.

---

## Appendix: Key Log Evidence

### Criteria Progression (TASK-VID-001)

| Turn | Verified | Rejected | Status |
|------|----------|----------|--------|
| 1 | 2/3 (67%) | 1 | feedback |
| 2 | 1/3 (33%) | 2 | feedback |
| 3 | 0/3 (0%) | 3 | feedback |
| 4 | 1/3 (33%) | 2 | feedback |
| 5-9 | 0/3 (0%) | 3 | feedback → stall |

### Criteria Progression (TASK-SKEL-004 — Success Case)

| Turn | Verified | Rejected | Status |
|------|----------|----------|--------|
| 1 | 5/6 (83%) | 1 | feedback |
| 2 | 1/6 (17%) | 5 | feedback |
| 3-5 | 0/6 (0%) | 6 | feedback |
| 6 | 6/6 (100%) | 0 | **approved** |

### File Changes per Turn (TASK-VID-001)

| Turn | Git Detection | Synthetic Report |
|------|--------------|-----------------|
| 1 | 8 files (+1/-0) | 1 created, 1 modified |
| 2 | 4 files (+2/-2) | 0 created, 1 modified |
| 3 | 3 files (+11/-3) | 0 created, 0 modified |
| 4-9 | 3-4 files (+11/-3) | 0 created, 0-1 modified |

---

# DEEP DIVE ANALYSIS (Revision)

## C4 Context Diagram: AutoBuild System

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AutoBuild System                            │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Feature     │───▶│  AutoBuild   │───▶│  Coach Validator    │  │
│  │ Orchestrator  │    │ Orchestrator │    │  (Quality Gates)    │  │
│  └──────────────┘    └──────┬───────┘    └──────────┬───────────┘  │
│                             │                       │               │
│                    ┌────────▼────────┐    ┌─────────▼──────────┐   │
│                    │ Agent Invoker   │    │ Synthetic Report   │   │
│                    │ (Player/Coach)  │    │ Builder            │   │
│                    └────────┬────────┘    └────────────────────┘   │
│                             │                                       │
│                    ┌────────▼────────┐    ┌────────────────────┐   │
│                    │ State Tracker   │    │  Stall Detector    │   │
│                    │ + Recovery      │    │                    │   │
│                    └────────┬────────┘    └────────────────────┘   │
│                             │                                       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────────┐
              │               │                   │
     ┌────────▼──────┐ ┌─────▼──────┐ ┌──────────▼──────┐
     │ Anthropic SDK │ │    Git     │ │   Test Runner   │
     │ (Claude Code  │ │ Worktree   │ │   (pytest)      │
     │  CLI/query()) │ │            │ │                 │
     └───────────────┘ └────────────┘ └─────────────────┘
```

## C4 Container Diagram: Verification Pipeline

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Coach Validator Container                              │
│                                                                            │
│  ┌─────────────────┐     ┌──────────────────────┐                         │
│  │ validate_        │────▶│ is_synthetic?        │                         │
│  │ requirements()   │     │                      │                         │
│  └─────────────────┘     └───────┬──────────────┘                         │
│                                  │                                         │
│                    ┌─────────────▼─────────────┐                          │
│                    │    YES: Synthetic Path     │                          │
│                    └─────────────┬──────────────┘                          │
│                                  │                                         │
│              ┌───────────────────┼──────────────────┐                     │
│              │                   │                   │                     │
│    ┌─────────▼──────┐ ┌─────────▼──────┐ ┌─────────▼──────┐             │
│    │ PATH A:        │ │ PATH B:        │ │ PATH C:        │             │
│    │ Promises +     │ │ Text Match     │ │ All Unmet      │             │
│    │ Hybrid         │ │ (no promises,  │ │ (no data)      │             │
│    │ Fallback       │ │ has req_addr)  │ │                │             │
│    └────────┬───────┘ └────────┬───────┘ └────────┬───────┘             │
│             │                  │                   │                     │
│    ┌────────▼───────┐         │                   │                     │
│    │ _match_by_     │         │                   │                     │
│    │ promises()     │         │                   │                     │
│    └────────┬───────┘         │                   │                     │
│             │                  │                   │                     │
│    ┌────────▼───────┐ ┌───────▼────────┐         │                     │
│    │ _hybrid_       │ │ _match_by_     │         │                     │
│    │ fallback()     │ │ text()         │         │                     │
│    │ [text matching]│ │ [3-level       │         │                     │
│    │                │ │  matching]     │         │                     │
│    └────────┬───────┘ └───────┬────────┘         │                     │
│             │                  │                   │                     │
│             ▼                  ▼                   ▼                     │
│    ┌────────────────────────────────────────────────────┐               │
│    │            CriterionResult[]                        │               │
│    │  verified / rejected / pending for each AC          │               │
│    └────────────────────────────────────────────────────┘               │
└────────────────────────────────────────────────────────────────────────────┘
```

## Sequence Diagram: TASK-VID-001 Failure Flow (Turn 1)

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│AutoBuild │  │ Agent    │  │Anthropic │  │  State   │  │Synthetic │  │  Coach   │
│Orch.     │  │ Invoker  │  │ SDK      │  │ Tracker  │  │ Report   │  │Validator │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │              │              │              │
     │ invoke_player│              │              │              │              │
     │─────────────▶│              │              │              │              │
     │              │ query(prompt)│              │              │              │
     │              │─────────────▶│              │              │              │
     │              │              │              │              │              │
     │              │  heartbeat   │ Player works │              │              │
     │              │  30s...60s.. │ (modifies    │              │              │
     │              │  90s...120s  │  pyproject)  │              │              │
     │              │  150s...     │              │              │              │
     │              │              │              │              │              │
     │              │  CancelledError             │              │              │
     │              │◀─ ─ ─ ─ ─ ─ ┤              │              │              │
     │              │ (cancel scope│              │              │              │
     │              │  ~150s)      │              │              │              │
     │              │              │              │              │              │
     │ failure result              │              │              │              │
     │◀─────────────┤              │              │              │              │
     │              │              │              │              │              │
     │ _attempt_state_recovery()   │              │              │              │
     │─────────────────────────────────────────▶│              │              │
     │              │              │ capture_state │              │              │
     │              │              │ git: 8 files  │              │              │
     │              │              │ tests: 48 fail│              │              │
     │              │              │ player_report │              │              │
     │ WorkState    │              │              │              │              │
     │◀─────────────────────────────────────────┤              │              │
     │              │              │              │              │              │
     │ _build_synthetic_report()   │              │              │              │
     │──────────────────────────────────────────────────────▶│              │
     │              │              │              │ 3 file-exist │              │
     │              │              │              │ promises     │              │
     │              │              │              │ 2 req_addr   │              │
     │ synthetic report            │              │ inferred     │              │
     │◀──────────────────────────────────────────────────────┤              │
     │              │              │              │              │              │
     │ validate_requirements(synthetic=True)      │              │              │
     │─────────────────────────────────────────────────────────────────────▶│
     │              │              │              │              │              │
     │              │              │              │              │  PATH A:     │
     │              │              │              │              │  promises +  │
     │              │              │              │              │  hybrid      │
     │              │              │              │              │              │
     │              │              │              │              │  AC-001:     │
     │              │              │              │              │  "yt-dlp in  │
     │              │              │              │              │  pyproject"  │
     │              │              │              │              │  → VERIFIED  │
     │              │              │              │              │  (text match │
     │              │              │              │              │   via hybrid)│
     │              │              │              │              │              │
     │              │              │              │              │  AC-002:     │
     │              │              │              │              │  "pip install│
     │              │              │              │              │   succeeds"  │
     │              │              │              │              │  → REJECTED  │
     │              │              │              │              │  (no file    │
     │              │              │              │              │   pattern,   │
     │              │              │              │              │   no keyword │
     │              │              │              │              │   match in   │
     │              │              │              │              │   files)     │
     │              │              │              │              │              │
     │              │              │              │              │  AC-003:     │
     │              │              │              │              │  "python -c  │
     │              │              │              │              │  import..."  │
     │              │              │              │              │  → VERIFIED  │
     │              │              │              │              │  (text match │
     │              │              │              │              │  "yt_dlp" in │
     │              │              │              │              │  file content│
     │              │              │              │              │  — FALSE     │
     │              │              │              │              │    POSITIVE) │
     │              │              │              │              │              │
     │ 2/3 verified, 1 rejected   │              │              │              │
     │◀─────────────────────────────────────────────────────────────────────┤
     │              │              │              │              │              │
     │ FEEDBACK: "Not all criteria met: pip install"           │              │
     │              │              │              │              │              │
```

## Sequence Diagram: TASK-VID-001 Turns 3-9 (Degradation Pattern)

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│AutoBuild │  │Synthetic │  │  Coach   │  │  Stall   │
│Orch.     │  │ Report   │  │Validator │  │ Detector │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │              │
     │  Turn 3 (perspective reset at turn 3)     │
     │──────────────────────────────────────────▶│
     │              │              │              │
     │ Player: CancelledError (~60s)             │
     │ State recovery: 0 created, 0 modified     │
     │              │              │              │
     │ build synthetic│              │              │
     │──────────────▶│              │              │
     │ 3 file-exist  │              │              │
     │ promises      │              │              │
     │ 0 req_addr(!) │              │              │
     │◀──────────────┤              │              │
     │              │              │              │
     │ validate     │              │              │
     │─────────────────────────────▶│              │
     │              │  AC-001: REJECTED           │
     │              │  (promise incomplete,       │
     │              │   no req_addr to match)     │
     │              │  AC-002: REJECTED           │
     │              │  AC-003: REJECTED           │
     │              │  0/3 verified               │
     │◀────────────────────────────┤              │
     │              │              │              │
     │  ...same pattern turns 4-9...              │
     │              │              │              │
     │  Turn 5 (perspective reset at turn 5)     │
     │  Still 0/3 — Player makes same changes    │
     │              │              │              │
     │  Turn 7:     │              │              │
     │  Partial progress stall warning            │
     │  "2 criteria passing but stuck for 7 turns"│
     │              │              │     ┌────────┤
     │              │              │     │MISMATCH│
     │              │              │     │Coach=0 │
     │              │              │     │Stall=2 │
     │              │              │     └────────┤
     │              │              │              │
     │  Turn 9:     │              │              │
     │─────────────────────────────────────────▶│
     │              │              │  sig=fc1ca613│
     │              │              │  5 turns same│
     │              │              │  0 criteria  │
     │◀────────────────────────────────────────┤
     │              │              │              │
     │ UNRECOVERABLE_STALL                       │
     │              │              │              │
```

## Sequence Diagram: TASK-SKEL-004 Success Path (Contrast)

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│AutoBuild │  │Synthetic │  │  Coach   │
│Orch.     │  │ Report   │  │Validator │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     │  Turn 1: CancelledError    │
     │  State: 2 created, 3 modified
     │──────────────▶│              │
     │ 6 file-exist  │              │
     │ 5 req_addr    │              │
     │◀──────────────┤              │
     │──────────────────────────▶│
     │              │  5/6 verified│
     │◀────────────────────────┤
     │              │              │
     │  Turns 2-5: CancelledError │
     │  Criteria: 0-1/6 (degraded)│
     │  (same "degradation" pattern│
     │   as FEAT-2AAA)            │
     │              │              │
     │  Turn 6: CancelledError    │
     │  State: 5 files (+58/-37)  │
     │  Tests: 47 PASSING (!)     │
     │──────────────▶│              │
     │ 6 file-exist  │              │
     │ 6 req_addr(!) │              │
     │◀──────────────┤              │
     │──────────────────────────▶│
     │              │              │
     │              │  Hybrid:     │
     │              │  upgraded 6  │
     │              │  criteria via│
     │              │  text match  │
     │              │  against     │
     │              │  6 req_addr  │
     │              │              │
     │              │  6/6 verified│
     │              │  = APPROVED  │
     │◀────────────────────────┤
     │              │              │
     │ SUCCESS      │              │
```

**Key difference**: TASK-SKEL-004's criteria are all file-existence-verifiable. When the Player finally produces enough file content for `infer_requirements_from_files()` to match >= 50% keywords against each criterion, the hybrid fallback upgrades them all to verified. TASK-VID-001 can never achieve this because "pip install succeeds" has no file-content keywords to match.

## Deep Dive 1: CancelledError Root Cause

### Code Path Traced

```
agent_invoker.py
├── invoke_player() [line 1128]
│   ├── _calculate_sdk_timeout() → 1200s (direct mode, complexity 1)
│   ├── _invoke_with_role() [line 1934]
│   │   ├── asyncio.timeout(1200s)  ← NOT the trigger
│   │   │   └── async_heartbeat(30s intervals)
│   │   │       └── query(prompt, options) [Anthropic SDK]
│   │   │           └── async generator from Claude Code CLI
│   │   │               └── CancelledError after ~60-150s
│   │   │
│   │   └── except (Exception, CancelledError) [line 1951]
│   │       └── return AgentInvocationResult(success=False)
│   │
│   └── except (Exception, CancelledError) [line 1292]
│       └── return AgentInvocationResult(success=False, error="Cancelled: ...")
│
autobuild.py
├── _invoke_player_safely() [line 3682]
│   └── except CancelledError [line 3811]
│       └── return AgentInvocationResult(success=False)
│
├── Turn loop [line 2020]
│   ├── player_result.success == False
│   ├── _attempt_state_recovery() [line 2097]
│   │   ├── MultiLayeredStateTracker.capture_state()
│   │   └── _build_synthetic_report()
│   └── Coach validation with synthetic report
```

### Root Cause: NOT the SDK Timeout

The `asyncio.timeout(1200s)` is **not** what's triggering the CancelledError. Evidence:

1. Player duration is ~60-150s, far below the 1200s timeout
2. The error message shows `cancel scope` with task names like `Task-101`, `Task-213` — these are **AnyIO cancel scopes**, not asyncio timeouts
3. The `_install_sdk_cleanup_handler()` explicitly suppresses "Attempted to exit cancel scope in a different task" — confirming this is a known pattern

### Actual Trigger: AnyIO Cancel Scope in Anthropic SDK Streaming

The Anthropic SDK's `query()` function returns an async generator that uses AnyIO cancel scopes internally. When the Claude Code CLI subprocess completes its work and the stream ends, the cancel scope cleanup triggers a `CancelledError` that propagates to the caller.

**Evidence from log pattern**:
```
CancelledError caught at invoke_player for TASK-VID-001: Cancelled via cancel scope 10d3f0f50
by <Task pending name='Task-101' coro=<<async_generator_athrow without __name__>()>>
```

The `<async_generator_athrow without __name__>()>` indicates this is the async generator's `athrow()` method being called during cleanup — this happens when an async generator is being closed (`.aclose()`) or when its enclosing cancel scope times out.

### Why This Is Not Actually a Bug

The CancelledError happens because:
1. The Player (Claude Code CLI) finishes its work
2. The SDK streaming connection closes
3. The AnyIO cancel scope exits
4. During cleanup, the async generator's cancel scope fires CancelledError
5. GuardKit catches it and treats it as a Player failure

**The Player DID complete its work** — files are modified in the worktree. The CancelledError is a **cleanup artifact**, not a failure. GuardKit's state recovery correctly detects this and recovers the work.

### But: Why Does This Matter?

Even though state recovery works, the CancelledError path means:
- The Player never returns structured `completion_promises` or `requirements_addressed`
- The system must build a **synthetic** report from git diff + file content
- Synthetic reports have **lower verification fidelity** than Player-reported results
- Command-execution criteria are **unverifiable** via the synthetic path

## Deep Dive 2: Coach Validator Internals

### Synthetic Report Path — Complete Code Flow

```
coach_validator.py: validate_requirements()
│
├── Line 1776: is_synthetic = task_work_results.get("_synthetic", False)
│
├── IF is_synthetic:
│   │
│   ├── Line 1783: completion_promises = _load_completion_promises()
│   │   └── Checks: task_work_results → player_turn_N.json → backward scan
│   │
│   ├── IF promises exist:
│   │   ├── _match_by_promises(criteria, promises)
│   │   │   └── Match AC-001 → criterion[0], AC-002 → criterion[1]...
│   │   │       └── status "complete"/"partial" → "verified"
│   │   │       └── status "incomplete"/missing → "rejected"
│   │   │
│   │   └── IF not all_criteria_met:
│   │       └── _hybrid_fallback(validation, criteria, requirements_addressed)
│   │           └── For each rejected criterion:
│   │               └── IF "No completion promise" or "Promise status: incomplete":
│   │                   └── _match_by_text(criterion, requirements_addressed)
│   │                       ├── Level 1: Exact match (normalized) → confidence 1.0
│   │                       ├── Level 2: Substring containment → confidence 0.9
│   │                       └── Level 3: Keyword overlap (Jaccard) → threshold 70%
│   │                           └── IF score >= 0.7: UPGRADE to "verified"
│   │
│   ├── ELIF no promises but has requirements_addressed:
│   │   └── _match_by_text(criteria, requirements_addressed)
│   │
│   └── ELSE (no data):
│       └── All criteria → "rejected"
```

### Why `pip install -e ".[dev]"` Never Matches

Let's trace AC-002 through the matching pipeline:

**Criterion text**: `` `pip install -e ".[dev]"` succeeds without errors ``

**Step 1: Promise matching** (`_match_by_promises`)
- Synthetic report generated 3 file-existence promises from git diff
- Promise regex patterns: `r'[\w./\-]+\.\w{1,5}'` (matches file paths)
- Applied to AC-002: No file path found in `pip install -e ".[dev]"`
- Result: **Promise status: "incomplete"**

**Step 2: Hybrid fallback** (`_hybrid_fallback`)
- AC-002 was rejected by promise matching
- Evidence contains "Promise status: incomplete" → eligible for text fallback
- Calls `_match_by_text` against `requirements_addressed`

**Step 3: Text matching** (`_match_by_text`)
- `requirements_addressed` = 2 entries inferred from file content analysis:
  - Entry 1: Something matching "`yt-dlp>=2024.1.0` added to `dependencies`..."
  - Entry 2: Something matching "`python -c "import yt_dlp..."` (keyword overlap)
- Neither entry contains "pip install" keywords
- **Level 1 (exact)**: No match
- **Level 2 (substring)**: "pip install" not substring of any requirement
- **Level 3 (Jaccard keywords)**:
  - Criterion keywords: {pip, install, succeeds, errors, dev}
  - Requirement keywords: {yt-dlp, added, dependencies, pyproject, toml} (entry 1)
  - Intersection: {} = 0 keywords
  - Score: 0/10 = 0% < 70% threshold
- Result: **REJECTED**

### requirements_addressed Inference Algorithm

```
synthetic_report.py: infer_requirements_from_files()
│
├── Line 402: Extract keywords from each acceptance criterion
│   └── Split on non-alphanumeric, filter >3 chars, remove stopwords
│
├── Line 464: Read file contents (up to 100KB each, 1MB total)
│   └── Created + modified files from git diff
│
├── Line 492: For each criterion:
│   ├── Extract keywords → {pip, install, succeeds, errors, dev}
│   ├── For each keyword, check if present in file content (case-insensitive)
│   ├── Compute ratio = matched_count / total_keywords
│   └── IF ratio >= 0.50 (50% threshold): mark as addressed
│
└── Return list of addressed criteria text
```

**For AC-002** (`pip install -e ".[dev]" succeeds`):
- Keywords: {pip, install, succeeds, errors, dev}
- File content (pyproject.toml): `dependencies = ["mcp>=1.0.0", "yt-dlp>=2024.1.0"]`
- Matches: "dev" might appear in `[project.optional-dependencies]` section
- Ratio: likely 1/5 = 20% < 50% threshold
- Result: **NOT ADDRESSED**

This is why Turn 1 inferred 2 requirements_addressed (AC-001 + AC-003 keywords partially matched) but AC-002 was never addressed.

## Deep Dive 3: Criteria Classification System Design

### Proposed Classification

```
┌─────────────────────────────────────────────────────────────────┐
│                  Criteria Classifier                             │
│                                                                  │
│  Input: acceptance_criteria: List[str]                           │
│  Output: List[ClassifiedCriterion]                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Classification Rules (priority order):                    │   │
│  │                                                           │   │
│  │ 1. COMMAND_EXECUTION:                                     │   │
│  │    Pattern: Backtick-wrapped command + "succeeds/runs/    │   │
│  │    passes/exits with" keywords                            │   │
│  │    Regex: `[^`]+`\s+(succeeds|runs|passes|exits)          │   │
│  │    Examples:                                               │   │
│  │    - `pip install -e ".[dev]"` succeeds without errors    │   │
│  │    - `python -c "import ..."` runs successfully           │   │
│  │    - `ruff check src/` passes with no errors              │   │
│  │    - `pytest tests/` passes                               │   │
│  │                                                           │   │
│  │ 2. MANUAL_VERIFICATION:                                   │   │
│  │    Pattern: "visible in", "manual verification",          │   │
│  │    "MCP Inspector", "screenshot"                          │   │
│  │    Examples:                                               │   │
│  │    - Tool visible in MCP Inspector                        │   │
│  │    - Manual verification of UI layout                     │   │
│  │                                                           │   │
│  │ 3. FILE_CONTENT:                                          │   │
│  │    Pattern: Everything else (default)                      │   │
│  │    Examples:                                               │   │
│  │    - `yt-dlp>=2024.1.0` added to dependencies            │   │
│  │    - `src/models.py` exists                               │   │
│  │    - @mcp.tool() decorator present                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Verification Strategy per Type:                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ FILE_CONTENT → Synthetic path (promises + text matching) │   │
│  │ COMMAND_EXECUTION → Execute command, check exit code     │   │
│  │ MANUAL_VERIFICATION → Skip (mark as "deferred to human") │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Approval Logic:                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ all(FILE_CONTENT verified) AND                            │   │
│  │ all(COMMAND_EXECUTION verified OR executed successfully)   │   │
│  │ → APPROVED (MANUAL_VERIFICATION deferred)                 │   │
│  │                                                           │   │
│  │ If COMMAND_EXECUTION cannot run (synthetic path):         │   │
│  │ Option A: Execute in worktree (preferred)                 │   │
│  │ Option B: Mark as unverifiable, approve if FILE_CONTENT ok│   │
│  │ Option C: Fail with "requires runtime verification"       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Approach

The classifier would be added to `coach_validator.py` before the `validate_requirements()` method:

```python
@dataclass
class ClassifiedCriterion:
    text: str
    category: Literal["file_content", "command_execution", "manual"]
    command: Optional[str] = None  # Extracted command for execution

COMMAND_PATTERNS = [
    re.compile(r'`([^`]+)`\s+(succeeds|runs|passes|exits|completes)', re.I),
    re.compile(r'`([^`]+)`\s+(without\s+errors|with\s+no\s+errors)', re.I),
    re.compile(r'`([^`]+)`\s+runs\s+successfully', re.I),
]

MANUAL_PATTERNS = [
    re.compile(r'(visible|shown|displayed)\s+in\s+(MCP Inspector|browser|UI)', re.I),
    re.compile(r'manual\s+(verification|review|check)', re.I),
]

def classify_criterion(text: str) -> ClassifiedCriterion:
    for pattern in COMMAND_PATTERNS:
        match = pattern.search(text)
        if match:
            return ClassifiedCriterion(
                text=text, category="command_execution", command=match.group(1)
            )
    for pattern in MANUAL_PATTERNS:
        if pattern.search(text):
            return ClassifiedCriterion(text=text, category="manual")
    return ClassifiedCriterion(text=text, category="file_content")
```

## Deep Dive 4: FEAT-2AAA Task Criteria Audit

### TASK-VID-001 (Wave 1, direct, scaffolding, complexity 1)

| Criterion | Current Type | Synthetic Verifiable | Recommendation |
|-----------|-------------|---------------------|----------------|
| `yt-dlp>=2024.1.0` added to `dependencies` in `pyproject.toml` | file_content | YES | Keep as-is |
| `pip install -e ".[dev]"` succeeds without errors | command_execution | NO | **Remove** — defer to TASK-VID-002 test suite |
| `python -c "import yt_dlp; print(yt_dlp.version.__version__)"` runs successfully | command_execution | NO | **Replace** with: "pyproject.toml is valid TOML" |

**Proposed rewrite**:
```markdown
- [ ] `yt-dlp>=2024.1.0` appears in the `dependencies` list in `pyproject.toml`
- [ ] `pyproject.toml` maintains valid TOML syntax (no parse errors)
```

### TASK-VID-002 (Wave 1, task-work, feature, complexity 4)

| Criterion | Current Type | Verifiable | Notes |
|-----------|-------------|-----------|-------|
| `extract_video_id()` handles URL patterns | file_content (test-verified) | YES | Code exists + tests verify |
| `extract_video_id()` raises `InvalidURLError` | file_content (test-verified) | YES | Test assertion |
| `VideoInfo` dataclass with 13 fields | file_content | YES | AST/code scan |
| `asyncio.to_thread()` for non-blocking | file_content | YES | Code pattern |
| `CancelledError` caught and re-raised | file_content (test-verified) | YES | Test assertion |
| Error mapping logic | file_content (test-verified) | YES | Test assertion |
| `_format_duration()` handling | file_content (test-verified) | YES | Test assertion |
| `_truncate()` at 500 chars | file_content (test-verified) | YES | Test assertion |
| `src/services/__init__.py` exists | file_content | YES | File existence |
| Code passes `ruff check` and `mypy` | **command_execution** | **NO** (in synthetic) | task-work Phase 5 runs this |

**Recommendation**: Replace linting criterion with: "`src/services/youtube_client.py` has no unused imports or variables". Or rely on task-work Phase 5 to handle it implicitly.

### TASK-VID-003 (Wave 2, task-work, feature, complexity 2)

| Criterion | Current Type | Verifiable | Notes |
|-----------|-------------|-----------|-------|
| Tool registered with `@mcp.tool()` | file_content | YES | Decorator pattern |
| Accepts `video_url: str` | file_content | YES | Function signature |
| Returns dict on success | file_content (test-verified) | YES | Test assertion |
| Error mapping to structured dict | file_content (test-verified) | YES | Test assertion |
| Tool docstring for LLM discovery | file_content | YES | Docstring presence |
| `YouTubeClient` at module level | file_content | YES | Code pattern |

**Recommendation**: All criteria are file-content verifiable. No changes needed.

### TASK-VID-004 (Wave 2, task-work, testing, complexity 3)

| Criterion | Current Type | Verifiable | Notes |
|-----------|-------------|-----------|-------|
| Test class/method existence | file_content | YES | File pattern |
| Duration formatting edge cases | file_content (test-verified) | YES | Test code exists |
| All tests pass: `pytest tests/...` | **command_execution** | **YES** (task-work Phase 4) | task-work runs tests |
| No network calls (all mocked) | file_content | YES | `unittest.mock.patch` presence |

**Recommendation**: Replace explicit `pytest` command criterion with: "Test file `tests/unit/test_video_info.py` contains test methods for all specified cases". task-work Phase 4 implicitly verifies test passing.

### TASK-VID-005 (Wave 3, direct, testing, complexity 1)

| Criterion | Current Type | Verifiable | Notes |
|-----------|-------------|-----------|-------|
| `ruff check src/ tests/` passes | command_execution | NO | Direct mode |
| `mypy src/` passes | command_execution | NO | Direct mode |
| Tool visible in MCP Inspector | manual | NO | Cannot auto-verify |
| Tool shows correct parameter schema | manual | NO | Cannot auto-verify |
| Tool docstring visible | file_content/manual | PARTIAL | File content check |
| All tests pass: `pytest tests/` | command_execution | NO | Direct mode |

**Recommendation**: This task is fundamentally unsuitable for `direct` mode autobuild. Either:
1. Change to `task-work` mode (which runs tests and linting)
2. Rewrite criteria to be file-content-only and mark MCP Inspector items as `(manual verification)`
3. Mark entire task as `manual` implementation_mode

**Proposed rewrite** (if keeping as direct):
```markdown
- [ ] No linting violations visible in `src/` directory files
- [ ] `get_video_info` tool definition exists in tool registration module
- [ ] Tool has `video_url: str` parameter in function signature
- [ ] Tool has descriptive docstring
- [ ] (Manual) MCP Inspector shows tool with correct schema
```

### Summary: Criteria Audit Results

| Task | Unverifiable Criteria | Fix Strategy |
|------|----------------------|-------------|
| TASK-VID-001 | 2/3 (command_execution) | Rewrite to file-content |
| TASK-VID-002 | 1/10 (linting command) | Rely on task-work Phase 5 |
| TASK-VID-003 | 0/9 | No changes needed |
| TASK-VID-004 | 1/7 (pytest command) | Rely on task-work Phase 4 |
| TASK-VID-005 | 5/6 (commands + manual) | Change mode or rewrite all |

**Total unverifiable**: 9 out of 35 criteria (26%) — concentrated in the `direct` mode tasks.

---

## Deep Dive 5: Claude Agent SDK Usage Verification

### Current SDK Integration Quality: 9.2/10

GuardKit's SDK usage was audited against the official Claude Agent SDK documentation (https://platform.claude.com/docs/en/agent-sdk/overview) and best practices.

### SDK Usage Summary

| Aspect | Best Practice | GuardKit Implementation | Compliance |
|--------|--------------|------------------------|------------|
| Import pattern | Lazy, with error handling | Lazy imports in methods with diagnostics | 100% |
| `query()` usage | Async generator, break on ResultMessage | Proper `async for` loop | 100% |
| Message accumulation | Collect for analysis | `response_messages` list | 100% |
| Error checking | Check AssistantMessage.error (bug #472) | `check_assistant_message_error()` | 100% |
| ContentBlock iteration | Iterate list, not str() | Proper isinstance checks | 100% |
| ResultMessage handling | Extract num_turns | Used for ceiling detection | 100% |
| Timeout management | asyncio.timeout() context manager | Properly implemented | 100% |
| CancelledError handling | Catch, log, re-raise | Correct pattern | 100% |
| Permission modes | Role-based tool restrictions | Player full, Coach read-only | 100% |
| Rate limit handling | Detect, extract reset_time, backoff | In task-work path only | 75% |
| MCP servers | Configure if needed | Not configured (not yet needed) | N/A |
| Hooks | Use if needed | Not used (not needed) | N/A |
| Sessions | Use session_id for resuming | Stateless design (intentional) | N/A |

### Key Findings

**1. SDK invocation is correct** — `query()` is consumed properly as an async generator with message accumulation, type checking, and error detection.

**2. Three distinct option profiles exist** for role-based access control:
- **Player (task-work delegation)**: `allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"]`, `permission_mode="acceptEdits"`
- **Player (direct)**: Same minus "Task"
- **Coach**: `allowed_tools=["Read", "Bash", "Grep", "Glob"]`, `permission_mode="bypassPermissions"`

**3. CancelledError is NOT an SDK misuse** — AnyIO cancel scope cleanup from Anthropic SDK's async generator. GuardKit handles it correctly by catching + logging + re-raising, with the `finally` block emitting instrumentation events.

**4. `setting_sources=["project"]` optimization** saves ~760KB by only loading CLAUDE.md (not user settings).

**5. Minor gap**: Rate limit detection (`detect_rate_limit()`) exists in `_invoke_task_work_implement()` but is missing from `_invoke_with_role()`, meaning Coach invocations won't get structured rate limit errors.

### SDK Features Not Yet Used (Opportunities)

| SDK Feature | Relevance | Priority |
|-------------|-----------|----------|
| **MCP servers** | Coach could use Playwright/custom verifiers for runtime criteria | **HIGH** — directly addresses FEAT-2AAA root cause |
| **Hooks (PreToolUse/PostToolUse)** | Could intercept tool calls for audit/filtering | Low — current post-processing is sufficient |
| **Sessions** | Could resume Player from where it was cancelled | Medium — would reduce redundant work on CancelledError |
| **Subagents** | Could define Player/Coach as formal AgentDefinition | Low — current delegation pattern works well |

### CancelledError Root Cause: Confirmed NOT SDK Misuse

```
┌──────────────────────────────────────────────────────────┐
│ CancelledError Source Chain                              │
│                                                          │
│ Anthropic API Stream                                     │
│   └─ AnyIO cancel scope (SDK internal)                   │
│       └─ async generator cleanup on stream close         │
│           └─ asyncio.CancelledError raised               │
│               └─ GuardKit catch → log → re-raise         │
│                   └─ Outer handler → state recovery      │
│                       └─ Synthetic report path           │
│                           └─ Coach validation            │
└──────────────────────────────────────────────────────────┘
```

The cancel fires when the Player subprocess completes and the SDK's async generator is garbage-collected. This is **inherent to the AnyIO/Anthropic SDK streaming architecture**, not a timeout or configuration issue. The Player has already done its work (files modified, tests run) by the time the cancel fires.

---

## Deep Dive 6: CancelledError Workaround Design

### Problem

When CancelledError fires at [agent_invoker.py:1951](guardkit/orchestrator/agent_invoker.py#L1951), the handler immediately re-raises without extracting partial data from `response_messages`, which has been accumulating `AssistantMessage` objects throughout the query loop.

### Available Data Sources After CancelledError

1. **`response_messages` list** — accumulated `AssistantMessage`/`ToolUseBlock` objects in memory
2. **`task_work_results.json`** — written by Player subprocess to disk BEFORE stream closes
3. **`player_turn_N.json`** — written by Player subprocess to disk
4. **`TaskWorkStreamParser`** — existing parser class ([agent_invoker.py:245-641](guardkit/orchestrator/agent_invoker.py#L245)) with logic for extracting quality gate results from text output

### Proposed Fix: Extract Partial Data Before Re-raising

```python
# agent_invoker.py line ~1951 (current)
except (Exception, asyncio.CancelledError) as exc:
    if isinstance(exc, asyncio.CancelledError):
        logger.warning(f"CancelledError caught: {exc}")
    call_status = "error"
    call_error = exc
    raise  # ← Loses partial data

# PROPOSED:
except (Exception, asyncio.CancelledError) as exc:
    if isinstance(exc, asyncio.CancelledError):
        logger.warning(f"CancelledError caught: {exc}")
        # Extract partial data before re-raising
        partial_report = _extract_partial_from_messages(response_messages)
        if partial_report:
            # Attach to exception for state recovery to use
            exc._partial_report = partial_report
            logger.info(
                "Extracted partial report from %d messages: %d text blocks, %d tool calls",
                len(response_messages),
                partial_report.get("text_blocks", 0),
                partial_report.get("tool_calls", 0),
            )
    call_status = "error"
    call_error = exc
    raise

def _extract_partial_from_messages(messages: list) -> Optional[dict]:
    """Extract usable data from accumulated response_messages."""
    text_blocks = []
    tool_calls = []
    files_modified = []

    for msg in messages:
        if hasattr(msg, 'content'):
            for block in msg.content:
                if hasattr(block, 'text'):
                    text_blocks.append(block.text)
                elif hasattr(block, 'name') and hasattr(block, 'input'):
                    tool_calls.append({"name": block.name, "input": block.input})
                    if block.name in ("Write", "Edit"):
                        path = block.input.get("file_path", "")
                        if path:
                            files_modified.append(path)

    if not text_blocks and not tool_calls:
        return None

    return {
        "text_blocks": len(text_blocks),
        "tool_calls": len(tool_calls),
        "files_modified": files_modified,
        "collected_text": "\n".join(text_blocks[-3:]),  # Last 3 text blocks
        "_partial": True,
    }
```

### Alternative: Read task_work_results.json from Disk

The Player subprocess writes `task_work_results.json` to the worktree BEFORE the async stream closes. State recovery in [autobuild.py:2425-2549](guardkit/orchestrator/autobuild.py#L2425) already attempts this, but the results are often empty because the file write may not complete before the cancel fires.

### Impact Assessment

| Approach | Effort | Impact | Risk |
|----------|--------|--------|------|
| Extract from response_messages | Low | Medium | Low — data already in memory |
| Read disk files in catch | Low | Medium | Medium — race condition on file write |
| SDK sessions for resume | High | High | Medium — architectural change |

### Recommendation

Implement the `response_messages` extraction approach first (low effort, immediate benefit). This gives state recovery access to partial quality gate results and file modification data that would otherwise be lost.

---

## Deep Dive 7: Coach Execution Mode Design

### Current Coach Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Coach Validator (coach_validator.py, 3,884 lines)           │
│                                                             │
│ Tools: Read, Bash, Grep, Glob (read-only)                   │
│ Mode: bypassPermissions                                     │
│                                                             │
│ ┌─────────────────┐  ┌─────────────────┐                    │
│ │ Verification     │  │ Test Execution   │                    │
│ │ Paths            │  │ Modes            │                    │
│ │                  │  │                  │                    │
│ │ A: Promises      │  │ SDK mode         │                    │
│ │ B: Hybrid        │  │ Subprocess mode  │                    │
│ │ C: Text match    │  │                  │                    │
│ └─────────────────┘  └─────────────────┘                    │
│                                                             │
│ Already has:                                                │
│ ✓ subprocess.run() with shell=True, timeout 300s            │
│ ✓ Full worktree access                                      │
│ ✓ Multi-language test command detection                      │
│ ✓ Infrastructure error classification                       │
│ ✓ Isolated temp directory execution                         │
└─────────────────────────────────────────────────────────────┘
```

### Key Insight: Coach ALREADY Executes Commands

The Coach validator already runs commands via `subprocess.run()` for test execution. The infrastructure for command execution exists — it's just not applied to acceptance criteria verification.

### Proposed: Coach Execution Mode

Add a fourth verification path (D: Runtime) that classifies criteria and executes command_execution criteria in the worktree:

```
                   ┌──────────────────────┐
                   │  Criteria Classifier  │
                   │  (new: POC exists)    │
                   └──────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼──────┐ ┌─────▼──────┐ ┌──────▼───────┐
    │ file_content    │ │ command_   │ │ manual       │
    │                │ │ execution  │ │              │
    │ Path A/B/C     │ │ Path D     │ │ Skip or      │
    │ (existing)     │ │ (NEW)      │ │ mark N/A     │
    └────────────────┘ └─────┬──────┘ └──────────────┘
                             │
                   ┌─────────▼──────────┐
                   │ Execute in worktree │
                   │ subprocess.run()    │
                   │ timeout: 60s        │
                   │ check exit code     │
                   └─────────┬──────────┘
                             │
                   ┌─────────▼──────────┐
                   │ Result: pass/fail   │
                   │ stdout/stderr       │
                   │ duration            │
                   └────────────────────┘
```

### Implementation: Three Options

#### Option A: MCP Tools (Recommended Long-term)

Add MCP servers to Coach SDK invocation:

```python
# agent_invoker.py — Coach invocation
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Bash", "Grep", "Glob"],
    permission_mode="bypassPermissions",
    mcp_servers={
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp@latest"],
        },
        "verify": {
            "command": "python",
            "args": ["-m", "guardkit.mcp.verify_server"],
        },
    },
)
```

**Pros**: Agent can reason about verification, use Playwright for UI testing, extensible
**Cons**: Requires MCP server implementation, more complex

#### Option B: Orchestrator-Level Execution (Recommended Short-term)

Execute command criteria in the orchestrator BEFORE Coach validation:

```python
# autobuild.py — After state recovery, before Coach
from guardkit.orchestrator.quality_gates.criteria_classifier import (
    classify_acceptance_criteria,
    CriterionType,
)

# Classify criteria
result = classify_acceptance_criteria(acceptance_criteria)

# Execute command criteria in worktree
command_results = {}
for criterion in result.command_criteria:
    if criterion.extracted_command:
        try:
            proc = subprocess.run(
                criterion.extracted_command,
                shell=True,
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
                timeout=60,
            )
            command_results[criterion.text] = proc.returncode == 0
        except subprocess.TimeoutExpired:
            command_results[criterion.text] = False

# Inject results into synthetic report as requirements_addressed
for criterion_text, passed in command_results.items():
    if passed:
        synthetic_report["requirements_addressed"].append(criterion_text)
```

**Pros**: Minimal code change, uses existing infrastructure, no MCP needed
**Cons**: Orchestrator does verification (not Coach), limited to shell commands

#### Option C: Extended Coach Validator (Medium-term)

Add verification methods directly to CoachValidator class:

```python
class CoachValidator:
    async def verify_runtime_criteria(
        self,
        criteria: List[ClassifiedCriterion],
    ) -> Dict[str, bool]:
        results = {}
        for criterion in criteria:
            if criterion.criterion_type == CriterionType.COMMAND_EXECUTION:
                results[criterion.text] = await self._execute_criterion(criterion)
        return results

    async def _execute_criterion(self, criterion: ClassifiedCriterion) -> bool:
        if not criterion.extracted_command:
            return False
        try:
            proc = subprocess.run(
                criterion.extracted_command,
                shell=True,
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False
```

### Decision Matrix

| Option | Effort | Impact | When |
|--------|--------|--------|------|
| B: Orchestrator execution | Low | High | **Now** — directly fixes FEAT-2AAA class of failures |
| C: Extended Coach validator | Medium | High | Next — cleaner architecture |
| A: MCP tools | High | Very High | Later — enables UI/API/browser verification |

### Security Considerations

Command execution in the Coach path requires safety controls:
- **Timeout**: 60s max per command (prevent hanging)
- **Working directory**: Must be the worktree (not host system)
- **Allowlist**: Only execute commands that match accepted patterns
- **No network access**: Consider `--network=none` for containerized execution
- **Audit trail**: Log all executed commands and results

---

## Deep Dive 8: Criteria Classifier POC (Implemented)

### Implementation

A working criteria classifier has been implemented at:
- **Code**: `guardkit/orchestrator/quality_gates/criteria_classifier.py`
- **Tests**: `tests/unit/test_criteria_classifier.py` (21 tests, all passing)

### Classification Logic

The classifier uses regex pattern matching with confidence scoring:

| Pattern Category | Confidence | Examples |
|-----------------|-----------|---------|
| Command execution (direct match) | 0.9 | `` `pip install` succeeds ``, `` `pytest` passes `` |
| File content (direct match) | 0.85 | "added to `pyproject.toml`", "module `server.py` exists" |
| Manual (direct match) | 0.8 | "visually verify", "performance stays under" |
| File path reference (fallback) | 0.6 | Contains `` `*.py` `` |
| Command-like content (fallback) | 0.5 | Long backtick content starting with known binary |
| Default (no match) | 0.3 | Defaults to file_content |

### Validation Against FEAT-2AAA

```
TASK-VID-001 (root cause of failure):
  ✓ Criterion 1: file_content  (yt-dlp added to pyproject.toml)
  ✓ Criterion 2: command_execution  (pip install succeeds)
  ✓ Criterion 3: command_execution  (python -c import runs)
  → Correctly identifies 2/3 as unverifiable via synthetic path

FEAT-SKEL-001 (successful run):
  ✓ All criteria classified as file_content
  → Correctly identifies all as verifiable via synthetic path
```

### Integration Point

The classifier is designed to plug into the Coach validation pipeline at the criteria matching stage:

```python
# Before matching, classify to route verification:
from guardkit.orchestrator.quality_gates.criteria_classifier import (
    classify_acceptance_criteria,
    CriterionType,
)

classification = classify_acceptance_criteria(acceptance_criteria)

# Route file_content criteria through existing Path A/B/C
file_criteria = [c.text for c in classification.file_content_criteria]
# Route command_execution criteria through new Path D
cmd_criteria = classification.command_criteria
# Skip or flag manual criteria
manual_criteria = classification.manual_criteria
```

---

## Updated Recommendations (Revision 3)

Based on the three deep dives (SDK verification, Coach execution mode, CancelledError workaround), the recommendations are updated:

### Tier 1: Immediate (fix the root cause)

| # | Recommendation | Effort | Impact | Addresses |
|---|---------------|--------|--------|-----------|
| R1 | **Orchestrator-level command execution** (Option B): Execute `command_execution` criteria in worktree before Coach validation | Low | High | Root cause — Coach can't verify runtime criteria |
| R2 | **Integrate criteria classifier** into Coach validation pipeline | Low | High | Classification routing for verification |

### Tier 2: Short-term (improve reliability)

| # | Recommendation | Effort | Impact | Addresses |
|---|---------------|--------|--------|-----------|
| R3 | **Extract partial data from response_messages** in CancelledError handler | Low | Medium | Better state recovery with partial quality gate data |
| R4 | **Carry forward best requirements_addressed** across turns | Low | Medium | Degradation over turns |
| R5 | **Align stall detector** with Coach criteria count | Low | Low | Criteria count mismatch |

### Tier 3: Medium-term (architectural improvements)

| # | Recommendation | Effort | Impact | Addresses |
|---|---------------|--------|--------|-----------|
| R6 | **Extended Coach validator** with runtime verification methods | Medium | High | Cleaner architecture for command execution |
| R7 | **Add rate limit detection** to `_invoke_with_role()` | Low | Low | Missing structured rate limit errors for Coach |

### Tier 4: Long-term (enablement for future capabilities)

| # | Recommendation | Effort | Impact | Addresses |
|---|---------------|--------|--------|-----------|
| R8 | **MCP tool integration** for Coach (Playwright, custom verifiers) | High | Very High | UI/API/browser verification capabilities |
| R9 | **SDK sessions** for Player resumption after CancelledError | High | High | Reduce redundant work on cancellation |

### What Changed from Initial Recommendations

| Initial | Updated | Change |
|---------|---------|--------|
| R1: Rewrite task criteria | Deprioritized | Treats symptoms, not cause |
| R2: Criteria classification | R2: Integrated as POC (implemented) | Now has working code |
| R3: Fix CancelledError | R3: Partial data extraction (specific fix) | Narrowed to actionable fix |
| R4: Carry forward requirements | R4: Unchanged | Still valid |
| R5: Align stall detector | R5: Unchanged | Still valid |
| (new) R1: Orchestrator execution | **Primary fix** | Addresses root cause directly |
| (new) R6-R9 | New tiers | Emerged from deep dives |

### Decision: Fix in GuardKit Orchestrator (not task rewriting)

The user correctly identified that rewriting task criteria addresses symptoms rather than the cause. The root cause is that **the Coach verification pipeline has no mechanism for runtime criteria verification**.

**Action plan**:
1. Deploy criteria classifier (R2) — **already implemented**
2. Add orchestrator-level command execution (R1) — injects verified command results into synthetic report
3. Extract partial data from CancelledError (R3) — improves state recovery fidelity
4. Plan MCP integration (R8) for UI/API verification — enables Coach to verify application behavior

This approach ensures that any future task with command_execution criteria will be automatically verified, without requiring task authors to know about the Coach's verification limitations.

---

## Revision 4: Regression Risk Review and Feedback Integration

Post-implementation task creation, a regression risk assessment was conducted against all recommendations. The following refinements were incorporated into the implementation tasks:

### R1 (CRV-537E): Worktree Path Assertion — Medium Regression Risk

**Feedback**: The design is sound but the working directory must always be the worktree, never the base repo.

**Action taken**: Added a defensive `_assert_worktree_path()` check before any `subprocess.run()` — asserts the path contains `.guardkit/worktrees/`. Added to acceptance criteria and implementation notes. Command allowlisting deferred for initial implementation since commands originate from user-authored task spec files.

### R2 (CRV-412F): Routing Layer, Not Replacement — Low Regression Risk

**Feedback**: If classification routing replaces existing code rather than routing alongside it, `file_content` criteria that previously succeeded via Path A/B/C could get mis-classified.

**Action taken**: Added explicit "routing layer on top, not replacement" constraint to task description and acceptance criteria. Added requirement for graceful fallback when classifier errors. Added regression check requirement — existing tests must produce **identical results**. The classifier's conservative default (file_content at confidence 0.3) is confirmed as correct design.

### R3 (CRV-1540): Instance Attribute Over Exception Attribute — Low Risk

**Feedback**: Attaching `_partial_report` to the exception object is unusual. Storing as an invoker instance attribute before re-raising is cleaner.

**Action taken**: Changed acceptance criteria to use `self._last_partial_report` instance attribute pattern. Added design note explaining rationale. This is safely additive — only enriches data that was previously discarded.

### R4 (CRV-9618): Staleness Check Required — Low Risk With Caveat

**Feedback**: A "best turn" result from turn 1 could become stale by turn 6 if the Player restructures files. Need to verify the source file still exists and still contains matching content.

**Action taken**: Added staleness check to acceptance criteria — before carrying forward a previous requirement, re-validate that the file that produced the keyword match still exists and still contains matching content in the current worktree state. Added test for staleness detection.

### R5 (CRV-90FB): Confirmed Correct — Low Risk

No changes needed. Confirmed as clearly correct alignment fix.

### CancelledError Confirmation

The review's conclusion — that CancelledError is an AnyIO cleanup artifact, not a genuine failure — is independently confirmed by the log signature: `Cancelled via cancel scope 10d3f0f50 by <Task pending name='Task-101' coro=<<async_generator_athrow without __name__>()>>`. Textbook async generator teardown. The Player completed its work. State recovery correctly handles it.

The more ambitious fix (SDK sessions for cleaner completion, R9) remains in Wave 4 as the long-term path. R3's partial data extraction is the right incremental improvement.

### Coach Verifying Running Applications — Architecture Refinement

**Critical feedback**: Server lifecycle management must be owned by the orchestrator, not the Coach.

The verification architecture decomposes into three tiers:

```
Tier 1: API Backends          Tier 2: Web Apps            Tier 3: Mobile/Desktop
(subprocess, no MCP)          (Playwright MCP)            (Appium, future)

Orchestrator:                 Orchestrator:               Out of scope
  pre_verification:             pre_verification:
    start server                  npm run dev
    wait for health               wait for port
  invoke Coach                  invoke Coach + MCP
  post_verification:            post_verification:
    terminate server              kill dev server
    cleanup ports                 release port
```

**Key architectural decisions**:
1. **Orchestrator owns lifecycle** — Coach is a pure verifier, never starts/stops services
2. **pre_verification / post_verification hooks** — cleanup guaranteed even on failure
3. **Port isolation** — orchestrator assigns unique ports from a pool for parallel tasks
4. **Tier 1 achievable without MCP** — API health checks are a natural subprocess extension
5. **Tier 2 requires Playwright MCP** — DOM assertions, screenshot comparison, rendered output

CRV-7DBC updated to reflect this architecture (complexity raised from 7 to 8).
