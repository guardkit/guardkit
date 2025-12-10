# Review Report: TASK-REV-426C

## Progressive Disclosure Refactoring for Stack Templates

**Review Mode**: Architectural
**Review Depth**: Standard (Revised)
**Duration**: ~2.5 hours
**Date**: 2025-12-03
**Revision**: 2 (incorporating user feedback)

---

## Executive Summary

The progressive disclosure proposal is **technically sound and strategically mandatory**. Token savings estimates are validated. This is an **all-or-nothing** refactor required for competitive positioning - developers will measure tokens/time as their primary comparison metric.

**Revised Recommendation**: **APPROVE** - Full implementation before launch with automated agent splitting (following the GitHub best practices pattern from TASK-STND-773D).

---

## User Feedback Incorporated

1. **Not an MVP approach** - This is all-or-nothing because developers will immediately measure token usage and compare with BMAD/SpecKit
2. **Rarely-used agents don't justify MVP** - zeplin-maui, figma-react are specialized; the competitive threat comes from any task
3. **Highest risk first** - template-create on existing codebases is the critical path
4. **Automated refactoring** - Follow the pattern from GitHub best practices (TASK-STND-773D) where `agent-content-enhancer` was updated to automatically generate boundary sections

---

## Revised Architecture: Automated Progressive Disclosure

### Pattern from GitHub Best Practices Implementation

The successful TASK-STND-773D implementation established a **process change** pattern:
- Instead of manually converting 7 agents → Updated `agent-content-enhancer` to generate ALWAYS/NEVER/ASK automatically
- Benefits ALL future enhancements, not just one-time conversion
- Single source of truth in the enhancer

### Apply Same Pattern for Progressive Disclosure

**Core Principle**: Update the generation/enhancement pipeline to **automatically produce split files**, not manually split existing files.

```
CURRENT FLOW:
template-create → claude_md_generator → Single CLAUDE.md (20KB)
agent-enhance → applier → Single agent.md (16-72KB)

NEW FLOW:
template-create → claude_md_generator → CLAUDE.md (8KB core) + docs/patterns/*.md
agent-enhance → applier → agent.md (6-18KB core) + agent-ext.md (10-50KB extended)
```

---

## Revised Implementation Plan

### Risk-Ordered Sequencing

**Principle**: Address highest-risk changes first, validate before proceeding.

### Phase 1: Foundation - Applier Refactor (HIGHEST RISK)

**Risk**: Complete behavior change in core component
**Validation**: Test with single agent before global rollout

| Task | Description | Complexity | Days |
|------|-------------|------------|------|
| **TASK-PD-001** | Refactor `applier.py` to create `{name}-ext.md` files | 7/10 | 2-3 |
| **TASK-PD-002** | Add loading instruction template to core files | 4/10 | 0.5 |
| **TASK-PD-003** | Update `enhancer.py` to use new applier behavior | 5/10 | 1 |
| **TASK-PD-004** | Update agent discovery to exclude `-ext.md` files | 3/10 | 0.5 |

**Checkpoint**: Validate with single test agent before Phase 2

---

### Phase 2: Template Generation - CLAUDE.md Split (MEDIUM RISK)

**Risk**: Changes template-create output structure
**Validation**: Test template-create on sample codebase

| Task | Description | Complexity | Days |
|------|-------------|------------|------|
| **TASK-PD-005** | Refactor `claude_md_generator.py` with `generate_core()` + `generate_patterns()` | 6/10 | 2 |
| **TASK-PD-006** | Update template orchestrator to write split structure | 5/10 | 1 |
| **TASK-PD-007** | Update `TemplateClaude` model for split output | 4/10 | 0.5 |

**Checkpoint**: Run `/template-create` on bulletproof-react sample, validate output

---

### Phase 3: Automated Global Agent Migration (MEDIUM RISK)

**Pattern**: Following TASK-STND-773D approach - batch process with validation

| Task | Description | Complexity | Days |
|------|-------------|------------|------|
| **TASK-PD-008** | Create `split-agent.py` script (automated splitter) | 6/10 | 1.5 |
| **TASK-PD-009** | Define content categorization rules (core vs extended) | 5/10 | 0.5 |
| **TASK-PD-010** | Run automated split on all 19 global agents | 4/10 | 1 |
| **TASK-PD-011** | Validate all split agents (discovery, loading) | 4/10 | 0.5 |

