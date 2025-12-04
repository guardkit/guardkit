# Progressive Disclosure Implementation Scope

**Date**: December 2025  
**Status**: Analysis Complete  
**Complexity**: HIGH - Touches multiple components across the template generation pipeline  
**Priority**: HIGH - Implement before public launch to avoid migration complexity

## Executive Summary

Implementing progressive disclosure in GuardKit requires changes across **5 major components**:

1. **CLAUDE.md Generator** - Split output into core + pattern references
2. **Agent Enhancement Command** - Write to separate `-ext.md` files instead of appending
3. **Enhancement Applier** - Major refactor to create separate files
4. **Global Agents** - Manually split existing large agent definitions
5. **Template Validation** - Update to recognize and validate split structure

This is NOT a simple refactoring task. It requires coordinated changes to maintain consistency across the template generation pipeline.

## Strategic Timing: Pre-Launch Implementation

### Why Implement Before Public Launch

Implementing progressive disclosure before the public launch of TaskWright and RequireKit provides significant advantages:

| Migration Work Avoided | Effort Saved |
|------------------------|--------------|
| Backward compatibility code | 2-3 days |
| Version detection logic | 1 day |
| Supporting two structures in validation | 1-2 days |
| Migration helper tool | 1-2 days |
| Documentation for "legacy" format | 1 day |
| GitHub issues from confused users | Ongoing |
| Deprecation warnings and announcements | Ongoing |

**Net savings: ~6-8 days plus ongoing support burden**

### The Developer Evaluation Problem

When developers evaluate frameworks, they measure what's easy to quantify:

| What Developers Measure | What Actually Matters |
|------------------------|----------------------|
| ⏱️ Time to first output | Code quality over time |
| 📊 Tokens consumed | Architectural consistency |
| 🔢 Number of commands | Reduction in rework/bugs |
| 📁 Lines of code generated | Maintainability |
| ✅ "It works" on first try | Test coverage quality |

**The irony**: GuardKit's value proposition is quality gates and human checkpoints - benefits that only become apparent after weeks of use, not in a 30-minute evaluation.

### First Impressions Window

A developer evaluating frameworks will typically:

1. Clone repo, run installer
2. Try `/template-create` on a sample project
3. Run `/task-work` on one feature
4. **Form opinion within 1-2 hours**

If during that window they see high token usage and slow responses, they'll move on before experiencing the quality benefits.

### Positioning Opportunity

Progressive disclosure can be positioned as a feature in launch messaging:

> *"GuardKit uses progressive disclosure to load only what's needed - core context always, detailed examples on-demand. This keeps token usage efficient while maintaining comprehensive quality standards."*

## Current Architecture

### File Generation Flow

```
/template-create or /template-init
    │
    ├── Phase 1-4: Analysis & Generation
    │
    ├── Phase 5: Agent Generation (agent_generator.py)
    │   └── Creates initial agent files with frontmatter + basic structure
    │
    ├── Phase 5.5: Agent Formatting (/agent-format)
    │   └── Adds boundary section TEMPLATES (✅/❌/⚠️ markers)
    │
    ├── Phase 6: CLAUDE.md Generation (claude_md_generator.py)
    │   └── Creates COMPLETE CLAUDE.md with ALL sections:
    │       ├── architecture_overview
    │       ├── technology_stack
    │       ├── project_structure
    │       ├── naming_conventions
    │       ├── patterns
    │       ├── examples
    │       ├── quality_standards
    │       └── agent_usage
    │
    ├── Phase 7: Package Assembly
    │   └── Writes all files to template directory
    │
    └── Phase 8: Agent Enhancement Tasks (optional)

/agent-enhance (run later, per-agent)
    │
    ├── Load agent metadata from frontmatter
    │
    ├── Discover relevant templates
    │
    ├── Generate enhancement (AI/static/hybrid)
    │   └── Returns: sections[], related_templates, examples, best_practices, boundaries
    │
    └── Apply enhancement (applier.py)
        └── APPENDS content to original agent file IN-PLACE
```

