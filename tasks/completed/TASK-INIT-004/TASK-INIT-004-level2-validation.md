---
id: TASK-INIT-004
title: "Port Level 2 extended validation to /template-init"
status: completed
created: 2025-11-26T07:30:00Z
updated: 2025-11-26T16:30:00Z
completed: 2025-11-26T16:30:00Z
priority: medium
tags: [template-init, validation, week2, quality-infrastructure]
complexity: 4
estimated_hours: 4
actual_hours: 2
parent_review: TASK-5E55
week: 2
phase: validation-framework
related_tasks: [TASK-INIT-003, TASK-INIT-005]
dependencies: [TASK-INIT-003]
test_results:
  status: passed
  coverage: 100
  last_run: 2025-11-26T16:30:00Z
implementation_summary: TASK-INIT-004-IMPLEMENTATION-SUMMARY.md
---

# Task: Port Level 2 Extended Validation to /template-init

## Problem Statement

`/template-init` lacks optional extended validation with quality reports, missing Critical Gap #7 from TASK-5E55. Users can't get detailed quality assessment before template deployment.

**Impact**: Teams deploy templates without quality metrics, risking production issues and maintenance burden.

## Analysis Findings

From TASK-5E55 review:
- `/template-create` Phase 7.5: Extended validation with `--validate` flag (TASK-043)
- Generates `validation-report.md` with 0-10 score
- Checks placeholder consistency, pattern fidelity
- Assigns letter grade (A-F)
- Exit code based on quality score
- `/template-init` has NO extended validation option
- Gap severity: 🟴 **HIGH**

**Current State**: Only Level 1 automatic validation (TASK-INIT-003).

**Desired State**: Optional `--validate` flag for comprehensive quality reports.

## Recommended Fix

**Approach**: Add `--validate` flag to enable extended validation and report generation.

**Strategy**:
- **MINIMAL SCOPE**: Add flag support, extended validation functions, report generation
- **REUSE**: Copy validation logic from `/template-create` Phase 7.5
- **OPTIONAL**: Only runs when `--validate` flag present
- **ACTIONABLE**: Generate markdown report with specific findings

## Code Changes Required

### File 1: installer/global/commands/lib/greenfield_qa_session.py

**MODIFY constructor** (around line 203):

```python
def __init__(self, validate: bool = False):
    """
    Initialize Q&A session.
    
    Args:
        validate: Run extended validation (Level 2)
    """
    if not INQUIRER_AVAILABLE:
        raise ImportError(
            "inquirer library not installed. "
            "Install with: pip install inquirer"
        )
    
    self.answers: Optional[GreenfieldAnswers] = None
    self._session_data: dict = {}
    self.validate = validate  # NEW flag
```

**ADD validation functions** (after line 530):

