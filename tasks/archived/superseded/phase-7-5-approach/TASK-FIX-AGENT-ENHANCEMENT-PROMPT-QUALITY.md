---
id: TASK-FIX-AGENT-ENHANCEMENT-PROMPT-QUALITY
title: "Fix Agent Enhancement: Explicit Section Requirements with Few-Shot Examples"
status: backlog
priority: critical
created: 2025-11-18
updated: 2025-11-18
estimated_effort: 2.5-3 hours
complexity: 5/10
tags:
  - enhancement
  - template-creation
  - agent-enhancement
  - prompt-engineering
  - phase-7-5
  - focused-fix
dependencies: []
related_tasks:
  - TASK-PHASE-7-5-BATCH-PROCESSING (batch enhancement)
reviews:
  - architectural-reviewer: 72/100 (approved with recommendations)
  - code-reviewer: 6.5/10 (approved with required changes)
confidence_assessment:
  current_fix_only: 55%
  with_all_enhancements: 85%
  target: 80%+
strategic_context: |
  This is the ONLY broken component in template-create. The 8-phase redesign
  proposal was rejected (9/10 scope creep). This focused 2.5-3 hour fix
  addresses the actual problem: poor prompt quality in agent_enhancer.py.
---

# Fix Agent Enhancement: Explicit Section Requirements with Few-Shot Examples

## Executive Summary

**Problem**: The prompt fix to add explicit section requirements is NECESSARY but NOT SUFFICIENT for high-quality agent generation. The AI already receives these section requirements in `_get_enhancement_instructions()` but produces generic 80-100 line content instead of the expected 150-250 lines with specific code references.

**Root Cause**: The AI lacks understanding of:
1. What "high-quality" means for agent documentation
2. How to extract patterns from code samples
3. The expected density of code examples vs prose

**Solution**: Enhance the prompt with:
1. Few-shot example output (shows exactly what good agent documentation looks like)
2. Negative examples (shows what will be rejected)
3. Section-specific length and content guidance
4. Improved validation (check for code blocks, template references, placeholders)

**Expected Impact**: Increase pass rate from 40-60% to 80-90%, with quality score improving from 5-6/10 to 7-8/10.

## Problem Statement

### Current Behavior

The AI generates content that:
- Is too short (80-100 lines vs 150-250 expected)
- Has generic practices without code references ("Use interfaces", "Follow SOLID")
- Missing required sections (especially "Code Examples")
- Fails validation and gets rejected

### Expected Behavior

AI-generated agents should match quality similar to built-in templates like `database-specialist.md` (910 lines) and `fastapi-specialist.md` (323 lines):
- Specific code examples from actual templates
- Template references with file paths and line numbers
- Best practices extracted from real code patterns
- Constraints based on actual template limitations

### Why Simple Section Enforcement Fails

The `_get_enhancement_instructions()` already specifies the 4 required sections, but:
1. Instructions are too abstract ("Extract patterns from template code")
2. No concrete example of expected output quality
3. No demonstration of expected depth per section
4. AI doesn't understand the quality bar

## Proposed Solution

### Priority 1: Add Few-Shot Example Output (CRITICAL)

**Impact**: Highest - teaches AI by example what quality looks like

Add a concrete 180-line example showing:
- Exact JSON format expected
- Specific template path references with line numbers
- Code blocks with proper syntax highlighting
- Placeholder usage ({{EntityName}})
- Proper section structure and depth

### Priority 2: Add Negative Examples (REQUIRED)

**Impact**: High - shows AI what will be rejected

Examples of:
- Generic content without code references (❌)
- Missing specific line numbers (❌)
- Placeholder code like "// implementation here" (❌)
- Practices without template evidence (❌)

### Priority 3: Section-Specific Length and Content Guidance (REQUIRED)

**Impact**: Medium - ensures proper depth per section