**Automated Splitter Logic**:
```python
# split-agent.py
CORE_SECTIONS = [
    'frontmatter',
    'title + description',
    'Quick Start',
    'Boundaries',
    'Capabilities (condensed)',
    'Phase Integration',
    'Loading Instruction'
]

EXTENDED_SECTIONS = [
    'Detailed Code Examples',
    'Template Best Practices',
    'Anti-Patterns (full)',
    'Cross-Stack Considerations',
    'Edge Cases',
    'MCP Integration Details',
    'Troubleshooting'
]
```

**Checkpoint**: All 19 agents split, discovery works, loading instructions present

---

### Phase 4: Built-in Template Agents (LOW RISK)

| Task | Description | Complexity | Days |
|------|-------------|------------|------|
| **TASK-PD-012** | Split react-typescript template agents (3 agents) | 4/10 | 0.5 |
| **TASK-PD-013** | Split fastapi-python template agents | 4/10 | 0.5 |
| **TASK-PD-014** | Split nextjs-fullstack template agents | 4/10 | 0.5 |
| **TASK-PD-015** | Split react-fastapi-monorepo template agents | 4/10 | 0.5 |

---

### Phase 5: Validation & Documentation (LOW RISK)

| Task | Description | Complexity | Days |
|------|-------------|------------|------|
| **TASK-PD-016** | Update template validation for split structure | 5/10 | 1 |
| **TASK-PD-017** | Update CLAUDE.md documentation (loading instructions section) | 3/10 | 0.5 |
| **TASK-PD-018** | Update command docs (template-create, agent-enhance) | 3/10 | 0.5 |
| **TASK-PD-019** | Integration testing (full workflow validation) | 5/10 | 1 |

---

## Revised Effort Summary

| Phase | Days | Risk Level |
|-------|------|------------|
| Phase 1: Applier Foundation | 4 | HIGH |
| Phase 2: CLAUDE.md Generator | 3.5 | MEDIUM |
| Phase 3: Automated Agent Migration | 3.5 | MEDIUM |
| Phase 4: Template Agents | 2 | LOW |
| Phase 5: Validation & Docs | 3 | LOW |
| **Total** | **16 days** | - |

**Buffer**: +2 days for unforeseen issues = **18 days**

---

## Content Categorization Rules

### Core Content (Always Loaded)

Must contain everything needed for **decision-making**:

```markdown
## Core Agent File Structure

1. YAML Frontmatter (complete - discovery needs this)
2. Title + Role Description (1-2 paragraphs)
3. Quick Start (5-10 essential examples)
4. Boundaries (ALWAYS/NEVER/ASK - GitHub compliance)
5. Capabilities (condensed list, no code)
6. Phase Integration (which phases, auto-routing)
7. Loading Instruction (explicit cat command)
```

### Extended Content (Loaded On-Demand)

Reference material for **implementation**:

```markdown
## Extended Agent File Structure

1. Detailed Code Examples (20-50 examples)
2. Template Best Practices (full explanations)
3. Anti-Patterns (full code with explanations)
4. Cross-Stack Considerations
5. MCP Integration Details
6. Edge Cases & Troubleshooting
7. Technology-Specific Sections
```

### Loading Instruction Format

```markdown
## 📚 Extended Reference

Before generating code or performing detailed implementation, load the extended reference:

```bash
cat agents/{agent-name}-ext.md
```

This file contains:
- 30+ detailed code examples
- Template best practices
- Common anti-patterns to avoid
- Technology-specific guidance
```

---

## Automated Splitter Script Design

### Script: `scripts/split-agent.py`

