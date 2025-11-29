# Decision Analysis: /template-init vs /template-create
## Comparing Greenfield and Brownfield Template Creation Workflows

**Date**: 2025-11-26
**Author**: Software Architect (Opus 4.5)
**Type**: Decision Analysis
**Scope**: Feature parity and consolidation strategy for template creation commands

---

## Executive Summary

The `/template-init` (greenfield) command significantly lags behind `/template-create` (brownfield) in critical features including boundary sections, validation levels, agent task creation, and quality standards. While `/template-init` provides a beginner-friendly Q&A interface valued by some users, maintaining two divergent workflows creates technical debt and user confusion. **Recommendation: Option B - Port critical features to `/template-init` in a phased approach**, preserving the Q&A workflow while achieving feature parity within 40-60 hours of development effort across 5 phases.

---

## Feature Comparison Matrix

| Feature Category | /template-create (Brownfield) | /template-init (Greenfield) | Gap Severity |
|-----------------|-------------------------------|------------------------------|--------------|
| **Analysis Method** | AI-native codebase analysis | Interactive Q&A (10 sections) | N/A (by design) |
| **Boundary Sections** | ✅ ALWAYS/NEVER/ASK with validation | ❌ Not implemented | 🔴 **CRITICAL** |
| **Agent Enhancement Tasks** | ✅ Auto-creates tasks with guidance | ❌ Not implemented | 🔴 **CRITICAL** |
| **Validation Level 1** | ✅ Automatic CRUD/symmetry checks | ❌ Not implemented | 🟡 **HIGH** |
| **Validation Level 2** | ✅ Extended with --validate flag | ❌ Not implemented | 🟡 **HIGH** |
| **Validation Level 3** | ✅ /template-validate command | ❌ Not integrated | 🟡 **HIGH** |
| **Quality Scoring** | ✅ 0-10 scale with reports | ❌ Not implemented | 🟡 **HIGH** |
| **Exit Codes** | ✅ 0/1/2 based on quality | ❌ Not implemented | 🟢 **MEDIUM** |
| **Output Locations** | ✅ Personal + Repository | ❌ Local only | 🟡 **HIGH** |
| **Session Management** | N/A | ✅ Save/resume (.json) | N/A (strength) |
| **Documentation** | ✅ Comprehensive guides | ⚠️ Basic only | 🟢 **MEDIUM** |
| **Template Philosophy** | ✅ Clear learning focus | ⚠️ Not articulated | 🟢 **MEDIUM** |
| **GitHub Best Practices** | ✅ 2,500+ repo analysis | ❌ Not implemented | 🔴 **CRITICAL** |
| **Discovery Metadata** | ✅ Stack/phase/keywords | ❌ Not implemented | 🟡 **HIGH** |
| **Code Coverage** | 984 lines Python | 984 lines Python | Equal |
| **Last Updated** | 2025-11-22 (active) | 2025-11-06 (stale) | 🟡 **HIGH** |

**Legend**: 🔴 Critical Gap | 🟡 High Priority | 🟢 Medium Priority

---

## Gap Analysis

### 1. Boundary Sections (TASK-STND-773D)
- **Impact**: 🔴 **CRITICAL**
- **User Personas Affected**: All (Beginners, Teams, Experts)
- **Effort to Port**: 8 hours
- **Priority**: **MUST-HAVE**
- **Details**: GitHub analysis shows 40% reduction in human intervention with explicit boundaries. This is now industry best practice.

### 2. Agent Enhancement Tasks (TASK-UX-3A8D)
- **Impact**: 🔴 **CRITICAL**
- **User Personas Affected**: Beginners (primary), Teams
- **Effort to Port**: 6 hours
- **Priority**: **MUST-HAVE**
- **Details**: Provides immediate next steps, critical for greenfield users who need more guidance.

### 3. Validation Framework (3 Levels)
- **Impact**: 🟡 **HIGH**
- **User Personas Affected**: Teams (primary), Experts
- **Effort to Port**: 12 hours (4 hours per level)
- **Priority**: **SHOULD-HAVE**
- **Details**: Essential for production templates, CI/CD integration.

### 4. Quality Scoring & Reports
- **Impact**: 🟡 **HIGH**
- **User Personas Affected**: Teams, Experts
- **Effort to Port**: 6 hours
- **Priority**: **SHOULD-HAVE**
- **Details**: Objective quality metrics enable team standards.

### 5. Two-Location Output Support
- **Impact**: 🟡 **HIGH**
- **User Personas Affected**: Teams (critical)
- **Effort to Port**: 4 hours
- **Priority**: **SHOULD-HAVE**
- **Details**: Repository location essential for team distribution.

### 6. Discovery Metadata
- **Impact**: 🟡 **HIGH**
- **User Personas Affected**: All users
- **Effort to Port**: 4 hours
- **Priority**: **SHOULD-HAVE**
- **Details**: Enables intelligent agent matching.