```
Section Length Guidelines:
- Template References: 50-80 lines (15-25 lines per template, including code snippets)
- Best Practices: 60-100 lines (15-20 lines per practice with code examples)
- Code Examples: 40-60 lines (actual working code, not pseudocode)
- Constraints: 20-40 lines (specific warnings with rationale)
```

### Priority 4: Improved Validation (RECOMMENDED)

**Impact**: Medium - catches low-quality content that passes basic structure checks

Add checks for:
- Minimum code blocks (at least 2)
- Template path references (must contain "templates/")
- Placeholder syntax (must contain "{{" and "}}")

## Implementation Plan

### Phase 1: Enhance Prompt with Few-Shot Example (45 minutes)

**File**: `installer/core/lib/template_creation/agent_enhancer.py`
**Location**: `_build_batch_prompt()` after line 1166

Add complete example output showing:
```python
example_output = """
**EXAMPLE OUTPUT** (follow this format):

For an agent named "repository-pattern-specialist", your output should be:

```json
{
  "agent_name": "repository-pattern-specialist",
  "enhanced_content": "---\\nname: repository-pattern-specialist\\n...

## Template References

### Primary Templates

**templates/repositories/LoadingRepository.cs.template**
- Demonstrates: Repository pattern with async CRUD operations and ErrorOr return types
- Key Pattern (lines 15-28): `public async Task<ErrorOr<Loading>> GetByIdAsync(string id)`
- When to use: All data access operations requiring explicit error handling

## Best Practices

### 1. Always Return ErrorOr for Database Operations

From `LoadingRepository.cs.template` lines 15-28:

```csharp
public async Task<ErrorOr<Loading>> GetByIdAsync(string id, CancellationToken ct)
{
    try
    {
        var result = await _realm.FindAsync<LoadingEntity>(id);
        if (result == null)
            return Error.NotFound(\"Loading.NotFound\", $\"Loading {id} not found\");
        return result.ToLoading();
    }
    catch (Exception ex)
    {
        return Error.Failure(\"Loading.GetFailed\", ex.Message);
    }
}
```

## Code Examples

### Complete Repository Implementation

```csharp
public class {{EntityName}}Repository : IRepository<{{EntityName}}>
{
    private readonly IRealmService _realm;

    public async Task<ErrorOr<{{EntityName}}>> GetByIdAsync(string id, CancellationToken ct)
    {
        // Implementation from template
    }
}
```

## Constraints

### Do NOT
- Return null from repository methods - use ErrorOr<T> instead
- Throw exceptions for expected conditions (not found, validation)
..."
}
```

This example shows ~180 lines of high-quality agent documentation.
"""
```

### Phase 2: Add Negative Examples (15 minutes)

**Location**: After the example output

```python
negative_examples = """
**REJECTED CONTENT** (do NOT generate):

❌ Generic (will be rejected):
```markdown
## Best Practices
- Use interfaces
- Follow SOLID principles
- Write clean code
```

❌ Missing code references (will be rejected):
```markdown
## Template References
The templates show good patterns for repository implementation.
```

✅ Specific content (expected):
```markdown
## Best Practices
### 1. Use ErrorOr for Explicit Error Handling
Based on `LoadingRepository.cs.template` lines 42-58:
```csharp
public async Task<ErrorOr<bool>> SaveAsync(...)
```
```
"""
```

### Phase 3: Add Section-Specific Guidelines (15 minutes)

**Location**: Replace current `_get_enhancement_instructions()` content (lines 1068-1114)

