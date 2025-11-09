---
id: TASK-060A
title: Reinstate and Improve Default Template (Language-Agnostic)
status: backlog
created: 2025-01-09T13:00:00Z
updated: 2025-01-09T13:00:00Z
priority: high
tags: [templates, breaking-change-fix, ux-improvement, quality]
complexity: 5
related_tasks: [TASK-060, TASK-061, TASK-068]
parent_task: TASK-060
---

# TASK-060A: Reinstate and Improve Default Template

## Description

Reinstate the `default` template that was removed in TASK-060, but with significant quality improvements to address the language-agnostic initialization use case that other templates don't cover.

**Background**: TASK-060 removed the `default` template (scored 6.0/10: "Generic template with minimal guidance") to improve overall template quality. However, this created breaking changes:

1. **Scripts still reference "default"**:
   - `~/.agentecflow/scripts/init-project.sh` defaults to `"default"` (line 26)
   - Help text in `taskwright-init` lists "default - Language-agnostic template"
   - Fallback logic tries to use "default" when template not found (lines 214-216)

2. **Documentation assumes it exists**:
   - TASK-061 lists `default` as available template (line 106)
   - CLAUDE.md template initialization examples

3. **Valid use case not served**:
   - Users with Go/Rust/Ruby/Elixir/etc. projects (languages not covered by existing templates)
   - Users wanting to evaluate Taskwright before committing to stack-specific template
   - Workflow: `taskwright init` → work in Claude Code → `/template-create` → generate custom template

