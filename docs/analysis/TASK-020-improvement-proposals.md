# TASK-020: Template Generation Improvement Proposals

**Date**: 2025-11-07
**Author**: Task-Manager Agent
**Status**: Complete
**Related**: [Root Cause Analysis](./TASK-020-root-cause-analysis.md)

---

## Executive Summary

This document proposes **three concrete approaches** to prevent incomplete template generation. Each approach addresses the root cause (selective sampling without pattern-aware completeness validation) with different trade-offs.

**Recommended Solution**: **Hybrid Approach** (combines Option A + Option C)

---

## Problem Restatement

**Current State**: AI samples representative files, generates templates, no completeness validation
**Gap**: Missing 7 Web endpoint templates (Update/Delete operations)
**Root Cause**: Selective sampling + no pattern completeness checks
**Impact**: Incomplete CRUD APIs, reduced template usability

---

## Proposal 1: Pattern-Aware Stratified Sampling

### Overview

Replace random/quality-based sampling with **stratified sampling** that ensures coverage of all pattern types before template generation begins.

### Current Sampling (Phase 2)

```python
# ai_analyzer.py, line 119
file_collector = FileCollector(codebase_path, max_files=10)
file_samples = file_collector.collect_samples()
```

**Problem**:
- Collects 10 "representative" files
- No guarantee of pattern diversity
- May miss entire pattern categories

### Proposed Stratified Sampling

```python
class StratifiedSampler:
    """Ensures pattern diversity in file sampling."""

    def collect_stratified_samples(
        self,
        codebase_path: Path,
        max_files: int = 20  # Increased from 10
    ) -> List[FileSample]:
        """
        Collect files ensuring coverage of all pattern types.

        Strategy:
        1. Discover all files by layer and pattern
        2. Sample proportionally from each category
        3. Ensure CRUD completeness for each entity
        4. Fill remaining slots with quality-ranked files
        """
        samples = []

        # Step 1: Identify pattern categories
        patterns = self._identify_pattern_categories()
        # Example: {'CRUD': ['Create', 'Read', 'Update', 'Delete'],
        #           'Query': ['GetById', 'List', 'Search'],
        #           'Validation': ['Validator', 'Specification']}

        # Step 2: Sample from each category
        for pattern_type, operations in patterns.items():
            for operation in operations:
                sample = self._find_best_example(pattern_type, operation)
                if sample:
                    samples.append(sample)

        # Step 3: Fill remaining with quality-ranked
        remaining = max_files - len(samples)
        if remaining > 0:
            quality_samples = self._rank_by_quality(
                exclude=samples,
                limit=remaining
            )
            samples.extend(quality_samples)

        return samples[:max_files]

    def _identify_pattern_categories(self) -> Dict[str, List[str]]:
        """
        Discover pattern categories in codebase.

        For CRUD patterns, specifically looks for:
        - Create operations
        - Read operations (GetById, List, Search)
        - Update operations
        - Delete operations
        """
        # Implementation: Scan directory names, file names, code analysis
        pass

    def _ensure_crud_completeness(
        self,
        samples: List[FileSample]
    ) -> List[FileSample]:
        """
        Verify CRUD completeness for each layer.

        If UseCases has Update, Web layer must have Update endpoint.
        """
        # Check for CRUD asymmetry
        use_cases_ops = self._extract_operations(samples, layer="UseCases")
        web_ops = self._extract_operations(samples, layer="Web")

        missing_web_ops = use_cases_ops - web_ops

        if missing_web_ops:
            # Add missing operations to samples
            for op in missing_web_ops:
                sample = self._find_operation_example(layer="Web", operation=op)
                if sample:
                    samples.append(sample)

        return samples
```

### Implementation Plan

**New Files**:
```
installer/global/lib/codebase_analyzer/
├── stratified_sampler.py       # NEW
│   ├── StratifiedSampler
│   ├── PatternCategoryDetector
│   └── CRUDCompletenessChecker
└── pattern_detector.py          # NEW
    ├── CRUDPatternDetector
    ├── ArchitectureLayerDetector
    └── OperationMatcher
```

