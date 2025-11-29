# TASK-UX-6581: Create Shared Boundary Utilities Library for /agent-enhance and /agent-format

**Created**: 2025-11-23
**Priority**: HIGH
**Estimated Effort**: 2-3 hours
**Complexity**: 4/10 (MEDIUM)
**Task Type**: refactoring + feature
**Tags**: agent-enhancement, code-reuse, github-standards, DRY-principle

---

## Problem Statement

### Current Situation

**Code Duplication**: `/agent-enhance` and `/agent-format` duplicate 166 lines of placement and validation logic:
- Placement logic: 107 lines in `applier.py` (lines 203-309)
- Validation logic: 59 lines in `parser.py` (lines 153-211)

**Gap in `/agent-format`**:
- Generates `[NEEDS_CONTENT]` placeholders instead of actual boundary content
- All 15 global agents lack ALWAYS/NEVER/ASK boundary sections
- GitHub Guideline Gap #4: Boundaries 0/10 → requires manual filling

### Impact

**Without Shared Library**:
- ❌ Duplicated code violates DRY principle
- ❌ Changes require updating 2 separate implementations
- ❌ Inconsistent placement logic across commands
- ❌ `/agent-format` can't generate compliant boundaries automatically

**With Shared Library**:
- ✅ Single source of truth for placement/validation
- ✅ `/agent-format` generates GitHub-compliant generic boundaries
- ✅ Batch format all 15 agents in <1 minute
- ✅ Quality improvement: 0/10 → 6/10 (generic) or 9/10 (AI-enhanced)

### Software Architect Analysis

Comprehensive analysis completed by software-architect agent identified:

**Reuse Opportunities**:
1. **Placement Logic**: `_find_boundaries_insertion_point()` + `_find_post_description_position()` from `applier.py`
2. **Validation Logic**: `_validate_boundaries()` from `parser.py`
3. **Generic Templates**: NEW functionality for role-based boundary generation

**Compliance Assessment**:
- Generic templates achieve **90% GitHub compliance** (9/10 criteria)
- Missing only domain-specific content (quality enhancement, not blocker)
- Format compliance: 100% (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK with ✅/❌/⚠️)

---

## Solution: Shared Boundary Utilities Library

### Architecture

**Create**: `installer/global/lib/agent_enhancement/boundary_utils.py`

**Exports**:
1. `find_boundaries_insertion_point(lines)` - Placement logic (extracted from `applier.py`)
2. `validate_boundaries_format(content)` - Validation logic (extracted from `parser.py`)
3. `generate_generic_boundaries(agent_name, agent_description)` - NEW: Generic content generation

**Integration**:
- `/agent-enhance` imports placement and validation functions
- `/agent-format` imports all 3 functions

---

## Acceptance Criteria

### AC-1: Shared Library Creation

- [ ] **AC-1.1**: Create `boundary_utils.py` in `installer/global/lib/agent_enhancement/`
- [ ] **AC-1.2**: Extract `find_boundaries_insertion_point()` from `applier.py` (107 lines)
- [ ] **AC-1.3**: Extract validation logic into `validate_boundaries_format()` from `parser.py` (59 lines)
- [ ] **AC-1.4**: Implement `generate_generic_boundaries()` with 5 role-specific templates
- [ ] **AC-1.5**: Add `_infer_role_category()` helper for template selection

### AC-2: Integration with /agent-enhance

- [ ] **AC-2.1**: Update `applier.py` to import and use `find_boundaries_insertion_point()`
- [ ] **AC-2.2**: Update `parser.py` to import and use `validate_boundaries_format()`
- [ ] **AC-2.3**: Remove duplicated `_find_boundaries_insertion_point()` and helpers from `applier.py`
- [ ] **AC-2.4**: Remove duplicated `_validate_boundaries()` and helpers from `parser.py`
- [ ] **AC-2.5**: All existing `/agent-enhance` tests pass (regression check)

### AC-3: Integration with /agent-format

- [ ] **AC-3.1**: Update `transformers.py` to import all 3 boundary_utils functions
- [ ] **AC-3.2**: Replace `[NEEDS_CONTENT]` placeholders with `generate_generic_boundaries()` calls
- [ ] **AC-3.3**: Use `find_boundaries_insertion_point()` for placement
- [ ] **AC-3.4**: Use `validate_boundaries_format()` to validate generated content
- [ ] **AC-3.5**: All existing `/agent-format` tests pass (regression check)

### AC-4: Testing Requirements

