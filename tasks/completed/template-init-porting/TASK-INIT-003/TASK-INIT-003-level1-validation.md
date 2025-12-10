---
id: TASK-INIT-003
title: Port Level 1 automatic validation to /template-init
status: completed
created: 2025-11-26 07:30:00+00:00
updated: '2025-11-26T11:14:13.101409Z'
priority: medium
tags:
- template-init
- validation
- week2
- quality-infrastructure
complexity: 4
estimated_hours: 4
parent_review: TASK-5E55
week: 2
phase: validation-framework
related_tasks:
- TASK-INIT-004
- TASK-INIT-005
dependencies: []
test_results:
  status: passed
  coverage: '>90%'
  last_run: '2025-11-26T11:14:13.101410Z'
completed: '2025-11-26T11:14:13.101290Z'
---

# Task: Port Level 1 Automatic Validation to /template-init

## Problem Statement

`/template-init` generates templates without automatic validation (CRUD completeness, layer symmetry), missing Critical Gap #6 from TASK-5E55. Templates may have architectural issues that go undetected until runtime.

**Impact**: Users create templates with missing CRUD operations or asymmetric layers, reducing template quality and requiring manual discovery of issues.

## Analysis Findings

From TASK-5E55 review:
- `/template-create` Phase 4.5: Automatic completeness validation (TASK-040)
- Checks CRUD coverage (60% threshold)
- Validates layer symmetry
- Provides auto-fix recommendations
- Warnings don't block creation
- `/template-init` has NO validation phase
- Gap severity: 🔴 **CRITICAL**

**Current State**: Templates generated without quality checks.

**Desired State**: Automatic validation after generation, before save, with actionable feedback.

## Recommended Fix

**Approach**: Add validation phase between agent generation (Phase 3) and save (Phase 4).

**Strategy**:
- **MINIMAL SCOPE**: Add validation as new phase, don't modify existing phases
- **REUSE**: Copy validation logic from `/template-create` Phase 4.5
- **NON-BLOCKING**: Display warnings, don't prevent template creation
- **ACTIONABLE**: Provide specific recommendations for fixes

## Code Changes Required

### File 1: installer/core/commands/lib/greenfield_qa_session.py

**ADD new validation functions** (after line 430):

```python
def _validate_crud_completeness(self, template_data: dict) -> dict:
    """
    Validate CRUD operation coverage.
    
    Port of template-create Phase 4.5 validation (TASK-040).
    
    Args:
        template_data: Template structure with agents and layers
        
    Returns:
        dict with coverage metrics and recommendations
        
    Example:
        >>> result = session._validate_crud_completeness(template_data)
        >>> result['crud_coverage']
        0.75
    """
    crud_operations = {'create', 'read', 'update', 'delete'}
    covered_operations = set()
    
    # Check agent capabilities for CRUD coverage
    agents = template_data.get('agents', [])
    for agent in agents:
        agent_name = agent.get('name', '').lower()
        capabilities = agent.get('capabilities', [])
        
        # Map agent types to CRUD operations
        if 'create' in agent_name or 'post' in capabilities:
            covered_operations.add('create')
        if 'read' in agent_name or 'get' in capabilities or 'list' in capabilities:
            covered_operations.add('read')
        if 'update' in agent_name or 'put' in capabilities or 'patch' in capabilities:
            covered_operations.add('update')
        if 'delete' in agent_name or 'remove' in capabilities:
            covered_operations.add('delete')
    
    coverage = len(covered_operations) / len(crud_operations)
    missing_operations = crud_operations - covered_operations
    
    return {
        'coverage': coverage,
        'covered_operations': list(covered_operations),
        'missing_operations': list(missing_operations),
        'threshold': 0.60,
        'passes': coverage >= 0.60
    }


def _validate_layer_symmetry(self, template_data: dict) -> dict:
    """
    Validate architectural layer symmetry.
    
    Port of template-create Phase 4.5 validation (TASK-040).
    
    Args:
        template_data: Template structure with layers
        
    Returns:
        dict with symmetry analysis and issues
        
    Example:
        >>> result = session._validate_layer_symmetry(template_data)
        >>> result['is_symmetric']
        True
    """
    layers = template_data.get('layers', [])
    
    # Common layer patterns (should appear together)
    layer_patterns = [
        {'api', 'service', 'repository'},  # 3-tier
        {'controller', 'service', 'data'},  # MVC
        {'presentation', 'business', 'data'},  # Classic 3-layer
    ]
    
    found_layers = {layer.lower() for layer in layers}
    issues = []
    matched_pattern = None
    
    # Check if layers match a known pattern
    for pattern in layer_patterns:
        if pattern.issubset(found_layers):
            matched_pattern = pattern
            break
        elif len(pattern & found_layers) > 0:
            # Partial match - missing layers
            missing = pattern - found_layers
            issues.append(f"Incomplete pattern: missing {missing}")
    
    # Check for orphan layers (no matching pattern)
    if not matched_pattern and len(found_layers) > 0:
        issues.append("No recognized architectural pattern detected")
    
    return {
        'is_symmetric': len(issues) == 0,
        'matched_pattern': list(matched_pattern) if matched_pattern else None,
        'found_layers': list(found_layers),
        'issues': issues
    }


def _generate_autofix_recommendations(
    self, 
    crud_result: dict, 
    layer_result: dict
) -> list:
    """
    Generate actionable auto-fix recommendations.
    
    Args:
        crud_result: CRUD completeness validation result
        layer_result: Layer symmetry validation result
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # CRUD recommendations
    if not crud_result['passes']:
        missing = crud_result['missing_operations']
        recommendations.append(
            f"⚠️ CRUD coverage {crud_result['coverage']:.0%} (threshold: 60%). "
            f"Consider adding agents for: {', '.join(missing)}"
        )
    
    # Layer symmetry recommendations
    if not layer_result['is_symmetric']:
        for issue in layer_result['issues']:
            recommendations.append(f"⚠️ Layer symmetry: {issue}")
    
    return recommendations


def _run_level1_validation(self, template_data: dict) -> dict:
    """
    Run Level 1 automatic validation.
    
    Port of template-create Phase 4.5 (TASK-040).
    
    Args:
        template_data: Complete template structure
        
    Returns:
        dict with validation results and recommendations
    """
    crud_result = self._validate_crud_completeness(template_data)
    layer_result = self._validate_layer_symmetry(template_data)
    recommendations = self._generate_autofix_recommendations(
        crud_result, 
        layer_result
    )
    
    return {
        'crud_completeness': crud_result,
        'layer_symmetry': layer_result,
        'recommendations': recommendations,
        'overall_pass': crud_result['passes'] and layer_result['is_symmetric']
    }
```

