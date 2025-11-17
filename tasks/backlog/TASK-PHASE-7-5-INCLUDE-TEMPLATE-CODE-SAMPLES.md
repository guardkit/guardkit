---
id: TASK-PHASE-7-5-INCLUDE-TEMPLATE-CODE-SAMPLES
title: "Fix Agent Enhancement: Include Template Code Samples in Batch Prompt"
status: backlog
priority: critical
created: 2025-11-17
estimated_effort: 2 hours
complexity: 4/10
tags:
  - enhancement
  - template-creation
  - agent-enhancement
  - phase-7-5
dependencies:
  - TASK-PHASE-7-5-BATCH-PROCESSING-FIX-REGRESSION (completed)
related_tasks:
  - TASK-PHASE-7-5-BATCH-PROCESSING (introduced batch enhancement)
reviews:
  - architectural-reviewer: 82/100 (approved with recommendations)
  - code-reviewer: 92/100 (approved - implement as-is)
---

# Fix Agent Enhancement: Include Template Code Samples in Batch Prompt

## Executive Summary

**Problem**: Agent enhancement generates generic, incomplete documentation (~33-37 lines) instead of detailed, template-specific content (150-250 lines).

**Root Cause**: The `agent-content-enhancer` AI receives only template **metadata** (paths/names) but NOT actual template **code**, causing it to generate generic content that fails validation (minimum 150 lines + 4 required sections).

**Solution**: Add template code samples (first 50 lines from 5 templates) to the batch enhancement prompt, enabling AI to generate specific, code-based documentation.

**Impact**: Increases agent enhancement validation pass rate from ~0% to ≥80%.

**Confidence**: 95% (based on root cause analysis with debugging-specialist agent)

## Problem Statement

### Current Behavior

**Phase 7.5 Output**:
```
✅ Enhanced 5/6 agents with template references
```

**Actual Agent Files**:
- Length: 31-35 lines (expected: 150-250 lines)
- Content: Generic descriptions without code examples
- Missing sections: Template References, Best Practices, Code Examples, Constraints
- Validation: **FAILS** (< 150 lines)

**Example Generic Content**:
```markdown
## Purpose
Implements repository pattern with database access.

## Best Practices
- Use interfaces
- Follow SOLID principles
```

### Expected Behavior

**Agent Files Should Be**:
- Length: 150-250 lines
- Content: Specific code references and examples
- All sections: Present with actual code snippets
- Validation: **PASSES**

**Example Specific Content**:
```markdown
## Purpose
Implements repository pattern with Realm database for offline-first data access,
following the IRepository<T> interface pattern demonstrated in ConfigurationRepository.

## Template References
**templates/other/ConfigurationRepository.cs.template**
- Demonstrates: Generic repository interface IRepository<T> with type constraints
- Key Pattern: `public interface IRepository<T> where T : class`
- Use for: Entity-specific repository implementations

## Code Examples
```csharp
public interface IRepository<T> where T : class
{
    Task<T> GetByIdAsync(string id, CancellationToken ct);
}
```
...
(continues for 150-250 lines)
```

## Root Cause Analysis

**Location**: `installer/global/lib/template_creation/agent_enhancer.py`

### The Bug (Lines 828-867)

The `_build_template_catalog()` method sends only metadata:

```python
def _build_template_catalog(self, all_templates: List[Path]) -> List[Dict[str, str]]:
    """Build compact template catalog for batch prompt."""
    catalog = []
    for template_path in all_templates:
        catalog.append({
            "path": str(rel_path),
            "category": category,
            "name": template_path.stem  # ← ONLY METADATA, NO CODE!
        })
    return catalog
```

**What AI Receives**:
```json
{
  "path": "templates/other/ConfigurationRepository.cs.template",
  "category": "other",
  "name": "ConfigurationRepository"
}
```

**What AI Needs**: Actual template code to extract patterns, interfaces, and implementation details.

### Why It Fails

Without code context, AI cannot:
- Extract specific patterns (e.g., `IRepository<T>` interface)
- Identify concrete implementation details (e.g., Realm database usage)
- Generate accurate best practices based on real code
- Create realistic code examples with proper syntax

**Result**: AI generates generic content (~50 lines) → fails validation → files never written.

## Proposed Solution

**High-Level Approach**: Add template code sampling to batch enhancement request.

### Key Design Decisions

1. **Sampling Strategy**: Read first 50 lines of up to 5 templates
   - **Rationale**: Balances context richness vs token budget
   - **Token Impact**: 5 templates × 50 lines × 15 tokens/line ≈ 3,750 tokens (acceptable)
   - **Coverage**: First 50 lines capture headers, interfaces, key methods

