# Progressive Disclosure Analysis for Stack Templates

**Date**: December 2025  
**Status**: Analysis Complete  
**Recommendation**: Implement progressive disclosure for CLAUDE.md and large agent files  
**Priority**: HIGH - Implement before public launch

## Executive Summary

This document analyzes the opportunity to implement progressive disclosure in GuardKit's stack templates to reduce context window usage while maintaining quality. Unlike Claude Skills (which are inappropriate for mandatory workflows), progressive disclosure allows explicit control over what content loads and when, preserving GuardKit's deterministic execution model.

**Critical Timing**: Implementing before public launch avoids all migration complexity and positions GuardKit favorably in developer evaluations.

## Why This Matters for Launch

### The Developer Evaluation Problem

When developers evaluate frameworks like AgentOS, BMAD, SpecKit, or GuardKit, they tend to measure what's **easy to quantify**:

| What Developers Measure | What Actually Matters |
|------------------------|----------------------|
| ⏱️ Time to first output | Code quality over time |
| 📊 Tokens consumed | Architectural consistency |
| 🔢 Number of commands | Reduction in rework/bugs |
| 📁 Lines of code generated | Maintainability |
| ✅ "It works" on first try | Test coverage quality |

**The irony**: GuardKit's entire value proposition is quality gates, human checkpoints, and enforcement of standards - but those benefits only become apparent after weeks of use, not in a 30-minute evaluation.

### First Impressions Matter Disproportionately

A developer evaluating frameworks will likely:

1. Clone repo, run installer
2. Try `/template-create` on a sample project
3. Run `/task-work` on one feature
4. **Form opinion within 1-2 hours**

If during that window they see:
- "Loading 45,000 tokens of context..."
- Slow response times from bloated prompts
- High API costs in their billing

They'll move on to the next framework before experiencing the actual quality benefits.

### Positioning Opportunity

Progressive disclosure can be positioned as a feature:

> *"GuardKit uses progressive disclosure to load only what's needed - core context always, detailed examples on-demand. This keeps token usage efficient while maintaining comprehensive quality standards."*

This positions the optimization as intentional design, not just an implementation detail.

## Current State Analysis

### File Sizes in react-typescript Template

| File Type | Example | Size | Token Estimate |
|-----------|---------|------|----------------|
| **CLAUDE.md** | react-typescript | 20KB | ~5,000 tokens |
| **Stack Agent** | react-query-specialist.md | 16KB | ~4,000 tokens |
| **Global Agent** | architectural-reviewer.md | 44KB | ~11,000 tokens |
| **Template** | get-entities.ts.template | ~2KB | ~500 tokens |

### Potential Context Load Per Task

If a task requires CLAUDE.md + 3 stack agents + 2 global agents:
- **Total**: ~45,000 tokens just for reference material
- This is before any code, task descriptions, or conversation history

### Content Analysis: What's Always Needed vs. Reference-Only

#### CLAUDE.md Structure

```
Current CLAUDE.md (~20KB, ~5,000 tokens)
├── Project Context (200 lines)           ✓ Always needed
├── Core Principles (50 lines)            ✓ Always needed
├── Architecture Overview (100 lines)     ✓ Always needed
├── Technology Stack (100 lines)          ✓ Useful for decisions
├── Project Structure (80 lines)          ✓ Always needed
├── Naming Conventions (100 lines)        ◐ Needed during implementation
├── Patterns and Best Practices (300 lines) ◐ Needed per-pattern
├── Code Examples (200 lines)             ○ Only specific features
├── Quality Standards (50 lines)          ✓ Always needed
├── Testing Strategy (150 lines)          ◐ Needed during test phase
├── Development Workflow (100 lines)      ○ Reference only
├── Common Tasks (100 lines)              ○ Reference only
├── Troubleshooting (100 lines)           ○ Only when debugging
```

**Finding**: ~40% of CLAUDE.md is reference material not needed for every task.

#### Agent File Structure

```
Current Agent File (~16KB, ~4,000 tokens)
├── YAML Frontmatter (discovery)          ✓ Always needed
├── Role Description (20 lines)           ✓ Always needed
├── Responsibilities (50 lines)           ✓ Always needed
├── Code Patterns (100 lines)             ◐ Needed during active work
├── Best Practices (50 lines)             ◐ Needed during active work
├── Anti-Patterns (100 lines)             ○ Reference for quality
├── Related Templates (200 lines)         ○ Only when generating code
├── Template Code Examples (300 lines)    ○ Only when generating code
├── Template Best Practices (100 lines)   ○ Only when generating code
├── Template Anti-Patterns (100 lines)    ○ Only when generating code
```