- [ ] **AC-4.1**: Unit test: `test_find_boundaries_insertion_point_with_quick_start()`
- [ ] **AC-4.2**: Unit test: `test_find_boundaries_insertion_point_no_quick_start()`
- [ ] **AC-4.3**: Unit test: `test_validate_boundaries_format_valid()`
- [ ] **AC-4.4**: Unit test: `test_validate_boundaries_format_invalid_counts()`
- [ ] **AC-4.5**: Unit test: `test_generate_generic_boundaries_testing_agent()`
- [ ] **AC-4.6**: Unit test: `test_generate_generic_boundaries_validates()`
- [ ] **AC-4.7**: Integration test: Generated boundaries pass validation
- [ ] **AC-4.8**: Coverage ≥80% for new `boundary_utils.py`

### AC-5: Generic Template Quality

- [ ] **AC-5.1**: Testing template: 5 ALWAYS, 5 NEVER, 3 ASK rules
- [ ] **AC-5.2**: Architecture template: 5 ALWAYS, 5 NEVER, 3 ASK rules
- [ ] **AC-5.3**: Code review template: 5 ALWAYS, 5 NEVER, 3 ASK rules
- [ ] **AC-5.4**: Orchestration template: 5 ALWAYS, 5 NEVER, 3 ASK rules
- [ ] **AC-5.5**: Default template: 5 ALWAYS, 5 NEVER, 3 ASK rules
- [ ] **AC-5.6**: All templates use correct emoji format (✅/❌/⚠️)
- [ ] **AC-5.7**: All templates pass `validate_boundaries_format()` check

### AC-6: Scope Compliance

- [ ] **AC-6.1**: ONLY 1 new file created: `boundary_utils.py`
- [ ] **AC-6.2**: ONLY 3 files modified: `applier.py`, `parser.py`, `transformers.py`
- [ ] **AC-6.3**: NO changes to `prompt_builder.py` (AI generation unchanged)
- [ ] **AC-6.4**: NO changes to existing test files (only add new test file)
- [ ] **AC-6.5**: NO changes to command specifications
- [ ] **AC-6.6**: NO breaking changes to public APIs

### AC-7: Quality Gates

- [ ] **AC-7.1**: All existing tests pass (100% regression prevention)
- [ ] **AC-7.2**: New tests pass (100% new functionality coverage)
- [ ] **AC-7.3**: Code coverage ≥80% for `boundary_utils.py`
- [ ] **AC-7.4**: No linting errors in modified files
- [ ] **AC-7.5**: Docstrings complete for all exported functions

---

## Scope Boundaries

### ✅ IN SCOPE

**File to Create**:
- `installer/global/lib/agent_enhancement/boundary_utils.py` (NEW - shared library)

**Files to Modify**:
1. `installer/global/lib/agent_enhancement/applier.py`
   - Line 169: Change to `from .boundary_utils import find_boundaries_insertion_point`
   - Line 169-176: Replace `self._find_boundaries_insertion_point(new_lines)` with `find_boundaries_insertion_point(new_lines)`
   - Lines 203-309: DELETE (moved to boundary_utils.py)

2. `installer/global/lib/agent_enhancement/parser.py`
   - Add import: `from .boundary_utils import validate_boundaries_format`
   - Lines 153-258: REPLACE with call to `validate_boundaries_format()`
   - Keep error handling wrapper

3. `installer/global/lib/agent_formatting/transformers.py`
   - Add imports: `find_boundaries_insertion_point`, `validate_boundaries_format`, `generate_generic_boundaries`
   - Lines 115-187: UPDATE to use shared functions
   - Replace `BOUNDARY_TEMPLATE` constant with `generate_generic_boundaries()` calls

**Test File to Create**:
- `tests/lib/agent_enhancement/test_boundary_utils.py` (NEW - unit tests for shared library)

### ❌ OUT OF SCOPE (CRITICAL - Prevent Scope Creep)

**DO NOT MODIFY**:
1. `installer/global/lib/agent_enhancement/prompt_builder.py`
   - AI boundary generation logic unchanged
   - Prompt templates unchanged

2. Command specification files:
   - `installer/global/commands/agent-enhance.md` (documentation only if needed)
   - `installer/global/commands/agent-format.md` (documentation only if needed)

3. Existing test files:
   - DO NOT modify existing tests
   - ONLY add new test file

4. Template files:
   - DO NOT modify agent templates
   - DO NOT auto-format agents (separate task)

5. Any other files not explicitly listed in "IN SCOPE"

