# TASK-040 Implementation Plan

## Task: Implement Phase 1 - Completeness Validation Layer

**Complexity**: 6/10 (Medium)
**Estimated Duration**: 18-24 hours
**Stack**: Python
**Mode**: Standard (Implementation + Tests Together)

---

## Overview

Implement the Completeness Validation Layer (Phase 5.5) to detect and auto-fix incomplete CRUD patterns in generated templates. This will improve the False Negative score from 4.3/10 to ≥8.0/10 by catching missing templates before package assembly.

---

## Architecture

### Component Structure

```
installer/global/lib/template_generator/
├── completeness_validator.py    (NEW - 300-400 lines)
├── pattern_matcher.py            (NEW - 200-300 lines)
└── models.py                     (MODIFY - add new models)

installer/global/commands/lib/
└── template_create_orchestrator.py (MODIFY - add Phase 5.5)

tests/
├── unit/
│   ├── test_completeness_validator.py (NEW - 500+ lines)
│   └── test_pattern_matcher.py         (NEW - 200+ lines)
└── integration/
    └── test_template_create_completeness.py (NEW - 300+ lines)
```

### Design Patterns

1. **Strategy Pattern**: Different validation strategies (CRUD, Layer Symmetry, Pattern Consistency)
2. **Builder Pattern**: ValidationReport construction
3. **Template Method**: Base validation flow with customizable checks
4. **Factory Pattern**: Auto-generation of missing templates

---

## Implementation Steps

### Step 1: Create Data Models (2-3 hours)

**File**: `installer/global/lib/template_generator/models.py` (MODIFY)

**New Models to Add**:

```python
@dataclass
class CompletenessIssue:
    """Represents a completeness validation issue"""
    severity: str  # 'critical', 'high', 'medium', 'low'
    type: str  # 'incomplete_crud', 'layer_asymmetry', 'pattern_inconsistency'
    message: str
    entity: Optional[str] = None
    operation: Optional[str] = None
    layer: Optional[str] = None
    missing_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

@dataclass
class TemplateRecommendation:
    """Recommendation for missing template"""
    file_path: str
    reason: str
    can_auto_generate: bool
    reference_template: Optional[str] = None
    estimated_confidence: float = 0.0  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

@dataclass
class ValidationReport:
    """Complete validation report with issues and recommendations"""
    is_complete: bool
    issues: List[CompletenessIssue]
    recommended_templates: List[TemplateRecommendation]
    false_negative_score: float  # 0-10
    templates_generated: int
    templates_expected: int
    validation_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'is_complete': self.is_complete,
            'issues': [issue.to_dict() for issue in self.issues],
            'recommended_templates': [rec.to_dict() for rec in self.recommended_templates],
            'false_negative_score': self.false_negative_score,
            'templates_generated': self.templates_generated,
            'templates_expected': self.templates_expected,
            'validation_timestamp': self.validation_timestamp
        }
```

**Tests**: `tests/unit/test_models.py` - Test model creation and serialization

---

### Step 2: Create Pattern Matcher (4-5 hours)

**File**: `installer/global/lib/template_generator/pattern_matcher.py` (NEW)

**Classes**:

1. **CRUDPatternMatcher**: Identify CRUD operations from file paths/names
   - `identify_crud_operation(template: CodeTemplate) -> Optional[str]`
   - `identify_layer(template: CodeTemplate) -> Optional[str]`
   - `identify_entity(template: CodeTemplate) -> Optional[str]`

2. **OperationExtractor**: Group templates by operation and entity
   - `extract_operations_by_layer(templates: TemplateCollection) -> Dict[str, Set[str]]`
   - `group_by_entity(templates: TemplateCollection) -> Dict[str, Dict[str, List[CodeTemplate]]]`

**Pattern Matching Rules**:

```python
# CRUD Operation Detection (case-insensitive)
CRUD_PATTERNS = {
    'Create': ['Create', 'Add', 'Insert', 'New'],
    'Read': ['Get', 'Query', 'List', 'Find', 'Fetch', 'Read'],
    'Update': ['Update', 'Edit', 'Modify', 'Put', 'Patch'],
    'Delete': ['Delete', 'Remove', 'Destroy']
}

# Layer Detection
LAYER_PATTERNS = {
    'Domain': ['/Core/', '/Domain/', 'Domain.'],
    'UseCases': ['/UseCases/', '/Application/', 'UseCases.', 'Application.'],
    'Web': ['/Web/', '/Api/', '/Endpoints/', 'Web.', 'Api.', 'Endpoints.'],
    'Infrastructure': ['/Infrastructure/', '/Persistence/', 'Infrastructure.', 'Persistence.']
}
```

