# TASK-044: Create Template Validate Command (Phase 2)

**Created**: 2025-01-08
**Priority**: Low
**Type**: Feature
**Parent**: Template Validation Strategy
**Status**: Backlog
**Complexity**: 6/10 (Medium)
**Estimated Effort**: 3-5 days (24-40 hours)
**Dependencies**: TASK-043 (Phase 1), TASK-068 (Template Location Refactor)

---

## Problem Statement

Create `/template-validate` command for comprehensive interactive template auditing using the 16-section checklist from [template-analysis-task.md](../../docs/testing/template-analysis-task.md). This enables systematic validation for production templates and development testing.

**Goal**: Provide Level 3 (Comprehensive) validation from the [Template Validation Strategy](../../docs/research/template-validation-strategy.md) - full manual audit with AI assistance.

---

## Context

**Related Documents**:
- [Template Validation Strategy](../../docs/research/template-validation-strategy.md)
- [Template Analysis Task](../../docs/testing/template-analysis-task.md) - 16-section checklist
- [Template Quality Validation Guide](../../docs/guides/template-quality-validation.md)

**Current State** (After TASK-043):
- Level 1 validation: Phase 5.5 automatic validation (TASK-040)
- Level 2 validation: `--validate` flag with extended checks (TASK-043)
- No comprehensive manual audit tool

**Desired State**:
- `/template-validate` command for deep auditing
- Interactive section-by-section walkthrough
- Selective section execution
- Session save/resume capability
- Inline issue fixes
- Comprehensive audit reports

---

## Objectives

### Primary Objective
Create interactive `/template-validate` command that guides users through comprehensive 16-section template audit.

### Success Criteria
- [x] `/template-validate <path>` command works
- [x] All 16 sections from template-analysis-task.md implemented
- [x] Interactive section navigation
- [x] Section selection: `--sections 1,4,7` or `--sections 1-7`
- [x] Session save/resume: `--resume <session-id>`
- [x] Inline fixes for detected issues
- [x] Comprehensive audit report generation
- [x] Scoring rubric (0-10 per section, overall grade)
- [x] Decision framework (APPROVE/NEEDS_IMPROVEMENT/REJECT)
- [x] Documentation complete
- [x] Tests passing (≥75% coverage)

---

## 16-Section Audit Framework

### Sections 1-7: Technical Validation
1. **Manifest Analysis** - Template metadata, placeholders, quality scores
2. **Settings Analysis** - Naming conventions, layer mappings, code style
3. **Documentation Analysis** - CLAUDE.md architecture, patterns, examples
4. **Template Files Analysis** - File selection quality, placeholder integration
5. **AI Agents Analysis** - Agent relevance, prompt quality, capabilities
6. **README Review** - Content completeness, usability, accuracy
7. **Global Template Validation** - Installation test, discovery, structure

### Sections 8-13: Quality Assessment
8. **Comparison with Source** - Pattern coverage, false positives/negatives
9. **Production Readiness** - Developer experience, pattern enforcement, learning curve
10. **Scoring Rubric** - Overall quality score, grade assignment
11. **Detailed Findings** - Strengths, weaknesses, critical issues
12. **Validation Testing** - Placeholder replacement, agent integration, cross-references
13. **Market Comparison** - Comparison with other templates, market potential

### Sections 14-16: Decision Framework
14. **Final Recommendations** - Release decision, pre-release checklist
15. **Testing Recommendations** - Next steps for testing, generalization assessment
16. **Summary Report** - Executive summary, key metrics, sign-off

---

## Implementation Scope

### Files to Create

#### 1. Command Specification
**File**: `installer/global/commands/template-validate.md`

**Content**:
```markdown
# Template Validate - Comprehensive Template Audit

Performs interactive comprehensive audit of template packages using 16-section validation framework.

## Purpose

Systematic quality validation for:
- Production templates (global library deployment)
- Critical deployments
- Development testing of template-create feature
- Troubleshooting template quality issues

## Usage

```bash
# Full audit (all sections)
/template-validate <template-path>

# Validate personal template (in global location)
/template-validate ~/.agentecflow/templates/my-template

# Validate repository template (for distribution)
/template-validate installer/global/templates/react-typescript

# Specific sections only
/template-validate <template-path> --sections 1,4,7,12

# Section ranges
/template-validate <template-path> --sections 1-7

# Resume previous audit
/template-validate <template-path> --resume <session-id>