**Scope Constraints**:
- **1 new file** created
- **3 existing files** modified
- **1 new test file** created
- **0 breaking changes** to existing APIs
- **0 behavioral changes** to existing functionality

---

## Implementation Plan

### Phase 1: Create Shared Library (1.5 hours)

**Step 1.1: Create `boundary_utils.py` skeleton** (15 min)
```python
"""
Shared Boundary Section Utilities

Used by both /agent-enhance (AI content) and /agent-format (generic content).
Provides consistent placement and validation across commands.
"""

from typing import Optional
import re

# Exports
__all__ = [
    'find_boundaries_insertion_point',
    'validate_boundaries_format',
    'generate_generic_boundaries'
]
```

**Step 1.2: Extract placement logic from `applier.py`** (30 min)

Copy lines 203-309 from `applier.py`:
```python
def find_boundaries_insertion_point(lines: list[str]) -> Optional[int]:
    """
    Find optimal insertion point for boundaries section.

    EXTRACTED FROM: applier.py lines 203-309 (TASK-STND-0B1A)

    Target: Lines 80-150 (GitHub recommendation for authority clarity).

    Strategy:
    1. Find "## Quick Start" section
    2. Find next ## section after Quick Start
    3. Insert boundaries before that next section
    4. Fallback: Insert at line 50-80 if no Quick Start found

    Args:
        lines: List of content lines

    Returns:
        Line index for insertion or None if no suitable point found
    """
    # Step 1: Find Quick Start
    quick_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Quick Start"):
            quick_start_idx = i
            break

    if quick_start_idx is None:
        # Fallback: No Quick Start, insert after description
        return _find_post_description_position(lines)

    # Step 2: Find next ## section after Quick Start
    for i in range(quick_start_idx + 1, len(lines)):
        if lines[i].strip().startswith("## "):
            return i  # Insert before this section

    # Step 3: No next section, insert at reasonable position
    target_line = quick_start_idx + 30
    return min(target_line, len(lines))


def _find_post_description_position(lines: list[str]) -> Optional[int]:
    """
    Fallback: Find position after description/purpose section.

    EXTRACTED FROM: applier.py lines 243-309 (TASK-STND-0B1A)
    """
    # Find end of frontmatter
    frontmatter_end = 0
    frontmatter_count = 0

    for i, line in enumerate(lines):
        if line.strip() == '---':
            frontmatter_count += 1
            if frontmatter_count == 2:
                frontmatter_end = i + 1
                break

    # Find sections after frontmatter
    early_sections = ["Purpose", "Why This Agent Exists", "Technologies", "Usage", "When to Use"]
    content_sections = ["Code Examples", "Examples", "Related Templates", "Best Practices", "Capabilities"]

    sections_found = []
    for i in range(frontmatter_end, min(frontmatter_end + 100, len(lines))):
        if lines[i].strip().startswith("## "):
            section_name = lines[i].strip()[3:].strip()
            sections_found.append((i, section_name))

    # Strategy: Insert before first "content" section OR after last "early" section
    last_early_section_idx = None
    first_content_section_idx = None

    for idx, name in sections_found:
        if any(early in name for early in early_sections):
            last_early_section_idx = idx
        elif any(content in name for content in content_sections):
            if first_content_section_idx is None:
                first_content_section_idx = idx
            break

    # Decision logic
    if first_content_section_idx is not None:
        return first_content_section_idx

    if last_early_section_idx is not None:
        for idx, name in sections_found:
            if idx > last_early_section_idx:
                return idx
        return min(50, len(lines))

    return None
```

**Step 1.3: Extract validation logic from `parser.py`** (20 min)

