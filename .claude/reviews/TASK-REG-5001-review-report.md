# Regression Risk Analysis Report: TASK-REG-5001

## Executive Summary

**Task Under Review**: TASK-P28-D102 - Enhance Phase 2.8 with Business Decision Detection
**Analysis Date**: 2025-12-03
**Release Context**: Pre-public release
**Risk Tolerance**: Low

---

## Risk Summary

| Metric | Value |
|--------|-------|
| **Overall Risk Score** | **4/10** |
| **Risk Level** | **MEDIUM-LOW** |
| **Recommendation** | **DEFER TO POST-RELEASE** |

---

## Component Risk Analysis

### 1. Phase 2.8 Checkpoint Modification

**Files Affected**:
- `installer/core/commands/lib/checkpoint_display.py` (20KB, 12 functions)
- `installer/core/commands/lib/phase_execution.py` (34KB)

**Current Implementation**:
- Phase 2.8 triggers on: complexity ≥7 OR architectural review <60
- User options: [A]pprove, [M]odify, [S]implify, [R]eject, [P]ostpone

**Proposed Change**:
- Add new trigger: business decision points ≥1
- Add new option: [D]ecisions

**Risk Assessment**:

| Factor | Score | Rationale |
|--------|-------|-----------|
| Likelihood of Regression | 2/5 | Additive change (new trigger, new option) |
| Impact if Regression | 4/5 | Affects ALL `/task-work` executions |
| Test Coverage | Good | 115 existing tests for Phase 2.8 components |
| Rollback Complexity | Low | Can remove new trigger without affecting existing |

**Risk Level**: MEDIUM (Score: 3/5)

---

### 2. Task File Frontmatter Changes

**Files Affected**:
- `installer/core/commands/lib/task_utils.py` (10KB)

**Current Implementation**:
- `parse_task_frontmatter()` handles unknown fields gracefully
- `write_task_frontmatter()` preserves existing fields

**Proposed Change**:
- Add new fields: `has_decision_points`, `decision_points_count`, `decision_points[]`

**Risk Assessment**:

| Factor | Score | Rationale |
|--------|-------|-----------|
| Likelihood of Regression | 1/5 | New fields are additive, existing parsing unchanged |
| Impact if Regression | 3/5 | Could break task loading if YAML invalid |
| Test Coverage | Good | Unit tests cover frontmatter parsing |
| Rollback Complexity | Low | Fields can be removed without breaking tasks |

**Backward Compatibility Check**:
- ✅ New fields optional (not required for task loading)
- ✅ Existing tasks without fields will work (defaults to no decision points)
- ✅ YAML parser already handles unknown fields gracefully

**Risk Level**: LOW (Score: 1.5/5)

---

### 3. User Workflow Changes

**Current Flow**:
```
Phase 2 → Phase 2.5 → Phase 2.7 → Phase 2.8 → Phase 3
                                    ↓
                              [A/M/S/R/P]
```

**Proposed Flow**:
```
Phase 2 → [Decision Detection] → Phase 2.5 → Phase 2.7 → Phase 2.8 → Phase 3
                                                           ↓
                                                   [A/D/M/S/R/P]
```

**Risk Assessment**:

| Factor | Score | Rationale |
|--------|-------|-----------|
| Likelihood of Confusion | 3/5 | New users may not understand [D]ecisions option |
| Impact if Confused | 2/5 | Users can skip/proceed without using [D] |
| Documentation Coverage | TBD | New docs required before release |
| Rollback Complexity | Low | Remove option, detection logic |

**User Experience Concerns for Public Release**:
- ⚠️ New users learning GuardKit for first time
- ⚠️ Extra step could create friction in initial experience
- ⚠️ False positives could interrupt simple tasks

**Risk Level**: MEDIUM (Score: 2.5/5)

---

### 4. Heuristic Detection Accuracy

**Proposed Detection**:
- Keyword-based heuristics for 4 categories
- Ambiguity keyword detection
- Confidence scoring (High/Medium/Low)
- Only High confidence flagged by default

**Risk Assessment**:

| Factor | Score | Rationale |
|--------|-------|-----------|
| False Positive Risk | 3/5 | Heuristics can match unintended patterns |
| False Negative Risk | 2/5 | May miss actual decision points |
| Impact on Workflow | 2/5 | Extra checkpoints, but skippable |
| Tuning Required | High | Will need adjustment based on real-world usage |

**Specific Concerns**:
- Keywords like "validate", "required", "contract" appear in many tasks
- Could trigger Phase 2.8 for simple tasks (complexity <7)
- No way to tune thresholds without code changes

**Risk Level**: MEDIUM (Score: 2.5/5)

---

### 5. New Files (No Regression Risk)

**Files to Create**:
1. `decision_detection.py` - New module
2. `decision_capture.py` - New module
3. Test files (3)

**Risk**: NONE - New files cannot cause regression

---

## Test Coverage Analysis

### Existing Test Coverage for Phase 2.8

| Test File | Test Count | Coverage Area |
|-----------|------------|---------------|
| `test_phase28_checkpoint.py` | 10 | E2E checkpoint display |
| `test_phase28_checkpoint_workflow.py` | 12 | Full workflow |
| `test_checkpoint_display.py` | 29 | Unit tests |
| `test_checkpoint_display_comprehensive.py` | 64 | Edge cases |
| **Total** | **115** | |