**Current State**:
- Existing installations work (have old default template installed)
- New installations **will fail** (template doesn't exist in repository)
- Fresh users running `taskwright init` → defaults to "default" → **error**

**Related Tasks**:
- **TASK-060**: Removed default template (parent task)
- **TASK-061**: Documentation assumes default exists
- **TASK-068**: Template output location refactoring

## Acceptance Criteria

### Core Functionality
- [x] **AC1**: Default template reinstated at `installer/global/templates/default/`
- [x] **AC2**: Template scores ≥8.0/10 on quality audit (improved from 6.0/10)
- [x] **AC3**: Contains all required files (CLAUDE.md, settings.json, agents/, templates/)
- [x] **AC4**: Language-agnostic guidance (no stack-specific assumptions)
- [x] **AC5**: Works with `taskwright init` without arguments

### Quality Improvements (from original 6.0/10)
- [x] **AC6**: CLAUDE.md provides clear, actionable guidance (not generic boilerplate)
- [x] **AC7**: Settings.json configured for optimal language-agnostic workflow
- [x] **AC8**: Template files demonstrate best practices (ADR, task, requirement formats)
- [x] **AC9**: Documentation explains when to use default vs stack-specific templates
- [x] **AC10**: Includes examples for common language-agnostic scenarios

### Integration & Compatibility
- [x] **AC11**: Compatible with existing init scripts (no script changes needed)
- [x] **AC12**: install.sh correctly copies default template to `~/.agentecflow/templates/`
- [x] **AC13**: Works with TASK-068's `--output-location` flag for `/template-create`
- [x] **AC14**: taskwright doctor validates default template structure

### Documentation
- [x] **AC15**: CLAUDE.md updated to reflect default template purpose and use cases
- [x] **AC16**: TASK-061 documentation aligned with improved default template
- [x] **AC17**: Migration guide updated to clarify when to use default
- [x] **AC18**: Help text in taskwright-init accurately describes default template
- [x] **AC19**: README.md template table includes improved default template

### Testing
- [x] **AC20**: Fresh installation test (remove ~/.agentecflow → install.sh → verify default exists)
- [x] **AC21**: Init with no args test (`taskwright init` → verify default template used)
- [x] **AC22**: Template quality audit (≥8.0/10 score)
- [x] **AC23**: Integration with `/template-create` workflow test

## Implementation Plan

### Phase 1: Recover and Analyze Original Template
1. Retrieve archived default template from git history (commit `413a36b`)
2. Extract files:
   - CLAUDE.md
   - settings.json
   - agents/architectural-reviewer.md
   - templates/adr-template.md
   - templates/bdd-scenario.md
   - templates/ears-requirement.md
   - templates/task-template.md
3. Document what made it "generic with minimal guidance" (6.0/10 issues)

### Phase 2: Improve Template Quality (6.0 → 8.0+)

#### CLAUDE.md Improvements
**Old Issues** (from audit):
- Generic boilerplate
- Minimal specific guidance
- No clear use case explanation

**New Content**:
```markdown
# CLAUDE.md for Language-Agnostic Projects

## When to Use This Template

✅ **Use the default template when**:
- Your project uses Go, Rust, Ruby, Elixir, PHP, or languages not covered by other templates
- You're evaluating Taskwright before committing to a stack-specific template
- You want Taskwright's workflow without stack-specific patterns

⚠️ **Use a stack-specific template instead when**:
- Your project uses React, Python, .NET, or other supported stacks
- You want framework-specific agents and patterns
- You're building a new project from scratch

## Getting Started with Your Language

[Language-agnostic guidance that applies to any stack]

## Creating Your Custom Template

Once you've validated Taskwright works for your stack:

1. Work in your project using this default template
2. Use `/template-create` to generate a custom template from your code
3. Initialize new projects with `taskwright init your-custom-template`

**Why?** Your proven code patterns are better than any generic template.
```

#### Settings.json Improvements
- Simplify documentation levels (default to "standard")
- Remove stack-specific complexity thresholds
- Add language-agnostic best practices

#### Template Files Improvements
- **adr-template.md**: Add more examples, clearer structure
- **task-template.md**: Updated with Phase 2.5/4.5 quality gates
- **bdd-scenario.md**: Better Gherkin examples
- **ears-requirement.md**: Clearer EARS notation

### Phase 3: Verify Breaking Changes Fixed

1. **Script Verification**:
   - `~/.agentecflow/scripts/init-project.sh` line 26: `TEMPLATE="${1:-default}"` ✓ (works)
   - Lines 214-216: Fallback to default ✓ (works)
   - `~/.agentecflow/bin/taskwright-init`: Help text ✓ (accurate)

2. **Documentation Verification**:
   - TASK-061 line 106: Template list ✓ (includes default)
   - CLAUDE.md: Template initialization examples ✓

3. **Installation Verification**:
   - `installer/scripts/install.sh` copies templates ✓
   - Fresh installation has default in `~/.agentecflow/templates/default/` ✓

### Phase 4: Documentation Updates

1. **CLAUDE.md** (project root):
   - Update "Available Templates" section
   - Add guidance on when to use default vs stack-specific
   - Example:
     ```markdown
     **Available Templates:**
     - **default**: Language-agnostic (Go, Rust, Ruby, etc.) - for evaluation or unsupported stacks
     - **react**: React + TypeScript + Next.js + Tailwind
     - **python**: FastAPI + pytest + LangGraph
     - ...
     ```

2. **README.md**:
   - Update template table with default template
   - Add quality score (8.0+/10)
   - Clarify use cases

3. **docs/guides/template-migration.md**:
   - Update "What happened to default?" section
   - Change from "removed" to "improved and reinstated"
   - Add before/after quality comparison

4. **TASK-061** (if not yet implemented):
   - Ensure default template examples are accurate
   - Update template list to match reality

### Phase 5: Quality Audit

Run template quality audit (similar to TASK-056):
- **Target Score**: ≥8.0/10 (improvement from 6.0/10)
- **Criteria**:
  - CLAUDE.md clarity: 8+/10
  - Settings.json appropriateness: 8+/10
  - Template files quality: 8+/10
  - Documentation completeness: 9+/10
  - Use case clarity: 9+/10

### Phase 6: Testing

#### Test 1: Fresh Installation
```bash
# Backup existing installation
mv ~/.agentecflow ~/.agentecflow.backup

# Fresh install
./installer/scripts/install.sh

# Verify default template exists
ls -la ~/.agentecflow/templates/default/
# Expected: CLAUDE.md, settings.json, agents/, templates/
```

#### Test 2: Default Init (No Args)
```bash
cd /tmp/test-project
taskwright init
# Expected: Initializes with default template (language-agnostic)
```

#### Test 3: Explicit Default Init
```bash
cd /tmp/test-project-2
taskwright init default
# Expected: Initializes with default template
```

#### Test 4: Template Creation Workflow
```bash
# Scenario: User with Go project evaluates Taskwright
cd /path/to/go-project
taskwright init  # Uses default
# [Work in Claude Code]
/template-create  # Creates custom template from Go code
taskwright init my-go-template  # Future projects use custom template
```

#### Test 5: Help Text Accuracy
```bash
taskwright init --help
# Expected: "default - Language-agnostic template" description accurate
```

## Test Requirements

### Unit Tests
- [ ] Template structure validation (CLAUDE.md, settings.json, agents/, templates/)
- [ ] File content validation (no placeholders, complete content)
- [ ] Quality scoring ≥8.0/10

### Integration Tests
- [ ] Fresh installation includes default template
- [ ] `taskwright init` defaults to "default" when no arg provided
- [ ] `taskwright init default` explicitly selects default
- [ ] Template works with `/template-create` command (TASK-068)

### Quality Tests
- [ ] Template audit score ≥8.0/10 (TASK-056 methodology)
- [ ] CLAUDE.md provides actionable guidance (not generic)
- [ ] Settings appropriate for language-agnostic workflow

## Files to Create/Modify

### Files to Create (Reinstated)
```
installer/global/templates/default/
├── CLAUDE.md (IMPROVED: clear guidance, use cases, 8+/10 quality)
├── settings.json (IMPROVED: simplified, language-agnostic defaults)
├── agents/
│   └── architectural-reviewer.md (language-agnostic version)
└── templates/
    ├── adr-template.md (IMPROVED: better examples)
    ├── bdd-scenario.md (IMPROVED: clearer Gherkin)
    ├── ears-requirement.md (IMPROVED: better EARS notation)
    └── task-template.md (UPDATED: Phase 2.5/4.5 gates)
```

### Files to Modify
```
CLAUDE.md (root)
├── Update "Available Templates" section
└── Add guidance on default vs stack-specific selection

README.md
├── Add default to template table
└── Update quality scores

docs/guides/template-migration.md
├── Update default template section
└── Change "removed" to "improved and reinstated"

CHANGELOG.md
└── Add v2.0.1 entry for default template reinstatement
```

### Files Verified (No Changes Needed)
```
installer/scripts/install.sh
├── Line 307: Copies templates (already works) ✓
└── Lines 304-312: Template installation loop ✓

~/.agentecflow/scripts/init-project.sh
├── Line 26: Defaults to "default" ✓
└── Lines 214-216: Fallback to default ✓

~/.agentecflow/bin/taskwright-init
└── Help text mentions default ✓
```

## Success Metrics

### Quality Improvement
- **Before**: 6.0/10 ("Generic template with minimal guidance")
- **After**: ≥8.0/10 (Clear guidance, specific use cases, actionable content)

### Breaking Changes Fixed
- ✅ Scripts work with default template
- ✅ Fresh installations include default
- ✅ Documentation accurate
- ✅ No errors when running `taskwright init`

### Use Case Coverage
- ✅ Language-agnostic initialization (Go, Rust, Ruby, Elixir, PHP, etc.)
- ✅ Taskwright evaluation workflow
- ✅ `/template-create` workflow (init default → create custom → use custom)

### User Impact
- **Before**: Breaking changes for new installations
- **After**: Seamless experience for all users, all languages

## Risk Mitigation

### Risk 1: Template Quality Still Low
**Mitigation**: Run quality audit (TASK-056 methodology) before completion
**Threshold**: Must score ≥8.0/10 or iterate

### Risk 2: Conflicts with Stack-Specific Templates
**Mitigation**: Clear documentation on when to use default vs others
**Indicator**: Users choose wrong template → Add decision tree to docs

### Risk 3: Breaking Changes in Scripts
**Mitigation**: Verify all script references work with reinstated template
**Test**: Fresh installation + init with no args

## Related Documentation

- **Parent Task**: [TASK-060](tasks/completed/TASK-060-remove-low-quality-templates.md) - Original removal
- **Documentation Task**: [TASK-061](tasks/backlog/TASK-061-update-template-documentation.md) - Assumes default exists
- **Template Location**: [TASK-068](tasks/completed/TASK-068-refactor-template-creation-location-strategy.md) - Output location flag
- **Quality Audit**: [TASK-056](tasks/completed/TASK-056-audit-template-quality.md) - Scoring methodology

## Questions to Resolve

1. ✅ Should default be the default template when running `taskwright init`?
   - **Answer**: Yes (already is in init-project.sh line 26)

2. Should we add auto-detection to suggest stack-specific templates when available?
   - **Example**: User runs `taskwright init` in React project → suggest `taskwright init react`

3. Should default template include placeholder detection for common patterns?
   - **Example**: Detect `package.json` → suggest React/TypeScript templates

4. Should we create a template quality baseline test suite?
   - **Purpose**: Prevent future quality regressions

## Notes

### Original Template Files (Archived at commit 413a36b)
- CLAUDE.md: 157 lines (generic project overview)
- settings.json: 82 lines (documentation levels)
- agents/architectural-reviewer.md: 655 lines
- templates/adr-template.md: 183 lines
- templates/bdd-scenario.md: 200 lines
- templates/ears-requirement.md: 99 lines
- templates/task-template.md: 191 lines

**Total**: 9 files in archived template

### Why 6.0/10 Score (TASK-060)?
- "Generic template with minimal guidance"
- CLAUDE.md was boilerplate without specific direction
- Settings.json not optimized for any particular workflow
- Templates were complete but not exceptional

### Improvement Strategy
- Transform "generic" into "intentionally language-agnostic"
- Add clear use case guidance (when to use, when not to use)
- Better examples in template files
- Integration with `/template-create` workflow

---

**Estimated Complexity**: 5/10 (Medium)
- File restoration: Low complexity
- Quality improvements: Medium complexity
- Documentation updates: Medium complexity
- Testing: Low-medium complexity

**Estimated Duration**: 4-6 hours

**Priority**: High
- **Reason**: Breaking changes affect new installations
- **Impact**: All users who don't use React/Python/.NET stacks

**Type**: Bug Fix + Enhancement
- Fixes breaking changes from TASK-060
- Improves template quality (6.0 → 8.0+)
- Restores language-agnostic use case
