# TASK-056 Implementation Plan: Audit Existing Templates

**Created**: 2025-11-08
**Task**: TASK-056 - Audit Existing Templates with Comprehensive Validation
**Complexity**: 6/10 (Medium)
**Estimated Effort**: 3-5 days

---

## Executive Summary

Perform comprehensive quality audit of all existing GuardKit templates using the `/template-validate` command (implemented in TASK-044). Generate individual audit reports for each template, create comparative analysis, and produce template removal plan to inform the 3-template strategy decision.

---

## Objectives

### Primary Objective
Audit all existing templates using `/template-validate` 16-section framework and produce actionable quality reports.

### Success Criteria
- All templates audited using comprehensive validation
- Individual audit reports generated (audit-report.md per template)
- Comparative analysis report created
- Template removal plan documented
- Findings inform TASK-060 (removal decisions)

---

## Scope

### In Scope
1. Auditing all templates in `installer/global/templates/`
2. Running full 16-section validation for each template
3. Collecting and aggregating quality scores
4. Identifying common patterns (strengths/weaknesses)
5. Creating comparative analysis report
6. Creating template removal plan
7. Documenting audit methodology

### Out of Scope
- Fixing template issues (separate tasks)
- Creating new templates (TASK-057, TASK-058, TASK-059)
- Implementing template removal (TASK-060)
- Auto-fix feature development (that's TASK-064)

---

## Implementation Approach

### Phase 1: Discovery and Preparation (0.5 day)

**Tasks:**
1. Enumerate all templates in `installer/global/templates/`
2. Verify `/template-validate` command is accessible
3. Test command on one sample template
4. Create tracking spreadsheet for audit progress
5. Set up output directory structure

**Deliverables:**
- List of all templates to audit
- Verification that command works
- Progress tracking document

**Files to Read:**
- `installer/global/templates/` (directory listing)
- `installer/global/commands/template-validate.md` (command spec)
- `installer/global/commands/lib/template_validate_cli.py` (implementation)

### Phase 2: Template Audits - Batch 1 (1.5 days)

**Templates to Audit:**
1. default
2. react
3. python
4. typescript-api
5. maui-appshell

**Process for Each Template:**
```bash
/template-validate installer/global/templates/{template-name}
# Run full 16-section interactive audit
# Review generated audit-report.md
# Document key findings in tracking spreadsheet
```

**Deliverables:**
- 5 audit reports: `{template-name}/audit-report.md`
- 5 session files: `{template-name}/audit-session-*.json`
- Initial observations document

**Expected Outputs Per Template:**
- Overall score (0-10)
- Grade (A+, A, A-, B+, B, C, D, F)
- Section scores (1-16)
- Top 5 strengths
- Top 5 weaknesses
- Critical issues
- Production readiness decision

### Phase 3: Template Audits - Batch 2 (1 day)

**Templates to Audit:**
6. maui-navigationpage
7. dotnet-fastendpoints
8. dotnet-aspnetcontroller
9. dotnet-minimalapi

**Process:**
Same as Phase 2

**Deliverables:**
- 4 audit reports
- 4 session files
- Combined observations from all 9 templates

### Phase 4: Comparative Analysis (1 day)

**Tasks:**
1. Aggregate all scores into comparison table
2. Categorize templates by quality level:
   - High Quality (8-10)
   - Medium Quality (6-7.9)
   - Low Quality (<6)
3. Identify common strengths across templates
4. Identify common weaknesses across templates
5. Analyze patterns by technology stack
6. Create visualization of score distribution
7. Write comparative analysis report

**Deliverables:**
- `docs/research/template-audit-comparative-analysis.md`

**Report Structure:**
```markdown
# Template Audit Comparative Analysis

## Executive Summary
- Audit date, methodology, templates audited

## Overall Scores
| Template | Score | Grade | Recommendation |
|----------|-------|-------|----------------|
| ...      | ...   | ...   | ...            |

## Quality Distribution
- High/Medium/Low breakdown

## Key Findings
### Templates Meeting 8+/10 Bar
### Templates Below Bar

## Common Strengths/Weaknesses
## Recommendations for Template Strategy
### Keep (Reference Implementations)
### Remove
### Improve Before Decision

## Impact on 3-Template Strategy
```

### Phase 5: Template Removal Plan (0.5 day)

**Tasks:**
1. List templates scoring below 8/10
2. Assess user impact for each removal
3. Document migration paths
4. Create deprecation timeline
5. Draft communication strategy

**Deliverables:**
- `docs/research/template-removal-plan.md`

**Report Structure:**
```markdown
# Template Removal Plan

## Templates Scheduled for Removal
- Template name, score, rationale

## User Impact Assessment
- Current usage estimates
- Breaking changes

## Migration Paths
- Recommended alternatives
- Migration guides

## Deprecation Timeline
- Announcement date
- Deprecation period
- Removal date

## Communication Strategy
- Documentation updates
- User notifications
- Support plan
```

### Phase 6: Documentation and Finalization (0.5 day)

**Tasks:**
1. Review all audit reports for consistency
2. Finalize comparative analysis
3. Finalize removal plan
4. Create summary presentation
5. Link findings to template strategy decision docs

**Deliverables:**
- Updated task documentation
- Links to related tasks
- Summary of findings

---

## File Changes

### Files to Create

**Audit Reports (9 files):**
1. `installer/global/templates/default/audit-report.md`
2. `installer/global/templates/react/audit-report.md`
3. `installer/global/templates/python/audit-report.md`
4. `installer/global/templates/typescript-api/audit-report.md`
5. `installer/global/templates/maui-appshell/audit-report.md`
6. `installer/global/templates/maui-navigationpage/audit-report.md`
7. `installer/global/templates/dotnet-fastendpoints/audit-report.md`
8. `installer/global/templates/dotnet-aspnetcontroller/audit-report.md`
9. `installer/global/templates/dotnet-minimalapi/audit-report.md`

**Analysis Documents (2 files):**
1. `docs/research/template-audit-comparative-analysis.md`
2. `docs/research/template-removal-plan.md`

**Session Files (9 files):**
- `{template-name}/audit-session-*.json` (auto-generated)

### Files to Read (for context)

**Existing Documentation:**
- `docs/research/template-strategy-decision.md`
- `docs/research/template-validation-strategy.md`
- `installer/global/commands/template-validate.md`

**Existing Templates:**
- All 9 template directories in `installer/global/templates/`

### Files to Update

**Task File:**
- `tasks/in_progress/TASK-056-audit-existing-templates.md`
  - Update status as phases complete
  - Check off acceptance criteria
  - Update with actual findings

---

## Testing Strategy

### Validation Tests

**Test 1: Verify Audit Reports Exist**
```bash
# Expected: 9 audit reports
ls -la installer/global/templates/*/audit-report.md | wc -l
# Should return: 9
```

**Test 2: Verify Comparative Analysis Exists**
```bash
test -f docs/research/template-audit-comparative-analysis.md
echo $?
# Should return: 0
```

**Test 3: Verify Removal Plan Exists**
```bash
test -f docs/research/template-removal-plan.md
echo $?
# Should return: 0
```

**Test 4: Validate Report Format**
```bash
# Check that all reports have required sections
for report in installer/global/templates/*/audit-report.md; do
  grep -q "Overall Score:" "$report" && \
  grep -q "Grade:" "$report" && \
  grep -q "Strengths" "$report" && \
  grep -q "Weaknesses" "$report" || \
  echo "Missing sections in $report"
done
```

### Quality Checks

**QC1: Score Consistency**
- All scores are 0-10 scale ✓
- All grades match score thresholds ✓
- No missing scores ✓

**QC2: Report Completeness**
- All 16 sections completed per template ✓
- All critical issues documented ✓
- All recommendations are actionable ✓

**QC3: Analysis Quality**
- Comparative analysis covers all templates ✓
- Common patterns identified ✓
- Recommendations linked to scores ✓

**QC4: Removal Plan Quality**
- User impact assessed ✓
- Migration paths documented ✓
- Timeline is realistic ✓

---

## Risk Assessment

### Risk 1: Templates Discovered Beyond 9
**Probability**: Medium
**Impact**: Low
**Mitigation**: Already discovered 10+ templates in initial scan. Will audit all templates found, not just the 9 listed in task.

### Risk 2: Audit Process Too Time-Consuming
**Probability**: Medium
**Impact**: Medium
**Mitigation**:
- Use focused section selection for quicker audits if needed
- Prioritize technical sections (1-7) over optional sections
- Use --non-interactive mode if time-constrained

### Risk 3: All Templates Score Low
**Probability**: High (expected)
**Impact**: Low (validates strategy)
**Mitigation**: This is actually the expected outcome and validates the decision to create new templates from exemplar repos.

### Risk 4: Command Issues During Audits
**Probability**: Low
**Impact**: High
**Mitigation**: Test command thoroughly in Phase 1 before starting batch audits. Have fallback to manual section-by-section validation.

---

## Dependencies

### Blocking Dependencies
- **TASK-044**: Template Validate Command (✅ COMPLETE)
  - Required: `/template-validate` command implementation
  - Status: Completed, verified working

### Optional Dependencies
- **TASK-045**: AI-assisted validation (⚪ OPTIONAL)
  - Would speed up sections 8, 11, 12, 13
  - Not required for completion

### Dependent Tasks
- **TASK-060**: Remove Low-Quality Templates
  - Blocked by: TASK-056 completion
  - Requires: Audit findings and removal plan

---

## Success Metrics

### Quantitative Metrics
- **Templates Audited**: 100% (all templates in directory)
- **Audit Reports Generated**: 1 per template
- **Comparative Analysis**: 1 document
- **Removal Plan**: 1 document
- **Coverage**: All 16 sections per template

### Qualitative Metrics
- **Audit Methodology**: Systematic and repeatable
- **Finding Quality**: Evidence-based, objective scoring
- **Report Clarity**: Comprehensive and actionable
- **Strategic Value**: Findings inform template strategy decisions

### Acceptance Gates
- [ ] All templates audited with full 16-section framework
- [ ] All audit reports contain complete scoring and findings
- [ ] Comparative analysis includes all templates with aggregated insights
- [ ] Removal plan addresses user impact and migration paths
- [ ] All deliverables reviewed and validated
- [ ] Findings documented in task file
- [ ] Related tasks (TASK-060) unblocked

---

## Timeline

**Total Estimated Duration**: 5 days

| Phase | Duration | Days |
|-------|----------|------|
| Phase 1: Discovery & Prep | 4 hours | 0.5 |
| Phase 2: Audits Batch 1 (5 templates) | 12 hours | 1.5 |
| Phase 3: Audits Batch 2 (4 templates) | 8 hours | 1.0 |
| Phase 4: Comparative Analysis | 8 hours | 1.0 |
| Phase 5: Removal Plan | 4 hours | 0.5 |
| Phase 6: Documentation | 4 hours | 0.5 |
| **Total** | **40 hours** | **5 days** |

**Note**: Timeline assumes 8-hour working days and may be compressed with parallel work or extended if templates require deeper analysis.

---

## Related Documents

- **Task Definition**: `tasks/in_progress/TASK-056-audit-existing-templates.md`
- **Command Spec**: `installer/global/commands/template-validate.md`
- **Strategy Docs**:
  - `docs/research/template-strategy-decision.md`
  - `docs/research/template-validation-strategy.md`
- **Related Tasks**:
  - TASK-044: Template Validate Command (prerequisite)
  - TASK-060: Remove Low-Quality Templates (dependent)
  - TASK-057, TASK-058, TASK-059: Create new reference templates

---

## Notes

### Audit Approach
- Use interactive mode for thorough analysis
- Document findings immediately after each audit
- Take screenshots of key sections if needed
- Save session files for potential resume

### Quality Focus
- Prioritize objectivity in scoring
- Base recommendations on evidence, not assumptions
- Document both strengths and weaknesses
- Focus on actionable findings

### Communication
- Share findings with stakeholders after each batch
- Request feedback on initial observations
- Validate scoring methodology before final analysis

---

**Plan Status**: Ready for Implementation
**Review Status**: Pending Phase 2.5 Architectural Review
**Approval Status**: Pending Human Checkpoint (if required)