Copy validation logic from `parser.py` lines 153-258:
```python
def validate_boundaries_format(boundaries_content: str) -> tuple[bool, list[str]]:
    """
    Validate boundaries section structure and rule counts.

    EXTRACTED FROM: parser.py lines 153-258 (TASK-STND-8B4C)

    Ensures ALWAYS/NEVER/ASK framework compliance:
    - ALWAYS: 5-7 rules with ✅ prefix
    - NEVER: 5-7 rules with ❌ prefix
    - ASK: 3-5 scenarios with ⚠️ prefix

    Args:
        boundaries_content: Markdown content of boundaries section

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    if not boundaries_content or not boundaries_content.strip():
        issues.append("Boundaries section is empty")
        return False, issues

    # Check for required subsections
    if "### ALWAYS" not in boundaries_content:
        issues.append("Missing '### ALWAYS' subsection")
    if "### NEVER" not in boundaries_content:
        issues.append("Missing '### NEVER' subsection")
    if "### ASK" not in boundaries_content:
        issues.append("Missing '### ASK' subsection")

    if issues:
        return False, issues

    # Extract sections
    always_section = _extract_subsection(boundaries_content, "### ALWAYS", "### NEVER")
    never_section = _extract_subsection(boundaries_content, "### NEVER", "### ASK")
    ask_section = _extract_subsection(boundaries_content, "### ASK", None)

    # Count rules
    always_count = _count_rules(always_section, "✅")
    never_count = _count_rules(never_section, "❌")
    ask_count = _count_rules(ask_section, "⚠️")

    # Validate counts
    if not (5 <= always_count <= 7):
        issues.append(
            f"ALWAYS section must have 5-7 rules, found {always_count}. "
            f"Each rule should start with '- ✅'"
        )

    if not (5 <= never_count <= 7):
        issues.append(
            f"NEVER section must have 5-7 rules, found {never_count}. "
            f"Each rule should start with '- ❌'"
        )

    if not (3 <= ask_count <= 5):
        issues.append(
            f"ASK section must have 3-5 scenarios, found {ask_count}. "
            f"Each scenario should start with '- ⚠️'"
        )

    is_valid = len(issues) == 0
    return is_valid, issues


def _extract_subsection(content: str, start_marker: str, end_marker: Optional[str]) -> str:
    """Extract content between two section markers."""
    start_idx = content.find(start_marker)
    if start_idx == -1:
        return ""

    start_idx = content.find('\n', start_idx) + 1

    if end_marker is None:
        return content[start_idx:]

    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        return content[start_idx:]

    return content[start_idx:end_idx]


def _count_rules(section_content: str, emoji: str) -> int:
    """Count rules in a section by counting lines with specific emoji prefix."""
    count = 0
    for line in section_content.split('\n'):
        stripped = line.strip()
        if stripped.startswith(f"- {emoji}") or stripped.startswith(f"-{emoji}"):
            count += 1
    return count
```

**Step 1.4: Implement generic boundary generation** (45 min)

