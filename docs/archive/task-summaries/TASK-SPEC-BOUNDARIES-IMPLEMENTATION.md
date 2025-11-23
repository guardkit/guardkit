# Task Specification: Complete Boundaries (ALWAYS/NEVER/ASK) Implementation

**Task ID**: (To be assigned by /task-create)
**Title**: Complete TASK-STND-773D: Implement boundaries section generation in agent enhancement pipeline
**Priority**: High (P0 - Critical Gap #4 per GitHub standards)
**Estimated Effort**: 12-16 hours
**Type**: Bug Fix + Enhancement
**Parent Task**: TASK-STND-773D (completed but incomplete)

---

## Executive Summary

TASK-STND-773D was marked complete (commit 814d810) but only updated documentation—the actual implementation in the agent enhancement pipeline was never completed. This results in enhanced agents having "Best Practices" sections instead of the required "Boundaries (ALWAYS/NEVER/ASK)" sections, causing a 0/10 boundary clarity score per GitHub standards analysis.

**Impact**: All enhanced agents fail Critical Gap #4 (boundary clarity), reducing their actionability and increasing misuse incidents.

**Root Cause**: Task implementation stopped after Phase 1 (documentation update) and never proceeded to Phase 2 (code implementation).

---

## Problem Statement

### Current State (Broken)

1. **Documentation Says**: `agent-content-enhancer.md` specifies boundaries section with ALWAYS/NEVER/ASK framework (lines 64-92, 395-436)
2. **Code Does**: `prompt_builder.py` requests "best_practices" section (lines 80, 86, 89)
3. **Result**: Enhanced agents contain "Best Practices" instead of "Boundaries"
4. **Consequence**: Boundary clarity score 0/10 (should be 9/10)

### Evidence of Incomplete Implementation

**File: `installer/global/lib/agent_enhancement/prompt_builder.py`**
```python
# Lines 80, 86, 89 - INCORRECT (still requesting best_practices)
3. Best practices for using this agent with these templates
    "sections": ["related_templates", "examples", "best_practices"],
    "best_practices": "## Best Practices\\n\\n1. Practice 1\\n2. Practice 2\\n..."
```

**Expected (per agent-content-enhancer.md):**
```python
# Should request boundaries with ALWAYS/NEVER/ASK subsections
3. Boundaries for this agent (ALWAYS do, NEVER do, ASK first)
    "sections": ["related_templates", "examples", "boundaries"],
    "boundaries": "## Boundaries\\n\\n### ALWAYS\\n- ✅ Rule 1\\n..."
```

**File: `installer/global/lib/agent_enhancement/parser.py`**
- No validation for boundaries section structure
- No validation for ALWAYS/NEVER/ASK subsections
- No validation for rule counts (5-7/5-7/3-5)
- No validation for emoji prefixes (✅/❌/⚠️)

**File: `installer/global/lib/agent_enhancement/applier.py`**
- Section insertion logic is generic (line 156)
- No special handling for boundaries placement (should be after line 12, before Related Templates)
- No validation of boundaries format

### Impact Analysis

**GitHub Standards Compliance:**
- **Current**: 0/10 boundary clarity (missing entirely)
- **After Fix**: 9/10 boundary clarity (explicit ALWAYS/NEVER/ASK framework)

**Developer Experience:**
- **Current**: Confusion about agent authority, misuse incidents, unnecessary escalations
- **After Fix**: Clear decision framework, 40% reduction in human intervention

**Validation Failures:**
- All enhanced agents fail boundary validation checks
- Quality scores artificially lowered
- Iterative refinement loops triggered unnecessarily

---

## Motivation

### Why This Matters

**1. GitHub Industry Standards (Critical Gap #4)**

Per analysis of 2,500+ repositories (docs/analysis/github-agent-best-practices-analysis.md):
- Explicit boundaries reduce misuse by 60%
- ALWAYS/NEVER/ASK framework reduces escalations by 40%
- Boundary clarity correlates with 8+ satisfaction scores

**2. Quality Gate Enforcement**

Per `agent-content-enhancer.md` lines 148-167:
```yaml
validation_report:
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  boundary_completeness:
    always_count: 6 ✅ (threshold: 5-7)
    never_count: 6 ✅ (threshold: 5-7)
    ask_count: 4 ✅ (threshold: 3-5)
    emoji_correct: true ✅
    format_valid: true ✅
    placement_correct: true ✅
```

**Current Reality**: All enhanced agents fail these checks.

**3. Agent Enhancement Strategy**

The `/agent-enhance` command (from template-create) depends on:
- Prompt requesting boundaries → parser extracting boundaries → applier inserting boundaries
- **All three stages broken** due to incomplete TASK-STND-773D implementation

**4. Developer Productivity**

From GitHub analysis (lines 260-266):
```
Impact of Missing Boundaries:
- Developers confused about agent authority
- "Can the agent do X?" questions common
- Misuse incidents (agents used outside scope)
- Unnecessary escalations (unclear when to ask)
```

---

## Acceptance Criteria

### 1. Prompt Builder Updates

**File**: `installer/global/lib/agent_enhancement/prompt_builder.py`

✅ **AC-1.1**: Lines 80, 86, 89 updated to request "boundaries" instead of "best_practices"

✅ **AC-1.2**: Prompt specifies ALWAYS/NEVER/ASK subsection structure:
```json
{
    "sections": ["related_templates", "examples", "boundaries"],
    "boundaries": "## Boundaries\\n\\n### ALWAYS\\n- ✅ Rule\\n\\n### NEVER\\n- ❌ Rule\\n\\n### ASK\\n- ⚠️ Scenario"
}
```

✅ **AC-1.3**: Prompt includes validation requirements:
- ALWAYS: 5-7 rules with ✅ emoji prefix
- NEVER: 5-7 rules with ❌ emoji prefix
- ASK: 3-5 scenarios with ⚠️ emoji prefix

✅ **AC-1.4**: Prompt includes placement guidance:
- Insert after frontmatter (line ~12)
- Before "Related Templates" section
- After "Quick Start" section (if present)

### 2. Parser Validation

**File**: `installer/global/lib/agent_enhancement/parser.py`

✅ **AC-2.1**: Add `_validate_boundaries()` method with structure checks:
- Presence of all three subsections (ALWAYS/NEVER/ASK)
- Markdown heading format (`### ALWAYS`, `### NEVER`, `### ASK`)
- Each rule starts with correct emoji (✅/❌/⚠️)

✅ **AC-2.2**: Add rule count validation:
- ALWAYS: 5-7 rules (warn if <5 or >7)
- NEVER: 5-7 rules (warn if <5 or >7)
- ASK: 3-5 scenarios (warn if <3 or >5)

✅ **AC-2.3**: Call validation in `parse()` method:
```python
def parse(self, response: str) -> Dict[str, Any]:
    enhancement = json.loads(json_content)
    self._validate_basic_structure(enhancement)

    # NEW: Validate boundaries if present
    if "boundaries" in enhancement.get("sections", []):
        self._validate_boundaries(enhancement.get("boundaries", ""))

    return enhancement
```

✅ **AC-2.4**: Backward compatibility:
- Accept responses with "best_practices" section
- Warn if "best_practices" found (deprecated format)
- Do not fail on old format (transition period)

### 3. Applier Placement Logic

**File**: `installer/global/lib/agent_enhancement/applier.py`

✅ **AC-3.1**: Update `_merge_content()` to handle boundaries placement:
```python
def _merge_content(self, original: str, enhancement: Dict[str, Any]) -> str:
    # Find frontmatter end (line ~12)
    frontmatter_end = self._find_frontmatter_end(lines)

    # Insert boundaries after frontmatter, before other sections
    if "boundaries" in sections_to_add:
        boundaries_content = enhancement.get("boundaries", "")
        lines.insert(frontmatter_end + 1, boundaries_content)

    # Insert other sections at end (existing logic)
    for section in [s for s in sections_to_add if s != "boundaries"]:
        # ... existing insertion logic
```

✅ **AC-3.2**: Boundaries section inserted at correct location:
- After frontmatter (line ~12)
- Before "Related Templates" section
- Before "Code Examples" section
- Before any other enhanced sections

✅ **AC-3.3**: Section header normalization:
- "boundaries" → "## Boundaries" (not "## Best Practices")
- Preserve subsection headings (### ALWAYS, ### NEVER, ### ASK)

### 4. Testing Requirements

**New Test File**: `tests/unit/lib/agent_enhancement/test_boundaries_validation.py`

✅ **AC-4.1**: Test prompt builder generates correct boundaries request:
```python
def test_prompt_requests_boundaries_section():
    """Verify prompt requests 'boundaries' not 'best_practices'"""
    prompt = builder.build(agent_metadata, templates, template_dir)
    assert '"boundaries"' in prompt
    assert '"best_practices"' not in prompt
    assert "### ALWAYS" in prompt
    assert "### NEVER" in prompt
    assert "### ASK" in prompt
```

✅ **AC-4.2**: Test parser validates boundaries structure:
```python
def test_parser_validates_boundaries_structure():
    """Verify parser checks ALWAYS/NEVER/ASK subsections"""
    response = '{"sections": ["boundaries"], "boundaries": "## Boundaries\\n### ALWAYS\\n- ✅ Rule"}'
    # Should pass validation

    response_missing = '{"sections": ["boundaries"], "boundaries": "## Boundaries\\n- Rule"}'
    # Should warn about missing subsections
```

✅ **AC-4.3**: Test parser validates rule counts:
```python
def test_parser_validates_rule_counts():
    """Verify parser checks 5-7/5-7/3-5 rule counts"""
    boundaries_valid = create_boundaries(always=6, never=6, ask=4)
    # Should pass

    boundaries_invalid = create_boundaries(always=3, never=8, ask=2)
    # Should warn about counts
```

✅ **AC-4.4**: Test parser validates emoji prefixes:
```python
def test_parser_validates_emoji_prefixes():
    """Verify parser checks ✅/❌/⚠️ emoji usage"""
    boundaries_correct = "### ALWAYS\\n- ✅ Rule 1\\n- ✅ Rule 2"
    # Should pass

    boundaries_incorrect = "### ALWAYS\\n- Rule 1\\n- Rule 2"
    # Should warn about missing emojis
```

✅ **AC-4.5**: Test applier placement:
```python
def test_applier_inserts_boundaries_after_frontmatter():
    """Verify boundaries inserted at line ~12-13"""
    original = "---\\nname: test\\n---\\n\\nOriginal content"
    enhancement = {"sections": ["boundaries"], "boundaries": "## Boundaries\\n..."}

    result = applier.apply(agent_file, enhancement)

    # Boundaries should be at line 5 (after frontmatter + blank line)
    lines = result.split('\n')
    assert lines[4] == "## Boundaries"
```

✅ **AC-4.6**: Test backward compatibility:
```python
def test_parser_accepts_legacy_best_practices():
    """Verify parser handles old 'best_practices' format during transition"""
    response_old = '{"sections": ["best_practices"], "best_practices": "..."}'
    result = parser.parse(response_old)

    # Should accept but warn
    assert result is not None
    # Check warning logged
```

### 5. Integration Testing

✅ **AC-5.1**: End-to-end test with real agent enhancement:
```python
def test_end_to_end_boundaries_generation():
    """Verify full pipeline from prompt → parse → apply"""
    # Build prompt
    prompt = builder.build(agent_metadata, templates, template_dir)

    # Simulate AI response with boundaries
    ai_response = generate_mock_response_with_boundaries()

    # Parse response
    enhancement = parser.parse(ai_response)

    # Apply to agent file
    applier.apply(agent_file, enhancement)

    # Verify result
    content = agent_file.read_text()
    assert "## Boundaries" in content
    assert "### ALWAYS" in content
    assert "### NEVER" in content
    assert "### ASK" in content
    assert content.index("## Boundaries") < content.index("## Related Templates")
```

### 6. Documentation Updates

✅ **AC-6.1**: Update `CHANGELOG.md` with fix details:
```markdown
## [Version] - YYYY-MM-DD

### Fixed
- **TASK-STND-773D Complete**: Agent enhancement now generates Boundaries sections
  - Updated prompt_builder.py to request "boundaries" instead of "best_practices"
  - Added boundaries validation in parser.py (structure, counts, emoji format)
  - Enhanced applier.py to insert boundaries after frontmatter (line ~12)
  - Added comprehensive test coverage for boundaries pipeline
  - Backward compatible with legacy "best_practices" format during transition
  - **Impact**: Enhanced agents now achieve 9/10 boundary clarity (was 0/10)
```

✅ **AC-6.2**: Update `docs/guides/agent-enhancement-guide.md` (if exists):
- Document new boundaries section format
- Explain ALWAYS/NEVER/ASK framework
- Show example enhanced agent with boundaries
- Note deprecation of "best_practices" format

### 7. Validation Metrics

✅ **AC-7.1**: Enhanced agents pass all boundary validation checks:
```yaml
validation_report:
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  boundary_completeness:
    always_count: 5-7 ✅
    never_count: 5-7 ✅
    ask_count: 3-5 ✅
    emoji_correct: true ✅
    format_valid: true ✅
    placement_correct: true ✅
```

✅ **AC-7.2**: GitHub standards compliance:
- Boundary clarity: 0/10 → 9/10 ✅
- Overall quality score: +1.5 points ✅

---

## Implementation Plan

### Phase 1: Prompt Builder Update (2 hours)

**File**: `installer/global/lib/agent_enhancement/prompt_builder.py`

**Changes**:
1. Line 80: `3. Boundaries for this agent (ALWAYS do, NEVER do, ASK first)`
2. Line 86: `"sections": ["related_templates", "examples", "boundaries"],`
3. Line 89: `"boundaries": "## Boundaries\\n\\n### ALWAYS\\n- ✅ Rule 1 (rationale)\\n- ✅ Rule 2\\n...\\n\\n### NEVER\\n- ❌ Rule 1 (rationale)\\n- ❌ Rule 2\\n...\\n\\n### ASK\\n- ⚠️ Scenario 1\\n- ⚠️ Scenario 2\\n..."`
4. Lines 93-99: Add guidance on boundaries structure:
```python
**Boundaries Requirements**:
- ALWAYS: 5-7 non-negotiable rules with ✅ emoji
- NEVER: 5-7 prohibited actions with ❌ emoji
- ASK: 3-5 escalation scenarios with ⚠️ emoji
- Format: [emoji] [action] ([brief rationale])
- Derive from template patterns and anti-patterns
```

**Testing**:
- Run existing tests to ensure no regression
- Verify prompt contains "boundaries" string
- Verify prompt does NOT contain "best_practices" string

**Estimated Time**: 2 hours

---

### Phase 2: Parser Validation (4 hours)

**File**: `installer/global/lib/agent_enhancement/parser.py`

**New Methods**:

```python
def _validate_boundaries(self, boundaries_content: str) -> Dict[str, Any]:
    """
    Validate boundaries section structure and content.

    Checks:
    - Presence of ALWAYS/NEVER/ASK subsections
    - Rule counts (5-7/5-7/3-5)
    - Emoji prefixes (✅/❌/⚠️)
    - Format compliance

    Args:
        boundaries_content: Markdown content of boundaries section

    Returns:
        Dict with validation results and warnings

    Raises:
        ValueError: If critical structure violations found
    """
    validation = {
        "has_always": False,
        "has_never": False,
        "has_ask": False,
        "always_count": 0,
        "never_count": 0,
        "ask_count": 0,
        "emoji_correct": True,
        "warnings": []
    }

    # Parse sections
    lines = boundaries_content.split('\n')
    current_section = None

    for line in lines:
        # Detect subsection headers
        if line.strip() == "### ALWAYS":
            validation["has_always"] = True
            current_section = "always"
        elif line.strip() == "### NEVER":
            validation["has_never"] = True
            current_section = "never"
        elif line.strip() == "### ASK":
            validation["has_ask"] = True
            current_section = "ask"

        # Count rules and check emoji
        if line.strip().startswith('-'):
            if current_section == "always":
                validation["always_count"] += 1
                if not line.strip().startswith('- ✅'):
                    validation["emoji_correct"] = False
                    validation["warnings"].append(
                        f"ALWAYS rule missing ✅ emoji: {line.strip()}"
                    )
            elif current_section == "never":
                validation["never_count"] += 1
                if not line.strip().startswith('- ❌'):
                    validation["emoji_correct"] = False
                    validation["warnings"].append(
                        f"NEVER rule missing ❌ emoji: {line.strip()}"
                    )
            elif current_section == "ask":
                validation["ask_count"] += 1
                if not line.strip().startswith('- ⚠️'):
                    validation["emoji_correct"] = False
                    validation["warnings"].append(
                        f"ASK scenario missing ⚠️ emoji: {line.strip()}"
                    )

    # Validate subsection presence
    if not validation["has_always"]:
        raise ValueError("Boundaries section missing ALWAYS subsection")
    if not validation["has_never"]:
        raise ValueError("Boundaries section missing NEVER subsection")
    if not validation["has_ask"]:
        raise ValueError("Boundaries section missing ASK subsection")

    # Validate rule counts (warnings, not errors)
    if validation["always_count"] < 5 or validation["always_count"] > 7:
        validation["warnings"].append(
            f"ALWAYS rule count {validation['always_count']} outside 5-7 range"
        )
    if validation["never_count"] < 5 or validation["never_count"] > 7:
        validation["warnings"].append(
            f"NEVER rule count {validation['never_count']} outside 5-7 range"
        )
    if validation["ask_count"] < 3 or validation["ask_count"] > 5:
        validation["warnings"].append(
            f"ASK scenario count {validation['ask_count']} outside 3-5 range"
        )

    # Log warnings
    for warning in validation["warnings"]:
        logger.warning(f"Boundaries validation: {warning}")

    return validation
```

**Update `parse()` method**:
```python
def parse(self, response: str) -> Dict[str, Any]:
    # ... existing JSON extraction logic ...

    enhancement = json.loads(json_content)
    self._validate_basic_structure(enhancement)

    # NEW: Validate boundaries if present
    sections = enhancement.get("sections", [])

    # Handle legacy format
    if "best_practices" in sections:
        logger.warning(
            "Response uses deprecated 'best_practices' section. "
            "Please update to 'boundaries' format."
        )

    # Validate boundaries format
    if "boundaries" in sections:
        boundaries_content = enhancement.get("boundaries", "")
        validation_result = self._validate_boundaries(boundaries_content)

        # Attach validation metadata
        enhancement["_boundaries_validation"] = validation_result

    return enhancement
```

**Testing**:
- Test all subsection presence checks
- Test rule count validation (5-7/5-7/3-5)
- Test emoji validation (✅/❌/⚠️)
- Test backward compatibility with "best_practices"
- Test warning logging

**Estimated Time**: 4 hours

---

### Phase 3: Applier Placement Logic (3 hours)

**File**: `installer/global/lib/agent_enhancement/applier.py`

**Update `_merge_content()` method**:

```python
def _merge_content(self, original: str, enhancement: Dict[str, Any]) -> str:
    """
    Merge original content with enhancement sections.

    Strategy:
    1. Preserve frontmatter (YAML between ---...---)
    2. Insert boundaries after frontmatter (line ~12)
    3. Preserve existing content
    4. Append other sections at the end

    Args:
        original: Original file content
        enhancement: Enhancement dict with sections

    Returns:
        Merged content string
    """
    sections_to_add = enhancement.get("sections", [])

    # Split content into lines
    lines = original.split('\n')

    # Find end of frontmatter (if exists)
    frontmatter_end = self._find_frontmatter_end(lines)

    # Separate boundaries from other sections
    boundaries_section = None
    other_sections = []

    for section_name in sections_to_add:
        if section_name == "boundaries":
            boundaries_section = enhancement.get("boundaries", "")
        else:
            other_sections.append(section_name)

    # Build new content
    new_lines = lines[:frontmatter_end] if frontmatter_end > 0 else []

    # Insert boundaries after frontmatter
    if boundaries_section and boundaries_section.strip():
        # Add blank line after frontmatter if needed
        if new_lines and new_lines[-1].strip():
            new_lines.append("")

        # Add boundaries section
        new_lines.append(boundaries_section.strip())
        new_lines.append("")  # Blank line after boundaries

    # Add remaining original content (skip frontmatter)
    if frontmatter_end > 0:
        new_lines.extend(lines[frontmatter_end:])

    # Check if other sections already exist (avoid duplicates)
    existing_content = '\n'.join(new_lines)

    # Append other enhancement sections at end (existing logic)
    for section_name in other_sections:
        section_content = enhancement.get(section_name, "")

        if section_content and section_content.strip():
            section_header = f"## {section_name.replace('_', ' ').title()}"

            if section_header not in existing_content:
                # Add blank line before section if content exists
                if new_lines and new_lines[-1].strip():
                    new_lines.append("")

                # Add section content
                new_lines.append(section_content.strip())

    return '\n'.join(new_lines)

def _find_frontmatter_end(self, lines: list[str]) -> int:
    """
    Find line number where frontmatter ends.

    Frontmatter is YAML between two --- delimiters.

    Args:
        lines: File content as list of lines

    Returns:
        Line number after second --- (0 if no frontmatter)
    """
    frontmatter_count = 0

    for i, line in enumerate(lines):
        if line.strip() == '---':
            frontmatter_count += 1
            if frontmatter_count == 2:
                return i + 1  # Line after second ---

    return 0  # No frontmatter found
```

**Testing**:
- Test boundaries inserted after frontmatter
- Test boundaries NOT duplicated if already present
- Test boundaries placed before "Related Templates"
- Test boundaries placed before "Code Examples"
- Test backward compatibility with no frontmatter
- Test blank line insertion logic

**Estimated Time**: 3 hours

---

### Phase 4: Unit Testing (5 hours)

**New Test File**: `tests/unit/lib/agent_enhancement/test_boundaries_validation.py`

**Test Coverage**:

1. **Prompt Builder Tests** (1 hour):
   - `test_prompt_requests_boundaries_section()`
   - `test_prompt_specifies_boundaries_structure()`
   - `test_prompt_includes_emoji_requirements()`
   - `test_prompt_excludes_best_practices()`

2. **Parser Validation Tests** (2 hours):
   - `test_parser_validates_always_subsection()`
   - `test_parser_validates_never_subsection()`
   - `test_parser_validates_ask_subsection()`
   - `test_parser_validates_rule_counts()`
   - `test_parser_validates_emoji_prefixes()`
   - `test_parser_accepts_legacy_best_practices()`
   - `test_parser_warns_on_missing_emoji()`
   - `test_parser_warns_on_incorrect_counts()`

3. **Applier Placement Tests** (2 hours):
   - `test_applier_finds_frontmatter_end()`
   - `test_applier_inserts_boundaries_after_frontmatter()`
   - `test_applier_preserves_existing_content()`
   - `test_applier_avoids_duplicate_boundaries()`
   - `test_applier_inserts_blank_lines_correctly()`
   - `test_applier_handles_no_frontmatter()`

**Test Fixtures**:

```python
# tests/fixtures/agent_enhancement.py

MOCK_AGENT_METADATA = {
    "name": "test-specialist",
    "description": "Test agent for boundaries validation",
    "tools": ["Read", "Write"],
    "tags": ["testing"]
}

MOCK_TEMPLATES = [
    Path("templates/test/TestComponent.tsx.template"),
    Path("templates/test/TestRepository.cs.template")
]

MOCK_RESPONSE_WITH_BOUNDARIES = """{
    "sections": ["related_templates", "examples", "boundaries"],
    "related_templates": "## Related Templates\\n\\n- template1\\n- template2",
    "examples": "## Code Examples\\n\\n### Example 1\\n```code```",
    "boundaries": "## Boundaries\\n\\n### ALWAYS\\n- ✅ Rule 1 (rationale)\\n- ✅ Rule 2\\n- ✅ Rule 3\\n- ✅ Rule 4\\n- ✅ Rule 5\\n- ✅ Rule 6\\n\\n### NEVER\\n- ❌ Rule 1 (rationale)\\n- ❌ Rule 2\\n- ❌ Rule 3\\n- ❌ Rule 4\\n- ❌ Rule 5\\n- ❌ Rule 6\\n\\n### ASK\\n- ⚠️ Scenario 1\\n- ⚠️ Scenario 2\\n- ⚠️ Scenario 3\\n- ⚠️ Scenario 4"
}"""

MOCK_RESPONSE_LEGACY_BEST_PRACTICES = """{
    "sections": ["related_templates", "examples", "best_practices"],
    "related_templates": "## Related Templates\\n\\n- template1",
    "examples": "## Code Examples\\n\\n### Example 1",
    "best_practices": "## Best Practices\\n\\n1. Practice 1\\n2. Practice 2"
}"""

MOCK_AGENT_FILE_CONTENT = """---
name: test-specialist
description: Test agent
tools: [Read, Write]
tags: [testing]
---

# Test Specialist

Existing agent content.
"""
```

**Estimated Time**: 5 hours

---

### Phase 5: Integration Testing (2 hours)

**Test File**: `tests/integration/lib/agent_enhancement/test_boundaries_e2e.py`

**End-to-End Test**:

```python
def test_full_boundaries_pipeline():
    """
    Verify complete pipeline from prompt → parse → apply.

    Steps:
    1. Build prompt with boundaries request
    2. Mock AI response with valid boundaries
    3. Parse response and validate boundaries
    4. Apply boundaries to agent file
    5. Verify final agent file structure
    """
    # Setup
    builder = EnhancementPromptBuilder()
    parser = EnhancementParser()
    applier = EnhancementApplier()

    # Create temp agent file
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text(MOCK_AGENT_FILE_CONTENT)

    # 1. Build prompt
    prompt = builder.build(
        MOCK_AGENT_METADATA,
        MOCK_TEMPLATES,
        tmp_path / "templates"
    )

    # Verify prompt requests boundaries
    assert '"boundaries"' in prompt
    assert "### ALWAYS" in prompt
    assert "### NEVER" in prompt
    assert "### ASK" in prompt

    # 2. Parse mock response
    enhancement = parser.parse(MOCK_RESPONSE_WITH_BOUNDARIES)

    # Verify parsing succeeded
    assert "boundaries" in enhancement["sections"]
    assert enhancement["_boundaries_validation"]["has_always"]
    assert enhancement["_boundaries_validation"]["has_never"]
    assert enhancement["_boundaries_validation"]["has_ask"]

    # 3. Apply to agent file
    applier.apply(agent_file, enhancement)

    # 4. Verify result
    result_content = agent_file.read_text()
    lines = result_content.split('\n')

    # Find boundaries section
    boundaries_line = None
    for i, line in enumerate(lines):
        if line.strip() == "## Boundaries":
            boundaries_line = i
            break

    assert boundaries_line is not None, "Boundaries section not found"

    # Verify placement (should be after frontmatter, around line 12-15)
    assert 10 <= boundaries_line <= 20, f"Boundaries at line {boundaries_line}, expected 10-20"

    # Verify subsections present
    assert "### ALWAYS" in result_content
    assert "### NEVER" in result_content
    assert "### ASK" in result_content

    # Verify emoji prefixes
    assert "✅" in result_content
    assert "❌" in result_content
    assert "⚠️" in result_content

    # Verify ordering (boundaries before related templates)
    boundaries_index = result_content.index("## Boundaries")
    templates_index = result_content.index("## Related Templates")
    assert boundaries_index < templates_index
```

**Estimated Time**: 2 hours

---

### Phase 6: Documentation & Changelog (2 hours)

**Files to Update**:

1. **CHANGELOG.md** (30 min):
   - Add entry under appropriate version
   - Document fix for TASK-STND-773D
   - List all changed files
   - Note backward compatibility

2. **docs/guides/agent-enhancement-guide.md** (if exists, 1 hour):
   - Add section on boundaries format
   - Show example enhanced agent with boundaries
   - Explain ALWAYS/NEVER/ASK framework
   - Note migration from best_practices

3. **installer/global/agents/agent-content-enhancer.md** (30 min):
   - Already updated in TASK-STND-773D
   - Verify alignment with implementation
   - Add note that implementation is now complete

**Estimated Time**: 2 hours

---

## Testing Strategy

### Test Levels

**1. Unit Tests** (files in isolation):
- `test_prompt_builder.py` - Prompt generation
- `test_parser.py` - Response parsing & validation
- `test_applier.py` - Content merging & placement

**2. Integration Tests** (cross-file interaction):
- `test_boundaries_e2e.py` - Full pipeline
- `test_backward_compatibility.py` - Legacy format handling

**3. Acceptance Tests** (real-world scenarios):
- Run `/agent-enhance` on actual template
- Verify enhanced agent has boundaries
- Validate boundaries format manually
- Check GitHub compliance score

### Test Data

**Valid Boundaries**:
```markdown
## Boundaries

### ALWAYS
- ✅ Validate input schemas (prevent invalid data processing)
- ✅ Run tests before approval (quality gate enforcement)
- ✅ Log decision rationale (audit trail maintenance)
- ✅ Execute in technology-specific runner (pytest/vitest/dotnet test)
- ✅ Block on compilation failures (prevent false positive tests)
- ✅ Enforce coverage thresholds (≥80% line, ≥75% branch)

### NEVER
- ❌ Never skip validation checks (security risk)
- ❌ Never assume defaults (explicit configuration required)
- ❌ Never auto-approve without review (quality gate bypass prohibited)
- ❌ Never proceed with failing tests (zero tolerance policy)
- ❌ Never modify production config (manual approval required)
- ❌ Never lower coverage without justification (quality standards)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Breaking changes required: Ask before implementing API changes
- ⚠️ Security tradeoffs: Ask if performance weakens security posture
- ⚠️ Ambiguous requirements: Ask if acceptance criteria conflict
```

**Invalid Boundaries** (for negative testing):
- Missing ALWAYS section
- Missing emoji prefixes
- Rule counts outside range (3 ALWAYS, 9 NEVER, 1 ASK)
- Wrong emoji (✅ in NEVER section)

### Coverage Targets

- **Line Coverage**: ≥80%
- **Branch Coverage**: ≥75%
- **Function Coverage**: 100% (all public methods tested)

### Test Execution

```bash
# Run all enhancement tests
pytest tests/unit/lib/agent_enhancement/ -v --cov=installer/global/lib/agent_enhancement --cov-report=term

# Run boundaries-specific tests
pytest tests/unit/lib/agent_enhancement/test_boundaries_validation.py -v

# Run integration tests
pytest tests/integration/lib/agent_enhancement/test_boundaries_e2e.py -v

# Generate coverage report
pytest tests/ --cov=installer/global/lib/agent_enhancement --cov-report=html
```

---

## Risk Assessment

### High Risk

**1. Breaking Changes to Existing Enhanced Agents**

**Risk**: Agents enhanced before this fix have "Best Practices" sections that won't be recognized by new validation logic.

**Mitigation**:
- Backward compatibility in parser (accept "best_practices")
- Warn users about deprecated format
- Provide migration guide
- Don't fail on old format during transition period (90 days)

**2. AI Response Format Changes**

**Risk**: AI might not follow new boundaries format correctly.

**Mitigation**:
- Clear, detailed prompt with examples
- Validation in parser with helpful error messages
- Iterative refinement loop (max 3 attempts)
- Fallback to legacy format if boundaries generation fails

### Medium Risk

**3. Placement Logic Errors**

**Risk**: Boundaries inserted at wrong location (breaks agent readability).

**Mitigation**:
- Comprehensive unit tests for placement
- Integration test verifies correct ordering
- Manual review of first enhanced agent
- Rollback plan if placement broken

**4. Emoji Rendering Issues**

**Risk**: Emoji might not render correctly in all environments.

**Mitigation**:
- Test emoji rendering in markdown preview
- Use standard Unicode emoji (not custom)
- Fallback text format if needed:
  - `[ALWAYS]` instead of ✅
  - `[NEVER]` instead of ❌
  - `[ASK]` instead of ⚠️

### Low Risk

**5. Performance Impact**

**Risk**: Additional validation adds processing time.

**Mitigation**:
- Validation is lightweight (string parsing)
- Only runs during enhancement (not runtime)
- Expected impact: <100ms per agent

**6. Test Flakiness**

**Risk**: Integration tests might fail intermittently.

**Mitigation**:
- Use deterministic test data (no AI calls in tests)
- Mock file I/O with temp directories
- Cleanup fixtures after each test

---

## Rollback Plan

### Rollback Triggers

- ✅ **FAIL**: >10% of unit tests fail
- ✅ **FAIL**: Integration test fails
- ✅ **FAIL**: Enhanced agent file corrupted (invalid markdown)
- ⚠️ **WARN**: Coverage drops below 75%

### Rollback Steps

1. **Immediate Revert** (5 minutes):
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Restore Legacy Behavior** (10 minutes):
   - Revert `prompt_builder.py` to request "best_practices"
   - Disable boundaries validation in `parser.py`
   - Keep applier changes (backward compatible)

3. **Verify Restoration** (15 minutes):
   ```bash
   pytest tests/unit/lib/agent_enhancement/ -v
   # Should pass 100%
   ```

4. **Communication** (30 minutes):
   - Update CHANGELOG with rollback notice
   - Document why rollback occurred
   - Create follow-up task to fix issues

### Partial Rollback Options

**Option A**: Keep prompt changes, disable validation
- Agents get boundaries sections but no validation
- Allows gradual validation rule tuning

**Option B**: Keep validation, revert prompt
- Keep requesting "best_practices" temporarily
- Validation ready for future re-enable

**Option C**: Feature flag (requires additional work)
- Add `ENABLE_BOUNDARIES_VALIDATION` env var
- Toggle between old/new behavior
- Gradual rollout strategy

---

## Success Metrics

### Code Quality Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| **Boundary Clarity** | 0/10 | - | 9/10 |
| **Unit Test Coverage** | - | - | ≥80% |
| **Integration Tests** | - | - | 1 E2E test passing |
| **Documentation** | Partial | - | Complete |

### Enhanced Agent Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| **Boundaries Section Present** | 0% | - | 100% |
| **ALWAYS Rules (5-7)** | N/A | - | 100% |
| **NEVER Rules (5-7)** | N/A | - | 100% |
| **ASK Scenarios (3-5)** | N/A | - | 100% |
| **Emoji Format Correct** | N/A | - | 100% |
| **Placement Correct** | N/A | - | 100% (after frontmatter) |

### GitHub Compliance

| Standard | Before | After | Target |
|----------|--------|-------|--------|
| **Boundary Clarity** | 0/10 | - | 9/10 |
| **Overall Quality Score** | 8.77/10 | - | 9.2/10 |
| **Developer Satisfaction** | Baseline | - | +15% |
| **Misuse Incidents** | Baseline | - | -60% |
| **Unnecessary Escalations** | Baseline | - | -40% |

### Validation Success Rate

| Validation Check | Target |
|------------------|--------|
| **Structure Valid** | ≥95% |
| **Rule Counts Valid** | ≥90% |
| **Emoji Format Valid** | ≥95% |
| **Placement Correct** | 100% |

---

## Dependencies

### Internal Dependencies

- `installer/global/lib/agent_enhancement/prompt_builder.py` (exists)
- `installer/global/lib/agent_enhancement/parser.py` (exists)
- `installer/global/lib/agent_enhancement/applier.py` (exists)
- `installer/global/agents/agent-content-enhancer.md` (updated in TASK-STND-773D)

### External Dependencies

- None (all Python stdlib)

### Blocked By

- None

### Blocks

- TASK-AGENT-BOUND (depends on this infrastructure being in place)
- Template enhancement workflows (waiting for correct boundaries generation)
- GitHub compliance improvements (boundary clarity is Critical Gap #4)

---

## Related Tasks

### Parent/Predecessor

- **TASK-STND-773D** (completed 814d810): Documentation update only, implementation incomplete

### Child/Successor Tasks

- **TASK-AGENT-BOUND**: Apply boundaries to all 15 global agents (15 hours)
- **TASK-VALIDATE-ENHANCED**: Validate all enhanced agents meet GitHub standards
- **TASK-MIGRATION-GUIDE**: Document migration from best_practices to boundaries

### Related Work

- **GitHub Analysis** (docs/analysis/github-agent-best-practices-analysis.md): Identified Critical Gap #4
- **Agent Content Enhancer** (installer/global/agents/agent-content-enhancer.md): Specifies boundaries format

---

## Definition of Done

- [ ] All acceptance criteria (AC-1.1 through AC-7.2) met
- [ ] Code changes implemented in all 3 files (prompt_builder.py, parser.py, applier.py)
- [ ] Unit tests passing (≥80% coverage)
- [ ] Integration test passing (E2E boundaries pipeline)
- [ ] Documentation updated (CHANGELOG.md, guides)
- [ ] Manual testing completed (real agent enhancement)
- [ ] GitHub compliance verified (boundary clarity 9/10)
- [ ] Code reviewed and approved
- [ ] No regressions in existing tests
- [ ] Backward compatibility confirmed (legacy format accepted)

---

## Notes

### Context from TASK-STND-773D

Original task (commit 814d810) updated:
- ✅ `installer/global/agents/agent-content-enhancer.md` (lines 64-92, 395-436)
- ✅ Quality requirements (lines 148-167, 302-314)
- ❌ **Missing**: Implementation in prompt_builder.py, parser.py, applier.py

### Why This Matters

From GitHub analysis (docs/analysis/github-agent-best-practices-analysis.md):
- "Explicit boundaries prevent costly mistakes and reduce human intervention by 40%"
- "Boundary clarity correlates with 8+ satisfaction scores"
- "Critical Gap #4" with 0/10 current score

### Technical Debt

If not fixed:
- All enhanced agents fail boundary validation
- Developer confusion about agent authority continues
- Misuse incidents remain high
- GitHub compliance score artificially lowered
- Template creation workflow produces substandard agents

---

**Ready for /task-create**: Yes
**Estimated Total Effort**: 12-16 hours
**Priority**: High (P0 - Critical Gap)
**Complexity**: 6/10 (Medium - clear requirements, moderate testing scope)