```python
def _get_enhancement_instructions(self) -> str:
    return """
**REQUIRED SECTIONS (all must be present):**

1. **Template References** (50-80 lines)
   - 2-3 primary templates from catalog
   - For EACH template, provide:
     * File path (exact, from catalog)
     * 10-15 line code snippet from template
     * 2-3 sentences explaining the pattern
     * When to use this template

2. **Best Practices** (60-100 lines)
   - 3-5 practices extracted FROM THE CODE SAMPLES
   - Each practice MUST include:
     * Practice name
     * Code reference (file + line or code snippet)
     * 2-3 sentence explanation
   - Do NOT list generic SOLID principles without code references

3. **Code Examples** (40-60 lines)
   - 1-2 realistic examples based on template patterns
   - Must use actual syntax from the code samples
   - Include proper placeholders with {{syntax}}
   - Show complete, working code (not pseudocode)

4. **Constraints** (20-40 lines)
   - What this agent should NOT do
   - Technology limitations based on templates
   - Anti-patterns to avoid (reference actual code)

**CONTENT WILL BE REJECTED IF:**
- Any section is missing
- Total lines < 150
- Generic practices without code references
- Placeholder code like "// implementation here"
"""
```

### Phase 4: Improve Validation (30 minutes)

**Location**: `_validate_enhancement()` (lines 1321-1361)

Add content quality checks:
```python
def _validate_enhancement(self, content: str) -> bool:
    """Validate enhanced agent content meets quality standards."""
    lines = content.split("\n")
    line_count = len(lines)

    # Minimum length check
    if line_count < 150:
        logger.warning(f"Enhancement too short: {line_count} lines (expected >= 150)")
        return False

    # Required sections check
    required_sections = [
        "Template References",
        "Best Practices",
        "Code Examples",
        "Constraints"
    ]

    for section in required_sections:
        if section not in content:
            logger.warning(f"Missing required section: {section}")
            return False

    # NEW: Content quality checks

    # Check for code blocks (at least 2 complete blocks = 4 backtick markers)
    code_block_count = content.count("```")
    if code_block_count < 4:
        logger.warning(f"Insufficient code blocks: {code_block_count // 2} (expected >= 2)")
        return False

    # Check for template path references
    if "templates/" not in content:
        logger.warning("No template path references found")
        return False

    # Check for placeholder syntax
    if "{{" not in content or "}}" not in content:
        logger.warning("No placeholder syntax found (e.g., {{EntityName}})")
        return False

    # Maximum length warning (not blocking)
    if line_count > 250:
        logger.warning(f"Enhancement longer than expected: {line_count} lines")

    return True
