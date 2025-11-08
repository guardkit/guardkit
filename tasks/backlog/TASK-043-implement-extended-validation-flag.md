# TASK-043: Implement Extended Validation Flag (Phase 1)

**Created**: 2025-01-08
**Priority**: Medium
**Type**: Enhancement
**Parent**: Template Validation Strategy
**Status**: Backlog
**Complexity**: 3/10 (Low-Medium)
**Estimated Effort**: 1 day (6-8 hours)

---

## Problem Statement

Add optional `--validate` flag to `/template-create` command to provide extended validation with detailed quality reports. This enables users to get comprehensive quality insights before sharing templates with their team.

**Goal**: Provide Level 2 (Standard) validation from the [Template Validation Strategy](../../docs/research/template-validation-strategy.md) - extended automated validation with report generation.

---

## Context

**Related Documents**:
- [Template Validation Strategy](../../docs/research/template-validation-strategy.md)
- [Template Quality Validation Guide](../../docs/guides/template-quality-validation.md)
- [Template Completeness Validation Checklist](../../docs/checklists/template-completeness-validation.md)

**Current State**:
- Phase 5.5 validation exists (TASK-040) - automatic CRUD/layer checks
- Runs by default with auto-fix enabled
- Provides basic quality assurance (Level 1)
- No detailed reporting or extended checks

**Desired State**:
- Optional `--validate` flag for extended validation
- Comprehensive quality report generation
- Additional checks beyond Phase 5.5
- Exit codes based on quality scores
- Foundation for CI/CD integration

---

## Objectives

### Primary Objective
Implement `--validate` flag that runs extended validation and generates detailed quality reports.

### Success Criteria
- [x] `--validate` flag added to `/template-create` command
- [x] Extended validation runs after Phase 5.5
- [x] Validation report generated as markdown file
- [x] Exit code reflects quality score (0 = ≥8/10, 1 = 6-7.9/10, 2 = <6/10)
- [x] Extended checks include:
  - Placeholder consistency validation
  - Pattern fidelity spot-checks (5 random files)
  - Documentation completeness verification
  - Agent reference validation
  - Manifest accuracy checks
- [x] Report includes actionable recommendations
- [x] Works with existing flags (`--dry-run`, `--skip-validation`, etc.)
- [x] Documentation updated
- [x] Tests passing (≥80% coverage)

---

## Implementation Scope

### Files to Modify

#### 1. Command Specification
**File**: `installer/global/commands/template-create.md`

**Changes**:
Add `--validate` flag documentation:
```markdown
--validate               Run extended validation and generate quality report
                         Default: false (only Phase 5.5 runs)

                         When enabled:
                         - Runs all Phase 5.5 checks
                         - Adds extended validation checks
                         - Generates validation-report.md
                         - Exit code based on quality score
```

#### 2. Orchestrator Configuration
**File**: `installer/global/commands/lib/template_create_orchestrator.py`

**Changes**:
```python
@dataclass
class OrchestrationConfig:
    # ... existing fields ...
    validate: bool = False  # NEW: Extended validation flag
```

**New Method**:
```python
def _phase5_7_extended_validation(
    self,
    templates: TemplateCollection,
    manifest: Dict[str, Any],
    settings: Dict[str, Any],
    claude_md_path: Path,
    agents: List[Path]
) -> ExtendedValidationReport:
    """
    Phase 5.7: Extended Validation (only if --validate flag set)

    Runs after Phase 5.5 completeness validation.
    Performs deeper quality checks and generates report.
    """
```

### Files to Create

#### 1. Extended Validator
**File**: `installer/global/lib/template_validation/extended_validator.py`

**Purpose**: Perform extended validation checks

