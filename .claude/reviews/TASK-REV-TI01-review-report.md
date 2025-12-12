# Review Report: TASK-REV-TI01

## Executive Summary

The `/template-init` command and `init-project.sh` script have **partial support** for both progressive disclosure and rules structure, but there are **significant gaps** that need to be addressed for full alignment with the recent `/template-create` updates.

**Overall Assessment**: The `init-project.sh` script correctly copies the rules structure from templates, but the `/template-init` command specification (greenfield template creation) lacks documentation and implementation for generating rules structure in new templates created from Q&A sessions.

**Architecture Score**: 65/100
- Progressive Disclosure: 70/100 (partial support)
- Rules Structure: 60/100 (runtime support, generation gap)
- Documentation Alignment: 55/100 (needs update)
- Consistency with template-create: 70/100

## Review Scope

### Files Analyzed

1. **Command Specification**: `installer/core/commands/template-init.md`
2. **Implementation Script**: `installer/scripts/init-project.sh`
3. **Reference**: `installer/core/commands/template-create.md`
4. **Guide**: `docs/guides/rules-structure-guide.md`
5. **Existing Templates**: `installer/core/templates/*/`

## Findings

### Finding 1: init-project.sh Has Rules Structure Support (GOOD)

**Evidence**: Lines 255-259 of `init-project.sh`

```bash
# Copy .claude/rules/ directory (for Claude Code modular rules)
if [ -d "$template_dir/.claude/rules" ]; then
    mkdir -p .claude/rules
    cp -r "$template_dir/.claude/rules/"* .claude/rules/ 2>/dev/null || true
    print_success "Copied rules structure for Claude Code"
fi
```

**Also**: Lines 286-303 verify the rules structure was copied correctly.

**Status**: ✅ **Working correctly** - The runtime initialization script properly copies the rules structure from templates.

### Finding 2: init-project.sh Has Progressive Disclosure Support (GOOD)

**Evidence**: Lines 234-253 of `init-project.sh`

```bash
# Copy template docs (patterns/reference for progressive disclosure)
if [ -d "$template_dir/docs" ]; then
    local docs_copied=0

    # Copy patterns if exists
    if [ -d "$template_dir/docs/patterns" ]; then
        mkdir -p docs/patterns
        cp -r "$template_dir/docs/patterns/"* docs/patterns/ 2>/dev/null && docs_copied=1 || true
    fi

    # Copy reference if exists
    if [ -d "$template_dir/docs/reference" ]; then
        mkdir -p docs/reference
        cp -r "$template_dir/docs/reference/"* docs/reference/ 2>/dev/null && docs_copied=1 || true
    fi
```

**Status**: ✅ **Working correctly** - Progressive disclosure docs are copied during initialization.

### Finding 3: Existing Templates Have Rules Structure (GOOD)

**Evidence**: Templates already include `.claude/rules/` structure:

- `react-typescript/.claude/rules/` - 10 rule files with `paths:` frontmatter
- `fastapi-python/.claude/rules/` - 12 rule files with `paths:` frontmatter
- `nextjs-fullstack/.claude/rules/` - Similar structure

**Status**: ✅ **Templates are compliant** - All reference templates have the rules structure.

### Finding 4: Templates Have Progressive Disclosure Split Files (GOOD)

**Evidence**: 14 agent files found with `-ext.md` suffix:

- `react-typescript/agents/react-query-specialist-ext.md`
- `fastapi-python/agents/fastapi-specialist-ext.md`
- etc.

**Status**: ✅ **Templates are compliant** - Progressive disclosure split files exist.

### Finding 5: /template-init Command Missing Rules Structure Flags (GAP)

**Evidence**: The command specification (`installer/core/commands/template-init.md`) has these options:

```
--validate                    Run extended validation (Level 2)
--output-location global|repo Where to save template
--no-create-agent-tasks       Skip agent enhancement task creation
```

**Missing Flags** (compared to `/template-create`):
- `--use-rules-structure` (default: true)
- `--no-rules-structure` (opt-out)
- `--claude-md-size-limit SIZE`

**Status**: ❌ **Gap identified** - Greenfield template creation cannot generate rules structure.