**Modified Files**:
```python
# ai_analyzer.py
class CodebaseAnalyzer:
    def __init__(self, max_files: int = 20):  # Increased
        self.sampler = StratifiedSampler()

    def analyze_codebase(self, codebase_path: Path):
        # Replace FileCollector with StratifiedSampler
        samples = self.sampler.collect_stratified_samples(
            codebase_path,
            max_files=self.max_files
        )
```

### Advantages

✅ **Proactive**: Catches completeness issues during analysis
✅ **No False Negatives**: Guarantees pattern coverage
✅ **Minimal Prompt Changes**: AI still does same generation work
✅ **Technology Agnostic**: Works for any CRUD-based architecture

### Disadvantages

⚠️ **Increased Sampling Time**: Need to scan more files upfront
⚠️ **Complexity**: Pattern detection logic must be robust
⚠️ **Token Usage**: May increase context window (20 files vs 10)

### Estimated Effort

- **Design**: 4 hours
- **Implementation**: 12 hours
- **Testing**: 6 hours
- **Total**: 22 hours

### Success Criteria

- False Negative score improves from 4.3/10 to ≥8/10
- All CRUD operations captured for each entity
- Re-test on ardalis-clean-architecture shows 33 templates (26+7)

---

## Proposal 2: Post-Generation Completeness Validation (Phase 6.5)

### Overview

Add a **validation phase after template generation** (Phase 6.5) that checks for pattern completeness and generates missing templates.

### Current Workflow

```
Phase 6: Template File Generation
  ↓
Phase 7: Agent Recommendation
```

### Proposed Workflow

```
Phase 6: Template File Generation
  ↓
Phase 6.5: Completeness Validation ← NEW
  ├─ Check CRUD completeness
  ├─ Check layer symmetry
  ├─ Identify missing patterns
  └─ Generate missing templates OR warn user
  ↓
Phase 7: Agent Recommendation
```

### Implementation