```

### Phase 5: Reorder Prompt for Better Attention (15 minutes)

Put critical information (example output, requirements) BEFORE the code samples so AI sees them first:

```python
return f"""You are enhancing AI agent documentation files with template-specific content.

**CRITICAL: Read the EXAMPLE OUTPUT section below before proceeding.**

**Agents to Enhance ({len(agents)} total):**
{agents_list}

{example_output}

{negative_examples}

**Enhancement Guidelines:**
{instructions}

**Available Templates:**
{catalog_text}

**Template Code Samples (for reference):**
{code_samples_text}

**Output Format:**
Return JSON with structure:
{{
  "enhancements": [
    {{
      "agent_name": "agent-file-name",
      "enhanced_content": "complete markdown with frontmatter"
    }}
  ]
}}

Generate the enhancements now:"""
```

## Acceptance Criteria

### Must Have (Critical)

1. ✅ **Few-shot example output**:
   - Complete 150-180 line example of high-quality agent documentation
   - Shows exact JSON format expected
   - Demonstrates specific template references with line numbers
   - Includes proper code blocks with syntax highlighting

2. ✅ **Negative examples**:
   - Shows generic content that will be rejected
   - Shows content without code references
   - Clear ❌ and ✅ indicators

3. ✅ **Section-specific guidelines**:
   - Line count per section (50-80, 60-100, 40-60, 20-40)
   - Content requirements per section
   - Explicit rejection criteria

4. ✅ **Quality validation**:
   - Check for minimum code blocks (≥2)
   - Check for template path references
   - Check for placeholder syntax

5. ✅ **Pass rate**: ≥80% of enhanced agents pass validation
6. ✅ **Quality score**: Enhanced agents score 7-8/10 (comparable to built-in)

### Should Have (Important)

7. ✅ **Prompt reordering**: Critical information before code samples
8. ✅ **Quality metrics logging**: Track code blocks, template refs, placeholders

### Could Have (Nice to Have)

9. ⚪ **Two-phase enhancement**: Separate pattern extraction from documentation generation
10. ⚪ **Template-specific prompts**: Different prompt structure per technology

## Token Budget Analysis

**Current Budget**:
- Agents list: ~500 tokens
- Template catalog: ~1,000 tokens
- Code samples: ~3,750 tokens
- Enhancement instructions: ~500 tokens
- **Total**: ~5,750 tokens

**Additional Content**:
- Few-shot example: ~750 tokens
- Negative examples: ~150 tokens
- Enhanced instructions: ~300 tokens
- **Additional total**: ~1,200 tokens

**New Total**: ~6,950 tokens (well within 100k limit)

## Expected Outcomes

### Before (Current Fix Only)

| Metric | Value |
|--------|-------|
| Pass Rate | 40-60% |
| Avg Length | 80-120 lines |
| Code References | 1-2 |
| Quality Score | 5-6/10 |

### After (All Enhancements)

| Metric | Value |
|--------|-------|
| Pass Rate | 80-90% |
| Avg Length | 150-200 lines |
| Code References | 5-8 |
| Quality Score | 7-8/10 |

## Quality Comparison

### Built-in Templates (9-10/10)
- Hand-crafted by domain experts
- 300-900+ lines with deep examples
- Nuanced explanations and edge cases

### AI-Generated with Enhancements (7-8/10)
- Follows structured pattern
- 150-200 lines with specific references
- Good practices from actual code

**Note**: AI-generated agents will be functional and useful but won't match the encyclopedic depth of hand-crafted agents. This is acceptable for the use case.

## Testing Strategy

### Unit Tests (5 new tests)

1. `test_validation_checks_code_blocks` - Verify code block count validation
2. `test_validation_checks_template_refs` - Verify template path validation
3. `test_validation_checks_placeholders` - Verify placeholder syntax validation
4. `test_prompt_includes_example_output` - Verify example in prompt
5. `test_prompt_includes_negative_examples` - Verify negative examples in prompt

### Manual Verification

1. Run `/template-create` on MAUI project
2. Verify enhanced agents have ≥150 lines
3. Verify agents include specific code references from templates
4. Verify agents pass validation (≥80% pass rate)
5. Compare quality to built-in templates

## Risk Assessment

### Prompt Complexity Risk
**Analysis**: MEDIUM
- Longer prompts can confuse AI
- **Mitigation**: Clear structure with headers, examples before content

### Token Budget Risk
**Analysis**: LOW
- Adding ~1,200 tokens to ~5,750
- Well within 100k context limit

### Quality Gap Risk
**Analysis**: MEDIUM
- AI may still produce lower quality than built-in
- **Mitigation**: 7-8/10 is acceptable; can improve iteratively

## Rollback Plan

If enhancements don't improve quality:
1. A/B test individual changes (example only, negative only, etc.)
2. Consider two-phase enhancement (pattern extraction → documentation)
3. Fall back to template-specific prompts per technology

## Estimated Effort

**Total**: 2-3 hours

- Phase 1 (Few-shot example): 45 minutes
- Phase 2 (Negative examples): 15 minutes
- Phase 3 (Section guidelines): 15 minutes
- Phase 4 (Validation improvements): 30 minutes
- Phase 5 (Prompt reordering): 15 minutes
- Testing: 30 minutes
- Manual verification: 30 minutes

## Notes

This task builds on TASK-PHASE-7-5-INCLUDE-TEMPLATE-CODE-SAMPLES which provides relevance-based template selection. Both tasks together address the complete agent enhancement quality problem:

1. **Relevance selection** (previous task): Ensures AI receives correct templates for each agent
2. **Prompt quality** (this task): Ensures AI generates high-quality content from those templates

The combination should achieve the target 80%+ pass rate with 7-8/10 quality score.

## Architectural Review Recommendations (72/100)

Based on architectural review:

### Priority 1: Extract Constants for DRY (10 minutes)

```python
# At top of agent_enhancer.py
REQUIRED_SECTIONS = [
    "Template References",
    "Best Practices",
    "Code Examples",
    "Constraints"
]

