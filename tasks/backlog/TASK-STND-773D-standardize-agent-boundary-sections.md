# TASK-STND-773D: Update Agent-Content-Enhancer to Generate ALWAYS/NEVER/ASK Boundary Sections

**Task ID**: TASK-STND-773D
**Priority**: HIGH
**Status**: BACKLOG
**Created**: 2025-11-22T12:30:00Z
**Updated**: 2025-11-22T15:00:00Z
**Tags**: [standardization, agent-enhancement, github-standards, process-improvement]
**Complexity**: 6/10 (Medium-High - process change with validation)
**Related**: TASK-AGENT-ENHANCER-20251121-160000 (completed), TASK-UX-B9F7 (completed)

---

## Overview

Update the `agent-content-enhancer` agent to automatically generate ALWAYS/NEVER/ASK boundary sections for ALL future agent enhancements, conforming to GitHub best practices analysis findings.

**Current State**:
- ✅ agent-content-enhancer generates high-quality content (8-10/10 specificity, 43-64% example density)
- ⚠️ agent-content-enhancer uses "Best Practices" and "Anti-Patterns" sections (outdated format)
- ⚠️ GitHub analysis shows 0/10 score for boundary clarity (Critical Gap #4)
- ✅ GitHub standards document exists with ALWAYS/NEVER/ASK requirements

**Target State**:
- ✅ agent-content-enhancer generates ALWAYS/NEVER/ASK boundary sections by default
- ✅ Boundary sections included in enhancement structure template
- ✅ Quality validation enforces boundary section presence
- ✅ All future enhanced agents conform to GitHub standards automatically
- ✅ Existing validation report includes boundary section metrics

**Impact**:
- **Process Change**: Updates agent generation workflow, not one-time conversion
- **Scope**: All future `/agent-enhance` invocations will generate ALWAYS/NEVER/ASK
- **Benefits**: Boundary clarity improves from 0/10 to 9/10 (GitHub standards compliance)

---

## Acceptance Criteria

### AC1: Agent-Content-Enhancer Documentation Update
- [ ] **AC1.1**: Update "Enhancement Structure" section to replace "Best Practices" with "Boundaries" section
- [ ] **AC1.2**: Add detailed ALWAYS/NEVER/ASK format specification with examples
- [ ] **AC1.3**: Document rule count requirements (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- [ ] **AC1.4**: Document emoji prefix requirements (✅ ALWAYS, ❌ NEVER, ⚠️ ASK)
- [ ] **AC1.5**: Add rule structure specification: `[emoji] [imperative verb] [action] ([brief rationale])`

### AC2: GitHub Standards Integration
- [ ] **AC2.1**: Reference github-agent-best-practices-analysis.md in agent-content-enhancer
- [ ] **AC2.2**: Include Boundary Sections as Critical Quality Threshold (currently lines 59-90)
- [ ] **AC2.3**: Add boundary section enforcement to Self-Validation Protocol (lines 136-176)
- [ ] **AC2.4**: Update validation report schema to include boundary_sections metric
- [ ] **AC2.5**: Document boundary section placement (after "Quick Start", before "Capabilities")

### AC3: Validation Enhancement
- [ ] **AC3.1**: Add boundary_sections check to Quality Enforcement Checklist (lines 264-273)
- [ ] **AC3.2**: Update validation report format to include boundary status (lines 275-309)
- [ ] **AC3.3**: Add boundary validation to iterative refinement loop
- [ ] **AC3.4**: Set FAIL threshold if ALWAYS/NEVER/ASK sections missing or incomplete
- [ ] **AC3.5**: Document boundary validation criteria (section presence, rule counts, emoji format)

### AC4: Output Format Specification
- [ ] **AC4.1**: Update section 9 "Enhancement Structure" (lines 310-348) to include Boundaries
- [ ] **AC4.2**: Replace "Best Practices" section with "Boundaries" section specification
- [ ] **AC4.3**: Add boundary section template with ALWAYS/NEVER/ASK structure
- [ ] **AC4.4**: Include example boundary rules for common agent types
- [ ] **AC4.5**: Document rule derivation guidance (how to categorize practices as ALWAYS/NEVER/ASK)

### AC5: Quality Requirements Update
- [ ] **AC5.1**: Add "ALWAYS/NEVER/ASK sections present" to quality requirements (lines 349-357)
- [ ] **AC5.2**: Update quality score interpretation to include boundary clarity
- [ ] **AC5.3**: Set minimum 3 sections required (ALWAYS, NEVER, ASK)
- [ ] **AC5.4**: Document failure behavior if boundary sections missing
- [ ] **AC5.5**: Add boundary completeness to confidence threshold calculation

### AC6: Testing & Validation
- [ ] **AC6.1**: Test agent-content-enhancer on sample agent (verify ALWAYS/NEVER/ASK generation)
- [ ] **AC6.2**: Verify validation report includes boundary_sections metric
- [ ] **AC6.3**: Confirm boundary sections match GitHub standards format
- [ ] **AC6.4**: Validate rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- [ ] **AC6.5**: Verify emoji usage correct (✅/❌/⚠️)

---

## Implementation Plan

**See**: [TASK-STND-773D-implementation-plan-NEW.md](./TASK-STND-773D-implementation-plan-NEW.md) for detailed 4-phase implementation guide.

### Summary

**Phase 1**: Agent-Content-Enhancer Documentation Update (2 hours)
- Update Enhancement Structure section (replace "Best Practices" with "Boundaries")
- Update Quality Enforcement Checklist (add boundary validation)
- Update Validation Report Schema (add boundary_completeness metrics)

**Phase 2**: Self-Validation Protocol Enhancement (1.5 hours)
- Add boundary validation to iterative refinement loop
- Document boundary placement (after "When to Use", before "Capabilities")
- Add reference to GitHub analysis document

**Phase 3**: Quality Requirements Update (1 hour)
- Update quality requirements (add boundary completeness)
- Update quality score interpretation (include boundary clarity)
- Update fallback behavior documentation

**Phase 4**: Testing & Documentation (1.5 hours)
- Create test agent for validation
- Validate against GitHub standards format
- Update CLAUDE.md documentation

**Total Effort**: 6 hours
**Risk**: Low (documentation-only changes)

### Files Modified

1. `installer/global/agents/agent-content-enhancer.md`:
   - Lines 310-348: Enhancement Structure (replace "Best Practices" with "Boundaries")
   - Lines 264-273: Quality Enforcement Checklist (add boundary checks)
   - Lines 275-309: Validation Report Schema (add boundary_completeness)
   - Lines 136-176: Self-Validation Protocol (add boundary validation)
   - Lines 349-357: Quality Requirements (add boundary sections)
   - Lines 374-381: Quality Score Interpretation (add boundary clarity)
   - Lines 383-390: Fallback Behavior (add boundary failure handling)

2. `CLAUDE.md`:
   - Add note about boundary sections in MCP Integration Best Practices section

3. Test agent (for validation):
   - `test-agents/sample-basic-agent.md`

### Key Changes

**Old Format**:
```markdown
### 7. Best Practices (3-5 practices)
DO and DON'T guidance derived from template patterns.
```


**New Format**:
```markdown
### 7. Boundaries (ALWAYS/NEVER/ASK)
Explicit behavior rules conforming to GitHub best practices.

**Structure**: ALWAYS (5-7 rules), NEVER (5-7 rules), ASK (3-5 scenarios)
**Emoji**: ✅ ALWAYS, ❌ NEVER, ⚠️ ASK
**Placement**: After "When to Use", before "Capabilities"
```

**Example**:
```markdown
## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
[... 3-5 more]

### NEVER
- ❌ Never approve code with failing tests (zero tolerance for test failures)
- ❌ Never skip compilation check (prevents false positive test runs)
[... 3-5 more]

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Performance tests failing: Ask if acceptable for non-production changes
[... 1-3 more]
```

---

## Testing Strategy

### Test 1: Documentation Validation

**Objective**: Verify agent-content-enhancer.md correctly documents boundary generation

**Method**: Manual review of updated sections

**Success Criteria**:
- Enhancement Structure section includes "Boundaries" (not "Best Practices")
- Quality Enforcement Checklist includes boundary validation checks
- Validation Report Schema includes boundary_completeness metrics
- Self-Validation Protocol includes boundary validation in iterative refinement

### Test 2: Boundary Generation Test

**Objective**: Verify enhanced agents contain ALWAYS/NEVER/ASK sections

**Method**:
```bash
# Create test agent
mkdir -p test-agents
cat > test-agents/test-repository-specialist.md << 'EOF'
---
name: test-repository-specialist
description: Repository pattern implementation
tools: [Read, Write, Edit]
---
# Test Repository Specialist
Basic agent for testing.
EOF

# Run enhancement
/agent-enhance test-template/test-repository-specialist

# Verify output contains boundaries
grep -A 20 "## Boundaries" test-agents/test-repository-specialist.md
```

**Success Criteria**:
- Enhanced agent contains "## Boundaries" section
- ALWAYS subsection present with 5-7 ✅ rules
- NEVER subsection present with 5-7 ❌ rules
- ASK subsection present with 3-5 ⚠️ scenarios

### Test 3: Validation Report Check

**Objective**: Verify validation report includes boundary metrics

**Method**: Inspect agent-enhance output

**Success Criteria**:
```yaml
validation_report:
  boundary_completeness:
    always_count: 5-7 ✅
    never_count: 5-7 ✅
    ask_count: 3-5 ✅
    emoji_correct: true ✅
    format_valid: true ✅
  overall_status: PASSED
```

### Test 4: GitHub Standards Compliance

**Objective**: Verify generated boundaries match GitHub best practices format

**Method**: Compare output to github-agent-best-practices-analysis.md examples (lines 240-260)

**Success Criteria**:
- Rule format: `- [emoji] [action] ([rationale])`
- Emoji usage correct (✅/❌/⚠️)
- Rule counts correct (5-7/5-7/3-5)
- Placement correct (after "When to Use", before "Capabilities")

---

## Design Decisions & Rationale

### Decision 1: Process Change vs One-Time Conversion

**Chosen**: Update agent-content-enhancer to generate ALWAYS/NEVER/ASK automatically
**Alternative**: Convert 7 existing maui-test agents manually

**Rationale**:
- ✅ Process change benefits ALL future agent enhancements (not just 7 agents)
- ✅ Prevents regression (new agents won't use old "Best Practices" format)
- ✅ Lower long-term maintenance (one source of truth in agent-content-enhancer)
- ✅ Scales to all templates (not limited to maui-test)
- ⚠️ Existing agents keep old format until re-enhanced (acceptable tradeoff)

### Decision 2: Rule Count Targets

**Chosen**: 5-7 ALWAYS, 5-7 NEVER, 3-5 ASK
**Alternative**: Flexible counts based on content

**Rationale**:
- ✅ Aligns with GitHub standards research
- ✅ Follows Miller's Law (7±2 items for memorability)
- ✅ Forces prioritization of critical rules
- ⚠️ May require combining related rules

### Decision 3: Code Example Placement

**Chosen**: Separate from Boundaries section
**Alternative**: Inline code examples in ALWAYS/NEVER

**Rationale**:
- ✅ Keeps Boundaries scannable
- ✅ Allows examples to demonstrate multiple rules
- ✅ Maintains clean separation of concerns
- ⚠️ Requires cross-referencing

### Decision 4: ASK Section Structure

**Chosen**: Question + Decision Criteria
**Alternative**: Conditional statements only

**Rationale**:
- ✅ Question format is more actionable
- ✅ Criteria help developers make informed decisions
- ✅ Aligns with pattern advisor recommendations
- ⚠️ Requires more effort to craft good questions

---

## Success Metrics

### Quantitative

- **Documentation updates**: 7 sections in agent-content-enhancer.md updated
- **Validation coverage**: Boundary checks added to all 3 validation points
- **Format compliance**: 100% (enhanced agents pass boundary validation)
- **GitHub standards score**: Boundary clarity improved from 0/10 to 9/10
- **Time to complete**: ≤6 hours

### Qualitative

- **Process improvement**: ALL future enhancements use ALWAYS/NEVER/ASK (not just one-time fix)
- **Scalability**: Works for all templates (not limited to maui-test)
- **Maintainability**: Single source of truth in agent-content-enhancer
- **Standards compliance**: Conforms to GitHub best practices research

### Validation

**Before Completion**:
- [ ] agent-content-enhancer.md updated (7 sections)
- [ ] Test agent enhanced successfully with boundaries
- [ ] Validation report includes boundary metrics
- [ ] All acceptance criteria met (AC1-AC6)
- [ ] Changes committed

**After Deployment** (2 weeks):
- [ ] All newly enhanced agents contain ALWAYS/NEVER/ASK sections
- [ ] Validation reports show boundary_completeness metrics
- [ ] No format violations in enhanced agents
- [ ] Boundary clarity score ≥9/10 in quality reports

---

## Risk Assessment

### Risk 1: Incorrect Boundary Generation by AI

**Likelihood**: Low (AI has context from agent description + templates)
**Impact**: Medium (enhanced agents may have weak boundaries)

**Mitigation**:
- Validation enforces rule counts (5-7/5-7/3-5)
- Iterative refinement (up to 3 attempts) if validation fails
- Human review during template-create Phase 7.5
- Fallback to basic agent if enhancement fails

### Risk 2: Existing Agents Not Updated

**Likelihood**: High (process change only affects new enhancements)
**Impact**: Low (existing agents still functional, just use old format)

**Mitigation**:
- Acceptable tradeoff (process change benefits all future agents)
- Can re-enhance existing agents manually if needed: `/agent-enhance template/agent`
- Document in CLAUDE.md that old format agents will phase out naturally

### Risk 3: Breaking Changes to agent-content-enhancer

**Likelihood**: Low (documentation-only changes, no code)
**Impact**: Medium (could affect template-create workflow)

**Mitigation**:
- Test with sample agent before completing task
- Validation report will catch malformed boundaries
- Rollback plan available (revert agent-content-enhancer.md)

---

## Rollout Plan

### Phase 1: Documentation Update (2 hours)
- Update Enhancement Structure section
- Update Quality Enforcement Checklist
- Update Validation Report Schema
- **Checkpoint**: All documentation sections updated

### Phase 2: Validation Enhancement (1.5 hours)
- Add boundary validation to Self-Validation Protocol
- Document boundary placement rules
- Add GitHub standards reference
- **Checkpoint**: Validation protocol includes boundaries

### Phase 3: Quality Requirements (1 hour)
- Update quality requirements
- Update quality score interpretation
- Update fallback behavior
- **Checkpoint**: Quality standards include boundaries

### Phase 4: Testing & Documentation (1.5 hours)
- Create and enhance test agent
- Verify boundary generation
- Validate against GitHub standards
- Update CLAUDE.md
- **Checkpoint**: Test passes, documentation complete

**Total Estimated Time**: 6 hours

---

## Dependencies

**Blocks**: None
**Blocked By**: None
**Related**:
- TASK-AGENT-ENHANCER-20251121-160000 (GitHub standards implementation) - Completed
- TASK-UX-B9F7 (agent-enhance UX simplification) - Independent

---

## Completion Checklist

Before marking this task complete:

- [ ] **AC1**: Agent-Content-Enhancer Documentation Update (5 sub-criteria)
  - [ ] AC1.1: Enhancement Structure section updated
  - [ ] AC1.2: ALWAYS/NEVER/ASK format specification added
  - [ ] AC1.3: Rule count requirements documented
  - [ ] AC1.4: Emoji prefix requirements documented
  - [ ] AC1.5: Rule structure specification added

- [ ] **AC2**: GitHub Standards Integration (5 sub-criteria)
  - [ ] AC2.1: Reference to github-agent-best-practices-analysis.md added
  - [ ] AC2.2: Boundary Sections as Critical Quality Threshold
  - [ ] AC2.3: Boundary enforcement in Self-Validation Protocol
  - [ ] AC2.4: Validation report schema updated
  - [ ] AC2.5: Boundary section placement documented

- [ ] **AC3**: Validation Enhancement (5 sub-criteria)
  - [ ] AC3.1: Boundary checks in Quality Enforcement Checklist
  - [ ] AC3.2: Validation report format includes boundary status
  - [ ] AC3.3: Boundary validation in iterative refinement loop
  - [ ] AC3.4: FAIL threshold for missing boundaries
  - [ ] AC3.5: Boundary validation criteria documented

- [ ] **AC4**: Output Format Specification (5 sub-criteria)
  - [ ] AC4.1: Enhancement Structure updated to include Boundaries
  - [ ] AC4.2: "Best Practices" replaced with "Boundaries"
  - [ ] AC4.3: Boundary section template added
  - [ ] AC4.4: Example boundary rules for common agents
  - [ ] AC4.5: Rule derivation guidance documented

- [ ] **AC5**: Quality Requirements Update (5 sub-criteria)
  - [ ] AC5.1: ALWAYS/NEVER/ASK sections in quality requirements
  - [ ] AC5.2: Quality score interpretation includes boundary clarity
  - [ ] AC5.3: Minimum 3 sections required (ALWAYS, NEVER, ASK)
  - [ ] AC5.4: Failure behavior documented
  - [ ] AC5.5: Boundary completeness in confidence threshold

- [ ] **AC6**: Testing & Validation (5 sub-criteria)
  - [ ] AC6.1: Test agent enhanced successfully with boundaries
  - [ ] AC6.2: Validation report includes boundary_sections metric
  - [ ] AC6.3: Boundary sections match GitHub standards format
  - [ ] AC6.4: Rule counts validated (5-7/5-7/3-5)
  - [ ] AC6.5: Emoji usage verified (✅/❌/⚠️)

- [ ] All 4 phases complete (6 hours total)
- [ ] Test agent passes validation
- [ ] CLAUDE.md updated with boundary section note
- [ ] Changes committed to git
- [ ] Detailed implementation plan created

---

**Created**: 2025-11-22T12:30:00Z
**Updated**: 2025-11-22T15:00:00Z
**Status**: BACKLOG
**Ready for Implementation**: YES
**Complexity**: 6/10 (Medium-High - process change with validation)
**Estimated Effort**: 6 hours

---

## Related Documents

- **Implementation Plan**: [TASK-STND-773D-implementation-plan-NEW.md](./TASK-STND-773D-implementation-plan-NEW.md)
- **GitHub Analysis**: [docs/analysis/github-agent-best-practices-analysis.md](../../docs/analysis/github-agent-best-practices-analysis.md)
- **Target Agent**: [installer/global/agents/agent-content-enhancer.md](../../installer/global/agents/agent-content-enhancer.md)
- **Related Tasks**:
  - TASK-AGENT-ENHANCER-20251121-160000 (GitHub standards foundation) - ✅ Completed
  - TASK-UX-B9F7 (agent-enhance flag simplification) - ✅ Completed