```python
class CompletenessValidator:
    """
    Validates template completeness after Phase 6.

    Checks:
    1. CRUD operations: If Create exists, Update/Delete should exist
    2. Layer symmetry: If UseCases has Update, Web should have Update
    3. Pattern completeness: Validators for each request, etc.
    """

    def validate_completeness(
        self,
        templates: TemplateCollection,
        analysis: CodebaseAnalysis
    ) -> ValidationReport:
        """
        Validate template collection completeness.

        Returns report with:
        - Missing patterns
        - Layer asymmetries
        - Recommended additions
        """
        issues = []

        # Check 1: CRUD Completeness
        crud_issues = self._check_crud_completeness(templates)
        issues.extend(crud_issues)

        # Check 2: Layer Symmetry
        symmetry_issues = self._check_layer_symmetry(templates)
        issues.extend(symmetry_issues)

        # Check 3: Pattern Consistency
        pattern_issues = self._check_pattern_consistency(templates)
        issues.extend(pattern_issues)

        return ValidationReport(
            is_complete=len(issues) == 0,
            issues=issues,
            recommended_templates=self._generate_recommendations(issues)
        )

    def _check_crud_completeness(
        self,
        templates: TemplateCollection
    ) -> List[CompletenessIssue]:
        """
        Verify CRUD operations are complete.

        Logic:
        - If Create exists, Update and Delete should exist
        - If GetById exists, List should exist
        - If any CRUD exists, all should exist
        """
        issues = []

        # Group templates by entity and operation
        entities = self._group_by_entity(templates)

        for entity, ops in entities.items():
            crud_ops = {'Create', 'Get', 'Update', 'Delete', 'List'}
            present_ops = set(ops.keys())
            missing_ops = crud_ops - present_ops

            if present_ops and missing_ops:
                issues.append(CompletenessIssue(
                    severity='high',
                    type='incomplete_crud',
                    entity=entity,
                    missing_operations=missing_ops,
                    message=f"Entity '{entity}' has incomplete CRUD: "
                            f"missing {', '.join(missing_ops)}"
                ))

        return issues

    def _check_layer_symmetry(
        self,
        templates: TemplateCollection
    ) -> List[CompletenessIssue]:
        """
        Verify operations exist across layers.

        Rule: If UseCases has UpdateEntity, Web must have Update endpoint
        """
        issues = []

        # Extract operations by layer
        use_cases = self._extract_operations(templates, layer='UseCases')
        web = self._extract_operations(templates, layer='Web')
        infrastructure = self._extract_operations(templates, layer='Infrastructure')

        # Check symmetry
        for op in use_cases:
            if op not in web and op != 'List':  # List may be optional
                issues.append(CompletenessIssue(
                    severity='high',
                    type='layer_asymmetry',
                    operation=op,
                    message=f"Operation '{op}' exists in UseCases but "
                            f"missing from Web layer"
                ))

        return issues

    def _generate_recommendations(
        self,
        issues: List[CompletenessIssue]
    ) -> List[TemplateRecommendation]:
        """
        Generate recommendations for missing templates.

        Can optionally auto-generate missing templates using patterns.
        """
        recommendations = []

        for issue in issues:
            if issue.type == 'incomplete_crud':
                for missing_op in issue.missing_operations:
                    recommendations.append(TemplateRecommendation(
                        file_path=f"Web/Endpoints/{missing_op}.cs.template",
                        reason=f"Complete CRUD for {issue.entity}",
                        can_auto_generate=True,
                        reference_template=self._find_similar_template(missing_op)
                    ))

        return recommendations


class PhaseResult:
    """Result object for phase execution."""
    pass


def execute_phase_6_5_validation(
    templates: TemplateCollection,
    analysis: CodebaseAnalysis,
    orchestrator_config: OrchestrationConfig
) -> PhaseResult:
    """
    Phase 6.5: Completeness Validation

    Executed after Phase 6 (Template Generation).
    """
    print("\n" + "="*60)
    print("Phase 6.5: Completeness Validation")
    print("="*60)

    validator = CompletenessValidator()
    report = validator.validate_completeness(templates, analysis)

    if report.is_complete:
        print("✅ All patterns complete")
        return PhaseResult(success=True)

    # Display issues
    print(f"\n⚠️  Found {len(report.issues)} completeness issues:\n")
    for issue in report.issues:
        print(f"  [{issue.severity.upper()}] {issue.message}")

    # Show recommendations
    if report.recommended_templates:
        print(f"\n💡 Recommended additions ({len(report.recommended_templates)}):\n")
        for rec in report.recommended_templates:
            print(f"  + {rec.file_path}")
            if rec.can_auto_generate:
                print(f"    (Can auto-generate based on {rec.reference_template})")

    # Decision point
    if orchestrator_config.interactive:
        choice = input("\nOptions:\n"
                      "  [A] Auto-generate missing templates\n"
                      "  [C] Continue without fixes (not recommended)\n"
                      "  [Q] Quit and fix manually\n"
                      "Choice: ").lower()

        if choice == 'a':
            # Auto-generate missing templates
            new_templates = validator.generate_missing_templates(
                report.recommended_templates,
                existing_templates=templates
            )
            templates.templates.extend(new_templates)
            print(f"✅ Generated {len(new_templates)} missing templates")
            return PhaseResult(success=True, templates_added=len(new_templates))
        elif choice == 'c':
            print("⚠️  Continuing with incomplete templates")
            return PhaseResult(success=True, warnings=["Incomplete templates"])
        else:
            print("❌ Template creation cancelled")
            return PhaseResult(success=False)
    else:
        # Non-interactive: Auto-generate if possible
        if all(rec.can_auto_generate for rec in report.recommended_templates):
            new_templates = validator.generate_missing_templates(
                report.recommended_templates,
                existing_templates=templates
            )
            templates.templates.extend(new_templates)
            print(f"✅ Auto-generated {len(new_templates)} missing templates")
            return PhaseResult(success=True, templates_added=len(new_templates))
        else:
            print("❌ Cannot auto-generate all missing templates")
            return PhaseResult(success=False, errors=["Manual intervention required"])
```

### Integration into Orchestrator

