---
id: TASK-INIT-007
title: "Port two-location output support to /template-init"
status: backlog
created: 2025-11-26T07:30:00Z
updated: 2025-11-26T07:30:00Z
priority: high
tags: [template-init, distribution, week3, quality-output]
complexity: 3
estimated_hours: 4
parent_review: TASK-5E55
week: 3
phase: quality-output
related_tasks: []
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Port Two-Location Output Support to /template-init

## Problem Statement

`/template-init` only saves to personal location (`~/.agentecflow/templates/`) while `/template-create` supports both personal and repository locations, missing Critical Gap #10 from TASK-5E55.

**Impact**: Teams cannot save greenfield templates to repository location (`installer/global/templates/`) for sharing and distribution.

## Analysis Findings

From TASK-5E55 review:
- `/template-create` supports `--output-location global|repo` flag (TASK-068)
- `global`: Personal templates (~/.agentecflow/templates/)
- `repo`: Repository templates (installer/global/templates/)
- `/template-init` hardcoded to personal location only
- Gap severity: 🔴 **CRITICAL** (blocks team distribution)

**Current State**: Templates only saved to ~/.agentecflow/templates/

**Desired State**: Support both locations with --output-location flag

## Recommended Fix

**Approach**: Add `--output-location` flag to control save location.

**Strategy**:
- **MINIMAL SCOPE**: Add flag and path logic, don't change save mechanism
- **DEFAULT**: Keep `global` (personal) as default for backward compatibility
- **FLAG**: `--output-location repo` saves to installer/global/templates/
- **GUIDANCE**: Display location-specific usage instructions

## Code Changes Required

### File: installer/global/commands/lib/greenfield_qa_session.py

**MODIFY constructor** (around line 203):

```python
def __init__(self, validate: bool = False, output_location: str = 'global'):
    """
    Initialize Q&A session.

    Args:
        validate: Run extended validation (Level 2)
        output_location: Where to save template ('global' or 'repo')
    """
    if not INQUIRER_AVAILABLE:
        raise ImportError(
            "inquirer library not installed. "
            "Install with: pip install inquirer"
        )

    self.answers: Optional[GreenfieldAnswers] = None
    self._session_data: dict = {}
    self.validate = validate
    self.output_location = output_location  # NEW flag
```

**ADD path resolution method** (after line 850):

```python
def _get_template_path(self, template_name: str) -> Path:
    """
    Get template save path based on output location.

    Port of template-create two-location support (TASK-068).

    Args:
        template_name: Name of template

    Returns:
        Path to save template

    Example:
        >>> session = TemplateInitQASession(output_location='repo')
        >>> path = session._get_template_path('my-template')
        >>> 'installer/global/templates' in str(path)
        True
    """
    if self.output_location == 'repo':
        # Repository location for team distribution
        base_path = Path.cwd() / 'installer' / 'global' / 'templates'
    else:
        # Personal location (default)
        base_path = Path.home() / '.agentecflow' / 'templates'

    return base_path / template_name


def _display_location_guidance(self, template_path: Path) -> None:
    """
    Display location-specific usage guidance.

    Args:
        template_path: Where template was saved
    """
    print("\n" + "=" * 70)
    print("  Template Saved")
    print("=" * 70 + "\n")

    if self.output_location == 'repo':
        print(f"✅ Repository template: {template_path}")
        print()
        print("This template is now available for:")
        print("  • Team distribution (git commit)")
        print("  • Public sharing")
        print("  • Global discovery")
        print()
        print("Next steps:")
        print("  1. Review generated template")
        print("  2. Commit to repository: git add installer/global/templates/")
        print("  3. Share with team: git push")
        print()
        print("Usage:")
        print(f"  taskwright init {template_path.name}")
    else:
        print(f"✅ Personal template: {template_path}")
        print()
        print("This template is for:")
        print("  • Personal use")
        print("  • Local development")
        print("  • Experimentation")
        print()
        print("To share with team, create repository template:")
        print(f"  /template-init --output-location=repo")
        print()
        print("Usage:")
        print(f"  taskwright init {template_path.name}")
```

**MODIFY _save_template() method** (around line 920):

```python
def _save_template(self) -> Path:
    """
    Save template to appropriate location.

    NOW USES output_location to determine path.
    """
    template_name = self._session_data.get('template_name', 'unnamed-template')

    # Get path based on output location
    template_path = self._get_template_path(template_name)

    # Create directory
    template_path.mkdir(parents=True, exist_ok=True)

    # ... existing save logic ...

    return template_path
```

