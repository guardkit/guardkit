# TASK-020: Template Completeness Improvement - Implementation Plan

**Date**: 2025-11-07
**Status**: Ready for Implementation
**Approach**: Hybrid (Stratified Sampling + Completeness Validation + Enhanced Prompts)
**Estimated Duration**: 8-10 days
**Priority**: High

---

## Executive Summary

This document provides a **detailed implementation plan** for fixing template generation completeness issues identified in TASK-020. The plan adopts a **phased approach** with three distinct stages that can be implemented and tested independently.

**Goal**: Improve False Negative score from 4.3/10 to ≥8/10 (target: 9/10)

---

## Background

**Problem**: Template generation missed 7 Web endpoint templates (Update/Delete operations) while successfully capturing their UseCases handlers.

**Root Cause**: Selective sampling without pattern-aware completeness validation.

**Solution**: Three-phase implementation:
1. Phase 1: Completeness Validation (safety net)
2. Phase 2: Stratified Sampling (proactive prevention)
3. Phase 3: Enhanced Prompts (AI guidance)

---

## Phase 1: Completeness Validation Layer

**Duration**: 3-4 days (18-24 hours)
**Priority**: Critical (MVP)
**Dependencies**: None
**Deliverables**:
- CompletenessValidator component
- Phase 5.5 integration
- Validation reports
- Auto-fix capability

### 1.1 Component Design

#### CompletenessValidator

**File**: `installer/core/lib/template_generator/completeness_validator.py`

**Responsibilities**:
- Validate CRUD operation completeness
- Check layer symmetry (UseCases ↔ Web)
- Detect pattern inconsistencies
- Generate fix recommendations
- Auto-generate missing templates (if possible)

**Class Structure**:
```python
class CompletenessValidator:
    """Validates template collection completeness."""

    def __init__(self):
        self.crud_operations = ['Create', 'Get', 'Update', 'Delete', 'List']
        self.required_layers = ['Core', 'UseCases', 'Web', 'Infrastructure']

    def validate(
        self,
        templates: TemplateCollection,
        analysis: CodebaseAnalysis
    ) -> ValidationReport:
        """Main validation entry point."""
        pass

    def _check_crud_completeness(
        self,
        templates: TemplateCollection
    ) -> List[CompletenessIssue]:
        """Verify all CRUD operations present for each entity."""
        pass

    def _check_layer_symmetry(
        self,
        templates: TemplateCollection
    ) -> List[CompletenessIssue]:
        """Verify operations exist across layers."""
        pass

    def _check_pattern_consistency(
        self,
        templates: TemplateCollection
    ) -> List[CompletenessIssue]:
        """Verify supporting files (validators, DTOs) are complete."""
        pass

    def generate_missing_templates(
        self,
        recommendations: List[TemplateRecommendation],
        existing_templates: TemplateCollection
    ) -> List[CodeTemplate]:
        """Auto-generate missing templates from patterns."""
        pass


@dataclass
class ValidationReport:
    """Validation results."""
    is_complete: bool
    issues: List[CompletenessIssue]
    recommended_templates: List[TemplateRecommendation]
    false_negative_score: float  # 0-10


@dataclass
class CompletenessIssue:
    """Individual completeness issue."""
    severity: str  # 'critical', 'high', 'medium', 'low'
    type: str  # 'incomplete_crud', 'layer_asymmetry', 'pattern_inconsistency'
    message: str
    entity: Optional[str] = None
    operation: Optional[str] = None
    layer: Optional[str] = None
    missing_files: List[str] = field(default_factory=list)


@dataclass
class TemplateRecommendation:
    """Recommendation for missing template."""
    file_path: str
    reason: str
    can_auto_generate: bool
    reference_template: Optional[str] = None
```

#### Pattern Matcher

**File**: `installer/core/lib/template_generator/pattern_matcher.py`

**Purpose**: Extract operations and patterns from template collection