```python
# template_create_orchestrator.py

def run(self) -> OrchestrationResult:
    # ... existing phases ...

    # Phase 6: Template File Generation
    templates = self._phase6_template_generation(analysis)
    if not templates:
        self.warnings.append("No template files generated")

    # Phase 6.5: Completeness Validation ← NEW
    validation_result = self._phase6_5_completeness_validation(
        templates=templates,
        analysis=analysis
    )
    if not validation_result.success:
        return self._create_error_result("Template completeness validation failed")

    # Phase 7: Agent Recommendation
    # ... continue ...
```

### Implementation Plan

**New Files**:
```
installer/global/lib/template_generator/
├── completeness_validator.py    # NEW
│   ├── CompletenessValidator
│   ├── ValidationReport
│   ├── CompletenessIssue
│   └── TemplateRecommendation
└── pattern_matcher.py            # NEW
    ├── CRUDPatternMatcher
    ├── LayerSymmetryChecker
    └── OperationGrouper
```

**Modified Files**:
```
installer/global/commands/lib/template_create_orchestrator.py
├── Add _phase6_5_completeness_validation()
└── Update run() to call Phase 6.5
```

### Advantages

✅ **Safety Net**: Catches issues even if sampling missed them
✅ **User Control**: Interactive mode lets users decide
✅ **Auto-Fix**: Can generate missing templates from patterns
✅ **Clear Feedback**: Tells users exactly what's missing

### Disadvantages

⚠️ **Reactive**: Waits until generation complete to check
⚠️ **Duplication**: May need to re-invoke AI for missing templates
⚠️ **Complexity**: Requires pattern matching logic

### Estimated Effort

- **Design**: 3 hours
- **Implementation**: 10 hours
- **Testing**: 5 hours
- **Total**: 18 hours

### Success Criteria

- Detects 7 missing endpoint templates
- Offers to auto-generate or warns user
- False Negative score improves to ≥8/10

---

## Proposal 3: Enhanced AI Prompting with Completeness Requirements

### Overview

Update AI prompts to **explicitly require CRUD completeness** and provide checklists for validation.

### Current Approach

AI receives general instruction: "Generate comprehensive set of template files"

### Proposed Enhanced Prompt

```markdown
You are generating templates for a Clean Architecture codebase.

CRITICAL COMPLETENESS REQUIREMENTS:

1. CRUD Completeness:
   For each entity, generate templates for ALL operations:
   ✓ Create (POST endpoint + Command + Handler)
   ✓ Read   (GET endpoint + Query + Handler)
   ✓ Update (PUT endpoint + Command + Handler)
   ✓ Delete (DELETE endpoint + Command + Handler)
   ✓ List   (GET collection endpoint + Query + Handler)

2. Layer Symmetry:
   For each operation in UseCases layer, Web layer MUST have corresponding endpoint:
   - If UseCases/Create exists → Web/Create must exist
   - If UseCases/Update exists → Web/Update must exist
   - If UseCases/Delete exists → Web/Delete must exist

3. REPR Pattern Completeness (for FastEndpoints):
   Each endpoint requires:
   ✓ Endpoint class (e.g., Create.cs)
   ✓ Request DTO (e.g., CreateEntityRequest.cs)
   ✓ Response DTO (e.g., CreateEntityResponse.cs) [if not void]
   ✓ Validator (e.g., CreateEntityValidator.cs)

4. Validation Checklist:
   Before completing Phase 6, verify:
   ☐ All CRUD operations present for each entity
   ☐ UseCases operations match Web endpoints
   ☐ Each Request has Validator
   ☐ Each Command/Query has Handler

SCAFFOLDING VS EXAMPLES:
You are generating SCAFFOLDING, not just examples.
Users need COMPLETE sets of operations, not representative samples.
"Create, Get, List" is NOT sufficient - users need Update and Delete too.

If you detect patterns for Update/Delete in source code,
you MUST generate corresponding templates, even if they seem
similar to Create/Get patterns.
```

### Implementation