```python
def generate_generic_boundaries(agent_name: str, agent_description: str) -> str:
    """
    Generate generic boundary content for pattern-based formatting.

    NOT AI-powered - uses templates that work for ANY agent.
    For domain-specific content, use /agent-enhance instead.

    Args:
        agent_name: Name of agent (e.g., "architectural-reviewer")
        agent_description: Agent description from frontmatter

    Returns:
        Markdown content with ALWAYS/NEVER/ASK sections (passes validation)
    """
    # Infer agent role category
    role_category = _infer_role_category(agent_name, agent_description)

    # Select template based on category
    templates = {
        "testing": _testing_boundaries_template(),
        "architecture": _architecture_boundaries_template(),
        "code_review": _code_review_boundaries_template(),
        "orchestration": _orchestration_boundaries_template(),
        "default": _default_boundaries_template()
    }

    return templates.get(role_category, templates["default"])


def _infer_role_category(agent_name: str, agent_description: str) -> str:
    """Infer agent role category from name/description."""
    combined = (agent_name + " " + agent_description).lower()

    if any(kw in combined for kw in ["test", "coverage", "verification"]):
        return "testing"
    elif any(kw in combined for kw in ["architect", "design", "solid", "pattern"]):
        return "architecture"
    elif any(kw in combined for kw in ["review", "quality", "lint", "format"]):
        return "code_review"
    elif any(kw in combined for kw in ["orchestrat", "workflow", "phase", "task"]):
        return "orchestration"
    else:
        return "default"


def _testing_boundaries_template() -> str:
    """Testing-focused generic boundaries."""
    return """## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
- ✅ Report failures with actionable error messages (aid debugging)
- ✅ Enforce 100% test pass rate (zero tolerance for failures)
- ✅ Validate test coverage thresholds (ensure quality gates met)

### NEVER
- ❌ Never approve code with failing tests (zero tolerance policy)
- ❌ Never skip compilation check (prevents false positive test runs)
- ❌ Never modify test code to make tests pass (integrity violation)
- ❌ Never ignore coverage below threshold (quality gate bypass prohibited)
- ❌ Never run tests without dependency installation (environment consistency required)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Performance tests failing: Ask if acceptable for non-production changes
- ⚠️ Flaky tests detected: Ask if should quarantine or fix immediately
"""


def _architecture_boundaries_template() -> str:
    """Architecture-focused generic boundaries."""
    return """## Boundaries

### ALWAYS
- ✅ Evaluate against SOLID principles (detect violations early)
- ✅ Assess design patterns for appropriateness (prevent over-engineering)
- ✅ Check for separation of concerns (enforce clean architecture)
- ✅ Review dependency management (minimize coupling)
- ✅ Validate testability of proposed design (enable quality assurance)

### NEVER
- ❌ Never approve tight coupling between layers (violates maintainability)
- ❌ Never accept violations of established patterns (consistency required)
- ❌ Never skip assessment of design complexity (prevent technical debt)
- ❌ Never approve design without considering testability (quality gate)
- ❌ Never ignore dependency injection opportunities (enable flexibility)

### ASK
- ⚠️ New pattern introduction: Ask if justified given team familiarity
- ⚠️ Trade-off between performance and maintainability: Ask for priority
- ⚠️ Refactoring scope exceeds task boundary: Ask if should split task
"""


def _code_review_boundaries_template() -> str:
    """Code review-focused generic boundaries."""
    return """## Boundaries

### ALWAYS
- ✅ Run linters before review (catch mechanical issues early)
- ✅ Check for code duplication (enforce DRY principle)
- ✅ Validate error handling completeness (ensure robustness)
- ✅ Verify consistent naming conventions (maintain readability)
- ✅ Ensure adequate code comments (support maintainability)

### NEVER
- ❌ Never approve code with linting errors (quality baseline)
- ❌ Never skip security vulnerability checks (safety critical)
- ❌ Never accept copy-paste duplication (technical debt source)
- ❌ Never approve missing error handling (reliability violation)
- ❌ Never ignore inconsistent formatting (team standard breach)

### ASK
- ⚠️ Style preference conflicts with project standards: Ask for clarification
- ⚠️ Refactoring suggestion exceeds scope: Ask if should defer
- ⚠️ Performance optimization needed but complex: Ask for priority
"""


def _orchestration_boundaries_template() -> str:
    """Orchestration-focused generic boundaries."""
    return """## Boundaries

### ALWAYS
- ✅ Execute phases in defined sequence (ensure workflow integrity)
- ✅ Validate prerequisites before phase execution (prevent failures)
- ✅ Capture state transitions in task metadata (enable traceability)
- ✅ Enforce quality gates at checkpoints (maintain standards)
- ✅ Provide clear progress indicators (support transparency)

### NEVER
- ❌ Never skip required phases (workflow integrity violation)
- ❌ Never proceed if prerequisites not met (dependency failure)
- ❌ Never bypass quality gates (standard erosion)
- ❌ Never lose state during transitions (data integrity issue)
- ❌ Never execute out-of-sequence phases (workflow corruption)

### ASK
- ⚠️ Quality gate failure with borderline metrics: Ask if acceptable
- ⚠️ Workflow customization requested: Ask if deviates from standard
- ⚠️ Phase timeout but progress visible: Ask if should extend
"""


def _default_boundaries_template() -> str:
    """Default generic boundaries for unrecognized agent types."""
    return """## Boundaries

### ALWAYS
- ✅ Execute core responsibilities as defined in Purpose section (role clarity)
- ✅ Follow established patterns in technology stack (consistency)
- ✅ Validate inputs before processing (error prevention)
- ✅ Provide clear, actionable feedback (user guidance)
- ✅ Document assumptions and constraints (transparency)

### NEVER
- ❌ Never skip validation steps (quality assurance)
- ❌ Never modify code without understanding context (safety)
- ❌ Never generate content without verification (accuracy)
- ❌ Never ignore user constraints (respect requirements)
- ❌ Never proceed if prerequisites missing (dependency management)

### ASK
- ⚠️ High-risk changes requiring approval (risk management)
- ⚠️ Conflicting requirements or constraints (decision needed)
- ⚠️ Uncertain approach with multiple valid options (human judgment)
"""
```

### Phase 2: Update /agent-enhance (0.5 hours)

**Step 2.1: Update `applier.py`** (15 min)

```python
# Add import at top (after line 20)
from .boundary_utils import find_boundaries_insertion_point

# Line 169: Replace method call
# OLD:
insertion_point = self._find_boundaries_insertion_point(new_lines)

# NEW:
insertion_point = find_boundaries_insertion_point(new_lines)

# Lines 203-309: DELETE entire _find_boundaries_insertion_point() method and helper
# (Moved to boundary_utils.py)
```