# Non-interactive mode (batch processing)
/template-validate <template-path> --non-interactive
```

**Note**: TASK-068 introduces two template locations:
- `~/.agentecflow/templates/` - Personal templates (default, immediate use)
- `installer/global/templates/` - Repository templates (team/public distribution)

The `/template-validate` command works with templates in either location.

## 16-Section Framework

[Details of all 16 sections]

## Reports Generated

- `audit-report.md` - Comprehensive audit report
- `audit-session.json` - Session data (for resume)
- `audit-fixes.log` - Log of inline fixes applied
```

#### 2. Interactive Orchestrator
**File**: `installer/global/commands/lib/template_validate_interactive.py`

**Purpose**: Main orchestrator for interactive validation

**Class**:
```python
class TemplateValidateOrchestrator:
    """
    Interactive orchestrator for comprehensive template validation.

    Guides user through 16-section audit framework with:
    - Section navigation
    - Progress tracking
    - Inline fixes
    - Session save/resume
    - Report generation
    """

    def __init__(self, config: ValidateConfig):
        self.config = config
        self.session = AuditSession()
        self.auditor = ComprehensiveAuditor()

    def run(self) -> AuditResult:
        """Execute interactive validation"""

        # Load or create session
        if self.config.resume:
            self.session = self._load_session(self.config.resume)
        else:
            self.session = self._create_session()

        # Interactive section selection
        sections = self._select_sections()

        # Execute each section
        for section_num in sections:
            result = self._execute_section(section_num)
            self.session.add_result(section_num, result)

            # Offer inline fixes
            if result.has_issues():
                self._offer_fixes(result)

            # Save progress
            self._save_session()

            # Continue?
            if not self._should_continue():
                break

        # Generate report
        report = self._generate_report()

        return AuditResult(
            session=self.session,
            report=report,
            recommendation=self._make_recommendation()
        )

    def _select_sections(self) -> List[int]:
        """Interactive section selection"""

        if self.config.sections:
            # Command-line specified
            return self._parse_section_spec(self.config.sections)

        # Interactive menu
        return self._interactive_section_menu()

    def _execute_section(self, section_num: int) -> SectionResult:
        """Execute a single audit section"""

        section = self.auditor.get_section(section_num)

        print(f"\n---\nSection {section_num}: {section.title}\n---\n")

        result = section.execute(
            template_path=self.config.template_path,
            interactive=self.config.interactive
        )

        return result

    def _offer_fixes(self, result: SectionResult):
        """Offer inline fixes for detected issues"""

        for issue in result.fixable_issues():
            if self._prompt_fix(issue):
                fix_result = issue.apply_fix()
                self.session.log_fix(fix_result)
```

#### 3. Comprehensive Auditor
**File**: `installer/global/lib/template_validation/comprehensive_auditor.py`

**Purpose**: Implement 16-section audit framework

**Classes**:
```python
class ComprehensiveAuditor:
    """16-section comprehensive audit implementation"""

    def __init__(self):
        self.sections = self._initialize_sections()

    def _initialize_sections(self) -> Dict[int, AuditSection]:
        """Initialize all 16 audit sections"""
        return {
            1: ManifestAnalysisSection(),
            2: SettingsAnalysisSection(),
            3: DocumentationAnalysisSection(),
            4: TemplateFilesAnalysisSection(),
            5: AIAgentsAnalysisSection(),
            6: ReadmeReviewSection(),
            7: GlobalTemplateValidationSection(),
            8: ComparisonWithSourceSection(),
            9: ProductionReadinessSection(),
            10: ScoringRubricSection(),
            11: DetailedFindingsSection(),
            12: ValidationTestingSection(),
            13: MarketComparisonSection(),
            14: FinalRecommendationsSection(),
            15: TestingRecommendationsSection(),
            16: SummaryReportSection(),
        }

    def get_section(self, section_num: int) -> AuditSection:
        """Get audit section by number"""
        return self.sections[section_num]


class AuditSection(ABC):
    """Base class for audit sections"""

    @property
    @abstractmethod
    def title(self) -> str:
        """Section title"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Section description"""

    @abstractmethod
    def execute(
        self,
        template_path: Path,
        interactive: bool
    ) -> SectionResult:
        """Execute section audit"""


class ManifestAnalysisSection(AuditSection):
    """
    Section 1: Manifest Analysis

    Validates:
    - Template metadata (ID, version, author)
    - Technology stack detection
    - Architectural metadata
    - Intelligent placeholders
    - Quality scores
    """

    title = "Manifest Analysis"
    description = "Validate template metadata, placeholders, and quality scores"

    def execute(
        self,
        template_path: Path,
        interactive: bool
    ) -> SectionResult:
        """Execute manifest analysis"""

        manifest = self._load_manifest(template_path)

        # 1.1 Metadata Review
        metadata_score = self._validate_metadata(manifest)

        # 1.2 Technology Stack Validation
        tech_score = self._validate_technology_stack(manifest)

        # 1.3 Architectural Metadata
        arch_score = self._validate_architecture_metadata(manifest)

        # 1.4 Intelligent Placeholders
        placeholder_score = self._validate_placeholders(manifest)

        # 1.5 Quality Scores
        quality_score = self._validate_quality_scores(manifest)

        overall_score = self._calculate_section_score([
            metadata_score,
            tech_score,
            arch_score,
            placeholder_score,
            quality_score
        ])

        return SectionResult(
            section_num=1,
            score=overall_score,
            findings=self.findings,
            issues=self.issues,
            recommendations=self.recommendations
        )


# ... implement all 16 sections similarly ...
```