```python
class OperationExtractor:
    """Extract operations from template paths and content."""

    def extract_operations_by_layer(
        self,
        templates: TemplateCollection
    ) -> Dict[str, Set[str]]:
        """
        Returns: {
            'UseCases': {'Create', 'Update', 'Delete', 'Get', 'List'},
            'Web': {'Create', 'Get', 'List'}  # Missing Update/Delete
        }
        """
        pass

    def group_by_entity(
        self,
        templates: TemplateCollection
    ) -> Dict[str, Dict[str, List[CodeTemplate]]]:
        """
        Returns: {
            'Contributor': {
                'Create': [CreateCommand, CreateHandler, CreateEndpoint],
                'Update': [UpdateCommand, UpdateHandler]  # Missing endpoint
            }
        }
        """
        pass


class CRUDPatternMatcher:
    """Match CRUD patterns in templates."""

    def identify_crud_operation(self, template: CodeTemplate) -> Optional[str]:
        """Identify if template is Create, Read, Update, Delete, or List."""
        pass

    def identify_layer(self, template: CodeTemplate) -> Optional[str]:
        """Identify architectural layer from path."""
        pass

    def identify_entity(self, template: CodeTemplate) -> Optional[str]:
        """Extract entity name from template."""
        pass
```

### 1.2 Orchestrator Integration

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

**Modifications**:

```python
class TemplateCreateOrchestrator:

    def run(self) -> OrchestrationResult:
        """Execute complete template creation workflow."""

        # ... existing phases 1-4 ...

        # Phase 5: Template File Generation (renumbered from Phase 6 by TASK-019A)
        templates = self._phase5_template_generation(analysis)
        if not templates:
            self.warnings.append("No template files generated")

        # ===== NEW: Phase 5.5 Completeness Validation =====
        if not self.config.skip_validation:
            validation_result = self._phase5_5_completeness_validation(
                templates=templates,
                analysis=analysis
            )

            if not validation_result.success:
                return self._create_error_result(
                    "Template completeness validation failed"
                )

            # Update templates if auto-fix applied
            if validation_result.templates_added > 0:
                templates = validation_result.updated_templates

        # Phase 6: Agent Recommendation (renumbered from Phase 7 by TASK-019A)
        agents = []
        if not self.config.no_agents:
            agents = self._phase6_agent_recommendation(analysis)

        # Phase 7: CLAUDE.md Generation (renumbered from Phase 5 by TASK-019A)
        # Phase 8: Package Assembly
        # ... continue with remaining phases ...


    def _phase5_5_completeness_validation(
        self,
        templates: TemplateCollection,
        analysis: CodebaseAnalysis
    ) -> PhaseResult:
        """
        Phase 5.5: Completeness Validation

        Validates template completeness and offers to auto-fix gaps.
        """
        self._print_phase_header("Phase 5.5: Completeness Validation")

        from installer.core.lib.template_generator.completeness_validator import (
            CompletenessValidator
        )

        validator = CompletenessValidator()
        report = validator.validate(templates, analysis)

        # Display results
        self._print_validation_report(report)

        if report.is_complete:
            self._print_success_line("All patterns complete")
            return PhaseResult(success=True)

        # Has issues - offer to fix
        if self.config.interactive:
            return self._handle_validation_issues_interactive(
                report,
                templates,
                validator
            )
        else:
            return self._handle_validation_issues_noninteractive(
                report,
                templates,
                validator
            )


    def _handle_validation_issues_interactive(
        self,
        report: ValidationReport,
        templates: TemplateCollection,
        validator: CompletenessValidator
    ) -> PhaseResult:
        """Interactive mode: Ask user what to do."""

        print(f"\n⚠️  Found {len(report.issues)} completeness issues")
        print(f"   False Negative Score: {report.false_negative_score}/10")

        if report.recommended_templates:
            print(f"\n💡 Can auto-generate {len(report.recommended_templates)} missing templates:\n")
            for rec in report.recommended_templates[:5]:  # Show first 5
                print(f"  + {rec.file_path}")
            if len(report.recommended_templates) > 5:
                print(f"  ... and {len(report.recommended_templates) - 5} more")

        choice = input("\nOptions:\n"
                      "  [A] Auto-generate missing templates (recommended)\n"
                      "  [C] Continue without fixes (not recommended)\n"
                      "  [Q] Quit and review issues\n"
                      "Your choice: ").lower()

        if choice == 'a':
            # Auto-generate
            new_templates = validator.generate_missing_templates(
                report.recommended_templates,
                templates
            )
            templates.templates.extend(new_templates)
            self._print_success_line(f"Generated {len(new_templates)} missing templates")

            # Re-validate
            new_report = validator.validate(templates, None)
            self._print_info(f"New False Negative Score: {new_report.false_negative_score}/10")

            return PhaseResult(
                success=True,
                templates_added=len(new_templates),
                updated_templates=templates
            )

        elif choice == 'c':
            self._print_warning("Continuing with incomplete templates")
            return PhaseResult(
                success=True,
                warnings=[f"Incomplete templates (score: {report.false_negative_score}/10)"]
            )

        else:  # 'q' or other
            self._print_error("Template creation cancelled")
            return PhaseResult(
                success=False,
                errors=["User cancelled due to completeness issues"]
            )


    def _print_validation_report(self, report: ValidationReport):
        """Display validation report."""
        print(f"\nCompleteness Score: {report.false_negative_score}/10")

        if report.is_complete:
            print("✅ All validation checks passed")
            return

        # Group issues by severity
        critical = [i for i in report.issues if i.severity == 'critical']
        high = [i for i in report.issues if i.severity == 'high']
        medium = [i for i in report.issues if i.severity == 'medium']

        if critical:
            print(f"\n🚨 Critical Issues ({len(critical)}):")
            for issue in critical:
                print(f"  - {issue.message}")

        if high:
            print(f"\n⚠️  High Priority ({len(high)}):")
            for issue in high[:3]:  # Show first 3
                print(f"  - {issue.message}")
            if len(high) > 3:
                print(f"  ... and {len(high) - 3} more")


@dataclass
class PhaseResult:
    """Result of phase execution."""
    success: bool
    templates_added: int = 0
    updated_templates: Optional[TemplateCollection] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
```