**Step 2.2: Update `parser.py`** (15 min)

```python
# Add import at top
from .boundary_utils import validate_boundaries_format

# Lines 153-258: REPLACE _validate_boundaries() method body
def _validate_boundaries(self, boundaries_content: str) -> None:
    """
    Validate boundaries section structure and rule counts.

    Uses shared boundary_utils.validate_boundaries_format() for validation.
    """
    is_valid, issues = validate_boundaries_format(boundaries_content)

    if not is_valid:
        # Combine issues into single error message
        raise ValueError("; ".join(issues))

    # Log success (matches old behavior)
    logger.info("Boundaries validation passed via shared utility")
```

**Step 2.3: Run regression tests** (10 min)

```bash
pytest tests/lib/agent_enhancement/ -v
# Verify all existing tests pass
```

### Phase 3: Update /agent-format (0.5 hours)

**Step 3.1: Update `transformers.py`** (20 min)

```python
# Add imports at top (handle cross-library import)
import sys
from pathlib import Path

# Add agent_enhancement to path
_lib_dir = Path(__file__).resolve().parent.parent
_agent_enhancement_dir = _lib_dir / "agent_enhancement"
if str(_agent_enhancement_dir) not in sys.path:
    sys.path.insert(0, str(_agent_enhancement_dir))

from boundary_utils import (
    find_boundaries_insertion_point,
    validate_boundaries_format,
    generate_generic_boundaries
)

# Lines 17-34: REMOVE BOUNDARY_TEMPLATE constant

# Lines 115-187: UPDATE _add_boundary_sections() method
def _add_boundary_sections(
    self,
    lines: list[str],
    agent: AgentStructure,
    existing: dict[str, bool],
) -> list[str]:
    """Add missing ALWAYS/NEVER/ASK boundary sections using shared library."""

    # Step 1: Find insertion point (SHARED)
    insert_line = find_boundaries_insertion_point(lines)

    if insert_line is None:
        insert_line = len(lines)  # Fallback

    # Step 2: Generate generic boundary content (NEW)
    agent_name = agent.frontmatter.get("name", "unknown")
    agent_description = agent.frontmatter.get("description", "")

    boundaries_content = generate_generic_boundaries(agent_name, agent_description)

    # Step 3: Validate generated content (SHARED)
    is_valid, issues = validate_boundaries_format(boundaries_content)

    if not is_valid:
        # Fallback to placeholder if generation failed
        boundaries_content = """## Boundaries

### ALWAYS
- ✅ [PLACEHOLDER: Generic generation failed - manual intervention required]

### NEVER
- ❌ [PLACEHOLDER: Generic generation failed - manual intervention required]

### ASK
- ⚠️ [PLACEHOLDER: Generic generation failed - manual intervention required]
"""

    # Step 4: Insert content
    boundary_lines = boundaries_content.strip().split('\n')
    lines = lines[:insert_line] + [''] + boundary_lines + [''] + lines[insert_line:]

    return lines
```

**Step 3.2: Run regression tests** (10 min)

```bash
pytest tests/lib/agent_formatting/ -v
# Verify all existing tests pass
```

### Phase 4: Add Unit Tests (1 hour)

**Step 4.1: Create `test_boundary_utils.py`** (60 min)