**Tests**: `tests/unit/test_pattern_matcher.py`
- Test operation detection for various naming patterns
- Test layer detection for different architectures
- Test entity extraction
- Test operation grouping

---

### Step 3: Create Completeness Validator (6-8 hours)

**File**: `installer/global/lib/template_generator/completeness_validator.py` (NEW)

**Main Class**: `CompletenessValidator`

**Methods**:

1. **validate()**: Main entry point
   ```python
   def validate(
       templates: TemplateCollection,
       analysis: CodebaseAnalysis
   ) -> ValidationReport:
       """
       Validate completeness of template collection.

       Performs three types of validation:
       1. CRUD completeness (all 5 operations present)
       2. Layer symmetry (UseCases ↔ Web)
       3. Pattern consistency (naming, structure)
       """
   ```

2. **_check_crud_completeness()**: Detect incomplete CRUD patterns
   ```python
   def _check_crud_completeness(
       templates: TemplateCollection
   ) -> List[CompletenessIssue]:
       """
       Check if all CRUD operations are present for each entity.

       Expected operations: Create, Read, Update, Delete, List
       """
   ```

3. **_check_layer_symmetry()**: Detect layer mismatches
   ```python
   def _check_layer_symmetry(
       templates: TemplateCollection
   ) -> List[CompletenessIssue]:
       """
       Check if operations exist in both UseCases and Web layers.

       Example issue: UpdateProduct.cs exists in UseCases but not in Web
       """
   ```

4. **_check_pattern_consistency()**: Detect pattern violations
   ```python
   def _check_pattern_consistency(
       templates: TemplateCollection
   ) -> List[CompletenessIssue]:
       """
       Check for naming and structural inconsistencies.

       Examples:
       - Inconsistent naming (GetProduct vs FetchProduct)
       - Missing Request/Response pairs
       - Missing Validator files
       """
   ```

5. **generate_missing_templates()**: Auto-generate missing templates
   ```python
   def generate_missing_templates(
       recommendations: List[TemplateRecommendation],
       existing_templates: TemplateCollection
   ) -> List[CodeTemplate]:
       """
       Auto-generate missing templates by cloning reference templates.

       Strategy:
       1. Find reference template (e.g., Create.cs for Update.cs)
       2. Clone content
       3. Replace operation names
       4. Update HTTP methods/routes
       5. Preserve entity placeholders
       """
   ```

6. **_calculate_false_negative_score()**: Calculate FN score
   ```python
   def _calculate_false_negative_score(
       templates_generated: int,
       templates_expected: int
   ) -> float:
       """
       Calculate False Negative score: (generated / expected) × 10

       Target: ≥8.0/10
       """
       if templates_expected == 0:
           return 10.0
       return (templates_generated / templates_expected) * 10.0
   ```

**Tests**: `tests/unit/test_completeness_validator.py`
- Test incomplete CRUD detection
- Test layer asymmetry detection
- Test pattern consistency checks
- Test auto-generation logic
- Test False Negative score calculation
- Test edge cases (empty collection, single template, etc.)

---

### Step 4: Integrate into Orchestrator (3-4 hours)

**File**: `installer/global/commands/lib/template_create_orchestrator.py` (MODIFY)

**Changes**:

1. **Add Phase 5.5 method**:
   ```python
   def _phase5_5_completeness_validation(
       self,
       templates: TemplateCollection,
       analysis: Any
   ) -> TemplateCollection:
       """
       Phase 5.5: Completeness Validation (NEW).

       Validates template completeness and optionally auto-fixes issues.

       Returns:
           Updated TemplateCollection (possibly with auto-generated templates)
       """
   ```

2. **Add interactive handling**:
   ```python
   def _handle_validation_issues_interactive(
       self,
       validation_report: ValidationReport
   ) -> str:
       """
       Handle validation issues in interactive mode.

       Prompts: [A]uto-fix / [C]ontinue / [Q]uit

       Returns:
           Action: 'auto_fix', 'continue', or 'quit'
       """
   ```