### 1.3 Testing Plan

**Unit Tests** (`tests/unit/test_completeness_validator.py`):

```python
def test_detect_incomplete_crud():
    """Test detection of incomplete CRUD operations."""
    # Given: Templates with Create, Get, List but missing Update/Delete
    templates = create_test_templates([
        'UseCases/Create/CreateEntityHandler',
        'UseCases/Get/GetEntityHandler',
        'UseCases/List/ListEntityHandler',
        'Web/Endpoints/Create',
        'Web/Endpoints/GetById',
        'Web/Endpoints/List'
    ])

    # When: Validate
    validator = CompletenessValidator()
    report = validator.validate(templates, None)

    # Then: Should detect missing Update/Delete
    assert not report.is_complete
    assert len(report.issues) >= 2  # Update and Delete missing
    assert any('Update' in issue.message for issue in report.issues)
    assert any('Delete' in issue.message for issue in report.issues)


def test_detect_layer_asymmetry():
    """Test detection of layer asymmetry."""
    # Given: UseCases has Update, Web does not
    templates = create_test_templates([
        'UseCases/Update/UpdateEntityHandler',
        'Web/Endpoints/Create'  # Missing Update endpoint
    ])

    # When: Validate
    validator = CompletenessValidator()
    report = validator.validate(templates, None)

    # Then: Should detect asymmetry
    assert not report.is_complete
    asymmetry_issues = [i for i in report.issues if i.type == 'layer_asymmetry']
    assert len(asymmetry_issues) > 0
    assert 'Update' in asymmetry_issues[0].message


def test_auto_generate_missing_template():
    """Test auto-generation of missing templates."""
    # Given: Missing Update endpoint
    existing_templates = create_test_templates(['Web/Endpoints/Create'])
    recommendations = [
        TemplateRecommendation(
            file_path='Web/Endpoints/Update.cs.template',
            reason='Complete CRUD',
            can_auto_generate=True,
            reference_template='Web/Endpoints/Create.cs.template'
        )
    ]

    # When: Generate missing
    validator = CompletenessValidator()
    new_templates = validator.generate_missing_templates(
        recommendations,
        existing_templates
    )

    # Then: Should generate Update template
    assert len(new_templates) == 1
    assert 'Update' in new_templates[0].name
    assert '{{EntityName}}' in new_templates[0].content
```

**Integration Tests** (`tests/integration/test_template_create_completeness.py`):

```python
def test_phase_5_5_detects_missing_operations():
    """Test Phase 5.5 detects incompleteness in real workflow."""
    # Given: Run template-create on test repository
    config = OrchestrationConfig(
        codebase_path=Path('tests/fixtures/incomplete-crud-repo'),
        skip_qa=True,
        interactive=False
    )

    # When: Run orchestration
    orchestrator = TemplateCreateOrchestrator(config)
    result = orchestrator.run()

    # Then: Should detect issues and report them
    assert result.success is False
    assert any('incomplete' in err.lower() for err in result.errors)


def test_phase_5_5_auto_fix_completes_templates():
    """Test auto-fix generates missing templates."""
    # Given: Repository with incomplete CRUD
    config = OrchestrationConfig(
        codebase_path=Path('tests/fixtures/incomplete-crud-repo'),
        skip_qa=True,
        interactive=False,
        auto_fix=True  # Enable auto-fix
    )

    # When: Run with auto-fix
    orchestrator = TemplateCreateOrchestrator(config)
    result = orchestrator.run()

    # Then: Should auto-generate and succeed
    assert result.success is True
    assert result.template_count >= 30  # Complete CRUD
```