**Finding**: ~60% of agent files are "Related Templates" sections with detailed examples.

## Proposed Solution: Progressive Disclosure via File Splitting

### Principle

Split files into:
1. **Core content**: Always loaded, essential for task execution
2. **Extended content**: Loaded on-demand via explicit instructions

### CLAUDE.md Split

**Before**: Single 20KB file

**After**:

```
templates/react-typescript/
├── CLAUDE.md                              # Core (~8KB)
│   ├── Project Context
│   ├── Core Principles
│   ├── Architecture Overview
│   ├── Project Structure
│   ├── Naming Conventions
│   └── Quality Standards
│
└── docs/
    ├── patterns/                          # On-demand
    │   ├── react-query-patterns.md
    │   ├── form-validation-patterns.md
    │   ├── component-patterns.md
    │   └── testing-patterns.md
    │
    └── reference/                         # On-demand
        ├── troubleshooting.md
        ├── development-workflow.md
        └── common-tasks.md
```

**CLAUDE.md would include explicit loading instructions**:

```markdown
## Pattern References

When implementing specific patterns, load the relevant guide:

- **Data fetching**: `cat docs/patterns/react-query-patterns.md`
- **Forms**: `cat docs/patterns/form-validation-patterns.md`
- **Components**: `cat docs/patterns/component-patterns.md`
- **Testing**: `cat docs/patterns/testing-patterns.md`

## Troubleshooting

If encountering issues: `cat docs/reference/troubleshooting.md`
```

### Agent File Split

**Before**: Single 16KB file (e.g., react-query-specialist.md)

**After**:

```
agents/
├── react-query-specialist.md              # Core (~6KB)
│   ├── YAML frontmatter (full)
│   ├── Role and expertise
│   ├── Responsibilities
│   ├── Code patterns (essential only)
│   ├── Best practices (condensed)
│   └── Loading instruction for extended content
│
└── react-query-specialist-ext.md          # Extended (~10KB)
    ├── Detailed template code examples
    ├── DO/DON'T patterns with full code
    ├── Template best practices
    ├── Template anti-patterns
    └── Cross-stack considerations
```

**Agent would include explicit loading instruction**:

```markdown
## 📚 Extended Reference (Load Before Code Generation)

**Template examples and anti-patterns**: 
```bash
cat agents/react-query-specialist-ext.md
```

Load this file before generating code from templates to ensure pattern compliance.
```

## Implementation Options

### Option A: Explicit `cat` Instructions (Recommended)

Add explicit loading instructions to core files:

```markdown
## Extended Reference

Before generating React Query code, load template examples:
```bash
cat docs/agents/react-query-templates.md
```
```

**Pros**:
- Simple implementation
- No tooling changes required
- Works immediately
- Self-documenting

**Cons**:
- Relies on Claude following instructions
- No enforcement mechanism

### Option B: Structured References in Frontmatter

Add `extended_context` to YAML frontmatter:

```yaml
---
name: react-query-specialist
description: TanStack Query specialist

extended_context:
  - path: agents/react-query-specialist-ext.md
    load_when: "generating code from templates"
  - path: docs/patterns/caching-strategies.md  
    load_when: "implementing cache invalidation"
---
```

**Pros**:
- Structured and parseable
- Could be enforced by tooling
- Clear contract

**Cons**:
- Requires command changes to interpret
- Additional complexity

### Option C: Section Headers with Visual Indicators

Use standardized section headers:

```markdown
## 📚 Extended Reference (Load Before Code Generation)

**Template examples**: `agents/react-query-specialist-ext.md`

Load this file before generating any code to ensure pattern compliance.
```

**Pros**:
- Self-documenting
- Visual indicator (📚) aids scanning
- No tooling changes
- Clear purpose statement

**Cons**:
- Still relies on Claude following instructions

### Recommendation: Combination of A and C

Use explicit `cat` instructions with visual section headers for clarity.

## Expected Token Savings

### Scenario Analysis

| Scenario | Current | With Progressive Disclosure | Savings |
|----------|---------|----------------------------|---------|
| Simple task (no templates) | ~45K tokens | ~20K tokens | 56% |
| Standard task | ~45K tokens | ~30K tokens | 33% |
| Complex task with templates | ~45K tokens | ~35K tokens | 22% |
| Debugging session | ~45K tokens | ~25K tokens | 44% |

### Per-File Savings

| File | Current | Core Only | Reduction |
|------|---------|-----------|-----------|
| CLAUDE.md | 20KB | 8KB | 60% |
| react-query-specialist.md | 16KB | 6KB | 63% |
| architectural-reviewer.md | 44KB | 18KB | 59% |

