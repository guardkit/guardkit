# Agent Quality Enhancement: Implementation Plan

**Date**: 2025-11-21
**Status**: Ready for Implementation
**Estimated Total Effort**: 32 hours (1 week)

---

## Executive Summary

Based on analysis of GitHub's blog post about writing effective AGENTS.md files (from 2,500+ repositories), we've designed a comprehensive agent quality enhancement system for Taskwright. Instead of creating a separate guidelines document (which would be 95%+ redundant), we're implementing:

1. **Enhanced agent-content-enhancer.md** - AI agent that self-validates output against GitHub standards
2. **/agent-validate command** - Automated quality checking tool with objective scoring
3. **Comprehensive test suite** - 150+ tests ensuring quality

**Key Innovation**: The AI becomes a **self-validating quality system** - it checks its own output against measurable thresholds and iteratively refines until quality gates pass.

---

## Problem Statement

### Current State

**Agent Quality Issues**:
- Time to first example: 150-280 lines (users abandon before finding examples)
- Example density: 20-30% (below 40-50% industry target)
- Boundary clarity: Implicit (no explicit ALWAYS/NEVER/ASK sections)
- Quality consistency: Variable (depends on AI model state)

**Annual Cost**: $68,600/year for 10-person team (time wasted searching for examples, unclear guidance)

### Proposed Solution

**Automated Quality Enforcement**:
- Time to first example: <50 lines (66-82% reduction)
- Example density: 40-50% (33-67% increase)
- Boundary clarity: Explicit ALWAYS/NEVER/ASK (100% compliance)
- Quality consistency: Guaranteed ≥8/10 score

**ROI**: $138,000/year savings, 6.6:1 return on investment

---

## Implementation Tasks

### Task 1: TASK-AGENT-ENHANCER-20251121-160000 ⭐ START HERE

**Priority**: CRITICAL (P0)
**Effort**: 4 hours
**Dependencies**: None
**File**: [tasks/backlog/TASK-AGENT-ENHANCER-20251121-160000.md](../../tasks/backlog/TASK-AGENT-ENHANCER-20251121-160000.md)

**What It Does**:
Enhances `installer/global/agents/agent-content-enhancer.md` with GitHub best practices, transforming it into a standards-enforcing engine that automatically validates its own output.

**Key Deliverables**:
1. Add "GitHub Best Practices" section (~85 lines) to agent-content-enhancer.md
2. Create shared validation module (`.claude/commands/shared/agent_validation.py`)
3. Update command documentation with validation report format
4. Unit tests (5+ tests) and integration tests (2+ tests)

**Acceptance Criteria**:
- ✅ GitHub Best Practices section added with 6 quality thresholds
- ✅ Validation algorithm implemented (time to example, density, boundaries, etc.)
- ✅ Self-validation protocol (iterative refinement, max 3 attempts)
- ✅ Backward compatible (existing agents still work)

**Expected Output**:

When you run `/agent-enhance`, you now get:

```yaml
✅ Enhanced architectural-reviewer.md

Validation Report:
  time_to_first_example: 35 lines ✅
  example_density: 47% ✅
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  commands_first: 28 lines ✅
  specificity_score: 9/10 ✅
  code_to_text_ratio: 1.3:1 ✅
  overall_status: PASSED
  iterations_required: 1
```

---

### Task 2: TASK-AGENT-VALIDATE-20251121-160001

**Priority**: CRITICAL (P0)
**Effort**: 24 hours
**Dependencies**: TASK-AGENT-ENHANCER (needs shared validation module)
**File**: [tasks/backlog/TASK-AGENT-VALIDATE-20251121-160001.md](../../tasks/backlog/TASK-AGENT-VALIDATE-20251121-160001.md)

**What It Does**:
Creates `/agent-validate` command to check agent files against GitHub best practices with objective scoring and actionable recommendations.

**Key Deliverables**:
1. Command interface (`/agent-validate <file>` with flags)
2. 6 validation categories with 15+ individual checks
3. Output formatters (console, JSON, minimal)
4. Batch validation mode (`/agent-validate-batch <directory>`)
5. CI/CD integration (exit codes, thresholds)

**Acceptance Criteria**:
- ✅ Objective scoring (0-10 scale, deterministic)
- ✅ Actionable recommendations (line numbers, specific fixes, impact estimates)
- ✅ Multiple output formats (console/JSON/minimal)
- ✅ Performance targets (<2s single, <20s batch for 15 agents)
- ✅ Uses shared validation module from TASK-AGENT-ENHANCER

**Expected Output**:

When you run `/agent-validate installer/global/agents/code-reviewer.md`:

```
Analyzing: code-reviewer.md (595 lines)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ YAML frontmatter: Valid (lines 1-11)
✅ Early actionability: First example at line 28 (target: <50)
⚠️  File length: 595 lines (target: 150-300)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE DENSITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Example density: 30% (target: 40-50%)
   Gap: Need 60 more lines of code (~12 examples)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL SCORE: 7.2/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: Production-Ready with Improvements

[P1 - CRITICAL] Increase example density to 40%
  Current: 30% (178 lines)
  Target: 40% (238 lines)
  Action: Add 60 lines of code examples (~12 examples)
  Impact: +2.0 points (7.2 → 9.2 overall score)
  Time: 30 minutes
```

---

### Task 3: TASK-TEST-87F4 (Already Created)

**Priority**: HIGH (P1)
**Effort**: 4-5 days
**Dependencies**: TASK-AGENT-ENHANCER, TASK-AGENT-VALIDATE
**File**: [tasks/backlog/TASK-TEST-87F4-comprehensive-test-suite-agent-enhancement.md](../../tasks/backlog/TASK-TEST-87F4-comprehensive-test-suite-agent-enhancement.md)

**What It Does**:
Creates comprehensive test suite covering enhancement, validation, integration, regression, and quality validation.

**Key Deliverables**:
1. Unit tests (103 tests) - Enhancement (38), Validation (45), Commands (20)
2. Integration tests (25 tests) - Workflows, batch, CI/CD
3. Regression tests (13 tests) - Existing agents, API compatibility
4. Quality tests (9 tests) - Before/after improvement validation

**Acceptance Criteria**:
- ✅ Coverage targets (≥90% lines, ≥85% branches, 100% functions)
- ✅ Test fixtures (5 quality tiers, known-good/known-bad agents)
- ✅ CI/CD integration (GitHub Actions, quality gates)
- ✅ Performance benchmarks (<2s validation, <20s batch)

---

## Recommended Implementation Sequence

### Week 1: Foundation (TASK-AGENT-ENHANCER)

**Days 1-2**:
1. Create GitHub Best Practices section in agent-content-enhancer.md (~85 lines)
2. Implement shared validation module (`.claude/commands/shared/agent_validation.py`)
3. Update agent-enhance command documentation

**Day 3**:
4. Write unit tests (5+ tests for validation functions)
5. Write integration tests (2+ tests for enhancement workflow)
6. Manual testing on 3 existing agents (architectural-reviewer, test-orchestrator, code-reviewer)

**Expected Outcome**: agent-content-enhancer.md now enforces GitHub standards automatically

---

### Week 2: Validation Tool (TASK-AGENT-VALIDATE)

**Days 1-3**:
1. Create command specification (`installer/global/commands/agent-validate.md`)
2. Implement core validator (`lib/agent_validator/validator.py`)
3. Implement 6 check categories (structure, example_density, boundaries, specificity, example_quality, maintenance)

**Days 4-5**:
4. Implement output formatters (console, JSON, minimal)
5. Implement batch validation mode
6. Write unit tests (45+ tests for validation checks)
7. Write integration tests (6+ tests for workflows)

**Expected Outcome**: `/agent-validate` command provides objective quality scores for all agents

---

### Week 3: Testing & Integration (TASK-TEST-87F4)

**Days 1-2**:
1. Implement unit tests (103 tests total)
2. Implement integration tests (25 tests)
3. Implement regression tests (13 tests)

**Days 3-4**:
4. Implement quality validation tests (9 tests)
5. Create CI/CD workflows (GitHub Actions)
6. Document testing procedures

**Day 5**:
7. Run full test suite
8. Fix any failures
9. Verify coverage targets met (≥90% lines)

**Expected Outcome**: Comprehensive test coverage ensures quality and prevents regressions

---

## Architecture Decision Records

### ADR-001: No Standalone Guidelines Document

**Decision**: Do NOT create separate agent authoring guidelines document

**Rationale**:
- 95%+ redundant with existing artifacts (5 tasks, analysis doc, agent files)
- Dual-purpose document (human + AI) creates "documentation uncanny valley"
- Maintenance burden ($3,600/year to keep synced)
- Negative ROI (cost > benefit)

**Alternative**: Enhance agent-content-enhancer.md directly + create validation tool

**Status**: Approved

---

### ADR-002: Validation as Part of Generation

**Decision**: agent-content-enhancer.md validates its own output before returning

**Rationale**:
- Self-enforcing quality (no separate validation step needed)
- Iterative refinement (max 3 attempts) ensures quality
- Measurable standards (numeric thresholds, objective scoring)
- Single source of truth (agent owns its standards)

**Status**: Approved

---

### ADR-003: Shared Validation Module