```python
#!/usr/bin/env python3
"""
Automated agent file splitter for progressive disclosure.

Usage:
    python3 scripts/split-agent.py --agent installer/core/agents/task-manager.md
    python3 scripts/split-agent.py --all-global
    python3 scripts/split-agent.py --template react-typescript
    python3 scripts/split-agent.py --dry-run --all-global

Pattern: Following TASK-STND-773D automated enhancement approach
"""

CORE_SECTION_PATTERNS = [
    r'^---[\s\S]+?---',  # Frontmatter (always keep)
    r'^# .+',  # Title
    r'^## Quick Start',
    r'^## Boundaries',
    r'^## Capabilities',
    r'^## Phase \d',
    r'^## When to Use',
    r'^## Your (Critical )?Mission',
]

EXTENDED_SECTION_PATTERNS = [
    r'^## .*Example',
    r'^## .*Pattern',
    r'^## .*Anti-Pattern',
    r'^## .*Best Practice',
    r'^## .*Troubleshoot',
    r'^## .*Integration',
    r'^## .*Template',
    r'^## .*Technology',
    r'^## .*MCP',
]

def split_agent(agent_path: Path, dry_run: bool = False) -> Tuple[str, str]:
    """Split agent into core + extended files."""
    content = agent_path.read_text()

    core_content = extract_core_sections(content)
    extended_content = extract_extended_sections(content)

    # Add loading instruction to core
    core_content = add_loading_instruction(core_content, agent_path.stem)

    # Add header to extended
    extended_content = add_extended_header(extended_content, agent_path.stem)

    if not dry_run:
        write_files(agent_path, core_content, extended_content)

    return core_content, extended_content

def validate_split(agent_path: Path) -> bool:
    """Validate split agent files."""
    ext_path = agent_path.with_stem(f"{agent_path.stem}-ext")

    # Check core has frontmatter
    # Check core has loading instruction
    # Check extended has content
    # Check combined size ≈ original size
    pass
```

### Validation Checklist (Automated)

```python
def validate_all_splits():
    """Run after Phase 3 to validate all splits."""
    checks = {
        'frontmatter_intact': check_frontmatter_all_agents(),
        'loading_instruction_present': check_loading_instructions(),
        'discovery_excludes_ext': check_discovery_scan(),
        'ext_files_created': check_ext_files_exist(),
        'content_preserved': check_no_content_loss(),
        'size_reduction': check_core_size_reduction(),
    }
    return all(checks.values())
```

---

## Risk Mitigation

### Risk 1: Applier Refactor Breaks Enhancement

**Mitigation**:
- Create new `create_extended_file()` method without touching existing `apply()`
- Feature flag to enable progressive disclosure
- Test with single agent before global rollout

### Risk 2: Automated Splitter Miscategorizes Content

**Mitigation**:
- Review first 3 splits manually
- Define explicit section mapping (not just regex)
- Keep original files as backup until validated

### Risk 3: template-create Regression

**Mitigation**:
- Run template-create on bulletproof-react sample before/after
- Compare token counts
- Verify split structure correct

### Risk 4: Discovery System Breaks

**Mitigation**:
- Simple exclusion: `if not stem.endswith('-ext')`
- Test discovery before/after Phase 1

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Core CLAUDE.md size | ≤8KB | `wc -c CLAUDE.md` |
| Core agent size (avg) | ≤15KB | Average of all core agents |
| Token reduction | ≥55% | Before/after token count |
| Agent discovery | 100% | All 19 agents discovered |
| Loading compliance | 100% | All core files have loading instruction |
| Content preservation | 100% | Core + Extended = Original |

---

## Task Dependency Graph

```
TASK-PD-001 (applier refactor)
    │
    ├─► TASK-PD-002 (loading instruction)
    │       │
    │       └─► TASK-PD-003 (enhancer update)
    │               │
    │               └─► TASK-PD-004 (discovery exclude)
    │                       │
    │                       └─► [CHECKPOINT: Test single agent]
    │
    └─────────────────────────────────────────────────────────────►
                                                                   │
TASK-PD-005 (claude_md_generator) ─────────────────────────────────┤
    │                                                              │
    ├─► TASK-PD-006 (orchestrator update)                          │
    │       │                                                      │
    │       └─► TASK-PD-007 (model update)                         │
    │               │                                              │
    │               └─► [CHECKPOINT: Test template-create]         │
    │                                                              │
    └──────────────────────────────────────────────────────────────►
                                                                   │
TASK-PD-008 (split-agent.py script) ───────────────────────────────┤
    │                                                              │
    ├─► TASK-PD-009 (categorization rules)                         │
    │       │                                                      │
    │       └─► TASK-PD-010 (run on all 19 global agents)          │
    │               │                                              │
    │               └─► TASK-PD-011 (validate splits)              │
    │                       │                                      │
    │                       └─► [CHECKPOINT: All global agents]    │
    │                                                              │
    └──────────────────────────────────────────────────────────────►
                                                                   │
TASK-PD-012-015 (template agents) ─────────────────────────────────┤
    │                                                              │
    └─► [CHECKPOINT: All template agents]                          │
                                                                   │
                                                                   ▼
TASK-PD-016-019 (validation & docs) ─────────────────────────────► COMPLETE
```

