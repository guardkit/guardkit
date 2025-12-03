# TASK-0CE5: Fix Empty example_files in AI Analysis (Phase 2)

**Status**: Backlog
**Priority**: High
**Complexity**: 4/10
**Estimated Time**: 2-3 hours

---

## 🚨 CRITICAL ARCHITECTURAL MANDATE 🚨

**THIS SYSTEM IS AI-DRIVEN AND TECHNOLOGY-AGNOSTIC. THIS IS NON-NEGOTIABLE.**

### What This Means

1. **AI Analyzes Codebases**: The architectural-reviewer agent reads files and infers everything
2. **NO Python Detection Code**: Zero hardcoded language/framework/pattern detection in Python
3. **Technology Agnostic**: Must work for ANY language (C#, Python, TypeScript, Go, Rust, Ruby, PHP, Elixir, etc.)
4. **AI Does The Work**: Python only orchestrates; AI does all analysis and inference

### What Is FORBIDDEN

❌ **DO NOT** add Python code to detect languages
❌ **DO NOT** add Python code to detect frameworks
❌ **DO NOT** add Python code to detect patterns
❌ **DO NOT** add Python code to select example files
❌ **DO NOT** add ANY hardcoded technology-specific logic

### What IS Allowed

✅ **DO** improve the AI prompt to request example_files
✅ **DO** add validation that example_files was returned
✅ **DO** add logging to debug what AI returns
✅ **DO** fail loudly if AI doesn't return example_files
✅ **DO** ensure AI receives sufficient context to analyze ANY codebase

---

## Problem Statement

The `/template-create` command successfully:
- ✅ Discovers 273 source files (stratified sampling)
- ✅ Invokes architectural-reviewer agent
- ✅ Generates 13 specialized agents (proves agent invocation works)
- ✅ Generates manifest.json and settings.json

BUT fails to:
- ❌ Generate ANY template files (0 templates)
- ❌ Create templates/ directory
- ❌ Populate analysis.example_files with representative files

**Root Cause**: `analysis.example_files` is empty after Phase 2 (AI Analysis), causing Phase 4 (Template Generation) to skip template creation entirely.

---

## Technical Analysis

### Evidence

```
Phase 1: File Collection
  ✅ Stratified sampler discovered 273 source files
  ✅ Categorized files by type (crud_read, validators, repositories, etc.)
  ✅ Selected 30 representative files for AI analysis

Phase 2: AI Analysis
  ✅ architectural-reviewer agent invoked successfully
  ❌ analysis.example_files = [] (EMPTY!)
  ℹ️  Agent returned agents, technology, architecture, quality
  ❌ Agent did NOT return example_files (or returned empty list)

Phase 4: Template Generation
  ❌ TemplateGenerator.generate() iterates analysis.example_files
  ❌ Empty list → 0 iterations → 0 templates
  ❌ No templates/ directory created

Phase 5: Agent Generation
  ✅ 13 agents created successfully (proves agent invocation works)

Phase 7: Validation
  ⚠️  Validation report: "No spot-checks performed (no templates to validate)"
  ⚠️  Gave 9.8/10 score despite 0 templates (incorrect validation logic)
```

### Code Flow

```
prompt_builder.py (L273-344)
  └─ Requests 10 example_files in JSON response
       ↓
architectural-reviewer agent
  └─ Should analyze codebase and return example_files
       ↓
response_parser.py (L175-177)
  └─ Extracts: example_files_data = data.get("example_files", [])
       ↓
CodebaseAnalysis.example_files = [] (EMPTY!)
       ↓
template_generator.py (L58-64)
  └─ for example_file in analysis.example_files:  # Empty = 0 iterations
       ↓
0 templates generated
```

### Key Files

- `installer/global/lib/codebase_analyzer/prompt_builder.py` - Prompt construction
- `installer/global/lib/codebase_analyzer/response_parser.py` - Response parsing
- `installer/global/lib/codebase_analyzer/ai_analyzer.py` - Agent invocation
- `installer/global/lib/template_generator/template_generator.py` - Template generation

---

## Acceptance Criteria

### Functional Requirements

1. **AI Returns example_files** ✅
   - After Phase 2, `analysis.example_files` contains 5-15 representative files
   - Files span multiple layers/patterns (Domain, API, Tests, etc.)
   - Files are suitable for template generation

2. **Template Files Generated** ✅
   - Phase 4 creates templates/ directory
   - At least 5 .template files created
   - Templates have proper placeholders ({{ProjectName}}, etc.)

3. **Validation Accurate** ✅
   - Validation report shows actual template count
   - Score reflects template quality, not just agents

4. **Technology Agnostic** ✅ ✅ ✅
   - Works for C# MAUI project (current test case)
   - NO Python code added for C#-specific detection
   - NO hardcoded language/framework logic
   - AI infers everything from codebase

### Technical Requirements

5. **Prompt Enhancement** ✅
   - Update prompt_builder.py to EMPHASIZE example_files requirement
   - Make it crystal clear this is MANDATORY, not optional
   - Provide clear examples of what example_files should contain

6. **Validation Added** ✅
   - After Phase 2, validate analysis.example_files is not empty
   - Fail loudly (with helpful error) if empty
   - Log what AI actually returned for debugging

7. **Logging Added** ✅
   - Log example_files count after Phase 2
   - Log each example file path for verification
   - Log if prompt included example_files request

### Quality Gates

8. **Test Case: C# MAUI Project** ✅
   - Run `/template-create --validate` on DeCUK.Mobile.MyDrive
   - Verify 5+ template files generated
   - Verify templates/ directory exists
   - Verify validation score reflects actual templates

9. **Code Review** ✅
   - NO hardcoded language detection added
   - NO hardcoded framework detection added
   - NO hardcoded pattern detection added
   - Only prompt improvements and validation logic

10. **Coverage** ✅
    - Unit tests for response_parser.py with example_files
    - Unit tests for prompt_builder.py example_files section
    - Integration test for end-to-end template creation

---

## Implementation Approach

### Step 1: Add Debug Logging (5-10 minutes)

Add logging to understand what AI is actually returning:

```python
# In response_parser.py after JSON extraction
logger.debug(f"AI response keys: {list(json_data.keys())}")
logger.debug(f"example_files in response: {'example_files' in json_data}")
if 'example_files' in json_data:
    logger.debug(f"example_files count: {len(json_data['example_files'])}")
```

### Step 2: Enhance Prompt (30-45 minutes)

Update `prompt_builder.py` to make example_files requirement crystal clear:

```python
## 🚨 CRITICAL REQUIREMENT: example_files

**YOU MUST INCLUDE 10-15 example_files IN YOUR RESPONSE.**

These files are used to generate .template files for scaffolding new projects.
If you omit example_files, the template creation will fail.

Select files that:
- Span multiple architectural layers (Domain, Application, Infrastructure, Web)
- Represent different patterns (CRUD operations, validation, repositories, tests)
- Are suitable for templating (contain patterns users will repeat)
- Cover the full technology stack (not just domain models)

MANDATORY: Your JSON response MUST include the "example_files" array with 10-15 entries.
```

### Step 3: Add Validation (20-30 minutes)

In `ai_analyzer.py` after parsing response:

```python
# Validate example_files was returned
if not analysis.example_files:
    logger.error("AI did not return example_files - template generation will fail")
    logger.error("This is a critical bug in the AI prompt or agent response")
    raise ValueError(
        "AI analysis returned empty example_files. "
        "Cannot generate templates without example files. "
        "This indicates the AI prompt needs improvement or agent didn't follow instructions."
    )

logger.info(f"AI returned {len(analysis.example_files)} example files for templating")
for example_file in analysis.example_files:
    logger.debug(f"  - {example_file.path} ({example_file.layer})")
```

### Step 4: Test and Verify (30-60 minutes)

1. Run `/template-create --validate` on test C# MAUI project
2. Verify debug logs show example_files in response
3. Verify templates/ directory created
4. Verify 5+ .template files generated
5. Verify validation report shows actual template count

---

## Testing Strategy

### Unit Tests

```python
# test_response_parser.py
def test_parse_analysis_with_example_files():
    """Verify example_files are extracted from response"""
    response = json.dumps({
        "technology": {...},
        "architecture": {...},
        "quality": {...},
        "example_files": [
            {
                "path": "src/domain/user.py",
                "purpose": "User entity",
                "layer": "Domain",
                "patterns_used": ["Entity"],
                "key_concepts": ["User"]
            }
        ]
    })

    parser = ResponseParser()
    analysis = parser.parse_analysis_response(response, "/path", None)

    assert len(analysis.example_files) == 1
    assert analysis.example_files[0].path == "src/domain/user.py"

def test_parse_analysis_missing_example_files():
    """Verify validation fails if example_files missing"""
    response = json.dumps({
        "technology": {...},
        "architecture": {...},
        "quality": {...}
        # example_files missing
    })

    parser = ResponseParser()
    analysis = parser.parse_analysis_response(response, "/path", None)

    # Should default to empty list
    assert analysis.example_files == []

    # Validation should catch this
    is_valid, issues = parser.validate_analysis(analysis)
    assert not is_valid
    assert any("example files" in issue.lower() for issue in issues)
```

### Integration Tests

```python
# test_template_create_orchestrator.py
def test_template_creation_generates_templates():
    """End-to-end test verifying templates are generated"""
    config = OrchestrationConfig(
        codebase_path=Path("test_fixtures/sample_csharp_project"),
        output_location="global",
        validate=True
    )

    orchestrator = TemplateCreateOrchestrator(config)
    result = orchestrator.run()

    # Verify success
    assert result.success

    # Verify templates generated
    assert result.templates is not None
    assert result.templates.total_count >= 5

    # Verify files on disk
    template_dir = Path.home() / ".agentecflow" / "templates" / result.manifest.name
    assert (template_dir / "templates").exists()

    template_files = list((template_dir / "templates").rglob("*.template"))
    assert len(template_files) >= 5
```

---

## Success Metrics

### Before Fix
- ❌ 0 template files generated
- ❌ No templates/ directory
- ❌ Validation report: "No spot-checks performed"
- ❌ Users cannot use generated templates (nothing to use)

### After Fix
- ✅ 5-15 template files generated
- ✅ templates/ directory exists with .template files
- ✅ Validation report shows actual template count and quality
- ✅ Users can run `guardkit init <template-name>` successfully

### Architecture Compliance
- ✅ NO Python code added for language detection
- ✅ NO Python code added for framework detection
- ✅ NO Python code added for pattern detection
- ✅ AI-driven analysis maintained
- ✅ Technology-agnostic architecture preserved

---

## Related Tasks

- **TASK-51B2**: AI-native codebase analysis (completed)
- **TASK-51B2-A785**: Fix agent markdown formatting (completed)
- **TASK-769D**: Agent invocation via checkpoint-resume (completed)

---

## Notes

### Why This Is Critical

Without template files, the entire `/template-create` command is useless:
1. No templates → Users cannot scaffold new projects
2. 9.8/10 validation score is misleading (should fail if no templates)
3. Agents are generated but have nothing to generate

### Why This Must Be AI-Driven

The system is designed to work with ANY technology stack:
- C# MAUI, Python FastAPI, TypeScript React, Go microservices, Rust CLI, Ruby Rails, etc.
- Hardcoding language detection breaks this architectural goal
- AI is capable of analyzing ANY codebase - let it do its job

### Debug Checklist

If example_files is still empty after fix:
1. Check AI response JSON - does it include "example_files" key?
2. Check prompt - is example_files requirement clear enough?
3. Check agent definition - does architectural-reviewer understand its role?
4. Check file samples - are they reaching the AI with content?
5. Check response parsing - is extraction logic correct?

---

## Implementation Time Estimate

- Debug logging: 10 minutes
- Prompt enhancement: 45 minutes
- Validation logic: 30 minutes
- Unit tests: 30 minutes
- Integration test: 30 minutes
- Manual testing: 30 minutes
- Code review: 15 minutes

**Total**: 2.5-3 hours
