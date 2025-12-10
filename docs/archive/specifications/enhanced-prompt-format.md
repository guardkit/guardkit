# Enhanced Prompt Format Specification

**Version**: 1.0.0
**Status**: Implemented (TASK-042)
**Date**: 2025-01-07

## Overview

This document specifies the enhanced prompt format used in template generation to guide AI toward creating complete CRUD scaffolding rather than representative samples.

## Purpose

The enhanced prompt format addresses the completeness gap identified in TASK-020 by:
1. Explicitly stating CRUD completeness requirements
2. Explaining layer symmetry rules
3. Clarifying pattern completeness expectations
4. Reminding AI that users need complete operations, not samples

## Prompt Structure

### Base Prompt Structure

```
Convert this {language} file into a reusable template by replacing specific values with placeholders.

**Original File**: {file_path}
**Purpose**: {purpose}
**Language**: {language}

{COMPLETENESS_REQUIREMENTS}

**Instructions**:
[Standard placeholder extraction instructions]

**Original Content**:
```{language}
{content}
```

**Output Format**:
[Standard output format]
```

### Completeness Requirements Section

The completeness requirements section is injected after the file metadata and before the standard instructions:

```markdown
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
```

## Design Principles

### 1. Explicitness
- **Don't assume AI knows**: State requirements explicitly
- **Use clear language**: "ALL must be generated" not "should generate"
- **Define terms**: Explain what "layer symmetry" means

### 2. Visual Emphasis
- **Bold headers**: `**CRITICAL - TEMPLATE COMPLETENESS**`
- **Checkmarks**: Use ✓ to highlight required items
- **Structured lists**: Break down requirements into digestible bullets

### 3. Repetition
- State key concepts multiple times
- Use different phrasings ("CRUD completeness", "complete operations", "ALL CRUD")
- End with reminder about user needs

### 4. Context Setting
- Explain why completeness matters ("SCAFFOLDING for complete features")
- Contrast with wrong approach ("not just examples", "not representative samples")
- Frame as user requirement ("Users need...")

### 5. Pattern-Specific Guidance
- REPR pattern for FastEndpoints projects
- Repository pattern for Clean Architecture
- Layer symmetry for multi-tier applications

## Implementation Location

**File**: `installer/core/lib/template_generator/template_generator.py`

**Method**: `_create_extraction_prompt()`

**Lines**: ~201-284 (as of TASK-042)

## Token Budget

The completeness requirements section adds approximately **150-200 tokens** to each prompt:
- CRUD Completeness Rule: ~60 tokens
- Layer Symmetry Rule: ~50 tokens
- REPR Pattern Completeness: ~70 tokens
- Wrapper text: ~20 tokens

**Total Impact**: ~200 tokens per template generation call

## Usage Examples

### Example 1: Domain Operation
```python
prompt = generator._create_extraction_prompt(
    content="namespace MyApp.Domain { public class UpdateProduct {} }",
    file_path="src/Domain/Operations/UpdateProduct.cs",
    language="C#",
    purpose="Update product operation"
)

# Prompt will include:
# - CRUD Completeness Rule (ensure Create/Read/Delete also exist)
# - Layer Symmetry Rule (ensure Web endpoint exists)
# - Reminder about complete operations
```

### Example 2: Web Endpoint
```python
prompt = generator._create_extraction_prompt(
    content="public class Create : Endpoint<CreateRequest, CreateResponse> {}",
    file_path="src/Web/Products/Create.cs",
    language="C#",
    purpose="Create product endpoint"
)

# Prompt will include:
# - CRUD Completeness Rule
# - REPR Pattern Completeness (Request/Response/Validator)
# - Layer Symmetry Rule (ensure UseCases handler exists)
```

## Validation

### Prompt Quality Checklist

When reviewing generated prompts, verify:

- [ ] **CRUD Completeness** section present
- [ ] All 4 operations listed (Create/Read/Update/Delete)
- [ ] **Layer Symmetry** section present
- [ ] Examples show layer-to-layer mapping
- [ ] **REPR Pattern** section present (if applicable)
- [ ] All components listed (Endpoint/Request/Response/Validator)
- [ ] **Reminder** at end about user needs
- [ ] Clear formatting with bold headers and bullets