---

## Implementation Tasks (Full List)

### Phase 1: Foundation (4 days)

| ID | Title | Complexity | Blocked By |
|----|-------|------------|------------|
| TASK-PD-001 | Refactor applier.py with create_extended_file() method | 7/10 | - |
| TASK-PD-002 | Add loading instruction template generation | 4/10 | PD-001 |
| TASK-PD-003 | Update enhancer.py to call new applier methods | 5/10 | PD-002 |
| TASK-PD-004 | Update agent_scanner.py to exclude -ext.md files | 3/10 | PD-003 |

### Phase 2: CLAUDE.md Generator (3.5 days)

| ID | Title | Complexity | Blocked By |
|----|-------|------------|------------|
| TASK-PD-005 | Refactor claude_md_generator.py (generate_core + generate_patterns) | 6/10 | PD-004 |
| TASK-PD-006 | Update template_create_orchestrator.py for split output | 5/10 | PD-005 |
| TASK-PD-007 | Update TemplateClaude model with split fields | 4/10 | PD-006 |

### Phase 3: Automated Agent Migration (3.5 days)

| ID | Title | Complexity | Blocked By |
|----|-------|------------|------------|
| TASK-PD-008 | Create scripts/split-agent.py (automated splitter) | 6/10 | PD-007 |
| TASK-PD-009 | Define CORE_SECTIONS and EXTENDED_SECTIONS rules | 5/10 | PD-008 |
| TASK-PD-010 | Run split-agent.py --all-global (19 agents) | 4/10 | PD-009 |
| TASK-PD-011 | Validate all split agents (discovery, loading, content) | 4/10 | PD-010 |

### Phase 4: Template Agents (2 days)

| ID | Title | Complexity | Blocked By |
|----|-------|------------|------------|
| TASK-PD-012 | Split react-typescript/agents/*.md (3 files) | 4/10 | PD-011 |
| TASK-PD-013 | Split fastapi-python/agents/*.md | 4/10 | PD-011 |
| TASK-PD-014 | Split nextjs-fullstack/agents/*.md | 4/10 | PD-011 |
| TASK-PD-015 | Split react-fastapi-monorepo/agents/*.md | 4/10 | PD-011 |

### Phase 5: Validation & Documentation (3 days)

| ID | Title | Complexity | Blocked By |
|----|-------|------------|------------|
| TASK-PD-016 | Update template_validation for split structure recognition | 5/10 | PD-015 |
| TASK-PD-017 | Update CLAUDE.md with loading instructions documentation | 3/10 | PD-016 |
| TASK-PD-018 | Update command docs (template-create.md, agent-enhance.md) | 3/10 | PD-017 |
| TASK-PD-019 | Full integration testing (end-to-end workflow) | 5/10 | PD-018 |

---

## Competitive Context

### Why All-or-Nothing

When developers evaluate GuardKit vs BMAD vs SpecKit:

| What They Measure | Why It Matters |
|-------------------|----------------|
| Time to first output | GuardKit's quality gates add time |
| Tokens consumed | Easy to compare API bills |
| Response latency | Bloated context = slower responses |
| "Works on first try" | Quality gates may require iterations |

**The quality benefits (reduced bugs, consistent architecture) only become apparent after weeks of use** - but developers form opinions in 1-2 hours.

### Competitive Positioning

With progressive disclosure:
> "GuardKit uses progressive disclosure to load only what's needed - core context always, detailed examples on-demand. Lower token usage than BMAD/SpecKit while maintaining comprehensive quality standards."

---

**Report Generated**: 2025-12-03
**Review Duration**: 2.5 hours (including revision)
**Recommendation**: APPROVE - Full implementation with automated splitting
**Total Effort**: 16-18 days