2. **Token Budget Management**:
   - Current batch prompt: ~8,000-10,000 tokens (metadata only)
   - With code samples: ~15,000-20,000 tokens
   - Claude context limit: 100,000 tokens
   - **Safety**: Well below limits, increase MCP timeout from 180s to 240s

3. **Performance Trade-off**:
   - File I/O cost: ~100ms for 5 templates (acceptable)
   - AI processing time: +30-60s (worth it for 5x better quality)

4. **Error Handling Philosophy**:
   - Missing files: Log warning, continue with remaining templates
   - Encoding errors: Fall back to empty string for that template
   - **Never fail entire batch** for one bad template

### Architecture Decisions (from architectural-reviewer)

**Overall Score**: 82/100 (approved with recommendations)

**SOLID Compliance**: 44/50
- Single Responsibility: 9/10 ✅
- Open/Closed: 9/10 ✅
- Interface Segregation: 8/10 ✅
- Dependency Inversion: 8/10 ✅

**DRY Compliance**: 23/25 ✅

**YAGNI Compliance**: 15/25 ⚠️
- Recommendation: Extract to constants (magic numbers)
- Recommendation: Add feature flag for A/B testing

## Implementation Plan

### Phase 1: Add Template Code Reading Method (30 minutes)

**File**: `installer/global/lib/template_creation/agent_enhancer.py`

**Insert after line 867** (after `_build_template_catalog`):

```python
def _sample_template_code(
    self,
    template_paths: List[str],
    max_templates: int = 5,
    max_lines_per_template: int = 50
) -> Dict[str, str]:
    """
    Sample code from templates for AI context enrichment.

    Architectural Context:
    - Provides AI with actual code to generate specific documentation
    - Limits sampling to prevent token overflow
    - Handles file I/O errors gracefully (non-blocking)

    Sampling Strategy:
    - First N lines from each template (captures headers, interfaces, imports)
    - Truncates long files to stay within token budget
    - Returns empty string for unreadable files

    Args:
        template_paths: Relative template paths from catalog
        max_templates: Maximum templates to sample (default: 5)
        max_lines_per_template: Maximum lines per template (default: 50)

    Returns:
        Dict mapping template path to code sample (empty string if unreadable)

    Performance:
    - File I/O: ~20ms per template (acceptable for 5 templates)
    - Memory: ~10KB per template sample (negligible)

    Error Handling:
    - Missing file: Log warning, return empty string
    - Encoding error: Log warning, return empty string
    - I/O error: Log warning, return empty string
    """
    samples = {}

    for path_str in template_paths[:max_templates]:
        try:
            full_path = self.template_root / path_str

            if not full_path.exists():
                logger.warning(f"Template not found for sampling: {path_str}")
                samples[path_str] = ""
                continue

            # Read and sample lines
            lines = full_path.read_text(encoding='utf-8').splitlines()

            if len(lines) > max_lines_per_template:
                lines = lines[:max_lines_per_template]
                lines.append("... (truncated)")

            samples[path_str] = "\n".join(lines)

            logger.debug(
                f"Sampled {len(lines)} lines from {path_str} "
                f"({len(samples[path_str])} chars)"
            )

        except UnicodeDecodeError as e:
            logger.warning(f"Encoding error reading {path_str}: {e}")
            samples[path_str] = ""
        except Exception as e:
            logger.warning(f"Failed to sample {path_str}: {e}")
            samples[path_str] = ""

    return samples
```

**Unit Tests** (5 tests):
```python
def test_sample_template_code_success()
def test_sample_template_code_missing_file()
def test_sample_template_code_encoding_error()
def test_sample_template_code_respects_limits()
def test_sample_template_code_truncates_long_files()
```

### Phase 2: Integrate Code Sampling into Batch Request (30 minutes)

**Modify**: `_build_batch_enhancement_request()` (lines 789-835)

**Add after line 829**:

```python
# Build compact template catalog (UNCHANGED)
template_catalog = self._build_template_catalog(all_templates)

# NEW: Sample template code for AI context
template_paths = [t["path"] for t in template_catalog[:5]]
code_samples = self._sample_template_code(template_paths)

logger.info(
    f"Batch request: {len(agents)} agents, {len(template_catalog)} templates, "
    f"{len(code_samples)} code samples"
)

return {
    "agents": agents,
    "template_catalog": template_catalog,
    "template_code_samples": code_samples,  # ← NEW FIELD
    "enhancement_instructions": self._get_enhancement_instructions()
}
```

**Integration Tests** (2 tests):
```python
def test_batch_request_includes_code_samples()
def test_batch_request_handles_empty_templates()
```

### Phase 3: Update Batch Prompt to Include Code Samples (30 minutes)

**Modify**: `_build_batch_prompt()` (lines 917-965)