**Assessment**: Excellent existing test coverage would catch regressions quickly.

### Tests Required for New Feature

| Test Area | Required Tests |
|-----------|----------------|
| Decision detection logic | 10-15 |
| Phase 2.8 trigger expansion | 5-8 |
| [D]ecisions workflow | 8-12 |
| Frontmatter updates | 5-8 |
| Integration tests | 5-10 |
| **Total New Tests** | **33-53** |

---

## Risk Matrix

| Component | Likelihood | Impact | Risk Level | Mitigation Available |
|-----------|------------|--------|------------|---------------------|
| Phase 2.8 checkpoint | Low | High | MEDIUM | Yes - additive change |
| Task file parsing | Very Low | Medium | LOW | Yes - optional fields |
| User workflow | Medium | Medium | MEDIUM | Partial - needs docs |
| Heuristic accuracy | Medium | Low | MEDIUM-LOW | Yes - conservative threshold |
| New code | None | None | NONE | N/A |

**Composite Risk Score**: 4/10 (MEDIUM-LOW)

---

## Decision Framework Evaluation

### Criteria for Inclusion in Release

| Criterion | Met? | Notes |
|-----------|------|-------|
| All modified files have existing tests | ✅ | 115 tests cover affected code |
| New code paths are additive | ✅ | No modification to existing logic |
| New frontmatter fields have defaults | ✅ | Optional fields, backward compatible |
| Feature can be disabled without code changes | ❌ | No feature flag mechanism |
| Rollback plan documented and tested | ❌ | Not yet created |
| User documentation complete | ❌ | Not yet written |

### Criteria for Deferral

| Criterion | Met? | Notes |
|-----------|------|-------|
| Core workflow modifications are invasive | ❌ | Changes are additive |
| Test coverage for affected areas insufficient | ❌ | 115 tests exist |
| New dependencies introduced | ❌ | No new dependencies |
| Rollback would be complex | ❌ | Simple removal possible |
| User documentation incomplete | ✅ | **Not yet written** |

---

## Recommendation

### DEFER TO POST-RELEASE

**Primary Rationale**:

1. **First Impressions Matter**: For a public release, new users should experience a streamlined, polished workflow. Adding a new decision detection feature that may trigger false positives could create unnecessary friction.

2. **Heuristics Need Tuning**: Keyword-based detection will require real-world feedback to calibrate. Better to gather this feedback from early adopters post-release than risk frustrating new users.

3. **Documentation Gap**: The feature requires significant documentation updates. Rushing documentation for release risks incomplete or confusing guidance.

4. **Feature Flag Missing**: Without a way to disable the feature, users experiencing issues would have no recourse other than waiting for a fix.

5. **Risk/Reward Analysis**:
   - Risk: Medium-low technical regression, but potentially high UX regression for new users
   - Reward: Valuable feature, but not critical for initial release
   - Trade-off: Defer to ensure polished first experience

---

## Alternative: Minimal Pre-Release Version

If you strongly want some form of decision detection in the initial release, consider a **minimal version**:

### Minimal Version Scope

1. **Detection Only** (no interactive capture):
   - Detect decision points during Phase 2
   - Display in Phase 2.8 as informational section
   - NO new [D]ecisions option
   - NO frontmatter updates

2. **Conservative Thresholds**:
   - Only flag if 3+ high-confidence decision points detected
   - Reduces false positive risk

3. **No Workflow Changes**:
   - Existing Phase 2.8 triggers unchanged
   - Decision points are informational only

**Minimal Version Risk**: LOW (2/10)
**Implementation Time**: ~2 hours
**Rollback**: Trivial (remove display section)

---

## Post-Release Roadmap

If deferring, plan for post-release:

| Phase | Timeframe | Deliverable |
|-------|-----------|-------------|
| v1.0.0 | Release | Core workflow (no decision detection) |
| v1.0.1 | +1 week | Minimal detection (informational only) |
| v1.1.0 | +4 weeks | Full decision detection with [D]ecisions |

---

## Decision Checkpoint

Based on this analysis:

| Option | Recommendation |
|--------|---------------|
| **[A]** Include full feature | ❌ NOT RECOMMENDED |
| **[B]** Include minimal version | ⚠️ ACCEPTABLE (if needed) |
| **[C]** Defer to post-release | ✅ **RECOMMENDED** |
| **[D]** Cancel entirely | ❌ NOT RECOMMENDED |

**Suggested Action**: Choose **[C] DEFER** and implement post-release per roadmap above.

---

## Appendix: Files Analyzed

| File | Size | Functions | Test Coverage |
|------|------|-----------|---------------|
| checkpoint_display.py | 20KB | 12 | 93 tests |
| phase_execution.py | 34KB | 15 | 22 tests |
| task_utils.py | 10KB | 6 | 8 tests |
| phase_gate_validator.py | 4KB | 4 | 6 tests |

---

**Review Status**: COMPLETE
**Reviewer**: Claude Code (decision analysis mode)
**Confidence Level**: HIGH