**Class**:
```python
@dataclass
class ExtendedValidationReport:
    """Extended validation report with detailed findings"""
    overall_score: float  # 0-10
    placeholder_consistency_score: float
    pattern_fidelity_score: float
    documentation_score: float
    agent_validation_score: float
    manifest_accuracy_score: float

    issues: List[ValidationIssue]
    recommendations: List[str]
    spot_check_results: List[SpotCheckResult]

    def is_production_ready(self) -> bool:
        """Returns True if score ≥ 8.0"""
        return self.overall_score >= 8.0

    def get_grade(self) -> str:
        """Returns letter grade (A+, A, A-, B+, B, C, F)"""
        if self.overall_score >= 9.5: return "A+"
        if self.overall_score >= 9.0: return "A"
        if self.overall_score >= 8.5: return "A-"
        if self.overall_score >= 8.0: return "B+"
        if self.overall_score >= 7.0: return "B"
        if self.overall_score >= 6.0: return "C"
        return "F"


class ExtendedValidator:
    """Extended template validation beyond Phase 5.5"""

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate(
        self,
        templates: TemplateCollection,
        manifest: Dict[str, Any],
        settings: Dict[str, Any],
        claude_md_path: Path,
        agents: List[Path]
    ) -> ExtendedValidationReport:
        """Run all extended validation checks"""

        # 1. Placeholder consistency
        placeholder_score = self._validate_placeholder_consistency(templates)

        # 2. Pattern fidelity (spot-check 5 random files)
        fidelity_score, spot_checks = self._validate_pattern_fidelity(templates)

        # 3. Documentation completeness
        doc_score = self._validate_documentation(claude_md_path, manifest, agents)

        # 4. Agent validation
        agent_score = self._validate_agents(agents, claude_md_path)

        # 5. Manifest accuracy
        manifest_score = self._validate_manifest(manifest, templates)

        # Calculate overall score (weighted)
        overall_score = self._calculate_overall_score(
            placeholder_score,
            fidelity_score,
            doc_score,
            agent_score,
            manifest_score
        )

        return ExtendedValidationReport(...)

    def _validate_placeholder_consistency(
        self,
        templates: TemplateCollection
    ) -> float:
        """
        Validate placeholder naming consistency across templates.

        Checks:
        - Same placeholder names used consistently (e.g., {{EntityName}}, not {{Entity}})
        - Consistent casing (PascalCase for types, camelCase for variables)
        - No hard-coded values that should be placeholders

        Returns: Score 0-10
        """

    def _validate_pattern_fidelity(
        self,
        templates: TemplateCollection
    ) -> Tuple[float, List[SpotCheckResult]]:
        """
        Spot-check 5 random templates against source patterns.

        For each file:
        - Compare structure to source
        - Verify dependencies match
        - Check method signatures
        - Validate error handling patterns

        Returns: (score 0-10, list of spot-check results)
        """

    def _validate_documentation(
        self,
        claude_md_path: Path,
        manifest: Dict[str, Any],
        agents: List[Path]
    ) -> float:
        """
        Validate CLAUDE.md completeness.

        Checks:
        - All patterns from manifest documented
        - All agents mentioned
        - Code examples present
        - Architecture overview complete
        - Quality standards specified

        Returns: Score 0-10
        """

    def _validate_agents(
        self,
        agents: List[Path],
        claude_md_path: Path
    ) -> float:
        """
        Validate agent files and references.

        Checks:
        - All agents have valid frontmatter
        - All agents mentioned in CLAUDE.md
        - No broken agent references in documentation

        Returns: Score 0-10
        """

    def _validate_manifest(
        self,
        manifest: Dict[str, Any],
        templates: TemplateCollection
    ) -> float:
        """
        Validate manifest accuracy.

        Checks:
        - All placeholders in manifest are used in templates
        - All patterns in manifest have corresponding templates
        - Technology stack matches template content
        - Version information present

        Returns: Score 0-10
        """

    def _calculate_overall_score(
        self,
        placeholder_score: float,
        fidelity_score: float,
        doc_score: float,
        agent_score: float,
        manifest_score: float
    ) -> float:
        """
        Calculate weighted overall score.

        Weights:
        - Placeholder Consistency: 10%
        - Pattern Fidelity: 10%
        - Documentation: 10%
        - Agent Validation: 10%
        - Manifest Accuracy: 10%
        - Phase 5.5 Score: 50% (from completeness validation)

        Returns: Score 0-10
        """
```