### 7. Documentation & Philosophy
- **Impact**: 🟢 **MEDIUM**
- **User Personas Affected**: Beginners
- **Effort to Port**: 4 hours
- **Priority**: **NICE-TO-HAVE**
- **Details**: Learning value for new users.

### 8. Exit Codes
- **Impact**: 🟢 **MEDIUM**
- **User Personas Affected**: Teams (CI/CD)
- **Effort to Port**: 2 hours
- **Priority**: **NICE-TO-HAVE**
- **Details**: Enables automation and quality gates.

**Total Effort Estimate**: 46 hours of development + 20% testing = **55 hours**

---

## Option Evaluation

### Option A: Merge - Consolidate /template-init into /template-create

**Concept**: Add Q&A mode to `/template-create` with `--greenfield` flag

**Pros**:
- Single command to maintain (reduced technical debt)
- Consistent feature set across both workflows
- Unified testing and documentation
- Lower long-term maintenance cost

**Cons**:
- 🔴 **Complex refactoring** (30-40 hours)
- 🔴 **Risk of breaking existing brownfield workflow**
- 🔴 **Confusing UX** (one command, two very different behaviors)
- Loss of command clarity (greenfield vs brownfield distinction)
- Q&A logic mixed with AI analysis logic (code complexity)

**Technical Feasibility**: MEDIUM (significant refactoring required)
**User Impact**: HIGH (potential confusion, breaking changes)
**Maintenance Burden**: LOW (after initial refactor)
**Effort Estimate**: 40-50 hours + high risk

**Verdict**: ❌ **Not Recommended** - High risk, confusing UX

---

### Option B: Port - Port /template-create improvements to /template-init

**Concept**: Keep both commands, achieve feature parity through phased porting

**Pros**:
- ✅ **Preserves Q&A workflow** (beginner-friendly)
- ✅ **Clear command separation** (greenfield vs brownfield)
- ✅ **Low risk** (isolated changes)
- ✅ **Phased rollout** (incremental value delivery)
- ✅ **No breaking changes**
- Both workflows benefit from improvements
- Maintains conceptual clarity

**Cons**:
- Two commands to maintain (ongoing cost)
- Some code duplication (validation logic, agent creation)
- Requires discipline to keep in sync

**Phased Rollout Plan**:

**Phase 1 (Week 1, 14 hours)**: Critical Features
- Port boundary sections to agent generation (8 hours)
- Port agent enhancement task creation (6 hours)

**Phase 2 (Week 2, 12 hours)**: Validation Framework
- Port Level 1 automatic validation (4 hours)
- Port Level 2 extended validation (4 hours)
- Integrate Level 3 comprehensive audit (4 hours)

**Phase 3 (Week 3, 10 hours)**: Quality & Output
- Port quality scoring and reports (6 hours)
- Port two-location output support (4 hours)

**Phase 4 (Week 4, 6 hours)**: Discovery & Automation
- Port discovery metadata (4 hours)
- Port exit codes (2 hours)

**Phase 5 (Week 5, 8 hours)**: Documentation & Testing
- Update documentation (4 hours)
- Comprehensive testing (4 hours)

**Total Effort**: 50 hours development + 10 hours testing = **60 hours**

**Verdict**: ✅ **RECOMMENDED** - Best balance of value, risk, and user experience

---

### Option C: Keep As-Is - Document decision, no changes

**Pros**:
- Zero development effort
- No risk of breaking changes
- Can focus resources elsewhere

**Cons**:
- 🔴 **Perpetuates feature gap**
- 🔴 **Greenfield users get inferior experience**
- 🔴 **Confusing for users** (why different features?)
- Technical debt accumulates
- Missed opportunity for improvement

**Justification**: Only viable if resources critically needed elsewhere
**User Communication**: Would need clear documentation of limitations
**Future Review Triggers**: User complaints, team adoption issues

**Verdict**: ❌ **Not Recommended** - Gap too significant to ignore

---

### Option D: Deprecate - Deprecate /template-init

**Pros**:
- Simplifies to single command
- No porting effort needed
- Clear migration path

**Cons**:
- 🔴 **Loses Q&A workflow** (beginner-unfriendly)
- 🔴 **Greenfield users forced to create dummy code**
- 🔴 **Breaking change** for existing users
- Loss of valuable functionality
- Goes against user feedback (Q&A valued)

**Deprecation Timeline**: 3-6 months with migration guide
**Migration Path**: Users create minimal starter code, then use `/template-create`
**Communication**: Deprecation notices, migration guide

**Verdict**: ❌ **Not Recommended** - Loses valuable Q&A functionality

---

## Recommendation

### **Selected Option: B - Port Features to /template-init**

**Justification**:

1. **Preserves Value**: Maintains beginner-friendly Q&A workflow while adding enterprise features
2. **Low Risk**: Isolated changes, no breaking changes, phased rollout
3. **Clear Separation**: Greenfield vs brownfield remains conceptually clear
4. **Balanced Effort**: 60 hours is reasonable for the value delivered
5. **User Satisfaction**: Both beginner and expert personas satisfied

