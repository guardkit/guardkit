# EPIC-001: Agent System Design - Final Summary
## AI-First Creation with Complementary Discovery

**Date**: 2025-11-01
**Status**: ✅ **DESIGN COMPLETE** - All decisions confirmed
**Session**: Comprehensive design review and refinement

---

## Executive Summary

The agent system has been redesigned based on key insight: **Claude Code creates excellent agents** (proven with MAUI, .NET microservices, Python API agents). The design focuses on AI-powered generation as the primary capability, with external discovery as an optional complement.

**Key Achievement**: Simplified from complex algorithmic discovery to elegant AI-first generation.

---

## Confirmed Design Decisions

### ✅ Decision 1: Agent Priority Order

**User Custom > Template > Global > AI-Generated > External**

1. User's custom agents (`.claude/agents/`) - HIGHEST priority ⭐⭐⭐
2. Template agents (template/agents/) - HIGH priority ⭐⭐
3. Global built-in agents (installer/core/agents/) - MEDIUM priority ⭐
4. AI-generated agents (created on-the-fly) - MEDIUM priority ⭐
5. External community agents (optional) - LOW priority ⭐

**Rationale**: User's work always takes precedence. AI fills gaps. External is complementary.

### ✅ Decision 2: External Discovery - Opt-In (Default OFF)

```bash
🌐 Discover community agents? [y/N] _
```

**Implementation**:
- Default: Disabled (no network calls)
- User must explicitly request
- Fast path for most users
- Phase 2 feature (not blocking MVP)

**Rationale**: Doesn't slow down default flow. Power users can opt-in.

### ✅ Decision 3: Generated Agent Reuse - Ask User

```bash
💡 Created: maui-appshell-navigator

   This agent is tailored to your project's patterns.
   Save to .claude/agents/ for reuse in future projects? [y/N] _
```

**Implementation**:
- Default: Agents stay in template (project-specific)
- User can save to `.claude/agents/` for reuse
- Saved agents become "custom" (highest priority)

**Rationale**: User control. Some agents are project-specific, others reusable.

### ✅ Decision 4: Deduplication - Auto-Skip

**When user has custom agent, automatically skip external equivalents**:

```bash
📡 Searching external sources...
  ℹ️  Skipping react-specialist (you have custom version)
  ℹ️  Skipping code-reviewer (using global version)
  ✓ Found react-testing-specialist (new capability)
```

**Implementation**:
- Exact name match: Auto-skip, use user's version
- Similar capability: Auto-skip, notify user
- Unique capability: Suggest as optional

**Rationale**: Respect user's custom agents. Clean UX (no clutter).

---

## 5-Phase Agent Flow

### Phase 1: Inventory (Scan Existing)
```
✓ Scan .claude/agents/ (user's custom)
✓ Scan template/agents/ (if using template)
✓ Scan installer/core/agents/ (built-in)
```

### Phase 2: Analysis (Determine Needs)
```
AI analyzes codebase:
- Language, frameworks, architecture
- Patterns, conventions, layers
- Identifies needed capabilities
```

### Phase 3: Gap Analysis (What's Missing)
```
Compare: Existing vs Needed
✅ Use existing agents
⚠️  Prefer user's custom over generic
❌ Identify gaps to fill
```

### Phase 4: Generation (Fill Gaps)
```
AI generates project-specific agents:
- Based on codebase analysis
- Using actual code examples
- Tailored to project conventions
- Offer to save for reuse
```

### Phase 5: Discovery (Optional, Phase 2)
```
External discovery (opt-in):
- WebFetch + AI extraction
- Show community agents
- User can preview/adopt
- Complementary only
```

---

## Implementation Roadmap

### Phase 1: MVP ✅ APPROVED

**Scope**:
- Multi-source scanning (user, template, global)
- AI-powered agent generation
- Smart deduplication
- Agent reuse prompts
- External discovery DISABLED by default

**Tasks**:
- **TASK-003**: Multi-Source Agent Scanner (8h)
  - Scan .claude/agents/, template/agents/, installer/core/agents/
  - Priority-ordered inventory
  - Duplicate detection
  - **File**: [TASK-003-multi-source-agent-scanner.md](TASK-003-multi-source-agent-scanner.md)

- **TASK-004A**: AI Agent Generator (8h)
  - Capability need identification
  - Gap analysis
  - AI-powered generation from code examples
  - Reuse prompts
  - **File**: [TASK-004A-ai-agent-generator.md](TASK-004A-ai-agent-generator.md)

- **TASK-009**: Agent Orchestration (6h)
  - 5-phase workflow
  - Error handling
  - Progress feedback
  - Convenience functions
  - **File**: [TASK-009-agent-orchestration.md](TASK-009-agent-orchestration.md)

