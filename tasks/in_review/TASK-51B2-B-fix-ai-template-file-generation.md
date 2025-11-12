---
id: TASK-51B2-B
title: Fix AI-native template file generation in /template-create
status: in_review
created: 2025-11-12T12:30:00Z
updated: 2025-11-12T14:51:00Z
priority: critical
tags: [template-create, ai-native, regression]
complexity: 4
test_results:
  status: passed
  total_tests: 48
  passed: 48
  failed: 0
  coverage:
    line: 83.3
    branch: 83.0
  last_run: "2025-11-12T14:48:00Z"
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
implementation_plan:
  file_path: "docs/state/TASK-51B2-B/implementation_plan.json"
  generated_at: "2025-11-12T14:45:00Z"
  version: 1
  approved: true
  approved_by: "timeout"
  approved_at: "2025-11-12T14:46:00Z"
complexity_evaluation:
  score: 4
  level: "medium"
  file_path: "docs/state/TASK-51B2-B/complexity_score.json"
  calculated_at: "2025-11-12T14:45:00Z"
  review_mode: "quick_optional"
  forced_review_triggers: []
  factors:
    file_complexity: 1.5
    pattern_familiarity: 0.5
    risk_level: 0.5
    dependency_complexity: 0
plan_audit:
  status: "approved"
  approved_by: "timeout"
  approved_at: "2025-11-12T14:50:00Z"
  file_path: "docs/state/TASK-51B2-B/plan_audit_report.json"
  severity: "low"
  files_match: true
  scope_creep_detected: false
---

# Task: Fix AI-native template file generation in /template-create

## Description

**CRITICAL REGRESSION**: After TASK-51B2 (Revert to AI-Native Template Creation), the `/template-create` command no longer generates any .template files. The AI-native workflow is executing but the AI agent is not returning example files that should be used as templates.

**Current behavior**:
- Phase 1 AI analysis completes successfully
- Phase 4 Template Generation runs but generates 0 template files
- Only metadata files created (manifest.json, settings.json, CLAUDE.md)

**Expected behavior**:
- AI analyzes codebase and identifies representative files for templates
- Phase 4 extracts and converts these files to .template files with placeholders
- Generated templates ready to use with `taskwright init`

**Root Cause**: The AI agent prompt is not sufficiently emphasizing that `example_files` should include files suitable for template generation, or the AI is not returning them.

This is a **critical regression** that blocks the core purpose of `/template-create`.

## AI-Native Philosophy

**IMPORTANT**: This task follows the AI-native approach from TASK-51B2. The fix involves:
- ✅ Enhancing AI prompts to better request template-suitable files
- ✅ Improving AI instructions for identifying reusable patterns
- ✅ Potentially increasing file sampling for better context
- ❌ NO Python pattern-matching code
- ❌ NO hard-coded detectors
- ❌ NO manual file selection logic

**The AI does the work. We just need to ask it better questions.**

## Root Cause Analysis

### Investigation Results

**File Flow**:
1. `template_create_orchestrator.py` → calls `CodebaseAnalyzer(max_files=10)` ⚠️ Low sample size
2. `ai_analyzer.py` → invokes architectural-reviewer agent with prompt
3. `prompt_builder.py` → asks AI for `example_files` in JSON response ✅ Prompt exists
4. `response_parser.py` → extracts `example_files` from AI response ✅ Parser works
5. `template_generator.py` → iterates `analysis.example_files` and generates templates ✅ Generator works

**Problem Identified**:
- AI prompt asks for `example_files` but doesn't emphasize they're for template generation
- Prompt shows minimal example (only 1 file: "src/domain/user.py")
- `max_files=10` may not give AI enough context to identify diverse patterns
- AI may be returning empty `example_files` array or minimal examples

### Current Prompt Structure

From `prompt_builder.py` lines 268-276:
```json
"example_files": [
  {
    "path": "src/domain/user.py",
    "purpose": "User entity with business logic",
    "layer": "Domain",
    "patterns_used": ["Entity", "Value Object"],
    "key_concepts": ["User", "Email", "Password"]
  }
]
```