#### 4. Session Management
**File**: `installer/global/lib/template_validation/audit_session.py`

**Purpose**: Manage audit sessions (save/resume)

**Class**:
```python
@dataclass
class AuditSession:
    """Audit session state"""
    session_id: str
    template_path: Path
    created_at: datetime
    updated_at: datetime
    sections_completed: List[int]
    section_results: Dict[int, SectionResult]
    fixes_applied: List[FixLog]

    def save(self, path: Path):
        """Save session to JSON"""
        session_data = {
            'session_id': self.session_id,
            'template_path': str(self.template_path),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'sections_completed': self.sections_completed,
            'section_results': {
                k: v.to_dict()
                for k, v in self.section_results.items()
            },
            'fixes_applied': [f.to_dict() for f in self.fixes_applied]
        }

        path.write_text(json.dumps(session_data, indent=2))

    @staticmethod
    def load(path: Path) -> 'AuditSession':
        """Load session from JSON"""
        # ... implementation ...
```

#### 5. Audit Report Generator
**File**: `installer/global/lib/template_validation/audit_report_generator.py`

**Purpose**: Generate comprehensive audit reports

**Class**:
```python
class AuditReportGenerator:
    """Generate comprehensive audit reports"""

    def generate_report(
        self,
        session: AuditSession,
        template_name: str,
        output_path: Path
    ) -> Path:
        """Generate full audit report"""

        content = self._build_comprehensive_report(session, template_name)

        report_path = output_path / "audit-report.md"
        report_path.write_text(content)

        return report_path

    def _build_comprehensive_report(
        self,
        session: AuditSession,
        template_name: str
    ) -> str:
        """Build comprehensive audit report content"""

        return f"""# Template Comprehensive Audit Report

**Template**: {template_name}
**Audit Date**: {session.created_at.date()}
**Session ID**: {session.session_id}
**Sections Completed**: {len(session.sections_completed)}/16
**Overall Grade**: {self._calculate_grade(session)} ({self._calculate_overall_score(session):.1f}/10)

## Executive Summary

{self._generate_executive_summary(session)}

**Recommendation**: {self._generate_recommendation(session)}

## Section Scores

| Section | Title | Score | Status |
|---------|-------|-------|--------|
{self._generate_section_scores_table(session)}

## Detailed Section Results

{self._generate_detailed_sections(session)}

## Overall Quality Assessment

### Strengths (Top 5)
{self._generate_strengths(session)}

### Weaknesses (Top 5)
{self._generate_weaknesses(session)}

### Critical Issues
{self._generate_critical_issues(session)}

## Production Readiness Decision

**Final Score**: {self._calculate_overall_score(session):.1f}/10
**Grade**: {self._calculate_grade(session)}
**Recommendation**: {self._generate_recommendation(session)}

**Reasoning**:
{self._generate_recommendation_reasoning(session)}

## Pre-Release Checklist

{self._generate_prerelease_checklist(session)}

## Next Steps

{self._generate_next_steps(session)}

---

**Audit Duration**: {self._calculate_duration(session)}
**Audit Session ID**: {session.session_id}
**Fixes Applied**: {len(session.fixes_applied)}
"""
```

### Testing Requirements

#### Unit Tests
**File**: `tests/unit/test_comprehensive_auditor.py`

**Test Cases**:
- Test each of 16 sections independently
- Test section scoring
- Test issue detection
- Test recommendations generation

#### Integration Tests
**File**: `tests/integration/test_template_validate_command.py`

**Test Cases**:
```python
def test_full_audit_all_sections():
    """Test complete audit with all 16 sections"""

def test_section_selection():
    """Test --sections flag (1,4,7 and 1-7 formats)"""

def test_session_save_resume():
    """Test saving and resuming audit sessions"""

def test_inline_fixes():
    """Test inline fix functionality"""

def test_report_generation():
    """Test comprehensive report generation"""

def test_non_interactive_mode():
    """Test batch processing mode"""
```

