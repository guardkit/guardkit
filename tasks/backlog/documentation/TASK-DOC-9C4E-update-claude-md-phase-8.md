---
task_id: TASK-DOC-9C4E
title: Update CLAUDE.md with Phase 8 incremental enhancement workflow
status: BACKLOG
priority: HIGH
complexity: 3
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [documentation, phase-8, user-guide, claude-md]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-DOC-F3A3, TASK-DOC-1E7B]
estimated_duration: 2 hours
technologies: [markdown, documentation]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Update CLAUDE.md with Phase 8 Incremental Enhancement Workflow

## Problem Statement (UPDATED 2025-11-23)

**STATUS**: PARTIALLY COMPLETE

CLAUDE.md **DOES mention** the `/agent-enhance` command (line 526+) and agent boundary sections (lines 524-620), BUT is missing:
- `/agent-format` command documentation
- `/agent-validate` command documentation
- Complete Phase 8 incremental enhancement workflow
- Task-based vs direct enhancement comparison

**Review Finding** (Section 6.3, Documentation Gap #1):
> **CLAUDE.md**: ~~No `/agent-enhance` command mentioned~~ NOW DOCUMENTED (2025-11-22)
> **Impact**: ~~Users don't know feature exists or how to use it~~ PARTIALLY ADDRESSED

**Current Coverage in CLAUDE.md**:
- ✅ Agent Enhancement with Boundary Sections (lines 524-620, 97 lines)
- ✅ `/agent-enhance` basic mention
- ✅ ALWAYS/NEVER/ASK framework explained
- ✅ Examples for Testing Agent and Repository Agent
- ❌ `/agent-format` not in Essential Commands
- ❌ `/agent-validate` not in Essential Commands
- ❌ Phase 8 workflow incomplete
- ❌ Enhancement strategies not fully documented

## Current State

**File**: `CLAUDE.md` (project root)

**Missing Sections**:
- No `/agent-enhance` command in command list
- No explanation of incremental enhancement workflow
- No Phase 8 in workflow documentation
- No agent enhancement best practices

**Related Missing Documentation**:
- No `docs/workflows/incremental-enhancement-workflow.md`
- No `installer/global/commands/agent-enhance.md`

## Acceptance Criteria

### 1. Command Documentation in CLAUDE.md
- [ ] Add `/agent-enhance` to "Essential Commands" section
- [ ] Include command syntax
- [ ] Include common usage examples
- [ ] Include flags (--strategy, --dry-run, --verbose)
- [ ] Cross-reference to detailed workflow guide

### 2. Workflow Integration
- [ ] Add "Incremental Enhancement Workflow" section
- [ ] Explain when to use vs `/template-create`
- [ ] Show relationship to Phase 8
- [ ] Explain manual vs automatic enhancement

### 3. Agent Enhancement Best Practices
- [ ] When to enhance agents (timing)
- [ ] Which strategy to use (ai/static/hybrid)
- [ ] How to review enhancements
- [ ] Quality standards for agent content

### 4. Examples and Use Cases
- [ ] Enhancing single agent
- [ ] Enhancing all agents in template
- [ ] Using with task workflow
- [ ] Dry-run before applying

### 5. Cross-References
- [ ] Link to incremental-enhancement-workflow.md
- [ ] Link to agent-enhance.md command spec
- [ ] Link to Phase 8 specification
- [ ] Link to template validation guide

## Technical Details

### Files to Modify

**1. `CLAUDE.md`** (project root)

Add sections:
- Essential Commands (update)
- Incremental Enhancement Workflow (new)
- Agent Enhancement Best Practices (new)

### Recommended Content

#### Section 1: Essential Commands Update

```markdown
## Essential Commands

### Core Workflow
```bash
/task-create "Title" [priority:high|medium|low]
/task-work TASK-XXX [--mode=standard|tdd]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX
```

### Template Creation
```bash
/template-create [--name NAME] [--validate] [--create-agent-tasks]
/template-validate TEMPLATE_PATH
```

### Agent Enhancement (NEW)
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR [--strategy=ai|static|hybrid] [--dry-run]
```

**See**: [Incremental Enhancement Workflow](docs/workflows/incremental-enhancement-workflow.md)
```

#### Section 2: Template Workflow Phases (Update)

```markdown
## Template Creation Workflow Phases

The `/template-create` command executes these phases automatically:

```
Phase 1: Source Analysis
Phase 2: File Discovery
Phase 3: Manifest Generation
Phase 4: Settings Extraction
Phase 5: CLAUDE.md Generation
Phase 6: Agent Discovery
Phase 7: Validation
Phase 8: Agent Task Creation [OPTIONAL]
  ├─ Creates one task per agent file
  ├─ Task metadata includes agent_file, template_dir, template_name
  ├─ Tasks can be enhanced incrementally using /task-work
  └─ Alternative: Manual enhancement with /agent-enhance
```

**Phase 8 Options**:
1. **Automatic** (with `--create-agent-tasks`): Creates tasks, enhance later
2. **Manual** (without flag): Use `/agent-enhance` directly per agent
```

#### Section 3: Incremental Enhancement Workflow (New)

```markdown
## Incremental Enhancement Workflow

Phase 8 enables **incremental agent enhancement** - you can improve agent files over time instead of all at once.

### When to Use

**Use Incremental Enhancement**:
- Template has 5+ agents (too many to enhance at once)
- Want to prioritize critical agents first
- Learning template patterns gradually
- Testing enhancement quality on small subset

**Use Full Enhancement** (during template creation):
- Template has 1-3 agents (quick to enhance)
- Need all agents complete immediately
- One-time template creation

### Workflow Options

#### Option A: Task-Based (Recommended)

```bash
# 1. Create template with agent tasks
/template-create --name my-template --create-agent-tasks

# 2. Review created tasks
/task-status

# Output:
# BACKLOG:
#   TASK-AGENT-API-ABC123 - Enhance api-service-specialist
#   TASK-AGENT-DATABASE-DEF456 - Enhance database-specialist
#   ...

# 3. Work on high-priority agents first
/task-work TASK-AGENT-API-ABC123

# 4. Complete when satisfied
/task-complete TASK-AGENT-API-ABC123

# 5. Repeat for other agents as needed
```

**Benefits**:
- Tracked in task system
- Can prioritize enhancement work
- Integrated with /task-work workflow
- Progress visible

#### Option B: Direct Enhancement

```bash
# 1. Create template (without --create-agent-tasks)
/template-create --name my-template

# 2. Enhance specific agent
/agent-enhance ~/.agentecflow/templates/my-template/agents/api-service-specialist.md \
               ~/.agentecflow/templates/my-template

# 3. Review changes (dry-run first)
/agent-enhance ~/.agentecflow/templates/my-template/agents/api-service-specialist.md \
               ~/.agentecflow/templates/my-template \
               --dry-run

# 4. Apply if satisfied
/agent-enhance ~/.agentecflow/templates/my-template/agents/api-service-specialist.md \
               ~/.agentecflow/templates/my-template
```

**Benefits**:
- Immediate enhancement
- No task overhead
- Quick iteration

### Enhancement Strategies

#### AI Strategy (Recommended)
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=ai
```
- Uses agent-content-enhancer
- Analyzes template code
- Generates examples and best practices
- **Requires**: AI integration (TASK-AI-2B37)

#### Static Strategy (Fallback)
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=static
```
- Uses template-based enhancement
- Extracts patterns from source
- No AI required
- Good for offline use

#### Hybrid Strategy (Default)
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=hybrid
```
- Tries AI first
- Falls back to static if AI fails
- Best reliability
- Recommended for most users

### Best Practices

1. **Start with Critical Agents**
   - Enhance high-priority agents first (priority >= 9)
   - Use task system to track priorities

2. **Review Before Applying**
   - Always use `--dry-run` first
   - Review generated content
   - Validate examples compile

3. **Iterate on Quality**
   - Enhance incrementally
   - Test agent guidance in practice
   - Refine based on user feedback

4. **Maintain Consistency**
   - Use same strategy across agents
   - Follow same content structure
   - Keep quality bar consistent

**See Also**:
- [Incremental Enhancement Workflow](docs/workflows/incremental-enhancement-workflow.md)
- [Agent Enhance Command](installer/global/commands/agent-enhance.md)
- [Phase 8 Specification](tasks/backlog/TASK-PHASE-8-INCREMENTAL-specification.md)
```

#### Section 4: Quality Standards (Add to existing section)

```markdown
## Template Quality Standards

### Agent Content Quality

**Minimum Standards** (enforced by validation):
- Valid frontmatter with required fields
- Technologies list populated
- Priority set (0-10 scale)

**Production Standards** (incremental enhancement goal):
- 3-5 code examples from template source
- Best practices section (5-8 practices)
- Anti-patterns section (3-5 common mistakes)
- Meaningful "Why This Agent Exists" (not circular)
- Integration guidance with usage examples

**Enhancement Path**:
1. Template creation: Generates stub agents (minimum standards)
2. Phase 8: Creates enhancement tasks (if --create-agent-tasks)
3. Incremental work: Enhance agents to production standards
4. Validation: Verify quality with /template-validate

**See**: [Agent Enhancement Task Template](tasks/backlog/TASK-*-enhance-*.md)
```

## Success Metrics

### Documentation Completeness
- [ ] `/agent-enhance` command documented
- [ ] Phase 8 workflow explained
- [ ] Enhancement strategies documented
- [ ] Best practices provided
- [ ] Examples included

### User Clarity
- [ ] User knows when to use incremental enhancement
- [ ] User knows difference between task-based vs direct
- [ ] User knows which strategy to choose
- [ ] User has actionable examples

### Cross-References
- [ ] Links to detailed workflow guide
- [ ] Links to command spec
- [ ] Links to related tasks
- [ ] Links to Phase 8 spec

## Dependencies

**Requires**:
- TASK-DOC-1E7B (incremental enhancement workflow guide)
- TASK-DOC-4F8A (agent-enhance command spec)

**Blocks**:
- User adoption of Phase 8 features
- TASK-DOC-F3A3 (documentation suite completion)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 6.3**: Documentation Gap #1 (CLAUDE.md)
- **Section 6.1**: Immediate Action Item (documentation)
- **Section 8**: Recommendations - Short Term #5

## Estimated Effort

**Duration**: 2 hours

**Breakdown**:
- Update Essential Commands (15 min)
- Add workflow sections (45 min)
- Add best practices (30 min)
- Add examples (20 min)
- Cross-references and review (10 min)

## Test Plan

### Content Validation

```python
def test_claude_md_has_agent_enhance():
    """Verify CLAUDE.md documents /agent-enhance."""
    content = Path("CLAUDE.md").read_text()

    assert "/agent-enhance" in content
    assert "AGENT_FILE" in content  # Syntax documented
    assert "TEMPLATE_DIR" in content

def test_claude_md_has_phase_8():
    """Verify CLAUDE.md explains Phase 8."""
    content = Path("CLAUDE.md").read_text()

    assert "Phase 8" in content or "phase 8" in content
    assert "incremental" in content.lower()

def test_claude_md_has_strategies():
    """Verify strategies are documented."""
    content = Path("CLAUDE.md").read_text()

    assert "ai" in content
    assert "static" in content
    assert "hybrid" in content

def test_claude_md_has_cross_references():
    """Verify links to other docs."""
    content = Path("CLAUDE.md").read_text()

    assert "incremental-enhancement-workflow.md" in content
    assert "agent-enhance.md" in content
```

## Notes

- **Priority**: HIGH - user documentation critical
- **Dependencies**: Requires workflow guide and command spec
- **Impact**: Enables user adoption of Phase 8 features
- **Risk**: LOW - documentation only

## Coordination

This task should be coordinated with:
- TASK-DOC-1E7B (workflow guide)
- TASK-DOC-4F8A (command spec)
- TASK-DOC-F3A3 (documentation suite)

All three should be completed together for consistency.