## Proposed File Structure After Refactoring

```
templates/react-typescript/
├── CLAUDE.md                              # Core context (8KB)
├── README.md                              # Unchanged
├── manifest.json                          # Unchanged
├── settings.json                          # Unchanged
│
├── agents/
│   ├── react-query-specialist.md          # Core (6KB)
│   ├── react-query-specialist-ext.md      # Extended (10KB)
│   ├── feature-architecture-specialist.md # Core (5KB)
│   ├── feature-architecture-ext.md        # Extended (8KB)
│   ├── form-validation-specialist.md      # Core (5KB)
│   └── form-validation-ext.md             # Extended (7KB)
│
├── docs/
│   ├── patterns/
│   │   ├── react-query-patterns.md        # Extracted from CLAUDE.md
│   │   ├── form-patterns.md               # Extracted from CLAUDE.md
│   │   ├── component-patterns.md          # Extracted from CLAUDE.md
│   │   └── testing-patterns.md            # Extracted from CLAUDE.md
│   │
│   └── reference/
│       ├── troubleshooting.md             # Extracted from CLAUDE.md
│       ├── development-workflow.md        # Extracted from CLAUDE.md
│       └── common-tasks.md                # Extracted from CLAUDE.md
│
└── templates/                             # Unchanged
    ├── api/
    ├── components/
    ├── mocks/
    └── routes/
```

## Implementation Plan

### Phase 1: CLAUDE.md Split (Low Risk)

1. Identify sections that are reference-only
2. Extract to `docs/patterns/` and `docs/reference/`
3. Add loading instructions to CLAUDE.md
4. Test with sample tasks
5. Verify no quality degradation

### Phase 2: Large Agent Split (Medium Risk)

1. Identify agents over 10KB
2. Split into core + extended
3. Ensure core contains all decision-making context
4. Extended contains examples and anti-patterns
5. Add loading instructions
6. Test with implementation tasks

### Phase 3: Apply to Other Templates

1. Apply same pattern to `fastapi-python`
2. Apply to `nextjs-fullstack`
3. Apply to `react-fastapi-monorepo`
4. Validate consistency across templates

## Quality Assurance

### What Must NOT Change

- Agent discovery via YAML frontmatter
- Core responsibilities and expertise definitions
- Essential code patterns for decision-making
- Quality gate execution (deterministic, not affected by file splitting)

### What Can Be Deferred

- Detailed template code examples
- Full DO/DON'T pattern lists
- Troubleshooting guides
- Development workflow documentation

### Verification Checklist

- [ ] Core files contain all decision-making context
- [ ] Extended files are truly reference-only
- [ ] Loading instructions are clear and explicit
- [ ] No quality degradation in generated code
- [ ] Agent discovery still works correctly
- [ ] Haiku agents still produce correct output with core files

## Comparison with Claude Skills

| Aspect | Progressive Disclosure | Claude Skills |
|--------|----------------------|---------------|
| **Control** | Explicit (developer controls loading) | Implicit (Claude decides) |
| **Determinism** | Deterministic | Heuristic-based |
| **Quality Gates** | Unaffected | Would compromise |
| **Implementation** | File splitting + instructions | New architecture |
| **Risk** | Low | High for mandatory workflows |

## Conclusion

Progressive disclosure via file splitting offers significant token savings (30-60%) without compromising GuardKit's deterministic execution model. Unlike Claude Skills, this approach:

1. Maintains explicit control over content loading
2. Preserves mandatory quality gate execution
3. Requires no architectural changes
4. Can be implemented incrementally

### Why Implement Before Launch

Implementing before public launch provides significant advantages:

1. **No migration burden** - Users start with optimized structure from day one
2. **Better first impressions** - Lower token usage during initial evaluation
3. **Competitive positioning** - Can highlight efficiency as a feature
4. **Cleaner codebase** - No backward compatibility code or dual-format support

### Recommended Next Steps

1. **Prototype**: Split one agent file (e.g., `react-query-specialist.md`) as proof of concept
2. **Test**: Verify code generation quality with split files
3. **Document**: Create guidelines for splitting other agents
4. **Roll out**: Apply to all templates systematically
5. **Launch**: Ship with optimized architecture from day one

### Files to Create as Prototypes

1. `agents/react-query-specialist.md` (core, ~6KB)
2. `agents/react-query-specialist-ext.md` (extended, ~10KB)
3. `CLAUDE.md` (slimmed, ~8KB)
4. `docs/patterns/react-query-patterns.md` (extracted)

This approach provides the token efficiency benefits without the execution model risks of Claude Skills.