### Token Usage Monitoring

Monitor token usage to ensure enhanced prompts don't cause issues:

```python
# Before enhancement (baseline)
base_tokens = count_tokens(base_prompt)

# After enhancement
enhanced_tokens = count_tokens(enhanced_prompt)

# Verify increase is ~200 tokens
assert enhanced_tokens - base_tokens < 250
```

## Integration with Other Phases

### Phase 1: Completeness Validation (TASK-040)
- Enhanced prompts reduce validation failures
- Fewer templates flagged as incomplete
- Higher pass rate on completeness checks

### Phase 2: Stratified Sampling (TASK-041)
- Enhanced prompts + stratified sampling = maximum coverage
- AI sees complete CRUD samples AND is told to generate complete CRUD
- Defense-in-depth approach

### Combined Effect
```
Phase 3 (Preventive): Enhanced Prompts
    ↓ (AI generates more complete templates)
Phase 2 (Proactive): Stratified Sampling
    ↓ (AI sees all CRUD operations in samples)
Phase 1 (Reactive): Completeness Validation
    ↓ (Catches any remaining gaps)
Result: False Negative Score ≥8/10
```

## Backward Compatibility

The enhanced prompt format is **fully backward compatible**:

- ✅ No changes to prompt signature
- ✅ No changes to response format
- ✅ No changes to placeholder extraction
- ✅ No changes to template structure

The completeness requirements section is inserted as additional context, not as a replacement for existing instructions.

## Testing

### Unit Tests
Located in: `tests/unit/test_template_generator.py`

Test that prompts include:
- CRUD completeness section
- Layer symmetry section
- REPR pattern section
- Reminder text

### Integration Tests
Located in: `tests/integration/test_enhanced_prompting.py`

Test full workflow:
- Template generation with enhanced prompts
- AI considers completeness during generation
- Generated templates have higher CRUD completeness

### Manual Testing
```bash
# Generate templates with enhanced prompts
python -m installer.core.lib.template_generator.cli \
  --codebase /path/to/test/repo \
  --output /tmp/templates

# Review AI logs for completeness mentions
grep -i "completeness" /tmp/templates/generation.log

# Verify templates have complete CRUD
./scripts/validate_template_completeness.py /tmp/templates
```

## Performance Impact

### Token Usage
- **Baseline**: ~1500 tokens per prompt (average)
- **Enhanced**: ~1700 tokens per prompt (average)
- **Increase**: ~13% token usage increase
- **Impact**: Negligible (well within model limits)

### Generation Time
- **No measurable impact** on generation time
- Enhanced prompts don't increase AI processing time
- Benefits outweigh minor token cost increase

### Cost Impact
- **Cost increase**: ~$0.0002 per template (at $0.003/1K tokens)
- **Benefit**: Prevents incomplete templates worth >> $0.0002 to fix
- **ROI**: Positive (prevents manual fixes)

## Future Enhancements

### Potential Improvements
1. **Dynamic completeness rules**: Adjust based on detected architecture
2. **Pattern-specific guidance**: More detailed rules per framework
3. **Example-driven prompts**: Show before/after of incomplete vs complete
4. **Confidence scoring**: Ask AI to rate template completeness

### Not Recommended
1. ❌ **Making prompts longer**: Diminishing returns after ~200 tokens
2. ❌ **Complex formatting**: Keep simple for AI readability
3. ❌ **Over-specification**: Let AI use judgment within guidelines

## References

- [TASK-020 Implementation Plan](../implementation-plans/TASK-020-completeness-improvement-plan.md) - Lines 750-876
- [TASK-020 Improvement Proposals](../analysis/TASK-020-improvement-proposals.md)
- [Prompt Engineering Best Practices](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [Template Generator Implementation](../../installer/core/lib/template_generator/template_generator.py)

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-07 | Initial specification for TASK-042 | AI Assistant |

## Approval

- [x] Technical specification complete
- [x] Implementation matches specification
- [x] Tests cover all requirements
- [x] Documentation complete
- [ ] Human review and approval pending