### 1.4 Acceptance Criteria

- [ ] CompletenessValidator detects 7 missing endpoint templates in ardalis test
- [ ] False Negative score calculation accurate (matches manual count)
- [ ] Auto-generation creates valid templates (compileable, correct placeholders)
- [ ] Interactive mode allows user choice (auto-fix / continue / quit)
- [ ] Non-interactive mode auto-fixes or fails with clear error
- [ ] Unit test coverage ≥85%
- [ ] Integration tests pass on 3 test repositories

### 1.5 Deliverables

**Code**:
- `completeness_validator.py` (300-400 lines)
- `pattern_matcher.py` (200-300 lines)
- Modified `template_create_orchestrator.py` (+150 lines)
- Unit tests (500+ lines)
- Integration tests (300+ lines)

**Documentation**:
- Phase 5.5 specification
- Validation report format
- Troubleshooting guide

---

## Phase 2: Stratified Sampling

**Duration**: 4-5 days (22-28 hours)
**Priority**: High
**Dependencies**: Phase 1 (for validation)
**Deliverables**:
- StratifiedSampler component
- Pattern category detector
- CRUD completeness checker
- Updated AI analyzer

### 2.1 Component Design

#### StratifiedSampler

**File**: `installer/core/lib/codebase_analyzer/stratified_sampler.py`

**Purpose**: Replace random sampling with pattern-aware stratified sampling

```python
class StratifiedSampler:
    """
    Stratified sampling ensures pattern diversity.

    Sampling Strategy:
    1. Discover pattern categories (CRUD, Queries, Validators, etc.)
    2. Sample proportionally from each category
    3. Ensure CRUD completeness for all entities
    4. Fill remaining with quality-ranked samples
    """

    def __init__(self, codebase_path: Path, max_files: int = 20):
        self.codebase_path = codebase_path
        self.max_files = max_files
        self.pattern_detector = PatternCategoryDetector()
        self.crud_checker = CRUDCompletenessChecker()

    def collect_stratified_samples(self) -> List[FileSample]:
        """Main entry point for stratified sampling."""
        # Step 1: Discover all files
        all_files = self._discover_all_files()

        # Step 2: Categorize by pattern
        categorized = self.pattern_detector.categorize_files(all_files)

        # Step 3: Stratified sampling
        samples = self._sample_from_categories(categorized)

        # Step 4: Ensure CRUD completeness
        samples = self.crud_checker.ensure_crud_completeness(samples, all_files)

        # Step 5: Fill remaining slots
        samples = self._fill_remaining_with_quality(samples, all_files)

        return samples[:self.max_files]

    def _sample_from_categories(
        self,
        categorized: Dict[str, List[Path]]
    ) -> List[FileSample]:
        """
        Sample proportionally from each category.

        Allocation:
        - CRUD operations: 40% of slots (8/20)
        - Query patterns: 20% of slots (4/20)
        - Validators/Specs: 15% of slots (3/20)
        - Infrastructure: 15% of slots (3/20)
        - Other: 10% of slots (2/20)
        """
        pass


class PatternCategoryDetector:
    """Detect pattern categories in codebase."""

    def categorize_files(
        self,
        files: List[Path]
    ) -> Dict[str, List[Path]]:
        """
        Returns: {
            'crud_create': [Create.cs, CreateHandler.cs, ...],
            'crud_read': [GetById.cs, List.cs, ...],
            'crud_update': [Update.cs, UpdateHandler.cs, ...],
            'crud_delete': [Delete.cs, DeleteHandler.cs, ...],
            'validators': [CreateValidator.cs, ...],
            'specifications': [EntityByIdSpec.cs, ...],
            'repositories': [IEntityRepository.cs, ...],
            'infrastructure': [EntityConfiguration.cs, ...],
            'other': [...]
        }
        """
        pass

    def detect_pattern_from_path(self, file_path: Path) -> str:
        """Detect pattern category from file path and name."""
        # Check directory structure
        # Check file name patterns
        # Check file content (if needed)
        pass


class CRUDCompletenessChecker:
    """Ensure CRUD completeness in samples."""

    def ensure_crud_completeness(
        self,
        samples: List[FileSample],
        all_files: List[Path]
    ) -> List[FileSample]:
        """
        Add files to ensure CRUD completeness.

        Rule: If any CRUD operation exists for an entity,
              ALL CRUD operations must be sampled.
        """
        # 1. Identify entities in samples
        entities = self._extract_entities(samples)

        # 2. For each entity, check CRUD completeness
        for entity in entities:
            operations = self._get_operations_for_entity(samples, entity)
            missing = {'Create', 'Read', 'Update', 'Delete', 'List'} - operations

            # 3. Add missing operations
            for op in missing:
                file = self._find_operation_file(all_files, entity, op)
                if file:
                    samples.append(FileSample.from_path(file))

        return samples
```

