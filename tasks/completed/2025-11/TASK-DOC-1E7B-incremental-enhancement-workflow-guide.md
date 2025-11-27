---
task_id: TASK-DOC-1E7B
title: Create incremental enhancement workflow guide
status: completed
priority: HIGH
complexity: 4
created: 2025-11-20T21:20:00Z
updated: 2025-11-27T21:15:00Z
completed: 2025-11-27T21:15:00Z
assignee: null
tags: [documentation, phase-8, workflow-guide]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-DOC-F3A3, TASK-DOC-9C4E, TASK-DOC-83F0]
estimated_duration: 3 hours
technologies: [markdown, documentation]
review_source: docs/reviews/phase-8-implementation-review.md
completion_notes: |
  Task completed as part of TASK-DOC-83F0 (Create missing guides).
  File created: docs/workflows/incremental-enhancement-workflow.md
  Size: 808 lines (21KB), 2500+ words
  Last Updated: 2025-11-27
  All acceptance criteria met.
---

# Create Incremental Enhancement Workflow Guide

## Problem Statement

There is no workflow guide explaining how to use Phase 8 incremental enhancement. Users need comprehensive documentation on when and how to enhance agents incrementally.

**Review Finding** (Section 6.3, Documentation Gap #2):
> **Workflow Guide**: No incremental enhancement docs
> **Impact**: Users don't understand workflow options

## Current State

**Missing File**: `docs/workflows/incremental-enhancement-workflow.md`

**Related Documentation Exists**:
- `docs/workflows/taskwright-workflow.md` (general workflow)
- `docs/workflows/template-validation-guide.md` (validation)
- `docs/workflows/design-first-workflow.md` (design-first)

**Gap**: No guide specific to agent enhancement workflow.

## Acceptance Criteria

### 1. Document Structure
- [ ] Overview section explaining purpose
- [ ] When to use incremental enhancement
- [ ] Workflow comparison (automatic vs manual)
- [ ] Step-by-step guide for each workflow
- [ ] Enhancement strategies explained
- [ ] Best practices section
- [ ] Troubleshooting section
- [ ] Examples and use cases

### 2. Content Quality
- [ ] Clear, actionable instructions
- [ ] Code examples with actual commands
- [ ] Decision flowcharts/diagrams
- [ ] Real-world scenarios
- [ ] Common pitfalls documented

### 3. Integration with Existing Docs
- [ ] Cross-references to CLAUDE.md
- [ ] Cross-references to template-create.md
- [ ] Cross-references to agent-enhance.md
- [ ] Links to Phase 8 specification
- [ ] Links to validation guide

### 4. User Journey Coverage
- [ ] First-time template creation
- [ ] Existing template enhancement
- [ ] Batch enhancement scenario
- [ ] Single agent enhancement
- [ ] Quality review and iteration

## Technical Details

### File to Create

**Location**: `docs/workflows/incremental-enhancement-workflow.md`

**Length**: ~2000-2500 words (comprehensive but not overwhelming)

**Format**: Markdown with code blocks, decision trees, examples

### Recommended Content Structure

```markdown
# Incremental Agent Enhancement Workflow

## Overview

Phase 8 of template creation enables **incremental agent enhancement** - the ability to improve agent files over time instead of requiring complete enhancement upfront.

**Problem Solved**: Templates often have 10+ agents. Enhancing all agents at once is:
- Time-consuming (20-30 hours)
- Overwhelming for users
- Not always necessary (some agents more critical than others)

**Solution**: Create stub agents initially, enhance incrementally based on priority and need.

## When to Use Incremental Enhancement

### Use Incremental Enhancement When:

✅ **Large Agent Count** (5+ agents)
- Enhancing all at once is impractical
- Want to spread work over time
- Can prioritize critical agents

✅ **Learning Template Patterns**
- New to template's tech stack
- Want to understand patterns gradually
- Test enhancement quality on subset

✅ **Continuous Improvement**
- Template evolves over time
- New patterns discovered
- User feedback drives enhancement

### Use Full Enhancement When:

❌ **Small Agent Count** (1-3 agents)
- Quick to enhance all at once
- Complete documentation immediately

❌ **Public Template Release**
- Need all agents complete
- Professional quality required
- User-facing documentation

❌ **Team Handoff**
- Template will be used by others
- Consistency required
- No time for incremental work

## Workflow Options

### Option A: Task-Based Enhancement (Recommended)

**Best For**: Teams, tracked work, prioritization

**Workflow**:

1. **Create Template with Task Generation**
   ```bash
   cd ~/my-project
   /template-create --name my-stack-template --create-agent-tasks
   ```

   Output:
   ```
   ✅ Template created: ~/.agentecflow/templates/my-stack-template/
   ✅ Created 8 agent enhancement tasks in tasks/backlog/
   ```

2. **Review Created Tasks**
   ```bash
   /task-status
   ```

   Output:
   ```
   BACKLOG (8 tasks):
   - TASK-API-SERVICE-A1B2C3D4 (HIGH) - Enhance api-service-specialist
   - TASK-DATABASE-A1B2C3D5 (HIGH) - Enhance database-specialist
   - TASK-DOMAIN-MOD-A1B2C3D6 (MEDIUM) - Enhance domain-model-specialist
   - ...
   ```

3. **Work on High-Priority Task**
   ```bash
   /task-work TASK-API-SERVICE-A1B2C3D4
   ```

   Phase 8 will:
   - Load agent file and template
   - Analyze template code
   - Generate enhancement (AI or static)
   - Apply enhancement to agent file
   - Validate enhanced content
   - Move task to IN_REVIEW

4. **Review Enhancement**
   ```bash
   cat ~/.agentecflow/templates/my-stack-template/agents/api-service-specialist.md
   ```

   Check for:
   - Code examples are relevant
   - Best practices are accurate
   - Anti-patterns are correct
   - "Why This Exists" is meaningful

5. **Complete Task**
   ```bash
   /task-complete TASK-API-SERVICE-A1B2C3D4
   ```

6. **Repeat for Other Agents**
   - Work through tasks by priority
   - Enhance critical agents first
   - Optional agents can wait

**Advantages**:
- ✅ Work is tracked in task system
- ✅ Can prioritize agents
- ✅ Progress visible
- ✅ Integrates with existing workflow
- ✅ Can assign to team members

**Disadvantages**:
- ❌ Overhead of task management
- ❌ Not needed for solo work

### Option B: Direct Enhancement

**Best For**: Solo work, quick iteration, no tracking needed

**Workflow**:

1. **Create Template** (without task generation)
   ```bash
   /template-create --name my-stack-template
   ```

2. **Enhance Specific Agent** (dry-run first)
   ```bash
   /agent-enhance ~/.agentecflow/templates/my-stack-template/agents/api-service-specialist.md \
                  ~/.agentecflow/templates/my-stack-template \
                  --dry-run --verbose
   ```

   Review output:
   ```
   Enhancement Preview:
   - Adding 4 code examples
   - Adding 6 best practices
   - Adding 3 anti-patterns
   - Updating "Why This Exists" section

   Changes:
   + ## Code Examples
   + ### Example 1: HTTP Client Configuration
   + ...
   ```

3. **Apply if Satisfied**
   ```bash
   /agent-enhance ~/.agentecflow/templates/my-stack-template/agents/api-service-specialist.md \
                  ~/.agentecflow/templates/my-stack-template
   ```

4. **Repeat for Other Agents**
   ```bash
   /agent-enhance ~/.agentecflow/templates/my-stack-template/agents/database-specialist.md \
                  ~/.agentecflow/templates/my-stack-template
   ```

**Advantages**:
- ✅ Immediate enhancement
- ✅ No task overhead
- ✅ Quick iteration
- ✅ Simple for solo work

**Disadvantages**:
- ❌ No tracking
- ❌ Hard to prioritize with many agents
- ❌ Can't see progress at a glance

## Enhancement Strategies

### AI Strategy

**When to Use**:
- Need comprehensive examples
- Want best practices explained
- Have AI integration setup (TASK-AI-2B37)
- Template code is complex

**How to Use**:
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=ai
```

**What It Does**:
1. Invokes agent-content-enhancer
2. Analyzes template source code
3. Generates examples from code
4. Writes best practices
5. Documents anti-patterns
6. Updates "Why This Exists"

**Pros**:
- ✅ High-quality content
- ✅ Comprehensive examples
- ✅ Context-aware

**Cons**:
- ❌ Requires AI integration
- ❌ Slower (~30-60 seconds)
- ❌ May fail if AI unavailable

### Static Strategy

**When to Use**:
- Offline work (no AI)
- Quick enhancement needed
- Template patterns are simple
- AI integration not available

**How to Use**:
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=static
```

**What It Does**:
1. Loads template source files
2. Extracts code patterns
3. Generates basic examples
4. Adds common best practices
5. Template-based enhancement

**Pros**:
- ✅ Works offline
- ✅ Fast (<1 second)
- ✅ No AI required

**Cons**:
- ❌ Less comprehensive
- ❌ Generic best practices
- ❌ May miss nuanced patterns

### Hybrid Strategy (Default)

**When to Use**:
- Most scenarios
- Want best of both
- Unsure which to use

**How to Use**:
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=hybrid
# or just:
/agent-enhance AGENT_FILE TEMPLATE_DIR
```

**What It Does**:
1. Tries AI strategy first
2. Falls back to static if AI fails
3. Best reliability

**Pros**:
- ✅ Best reliability
- ✅ Uses AI when available
- ✅ Fallback ensures success

**Cons**:
- ❌ None (recommended default)

## Best Practices

### 1. Start with Critical Agents

**Principle**: Enhance high-value agents first

**Implementation**:
```bash
# Review agent priorities
grep "priority:" ~/.agentecflow/templates/my-template/agents/*.md

# Focus on priority >= 9
/task-work TASK-API-SERVICE-ABC123  # priority: 10
/task-work TASK-DATABASE-DEF456     # priority: 9
# ... enhance lower priorities later
```

### 2. Always Dry-Run First

**Principle**: Review before applying

**Implementation**:
```bash
# Preview changes
/agent-enhance AGENT_FILE TEMPLATE_DIR --dry-run --verbose

# Review output carefully

# Apply if satisfied
/agent-enhance AGENT_FILE TEMPLATE_DIR
```

### 3. Validate Enhanced Content

**Principle**: Ensure quality before completion

**Checklist**:
- [ ] Code examples compile/are syntactically correct
- [ ] Best practices are accurate
- [ ] Anti-patterns are real issues
- [ ] "Why This Exists" is meaningful
- [ ] Examples come from template source
- [ ] No placeholder text remains

### 4. Iterate Based on Feedback

**Principle**: Enhancement is continuous

**Process**:
1. Enhance agent initially
2. Use agent in practice
3. Gather feedback
4. Refine enhancement
5. Repeat

### 5. Maintain Consistency

**Principle**: Same quality across all agents

**Implementation**:
- Use same strategy for all agents
- Follow same content structure
- Keep quality bar consistent
- Review existing agents when enhancing new ones

## Troubleshooting

### Issue: AI Enhancement Fails

**Symptom**:
```
ERROR: AI enhancement failed: Connection timeout
Falling back to static enhancement...
```

**Solutions**:
1. Check AI integration (TASK-AI-2B37 complete?)
2. Use static strategy explicitly: `--strategy=static`
3. Use hybrid (auto-fallback): `--strategy=hybrid`

### Issue: No Code Examples Generated

**Symptom**: Agent file has no code blocks after enhancement

**Solutions**:
1. Verify template has `.template` files
2. Check agent technologies match template
3. Use `--verbose` to see discovery process
4. Manual fallback: Add examples yourself

### Issue: Enhancement Quality Low

**Symptom**: Generic best practices, no specific examples

**Solutions**:
1. Try AI strategy if using static
2. Provide better agent metadata (technologies, priority)
3. Ensure template source code is high quality
4. Manual refinement after enhancement

## Examples

### Example 1: Enhancing New Template

```bash
# Step 1: Create template
/template-create --name my-fastapi-template --create-agent-tasks

# Step 2: Check tasks
/task-status
# Output: 5 agent enhancement tasks

# Step 3: Enhance critical agents
/task-work TASK-API-ROUTE-ABC123
/task-work TASK-DATABASE-DEF456

# Step 4: Test in practice
/task-create "Add user authentication"
/task-work TASK-001

# Step 5: Enhance remaining agents later
/task-work TASK-TESTING-GHI789
```

### Example 2: Enhancing Existing Template

```bash
# Scenario: Template created months ago, agents are stubs

# Step 1: Enhance one agent manually
/agent-enhance ~/.agentecflow/templates/old-template/agents/api-specialist.md \
               ~/.agentecflow/templates/old-template

# Step 2: Review quality
cat ~/.agentecflow/templates/old-template/agents/api-specialist.md

# Step 3: If satisfied, enhance others
for agent in ~/.agentecflow/templates/old-template/agents/*.md; do
    /agent-enhance $agent ~/.agentecflow/templates/old-template
done
```

## Next Steps

After completing enhancement:

1. **Validate Template**
   ```bash
   /template-validate ~/.agentecflow/templates/my-template
   ```

2. **Test in Practice**
   ```bash
   taskwright init my-template
   /task-create "Test task"
   /task-work TASK-001
   ```

3. **Iterate**
   - Gather feedback
   - Refine agents based on usage
   - Continuous improvement

## See Also

- [Template Creation Workflow](template-create.md)
- [Template Validation Guide](template-validation-guide.md)
- [Agent Enhance Command](../../../installer/global/commands/agent-enhance.md)
- [Phase 8 Specification](../../../tasks/backlog/TASK-PHASE-8-INCREMENTAL-specification.md)
```

## Success Metrics

### Documentation Quality
- [ ] Workflow clearly explained
- [ ] Decision trees provided
- [ ] Examples are actionable
- [ ] Troubleshooting helpful
- [ ] Best practices documented

### User Success
- [ ] User can choose appropriate workflow
- [ ] User knows which strategy to use
- [ ] User can troubleshoot issues
- [ ] User has concrete examples

### Completeness
- [ ] All workflow options covered
- [ ] All strategies explained
- [ ] Common issues documented
- [ ] Cross-references complete

## Dependencies

**Requires**:
- Understanding of Phase 8 implementation
- agent-enhance command spec (TASK-DOC-4F8A)

**Blocks**:
- TASK-DOC-9C4E (CLAUDE.md update)
- TASK-DOC-F3A3 (documentation suite completion)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 6.3**: Documentation Gap #2 (workflow guide)
- **Section 8**: Recommendations - Short Term #5
- **Section 6.1**: Immediate Priority #5 (documentation)

## Estimated Effort

**Duration**: 3 hours

**Breakdown**:
- Outline structure (20 min)
- Write workflow sections (80 min)
- Add examples (40 min)
- Write best practices (30 min)
- Troubleshooting section (20 min)
- Review and refine (30 min)

## Test Plan

### Content Validation

```python
def test_workflow_guide_exists():
    """Verify workflow guide file exists."""
    guide = Path("docs/workflows/incremental-enhancement-workflow.md")
    assert guide.exists()

def test_workflow_guide_has_required_sections():
    """Verify all required sections present."""
    content = Path("docs/workflows/incremental-enhancement-workflow.md").read_text()

    required_sections = [
        "## Overview",
        "## When to Use",
        "## Workflow Options",
        "## Enhancement Strategies",
        "## Best Practices",
        "## Troubleshooting",
        "## Examples",
    ]

    for section in required_sections:
        assert section in content, f"Missing section: {section}"

def test_workflow_guide_has_code_examples():
    """Verify guide has concrete code examples."""
    content = Path("docs/workflows/incremental-enhancement-workflow.md").read_text()

    assert "```bash" in content
    assert "/agent-enhance" in content
    assert "/task-work" in content
```

## Notes

- **Priority**: HIGH - user documentation critical
- **Effort**: 3 hours for comprehensive guide
- **Dependencies**: Coordinate with TASK-DOC-9C4E and TASK-DOC-4F8A
- **Impact**: Enables user adoption of Phase 8

## Quality Standards

This guide should match the quality of existing workflow docs:
- `docs/workflows/taskwright-workflow.md` (~2000 words)
- `docs/workflows/design-first-workflow.md` (~1500 words)
- Same formatting, same level of detail, same structure