QUALITY_THRESHOLDS = {
    "min_lines": 150,
    "max_lines": 250,
    "min_code_blocks": 2,
}

SECTION_REQUIREMENTS = {
    "Template References": {"min_chars": 500, "min_code_blocks": 0},
    "Best Practices": {"min_chars": 400, "min_code_blocks": 2},
    "Code Examples": {"min_chars": 300, "min_code_blocks": 1},
    "Constraints": {"min_chars": 150, "min_code_blocks": 0}
}
```

### Priority 2: Split Validation for SRP (10 minutes)

```python
def _validate_enhancement(self, content: str) -> bool:
    """Orchestrate all validation checks."""
    return (
        self._validate_structure(content) and
        self._validate_content_quality(content)
    )

def _validate_structure(self, content: str) -> bool:
    """Validate required sections are present."""
    for section in REQUIRED_SECTIONS:
        if section not in content:
            logger.warning(f"Missing required section: {section}")
            return False
    return True

def _validate_content_quality(self, content: str) -> bool:
    """Validate content quality metrics."""
    # See implementation in Phase 4 above
    pass
```

### Priority 3: Consider Prompt Template Files (Optional)

For future maintainability, consider extracting prompts to:
```
installer/core/lib/template_creation/
    prompts/
        agent_enhancement_example.md
        agent_enhancement_negative.md
```

## Code Review Recommendations (6.5/10)

Based on code review:

### Required Change 1: Expand Few-Shot Example to 220+ Lines

The example must include ALL sections that appear in final output:
- Purpose
- When to Use This Agent (4 scenarios)
- Template References (2-3 with code snippets)
- Best Practices (3-5 with code examples)
- Code Examples (complete implementation)
- Constraints (5-7 bullet points)
- Technologies
- Usage in Taskwright

### Required Change 2: Section Content Validation

Add `_extract_section_content()` helper:

```python
def _extract_section_content(self, content: str, section_name: str) -> str:
    """Extract content between section header and next section."""
    import re

    pattern = rf"##\s*{re.escape(section_name)}\s*\n"
    match = re.search(pattern, content)
    if not match:
        return ""

    start = match.end()
    next_section = re.search(r"\n##\s+", content[start:])
    end = start + next_section.start() if next_section else len(content)

    return content[start:end]
```

### Required Change 3: Add Quality Rubric to Prompt

```markdown
**Quality Scoring (aim for 8+):**
- 9-10: All sections with deep examples, 200+ lines, 8+ template refs
- 7-8: All sections with good examples, 150-200 lines, 5-7 template refs
- 5-6: All sections but sparse content, <150 lines (BORDERLINE)
- <5: Missing sections or no template references (REJECTED)
```

### Required Change 4: Reorder Prompt for Attention

Put critical information (examples, guidelines) BEFORE template catalog:
1. Role and critical instructions
2. Few-shot example
3. Negative examples
4. Section guidelines
5. Quality rubric
6. Agent list
7. Template catalog
8. Code samples
9. Output format reminder

## Definition of Done

1. ✅ All acceptance criteria met
2. ✅ Constants extracted (DRY improvement)
3. ✅ Validation split (SRP improvement)
4. ✅ Few-shot example is 220+ lines
5. ✅ Section content validation implemented
6. ✅ Unit tests pass
7. ✅ Manual verification: ≥80% pass rate
8. ✅ Manual verification: 3 agents score ≥7/10 average
9. ✅ Code committed and task moved to IN_REVIEW