**Total**: 22 hours (agent system only)

**Benefits**:
✅ Leverages Claude Code's proven capability
✅ Fast (no external dependencies)
✅ Context-aware (project-specific)
✅ User-controlled reuse

### Phase 2: Enhancement (Optional)

**Scope**:
- External agent discovery (opt-in)
- WebFetch + AI extraction
- Configurable sources
- Graceful degradation

**Tasks**:
- **TASK-004B**: External Agent Discovery (6h, optional)
  - AI-powered WebFetch extraction
  - Configuration-based sources
  - 24-hour caching
  - **File**: [TASK-004-REDESIGN-ai-agent-discovery.md](TASK-004-REDESIGN-ai-agent-discovery.md)

**Total**: 6 hours

**Priority**: MEDIUM (post-EPIC-001 or optional in EPIC-001)

---

## User Experience

### Example: Template Creation Flow

```bash
$ /template-create "mycompany-maui"

[Q&A Session - 8 questions...]

🔍 Analyzing codebase...
✓ Language: C# / .NET MAUI 8.0
✓ Architecture: MVVM + AppShell
✓ Patterns: ErrorOr, CQRS, Verb-based operations

============================================================
  Agent System
============================================================

📦 Scanning agent sources...
  ✓ Found 3 custom agents in .claude/agents/
    • mycompany-logging-specialist
    • mycompany-security-reviewer
    • mycompany-react-specialist
  ✓ Found 15 global agents

💡 Agent Priority:
  • react-specialist: Using your custom version

📊 Total: 18 agents available

🤖 Determining agent needs...
  ✓ Identified 5 capability needs
  ✓ architectural-reviewer: Using existing (global)
  ✓ code-reviewer: Using existing (global)
  ✓ mvvm-viewmodel-specialist: Covered by existing
  ❌ maui-appshell-navigator: MISSING (will create)
  ❌ errror-pattern-specialist: MISSING (will create)
  ✓ Found 2 gaps to fill

💡 Creating project-specific agents...
  → Generating: maui-appshell-navigator
    [AI analyzes AppShellPage.xaml, ProductListPage.xaml...]
    ✓ Created: maui-appshell-navigator (confidence: 85%)

  → Generating: errror-pattern-specialist
    [AI analyzes GetProducts.cs, ErrorOr usage...]
    ✓ Created: errror-pattern-specialist (confidence: 85%)

💾 Save agents for reuse?

  maui-appshell-navigator:
  This agent is tailored to your project's patterns.
  Save to .claude/agents/ for reuse in future projects? [y/N] y
    ✓ Saved to .claude/agents/maui-appshell-navigator.md

  errror-pattern-specialist:
  This agent is reusable across similar projects.
  Save to .claude/agents/ for reuse in future projects? [y/N] n
    ℹ️  Agent will be included in template only

============================================================
  Agent Setup Complete
============================================================

Total: 20 agents
  • Custom: 3
  • Global: 15
  • Generated: 2

💡 Using your custom agents:
  • mycompany-logging-specialist
  • mycompany-security-reviewer
  • mycompany-react-specialist

✨ Generated project-specific agents:
  • maui-appshell-navigator
  • errror-pattern-specialist

✅ Template created: mycompany-maui
   Location: installer/local/templates/mycompany-maui/
   Agents: 20 total
```

---

## Key Documents Created

### High-Level Design
- **[AGENT-STRATEGY-high-level-design.md](AGENT-STRATEGY-high-level-design.md)** ✅
  - Complete strategy document
  - All 4 decisions confirmed
  - Phase 1 & 2 roadmap
  - **Status**: APPROVED

### Architecture Decisions
- **[ADR-002-agent-discovery-strategy.md](ADR-002-agent-discovery-strategy.md)** ✅
  - WebFetch + AI vs algorithmic scraping
  - Risk assessment (LOW ✅)
  - Graceful degradation strategy
  - **Status**: APPROVED

### Task Specifications
- **[TASK-003-multi-source-agent-scanner.md](TASK-003-multi-source-agent-scanner.md)** ✅
  - 3-source scanning (user, template, global)
  - Priority-ordered inventory
  - 8 hours, Complexity 4/10

- **[TASK-004A-ai-agent-generator.md](TASK-004A-ai-agent-generator.md)** ✅
  - AI-powered generation from code examples
  - Capability gap analysis
  - Reuse prompts
  - 8 hours, Complexity 6/10

- **[TASK-004B-REDESIGN-ai-agent-discovery.md](TASK-004-REDESIGN-ai-agent-discovery.md)** ✅
  - External discovery (Phase 2, optional)
  - WebFetch + AI extraction
  - Configuration-based
  - 6 hours, Complexity 5/10