**Modified Files**:
```python
# template_generator.py

def _create_extraction_prompt(
    self,
    content: str,
    file_path: str,
    language: str,
    purpose: Optional[str]
) -> str:
    """Create prompt for AI placeholder extraction."""

    # Add completeness context
    completeness_note = """

    **IMPORTANT - Template Completeness**:
    You are generating templates for SCAFFOLDING, not examples.
    Ensure CRUD completeness: If Create exists, Update and Delete must exist.
    """

    base_prompt = f"""Convert this {language} file into a reusable template...
    {completeness_note}
    ...
    """
    return base_prompt


# claude_md_generator.py

def generate(self) -> TemplateClaude:
    """Generate CLAUDE.md with completeness validation section."""

    # Add validation checklist to documentation
    validation_section = """
    ## Template Validation Checklist

    Before using this template, verify:

    **CRUD Completeness**:
    - [ ] Create operation (endpoint + handler)
    - [ ] Read operation (GetById + handler)
    - [ ] Update operation (endpoint + handler)
    - [ ] Delete operation (endpoint + handler)
    - [ ] List operation (endpoint + handler)

    **Layer Symmetry**:
    - [ ] All UseCases commands have Web endpoints
    - [ ] All Web endpoints have UseCases handlers

    **REPR Pattern**:
    - [ ] Each endpoint has Request/Response/Validator
    """

    # Include in generated CLAUDE.md
    pass
```

### Orchestrator Integration

```python
# template_create_orchestrator.py

def _phase2_ai_analysis(self, qa_answers: Dict[str, Any]) -> Optional[Any]:
    """Phase 2 with enhanced completeness context."""

    template_context = {
        'name': qa_answers.get('template_name'),
        'language': qa_answers.get('primary_language'),
        # ... existing context ...

        # NEW: Add completeness requirements
        'completeness_requirements': {
            'crud_operations': ['Create', 'Read', 'Update', 'Delete', 'List'],
            'layer_symmetry_required': True,
            'pattern_type': 'scaffolding'  # vs 'examples'
        }
    }

    # Pass to analyzer
    analyzer = CodebaseAnalyzer(max_files=10)
    analysis = analyzer.analyze_codebase(
        codebase_path=codebase_path,
        template_context=template_context,  # Enhanced context
        save_results=False
    )
```

### Advantages

✅ **Simplest Implementation**: Just prompt changes
✅ **No New Components**: Uses existing infrastructure
✅ **Proactive**: AI knows requirements upfront
✅ **Educational**: Documents expectations in prompts

### Disadvantages

⚠️ **Reliance on AI**: Depends on AI following instructions
⚠️ **No Enforcement**: No validation if AI ignores prompt
⚠️ **Prompt Complexity**: Longer prompts may reduce effectiveness

### Estimated Effort

- **Design**: 2 hours
- **Implementation**: 4 hours
- **Testing**: 3 hours
- **Total**: 9 hours

### Success Criteria

- AI generates all CRUD operations
- No missing templates in test run
- False Negative score ≥8/10

---

## Proposal 4: Hybrid Approach (RECOMMENDED)

### Overview

Combine **Proposal 1 (Stratified Sampling)** + **Proposal 2 (Completeness Validation)** for robust solution.

### Strategy

```
Phase 2: AI Analysis
  └─ Use Stratified Sampling (Proposal 1)
     ├─ Ensure pattern diversity
     ├─ Sample all CRUD operations
     └─ Check layer symmetry during sampling

Phase 6: Template Generation
  └─ Use Enhanced Prompts (Proposal 3)
     ├─ Explicit CRUD completeness requirements
     └─ Scaffolding vs examples guidance

Phase 6.5: Completeness Validation (Proposal 2)
  └─ Safety net validation
     ├─ Check CRUD completeness
     ├─ Check layer symmetry
     ├─ Auto-generate missing if possible
     └─ Warn user if gaps remain
```

### Why Hybrid?

**Defense in Depth**:
1. **Proactive** (Stratified Sampling): Ensures good input data
2. **Guided** (Enhanced Prompts): Helps AI understand requirements
3. **Validated** (Completeness Check): Catches any remaining gaps