### 2.2 Integration into AI Analyzer

**File**: `installer/core/lib/codebase_analyzer/ai_analyzer.py`

**Changes**:

```python
class CodebaseAnalyzer:
    def __init__(
        self,
        agent_invoker: Optional[ArchitecturalReviewerInvoker] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_parser: Optional[ResponseParser] = None,
        serializer: Optional[AnalysisSerializer] = None,
        max_files: int = 20,  # CHANGED: Increased from 10
        use_agent: bool = True,
        use_stratified_sampling: bool = True  # NEW
    ):
        """Initialize with stratified sampling option."""
        self.max_files = max_files
        self.use_stratified_sampling = use_stratified_sampling
        # ... rest of init ...

    def analyze_codebase(
        self,
        codebase_path: str | Path,
        template_context: Optional[Dict[str, str]] = None,
        save_results: bool = False,
        output_path: Optional[Path] = None
    ) -> CodebaseAnalysis:
        """Analyze codebase with stratified sampling."""
        codebase_path = Path(codebase_path)

        logger.info(f"Analyzing codebase: {codebase_path}")

        # Step 1: Collect file samples (NEW: Stratified)
        logger.debug("Collecting file samples...")

        if self.use_stratified_sampling:
            from installer.core.lib.codebase_analyzer.stratified_sampler import (
                StratifiedSampler
            )
            sampler = StratifiedSampler(codebase_path, max_files=self.max_files)
            file_samples = sampler.collect_stratified_samples()
            logger.info(f"Collected {len(file_samples)} stratified samples")
        else:
            # Fallback to original sampling
            file_collector = FileCollector(codebase_path, max_files=self.max_files)
            file_samples = file_collector.collect_samples()
            logger.info(f"Collected {len(file_samples)} file samples")

        # ... rest of analysis ...
```

### 2.3 Testing Plan

**Unit Tests**:

```python
def test_stratified_sampling_covers_all_crud():
    """Stratified sampling includes all CRUD operations."""
    # Given: Repository with complete CRUD
    sampler = StratifiedSampler(
        codebase_path=Path('tests/fixtures/complete-crud-repo'),
        max_files=20
    )

    # When: Sample
    samples = sampler.collect_stratified_samples()

    # Then: Should include all CRUD operations
    operations = {s.operation for s in samples if s.operation}
    assert 'Create' in operations
    assert 'Update' in operations
    assert 'Delete' in operations
    assert 'Get' in operations or 'GetById' in operations
    assert 'List' in operations


def test_crud_completeness_checker_adds_missing():
    """CRUD completeness checker adds missing operations."""
    # Given: Samples with Create but missing Update/Delete
    samples = [
        FileSample(operation='Create', entity='Product'),
        FileSample(operation='Get', entity='Product')
    ]
    all_files = [
        Path('src/UseCases/Products/Create/CreateProductHandler.cs'),
        Path('src/UseCases/Products/Update/UpdateProductHandler.cs'),
        Path('src/UseCases/Products/Delete/DeleteProductHandler.cs')
    ]

    # When: Ensure completeness
    checker = CRUDCompletenessChecker()
    complete_samples = checker.ensure_crud_completeness(samples, all_files)

    # Then: Should add Update and Delete
    operations = {s.operation for s in complete_samples}
    assert 'Update' in operations
    assert 'Delete' in operations
```

### 2.4 Acceptance Criteria