### Finding 6: /template-init Generated Structure Missing Rules Directory (GAP)

**Evidence**: Template structure documentation in `template-init.md` shows:

```
{template-name}/
├── template-manifest.json
├── settings.json
├── CLAUDE.md                    # Single file, no rules/ mentioned
├── agents/
├── templates/
└── .validation-compatible
```

**Compare to `/template-create`** output structure:

```
.claude/
├── CLAUDE.md                    # Core documentation (~5KB)
└── rules/
    ├── code-style.md
    ├── testing.md
    ├── patterns/
    └── agents/
```

**Status**: ❌ **Gap identified** - Greenfield templates don't get rules structure.

### Finding 7: /template-init Documentation Not Aligned with Recent Work (GAP)

**Evidence**: The specification mentions:
- Boundary sections ✅
- Agent enhancement tasks ✅
- Validation levels ✅
- Progressive disclosure ❌ (not mentioned)
- Rules structure ❌ (not mentioned)

The comparison table (lines 534-561) shows feature parity claims but omits rules structure:

```
| **Boundary Sections** | ✅ Yes | ✅ Yes |
| **Agent Tasks** | ✅ Yes | ✅ Yes |
| **Validation Levels** | ✅ L1/L2/L3 | ✅ L1/L2/L3 |
```

But no row for rules structure or progressive disclosure.

**Status**: ❌ **Gap identified** - Documentation needs update for feature parity.

### Finding 8: Phase Structure Missing Rules Generation Phase

**Evidence**: `/template-init` phases (lines 311-410):

```
Phase 1: Identity
Phase 2: Q&A Session
Phase 3: Agent Generation
Phase 3.5: Level 1 Validation
Phase 4: Save Template
Phase 4.5: Quality Scoring
Phase 5: Agent Enhancement Tasks
Phase 5.5: Extended Validation
Phase 6: Display Guidance
```

**Compare to `/template-create`** phases:

```
Phase 6: CLAUDE.md Generation
├─ **[DEFAULT] Rules structure generation**
    ├─ Core CLAUDE.md (~5KB)
    ├─ rules/code-style.md
    ├─ rules/testing.md
    ├─ rules/patterns/*.md
    └─ rules/guidance/*.md (with paths: frontmatter)
```

**Status**: ❌ **Gap identified** - No phase for generating rules structure.

## Gap Analysis Summary

| Feature | /template-create | /template-init | init-project.sh |
|---------|-----------------|----------------|-----------------|
| Rules structure output | ✅ Default | ❌ Missing | ✅ Copies from template |
| `--use-rules-structure` flag | ✅ Yes (default) | ❌ Missing | N/A |
| `--no-rules-structure` flag | ✅ Yes | ❌ Missing | N/A |
| `--claude-md-size-limit` | ✅ Yes | ❌ Missing | N/A |
| Progressive disclosure docs | ✅ Generated | ❌ Not generated | ✅ Copies from template |
| Agent split files (-ext.md) | ✅ Generated | ❌ Not generated | ✅ Copies from template |
| Documentation aligned | ✅ Yes | ❌ Needs update | ✅ N/A |

## Recommendations

### Recommendation 1: Add Rules Structure Generation to /template-init (HIGH)

**Priority**: High
**Effort**: Medium (3-5 hours)

Add a new phase or extend Phase 4 to generate rules structure:

```
Phase 4.5 (new): Rules Structure Generation
├─ If not --no-rules-structure:
│   ├─ Create .claude/rules/ directory
│   ├─ Generate code-style.md based on Q&A answers (language-specific)
│   ├─ Generate testing.md based on Q&A answers (framework-specific)
│   ├─ Generate patterns/ files based on architecture pattern
│   └─ Generate guidance/ files from agents (slim summaries)
└─ Else: Single CLAUDE.md with all content
```

### Recommendation 2: Add Command Flags (HIGH)

**Priority**: High
**Effort**: Low (1-2 hours)

Add to `/template-init` options:

```markdown
--use-rules-structure    Generate modular .claude/rules/ structure (default: enabled)
                         Default: true

--no-rules-structure     Use single CLAUDE.md instead of modular rules/ directory
                         Use for simple templates (<15KB)

--claude-md-size-limit SIZE  Maximum size for core CLAUDE.md content
                             Format: NUMBER[KB|MB] (e.g., 100KB, 1MB)
                             Default: 50KB
```