**MODIFY run() method** (add location guidance after save, around line 995):

```python
def run(self) -> Optional[GreenfieldAnswers]:
    """
    Run interactive Q&A session for greenfield template creation.

    NOW SUPPORTS two-location output.
    """
    # ... existing Phases 1-4 ...

    # Phase 4: Save Template
    template_path = self._save_template()

    # Display location-specific guidance
    self._display_location_guidance(template_path)

    # ... rest of workflow ...

    return self.answers
```

## Scope Constraints

### ❌ DO NOT
- Change template save mechanism
- Modify template file format
- Add location validation beyond path resolution
- Require repository location setup
- Change default location (keep personal)

### ✅ DO ONLY
- Add --output-location flag
- Implement path resolution (_get_template_path)
- Display location-specific guidance
- Ensure backward compatibility
- Document both options

## Files to Modify

1. **installer/global/commands/lib/greenfield_qa_session.py** - MODIFY
   - `__init__()` constructor for output_location flag (~3 lines)
   - `_save_template()` to use path resolution (~3 lines)

2. **installer/global/commands/lib/greenfield_qa_session.py** - ADD
   - `_get_template_path()` method (~20 lines)
   - `_display_location_guidance()` method (~45 lines)

3. **installer/global/commands/lib/greenfield_qa_session.py** - MODIFY
   - `run()` method to display guidance (~3 lines)

## Files to NOT Touch

- Template save logic (keep existing mechanism)
- Template file format
- Repository structure
- installer/global/templates/ directory

## Testing Requirements

### Unit Tests

```python
def test_get_template_path_global():
    """Test global location path resolution."""
    session = TemplateInitQASession(output_location='global')
    path = session._get_template_path('test-template')

    assert '.agentecflow/templates' in str(path)
    assert path.name == 'test-template'

def test_get_template_path_repo():
    """Test repo location path resolution."""
    session = TemplateInitQASession(output_location='repo')
    path = session._get_template_path('test-template')

    assert 'installer/global/templates' in str(path)
    assert path.name == 'test-template'

def test_default_location_is_global():
    """Test default output location."""
    session = TemplateInitQASession()

    assert session.output_location == 'global'
```

### Integration Tests

```python
def test_save_to_global_location():
    """Test template saves to personal location."""
    session = TemplateInitQASession(output_location='global')
    session._session_data = {'template_name': 'test'}

    with patch('pathlib.Path.mkdir'):
        path = session._save_template()

        assert '.agentecflow/templates' in str(path)

def test_save_to_repo_location():
    """Test template saves to repository location."""
    session = TemplateInitQASession(output_location='repo')
    session._session_data = {'template_name': 'test'}

    with patch('pathlib.Path.mkdir'):
        path = session._save_template()

        assert 'installer/global/templates' in str(path)
```

## Acceptance Criteria

- [ ] --output-location flag accepts 'global' and 'repo'
- [ ] Default location is 'global' (personal)
- [ ] 'global' saves to ~/.agentecflow/templates/
- [ ] 'repo' saves to installer/global/templates/
- [ ] Location-specific guidance displayed
- [ ] Backward compatible (default unchanged)
- [ ] Template save mechanism unchanged
- [ ] Both locations work with taskwright init

## Estimated Effort

**4 hours** broken down as:
- Study template-create two-location logic (30 minutes)
- Implement path resolution (1 hour)
- Implement location guidance (1 hour)
- Integrate into workflow (1 hour)
- Testing (30 minutes)

## Dependencies

**None** - Independent feature (Week 3, Quality Output)

## Risk Assessment

### Risks

| Risk | Probability | Impact | Severity |
|------|------------|--------|----------|
| Path resolution errors | Low | Medium | 🟡 Low |
| Repository location not writable | Medium | Low | 🟡 Low |
| Users confused by two options | Low | Low | 🟢 Minimal |

### Mitigation Strategies

1. **Path errors**: Use Path.mkdir(parents=True, exist_ok=True) for robust creation
2. **Write permissions**: Clear error message if repository location not writable
3. **Option clarity**: Display clear guidance explaining each location's purpose

## References

- **Parent Review**: TASK-5E55
- **Source Feature**: TASK-068 (template-create two-location support)
- **Template Locations**:
  - Personal: ~/.agentecflow/templates/
  - Repository: installer/global/templates/

## Success Metrics

When complete:
- ✅ Both output locations supported
- ✅ Default remains personal (backward compatible)
- ✅ Teams can create repository templates
- ✅ Clear guidance for each location
- ✅ No breaking changes to existing workflows