3. **Add non-interactive handling**:
   ```python
   def _handle_validation_issues_noninteractive(
       self,
       validation_report: ValidationReport
   ) -> str:
       """
       Handle validation issues in non-interactive mode.

       Default: auto_fix if possible, fail if not

       Returns:
           Action: 'auto_fix' or 'fail'
       """
   ```

4. **Add report display**:
   ```python
   def _print_validation_report(
       self,
       validation_report: ValidationReport
   ) -> None:
       """
       Display validation report in readable format.

       Shows:
       - False Negative score
       - Issues by severity
       - Recommended actions
       """
   ```

5. **Insert Phase 5.5 into workflow**:
   ```python
   # In run() method, between Phase 5 and Phase 6:

   # Phase 5: Template File Generation
   templates = self._phase5_template_generation(analysis)

   # ===== NEW: Phase 5.5 Completeness Validation =====
   if not self.config.skip_validation:
       templates = self._phase5_5_completeness_validation(
           templates=templates,
           analysis=analysis
       )

   # Phase 6: Agent Recommendation
   agents = self._phase6_agent_recommendation(analysis)
   ```

6. **Add configuration flags**:
   ```python
   @dataclass
   class OrchestrationConfig:
       # ... existing fields ...
       skip_validation: bool = False
       auto_fix_templates: bool = True
       interactive_validation: bool = True
   ```

**Tests**: `tests/integration/test_template_create_completeness.py`
- Test Phase 5.5 executes correctly
- Test interactive mode choices
- Test non-interactive auto-fix
- Test validation on complete templates (no false positives)
- Test integration with full workflow

---

### Step 5: Create Test Fixtures (2-3 hours)

**Test Repositories**:

1. **tests/fixtures/incomplete-crud-repo/**
   - Product entity with only Create and Read operations
   - Missing: Update, Delete, List

2. **tests/fixtures/complete-crud-repo/**
   - Product entity with all CRUD operations
   - Should pass validation with no issues

3. **tests/fixtures/layer-asymmetry-repo/**
   - UseCases has Update operation
   - Web layer missing corresponding endpoint

**Tests**: Use these fixtures in integration tests

---

### Step 6: Documentation (2-3 hours)

**Files to Create**:

1. **docs/specifications/phase-5-5-completeness-validation.md**
   - Phase specification
   - Validation rules
   - Auto-generation strategy
   - Configuration options

2. **docs/guides/validation-report-format.md**
   - ValidationReport structure
   - Issue types and severities
   - False Negative score interpretation

3. **docs/troubleshooting/template-completeness-issues.md**
   - Common validation issues
   - How to fix manually
   - When to use auto-fix vs manual fix
   - How to disable validation

---

## Files to Create/Modify

### New Files (7 files)

1. `installer/global/lib/template_generator/completeness_validator.py` (300-400 lines)
2. `installer/global/lib/template_generator/pattern_matcher.py` (200-300 lines)
3. `tests/unit/test_completeness_validator.py` (500+ lines)
4. `tests/unit/test_pattern_matcher.py` (200+ lines)
5. `tests/integration/test_template_create_completeness.py` (300+ lines)
6. `tests/fixtures/incomplete-crud-repo/` (directory with test files)
7. `tests/fixtures/complete-crud-repo/` (directory with test files)

### Modified Files (2 files)

1. `installer/global/lib/template_generator/models.py` (+100 lines)
2. `installer/global/commands/lib/template_create_orchestrator.py` (+150 lines)

### Documentation Files (3 files)

1. `docs/specifications/phase-5-5-completeness-validation.md`
2. `docs/guides/validation-report-format.md`
3. `docs/troubleshooting/template-completeness-issues.md`

**Total**: 12 files (7 new code, 2 modified, 3 docs)

---

## Testing Strategy

### Unit Tests (≥85% coverage target)

**test_pattern_matcher.py**:
- Test CRUD operation detection (Create, Read, Update, Delete, List)
- Test layer detection (Domain, UseCases, Web, Infrastructure)
- Test entity extraction from file paths
- Test operation grouping by entity
- Test edge cases (ambiguous names, multiple matches)

**test_completeness_validator.py**:
- Test incomplete CRUD detection (missing operations)
- Test layer asymmetry detection (UseCases vs Web mismatch)
- Test pattern consistency checks
- Test auto-generation logic (template cloning)
- Test False Negative score calculation
- Test edge cases (empty collection, single template)

**test_models.py**:
- Test model creation and validation
- Test serialization (to_dict, JSON)
- Test model constraints

### Integration Tests

**test_template_create_completeness.py**:
- Test Phase 5.5 workflow integration
- Test validation on incomplete templates (should detect issues)
- Test validation on complete templates (no false positives)
- Test auto-fix workflow (generates valid templates)
- Test interactive mode user choices
- Test non-interactive mode auto-fix
- Test configuration flags (skip_validation, auto_fix_templates)

### Manual Testing

1. Run on ardalis-clean-architecture (should detect 7 missing files)
2. Verify auto-generated templates compile
3. Test interactive mode prompts
4. Verify False Negative score improves to ≥8.0/10

---

## Dependencies

### External Libraries (already available)
- Python 3.9+
- Pydantic (for models)
- pytest (for testing)
- pytest-cov (for coverage)

### Internal Dependencies
- `installer.global.lib.template_generator.models` (TemplateCollection, CodeTemplate)
- `installer.global.lib.codebase_analyzer.models` (CodebaseAnalysis)
- `installer.global.commands.lib.template_create_orchestrator` (orchestration)

---

## Risk Mitigation

### Risk 1: Auto-generation creates invalid templates
**Mitigation**:
- Conservative auto-generation (only clone similar templates)
- Add validation checks after generation
- Allow user to review before applying
- Fallback to warning if generation fails

### Risk 2: False positives (warns about intentional omissions)
**Mitigation**:
- Add confidence scoring to issues
- Allow "Continue without fixing" option
- Provide skip_validation flag
- Use heuristics to detect intentional patterns

### Risk 3: Performance degradation
**Mitigation**:
- Profile validation logic
- Optimize pattern matching (use regex caching)
- Target <5 seconds for 50 templates
- Skip validation for small template sets (<5 templates)

### Risk 4: Integration breaks existing workflow
**Mitigation**:
- Add skip_validation flag (default: False)
- Comprehensive integration tests
- Backward compatibility tests
- Rollback plan documented

---

## Success Criteria

### Functional
- [ ] Detects incomplete CRUD (missing Update, Delete, etc.)
- [ ] Detects layer asymmetry (UseCases vs Web mismatch)
- [ ] Auto-generates valid templates (compileable, correct placeholders)
- [ ] Interactive mode works (user can choose action)
- [ ] Non-interactive mode works (auto-fixes by default)
- [ ] False Negative score calculation accurate

### Quality
- [ ] Unit test coverage ≥85%
- [ ] All integration tests pass
- [ ] No false positives on complete templates
- [ ] Generated templates compile successfully
- [ ] Validation completes in <5 seconds for 50 templates

### Metrics
- [ ] False Negative score improves from 4.3/10 to ≥8.0/10
- [ ] Detects 7 missing files in ardalis-clean-architecture
- [ ] Auto-generates valid replacements for 7 missing files

---

## Estimated Timeline

| Step | Component | Estimated Hours |
|------|-----------|----------------|
| 1 | Data Models | 2-3 hours |
| 2 | Pattern Matcher | 4-5 hours |
| 3 | Completeness Validator | 6-8 hours |
| 4 | Orchestrator Integration | 3-4 hours |
| 5 | Test Fixtures | 2-3 hours |
| 6 | Documentation | 2-3 hours |
| **Total** | | **19-26 hours** |

**Target**: Complete in 3-4 days (18-24 hours)

---

## Implementation Order

1. **Day 1** (6-8 hours):
   - Create data models
   - Create pattern matcher
   - Write unit tests for pattern matcher

2. **Day 2** (6-8 hours):
   - Create completeness validator
   - Write unit tests for validator
   - Achieve ≥85% coverage

3. **Day 3** (4-6 hours):
   - Integrate into orchestrator
   - Create test fixtures
   - Write integration tests

4. **Day 4** (2-4 hours):
   - Manual testing on ardalis repo
   - Documentation
   - Final verification

---

## Next Steps After TASK-040

1. **TASK-041**: Stratified Sampling (Phase 2)
   - Use validation results to improve sampling
   - Ensure all CRUD operations represented

2. **TASK-042**: Enhanced AI Prompts (Phase 3)
   - Reference validation in prompts
   - Guide AI to generate complete templates

---

## Notes

- Use TDD approach for core validation logic
- Focus on simplicity and clarity over optimization
- Prioritize correctness over performance (but keep <5s target)
- Make validation optional (skip_validation flag)
- Provide clear error messages and actionable recommendations