**Decision**: Create `.claude/commands/shared/agent_validation.py` used by both enhancement and validation

**Rationale**:
- DRY principle (don't duplicate validation logic)
- Consistency (same thresholds for enhancement and validation)
- Maintainability (update standards in one place)
- Testability (shared module is easier to unit test)

**Status**: Approved

---

## Success Metrics

### Quantitative Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Time to first example | 150-280 lines | <50 lines | 66-82% reduction |
| Example density | 20-30% | 40-50% | 33-67% increase |
| Boundary clarity | 0% explicit | 100% explicit | 100% compliance |
| Quality consistency | Variable | ≥8/10 guaranteed | Predictable |
| Annual efficiency cost | $68,600 | $0 (automated) | $68,600 savings |

### Qualitative Metrics

**Developer Experience**:
- "Examples are much clearer now" (actionability)
- "I know exactly what this agent does" (specificity)
- "I understand when to use this agent vs manual work" (boundaries)

**AI Enhancement Quality**:
- Validation reports show consistent 8+/10 scores
- Fewer manual edits needed after enhancement
- Faster onboarding for new agents

---

## Risk Management

### Risk 1: AI Cannot Meet Thresholds

**Likelihood**: Low
**Mitigation**:
- Iterative refinement (3 attempts)
- If all fail, return best attempt + detailed report
- Human can manually enhance based on report

### Risk 2: Thresholds Too Strict

**Likelihood**: Medium
**Mitigation**:
- WARN vs FAIL distinction (only critical failures block)
- Monitor validation reports (Week 2)
- Adjust thresholds if >20% of agents fail

### Risk 3: Performance Impact

**Likelihood**: Low
**Impact**: Validation adds ~2-5 seconds per enhancement
**Mitigation**: Acceptable for quality improvement

### Risk 4: Backward Compatibility

**Likelihood**: Very Low
**Mitigation**:
- No changes to command interfaces
- Existing agents work as-is
- Validation is additive, not destructive

---

## Dependencies & Blockers

### Task Dependencies

```
TASK-AGENT-ENHANCER (4 hours)
  └─> TASK-AGENT-VALIDATE (24 hours)
       └─> TASK-TEST-87F4 (4-5 days)
```

### External Dependencies

- None (all work is internal to Taskwright)

### Blockers

- None identified

---

## Rollout Strategy

### Phase 1: Soft Launch (Week 1)

- Deploy TASK-AGENT-ENHANCER
- Test on 3 existing agents
- Validate quality improvements manually
- No forced migration (existing agents still work)

### Phase 2: Validation Tool (Week 2)

- Deploy TASK-AGENT-VALIDATE
- Run validation on all 15 global agents
- Identify low-scoring agents (<7/10)
- Prioritize enhancements

### Phase 3: Comprehensive Testing (Week 3)

- Deploy TASK-TEST-87F4
- Run full test suite
- Verify coverage targets (≥90% lines)
- Fix any regressions

### Phase 4: Batch Enhancement (Week 4+)

- Enhance remaining 12 global agents
- Monitor validation reports
- Refine thresholds based on real-world usage
- Document improvements

---

## Completion Criteria

### Must Have (Blocking)

- [ ] TASK-AGENT-ENHANCER complete (AC1-AC5)
- [ ] TASK-AGENT-VALIDATE complete (AC1-AC6)
- [ ] TASK-TEST-87F4 complete (all 150+ tests passing)
- [ ] All 15 existing agents still work (backward compatibility)
- [ ] Documentation updated (CLAUDE.md, command specs)

### Should Have (High Priority)

- [ ] Validation reports show ≥8/10 for enhanced agents
- [ ] Performance benchmarks met (<2s single, <20s batch)
- [ ] CI/CD integration working (GitHub Actions)
- [ ] Before/after improvement demonstrated on 3+ agents

### Nice to Have (Future Enhancements)

- [ ] Auto-enhance flag for validation tool
- [ ] Validation trend tracking (score over time)
- [ ] Custom threshold configuration per agent
- [ ] Validation report history

---

## Related Documentation

### Reference Documents

- [GitHub Agent Best Practices Analysis](../analysis/github-agent-best-practices-analysis.md) - Detailed comparison of Taskwright vs GitHub standards (20KB, 710 lines)
- [TASK-AI-2B37 Visual Comparison](./task-ai-2b37-visual-comparison.md) - Before/after examples for AI integration
- [TASK-AI-2B37 Clarification](./task-ai-2b37-clarification.md) - Implementation details for AI enhancement

### Task Files

- [TASK-AGENT-ENHANCER-20251121-160000](../../tasks/backlog/TASK-AGENT-ENHANCER-20251121-160000.md) - Enhance agent-content-enhancer.md (4 hours)
- [TASK-AGENT-VALIDATE-20251121-160001](../../tasks/backlog/TASK-AGENT-VALIDATE-20251121-160001.md) - Create validation tool (24 hours)
- [TASK-TEST-87F4](../../tasks/backlog/TASK-TEST-87F4-comprehensive-test-suite-agent-enhancement.md) - Comprehensive test suite (4-5 days)

### Superseded Tasks

These tasks are **archived** as their goals are now achieved through automated enforcement:

- ~~TASK-AGENT-STRUCT-20251121-151631~~ (structure enforced by validation)
- ~~TASK-AGENT-BOUND-20251121-151631~~ (boundaries enforced by validation)
- ~~TASK-AGENT-EXAMPLES-20251121-151804~~ (example density enforced by validation)

---

## Quick Start Guide

### For Implementers

**Week 1** (Start Here):
```bash
# 1. Read task specification
cat tasks/backlog/TASK-AGENT-ENHANCER-20251121-160000.md

# 2. Implement GitHub Best Practices section
vim installer/global/agents/agent-content-enhancer.md
# Add ~85 lines after line 50

# 3. Create shared validation module
vim .claude/commands/shared/agent_validation.py
# Implement validation functions

# 4. Test on 3 agents
/agent-enhance architectural-reviewer
/agent-enhance test-orchestrator
/agent-enhance code-reviewer

# 5. Verify improvements
diff architectural-reviewer.md.backup architectural-reviewer.md
# Should see: more examples, explicit boundaries, validation report
```

**Week 2**:
```bash
# 1. Create validation tool
vim lib/agent_validator/validator.py
# Implement core validator

# 2. Implement check modules
vim lib/agent_validator/checks/*.py
# 6 check categories

# 3. Test validation
/agent-validate installer/global/agents/code-reviewer.md
# Should output: scores, checks, recommendations
```

**Week 3**:
```bash
# 1. Implement test suite
pytest tests/unit/lib/agent_enhancement/ -v
pytest tests/integration/test_agent_enhancement_validation.py -v

# 2. Verify coverage
pytest --cov=lib/agent_validator --cov-report=term
# Should show: ≥90% line coverage
```

---

## Appendix: File Structure

### New Files Created

```
.claude/commands/shared/
  └── agent_validation.py          (~200 lines) - Shared validation logic

lib/agent_validator/
  ├── validator.py                  (~150 lines) - Core validator
  ├── models.py                     (~50 lines) - Data models
  ├── scoring.py                    (~100 lines) - Score aggregation
  ├── checks/
  │   ├── structure.py              (~100 lines) - Structure checks
  │   ├── example_density.py        (~100 lines) - Example checks
  │   ├── boundaries.py             (~80 lines) - Boundary checks
  │   ├── specificity.py            (~80 lines) - Specificity checks
  │   ├── example_quality.py        (~80 lines) - Quality checks
  │   └── maintenance.py            (~60 lines) - Maintenance checks
  ├── formatters/
  │   ├── console.py                (~150 lines) - Console output
  │   ├── json_formatter.py         (~80 lines) - JSON output
  │   └── minimal.py                (~40 lines) - Minimal output
  └── utils.py                      (~50 lines) - Helper functions

installer/global/commands/
  ├── agent-validate.md             (~100 lines) - Command spec
  └── agent-validate.py             (~80 lines) - Command entry point

tests/
  ├── unit/lib/agent_enhancement/
  │   └── test_validation.py        (~200 lines) - Validation tests
  └── integration/
      └── test_agent_enhancement_validation.py (~150 lines) - Integration tests

docs/implementation/
  └── agent-quality-enhancement-implementation-plan.md (this file)
```

### Modified Files

```
installer/global/agents/
  └── agent-content-enhancer.md     (+85 lines) - GitHub standards

installer/global/commands/
  └── agent-enhance.md              (+20 lines) - Validation output docs

CLAUDE.md                           (+30 lines) - Agent QA section
```

**Total Addition**: ~2,100 lines across 20+ files

---

## Contact & Support

**Questions?**
- Review [GitHub Agent Best Practices Analysis](../analysis/github-agent-best-practices-analysis.md)
- Read task specifications in `tasks/backlog/TASK-AGENT-*.md`
- Check implementation examples in task files

**Implementation Issues?**
- Refer to acceptance criteria in task files
- Run validation tests: `pytest tests/unit/lib/agent_enhancement/ -v`
- Check test fixtures in `tests/fixtures/`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
**Status**: Ready for Implementation
**Next Action**: Start TASK-AGENT-ENHANCER-20251121-160000