**Add after line 943**:

```python
# Extract code samples
code_samples = batch_request.get("template_code_samples", {})

# Format code samples for prompt
code_samples_text = ""
if code_samples:
    code_samples_text = "\n\n**Template Code Samples (for reference):**\n\n"
    for path, code in code_samples.items():
        if code:  # Only include non-empty samples
            code_samples_text += f"**{path}:**\n```\n{code}\n```\n\n"

return f"""You are enhancing AI agent documentation files with template-specific content.

**Agents to Enhance ({len(agents)} total):**
{agents_list}

**Available Templates ({len(template_catalog)} total):**
{catalog_text}
{code_samples_text}
**Enhancement Instructions:**
{instructions}

**CRITICAL REQUIREMENT:**
Base your documentation on the ACTUAL CODE shown in the template samples above.
Extract specific patterns, interfaces, and implementation details from the code.
Do NOT generate generic content - reference specific lines, classes, and methods from the samples.

**Important:**
- Process ALL agents in this batch
- Ensure each enhancement is 150-250 lines
- Base content ONLY on templates provided
- Reference specific code patterns from template samples
- Return valid JSON with all enhancements

Generate the enhancements now:"""
```

**Unit Tests** (2 tests):
```python
def test_batch_prompt_includes_code_samples()
def test_batch_prompt_handles_empty_code_samples()
```

### Phase 4: Update MCP Timeout (5 minutes)

**File**: `installer/global/lib/template_creation/agent_enhancer.py`
**Line**: 760 (in `_batch_enhance_agents`)

**Change**:
```python
# OLD:
timeout_seconds=180,  # Longer timeout for batch processing

# NEW:
timeout_seconds=240,  # Increased for code sample processing (15-20k tokens)
```

## Acceptance Criteria

### Must Have (Critical)

1. ✅ **Code Sampling Method**:
   - `_sample_template_code()` method exists
   - Reads first 50 lines from templates
   - Limits to 5 templates maximum
   - Handles missing files gracefully (empty string)
   - Handles encoding errors gracefully (empty string)
   - Logs warnings for unreadable files