- [ ] Stratified sampling discovers all CRUD operations
- [ ] Max_files allocation proportional (40% CRUD, 20% queries, etc.)
- [ ] CRUD completeness checker adds missing operations
- [ ] Pattern category detection accurate (≥90% correct categorization)
- [ ] Re-test on ardalis generates 33 templates (26 + 7 missing)
- [ ] False Negative score improves to ≥8/10

---

## Phase 3: Enhanced AI Prompting

**Duration**: 1-2 days (9-12 hours)
**Priority**: Medium
**Dependencies**: Phase 1, 2
**Deliverables**:
- Updated AI prompts
- Completeness documentation
- Validation checklists in CLAUDE.md

### 3.1 Prompt Enhancements

**File**: `installer/core/lib/template_generator/template_generator.py`

**Update `_create_extraction_prompt`**:

```python
def _create_extraction_prompt(
    self,
    content: str,
    file_path: str,
    language: str,
    purpose: Optional[str]
) -> str:
    """Enhanced prompt with completeness requirements."""

    completeness_requirements = """

**CRITICAL - TEMPLATE COMPLETENESS**:

You are generating SCAFFOLDING for complete features, not just examples.

CRUD Completeness Rule:
- If any CRUD operation exists, ALL must be generated:
  ✓ Create (POST)
  ✓ Read (GET by ID, GET collection)
  ✓ Update (PUT)
  ✓ Delete (DELETE)

Layer Symmetry Rule:
- If UseCases has UpdateEntity → Web must have Update endpoint
- If Web has Delete endpoint → UseCases must have DeleteEntity
- Operations must exist in ALL relevant layers

REPR Pattern Completeness:
- Each endpoint requires:
  ✓ Endpoint class (e.g., Create.cs)
  ✓ Request DTO (e.g., CreateEntityRequest.cs)
  ✓ Response DTO (e.g., CreateEntityResponse.cs) [if non-void]
  ✓ Validator (e.g., CreateEntityValidator.cs)

Remember: Users need COMPLETE CRUD operations, not representative samples.
"""

    return f"""Convert this {language} file into a reusable template...

{completeness_requirements}

**Original File**: {file_path}
...
"""
```

**File**: `installer/core/lib/template_generator/claude_md_generator.py`

**Add Validation Section**:

```python
def generate(self, analysis: CodebaseAnalysis) -> TemplateClaude:
    """Generate CLAUDE.md with validation checklist."""

    # ... existing sections ...

    validation_checklist = """
## Template Validation Checklist

Before using this template, verify:

**CRUD Completeness**:
- [ ] Create operation (endpoint + handler + validator)
- [ ] Read operation (GetById + List + handlers)
- [ ] Update operation (endpoint + handler + validator)
- [ ] Delete operation (endpoint + handler + validator)

**Layer Symmetry**:
- [ ] All UseCases commands have Web endpoints
- [ ] All Web endpoints have UseCases handlers
- [ ] Repository interfaces exist for all operations

**REPR Pattern** (if using FastEndpoints):
- [ ] Each endpoint has Request/Response/Validator
- [ ] Validators use FluentValidation
- [ ] Routes follow RESTful conventions

**Pattern Consistency**:
- [ ] All entities follow same operation structure
- [ ] Naming conventions consistent
- [ ] Placeholders consistently applied

See [Template Completeness Validation](../checklists/template-completeness-validation.md)
for detailed checklist.
"""

    # Add to CLAUDE.md content
    pass
```

### 3.2 Testing Plan

**Manual Testing**:
- Run template-create with enhanced prompts
- Verify AI generates all CRUD operations
- Check for completeness mentions in logs

**Integration Testing**:
- Compare template count before/after prompt changes
- Measure False Negative score improvement

### 3.3 Acceptance Criteria

- [ ] Prompts explicitly state CRUD completeness requirements
- [ ] CLAUDE.md includes validation checklist
- [ ] AI logs show consideration of completeness
- [ ] False Negative score ≥8/10

---

## Integration & Testing

### End-to-End Testing

**Test Suite**: `tests/e2e/test_template_create_complete_workflow.py`