```python
def _validate_placeholder_consistency(self, template_path: Path) -> dict:
    """
    Validate placeholder format consistency across template files.
    
    Port of template-create Phase 7.5 validation (TASK-043).
    
    Args:
        template_path: Path to generated template
        
    Returns:
        dict with consistency score and issues
        
    Example:
        >>> result = session._validate_placeholder_consistency(Path('/tmp/template'))
        >>> result['score']
        8
    """
    issues = []
    placeholder_formats = []
    
    # Scan template files for placeholder patterns
    for template_file in template_path.rglob("*.template"):
        content = template_file.read_text()
        
        # Detect placeholder formats: {{var}}, ${var}, {var}, __VAR__
        if '{{' in content and '}}' in content:
            placeholder_formats.append('mustache')
        if '${' in content and '}' in content:
            placeholder_formats.append('dollar_brace')
        if '__' in content:
            placeholder_formats.append('double_underscore')
    
    # Check for mixed formats (anti-pattern)
    unique_formats = set(placeholder_formats)
    if len(unique_formats) > 1:
        issues.append(f"Mixed placeholder formats detected: {unique_formats}")
    
    # Score: 10 if consistent, deduct 3 per inconsistency
    score = 10 - (len(issues) * 3)
    score = max(0, min(10, score))
    
    return {
        'score': score,
        'issues': issues,
        'formats_found': list(unique_formats)
    }


def _validate_pattern_fidelity(self, template_data: dict) -> dict:
    """
    Validate architectural pattern fidelity.
    
    Port of template-create Phase 7.5 validation (TASK-043).
    
    Args:
        template_data: Template structure with architecture pattern
        
    Returns:
        dict with fidelity score and issues
    """
    issues = []
    pattern = template_data.get('architecture_pattern', 'unknown')
    layers = template_data.get('layers', [])
    agents = template_data.get('agents', [])
    
    # Pattern-specific validation
    if pattern == '3-tier':
        expected_layers = {'api', 'service', 'repository'}
        found_layers = {layer.lower() for layer in layers}
        missing = expected_layers - found_layers
        if missing:
            issues.append(f"3-tier pattern missing layers: {missing}")
    
    elif pattern == 'microservices':
        # Check for service isolation agents
        service_agents = [a for a in agents if 'service' in a.get('name', '').lower()]
        if len(service_agents) < 2:
            issues.append("Microservices pattern should have multiple service agents")
    
    elif pattern == 'mvc':
        expected_layers = {'controller', 'model', 'view'}
        found_layers = {layer.lower() for layer in layers}
        missing = expected_layers - found_layers
        if missing:
            issues.append(f"MVC pattern missing layers: {missing}")
    
    # Score: 10 if perfect, deduct 2 per issue
    score = 10 - (len(issues) * 2)
    score = max(0, min(10, score))
    
    return {
        'score': score,
        'issues': issues,
        'pattern': pattern
    }


def _calculate_overall_quality_score(
    self,
    placeholder_result: dict,
    pattern_result: dict,
    crud_result: dict,
    layer_result: dict
) -> dict:
    """
    Calculate overall quality score (0-10) and grade.
    
    Args:
        placeholder_result: Placeholder consistency validation
        pattern_result: Pattern fidelity validation
        crud_result: CRUD completeness validation (from Level 1)
        layer_result: Layer symmetry validation (from Level 1)
        
    Returns:
        dict with overall score, grade, and component scores
    """
    # Component scores
    placeholder_score = placeholder_result['score']
    pattern_score = pattern_result['score']
    crud_score = 10 if crud_result['passes'] else 5
    layer_score = 10 if layer_result['is_symmetric'] else 5
    
    # Weighted average (placeholder and pattern more important in extended validation)
    weights = {
        'placeholder': 0.3,
        'pattern': 0.3,
        'crud': 0.2,
        'layer': 0.2
    }
    
    overall_score = (
        placeholder_score * weights['placeholder'] +
        pattern_score * weights['pattern'] +
        crud_score * weights['crud'] +
        layer_score * weights['layer']
    )
    
    # Calculate letter grade
    if overall_score >= 9:
        grade = 'A+'
    elif overall_score >= 8:
        grade = 'A'
    elif overall_score >= 7:
        grade = 'B'
    elif overall_score >= 6:
        grade = 'C'
    elif overall_score >= 5:
        grade = 'D'
    else:
        grade = 'F'
    
    return {
        'overall_score': round(overall_score, 1),
        'grade': grade,
        'component_scores': {
            'placeholder_consistency': placeholder_score,
            'pattern_fidelity': pattern_score,
            'crud_completeness': crud_score,
            'layer_symmetry': layer_score
        },
        'production_ready': overall_score >= 7
    }


def _generate_validation_report(
    self,
    template_path: Path,
    quality_scores: dict,
    placeholder_result: dict,
    pattern_result: dict,
    crud_result: dict,
    layer_result: dict
) -> None:
    """
    Generate validation-report.md in template directory.
    
    Args:
        template_path: Path to template
        quality_scores: Overall quality assessment
        placeholder_result: Placeholder validation results
        pattern_result: Pattern validation results
        crud_result: CRUD validation results
        layer_result: Layer validation results
    """
    from datetime import datetime
    
    report = f"""# Template Validation Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Template**: {template_path.name}
**Overall Score**: {quality_scores['overall_score']}/10 (Grade: {quality_scores['grade']})
**Production Ready**: {'✅ Yes' if quality_scores['production_ready'] else '❌ No'}

---

## Quality Scores

| Component | Score | Status |
|-----------|-------|--------|
| Placeholder Consistency | {quality_scores['component_scores']['placeholder_consistency']}/10 | {'✅' if quality_scores['component_scores']['placeholder_consistency'] >= 7 else '⚠️'} |
| Pattern Fidelity | {quality_scores['component_scores']['pattern_fidelity']}/10 | {'✅' if quality_scores['component_scores']['pattern_fidelity'] >= 7 else '⚠️'} |
| CRUD Completeness | {quality_scores['component_scores']['crud_completeness']}/10 | {'✅' if quality_scores['component_scores']['crud_completeness'] >= 7 else '⚠️'} |
| Layer Symmetry | {quality_scores['component_scores']['layer_symmetry']}/10 | {'✅' if quality_scores['component_scores']['layer_symmetry'] >= 7 else '⚠️'} |

---

## Detailed Findings

### Placeholder Consistency
"""
    
    if placeholder_result['issues']:
        report += "\n**Issues:**\n"
        for issue in placeholder_result['issues']:
            report += f"- ⚠️ {issue}\n"
    else:
        report += "✅ No issues detected\n"
    
    report += f"\n**Formats Found**: {', '.join(placeholder_result['formats_found']) if placeholder_result['formats_found'] else 'None'}\n"
    
    report += "\n### Pattern Fidelity\n"
    if pattern_result['issues']:
        report += "\n**Issues:**\n"
        for issue in pattern_result['issues']:
            report += f"- ⚠️ {issue}\n"
    else:
        report += "✅ No issues detected\n"
    
    report += f"\n**Pattern**: {pattern_result['pattern']}\n"
    
    report += "\n### CRUD Completeness\n"
    report += f"**Coverage**: {crud_result['coverage']:.0%} (threshold: {crud_result['threshold']:.0%})\n"
    report += f"**Covered Operations**: {', '.join(crud_result['covered_operations'])}\n"
    if crud_result['missing_operations']:
        report += f"**Missing Operations**: {', '.join(crud_result['missing_operations'])}\n"
    
    report += "\n### Layer Symmetry\n"
    report += f"**Symmetric**: {'✅ Yes' if layer_result['is_symmetric'] else '❌ No'}\n"
    report += f"**Found Layers**: {', '.join(layer_result['found_layers'])}\n"
    if layer_result['matched_pattern']:
        report += f"**Matched Pattern**: {', '.join(layer_result['matched_pattern'])}\n"
    if layer_result['issues']:
        report += "\n**Issues:**\n"
        for issue in layer_result['issues']:
            report += f"- ⚠️ {issue}\n"
    
    report += "\n---\n\n## Recommendations\n\n"
    
    if quality_scores['overall_score'] < 7:
        report += "⚠️ **Action Required**: Template quality below production threshold (7/10)\n\n"
    
    if placeholder_result['issues']:
        report += "1. **Placeholder Consistency**: Standardize on single placeholder format\n"
    if pattern_result['issues']:
        report += "2. **Pattern Fidelity**: Complete architectural pattern implementation\n"
    if not crud_result['passes']:
        report += "3. **CRUD Completeness**: Add missing CRUD operations\n"
    if not layer_result['is_symmetric']:
        report += "4. **Layer Symmetry**: Complete layer architecture\n"
    
    if quality_scores['production_ready']:
        report += "\n✅ **Template Ready**: Quality meets production standards\n"
    
    # Write report
    report_path = template_path / "validation-report.md"
    report_path.write_text(report)
    print(f"\n📄 Validation report saved: {report_path}")


def _run_level2_validation(
    self,
    template_path: Path,
    template_data: dict,
    level1_results: dict
) -> dict:
    """
    Run Level 2 extended validation.
    
    Port of template-create Phase 7.5 (TASK-043).
    
    Args:
        template_path: Path to generated template
        template_data: Template structure
        level1_results: Results from Level 1 validation
        
    Returns:
        dict with extended validation results and quality scores
    """
    print("Running extended validation...")
    
    # Extended checks
    placeholder_result = self._validate_placeholder_consistency(template_path)
    pattern_result = self._validate_pattern_fidelity(template_data)
    
    # Calculate overall quality
    quality_scores = self._calculate_overall_quality_score(
        placeholder_result,
        pattern_result,
        level1_results['crud_completeness'],
        level1_results['layer_symmetry']
    )
    
    # Generate report
    self._generate_validation_report(
        template_path,
        quality_scores,
        placeholder_result,
        pattern_result,
        level1_results['crud_completeness'],
        level1_results['layer_symmetry']
    )
    
    return {
        'quality_scores': quality_scores,
        'placeholder_consistency': placeholder_result,
        'pattern_fidelity': pattern_result
    }
```