2. ✅ **Batch Request Integration**:
   - `_build_batch_enhancement_request()` includes `template_code_samples` field
   - Samples are from top 5 templates in catalog
   - Backward compatible (doesn't break existing code)

3. ✅ **Prompt Enhancement**:
   - `_build_batch_prompt()` includes code samples in prompt
   - Code samples formatted with triple backticks
   - Empty samples handled gracefully (no empty code blocks)
   - Explicit instruction to AI: "Base on ACTUAL CODE"

4. ✅ **Quality Validation**:
   - Enhanced agents meet 150-line minimum
   - Enhanced agents include all required sections
   - Enhanced agents reference specific code patterns from samples
   - Validation pass rate ≥80%

### Should Have (Important)

5. ✅ **Performance**:
   - Code sampling completes in <500ms for 5 templates
   - Total batch enhancement time ≤5 minutes

6. ✅ **Observability**:
   - Log message shows sample count and total chars
   - Warning logged for each unreadable template
   - Debug logging shows lines sampled per template

7. ✅ **Token Budget Safety**:
   - Total prompt size ≤30,000 tokens
   - MCP timeout increased to 240s

### Could Have (Nice to Haves)

8. ⚪ **Advanced Sampling**:
   - Smart truncation (preserve class definitions)
   - Category-based sampling (sample from each category)

9. ⚪ **Caching**:
   - Cache template content in memory

10. ⚪ **Quality Metrics**:
    - Track before/after agent file sizes
    - Track before/after validation pass rates

## Testing Strategy

### Unit Tests (9 tests)

**File**: `tests/unit/lib/template_creation/test_agent_enhancer.py`

1. `test_sample_template_code_success` - Verify successful code sampling
2. `test_sample_template_code_missing_file` - Handle missing files gracefully
3. `test_sample_template_code_encoding_error` - Handle encoding errors
4. `test_sample_template_code_respects_limits` - Verify max limits enforced
5. `test_sample_template_code_truncates_long_files` - Verify truncation
6. `test_batch_request_includes_code_samples` - Verify field in request
7. `test_batch_request_handles_empty_templates` - Handle edge case
8. `test_batch_prompt_includes_code_samples` - Verify samples in prompt
9. `test_batch_prompt_handles_empty_code_samples` - Handle edge case

### Integration Tests (1 test)

**File**: `tests/integration/test_agent_enhancement_with_code_samples.py`

1. `test_enhanced_agents_reference_actual_code` - End-to-end verification

### Manual Verification

1. Run `/template-create` on Taskwright codebase
2. Inspect `agents/*.md` files
3. Verify:
   - Files are 150-250 lines ✅
   - Reference specific code patterns ✅
   - Include actual method signatures ✅
   - Best practices reference actual templates ✅

## Risk Assessment

### Token Overflow Risk

**Analysis**: LOW ✅
- Current: 8-10k tokens
- With sampling: 15-20k tokens
- Claude limit: 100k tokens
- **Well within limits**

**Mitigation**:
- Hard limit: `max_templates=5`
- Hard limit: `max_lines_per_template=50`

### Performance Risk

**Analysis**: LOW ✅
- File I/O: 100ms (5 templates)
- AI processing: +30-60s
- **Acceptable trade-off** for 5x quality improvement

### Quality Risk

**Analysis**: MEDIUM 🟡
- Best case: 150-250 line agents ✅
- Worst case: AI still generates generic content ⚠️

**Mitigation**:
- Explicit instruction: "Base on ACTUAL CODE"
- Validation: Check for template path references
- **Acceptance criteria**: ≥80% pass rate

## Success Metrics

### Before (Current State)

- Length: 33-37 lines (fails validation)
- Content quality: Generic
- Code references: None
- Validation pass rate: 0%

### After (Target State)

- Length: 150-250 lines (passes validation)
- Content quality: Specific code references
- Code references: 5-8 per agent
- Validation pass rate: ≥80%

### Quantitative Targets

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Average agent length | 35 lines | 180 lines | ≥150 lines |
| Validation pass rate | 0% | 85% | ≥80% |
| Code references per agent | 0 | 5-8 | ≥3 |
| Template mentions per agent | 0 | 2-3 | ≥2 |

## Dependencies

**Must Be In Place**:
1. ✅ Phase 7.5 batch enhancement (already implemented)
2. ✅ Template files written to disk before Phase 7.5
3. ✅ Agent validation logic (already implemented)
4. ✅ Agent bridge invoker (already implemented)

**Not Required**:
- ❌ MCP server changes
- ❌ Database changes
- ❌ Configuration changes

## Estimated Effort

**Total**: 2 hours

**Breakdown**:
- Phase 1 (Code sampling method): 30 minutes
  - Implementation: 15 minutes
  - Unit tests (5 tests): 15 minutes

- Phase 2 (Batch request integration): 30 minutes
  - Modify method: 15 minutes
  - Integration tests (2 tests): 15 minutes

- Phase 3 (Prompt enhancement): 30 minutes
  - Modify method: 15 minutes
  - Unit tests (2 tests): 15 minutes

- Phase 4 (MCP timeout): 5 minutes

- Integration testing: 25 minutes
  - End-to-end test: 15 minutes
  - Manual verification: 10 minutes

## Rollback Plan

**If Enhancement Quality Degrades**:
1. Add feature flag: `--skip-code-sampling` (temporarily disable)
2. Revert commits (3 files changed, clean revert)
3. Restore previous batch prompt

**Detection**:
- Monitor validation pass rate: If drops below 50%, investigate
- Check agent file lengths: If average <100 lines, rollback
- User feedback: If complaints about generic content, rollback

## Implementation Checklist

- [ ] Phase 1: Add `_sample_template_code()` method
- [ ] Phase 1: Write 5 unit tests
- [ ] Phase 2: Modify `_build_batch_enhancement_request()`
- [ ] Phase 2: Write 2 integration tests
- [ ] Phase 3: Modify `_build_batch_prompt()`
- [ ] Phase 3: Write 2 unit tests
- [ ] Phase 4: Update MCP timeout
- [ ] Run all unit tests (pytest -v)
- [ ] Run integration test
- [ ] Manual verification on Taskwright codebase
- [ ] Verify agent file lengths ≥150 lines
- [ ] Verify code references in enhanced content

## Related Documentation

- [Diagnostic Report](/tmp/DIAGNOSTIC_REPORT.md) - Complete root cause analysis
- [Root Cause Analysis](/tmp/root_cause_analysis.md) - Investigation notes
- [Debug Log](/tmp/template-create-debug.log) - Execution trace

## Expert Reviews

**Architectural Review** (architectural-reviewer):
- **Score**: 82/100 (approved with recommendations)
- **SOLID**: 44/50
- **DRY**: 23/25
- **YAGNI**: 15/25 (recommendation: extract constants)

**Code Review** (code-reviewer):
- **Score**: 92/100 (approved - implement as-is)
- **Correctness**: 10/10
- **Testing**: 9/10
- **Architecture**: 10/10
- **Minor improvements**: Extract magic numbers, fuzzy section matching

## Notes

This task implements the solution identified through systematic root cause analysis using the debugging-specialist agent. The proposed fix has been validated by both architectural-reviewer and code-reviewer agents, with high confidence (95%) that it will resolve the agent enhancement issue.