- **[TASK-009-agent-orchestration.md](TASK-009-agent-orchestration.md)** ✅
  - 5-phase workflow orchestration
  - Error handling
  - Progress feedback
  - 6 hours, Complexity 5/10

---

## Impact on EPIC-001 Timeline

### Original Agent Tasks (Removed)
- Old TASK-004: Configurable Agent Sources (3h) - Replaced

### New Agent Tasks (Phase 1 - MVP)
- TASK-003: Multi-Source Scanner (8h) - NEW (was 6h for single source)
- TASK-004A: AI Agent Generator (8h) - NEW
- TASK-009: Agent Orchestration (6h) - UPDATED (was 4h)

**Total Phase 1**: 22 hours (vs 13 hours original)
**Additional Time**: +9 hours
**Value Add**: AI-powered generation (primary capability), multi-source scanning, reuse prompts

### Phase 2 (Optional)
- TASK-004B: External Discovery (6h) - OPTIONAL

---

## Comparison: Before vs After

| Aspect | Original Design | Final Design | Improvement |
|--------|----------------|--------------|-------------|
| **Approach** | Discovery-focused | Generation-focused | ✅ Aligns with Claude Code capability |
| **Agent Sources** | 1 (global only) | 3 (user, template, global) | ✅ Respects user's work |
| **Primary Capability** | Find existing agents | Create tailored agents | ✅ AI-powered |
| **External Discovery** | Not included | Optional (Phase 2) | ✅ Complementary |
| **Agent Reuse** | Not addressed | User prompted | ✅ User control |
| **Deduplication** | Not addressed | Auto-skip duplicates | ✅ Clean UX |
| **Timeline** | 13 hours | 22 hours (Phase 1) | +9h for AI generation |
| **Risk** | Medium | LOW ✅ | Leverages proven capability |

---

## Benefits Summary

### Phase 1 (MVP) Benefits
✅ **Leverages proven capability**: Claude Code creates excellent agents
✅ **Context-aware**: Learns from actual project code
✅ **Respects user's work**: Custom agents highest priority
✅ **Fast**: No network calls (external discovery disabled)
✅ **User-controlled reuse**: Ask before saving
✅ **Smart deduplication**: Auto-skip duplicates
✅ **No external dependencies**: Works offline

### Phase 2 (Optional) Benefits
✅ **Access to community**: 50+ external agents
✅ **AI-powered extraction**: Not brittle scraping
✅ **User-controlled**: Opt-in, doesn't slow default flow
✅ **Configurable**: User defines sources
✅ **Graceful degradation**: Fallback to local agents

---

## Next Steps

### Immediate (Design Phase Complete)
- ✅ High-level design approved
- ✅ All 4 decisions confirmed
- ✅ Task specifications created
- ✅ ADR documented

### Implementation Phase (Ready to Start)
1. **TASK-003**: Implement multi-source scanner (8h)
2. **TASK-004A**: Implement AI agent generator (8h)
3. **TASK-009**: Implement orchestration (6h)
4. **Integration**: Connect to template creation flow
5. **Testing**: End-to-end validation

### Phase 2 (Optional, Post-MVP)
6. **TASK-004B**: Implement external discovery (6h)
7. **Testing**: External discovery validation

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Multi-source scanning works (user, template, global)
- [ ] AI generates agents from codebase analysis
- [ ] Agents tailored to project conventions
- [ ] User can save agents for reuse
- [ ] Deduplication prevents redundancy
- [ ] Integration with template creation works
- [ ] End-to-end tests pass

### Phase 2 Complete When:
- [ ] External discovery opt-in works
- [ ] WebFetch + AI extraction functional
- [ ] Configuration-based sources work
- [ ] Graceful degradation to local agents
- [ ] User can preview/adopt external agents

---

## Acknowledgments

**Key Insight** (User): "Claude Code should probably be able to create good definitions anyway - it did for my original subagents for maui and .net microservices, python api's etc."

**Design Evolution**:
1. Started with algorithmic discovery (complex, brittle)
2. Pivoted to AI-powered WebFetch (better than scraping)
3. Zoomed out to realize AI generation is primary capability
4. External discovery became complementary, not primary
5. Multi-source scanning to respect user's custom work

**Result**: Elegant AI-first design that leverages Claude Code's proven strengths.

---

## Status

**Design**: ✅ COMPLETE (2025-11-01)
**Decisions**: ✅ ALL CONFIRMED (4/4)
**Tasks**: ✅ ALL SPECIFIED (3 tasks)
**Implementation**: 🚀 READY TO START

---

**Created**: 2025-11-01
**Status**: ✅ **DESIGN COMPLETE** - Ready for implementation
**Phase 1 Timeline**: 22 hours (3 tasks)
**Phase 2 Timeline**: 6 hours (1 task, optional)