---

## Implementation Steps

### Phase 1: Core Infrastructure (1 day)
1. Create command specification
2. Create interactive orchestrator
3. Create session management
4. Implement save/resume functionality

### Phase 2: Section Framework (2 days)
1. Create base `AuditSection` class
2. Implement Sections 1-7 (Technical Validation)
3. Implement Sections 8-13 (Quality Assessment)
4. Implement Sections 14-16 (Decision Framework)

### Phase 3: Interactive UI (1 day)
1. Section selection menu
2. Progress indicators
3. Inline fix prompts
4. Navigation controls

### Phase 4: Report Generation (0.5 day)
1. Create report generator
2. Implement comprehensive report template
3. Add section-specific formatters

### Phase 5: Testing (1 day)
1. Unit tests for all sections
2. Integration tests for command
3. End-to-end audit testing

### Phase 6: Documentation (0.5 day)
1. Create template-validate.md
2. Update validation strategy doc
3. Add usage examples

---

## Acceptance Criteria

### Functional Requirements
- [ ] `/template-validate` command works
- [ ] All 16 sections implemented
- [ ] Section selection works (--sections)
- [ ] Session save/resume works
- [ ] Inline fixes functional
- [ ] Reports generated correctly
- [ ] Non-interactive mode works
- [ ] Scoring rubric accurate
- [ ] Decision framework clear

### Quality Requirements
- [ ] Test coverage ≥75%
- [ ] All tests passing
- [ ] Interactive UI smooth
- [ ] Reports comprehensive and actionable
- [ ] Audit completes in user-driven time
- [ ] No data loss on resume

### Documentation Requirements
- [ ] Command specification complete
- [ ] 16-section framework documented
- [ ] Usage examples provided
- [ ] Report structure explained

---

## Example Usage

```bash
# Full comprehensive audit
/template-validate ./installer/global/templates/ardalis-clean-architecture

# Output:
# ============================================================
#   Template Comprehensive Audit
# ============================================================
#
# Template: ardalis-clean-architecture
# Location: ./installer/global/templates/ardalis-clean-architecture/
#
# Audit Sections:
#   [1-7]   Technical Validation
#   [8-13]  Quality Assessment
#   [14-16] Decision Framework
#
# Run all sections? [Y/n/select]: select
#
# Enter sections (e.g., 1,4,7 or 1-7): 1-7,12
#
# Starting audit...
# [Interactive walkthrough of each section]
# ...
# Audit Complete!
#
# Overall Score: 9.2/10 (Excellent)
# Recommendation: APPROVE for production
#
# Report: ./installer/global/templates/ardalis-clean-architecture/audit-report.md

# Specific sections only
/template-validate ./templates/my-template --sections 1,4,7,12

# Resume previous audit
/template-validate ./templates/my-template --resume session-abc123

# Non-interactive batch mode
/template-validate ./templates/my-template --non-interactive --sections 1-13
```

---

## Dependencies

**Required**:
- TASK-043: Phase 1 - Extended Validation Flag (must be completed first)
- Python 3.8+
- Existing template validation infrastructure

**Optional**:
- TASK-045: AI-Assisted Validation (can enhance sections 8, 11, 12, 13)

---

## Risks and Mitigation

### Risk 1: Complexity
**Mitigation**: Modular section design, clear abstractions, comprehensive testing

### Risk 2: User Experience
**Mitigation**: Iterative UI refinement, user testing, clear progress indicators

### Risk 3: Session Corruption
**Mitigation**: Robust JSON serialization, backup on save, validation on load

---

## Success Metrics

**Quantitative**:
- All 16 sections implemented
- Test coverage ≥75%
- Session save/resume 100% reliable
- Report generation <30 seconds

**Qualitative**:
- Audit process feels systematic
- Reports are comprehensive
- Decision framework is clear
- Developers prefer this over manual checklists

---

## Future Enhancements (TASK-045)

- AI-assisted analysis for sections 8, 11, 12, 13
- Automatic source comparison
- Pattern detection improvements
- Market comparison database

---

## Related Documents

- [Template Validation Strategy](../../docs/research/template-validation-strategy.md) - Overall strategy (Phase 2)
- [Template Analysis Task](../../docs/testing/template-analysis-task.md) - 16-section source
- [TASK-043](./TASK-043-implement-extended-validation-flag.md) - Phase 1 (prerequisite)
- [TASK-045](./TASK-045-implement-ai-assisted-validation.md) - Phase 3 (enhancement)

---

**Document Status**: Ready for Implementation (after TASK-043)
**Created**: 2025-01-08
**Phase**: 2 of 3 (Template Validation Strategy)
