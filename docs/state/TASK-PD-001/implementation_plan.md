# Implementation Plan: TASK-PD-001

**Task**: Refactor applier.py with create_extended_file() method
**Complexity**: 7/10 (High Risk - Core file modification)
**Stack**: Python
**Estimated Duration**: 5-6 hours (with architectural recommendations applied)

---

## Architecture Overview

### Selected Approach: Strategy Pattern with Separate Methods

**Design Decision**: Create new `apply_with_split()` method alongside existing `apply()` method without modification.

**Rationale**:
- Zero regression risk - existing apply() untouched
- Clear interface separation
- Easy rollback if issues arise
- Explicit caller choice (no feature flag complexity)

**Architectural Recommendations Applied**:
1. ✅ Simplified return types (no Union types)
2. ✅ Removed feature flag (separate methods instead)
3. ✅ Simple list-based content categorization
4. ✅ Type safety with TypedDict for enhancement data

---

## Files to Modify

1. **installer/global/lib/agent_enhancement/applier.py**
   - Add `create_extended_file()` method (public)
   - Add `apply_with_split()` method (public)
   - Add `_categorize_sections()` method (private)
   - Add `_truncate_quick_start()` method (private)
   - Add `_build_extended_content()` method (private)
   - Add `_build_core_content()` method (private)

2. **installer/global/lib/agent_enhancement/models.py**
   - Add `SplitContent` dataclass
   - Add `AgentEnhancement` TypedDict (type safety)

3. **tests/unit/test_applier_progressive_disclosure.py** (new file)
   - 10 unit tests for new methods

4. **tests/integration/test_applier_end_to_end.py**
   - 3 integration tests for full workflow

---

## Content Categorization

### Core Sections (remain in main file)
- frontmatter (metadata)
- title (agent name/purpose)
- quick_start (2-3 examples max)
- boundaries (ALWAYS/NEVER/ASK)
- capabilities (bullet list)
- phase_integration (when agent used)
- loading_instruction (reference to extended file)

### Extended Sections (move to {name}-ext.md)
- detailed_examples (5-10 examples)
- best_practices (comprehensive list)
- anti_patterns (detailed explanations)
- cross_stack (multi-language examples)
- mcp_integration (optional integrations)
- troubleshooting (debug guides)
- technology_specific (per-tech guidance)

---

## Implementation Phases

### Phase 1: Data Models (1 hour)

**File**: `installer/global/lib/agent_enhancement/models.py`

```python
from dataclasses import dataclass
from typing import TypedDict, List

class AgentEnhancement(TypedDict, total=False):
    """Type-safe enhancement data structure."""
    sections: List[str]
    frontmatter: str
    title: str
    quick_start: str
    boundaries: str
    capabilities: str
    phase_integration: str
    detailed_examples: str
    best_practices: str
    anti_patterns: str
    cross_stack: str
    mcp_integration: str
    troubleshooting: str
    technology_specific: str

@dataclass
class SplitContent:
    """Represents content split between core and extended files."""
    core_path: Path
    extended_path: Path
    core_sections: List[str]
    extended_sections: List[str]
```

### Phase 2: Content Categorization (1-2 hours)

**File**: `installer/global/lib/agent_enhancement/applier.py`

```python
# Constants for section categorization
CORE_SECTIONS = [
    'frontmatter',
    'title',
    'quick_start',
    'boundaries',
    'capabilities',
    'phase_integration',
    'loading_instruction',
]

EXTENDED_SECTIONS = [
    'detailed_examples',
    'best_practices',
    'anti_patterns',
    'cross_stack',
    'mcp_integration',
    'troubleshooting',
    'technology_specific',
]

def _categorize_sections(self, enhancement: AgentEnhancement) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Split enhancement sections into core and extended categories."""
    core = {}
    extended = {}

    for section_name, content in enhancement.items():
        if section_name in CORE_SECTIONS:
            core[section_name] = content
        elif section_name in EXTENDED_SECTIONS:
            extended[section_name] = content

    # Limit Quick Start to 3 examples
    if 'quick_start' in core:
        core['quick_start'] = self._truncate_quick_start(core['quick_start'], max_examples=3)

    return core, extended
```

### Phase 3: Core Methods (2-3 hours)

**New Method**: `create_extended_file()`