**Fail-Safes**:
- If sampling misses patterns → Validation catches them
- If AI ignores prompts → Validation catches gaps
- If validation fails → User gets clear warning

### Implementation Plan

**Phase 1** (Weeks 1-2): Stratified Sampling
- Implement `StratifiedSampler`
- Implement `CRUDPatternDetector`
- Test on ardalis-clean-architecture

**Phase 2** (Week 3): Completeness Validation
- Implement `CompletenessValidator`
- Add Phase 6.5 to orchestrator
- Test validation detection

**Phase 3** (Week 4): Enhanced Prompts
- Update all AI prompts
- Add completeness documentation
- Final integration testing

### Advantages

✅ **Most Robust**: Multiple layers of protection
✅ **Best User Experience**: Catches gaps, offers fixes
✅ **Technology Agnostic**: Works for any architecture
✅ **Future-Proof**: Handles edge cases

### Disadvantages

⚠️ **Most Complex**: Requires all three implementations
⚠️ **Longest Timeline**: 4 weeks vs 1-2 weeks for individual approaches

### Estimated Effort

- **Stratified Sampling**: 22 hours
- **Completeness Validation**: 18 hours
- **Enhanced Prompts**: 9 hours
- **Integration**: 6 hours
- **Testing**: 10 hours
- **Total**: 65 hours (~8 days)

### Success Criteria

- False Negative score: 4.3/10 → ≥8/10 (target: 9/10)
- Re-test generates 33 templates (26 + 7 missing)
- Zero CRUD gaps detected in validation
- Works on 3+ different architecture types

---

## Comparison Matrix

| Criterion | Proposal 1 (Stratified) | Proposal 2 (Validation) | Proposal 3 (Prompts) | Hybrid (1+2+3) |
|-----------|------------------------|------------------------|---------------------|----------------|
| **Effort** | 22 hours | 18 hours | 9 hours | 65 hours |
| **Robustness** | High | Medium | Low | Very High |
| **Proactive** | ✅ Yes | ❌ No (reactive) | ✅ Yes | ✅ Yes |
| **Auto-Fix** | ❌ No | ✅ Yes | ❌ No | ✅ Yes |
| **AI-Dependent** | Low | Low | High | Low |
| **False Neg Fix** | 7/10 | 8/10 | 6/10 | 9/10 |
| **Timeline** | 3 weeks | 2.5 weeks | 1 week | 4 weeks |

---

## Recommendation

**Adopt: Hybrid Approach (Proposals 1 + 2 + 3)**

**Rationale**:
1. **Highest Quality**: Only approach likely to achieve 9/10 false negative score
2. **Defense in Depth**: Multiple validation points prevent gaps
3. **Best ROI Long-Term**: Prevents issues across all future templates
4. **User Confidence**: Auto-fix capability improves trust in system

**Implementation Priority**:
1. **Phase 1** (MVP): Completeness Validation (Proposal 2) - 18 hours
   - Quickest path to improvement
   - Validates current process
   - Can deploy independently

2. **Phase 2** (Enhanced): Stratified Sampling (Proposal 1) - 22 hours
   - Reduces validation failures
   - Improves analysis quality
   - More efficient overall

3. **Phase 3** (Optimization): Enhanced Prompts (Proposal 3) - 9 hours
   - Fine-tuning
   - Documentation improvements
   - Educational value

**Alternative (If Timeline Constrained)**:
Start with **Proposal 2 only** (Completeness Validation):
- Delivers 80% of value
- Can be implemented in 2.5 weeks
- Allows testing before committing to full hybrid

---

## Next Steps

1. **Review & Approve**: Get stakeholder approval for Hybrid Approach
2. **Detailed Design**: Create technical design docs for each component
3. **Implementation**: Execute in 3 phases (Validation → Sampling → Prompts)
4. **Testing**: Re-run ardalis-clean-architecture after each phase
5. **Documentation**: Update template creation guide
6. **Release**: Deploy to production with monitoring

---

**Document Status**: ✅ Complete
**Decision Required**: Approve recommended approach
**Next Action**: Detailed technical design for Phase 1 (Completeness Validation)