### Recommendation 3: Generate Agent Split Files (MEDIUM)

**Priority**: Medium
**Effort**: Medium (2-3 hours)

During agent generation (Phase 3), split agents into core + extended:

```
agents/
├── specialist.md           # Core (~6-10KB)
└── specialist-ext.md       # Extended examples and deep reference
```

This aligns with progressive disclosure approach already in place for `/template-create`.

### Recommendation 4: Update Documentation (MEDIUM)

**Priority**: Medium
**Effort**: Low (1 hour)

Update `installer/core/commands/template-init.md`:

1. Add rules structure section similar to `/template-create`
2. Update feature comparison table to include:
   - Rules structure support
   - Progressive disclosure support
   - Agent split files
3. Update output structure diagram to show `.claude/rules/`
4. Add examples showing rules structure output

### Recommendation 5: Add Guidance File Generation (LOW)

**Priority**: Low
**Effort**: Medium (2-3 hours)

Generate slim guidance files from agent files:

```
.claude/rules/guidance/
├── specialist-a.md    # Slim summary (~2-3KB) derived from agents/specialist-a.md
└── specialist-b.md    # With paths: frontmatter for conditional loading
```

This follows the architecture documented in `rules-structure-guide.md`:
- Agent files = source of truth (full content)
- Guidance files = derived summaries (slim, path-triggered)

## Implementation Tasks

Based on findings, the following tasks should be created:

### Task 1: Add Rules Structure Generation to template-init

**Description**: Implement rules structure generation phase in /template-init command
**Complexity**: 6/10
**Files to modify**:
- `installer/core/commands/template-init.md` (specification)
- Python orchestrator for template-init (implementation)

### Task 2: Add Rules Structure Flags to template-init

**Description**: Add --use-rules-structure, --no-rules-structure, and --claude-md-size-limit flags
**Complexity**: 4/10
**Files to modify**:
- `installer/core/commands/template-init.md`
- Related Python argument parser

### Task 3: Generate Agent Split Files in template-init

**Description**: Split generated agents into core + extended files during Phase 3
**Complexity**: 5/10
**Files to modify**:
- Agent generation module

### Task 4: Update template-init Documentation

**Description**: Align documentation with template-create for rules structure and progressive disclosure
**Complexity**: 3/10
**Files to modify**:
- `installer/core/commands/template-init.md`

### Task 5: Generate Guidance Files from Agents

**Description**: Create slim guidance files in .claude/rules/guidance/ from agent content
**Complexity**: 5/10
**Files to modify**:
- Template generation modules

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Greenfield templates missing rules structure | Medium | High | Implement Recommendation 1 |
| User confusion about feature parity | Low | Medium | Implement Recommendation 4 |
| Breaking existing workflows | Low | Low | All changes are additive, defaults preserved |
| Implementation complexity | Medium | Medium | Phase changes incrementally |

## Decision Matrix

| Option | Effort | Impact | Recommendation |
|--------|--------|--------|----------------|
| Full implementation (all 5 tasks) | High (10-15 hours) | High | ✅ Recommended |
| Documentation only (Task 4) | Low (1 hour) | Low | Partial solution |
| Flags + docs (Tasks 2, 4) | Medium (3 hours) | Medium | Minimum viable |
| Defer to future | None | None | Not recommended |

## Conclusion

The `init-project.sh` script is **correctly implemented** for copying rules structure and progressive disclosure files from templates at runtime. However, the `/template-init` command (greenfield template creation) has **significant gaps**:

1. Cannot generate rules structure for new templates
2. Cannot generate progressive disclosure split files
3. Documentation not aligned with recent `/template-create` updates

**Recommended Approach**: Implement Tasks 1-4 to achieve full feature parity with `/template-create`. Task 5 (guidance file generation) can be deferred as a nice-to-have.

**Estimated Total Effort**: 8-12 hours for full implementation

---

**Review Completed**: 2025-12-12
**Review Mode**: architectural
**Review Depth**: standard
**Reviewer**: architectural-reviewer agent