**Issues**:
- Only shows 1 example file (AI may think that's all we want)
- Doesn't explain these files will be used as templates
- Doesn't request diverse file types (domain, viewmodel, service, repository, etc.)

## Acceptance Criteria

- [ ] AI prompt emphasizes `example_files` are for template generation
- [ ] AI prompt requests diverse file types suitable as templates
- [ ] AI prompt includes multiple example entries (5-10 examples)
- [ ] Increased `max_files` sampling from 10 to 20-30 for better context
- [ ] Phase 4 generates appropriate number of .template files (10-20+ for typical codebase)
- [ ] Generated templates include placeholders ({{ProjectName}}, {{Namespace}}, etc.)
- [ ] Integration test verifies template file generation
- [ ] Manual test confirms templates work with `taskwright init`

## Implementation Notes

### Fix 1: Enhance AI Prompt in PromptBuilder

**File**: `installer/global/lib/codebase_analyzer/prompt_builder.py`

**Update around lines 268-276**:

```python
# OLD (minimal example)
"example_files": [
  {
    "path": "src/domain/user.py",
    "purpose": "User entity with business logic",
    ...
  }
]

# NEW (emphasize template generation with multiple examples)
"example_files": [
  {
    "path": "src/domain/{{EntityName}}.py",
    "purpose": "Domain entity - will be used as template for new entities",
    "layer": "Domain",
    "template_category": "entity",
    "patterns_used": ["Entity", "Value Object"],
    "key_concepts": ["Entity", "Validation", "Business Logic"],
    "why_good_template": "Clear structure, reusable entity pattern"
  },
  {
    "path": "src/repositories/{{EntityName}}Repository.py",
    "purpose": "Repository pattern - will be used as template for data access",
    "layer": "Data",
    "template_category": "repository",
    "patterns_used": ["Repository", "Dependency Injection"],
    "key_concepts": ["Repository", "CRUD", "Database Access"],
    "why_good_template": "Consistent repository pattern with standard operations"
  },
  {
    "path": "src/services/{{ServiceName}}Service.py",
    "purpose": "Service layer - will be used as template for business services",
    "layer": "Service",
    "template_category": "service",
    "patterns_used": ["Service Layer", "Dependency Injection"],
    "key_concepts": ["Service", "Business Logic", "Coordination"],
    "why_good_template": "Service pattern with clear responsibilities"
  },
  // Include 5-10 diverse examples showing different layers/patterns
]
```

**Add explicit instruction**:
```
IMPORTANT: The 'example_files' you identify will be converted into reusable .template files.
Choose files that:
1. Represent common patterns in the codebase (entities, repositories, services, viewmodels, views, etc.)
2. Have clear, reusable structure
3. Cover different architectural layers
4. Would be useful starting points for new features

Aim for 10-20 diverse example files covering the full architecture.
```

### Fix 2: Increase File Sampling

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

**Line 364** (in `_phase1_ai_analysis`):
```python
# OLD
analyzer = CodebaseAnalyzer(max_files=10)

# NEW (more context for AI)
analyzer = CodebaseAnalyzer(max_files=30)  # Increased for better pattern identification
```

**Rationale**: With only 10 files, AI may not see enough examples to identify diverse patterns. 30 files gives better coverage of architecture layers.

### Fix 3: Add Template Selection Guidance

**File**: `installer/global/lib/codebase_analyzer/prompt_builder.py`

**Add new section to prompt** (after line 289):
```
## Template File Selection Guidelines

Your 'example_files' will be used to generate reusable .template files. Please identify 10-20 files that:

### Must Include (if present in codebase):
- **Domain/Models**: Entity classes, value objects, domain services
- **Data Access**: Repositories, database contexts, data models
- **Business Logic**: Service classes, use cases, commands/queries
- **Presentation**: ViewModels, controllers, API endpoints
- **Views/UI**: Pages, components, views (for UI frameworks)
- **Tests**: Test fixtures, test utilities (if present)
- **Configuration**: Config classes, dependency injection setup

### Selection Criteria:
✅ Representative of common patterns
✅ Clear, well-structured code
✅ Reusable across features
✅ Not overly specific or complex
✅ Follows project conventions
❌ Avoid: Main entry points, highly coupled code, one-off utilities

### Coverage:
- Aim for breadth across architectural layers
- Include at least 2-3 files per major layer
- Balance between simple and moderately complex examples
```

## Files to Modify

### Primary (AI Prompt Enhancement):
1. `installer/global/lib/codebase_analyzer/prompt_builder.py`
   - Enhance `example_files` prompt section (lines 268-289)
   - Add template selection guidelines
   - Update example JSON to show 5-10 diverse files

2. `installer/global/commands/lib/template_create_orchestrator.py`
   - Increase `max_files` from 10 to 30 (line 364)

### Secondary (Testing):
3. `tests/integration/test_ai_native_template_creation.py`
   - Add test to verify `example_files` are returned
   - Add test to verify template generation produces files

## Test Requirements

### Unit Tests:
- [ ] Test that prompt includes template selection guidelines
- [ ] Test that prompt example shows multiple diverse files
- [ ] Test that response parser handles larger example_files arrays

### Integration Tests:
- [ ] Test AI analysis returns non-empty `example_files` array
- [ ] Test `example_files` includes diverse file types (domain, data, service layers)
- [ ] Test Phase 4 generates .template files from `example_files`
- [ ] Test generated templates include proper placeholders

### Manual Tests:
```bash
# Test 1: React TypeScript codebase
cd example-react-project
/template-create --save-analysis
# Verify: analysis.json contains example_files array with 10-20 entries
# Verify: Generated template includes .template files

# Test 2: FastAPI Python codebase
cd example-fastapi-project
/template-create --validate
# Verify: Template generation phase shows "15 template files generated"
# Verify: Templates work with `taskwright init test-template`

# Test 3: .NET MAUI codebase
cd example-maui-project
/template-create
# Verify: Templates include domain, viewmodel, view, repository files
```

## Expected Output (After Fix)

```bash
$ /template-create

============================================================
  Phase 1: AI Codebase Analysis
============================================================
🔍 Analyzing codebase...
  • Language: C# (net9.0)
  • Framework: .NET MAUI
  • Architecture: MVVM
✅ Analysis complete (confidence: 87%)

============================================================
  Phase 4: Template File Generation
============================================================
📝 Generating template files from 18 example files...
  ✓ Domain/{{EntityName}}Engine.cs.template
  ✓ ViewModels/{{EntityName}}ViewModel.cs.template
  ✓ Views/{{EntityName}}Page.xaml.template
  ... and 15 more

  Total: 18 template files generated
✅ Template file generation complete

============================================================
  Template Package Complete
============================================================
✅ Template saved successfully!

Location: ~/.agentecflow/templates/maui-mvvm-template
Files: 18 templates, manifest.json, settings.json, CLAUDE.md
Quality Score: 9.8/10 (Grade A+)
```

## Dependencies

**Related to**: TASK-51B2 (Revert to AI-Native Template Creation)
**Caused by**: AI prompt not emphasizing template generation purpose

## References

- [TASK-51B2 Completion](../completed/TASK-51B2/TASK-51B2.md)
- [AI Analyzer](../../installer/global/lib/codebase_analyzer/ai_analyzer.py)
- [Prompt Builder](../../installer/global/lib/codebase_analyzer/prompt_builder.py)
- [Template Generator](../../installer/global/lib/template_generator/template_generator.py)

## Implementation Estimate

**Duration**: 2-4 hours

**Complexity**: 5/10 (Medium)
- Enhance AI prompts with better instructions
- Increase file sampling limit
- Test with sample codebases
- Verify templates are generated and usable

## Success Criteria

✅ AI returns 10-20 example files in analysis
✅ Phase 4 generates corresponding .template files
✅ Templates include proper placeholders
✅ Templates work with `taskwright init`
✅ Integration tests pass
✅ No regression in metadata generation
✅ Maintains AI-native approach (no hard-coded patterns)

## Test Execution Log

_Automatically populated by /task-work_