#### 2. Report Generator
**File**: `installer/global/lib/template_validation/report_generator.py`

**Purpose**: Generate markdown validation reports

**Class**:
```python
class ValidationReportGenerator:
    """Generate markdown validation reports"""

    def generate_report(
        self,
        report: ExtendedValidationReport,
        template_name: str,
        output_path: Path
    ) -> Path:
        """
        Generate validation report as markdown.

        Returns: Path to generated report
        """

        content = self._build_report_content(report, template_name)
        report_path = output_path / "validation-report.md"
        report_path.write_text(content)

        return report_path

    def _build_report_content(
        self,
        report: ExtendedValidationReport,
        template_name: str
    ) -> str:
        """Build markdown report content"""

        return f"""# Template Validation Report

**Template**: {template_name}
**Generated**: {datetime.now().isoformat()}
**Overall Score**: {report.overall_score:.1f}/10 ({report.get_grade()})

## Executive Summary

{self._generate_summary(report)}

## Quality Scores

| Category | Score | Status |
|----------|-------|--------|
| CRUD Completeness | {report.completeness_score:.1f}/10 | {self._status_icon(report.completeness_score)} |
| Layer Symmetry | {report.symmetry_score:.1f}/10 | {self._status_icon(report.symmetry_score)} |
| Placeholder Consistency | {report.placeholder_consistency_score:.1f}/10 | {self._status_icon(report.placeholder_consistency_score)} |
| Pattern Fidelity | {report.pattern_fidelity_score:.1f}/10 | {self._status_icon(report.pattern_fidelity_score)} |
| Documentation | {report.documentation_score:.1f}/10 | {self._status_icon(report.documentation_score)} |
| **Overall** | **{report.overall_score:.1f}/10** | **{self._status_icon(report.overall_score)}** |

## Detailed Findings

{self._generate_detailed_findings(report)}

## Recommendations

{self._generate_recommendations(report)}

## Production Readiness

**Status**: {self._production_readiness_status(report)}

**Threshold**: ≥8/10 for production deployment

{self._generate_blocking_issues(report)}

---

**Report Generated**: {datetime.now().isoformat()}
**Validation Duration**: {report.duration}
**Template Location**: {report.template_path}
"""
```

### Testing Requirements

#### Unit Tests
**File**: `tests/unit/test_extended_validator.py`

**Test Cases**:
```python
def test_placeholder_consistency_validation():
    """Test placeholder consistency checking"""

def test_pattern_fidelity_spot_checks():
    """Test pattern fidelity spot-checking"""

def test_documentation_completeness():
    """Test documentation validation"""

def test_agent_validation():
    """Test agent file validation"""

def test_manifest_accuracy():
    """Test manifest accuracy checking"""

def test_overall_score_calculation():
    """Test weighted score calculation"""

def test_grade_assignment():
    """Test letter grade assignment (A+, A, A-, etc.)"""
```

#### Integration Tests
**File**: `tests/integration/test_validate_flag.py`

**Test Cases**:
```python
def test_validate_flag_with_template_create():
    """Test --validate flag integration with /template-create"""

def test_report_generation():
    """Test validation report file generation"""

def test_exit_codes():
    """Test exit codes based on quality scores"""

def test_validate_with_dry_run():
    """Test --validate with --dry-run flag"""

def test_validate_with_skip_validation():
    """Test that --validate is ignored if --skip-validation set"""
```

---

## Implementation Steps

### Step 1: Add Flag to Orchestrator (1 hour)
1. Add `validate: bool` to `OrchestrationConfig`
2. Update command-line argument parsing
3. Add flag documentation to `template-create.md`

### Step 2: Create Extended Validator (3 hours)
1. Create `extended_validator.py` with `ExtendedValidator` class
2. Implement placeholder consistency validation
3. Implement pattern fidelity spot-checks
4. Implement documentation validation
5. Implement agent validation
6. Implement manifest accuracy validation
7. Implement overall score calculation