**MODIFY run() method** (add Phase 3.5 validation around line 950):

```python
def run(self) -> Optional[GreenfieldAnswers]:
    """
    Run interactive Q&A session for greenfield template creation.
    
    NOW INCLUDES Phase 3.5: Automatic validation.
    """
    # ... existing Phases 1-3 ...
    
    # Phase 3: Generate agents
    agents = self._generate_agents()
    
    # NEW Phase 3.5: Level 1 Automatic Validation
    print("\n" + "=" * 70)
    print("  Phase 3.5: Template Validation")
    print("=" * 70 + "\n")
    
    template_data = {
        'agents': agents,
        'layers': self._session_data.get('layers', []),
        'architecture_pattern': self._session_data.get('architecture_pattern', 'unknown')
    }
    
    validation_result = self._run_level1_validation(template_data)
    
    # Display validation results
    if validation_result['overall_pass']:
        print("✅ Validation passed")
    else:
        print("⚠️ Validation warnings detected (template creation will proceed):\n")
        
        # CRUD completeness
        crud = validation_result['crud_completeness']
        print(f"  CRUD Coverage: {crud['coverage']:.0%} (threshold: {crud['threshold']:.0%})")
        if crud['missing_operations']:
            print(f"    Missing: {', '.join(crud['missing_operations'])}")
        
        # Layer symmetry
        layer = validation_result['layer_symmetry']
        if not layer['is_symmetric']:
            print(f"  Layer Symmetry: Issues detected")
            for issue in layer['issues']:
                print(f"    - {issue}")
        
        # Recommendations
        print("\n  Recommendations:")
        for rec in validation_result['recommendations']:
            print(f"    {rec}")
    
    # Phase 4: Save Template (continues regardless of warnings)
    # ... existing save logic ...
    
    return self.answers
```

## Scope Constraints

### ❌ DO NOT
- Modify Phases 1-3 (Q&A and agent generation work fine)
- Block template creation on validation failures
- Add complex validation rules beyond CRUD/layer symmetry
- Require external validation tools
- Change template file format

### ✅ DO ONLY
- Add Level 1 validation functions (CRUD, layer symmetry)
- Insert Phase 3.5 after agent generation
- Display warnings and recommendations
- Allow template creation to proceed regardless
- Reuse validation logic from template-create

## Files to Modify

1. **installer/core/commands/lib/greenfield_qa_session.py** - ADD
   - `_validate_crud_completeness()` method (~40 lines)
   - `_validate_layer_symmetry()` method (~40 lines)
   - `_generate_autofix_recommendations()` method (~20 lines)
   - `_run_level1_validation()` method (~20 lines)

2. **installer/core/commands/lib/greenfield_qa_session.py** - MODIFY
   - `run()` method to add Phase 3.5 (~30 lines)

## Files to NOT Touch

- Phases 1-3 logic - Working correctly
- Template save logic (Phase 4) - Keep unchanged
- Any validation configuration files - Keep simple