```python
"""Tests for shared boundary utilities."""

import pytest
from installer.global.lib.agent_enhancement.boundary_utils import (
    find_boundaries_insertion_point,
    validate_boundaries_format,
    generate_generic_boundaries,
)


class TestFindBoundariesInsertionPoint:
    """Test placement logic."""

    def test_with_quick_start(self):
        """Should insert after Quick Start, before next section."""
        lines = [
            "---",
            "name: test",
            "---",
            "# Agent",
            "## Quick Start",
            "Instructions",
            "## Code Examples",
            "Examples"
        ]

        result = find_boundaries_insertion_point(lines)
        assert result == 6  # Before Code Examples

    def test_no_quick_start(self):
        """Should use fallback placement."""
        lines = [
            "---",
            "name: test",
            "---",
            "# Agent",
            "## Purpose",
            "Description",
            "## Code Examples",
            "Examples"
        ]

        result = find_boundaries_insertion_point(lines)
        assert result == 6  # Before Code Examples


class TestValidateBoundariesFormat:
    """Test validation logic."""

    def test_valid_boundaries(self):
        """Should pass with 5 ALWAYS, 5 NEVER, 3 ASK."""
        content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3
- ✅ Rule 4
- ✅ Rule 5

### NEVER
- ❌ Rule 1
- ❌ Rule 2
- ❌ Rule 3
- ❌ Rule 4
- ❌ Rule 5

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
- ⚠️ Scenario 3
"""

        is_valid, issues = validate_boundaries_format(content)
        assert is_valid is True
        assert len(issues) == 0

    def test_invalid_rule_counts(self):
        """Should fail with wrong rule counts."""
        content = """## Boundaries

### ALWAYS
- ✅ Rule 1

### NEVER
- ❌ Rule 1

### ASK
- ⚠️ Scenario 1
"""

        is_valid, issues = validate_boundaries_format(content)
        assert is_valid is False
        assert len(issues) == 3  # All sections have wrong counts


class TestGenerateGenericBoundaries:
    """Test generic boundary generation."""

    def test_testing_agent(self):
        """Should generate testing-focused boundaries."""
        result = generate_generic_boundaries("test-verifier", "Test execution")

        assert "## Boundaries" in result
        assert "### ALWAYS" in result
        assert "### NEVER" in result
        assert "### ASK" in result

    def test_generated_content_validates(self):
        """Generated content should pass validation."""
        result = generate_generic_boundaries("test-agent", "Test description")

        is_valid, issues = validate_boundaries_format(result)
        assert is_valid is True, f"Generated content failed validation: {issues}"
```

---

## Test Strategy

### Unit Tests (6 required)

1. **test_find_boundaries_insertion_point_with_quick_start**
   - Setup: Agent with Quick Start section
   - Assert: Boundaries inserted after Quick Start, before next section

2. **test_find_boundaries_insertion_point_no_quick_start**
   - Setup: Agent without Quick Start
   - Assert: Fallback placement before Code Examples

3. **test_validate_boundaries_format_valid**
   - Setup: Valid boundaries with 5-7 ALWAYS, 5-7 NEVER, 3-5 ASK
   - Assert: `is_valid = True, issues = []`

4. **test_validate_boundaries_format_invalid_counts**
   - Setup: Invalid rule counts
   - Assert: `is_valid = False`, issues list populated

5. **test_generate_generic_boundaries_testing_agent**
   - Setup: Agent name with "test" keyword
   - Assert: Testing-focused template selected

6. **test_generate_generic_boundaries_validates**
   - Setup: Any agent name/description
   - Assert: Generated content passes `validate_boundaries_format()`

### Integration Tests

7. **test_agent_enhance_uses_shared_placement**
   - Setup: Run `/agent-enhance` on test agent
   - Assert: Boundaries placed using shared logic

8. **test_agent_format_generates_valid_boundaries**
   - Setup: Run `/agent-format` on test agent
   - Assert: Generic boundaries generated and validated

### Regression Tests

9. **test_all_existing_agent_enhance_tests_pass**
   - Run: `pytest tests/lib/agent_enhancement/test_boundaries_implementation.py -v`
   - Assert: 24/24 tests pass

10. **test_all_existing_agent_format_tests_pass**
    - Run: `pytest tests/lib/agent_formatting/ -v`
    - Assert: All tests pass

---

## Validation Criteria

### Success Metrics

**Code Reuse**:
- ✅ 166 lines of duplication eliminated
- ✅ Single source of truth for placement/validation

