---
task_id: TASK-ENH-7A2D
title: Populate agent files with code examples and best practices
status: BACKLOG
priority: MEDIUM
complexity: 6
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [enhancement, phase-8, template-quality, documentation, agent-content]
related_tasks: [TASK-PHASE-8-INCREMENTAL]
estimated_duration: 6-9 hours
technologies: [markdown, documentation, csharp, dotnet-maui]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Populate Agent Files with Code Examples and Best Practices

## Problem Statement

All three new agent files created for the net9-maui-mydrive template are skeleton/stub files with minimal content. They lack code examples, best practices, anti-patterns, and meaningful guidance despite excellent source code being available.

**Review Finding** (Section 3, Critical Issue #2):
> **Agent Files Quality**: 3/10
> **What's Missing**: Code examples, best practices, anti-patterns, meaningful "Why This Exists"
> **Impact**: Users won't get useful guidance from agents

## Current State

**Template**: `~/.agentecflow/templates/net9-maui-mydrive/`

**Agent Files** (all are stubs):
1. `agents/maui-api-service-specialist.md`
2. `agents/realm-thread-safety-specialist.md`
3. `agents/domain-validator-specialist.md`

**Current Content Example**:
```markdown
---
name: realm-thread-safety-specialist
description: Specialized agent for realm thread safety specialist
priority: 7
technologies: [csharp, realm-dotnet, maui]
---

# Realm Thread Safety Specialist

## Why This Agent Exists

Specialized agent for realm thread safety specialist

## Technologies

- csharp
- realm-dotnet
- maui
```

**Problems**:
- No code examples from MyDrive source
- Circular "Why This Exists" description
- No best practices section
- No anti-patterns section
- No integration guidance
- Not actionable for users

## Acceptance Criteria

### For Each Agent File

#### 1. Code Examples Section
- [ ] 3-5 code examples from template source code
- [ ] Examples show best practices in action
- [ ] Examples are well-commented
- [ ] Examples cover common use cases
- [ ] Good vs Bad examples where appropriate

#### 2. Best Practices Section
- [ ] 5-8 documented best practices
- [ ] Explain rationale for each practice
- [ ] Include performance considerations
- [ ] Link to relevant documentation
- [ ] Real-world scenarios

#### 3. Anti-Patterns Section
- [ ] 3-5 common mistakes documented
- [ ] Explain why they're problematic
- [ ] Show correct alternatives
- [ ] Include debugging tips
- [ ] Real errors users might encounter

#### 4. "Why This Agent Exists" Section
- [ ] Clear, specific explanation of purpose
- [ ] Specific problems it solves
- [ ] Technologies it specializes in
- [ ] Value it provides to users
- [ ] When to use this agent

#### 5. Integration Guidance
- [ ] How to use agent with /task-work
- [ ] When to invoke this agent
- [ ] Related agents to use with
- [ ] Example workflows

## Technical Details

### Files to Enhance

**1. `agents/realm-thread-safety-specialist.md`**

Source material from MyDrive:
- `LoadingRepository.cs.template` (lines showing thread-safe patterns)
- RealmOperationExecutor usage
- Async/await patterns with ConfigureAwait

**2. `agents/domain-validator-specialist.md`**

Source material from MyDrive:
- Business rule validation examples
- ErrorOr pattern usage
- Validation attribute usage

**3. `agents/maui-api-service-specialist.md`**

Source material from MyDrive:
- HTTP API service patterns
- JWT authentication
- Error handling with ErrorOr

### Recommended Content Structure

Each agent file should follow this structure:

```markdown
---
name: {agent-name}
description: {meaningful-description}
priority: {0-10}
technologies: [...]
---

# {Agent Name}

## Why This Agent Exists

{Clear, specific explanation that addresses:
- What specific problem this solves
- What technologies/patterns it specializes in
- When you should use this agent
- What value it provides}

## Technologies

- {tech1}: {brief note on usage}
- {tech2}: {brief note on usage}

## Code Examples

### Example 1: {Use Case Name}

**Scenario**: {When you need this}

```csharp
// Good: {What this demonstrates}
{code example from template}
```

**Key Points**:
- {Important aspect 1}
- {Important aspect 2}

### Example 2: {Another Use Case}

**Good vs Bad**:

```csharp
// Bad: {Anti-pattern}
{bad code example}

// Good: {Correct pattern}
{good code example from template}
```

**Why This Matters**: {Explanation}

## Best Practices

### 1. {Practice Name}

**What**: {Describe the practice}
**Why**: {Rationale}
**When**: {Use cases}
**How**: {Implementation guidance}

```csharp
{code example}
```

### 2. {Another Practice}

{...}

## Anti-Patterns to Avoid

### ❌ {Anti-Pattern Name}

**Problem**: {What's wrong}
**Symptom**: {Error message or behavior}
**Fix**: {How to correct it}

```csharp
// Don't do this:
{bad code}

// Do this instead:
{good code}
```

## Integration Guidance

### Using with /task-work

```bash
/task-work TASK-XXX  # Invokes this agent for {scenario}
```

### When to Use This Agent

- {Scenario 1}
- {Scenario 2}

### Related Agents

- **{agent-name}**: {When to use together}
- **{agent-name}**: {Complementary usage}

## Performance Considerations

{Performance tips specific to this agent's domain}

## Debugging Tips

{Common issues and how to debug them}

## References

- {Link to relevant documentation}
- {Link to pattern documentation}
```

## Success Metrics

### Content Quality
- [ ] Each agent has 3-5 concrete code examples
- [ ] Examples come from actual template source code
- [ ] "Why This Exists" is specific and meaningful
- [ ] No circular descriptions
- [ ] All sections populated with useful content

### User Value
- [ ] User can learn pattern from agent file alone
- [ ] Examples are copy-paste ready
- [ ] Anti-patterns help avoid common mistakes
- [ ] Integration guidance is actionable

### Completeness
- [ ] All three agents enhanced to same standard
- [ ] No placeholder text remaining
- [ ] No "TODO" markers
- [ ] All code examples compile/are syntactically correct

## Dependencies

**Requires**:
- Access to net9-maui-mydrive template source code
- Understanding of Realm, MAUI, and domain validation patterns

**Related To**:
- TASK-PHASE-8-INCREMENTAL (main implementation)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 3**: Template Output Review - Agent Analysis Quality 6/10
- **Section 3**: New Agent Files Quality 3/10 (Critical)
- **Section 6.1**: Should Fix #5 (2-3 hours per agent)
- **Section 6.3**: Immediate Action Item #4 (agent files are stubs)

## Estimated Effort

**Duration**: 6-9 hours (2-3 hours per agent)

**Breakdown per agent**:
- Extract code examples from source (45 min)
- Write best practices section (45 min)
- Document anti-patterns (30 min)
- Write "Why This Exists" (15 min)
- Add integration guidance (15 min)
- Review and refine (30 min)

**Total**: 3 hours × 3 agents = 9 hours maximum

## Implementation Strategy

### Phase 1: Realm Thread Safety Specialist (3 hours)

**Source Material**:
```bash
grep -r "Realm" ~/.agentecflow/templates/net9-maui-mydrive/*.template
grep -r "RealmOperationExecutor" ~/.agentecflow/templates/net9-maui-mydrive/*.template
```

**Content to Add**:
1. Thread-safe Realm access patterns
2. RealmOperationExecutor usage examples
3. Async/await with ConfigureAwait
4. Common thread-safety errors
5. Debugging Realm thread violations

### Phase 2: Domain Validator Specialist (3 hours)

**Source Material**:
```bash
grep -r "ErrorOr" ~/.agentecflow/templates/net9-maui-mydrive/*.template
grep -r "Validator" ~/.agentecflow/templates/net9-maui-mydrive/*.template
```

**Content to Add**:
1. Business rule validation examples
2. ErrorOr pattern usage
3. Validation attributes
4. Custom validator implementations
5. Validation error handling

### Phase 3: MAUI API Service Specialist (3 hours)

**Source Material**:
```bash
grep -r "HttpClient" ~/.agentecflow/templates/net9-maui-mydrive/*.template
grep -r "JWT" ~/.agentecflow/templates/net9-maui-mydrive/*.template
```

**Content to Add**:
1. HTTP API service patterns
2. JWT authentication flow
3. Error handling with ErrorOr
4. API retry logic
5. Network error scenarios

## Example Enhancement

### Before (Stub - 3/10):
```markdown
## Why This Agent Exists

Specialized agent for realm thread safety specialist
```

### After (Enhanced - 9/10):
```markdown
## Why This Agent Exists

Realm database has strict thread-safety requirements. **RealmObject instances can only be accessed from the thread they were created on.** Violating this causes runtime crashes that are hard to debug.

This agent ensures your Realm code:
- ✅ Uses proper async/await patterns with `ConfigureAwait(false)`
- ✅ Implements thread-safe repository patterns
- ✅ Leverages RealmOperationExecutor for safe cross-thread access
- ✅ Avoids common thread violations that crash apps

**When to Use**:
- Implementing repositories that use Realm
- Writing background tasks that access Realm
- Debugging "Realm accessed from incorrect thread" errors
- Reviewing Realm-related code for thread-safety

**Value Provided**:
- Prevents runtime crashes from thread violations
- Provides tested patterns for thread-safe Realm access
- Reduces debugging time for Realm issues
- Ensures app stability when using Realm
```

## Test Plan

### Quality Validation

For each agent file:

```python
def test_agent_file_has_code_examples():
    """Verify agent has 3+ code examples."""
    agent_content = Path("agents/realm-thread-safety-specialist.md").read_text()

    # Count code blocks
    code_blocks = agent_content.count("```csharp")
    assert code_blocks >= 3, f"Only {code_blocks} code examples found"

def test_agent_has_best_practices():
    """Verify agent has best practices section."""
    agent_content = Path("agents/realm-thread-safety-specialist.md").read_text()

    assert "## Best Practices" in agent_content
    assert "###" in agent_content  # Sub-sections for individual practices

def test_agent_has_anti_patterns():
    """Verify agent has anti-patterns section."""
    agent_content = Path("agents/realm-thread-safety-specialist.md").read_text()

    assert "## Anti-Patterns" in agent_content or "Anti-Patterns to Avoid" in agent_content

def test_why_exists_is_meaningful():
    """Verify 'Why This Exists' is not circular."""
    agent_content = Path("agents/realm-thread-safety-specialist.md").read_text()

    # Extract "Why This Exists" section
    why_section = extract_section(agent_content, "Why This Agent Exists")

    # Should NOT just repeat the agent name
    assert "Specialized agent for realm thread safety specialist" not in why_section
    assert len(why_section) > 200  # Substantial explanation
```

## Notes

- **Priority**: MEDIUM - impacts user experience significantly
- **Effort**: 6-9 hours total (2-3 hours per agent)
- **Impact**: HIGH - users get actual value from agents
- **Risk**: LOW - purely additive content

## Success Criteria Summary

Each agent file scores 8+/10 when evaluated on:
- Code examples (3-5 real examples from template)
- Best practices (5-8 documented practices)
- Anti-patterns (3-5 common mistakes)
- "Why This Exists" (meaningful, specific, actionable)
- Integration guidance (clear usage instructions)
- Overall usefulness to developers