**MODIFY run() method** (add Level 2 validation after save, around line 980):

```python
def run(self) -> Optional[GreenfieldAnswers]:
    """
    Run interactive Q&A session for greenfield template creation.
    
    NOW INCLUDES optional Level 2 extended validation.
    """
    # ... existing Phases 1-3.5 ...
    
    # Phase 4: Save Template
    template_path = self._save_template()
    
    # Optional Level 2 Extended Validation
    if self.validate:
        print("\n" + "=" * 70)
        print("  Level 2: Extended Validation")
        print("=" * 70 + "\n")
        
        level2_results = self._run_level2_validation(
            template_path,
            template_data,
            validation_result  # From Phase 3.5
        )
        
        # Display quality summary
        scores = level2_results['quality_scores']
        print(f"\n📊 Quality Assessment:")
        print(f"  Overall Score: {scores['overall_score']}/10 (Grade: {scores['grade']})")
        print(f"  Production Ready: {'✅ Yes' if scores['production_ready'] else '❌ No'}")
        
        # Return appropriate exit code
        if scores['overall_score'] >= 8:
            self._exit_code = 0
        elif scores['overall_score'] >= 6:
            self._exit_code = 1
        else:
            self._exit_code = 2
    
    return self.answers
```

## Scope Constraints

### ❌ DO NOT
- Make validation mandatory (keep optional with flag)
- Modify Level 1 validation logic
- Change report format beyond markdown
- Add external dependencies
- Block template creation on low scores