**GitHub Compliance**:
- ✅ Generic templates achieve 90% compliance (9/10 criteria)
- ✅ Format compliance: 100% (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- ✅ Placement compliance: Lines 80-150 (shared logic)

**Quality Gates**:
- ✅ All existing tests pass (0 regressions)
- ✅ New tests pass (100% coverage)
- ✅ Code coverage ≥80%
- ✅ No linting errors

**Scope Compliance**:
- ✅ Exactly 1 new file created
- ✅ Exactly 3 files modified
- ✅ 0 breaking changes

---

## Risk Assessment

### Risk 1: Import Path Issues Across Libraries

**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Add `sys.path` manipulation in `transformers.py` to resolve cross-library imports
**Validation**: Test import in both Python REPL and pytest

### Risk 2: Breaking Existing /agent-enhance Behavior

**Likelihood**: Low
**Impact**: High
**Mitigation**: Run all 24 existing tests, verify placement logic identical
**Rollback**: Revert changes to `applier.py` and `parser.py`, keep `boundary_utils.py` separate

### Risk 3: Generic Templates Don't Validate

**Likelihood**: Low
**Impact**: Medium
**Mitigation**: Test each template with `validate_boundaries_format()` before implementation
**Validation**: Unit test `test_generate_generic_boundaries_validates()`

### Risk 4: Regression in /agent-format

**Likelihood**: Low
**Impact**: Medium
**Mitigation**: Run existing `/agent-format` test suite
**Rollback**: Revert `transformers.py` changes, keep placeholders

---

## Definition of Done

### Code Complete

- [ ] `boundary_utils.py` created with all 3 exported functions
- [ ] `applier.py` updated to use shared placement
- [ ] `parser.py` updated to use shared validation
- [ ] `transformers.py` updated to use all 3 shared functions
- [ ] All 5 generic templates implemented

### Testing Complete

- [ ] 6 unit tests added in `test_boundary_utils.py`
- [ ] All unit tests pass
- [ ] All existing `/agent-enhance` tests pass (regression)
- [ ] All existing `/agent-format` tests pass (regression)
- [ ] Code coverage ≥80% for `boundary_utils.py`

### Quality Gates

- [ ] No linting errors in modified files
- [ ] Docstrings complete for all exported functions
- [ ] Type hints correct (`int | None` vs `Optional[int]`)
- [ ] No breaking changes to existing APIs

### Documentation

- [ ] Docstrings explain extraction source (e.g., "EXTRACTED FROM: applier.py lines 203-309")
- [ ] Comments explain role-specific template selection
- [ ] README updated if needed (optional)

---

## Related Tasks

**Upstream**:
- [TASK-STND-8B4C](tasks/completed/TASK-STND-8B4C/) - Boundaries implementation (placement logic source)
- [TASK-STND-0B1A](tasks/backlog/TASK-STND-0B1A-fix-boundaries-placement-agent-enhancer.md) - Placement fix (validation logic source)

**Downstream**:
- Follow-up task: Batch format all 15 global agents with `/agent-format`
- Follow-up task: Upgrade 4-5 critical agents with `/agent-enhance`

**Blocks**:
- None (can implement immediately)

**Blocked By**:
- None

---

## References

### Files to Read

1. [applier.py:203-309](installer/global/lib/agent_enhancement/applier.py#L203-L309) - Placement logic source
2. [parser.py:153-258](installer/global/lib/agent_enhancement/parser.py#L153-L258) - Validation logic source
3. [transformers.py:115-187](installer/global/lib/agent_formatting/transformers.py#L115-L187) - Current `/agent-format` implementation
4. [GitHub Best Practices](docs/analysis/github-agent-best-practices-analysis.md) - Gap #4 analysis

### Files to Create

1. `installer/global/lib/agent_enhancement/boundary_utils.py` (NEW - 350 lines estimated)
2. `tests/lib/agent_enhancement/test_boundary_utils.py` (NEW - 150 lines estimated)

### Files to Modify

1. `installer/global/lib/agent_enhancement/applier.py` (delete 107 lines, add 2 lines)
2. `installer/global/lib/agent_enhancement/parser.py` (replace 106 lines with 10 lines)
3. `installer/global/lib/agent_formatting/transformers.py` (replace 73 lines with 40 lines)

---

## Notes

### Why This Approach Works

**Code Reuse Benefits**:
- ✅ Eliminates 166 lines of duplication (DRY principle)
- ✅ Single source of truth (easier maintenance)
- ✅ Consistent placement across commands

**GitHub Compliance**:
- ✅ Generic templates achieve 90% compliance immediately
- ✅ Upgrade path to 100% via `/agent-enhance` later
- ✅ Fast batch processing (<1 min for 15 agents)

**Low Risk**:
- ✅ Extraction preserves exact logic (no behavioral changes)
- ✅ Comprehensive regression tests
- ✅ Fallback to placeholders if generation fails

### Why Scope Is Minimal

**1 new file**: `boundary_utils.py` (shared library)
**3 modified files**: `applier.py`, `parser.py`, `transformers.py` (use shared library)
**0 breaking changes**: Existing APIs unchanged
**0 behavioral changes**: Placement/validation logic identical

### Future Enhancements (Out of Scope)

- Batch format all 15 global agents (separate task)
- Upgrade critical agents with `/agent-enhance` (separate task)
- Add more role-specific templates (if needed)
- Document upgrade workflow in CLAUDE.md

---

**Task created by**: Claude Code (software-architect analysis)
**Creation date**: 2025-11-23
**Estimated completion**: 2-3 hours
**Complexity**: 4/10 (MEDIUM)
**Priority**: HIGH (fixes code duplication + enables GitHub compliance)