## Testing Requirements

### Unit Tests

```python
def test_validate_crud_completeness_full_coverage():
    """Test CRUD validation with full coverage."""
    session = TemplateInitQASession()
    template_data = {
        'agents': [
            {'name': 'create-agent', 'capabilities': ['post']},
            {'name': 'read-agent', 'capabilities': ['get']},
            {'name': 'update-agent', 'capabilities': ['put']},
            {'name': 'delete-agent', 'capabilities': ['delete']}
        ]
    }
    
    result = session._validate_crud_completeness(template_data)
    
    assert result['coverage'] == 1.0
    assert result['passes'] is True
    assert len(result['missing_operations']) == 0

def test_validate_crud_completeness_partial():
    """Test CRUD validation with partial coverage."""
    session = TemplateInitQASession()
    template_data = {
        'agents': [
            {'name': 'read-agent', 'capabilities': ['get']},
        ]
    }
    
    result = session._validate_crud_completeness(template_data)
    
    assert result['coverage'] == 0.25
    assert result['passes'] is False
    assert 'create' in result['missing_operations']

def test_validate_layer_symmetry_3tier():
    """Test layer symmetry validation for 3-tier."""
    session = TemplateInitQASession()
    template_data = {
        'layers': ['api', 'service', 'repository']
    }
    
    result = session._validate_layer_symmetry(template_data)
    
    assert result['is_symmetric'] is True
    assert result['matched_pattern'] == ['api', 'service', 'repository']

def test_validate_layer_symmetry_incomplete():
    """Test layer symmetry with incomplete pattern."""
    session = TemplateInitQASession()
    template_data = {
        'layers': ['api', 'service']  # Missing repository
    }
    
    result = session._validate_layer_symmetry(template_data)
    
    assert result['is_symmetric'] is False
    assert len(result['issues']) > 0
```

### Integration Tests

```python
def test_phase35_validation_runs_after_generation():
    """Test Phase 3.5 runs after agent generation."""
    session = TemplateInitQASession()
    session._session_data = {
        'template_name': 'test',
        'architecture_pattern': '3-tier',
        'layers': ['api', 'service', 'repository']
    }
    
    with patch.object(session, '_generate_agents') as mock_gen:
        mock_gen.return_value = [
            {'name': 'test-agent', 'capabilities': ['read']}
        ]
        
        with patch.object(session, '_run_level1_validation') as mock_val:
            mock_val.return_value = {
                'overall_pass': True,
                'recommendations': []
            }
            
            session.run()
            
            assert mock_val.called
```

## Acceptance Criteria

- [ ] `_validate_crud_completeness()` checks CRUD coverage
- [ ] CRUD threshold set to 60%
- [ ] `_validate_layer_symmetry()` validates layer patterns
- [ ] Recognizes 3 common patterns (3-tier, MVC, classic)
- [ ] Auto-fix recommendations generated
- [ ] Phase 3.5 runs after agent generation
- [ ] Validation warnings displayed clearly
- [ ] Template creation proceeds regardless of warnings
- [ ] No regressions in existing Q&A workflow
- [ ] Unit tests achieve 90%+ coverage

## Estimated Effort

**4 hours** broken down as:
- Study template-create Phase 4.5 validation (30 minutes)
- Implement CRUD validation (1 hour)
- Implement layer symmetry validation (1 hour)
- Integrate Phase 3.5 into run() (1 hour)
- Testing and validation (30 minutes)

## Dependencies

**None** - Independent task (Week 2, Validation Framework)

## Risk Assessment

### Risks

| Risk | Probability | Impact | Severity |
|------|------------|--------|----------|
| False positives in CRUD detection | Medium | Low | 🟡 Low |
| Layer patterns too restrictive | Low | Low | 🟢 Minimal |
| Validation slows down creation | Low | Low | 🟢 Minimal |
| Users ignore warnings | Medium | Low | 🟡 Low |

### Mitigation Strategies

1. **CRUD detection accuracy**: Use multiple heuristics (agent name, capabilities), prefer false negatives to false positives
2. **Layer patterns**: Support 3 common patterns, graceful degradation for unknown patterns
3. **Performance**: Validation is simple checks on in-memory data, <1 second overhead
4. **Warning visibility**: Clear formatting with emoji and actionable recommendations

## References

- **Parent Review**: TASK-5E55
- **Source Feature**: TASK-040 (template-create Phase 4.5 validation)
- **Related Tasks**: TASK-INIT-004 (Level 2), TASK-INIT-005 (Level 3)

## Success Metrics

When complete:
- ✅ 100% of templates receive automatic validation
- ✅ CRUD coverage calculated accurately
- ✅ Layer symmetry issues detected
- ✅ Actionable recommendations provided
- ✅ Template creation never blocked by warnings