### ✅ DO ONLY
- Add `--validate` flag support
- Implement extended validation functions
- Generate markdown report in template directory
- Calculate quality scores (0-10)
- Set exit code based on quality

## Files to Modify

1. **installer/global/commands/lib/greenfield_qa_session.py** - MODIFY
   - `__init__()` constructor for `validate` flag (~5 lines)

2. **installer/global/commands/lib/greenfield_qa_session.py** - ADD
   - `_validate_placeholder_consistency()` (~40 lines)
   - `_validate_pattern_fidelity()` (~45 lines)
   - `_calculate_overall_quality_score()` (~45 lines)
   - `_generate_validation_report()` (~80 lines)
   - `_run_level2_validation()` (~30 lines)

3. **installer/global/commands/lib/greenfield_qa_session.py** - MODIFY
   - `run()` method to add Level 2 validation (~25 lines)

## Files to NOT Touch

- Level 1 validation functions (TASK-INIT-003)
- Template save logic
- Q&A workflow
- Agent generation

## Testing Requirements

### Unit Tests

```python
def test_validate_placeholder_consistency_single_format():
    """Test placeholder validation with consistent format."""
    session = TemplateInitQASession(validate=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "template"
        template_path.mkdir()
        
        # Create template file with consistent format
        (template_path / "config.template").write_text("name: {{project_name}}")
        (template_path / "readme.template").write_text("# {{title}}")
        
        result = session._validate_placeholder_consistency(template_path)
        
        assert result['score'] == 10
        assert len(result['issues']) == 0

def test_validate_pattern_fidelity_3tier():
    """Test pattern fidelity for 3-tier architecture."""
    session = TemplateInitQASession(validate=True)
    template_data = {
        'architecture_pattern': '3-tier',
        'layers': ['api', 'service', 'repository'],
        'agents': []
    }
    
    result = session._validate_pattern_fidelity(template_data)
    
    assert result['score'] == 10
    assert len(result['issues']) == 0

def test_calculate_overall_quality_score():
    """Test overall quality score calculation."""
    session = TemplateInitQASession(validate=True)
    
    quality_scores = session._calculate_overall_quality_score(
        {'score': 10},  # placeholder
        {'score': 10},  # pattern
        {'passes': True},  # crud
        {'is_symmetric': True}  # layer
    )
    
    assert quality_scores['overall_score'] >= 9
    assert quality_scores['grade'] in ['A', 'A+']
    assert quality_scores['production_ready'] is True
```