```python
def test_complete_workflow_ardalis():
    """Test complete workflow on ardalis-clean-architecture."""
    # Given: ardalis-clean-architecture repository
    config = OrchestrationConfig(
        codebase_path=Path('tests/fixtures/CleanArchitecture-ardalis'),
        skip_qa=True,
        max_files=20,  # Phase 2
        interactive=False,
        auto_fix=True  # Phase 1
    )

    # When: Run complete workflow
    orchestrator = TemplateCreateOrchestrator(config)
    result = orchestrator.run()

    # Then: Should generate complete templates
    assert result.success is True
    assert result.template_count >= 33  # 26 + 7 missing
    assert result.false_negative_score >= 8.0

    # Verify specific missing templates now exist
    templates_dir = result.output_path / 'templates'
    assert (templates_dir / 'Web/Endpoints/Update.cs.template').exists()
    assert (templates_dir / 'Web/Endpoints/Delete.cs.template').exists()
```

### Regression Testing

**Ensure existing functionality unchanged**:
- Run on all test repositories
- Compare results with baseline (pre-changes)
- Verify no new issues introduced

---

## Deployment Plan

### Phase 1 Deployment

**Week 1**:
- Day 1-2: Implement CompletenessValidator
- Day 3: Integrate Phase 6.5
- Day 4: Testing
- Day 5: Deploy to staging, monitor

### Phase 2 Deployment

**Week 2-3**:
- Day 1-2: Implement StratifiedSampler
- Day 3: Integrate into AI analyzer
- Day 4-5: Testing
- Week 3 Day 1: Deploy to staging

### Phase 3 Deployment

**Week 3-4**:
- Day 1: Update prompts
- Day 2: Testing
- Day 3: Deploy to production

### Rollback Plan

**If Phase 1 causes issues**:
- Set `skip_validation=True` in config
- Revert orchestrator changes
- Continue with old workflow

**If Phase 2 causes issues**:
- Set `use_stratified_sampling=False`
- Fallback to original FileCollector

---

## Success Metrics

### Quantitative Metrics

| Metric | Baseline | Target | Actual |
|--------|----------|--------|--------|
| False Negative Score | 4.3/10 | ≥8/10 | ___ |
| Template Count (ardalis) | 26 | 33 | ___ |
| CRUD Completeness | 60% | 100% | ___ |
| Layer Symmetry | 60% | 100% | ___ |
| Test Coverage | 70% | ≥85% | ___ |

### Qualitative Metrics

- [ ] Developers trust template quality
- [ ] No manual fixes required after generation
- [ ] Clear validation reports
- [ ] Auto-fix works reliably

---

## Timeline

```
Week 1: Phase 1 (Completeness Validation)
  Days 1-2: Implementation
  Day 3: Integration
  Day 4: Testing
  Day 5: Deploy to staging

Week 2-3: Phase 2 (Stratified Sampling)
  Days 1-2: Implementation
  Day 3: Integration
  Days 4-5: Testing
  Week 3 Day 1: Deploy to staging

Week 3-4: Phase 3 (Enhanced Prompts)
  Day 1: Implementation
  Day 2: Testing
  Day 3: Deploy to production

Week 4: Validation & Documentation
  Days 1-2: End-to-end testing
  Day 3: Documentation updates
  Days 4-5: Production deployment
```

**Total Duration**: 8-10 days (excluding parallel work)

---

## Risk Mitigation

### Technical Risks

**Risk**: Auto-generation creates invalid templates
**Mitigation**:
- Validate generated templates before saving
- Test compilation of generated code
- Fallback to manual warning if auto-gen fails

**Risk**: Stratified sampling degrades performance
**Mitigation**:
- Profile sampling time
- Optimize pattern detection
- Provide skip flag if needed

### Process Risks

**Risk**: False positive rate increases (too many warnings)
**Mitigation**:
- Tune validation thresholds
- Allow user to override warnings
- Provide clear explanation of issues

---

## Documentation Updates

### Files to Update

1. `docs/guides/template-quality-validation.md` (NEW)
2. `docs/checklists/template-completeness-validation.md` (Already created)
3. `installer/core/commands/template-create.md` (Update with Phase 5.5)
4. `docs/workflows/template-creation-workflow.md` (Add validation step)

---

## Conclusion

This phased implementation plan provides a **robust, testable approach** to fixing template generation completeness issues. Each phase can be implemented and validated independently, reducing risk and allowing for course corrections.

**Next Steps**:
1. Get approval for Phase 1 implementation
2. Create detailed technical design for CompletenessValidator
3. Begin implementation Week 1

---

**Document Status**: ✅ Complete and Ready for Implementation
**Approval Required**: Technical Lead, Product Owner
**Start Date**: TBD