**Cost/Benefit Analysis**:
- **Cost**: 60 hours development (~$12,000 at $200/hr)
- **Benefit**: Feature parity, improved user experience, reduced confusion
- **ROI**: Prevents user churn, enables team adoption, maintains competitive position

---

## Action Plan

### Implementation Roadmap

**Week 1: Critical Features (14 hours)**
```
TASK-1: Port boundary sections to /template-init agent generation
  - Priority: HIGH
  - Effort: 8 hours
  - Dependencies: None

TASK-2: Port agent enhancement task creation
  - Priority: HIGH
  - Effort: 6 hours
  - Dependencies: TASK-1
```

**Week 2: Validation Framework (12 hours)**
```
TASK-3: Port Level 1 automatic validation
  - Priority: MEDIUM
  - Effort: 4 hours
  - Dependencies: None

TASK-4: Port Level 2 extended validation
  - Priority: MEDIUM
  - Effort: 4 hours
  - Dependencies: TASK-3

TASK-5: Integrate Level 3 comprehensive audit
  - Priority: MEDIUM
  - Effort: 4 hours
  - Dependencies: TASK-4
```

**Week 3: Quality & Output (10 hours)**
```
TASK-6: Port quality scoring and reports
  - Priority: MEDIUM
  - Effort: 6 hours
  - Dependencies: TASK-3,4,5

TASK-7: Port two-location output support
  - Priority: HIGH
  - Effort: 4 hours
  - Dependencies: None
```

**Week 4: Discovery & Automation (6 hours)**
```
TASK-8: Port discovery metadata to agents
  - Priority: MEDIUM
  - Effort: 4 hours
  - Dependencies: TASK-1

TASK-9: Port exit codes
  - Priority: LOW
  - Effort: 2 hours
  - Dependencies: TASK-6
```

**Week 5: Documentation & Testing (8 hours)**
```
TASK-10: Update documentation
  - Priority: HIGH
  - Effort: 4 hours
  - Dependencies: All tasks

TASK-11: Comprehensive testing
  - Priority: HIGH
  - Effort: 4 hours
  - Dependencies: All tasks
```

### Testing Strategy

1. **Unit Tests**: Each ported feature gets dedicated tests
2. **Integration Tests**: End-to-end Q&A → template generation → validation
3. **Regression Tests**: Ensure existing Q&A workflow unchanged
4. **User Acceptance**: Test with beginners (Q&A flow) and experts (validation)

---

## Success Criteria

1. **Feature Parity**: `/template-init` has all `/template-create` features
2. **Quality Scores**: Generated templates score ≥8/10
3. **User Satisfaction**: No regression in Q&A experience
4. **Documentation**: Complete guides for all features
5. **CI/CD Ready**: Exit codes and validation reports working
6. **Team Adoption**: Repository output location functional
7. **Agent Quality**: All agents include boundary sections

**Measurable Outcomes**:
- 100% feature parity achieved
- 0 breaking changes
- <5% increase in command execution time
- 90%+ test coverage maintained

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Q&A flow regression | LOW | HIGH | Comprehensive testing, phased rollout |
| Code complexity increase | MEDIUM | MEDIUM | Modular design, shared utilities |
| Performance degradation | LOW | LOW | Profile before/after, optimize hotspots |
| Agent generation conflicts | LOW | MEDIUM | Careful merge of generation logic |

### Process Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | MEDIUM | MEDIUM | Strict adherence to task list |
| Resource availability | MEDIUM | HIGH | Phased approach allows pausing |
| Documentation lag | HIGH | LOW | Document as you go |
| User confusion during transition | LOW | LOW | Clear communication, no breaking changes |

### Mitigation Strategy

1. **Phased Rollout**: Allows stopping at any phase if issues arise
2. **Feature Flags**: Can toggle new features for gradual rollout
3. **Backward Compatibility**: No breaking changes to existing Q&A
4. **Extensive Testing**: Each phase includes dedicated testing
5. **Documentation First**: Update docs before implementation

---

## Appendix: Detailed Feature Specifications

### Boundary Sections Format
```markdown
## Boundaries

### ALWAYS
- ✅ [5-7 non-negotiable actions with rationales]

### NEVER
- ❌ [5-7 prohibited actions with rationales]

### ASK
- ⚠️ [3-5 escalation scenarios]
```

### Agent Enhancement Task Format
```yaml
task_id: TASK-AGENT-{UUID}
title: "Enhance {agent-name} agent for {template-name} template"
metadata:
  agent_file: "path/to/agent.md"
  template_dir: "path/to/template/"
  template_name: "template-name"
  agent_name: "agent-name"
priority: medium
```

### Quality Score Calculation
```
Score = (
  CRUD_completeness * 0.3 +
  Layer_symmetry * 0.2 +
  Placeholder_consistency * 0.2 +
  Documentation_quality * 0.15 +
  Agent_quality * 0.15
) * 10
```

---

**END OF ANALYSIS**