### Integration Tests

```python
def test_level2_validation_with_flag():
    """Test Level 2 validation runs when flag set."""
    session = TemplateInitQASession(validate=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "template"
        template_path.mkdir()
        
        template_data = {'architecture_pattern': '3-tier'}
        level1_results = {
            'crud_completeness': {'passes': True, 'coverage': 1.0},
            'layer_symmetry': {'is_symmetric': True}
        }
        
        level2_results = session._run_level2_validation(
            template_path,
            template_data,
            level1_results
        )
        
        assert 'quality_scores' in level2_results
        assert (template_path / "validation-report.md").exists()

def test_no_validation_without_flag():
    """Test validation skipped when flag not set."""
    session = TemplateInitQASession(validate=False)
    
    assert session.validate is False
```

## Acceptance Criteria

- [ ] `--validate` flag triggers extended validation
- [ ] Placeholder consistency checked
- [ ] Pattern fidelity validated
- [ ] Overall quality score calculated (0-10)
- [ ] Letter grade assigned (A-F)
- [ ] Production readiness determined (≥7/10)
- [ ] `validation-report.md` generated in template directory
- [ ] Report includes component scores and recommendations
- [ ] Exit code set based on quality score
- [ ] No impact when flag not used

## Estimated Effort

**4 hours** broken down as:
- Study template-create Phase 7.5 (30 minutes)
- Implement validation functions (1.5 hours)
- Implement quality scoring (1 hour)
- Implement report generation (30 minutes)
- Testing and validation (30 minutes)

## Dependencies

**TASK-INIT-003** - Requires Level 1 validation results

## Risk Assessment

### Risks

| Risk | Probability | Impact | Severity |
|------|------------|--------|-------------|
| Quality scoring too strict | Medium | Low | 🟡 Low |
| Report format not useful | Low | Low | 🟢 Minimal |
| Performance overhead | Low | Low | 🟢 Minimal |
| Users misinterpret scores | Medium | Low | 🟡 Low |

### Mitigation Strategies

1. **Scoring strictness**: Test with diverse templates, adjust thresholds based on feedback
2. **Report usefulness**: Include actionable recommendations, clear formatting
3. **Performance**: Extended validation only runs with --validate flag
4. **Score interpretation**: Clear production readiness threshold (7/10), explain grades

## References

- **Parent Review**: TASK-5E55
- **Source Feature**: TASK-043 (template-create Phase 7.5)
- **Related Tasks**: TASK-INIT-003 (Level 1), TASK-INIT-005 (Level 3)

## Success Metrics

When complete:
- ✅ Extended validation available via --validate flag
- ✅ Quality reports generated with actionable findings
- ✅ Exit codes support CI/CD integration
- ✅ Production readiness clearly indicated
- ✅ No performance impact without flag