### Current Enhancement Applier Behavior

The `EnhancementApplier._merge_content()` method currently:

1. Preserves all original content
2. Inserts boundaries after "Quick Start" section
3. **Appends** other sections (related_templates, examples, best_practices) at the **end** of the file

**This is the root cause of large agent files** - all enhanced content goes into a single file.

## Required Changes

### 1. CLAUDE.md Generator (`claude_md_generator.py`)

**Current**: Generates a single ~20KB CLAUDE.md file

**Required Changes**:

```python
# Current method
def generate(self) -> TemplateClaude:
    return TemplateClaude(
        schema_version="1.0.0",
        architecture_overview=self._generate_architecture_overview(),  # ✓ Core
        technology_stack=self._generate_technology_stack(),            # ✓ Core
        project_structure=self._generate_project_structure(),          # ✓ Core
        naming_conventions=self._generate_naming_conventions(),        # ✓ Core
        patterns=self._generate_patterns(),                            # → Split out
        examples=self._generate_examples(),                            # → Split out
        quality_standards=self._generate_quality_standards(),          # ✓ Core
        agent_usage=self._generate_agent_usage(),                      # ✓ Core
    )

# New methods needed
def generate_core(self) -> CoreClaudeMd:
    """Generate core CLAUDE.md (~8KB)"""
    # Include: architecture, tech_stack, project_structure, 
    #          naming_conventions, quality_standards, agent_usage
    # Add: References to split-out pattern files

def generate_patterns(self) -> Dict[str, str]:
    """Generate pattern files for docs/patterns/"""
    # Return dict of filename -> content
    # e.g., {"react-query-patterns.md": "...", "form-patterns.md": "..."}

def generate_reference(self) -> Dict[str, str]:
    """Generate reference files for docs/reference/"""
    # Return dict of filename -> content
    # e.g., {"troubleshooting.md": "...", "development-workflow.md": "..."}
```

**New Output Structure**:
```
template/
├── CLAUDE.md                      # Core (~8KB) with references
└── docs/
    ├── patterns/
    │   ├── react-query-patterns.md
    │   ├── form-validation-patterns.md
    │   └── component-patterns.md
    └── reference/
        ├── troubleshooting.md
        └── development-workflow.md
```

**Effort**: Medium (refactor existing generation, add new file creation)

---

### 2. Agent Enhancement Command (`agent-enhance.md`, `enhancer.py`)

**Current**: Enhances agent by appending content to the same file

**Required Changes**:

The `SingleAgentEnhancer.enhance()` method must:

1. Generate enhancement content (same as now)
2. **NEW**: Write to `{agent-name}-ext.md` instead of appending
3. **NEW**: Add loading instruction to core agent file
4. **NEW**: Return both files in result

```python
# Current
def enhance(self, agent_file: Path, template_dir: Path) -> EnhancementResult:
    # ... generates enhancement
    self.applier.apply(agent_file, enhancement)  # Modifies in-place
    return result

# Required
def enhance(self, agent_file: Path, template_dir: Path) -> EnhancementResult:
    # ... generates enhancement
    ext_file = self._create_extended_file(agent_file, enhancement)
    self._add_loading_instruction(agent_file, ext_file)
    return result
```

**New Output Structure**:
```
agents/
├── react-query-specialist.md        # Core (~6KB) + loading instruction
└── react-query-specialist-ext.md    # Extended (~10KB) - templates, examples
```

**Core agent file gets this added**:
```markdown
## 📚 Extended Reference (Load Before Code Generation)

**Template examples and anti-patterns**: 
```bash
cat agents/react-query-specialist-ext.md
```

Load this file before generating code from templates to ensure pattern compliance.
```

**Effort**: High (significant behavior change, new file creation logic)

---

### 3. Enhancement Applier (`applier.py`)

**Current**: `_merge_content()` appends sections to original file

**Required Changes**:

Complete refactor needed:

```python
# Current
class EnhancementApplier:
    def apply(self, agent_file: Path, enhancement: Dict[str, Any]) -> None:
        # Reads file, merges content, writes back to SAME file
        new_content = self._merge_content(original_content, enhancement)
        safe_write_file(agent_file, new_content)

# Required
class EnhancementApplier:
    def apply(
        self, 
        agent_file: Path, 
        enhancement: Dict[str, Any]
    ) -> Tuple[Path, Path]:
        """
        Create extended file and update core file with reference.
        
        Returns:
            Tuple of (core_file_path, extended_file_path)
        """
        # 1. Create extended file with template content
        ext_file = self._create_extended_file(agent_file, enhancement)
        
        # 2. Add loading instruction to core file
        self._add_loading_instruction(agent_file, ext_file)
        
        return (agent_file, ext_file)
    
    def _create_extended_file(
        self, 
        agent_file: Path, 
        enhancement: Dict[str, Any]
    ) -> Path:
        """Create {agent-name}-ext.md with extended content."""
        ext_path = agent_file.with_stem(f"{agent_file.stem}-ext")
        
        content = self._format_extended_content(enhancement)
        safe_write_file(ext_path, content)
        
        return ext_path
    
    def _add_loading_instruction(self, agent_file: Path, ext_file: Path) -> None:
        """Add reference to extended file in core agent."""
        # Read core agent
        # Find insertion point (after boundaries, before capabilities)
        # Insert loading instruction
        # Write back
```

**Effort**: High (complete behavior change)

---

### 4. Global Agents (`installer/global/agents/`)

**Current**: Large monolithic agent files (16-44KB each)

**Required Changes**:

Manually split existing large agents:

```
Current:
├── architectural-reviewer.md (44KB)
├── code-reviewer.md (25KB)
├── test-orchestrator.md (20KB)
└── ...

Required:
├── architectural-reviewer.md (18KB core)
├── architectural-reviewer-ext.md (26KB extended)
├── code-reviewer.md (12KB core)
├── code-reviewer-ext.md (13KB extended)
└── ...
```

**Content Split Guidelines**:

**Core file should contain**:
- YAML frontmatter (complete)
- Role description
- Quick Start
- Boundaries (ALWAYS/NEVER/ASK)
- Capabilities summary
- Phase integration

**Extended file should contain**:
- Detailed code examples
- Template best practices
- Anti-patterns with full code
- Cross-stack considerations
- Edge case handling

**Effort**: High (manual work for 10+ agent files)

---

### 5. Stack-Specific Agents (in templates)

**Current**: Built-in templates have stack-specific agents

**Impact**:

- `/template-create` generates new templates - will use new split structure after changes
- Existing built-in templates need manual migration:

```
installer/global/templates/
├── react-typescript/agents/
│   ├── react-query-specialist.md → split needed
│   └── form-validation-specialist.md → split needed
├── fastapi-python/agents/
│   └── ... → split needed
└── nextjs-fullstack/agents/
    └── ... → split needed
```

**Effort**: Medium (depends on number of built-in templates)

---

### 6. Template Validation

**Current**: Validates single agent files

**Required Changes**:

Update validation to:
1. Recognize `-ext.md` files as valid companion files
2. Validate that core files have loading instructions when ext files exist
3. Validate that ext files are referenced correctly

**Effort**: Low-Medium

---

### 7. Documentation Updates

Commands requiring documentation updates:
- `template-create.md` - Document new split output structure
- `template-init.md` - Document new split output structure
- `agent-enhance.md` - Document ext file creation behavior
- `agent-format.md` - May need updates if it should handle ext files

**Effort**: Low

---

## Effort Estimates

### Pre-Launch Implementation (Recommended)

No migration support needed - clean implementation:

| Component | Days | Complexity |
|-----------|------|------------|
| Applier refactor | 2-3 | High |
| Enhancer updates | 1-2 | Medium |
| CLAUDE.md generator | 2-3 | Medium |
| Global agent split | 2-3 | Medium (manual) |
| Template agent split | 1-2 | Medium (manual) |
| Validation updates | 1 | Low |
| Documentation | 1 | Low |
| Testing | 2 | Medium |
| **Total** | **~10-14 days** | **High** |

### Post-Launch Implementation (If Delayed)

Would require additional migration support:

| Additional Work | Days |
|-----------------|------|
| Backward compatibility code | 2-3 |
| Version detection logic | 1 |
| Dual-format validation support | 1-2 |
| Migration helper tool | 1-2 |
| Legacy documentation | 1 |
| **Additional Total** | **~6-8 days** |

**Post-launch total: ~16-22 days** (plus ongoing support burden)

## Implementation Strategy

### Recommended Sequencing

1. **Applier + Enhancer first** - This is the core behavior change
2. **Test with one agent** - Validate the split structure works
3. **CLAUDE.md generator** - Apply same pattern
4. **Split existing agents** - Manual but straightforward
5. **Final validation pass** - Everything works together

### Phase 1: Foundation (Core Infrastructure)

1. **Create new applier behavior** - Write to separate files
2. **Update enhancer** - Use new applier, handle ext files
3. **Update agent-enhance command** - New output format
4. **Test** - Verify new behavior with single agent

### Phase 2: CLAUDE.md Split

1. **Refactor ClaudeMdGenerator** - Split generation methods
2. **Update template_create_orchestrator** - Write split files
3. **Update template_init** - Use new generation methods
4. **Test** - Verify template creation produces split structure

### Phase 3: Migration

1. **Split global agents** - Manual work with defined guidelines
2. **Split built-in template agents** - Apply same guidelines
3. **Update validation** - Handle new structure
4. **Documentation** - Update all command docs

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Agents not loading ext files | MEDIUM | Clear loading instructions, validation |
| Token savings less than expected | LOW | Measure actual savings before/after |
| Increased complexity | MEDIUM | Clear documentation, consistent patterns |
| Discovery system breaks | MEDIUM | Update discovery to index ext files |

## Decision Points

### 1. Extension File Naming

**Option A**: `{name}-ext.md` ✓ Recommended
- Clear relationship
- Easy to filter in listings

**Option B**: `{name}.extended.md`
- More descriptive
- Slightly longer

### 2. Loading Instruction Format

**Option A**: Explicit `cat` command ✓ Recommended
```markdown
## Extended Reference
Load before code generation:
```bash
cat agents/react-query-specialist-ext.md
```
```

**Option B**: Frontmatter reference
```yaml
extended_context:
  - agents/react-query-specialist-ext.md
```

## Next Steps

1. **Approve this scope document**
2. **Create implementation tasks** in backlog
3. **Prototype Phase 1** with single agent enhancement
4. **Measure token savings** to validate approach
5. **Complete implementation** before public launch
6. **Launch** with optimized architecture from day one

## Appendix: File Changes Summary

### Files to Modify

```
installer/global/lib/
├── agent_enhancement/
│   ├── enhancer.py              # Major: new file creation behavior
│   └── applier.py               # Major: complete refactor
├── template_generator/
│   └── claude_md_generator.py   # Medium: split generation
└── template_creation/
    └── template_create_orchestrator.py  # Medium: write split files

installer/global/commands/
├── agent-enhance.md             # Documentation update
├── template-create.md           # Documentation update
└── template-init.md             # Documentation update
```

### Files to Create (for each existing large agent)

```
installer/global/agents/
├── architectural-reviewer-ext.md    # New
├── code-reviewer-ext.md             # New
├── test-orchestrator-ext.md         # New
└── ... (other global agents)
```

### Files to Modify (existing agents)

```
installer/global/agents/
├── architectural-reviewer.md    # Add loading instruction
├── code-reviewer.md             # Add loading instruction
├── test-orchestrator.md         # Add loading instruction
└── ... (other global agents)
```
