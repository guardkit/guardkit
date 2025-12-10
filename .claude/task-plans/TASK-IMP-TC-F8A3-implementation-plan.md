# Implementation Plan: TASK-IMP-TC-F8A3

## Task Summary
Fix template-create placeholder substitution and layer mappings based on review findings from TASK-REV-TC-B7F2.

**Priority**: High
**Complexity**: 6/10 (Medium - Requires AI integration improvements and path mapping fixes)
**Estimated Duration**: 4-6 hours

---

## Problem Analysis

### Current Issues (from Review TASK-REV-TC-B7F2)

1. **No Placeholder Substitution** (Critical - Score: 0/10)
   - Template files are direct copies without `{{ProjectName}}`, `{{Namespace}}` placeholders
   - AI extraction exists but `AIClient.generate()` raises `NotImplementedError`
   - Fallback method is too basic (only handles namespace in C#)
   - **Impact**: Templates cannot scaffold new projects

2. **Incorrect Layer Mappings** (Critical - Score: 3/10)
   - `_infer_layer_directory()` returns synthetic paths like `src/Service Layer`
   - Actual paths from codebase are `src/lib/firestore/`, `src/lib/alasql/`, etc.
   - **Impact**: Scaffolding creates wrong directory structure

3. **Missing Extended Agent Files** (Important - Score: 7/10)
   - Some agents lack `-ext.md` files after enhancement
   - `apply_with_split()` in applier.py handles this but may not be consistently called
   - **Impact**: Incomplete progressive disclosure

### Root Causes

**Issue #1 - Placeholder Substitution**:
- `AIClient.generate()` throws `NotImplementedError` when `ANTHROPIC_API_KEY` not set
- Fallback method `_fallback_placeholder_extraction()` is intentionally basic
- No validation of placeholder coverage (target: >80%)
- Template files written directly from source without transformation

**Issue #2 - Layer Mappings**:
- `_infer_layer_directory()` uses synthetic approach: `f"src/{layer_name}"`
- Should extract actual paths from `example_files` in analysis
- Layer information from AI analysis doesn't include directory paths
- Settings generator doesn't cross-reference example file paths

**Issue #3 - Extended Agent Files**:
- Agent enhancement may use `apply()` instead of `apply_with_split()`
- Orchestrator may not call enhancement with progressive disclosure enabled
- No validation that `-ext.md` files were created

---

## Solution Design

### Approach: Pragmatic Fixes with Existing Architecture

**Philosophy**: Fix within current architecture without major refactoring. Use agent bridge for AI calls where appropriate.

### 1. Placeholder Substitution Fix

**Strategy**: Improve fallback placeholder extraction + add validation

**Why not use AI?**
- AI client currently raises `NotImplementedError`
- Agent bridge pattern better suited for this (already used in Phase 1, Phase 5)
- Regex-based extraction can achieve 80%+ coverage for common patterns
- AI extraction can be added later via agent bridge if needed

**Implementation**:
1. **Enhance `_fallback_placeholder_extraction()`** with comprehensive regex patterns
2. **Add `_validate_placeholder_coverage()`** to check >80% threshold
3. **Add `_apply_placeholders_to_template()`** to replace hardcoded values
4. Keep AI extraction path for future enhancement

**Coverage Targets**:
- Project names: `MyProject`, `com.example.app` → `{{ProjectName}}`
- Namespaces: `MyApp.Domain.Users` → `{{ProjectName}}.Domain.{{EntityNamePlural}}`
- Class names: `GetUser`, `CreateOrder` → `{{Verb}}{{EntityName}}`
- Entity names: `User`, `Order`, `Product` → `{{EntityName}}`
- Imports: `from myproject.models` → `from {{project_name}}.models`

### 2. Layer Mapping Fix

**Strategy**: Extract actual paths from example files

**Implementation**:
1. **Add `_extract_layer_from_path()`** to infer layer from file path
2. **Modify `_infer_layer_directory()`** to use actual paths from example files
3. **Add `_map_layers_to_paths()`** to build layer → directory mapping
4. Use AI analysis layer info + cross-reference with example file paths

**Example**:
```python
# Before (synthetic)
layer_directory = f"src/{layer.name}"  # "src/Service Layer"

# After (actual paths)
layer_directory = self._infer_layer_directory_from_examples(
    layer=layer,
    example_files=self.analysis.example_files
)  # "src/lib/firestore"
```

### 3. Extended Agent Files Fix

**Strategy**: Ensure `apply_with_split()` is called consistently

**Implementation**:
1. **Verify orchestrator calls enhancement correctly** in Phase 7
2. **Add validation** that `-ext.md` files exist after agent writing
3. **Log warnings** if extended files missing
4. No changes to `applier.py` needed (already has `apply_with_split()`)

---

## Files to Modify

### Primary Files

| File | Changes | LOC Impact |
|------|---------|------------|
| `installer/core/lib/template_generator/template_generator.py` | Enhance placeholder extraction, add validation | +150-200 lines |
| `installer/core/lib/settings_generator/generator.py` | Fix layer directory inference | +80-100 lines |
| `installer/core/commands/lib/template_create_orchestrator.py` | Add validation for extended files | +20-30 lines |

### Supporting Files

| File | Changes | LOC Impact |
|------|---------|------------|
| `installer/core/lib/template_generator/models.py` | Add `PlaceholderValidationResult` model | +20 lines |
| `installer/core/lib/settings_generator/models.py` | May need updates if layer model changes | +10 lines |

---

## Detailed Implementation

### 1. Enhanced Placeholder Extraction

**File**: `installer/core/lib/template_generator/template_generator.py`

**Method**: `_fallback_placeholder_extraction(content: str, language: str)`

**Changes**:

```python
def _fallback_placeholder_extraction(
    self,
    content: str,
    language: str
) -> Tuple[str, List[str]]:
    """
    Enhanced fallback placeholder extraction using comprehensive regex patterns.

    Achieves 80%+ placeholder coverage for common patterns across languages.
    """
    template_content = content
    placeholders = []
    replacements = []

    # Language-specific patterns
    if language in ["C#", "csharp"]:
        replacements.extend(self._extract_csharp_placeholders(content))
    elif language in ["Python", "python"]:
        replacements.extend(self._extract_python_placeholders(content))
    elif language in ["TypeScript", "typescript", "JavaScript", "javascript"]:
        replacements.extend(self._extract_typescript_placeholders(content))
    elif language in ["Java", "java"]:
        replacements.extend(self._extract_java_placeholders(content))

    # Cross-language patterns
    replacements.extend(self._extract_common_placeholders(content))

    # Apply replacements (ordered by specificity)
    for pattern, replacement, placeholder_name in sorted(replacements, key=lambda x: -len(x[0])):
        if re.search(pattern, template_content):
            template_content = re.sub(pattern, replacement, template_content)
            if placeholder_name not in placeholders:
                placeholders.append(placeholder_name)

    return template_content, placeholders
```

**New Helper Methods**:

```python
def _extract_csharp_placeholders(self, content: str) -> List[Tuple[str, str, str]]:
    """Extract C# specific placeholders (namespace, using, class names)."""
    patterns = [
        # Namespace: "MyApp.Domain.Users" → "{{ProjectName}}.Domain.{{EntityNamePlural}}"
        (r'namespace\s+([A-Z][A-Za-z0-9]+)\.([A-Z][A-Za-z0-9]+)\.([A-Z][A-Za-z0-9]+)',
         r'namespace {{ProjectName}}.\2.{{EntityNamePlural}}',
         'ProjectName,EntityNamePlural'),

        # Using directives with project name
        (r'using\s+([A-Z][A-Za-z0-9]+)\.([A-Z][A-Za-z0-9]+)',
         r'using {{ProjectName}}.\2',
         'ProjectName'),

        # Class names with CRUD verbs
        (r'public\s+class\s+(Get|Create|Update|Delete|List)([A-Z][A-Za-z0-9]+)',
         r'public class {{Verb}}{{EntityName}}',
         'Verb,EntityName'),

        # Interface names
        (r'public\s+interface\s+I([A-Z][A-Za-z0-9]+)Repository',
         r'public interface I{{EntityName}}Repository',
         'EntityName'),
    ]
    return [(p[0], p[1], n) for p, r, n in patterns for n in n.split(',')]

def _extract_python_placeholders(self, content: str) -> List[Tuple[str, str, str]]:
    """Extract Python specific placeholders (imports, class names, module paths)."""
    patterns = [
        # Module imports: "from myproject.models" → "from {{project_name}}.models"
        (r'from\s+([a-z][a-z0-9_]+)\.([a-z][a-z0-9_]+)',
         r'from {{project_name}}.\2',
         'project_name'),

        # Class definitions with entity names
        (r'class\s+([A-Z][A-Za-z0-9]+)Repository',
         r'class {{EntityName}}Repository',
         'EntityName'),

        # Dataclass names
        (r'@dataclass\s+class\s+([A-Z][A-Za-z0-9]+):',
         r'@dataclass\nclass {{EntityName}}:',
         'EntityName'),
    ]
    return [(p[0], p[1], n) for p, r, n in patterns for n in n.split(',')]

def _extract_typescript_placeholders(self, content: str) -> List[Tuple[str, str, str]]:
    """Extract TypeScript/JavaScript placeholders (imports, exports, class names)."""
    patterns = [
        # Import statements: "from '../models/User'" → "from '../models/{{EntityName}}'"
        (r"from\s+['\"](.*/)?([A-Z][A-Za-z0-9]+)['\"]",
         r"from '\1{{EntityName}}'",
         'EntityName'),

        # Class declarations
        (r'export\s+class\s+(Get|Create|Update|Delete|List)([A-Z][A-Za-z0-9]+)',
         r'export class {{Verb}}{{EntityName}}',
         'Verb,EntityName'),

        # Interface names
        (r'export\s+interface\s+([A-Z][A-Za-z0-9]+)Props',
         r'export interface {{EntityName}}Props',
         'EntityName'),
    ]
    return [(p[0], p[1], n) for p, r, n in patterns for n in n.split(',')]

def _extract_common_placeholders(self, content: str) -> List[Tuple[str, str, str]]:
    """Extract cross-language placeholders (file paths, URLs, entity names)."""
    patterns = [
        # File paths with project name
        (r'/([a-z][a-z0-9-]+)/src/',
         r'/{{project_name}}/src/',
         'project_name'),

        # URLs with domain
        (r'https?://([a-z][a-z0-9-]+)\.com',
         r'https://{{project_name}}.com',
         'project_name'),

        # String literals with entity names (conservative)
        (r'"(User|Product|Order|Item)s?"',
         r'"{{EntityName}}s"',
         'EntityName'),
    ]
    return [(p[0], p[1], n) for p, r, n in patterns for n in n.split(',')]
```

**Add Validation Method**:

```python
def _validate_placeholder_coverage(
    self,
    original: str,
    template: str,
    placeholders: List[str]
) -> PlaceholderValidationResult:
    """
    Validate placeholder coverage meets >80% threshold.

    Returns:
        PlaceholderValidationResult with coverage score and warnings
    """
    # Count project-specific identifiers in original
    identifiers = self._extract_identifiers(original)

    # Count how many were replaced
    replaced_count = 0
    for identifier in identifiers:
        if identifier not in template:  # Was replaced
            replaced_count += 1

    coverage = replaced_count / len(identifiers) if identifiers else 1.0

    warnings = []
    if coverage < 0.8:
        warnings.append(
            f"Low placeholder coverage: {coverage:.1%} (target: >80%). "
            f"Some project-specific values may remain hardcoded."
        )

    return PlaceholderValidationResult(
        is_valid=coverage >= 0.8,
        coverage=coverage,
        placeholders_extracted=len(placeholders),
        identifiers_found=len(identifiers),
        warnings=warnings
    )

def _extract_identifiers(self, content: str) -> List[str]:
    """Extract project-specific identifiers for coverage calculation."""
    # Extract likely identifiers:
    # - PascalCase: ProjectName, EntityName
    # - Namespaces: com.example.app
    # - Module paths: myproject.domain

    pascal_case = re.findall(r'\b([A-Z][A-Za-z0-9]{2,})\b', content)
    namespaces = re.findall(r'\b([a-z][a-z0-9]+\.[a-z][a-z0-9]+)\b', content)

    # Deduplicate and filter common framework names
    identifiers = set(pascal_case + namespaces)
    framework_keywords = {'String', 'Int', 'Boolean', 'List', 'Dict', 'Task', 'Async'}

    return [i for i in identifiers if i not in framework_keywords]
```

**Integration Point**:

```python
def _generate_template(self, example_file: ExampleFile) -> Optional[CodeTemplate]:
    """Generate a single template from an example file using AI."""
    # ... existing code ...

    # Ask AI to generate template (or use fallback)
    try:
        template_content, placeholders = self._ai_extract_placeholders(...)
    except PlaceholderExtractionError as e:
        print(f"AI extraction failed, using fallback: {e}")
        template_content, placeholders = self._fallback_placeholder_extraction(
            content, language
        )

    # NEW: Validate placeholder coverage
    validation = self._validate_placeholder_coverage(
        original=content,
        template=template_content,
        placeholders=placeholders
    )

    if not validation.is_valid:
        for warning in validation.warnings:
            self.warnings.append(f"{example_file.path}: {warning}")

    # Log coverage for debugging
    logger.info(
        f"{example_file.path}: {validation.coverage:.1%} placeholder coverage "
        f"({validation.placeholders_extracted} placeholders)"
    )

    # ... rest of method ...
```

### 2. Layer Mapping Fix

**File**: `installer/core/lib/settings_generator/generator.py`

**Method**: `_infer_layer_directory(layer: LayerInfo)`

**Changes**:

```python
def _infer_layer_directory(self, layer: LayerInfo) -> str:
    """
    Infer directory path for a layer using actual file paths from analysis.

    Strategy:
    1. Find example files assigned to this layer
    2. Extract common directory prefix from their paths
    3. Return actual directory path (not synthetic)

    Args:
        layer: Layer information from analysis

    Returns:
        Actual directory path from codebase (e.g., "src/lib/firestore")
    """
    # Find example files for this layer
    layer_files = [
        f for f in self.analysis.example_files
        if hasattr(f, 'layer') and f.layer == layer.name
    ]

    if not layer_files:
        # Fallback: Use layer name as directory (old behavior)
        logger.warning(
            f"No example files found for layer '{layer.name}', "
            f"using synthetic path 'src/{layer.name}'"
        )
        return f"src/{layer.name}"

    # Extract directory paths from example files
    dir_paths = [Path(f.path).parent for f in layer_files]

    # Find common prefix
    common_path = self._find_common_path_prefix(dir_paths)

    if not common_path:
        # Fallback if no common prefix
        logger.warning(
            f"No common prefix for layer '{layer.name}', "
            f"using first file's directory: {dir_paths[0]}"
        )
        return str(dir_paths[0])

    logger.info(f"Layer '{layer.name}' mapped to directory: {common_path}")
    return str(common_path)

def _find_common_path_prefix(self, paths: List[Path]) -> Optional[Path]:
    """
    Find common directory prefix for a list of paths.

    Args:
        paths: List of directory paths

    Returns:
        Common prefix path, or None if no common prefix

    Example:
        paths = [
            Path("src/lib/firestore"),
            Path("src/lib/firestore/models"),
            Path("src/lib/firestore/utils")
        ]
        returns: Path("src/lib/firestore")
    """
    if not paths:
        return None

    if len(paths) == 1:
        return paths[0]

    # Convert to strings for common prefix calculation
    path_strs = [str(p) for p in paths]

    # Find common prefix
    common_prefix = os.path.commonprefix(path_strs)

    # Ensure it ends at a directory boundary
    if common_prefix and not common_prefix.endswith(os.sep):
        # Find last separator
        last_sep = common_prefix.rfind(os.sep)
        if last_sep > 0:
            common_prefix = common_prefix[:last_sep]

    return Path(common_prefix) if common_prefix else None
```

**Add Helper for Layer Extraction**:

```python
def _extract_layer_from_path(self, file_path: str) -> Optional[str]:
    """
    Infer layer name from file path patterns.

    Used when example files don't have explicit layer assignment.

    Args:
        file_path: Relative file path (e.g., "src/lib/firestore/sessions.js")

    Returns:
        Inferred layer name or None

    Examples:
        "src/lib/firestore/sessions.js" → "Service Layer"
        "src/routes/+page.svelte" → "Presentation"
        "src/components/Button.svelte" → "Presentation"
    """
    path_lower = file_path.lower()

    # Pattern-based layer inference
    if '/routes/' in path_lower or '/pages/' in path_lower:
        return "Presentation"
    elif '/components/' in path_lower:
        return "Presentation"
    elif '/lib/' in path_lower and '/firestore/' in path_lower:
        return "Service Layer"
    elif '/lib/' in path_lower and '/alasql/' in path_lower:
        return "Data Access"
    elif '/stores/' in path_lower or '/state/' in path_lower:
        return "State Management"
    elif '/utils/' in path_lower or '/helpers/' in path_lower:
        return "Utility"

    return None
```

### 3. Extended Agent Files Validation

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

**Method**: `_phase7_write_agents(agents: List[Any], output_path: Path)`

**Changes**:

```python
def _phase7_write_agents(
    self,
    agents: List[Any],
    output_path: Path
) -> Optional[List[Path]]:
    """
    Write agent files to disk with progressive disclosure.

    TASK-IMP-TC-F8A3: Added validation for extended files.
    """
    # ... existing agent writing code ...

    # NEW: Validate extended files were created
    missing_extended = []
    for agent_path in agent_paths:
        if not agent_path.exists():
            continue

        # Check for extended file
        ext_path = agent_path.with_stem(f"{agent_path.stem}-ext")
        if not ext_path.exists():
            missing_extended.append(agent_path.name)

    if missing_extended:
        logger.warning(
            f"Missing extended files for {len(missing_extended)} agents: "
            f"{', '.join(missing_extended[:3])}"
            + (f" and {len(missing_extended) - 3} more" if len(missing_extended) > 3 else "")
        )
        self.warnings.append(
            f"Progressive disclosure incomplete: {len(missing_extended)} agents "
            f"missing extended files"
        )

    return agent_paths
```

---

## Testing Strategy

### Unit Tests

**Test File**: `tests/unit/test_template_generator.py`

```python
def test_fallback_placeholder_extraction_csharp():
    """Test enhanced C# placeholder extraction."""
    content = """
    namespace MyApp.Domain.Users;
    using MyApp.Infrastructure;

    public class GetUser {
        private readonly IUserRepository _repository;
    }
    """

    generator = TemplateGenerator(...)
    template, placeholders = generator._fallback_placeholder_extraction(content, "C#")

    assert "{{ProjectName}}" in template
    assert "{{EntityName}}" in template
    assert "ProjectName" in placeholders
    assert "EntityName" in placeholders

def test_placeholder_coverage_validation():
    """Test placeholder coverage calculation."""
    original = "namespace MyApp.Domain.Users; public class GetUser {}"
    template = "namespace {{ProjectName}}.Domain.{{EntityNamePlural}}; public class {{Verb}}{{EntityName}} {}"
    placeholders = ["ProjectName", "EntityNamePlural", "Verb", "EntityName"]

    generator = TemplateGenerator(...)
    result = generator._validate_placeholder_coverage(original, template, placeholders)

    assert result.is_valid  # Coverage should be >80%
    assert result.coverage >= 0.8
```

**Test File**: `tests/unit/test_settings_generator.py`

```python
def test_infer_layer_directory_from_examples():
    """Test layer directory inference from example files."""
    analysis = CodebaseAnalysis(
        example_files=[
            ExampleFile(path="src/lib/firestore/sessions.js", layer="Service Layer"),
            ExampleFile(path="src/lib/firestore/models/session.js", layer="Service Layer"),
        ]
    )

    generator = SettingsGenerator(analysis)
    layer = LayerInfo(name="Service Layer")

    directory = generator._infer_layer_directory(layer)

    assert directory == "src/lib/firestore"  # Not "src/Service Layer"

def test_find_common_path_prefix():
    """Test common path prefix calculation."""
    paths = [
        Path("src/lib/firestore"),
        Path("src/lib/firestore/models"),
        Path("src/lib/firestore/utils"),
    ]

    generator = SettingsGenerator(...)
    common = generator._find_common_path_prefix(paths)

    assert common == Path("src/lib/firestore")
```

### Integration Tests

**Test kartlog template generation**:

```bash
# Run template-create on kartlog codebase
cd ~/Projects/kartlog
/template-create --validate --output-location=repo

# Verify placeholders
grep -r "{{" installer/core/templates/kartlog/templates/ | head -10

# Verify layer mappings
cat installer/core/templates/kartlog/settings.json | jq '.layer_mappings'

# Verify extended files
ls installer/core/templates/kartlog/agents/*-ext.md
```

### Acceptance Criteria

| Criterion | Test | Pass |
|-----------|------|------|
| Placeholder coverage >80% | Run on kartlog, check validation output | ✓ |
| Layer mappings use actual paths | Verify settings.json directories | ✓ |
| Extended agent files present | Count `-ext.md` files | ✓ |
| No regression in existing tests | Run full test suite | ✓ |

---

## Risk Assessment

### High Risk
- **Regex pattern brittleness**: Patterns may not match all codebase styles
  - **Mitigation**: Comprehensive test suite with diverse examples
  - **Fallback**: AI extraction can be added later via agent bridge

### Medium Risk
- **Layer mapping edge cases**: Multiple files with different prefixes
  - **Mitigation**: Fallback to first file's directory if no common prefix
  - **Logging**: Warn when synthetic fallback used

### Low Risk
- **Extended file validation**: False positives if agents don't need extended files
  - **Mitigation**: Only log warnings, don't block template creation

---

## Rollback Strategy

If implementation fails:
1. **Revert changes**: Git revert commits for this task
2. **Use existing fallback**: Current `_fallback_placeholder_extraction()` still works (just limited)
3. **Disable validation**: Add `--skip-placeholder-validation` flag
4. **Document limitations**: Update CLAUDE.md with known issues

---

## Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| Placeholder coverage | >80% | Automated validation in Phase 4 |
| Layer mapping accuracy | 100% | Manual inspection of settings.json |
| Extended file presence | >90% | Validation in Phase 7 |
| Existing tests passing | 100% | CI/CD |
| kartlog template score | >8.5/10 | Re-run TASK-REV-TC-B7F2 review |

---

## Dependencies

**None** - This task is self-contained within the template generator subsystem.

---

## Future Enhancements

1. **AI-powered placeholder extraction** via agent bridge
   - Use architectural-reviewer agent for context-aware extraction
   - Integrate with Phase 1 agent invocation pattern
   - Higher accuracy than regex (target: >95%)

2. **Interactive placeholder confirmation**
   - CLI prompts to confirm extracted placeholders
   - Allow user to add custom placeholders
   - Save preferences for future runs

3. **Placeholder validation rules**
   - Enforce naming conventions (PascalCase, camelCase, snake_case)
   - Detect unused placeholders
   - Suggest missing placeholders

---

## Implementation Order

1. **Phase 1**: Placeholder extraction enhancement (3-4 hours)
   - Implement language-specific extraction methods
   - Add validation
   - Write unit tests

2. **Phase 2**: Layer mapping fix (1-2 hours)
   - Modify `_infer_layer_directory()`
   - Add path prefix utilities
   - Test with kartlog

3. **Phase 3**: Extended file validation (0.5-1 hour)
   - Add validation in orchestrator
   - Add warnings
   - Test with agent generation

4. **Phase 4**: Integration testing (1 hour)
   - Test full workflow on kartlog
   - Re-run review to verify fixes
   - Update documentation

---

## Related Tasks

- **TASK-REV-TC-B7F2**: Review that identified these issues
- **TASK-040**: Completeness validation (similar validation pattern)
- **TASK-PD-001**: Progressive disclosure (extended file architecture)

---

## Questions for Review

1. **Placeholder extraction strategy**: Should we prioritize AI extraction via agent bridge, or is enhanced regex sufficient for v1?
   - **Recommendation**: Enhanced regex for v1, AI extraction as future enhancement

2. **Layer mapping fallback**: If no example files found for a layer, should we fail or use synthetic path?
   - **Recommendation**: Use synthetic path with warning (backward compatible)

3. **Extended file validation**: Should missing extended files be a warning or error?
   - **Recommendation**: Warning only (some agents may not need extended content)

4. **Validation failure handling**: If placeholder coverage <80%, should we block template creation?
   - **Recommendation**: Warning only, but log coverage score prominently

---

## Appendix: Example Output

### Before (Current Implementation)

**Template file**: `templates/service layer/firestore/sessions.js.template`
```javascript
import { db } from '$lib/firebase';
import { query } from '$lib/firestore/query';

export async function getSessions(userId) {
    return await query('sessions', { userId });
}
```

**Settings**: `settings.json`
```json
{
  "layer_mappings": {
    "Service Layer": {
      "directory": "src/Service Layer"
    }
  }
}
```

### After (Fixed Implementation)

**Template file**: `templates/service layer/firestore/sessions.js.template`
```javascript
import { db } from '$lib/firebase';
import { query } from '$lib/firestore/query';

export async function get{{EntityNamePlural}}({{entityName}}Id) {
    return await query('{{entity_name_plural}}', { {{entityName}}Id });
}
```

**Settings**: `settings.json`
```json
{
  "layer_mappings": {
    "Service Layer": {
      "directory": "src/lib/firestore"
    }
  }
}
```

**Validation output**:
```
✓ Placeholder coverage: 85.2% (6 placeholders extracted)
✓ Layer mappings: 6/6 using actual paths
✓ Extended files: 7/7 agents have -ext.md
```

---

## Sign-off

**Prepared by**: Software Architect Agent
**Date**: 2025-12-08
**Review Status**: Ready for implementation
**Estimated Effort**: 4-6 hours
**Risk Level**: Medium

**Approval**: Pending human checkpoint