```python
def create_extended_file(self, agent_path: Path, extended_content: str) -> Path:
    """Create extended content file ({name}-ext.md).

    Args:
        agent_path: Path to core agent file
        extended_content: Content for extended file

    Returns:
        Path to created extended file
    """
    ext_path = agent_path.with_stem(f"{agent_path.stem}-ext")
    ext_path.write_text(extended_content, encoding='utf-8')
    return ext_path
```

**New Method**: `apply_with_split()`

```python
def apply_with_split(self, agent_path: Path, enhancement: AgentEnhancement) -> SplitContent:
    """Apply enhancement with progressive disclosure (split files).

    Args:
        agent_path: Path to agent file
        enhancement: Enhancement content to apply

    Returns:
        SplitContent with paths to core and extended files
    """
    # 1. Categorize sections
    core_sections, extended_sections = self._categorize_sections(enhancement)

    # 2. Build and write core content
    core_content = self._build_core_content(agent_path.stem, core_sections, has_extended=bool(extended_sections))
    agent_path.write_text(core_content, encoding='utf-8')

    # 3. Build and write extended content
    extended_path = None
    if extended_sections:
        extended_content = self._build_extended_content(agent_path.stem, extended_sections)
        extended_path = self.create_extended_file(agent_path, extended_content)

    return SplitContent(
        core_path=agent_path,
        extended_path=extended_path,
        core_sections=list(core_sections.keys()),
        extended_sections=list(extended_sections.keys())
    )
```

### Phase 4: Content Builders (1 hour)

**Helper Methods**:
- `_build_core_content()`: Assembles core file with link to extended file
- `_build_extended_content()`: Assembles extended file with link back to core
- `_truncate_quick_start()`: Limits Quick Start to first N examples
- `_format_section_title()`: Converts snake_case to Title Case

---

## Testing Strategy

### Unit Tests (10 tests, 2 hours)

1. `test_categorize_sections_core_only()`
2. `test_categorize_sections_extended_only()`
3. `test_categorize_sections_mixed()`
4. `test_truncate_quick_start()`
5. `test_create_extended_file_success()`
6. `test_create_extended_file_empty_content()`
7. `test_apply_with_split_both_files()`
8. `test_apply_with_split_core_only()`
9. `test_build_core_content_with_link()`
10. `test_build_extended_content_link_back()`

### Integration Tests (3 tests, 1 hour)

1. `test_full_workflow_progressive_disclosure()`
2. `test_backward_compatibility_apply_unchanged()`
3. `test_manual_fastapi_specialist()`

---

## Risk Mitigation

1. **Backward Compatibility**: Existing `apply()` method unchanged
2. **Type Safety**: TypedDict prevents runtime errors
3. **Simple Categorization**: List-based filtering (no complex logic)
4. **Clear Interfaces**: Separate methods (no conditional complexity)
5. **Rollback Plan**: Remove new methods if issues arise

---

## Success Metrics

- Core file size: 150-300 lines (down from 800+ lines)
- Extended file size: 500-800 lines
- Test coverage: ≥80% for new code
- Zero regressions: 100% existing tests pass
- Architectural score: 78/100 (approved with recommendations)

---

## Dependencies

**Internal**:
- `installer/global/lib/agent_enhancement/models.py`
- `installer/global/lib/agent_enhancement/parser.py`

**External**: None (Python 3.10+ standard library only)

---

## Implementation Checklist

### Code Changes
- [ ] Add `AgentEnhancement` TypedDict to models.py
- [ ] Add `SplitContent` dataclass to models.py
- [ ] Add CORE_SECTIONS and EXTENDED_SECTIONS constants
- [ ] Implement `_categorize_sections()` method
- [ ] Implement `_truncate_quick_start()` method
- [ ] Implement `create_extended_file()` method
- [ ] Implement `apply_with_split()` method
- [ ] Implement `_build_core_content()` method
- [ ] Implement `_build_extended_content()` method
- [ ] Implement `_format_section_title()` helper

### Testing
- [ ] Write 10 unit tests
- [ ] Write 3 integration tests
- [ ] Run existing test suite (verify no regressions)
- [ ] Manual test with fastapi-specialist.md

### Documentation
- [ ] Add docstrings to all new methods
- [ ] Update applier.py module docstring
- [ ] Add inline comments for complex logic

---

**Plan Ready for Implementation (Phase 3)**