### Step 3: Create Report Generator (1.5 hours)
1. Create `report_generator.py` with `ValidationReportGenerator` class
2. Implement markdown report template
3. Implement section generators
4. Implement formatting utilities

### Step 4: Integrate into Orchestrator (1 hour)
1. Add `_phase5_7_extended_validation()` method
2. Call after Phase 5.5 if `--validate` flag set
3. Generate and save report
4. Set exit code based on score

### Step 5: Testing (2 hours)
1. Write unit tests for `ExtendedValidator`
2. Write unit tests for `ValidationReportGenerator`
3. Write integration tests for `--validate` flag
4. Test with existing templates (maui-appshell, etc.)

### Step 6: Documentation (0.5 hours)
1. Update `template-create.md` with `--validate` flag
2. Add example usage
3. Document report structure
4. Update related guides

---

## Acceptance Criteria

### Functional Requirements
- [ ] `--validate` flag works with `/template-create`
- [ ] Extended validation runs after Phase 5.5
- [ ] Validation report generated as markdown
- [ ] Report includes all required sections
- [ ] Exit codes correct (0/1/2 based on score)
- [ ] Works with `--dry-run` flag
- [ ] Ignored if `--skip-validation` set
- [ ] No performance degradation when flag not used

### Quality Requirements
- [ ] Test coverage ≥80%
- [ ] All tests passing
- [ ] Report is human-readable and actionable
- [ ] Validation completes in <5 minutes
- [ ] No false positive validation errors

### Documentation Requirements
- [ ] `template-create.md` updated
- [ ] Example usage provided
- [ ] Report structure documented
- [ ] Integration guide updated

---

## Exit Codes

```bash
# Score ≥8.0 (Production ready)
/template-create --validate
echo $?  # 0

# Score 6.0-7.9 (Needs improvement)
/template-create --validate
echo $?  # 1

# Score <6.0 (Not ready)
/template-create --validate
echo $?  # 2
```

---

## Example Usage

```bash
# Basic usage
/template-create --validate
# → Runs extended validation
# → Generates validation-report.md
# → Exit code 0 if ≥8/10

# With dry run
/template-create --dry-run --validate
# → Analyze and validate without saving
# → Preview quality before committing

# Combined with other flags
/template-create --validate --save-analysis --verbose
# → Extended validation + detailed logs + analysis JSON
```

---

## Dependencies

**Required**:
- TASK-040: Phase 5.5 Completeness Validation (Completed)
- Python 3.8+
- Existing template creation infrastructure

**Optional**:
- None

---

## Risks and Mitigation

### Risk 1: Performance Impact
**Mitigation**: Only run extended checks if `--validate` flag set

### Risk 2: False Positives
**Mitigation**: Conservative validation thresholds, clear documentation of edge cases

### Risk 3: Report Quality
**Mitigation**: Use templates from appendix in validation strategy doc, iterate based on feedback

---

## Success Metrics

**Quantitative**:
- Validation completes in <5 minutes
- Test coverage ≥80%
- Exit codes 100% accurate
- No performance impact when flag not used

**Qualitative**:
- Reports are actionable
- Users understand findings
- Recommendations improve quality
- No confusion about when to use flag

---

## Related Documents

- [Template Validation Strategy](../../docs/research/template-validation-strategy.md) - Overall strategy
- [Template Quality Validation Guide](../../docs/guides/template-quality-validation.md) - Manual validation procedures
- [Template Completeness Validation Checklist](../../docs/checklists/template-completeness-validation.md) - CRUD validation checklist
- [TASK-040](../../tasks/completed/2025-11/TASK-040-implement-completeness-validation-layer.md) - Phase 5.5 implementation

---

## Next Steps

After TASK-043:
- **TASK-044**: Phase 2 - Create `/template-validate` command (comprehensive audit)
- **TASK-045**: Phase 3 - AI-Assisted Validation

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-08
**Phase**: 1 of 3 (Template Validation Strategy)
