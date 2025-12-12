---
id: TASK-TI-004
title: Update template-init documentation for rules structure
status: completed
created: 2025-12-12T10:45:00Z
updated: 2025-12-12T15:30:00Z
completed: 2025-12-12T15:30:00Z
priority: medium
tags: [template-init, documentation, rules-structure, progressive-disclosure]
complexity: 3
implementation_method: direct
wave: 3
conductor_workspace: template-init-rules-wave3-1
parent_feature: template-init-rules-structure
---

# Task: Update template-init Documentation for Rules Structure

## Description

Update `/template-init` command documentation to fully align with `/template-create` for rules structure and progressive disclosure features.

## Implementation Method

**Direct** (Claude Code) - Documentation-only changes, no code required.

## What to Update

### 1. Output Structure Diagram

Update the "Template Structure" section to show rules structure:

**Current** (around line 495):
```
{template-name}/
├── template-manifest.json
├── settings.json
├── CLAUDE.md
├── agents/
├── templates/
└── .validation-compatible
```

**Updated**:
```
{template-name}/
├── template-manifest.json
├── settings.json
├── .claude/
│   ├── CLAUDE.md              # Core documentation (~5KB)
│   └── rules/
│       ├── code-style.md      # paths: **/*.{ext}
│       ├── testing.md         # paths: **/tests/**
│       ├── patterns/
│       │   └── {pattern}.md   # Architecture-specific
│       └── guidance/
│           └── {agent}.md     # Agent guidance (slim)
├── agents/
│   ├── {name}.md              # Core agent (~8KB)
│   └── {name}-ext.md          # Extended content (~20KB)
├── templates/
└── .validation-compatible
```

### 2. Add Rules Structure Section

Add new section after "Two-Location Output" (around line 189):

```markdown
### 9. Rules Structure Generation (NEW)

Generated templates include modular `.claude/rules/` directory for optimized context loading.

**Generated Files**:
- `code-style.md` - Language-specific style rules with path patterns
- `testing.md` - Framework-specific testing guidance
- `patterns/*.md` - Architecture pattern documentation
- `guidance/*.md` - Slim agent guidance files

**Benefits**:
- 60-70% context window reduction
- Path-specific rule loading
- Better organization for complex templates
- Conditional agent guidance loading

**Opt-Out**:
```bash
/template-init --no-rules-structure
# Uses single CLAUDE.md without rules/ directory
```

See [Rules Structure Guide](../../docs/guides/rules-structure-guide.md) for details.
```

### 3. Add Progressive Disclosure Section

Add section explaining agent split files:

```markdown
### 10. Progressive Disclosure Agent Files (NEW)

Generated agents are split into core and extended files:

**Core File** (`{name}.md`, ~6-10KB):
- Frontmatter and metadata
- Boundaries (ALWAYS/NEVER/ASK)
- Quick Start examples (5-10)
- Capabilities summary
- Phase integration

**Extended File** (`{name}-ext.md`, ~15-25KB):
- Detailed code examples (30+)
- Best practices with explanations
- Anti-patterns with code samples
- Technology-specific guidance
- Troubleshooting scenarios

**Benefits**:
- 55-60% token reduction in typical tasks
- Faster AI responses
- Same comprehensive content when needed

**Loading Extended Content**:
```bash
cat agents/{agent-name}-ext.md
```
```

### 4. Update Feature Comparison Table

Update table (around line 534) to include all features:

```markdown
| Feature | /template-init | /template-create |
|---------|----------------|------------------|
| **Input** | Q&A session | Existing codebase |
| **Use Case** | Greenfield projects | Brownfield projects |
| **Boundary Sections** | ✅ Yes | ✅ Yes |
| **Agent Tasks** | ✅ Yes | ✅ Yes |
| **Validation Levels** | ✅ L1/L2/L3 | ✅ L1/L2/L3 |
| **Quality Scoring** | ✅ Q&A-based | ✅ Code analysis-based |
| **Output Locations** | ✅ global/repo | ✅ global/repo |
| **Discovery Metadata** | ✅ Yes | ✅ Yes |
| **Exit Codes** | ✅ Yes | ✅ Yes |
| **Rules Structure** | ✅ Default | ✅ Default |
| **Progressive Disclosure** | ✅ Yes | ✅ Yes |
| **Agent Split Files** | ✅ Yes | ✅ Yes |
| **AI Analysis** | Generated from Q&A | Inferred from codebase |
```

### 5. Update Phase Descriptions

Update workflow phases to include new phases:

**Before Phase 4** (add new):
```markdown
### Phase 3.5: Agent Split Generation
- Split generated agents into core + extended files
- Core: boundaries, quick start, capabilities
- Extended: detailed examples, best practices
- Validate size targets (core <15KB, extended <30KB)

**Duration**: 5-10 seconds
```

**After Phase 4** (add new):
```markdown
### Phase 4.5: Rules Structure Generation (Default)
- Generate `.claude/rules/` directory structure
- Create code-style.md based on language selection
- Create testing.md based on testing framework
- Create patterns/ based on architecture pattern
- Generate guidance/ from agent files
- Skip if --no-rules-structure flag set

**Duration**: 10-30 seconds
```

### 6. Update Examples Section

Add example showing complete output with rules structure:

```markdown
### Complete Output Example (with Rules Structure)
```bash
/template-init

[... Q&A session ...]

✅ Template Package Created Successfully!

📁 Location: ~/.agentecflow/templates/my-api/
🎯 Type: Personal use (immediately available)

  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── .claude/
  │   ├── CLAUDE.md (5 KB, core)
  │   └── rules/
  │       ├── code-style.md (3 KB)
  │       ├── testing.md (2.5 KB)
  │       ├── patterns/
  │       │   └── layered.md (2 KB)
  │       └── guidance/
  │           └── api-specialist.md (2.5 KB)
  ├── agents/
  │   ├── api-specialist.md (8 KB, core)
  │   └── api-specialist-ext.md (18 KB, extended)
  └── templates/ (5 files)

📝 Next Steps:
   guardkit init my-api
```
```

## Acceptance Criteria

- [x] Output structure diagram updated to show rules structure
- [x] New "Rules Structure Generation" section added
- [x] New "Progressive Disclosure Agent Files" section added
- [x] Feature comparison table updated with all features
- [x] Phase descriptions updated with new phases
- [x] Examples show complete output with rules structure
- [x] All documentation consistent with `/template-create`

## Files to Modify

- `installer/core/commands/template-init.md`

## Dependencies

- TASK-TI-002: Rules structure implementation (for accuracy)
- TASK-TI-003: Agent split implementation (for accuracy)

## Related Tasks

- TASK-TI-001: Flags documentation (already done in Wave 1)
- TASK-TI-005: Guidance file generation (parallel in Wave 3)
