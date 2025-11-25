# Agent Discovery Metadata Schema

**Version**: 1.0
**Status**: Active
**Created**: 2025-11-25
**Purpose**: Enable AI-powered agent selection for Phase 3 implementation tasks

## Table of Contents

- [Overview](#overview)
- [Design Principles](#design-principles)
- [Schema Fields](#schema-fields)
  - [Stack](#stack)
  - [Phase](#phase)
  - [Capabilities](#capabilities)
  - [Keywords](#keywords)
- [Validation Rules](#validation-rules)
- [Complete Examples](#complete-examples)
- [Migration Guide](#migration-guide)
- [FAQ](#faq)

## Overview

The Agent Discovery Metadata Schema enables AI-powered agent selection during Phase 3 implementation tasks. By adding structured metadata to agent frontmatter, the system can automatically match tasks to the most appropriate specialized agents based on technology stack, workflow phase, capabilities, and semantic keywords.

### Key Benefits

- **Automatic Agent Selection**: AI selects best agent based on task requirements
- **Zero Hardcoding**: No manual agent mappings needed
- **Graceful Degradation**: Agents without metadata still work via manual invocation
- **Backward Compatible**: Zero impact to existing 15+ agents
- **Future-Proof**: Extensible to new stacks and phases

### Opt-In Design

Discovery metadata is **completely optional**:
- ✅ Agents WITH metadata → Discoverable for phase-specific automatic selection
- ✅ Agents WITHOUT metadata → Continue working via manual invocation
- ✅ No breaking changes → Existing agents unaffected

## Design Principles

1. **Opt-In Discovery**: Only agents with metadata participate in automatic selection
2. **Backward Compatible**: Agents without metadata continue working normally
3. **Graceful Degradation**: Missing optional fields don't cause errors
4. **AI-Friendly**: Keywords enable semantic matching beyond exact stack names
5. **Future-Proof**: Extensible enum values without breaking changes

## Schema Fields

### Stack

**Type**: `array of strings`
**Required**: Yes (for discovery)
**Min Items**: 1
**Allowed Values**: `python`, `react`, `dotnet`, `typescript`, `javascript`, `go`, `rust`, `java`, `ruby`, `php`, `cross-stack`

#### Description

Specifies which technology stacks the agent supports. Use specific stack names for technology-specific agents, or `[cross-stack]` for agents that work across all technologies.

#### Examples

```yaml
# Python-specific agent
stack: [python]

# React + TypeScript agent
stack: [react, typescript]

# .NET-specific agent
stack: [dotnet]

# Cross-stack agent (works with all technologies)
stack: [cross-stack]
```

#### Validation Rules

- Must be non-empty array
- All values must be from allowed values list
- `cross-stack` cannot be combined with specific stack names
- Use specific stacks when agent has technology-specific knowledge
- Use `cross-stack` only for truly stack-agnostic agents (e.g., git-workflow-manager)

#### When to Use cross-stack

Use `[cross-stack]` for agents that:
- Have no technology-specific logic
- Work identically across all languages/frameworks
- Examples: git-workflow-manager, build-validator, security-specialist

**Do NOT use** `[cross-stack]` for:
- Agents with technology-specific patterns (use specific stack)
- Agents that "could" work with multiple stacks but have preferred patterns
- Agents with stack-specific validation or tooling

---

### Phase

**Type**: `string` (single value, not array)
**Required**: Yes (for discovery)
**Allowed Values**: `implementation`, `review`, `testing`, `orchestration`

#### Description

Identifies the primary workflow phase where the agent operates. Each agent has ONE primary phase representing where it provides the most value.

#### Phase Definitions

| Phase | Description | Example Agents |
|-------|-------------|----------------|
| `implementation` | Phase 3: Code generation and implementation | API specialists, domain specialists, UI specialists |
| `review` | Phase 5: Code review and quality assessment | code-reviewer, architectural-reviewer |
| `testing` | Phase 4: Test execution and verification | test-verifier, test-orchestrator |
| `orchestration` | Phase coordination and workflow management | task-manager, workflow coordinators |

#### Examples

```yaml
# Implementation phase agent
phase: implementation

# Review phase agent
phase: review

# Testing phase agent
phase: testing

# Orchestration phase agent
phase: orchestration
```

#### Validation Rules

- Must be single string value (NOT an array)
- Must be one of the four allowed values
- Choose the PRIMARY phase where agent provides most value
- If agent spans multiple phases, choose most prominent

#### Choosing the Right Phase

**Use `implementation`** when agent:
- Generates production code
- Creates new features/functionality
- Implements business logic
- Examples: python-api-specialist, react-state-specialist, dotnet-domain-specialist

**Use `review`** when agent:
- Analyzes code quality
- Checks architectural compliance
- Provides improvement recommendations
- Examples: code-reviewer, architectural-reviewer

**Use `testing`** when agent:
- Executes tests
- Validates coverage
- Verifies quality gates
- Examples: test-verifier, test-orchestrator

**Use `orchestration`** when agent:
- Coordinates workflow phases
- Manages task state transitions
- Orchestrates other agents
- Examples: task-manager

---

### Capabilities

**Type**: `array of strings`
**Required**: Yes (for discovery)
**Min Items**: 1
**Max Items**: 10 (recommended)
**Format**: Descriptive phrases (2-5 words)

#### Description

Lists specific technical capabilities and patterns the agent implements. Capabilities should be concrete, descriptive phrases that clearly communicate what the agent can do.

#### Examples

```yaml
# Python API Specialist
capabilities:
  - FastAPI endpoint implementation
  - Async request handling
  - Dependency injection patterns
  - Pydantic schema integration

# React State Specialist
capabilities:
  - React hooks implementation
  - State management patterns
  - TanStack Query integration
  - Component composition

# .NET Domain Specialist
capabilities:
  - Domain entity modeling
  - Value object patterns
  - Repository pattern implementation
  - Entity validation logic
```

#### Validation Rules

- Must have 1-10 items (keep focused)
- Each item should be a descriptive phrase (2-5 words)
- Avoid single-word entries (too generic)
- Avoid generic terms like "coding", "development", "programming"
- Focus on specific technical capabilities and patterns

#### Writing Good Capabilities

✅ **Good Examples** (Specific and concrete):
- "FastAPI endpoint implementation"
- "React hooks implementation"
- "Repository pattern implementation"
- "JWT token validation"
- "Entity relationship mapping"

❌ **Bad Examples** (Too generic or vague):
- "Coding"
- "API"
- "Development"
- "Best practices"
- "Quality code"

#### How Many Capabilities?

- **1-3 capabilities**: Highly specialized agent (e.g., single framework feature)
- **4-7 capabilities**: Typical specialist agent (e.g., API layer, domain layer)
- **8-10 capabilities**: Broad specialist (reaching upper limit)
- **10+ capabilities**: Consider splitting into multiple agents

---

### Keywords

**Type**: `array of strings`
**Required**: Yes (for discovery)
**Min Items**: 3
**Max Items**: 15
**Format**: Lowercase, hyphenated for multi-word terms

#### Description

Keywords enable AI-powered semantic matching beyond exact stack names. Include framework names, design patterns, technologies, and concepts relevant to the agent's domain.

#### Examples

```yaml
# Python API Specialist
keywords: [fastapi, async, endpoints, router, dependency-injection, pydantic, validation, middleware]

# React State Specialist
keywords: [react, hooks, state, zustand, tanstack-query, context, reducer, memoization]

# .NET Domain Specialist
keywords: [entity, domain, repository, ddd, value-object, aggregate, domain-events]
```

#### Validation Rules

- Must have 3-15 items
- All lowercase
- Use hyphens for multi-word terms (e.g., `dependency-injection`, `tanstack-query`)
- No special characters except hyphens
- Include framework names, patterns, technologies

#### Keyword Categories

Good keywords typically fall into these categories:

1. **Framework/Library Names**: `fastapi`, `react`, `dotnet`, `zustand`
2. **Design Patterns**: `repository`, `factory`, `observer`, `singleton`
3. **Technical Concepts**: `async`, `hooks`, `dependency-injection`, `middleware`
4. **Domain Concepts**: `entity`, `aggregate`, `value-object`, `domain-events`
5. **Technology Features**: `endpoints`, `router`, `state`, `context`

#### Writing Good Keywords

✅ **Good Examples**:
- `fastapi` (framework)
- `async` (concept)
- `dependency-injection` (pattern, hyphenated)
- `tanstack-query` (library, hyphenated)
- `pydantic` (technology)

❌ **Bad Examples**:
- `FastAPI` (should be lowercase)
- `Dependency Injection` (should be hyphenated: `dependency-injection`)
- `API` (too generic, prefer specific like `fastapi`, `rest-api`, `graphql-api`)
- `code` (too generic)

#### How Many Keywords?

- **3-5 keywords**: Minimal for discovery (might miss matches)
- **6-10 keywords**: Good balance for most agents
- **11-15 keywords**: Comprehensive coverage (recommended for broad agents)
- **15+ keywords**: Hitting upper limit (consider if all are necessary)

---

## Validation Rules

### Summary Table

| Field | Type | Required | Min | Max | Format |
|-------|------|----------|-----|-----|--------|
| `stack` | array | Yes | 1 | - | Enum values |
| `phase` | string | Yes | - | - | Single enum value |
| `capabilities` | array | Yes | 1 | 10 | Descriptive phrases |
| `keywords` | array | Yes | 3 | 15 | Lowercase, hyphenated |

### Validation Pseudo-Code

```python
def validate_discovery_metadata(metadata: dict) -> tuple[bool, list[str]]:
    """
    Validate agent discovery metadata.

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Validate stack
    if 'stack' not in metadata:
        errors.append("Missing required field: stack")
    elif not isinstance(metadata['stack'], list):
        errors.append("Field 'stack' must be an array")
    elif len(metadata['stack']) == 0:
        errors.append("Field 'stack' must have at least 1 item")
    else:
        valid_stacks = ['python', 'react', 'dotnet', 'typescript', 'javascript',
                        'go', 'rust', 'java', 'ruby', 'php', 'cross-stack']
        invalid_stacks = [s for s in metadata['stack'] if s not in valid_stacks]
        if invalid_stacks:
            errors.append(f"Invalid stack values: {', '.join(invalid_stacks)}")

        # cross-stack cannot be combined with specific stacks
        if 'cross-stack' in metadata['stack'] and len(metadata['stack']) > 1:
            errors.append("'cross-stack' cannot be combined with specific stack names")

    # Validate phase
    if 'phase' not in metadata:
        errors.append("Missing required field: phase")
    elif not isinstance(metadata['phase'], str):
        errors.append("Field 'phase' must be a string (not an array)")
    elif metadata['phase'] not in ['implementation', 'review', 'testing', 'orchestration']:
        errors.append(f"Invalid phase value: {metadata['phase']}")

    # Validate capabilities
    if 'capabilities' not in metadata:
        errors.append("Missing required field: capabilities")
    elif not isinstance(metadata['capabilities'], list):
        errors.append("Field 'capabilities' must be an array")
    elif len(metadata['capabilities']) == 0:
        errors.append("Field 'capabilities' must have at least 1 item")
    elif len(metadata['capabilities']) > 10:
        errors.append("Field 'capabilities' should have at most 10 items (keep focused)")
    else:
        # Check for single-word entries (likely too generic)
        single_word_caps = [c for c in metadata['capabilities'] if len(c.split()) == 1]
        if single_word_caps:
            errors.append(f"Capabilities should be descriptive phrases, not single words: {', '.join(single_word_caps)}")

    # Validate keywords
    if 'keywords' not in metadata:
        errors.append("Missing required field: keywords")
    elif not isinstance(metadata['keywords'], list):
        errors.append("Field 'keywords' must be an array")
    elif len(metadata['keywords']) < 3:
        errors.append("Field 'keywords' must have at least 3 items")
    elif len(metadata['keywords']) > 15:
        errors.append("Field 'keywords' should have at most 15 items")
    else:
        # Check for uppercase or invalid characters
        invalid_keywords = []
        for kw in metadata['keywords']:
            if not isinstance(kw, str):
                invalid_keywords.append(f"{kw} (not a string)")
            elif kw != kw.lower():
                invalid_keywords.append(f"{kw} (should be lowercase)")
            elif not all(c.isalnum() or c == '-' for c in kw):
                invalid_keywords.append(f"{kw} (invalid characters, use hyphens only)")

        if invalid_keywords:
            errors.append(f"Invalid keywords: {', '.join(invalid_keywords)}")

    return (len(errors) == 0, errors)


# Example usage
metadata = {
    'stack': ['python'],
    'phase': 'implementation',
    'capabilities': ['FastAPI endpoint implementation', 'Async request handling'],
    'keywords': ['fastapi', 'async', 'api']
}

is_valid, errors = validate_discovery_metadata(metadata)
if is_valid:
    print("✅ Metadata is valid")
else:
    print("❌ Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

### Example Validation Results

#### Valid Metadata ✅

```yaml
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint implementation
  - Async request handling
keywords: [fastapi, async, api]
```

**Result**: ✅ Valid - All required fields present with correct format

---

#### Invalid Metadata ❌

```yaml
stack: []  # Empty array
phase: [implementation, review]  # Should be string, not array
capabilities: [Coding]  # Single-word entry (too generic)
keywords: [FastAPI, API]  # Uppercase not allowed
```

**Errors**:
- Field 'stack' must have at least 1 item
- Field 'phase' must be a string (not an array)
- Capabilities should be descriptive phrases, not single words: Coding
- Field 'keywords' must have at least 3 items
- Invalid keywords: FastAPI (should be lowercase), API (too generic)

---

## Complete Examples

### Example 1: Python API Specialist

```yaml
---
# Existing fields (preserved)
name: python-api-specialist
description: FastAPI implementation specialist for Phase 3 development
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "API endpoint implementation follows deterministic patterns. Haiku efficiently generates clean, testable FastAPI code."

# NEW: Discovery metadata
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint implementation
  - Async request handling
  - Dependency injection patterns
  - Pydantic schema integration
keywords: [fastapi, async, endpoints, router, dependency-injection, pydantic, validation, middleware]

# Optional collaboration
collaborates_with:
  - python-testing-specialist
  - database-specialist
---
```

**Use Case**: Automatically selected for Phase 3 tasks involving Python API development

---

### Example 2: React State Specialist

```yaml
---
# Existing fields (preserved)
name: react-state-specialist
description: React state management specialist for Phase 3 development
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "State management follows established patterns. Haiku handles hooks, context, and Zustand efficiently."

# NEW: Discovery metadata
stack: [react, typescript]
phase: implementation
capabilities:
  - React hooks implementation
  - State management patterns
  - TanStack Query integration
  - Component composition
keywords: [react, hooks, state, zustand, tanstack-query, context, reducer, memoization, typescript]

# Optional collaboration
collaborates_with:
  - react-testing-specialist
  - ui-specialist
---
```

**Use Case**: Automatically selected for Phase 3 tasks involving React state management

---

### Example 3: .NET Domain Specialist

```yaml
---
# Existing fields (preserved)
name: dotnet-domain-specialist
description: .NET domain modeling specialist for Phase 3 development
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Domain entities follow DDD patterns. Haiku generates clean domain models with value objects efficiently."

# NEW: Discovery metadata
stack: [dotnet]
phase: implementation
capabilities:
  - Domain entity modeling
  - Value object patterns
  - Repository pattern implementation
  - Entity validation logic
keywords: [entity, domain, repository, ddd, value-object, aggregate, csharp, dotnet]

# Optional collaboration
collaborates_with:
  - dotnet-testing-specialist
  - database-specialist
---
```

**Use Case**: Automatically selected for Phase 3 tasks involving .NET domain modeling

---

### Example 4: Cross-Stack Agent (Git Workflow Manager)

```yaml
---
# Existing fields (preserved)
name: git-workflow-manager
description: Git workflow specialist for branch naming, conventional commits, PR creation
tools: [Bash, Read, Write, Grep]
model: haiku
model_rationale: "Git operations follow deterministic workflows. Haiku efficiently handles branch creation, commits, and PR generation."

# NEW: Discovery metadata
stack: [cross-stack]  # Works across all technology stacks
phase: orchestration
capabilities:
  - Branch naming conventions
  - Conventional commit formatting
  - PR/MR creation and management
  - Merge strategy selection
keywords: [git, branch, commit, pr, merge, workflow, conventional-commits]

# Optional collaboration
collaborates_with:
  - task-manager
---
```

**Use Case**: Automatically selected for git-related tasks regardless of technology stack

---

## Migration Guide

### When to Add Discovery Metadata

Discovery metadata is **completely optional** and should be added based on your needs:

#### Add Metadata When:

- ✅ Creating NEW specialized agents for Phase 3 implementation
- ✅ Agent should participate in automatic phase-specific selection
- ✅ Agent has clear technology stack focus
- ✅ Team benefits from automatic agent matching

#### Don't Add Metadata When:

- ❌ Agent is manually invoked only (e.g., debugging tools)
- ❌ Agent is not phase-specific (metadata won't help)
- ❌ Agent is experimental or temporary
- ❌ Maintaining existing agents that work fine without it

### Migration Methods

#### Method 1: Use `/agent-enhance` Command (Recommended)

The `/agent-enhance` command can automatically add discovery metadata to existing agents:

```bash
# Enhance agent with discovery metadata
/agent-enhance .claude/agents/python-api-specialist.md --add-discovery-metadata

# Review suggested metadata
# Confirm or modify suggestions
# Save enhanced agent
```

**Benefits**:
- AI suggests appropriate metadata based on agent content
- Interactive review process
- Validates metadata during enhancement
- Preserves existing fields

---

#### Method 2: Manual Addition

Add metadata manually by editing the agent's frontmatter:

1. **Open agent file**: `.claude/agents/your-agent.md`

2. **Add discovery fields** after existing fields:

```yaml
---
# Existing fields (keep these)
name: your-agent
description: Your agent description
tools: [Read, Write, Edit]

# NEW: Add discovery metadata here
stack: [python]  # Replace with your stack
phase: implementation  # Choose appropriate phase
capabilities:
  - Capability 1
  - Capability 2
keywords: [keyword1, keyword2, keyword3]
---
```

3. **Validate metadata** using validation rules above

4. **Test agent** to ensure it still works correctly

---

### Step-by-Step Manual Migration Example

Let's migrate an existing `python-api-specialist` agent:

#### Step 1: Current Agent (No Metadata)

```yaml
---
name: python-api-specialist
description: FastAPI implementation specialist
tools: [Read, Write, Edit, Bash]
model: haiku
---
```

#### Step 2: Identify Discovery Fields

Based on the agent's purpose:
- **Stack**: `[python]` (FastAPI is Python-specific)
- **Phase**: `implementation` (generates code)
- **Capabilities**: FastAPI-specific patterns
- **Keywords**: FastAPI-related terms

#### Step 3: Add Discovery Metadata

```yaml
---
name: python-api-specialist
description: FastAPI implementation specialist
tools: [Read, Write, Edit, Bash]
model: haiku

# NEW: Discovery metadata
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint implementation
  - Async request handling
  - Dependency injection patterns
keywords: [fastapi, async, api, endpoints, pydantic]
---
```

#### Step 4: Validate

Run validation (pseudo-code):
```python
metadata = extract_frontmatter('python-api-specialist.md')
is_valid, errors = validate_discovery_metadata(metadata)
```

#### Step 5: Test

Verify agent still works:
```bash
# Test agent invocation
/task-work TASK-XXX  # Should auto-select python-api-specialist for Python API tasks
```

---

### Migration Checklist

Before migrating an agent:

- [ ] Agent is used for Phase 3 implementation tasks
- [ ] Agent has clear technology stack focus
- [ ] You can identify 1-5 core capabilities
- [ ] You can list 3-10 relevant keywords
- [ ] You've reviewed validation rules

After migration:

- [ ] Metadata passes validation (use pseudo-code above)
- [ ] Agent still works via manual invocation
- [ ] Agent appears in discovery results (if applicable)
- [ ] Collaborating agents updated (if needed)
- [ ] Documentation updated (if agent has dedicated docs)

---

### Migration Timeline

There is **no required timeline** for migration:

- **Immediate**: New agents created for haiku-agent-implementation epic (TASK-HAI-002, 003, 004)
- **Incremental**: Existing agents as needed for automatic selection
- **Optional**: Agents that work fine without metadata can remain unchanged indefinitely

**Zero Pressure**: Only migrate when it provides clear value

---

## FAQ

### General Questions

#### Q: Is discovery metadata required for all agents?

**A**: No. Discovery metadata is completely optional and OPT-IN only:
- Agents WITH metadata → Discoverable for automatic phase-specific selection
- Agents WITHOUT metadata → Continue working via manual invocation
- Zero breaking changes for existing agents

---

#### Q: What happens if I don't add discovery metadata?

**A**: Nothing changes. Your agent continues working exactly as before via manual invocation. Only agents WITH metadata participate in automatic phase-specific selection.

---

#### Q: Can I add metadata to existing agents?

**A**: Yes. Use either:
1. `/agent-enhance` command (AI-assisted)
2. Manual frontmatter editing

Both methods preserve existing fields and agent functionality.

---

#### Q: Will adding metadata break existing workflows?

**A**: No. Adding metadata is purely additive:
- ✅ Existing invocations continue working
- ✅ Backward compatible with all current workflows
- ✅ Optional fields don't cause errors if missing
- ✅ Zero impact to agents without metadata

---

### Stack Field Questions

#### Q: When should I use `[cross-stack]`?

**A**: Only for agents with ZERO technology-specific logic:
- ✅ git-workflow-manager (git is stack-agnostic)
- ✅ security-specialist (security principles are universal)
- ❌ API specialist (API patterns vary by stack)
- ❌ Testing specialist (test frameworks are stack-specific)

**Rule of thumb**: If agent behavior differs by technology, use specific stack names.

---

#### Q: Can an agent support multiple stacks?

**A**: Yes, list all supported stacks:
```yaml
stack: [react, typescript]  # React + TypeScript specialist
```

However, if logic differs significantly per stack, consider separate agents.

---

#### Q: What if my stack isn't in the allowed values list?

**A**: Contact maintainers to add new stack values to the enum. The schema is designed to be extensible without breaking changes.

---

### Phase Field Questions

#### Q: My agent works in multiple phases. What should I choose?

**A**: Choose the PRIMARY phase where the agent provides the MOST value:
- If agent mainly generates code (Phase 3) → `implementation`
- If agent mainly reviews code (Phase 5) → `review`
- If agent mainly runs tests (Phase 4) → `testing`

Phase is single-value to ensure clear agent selection.

---

#### Q: What's the difference between `implementation` and `orchestration`?

**A**:
- **implementation**: Generates production code, features, business logic
  - Examples: python-api-specialist, react-state-specialist
- **orchestration**: Coordinates workflow phases, manages other agents
  - Examples: task-manager

Most specialists use `implementation`.

---

### Capabilities Field Questions

#### Q: How do I write good capabilities?

**A**: Use descriptive phrases (2-5 words) that are specific and concrete:

✅ Good:
- "FastAPI endpoint implementation"
- "React hooks implementation"
- "Repository pattern implementation"

❌ Bad:
- "Coding" (too generic)
- "API" (too vague)
- "Best practices" (not specific)

---

#### Q: How many capabilities should I list?

**A**:
- **1-3**: Highly specialized agent
- **4-7**: Typical specialist (recommended)
- **8-10**: Broad specialist (upper limit)
- **10+**: Consider splitting into multiple agents

---

#### Q: Can capabilities overlap between agents?

**A**: Yes, agents can share capabilities if they approach them differently:
- `python-api-specialist`: "Async request handling" (FastAPI-specific)
- `python-testing-specialist`: "Async test execution" (pytest-async-specific)

Overlapping capabilities help AI select based on context.

---

### Keywords Field Questions

#### Q: How are keywords different from capabilities?

**A**:
- **Capabilities**: What the agent DOES (descriptive phrases)
- **Keywords**: How the agent is FOUND (search terms)

Example:
```yaml
capabilities:
  - FastAPI endpoint implementation  # What agent does
keywords: [fastapi, async, endpoints]  # How agent is found
```

---

#### Q: Should I use uppercase keywords?

**A**: No. All keywords must be lowercase for consistency and matching:
- ✅ `fastapi`, `react`, `dotnet`
- ❌ `FastAPI`, `React`, `DotNet`

---

#### Q: How do I format multi-word keywords?

**A**: Use hyphens (kebab-case):
- ✅ `dependency-injection`, `tanstack-query`, `domain-events`
- ❌ `dependency_injection`, `TanstackQuery`, `domain events`

---

#### Q: How many keywords should I include?

**A**:
- **Minimum**: 3 (required for discovery)
- **Recommended**: 6-10 (good balance)
- **Maximum**: 15 (upper limit)

More keywords = better discoverability, but keep them relevant.

---

### Validation Questions

#### Q: How do I validate my metadata?

**A**: Use the validation pseudo-code provided in the [Validation Rules](#validation-rules) section:

```python
metadata = extract_frontmatter('your-agent.md')
is_valid, errors = validate_discovery_metadata(metadata)
```

Or use `/agent-enhance` command which validates automatically.

---

#### Q: What happens if validation fails?

**A**: Validation errors prevent agent from being discoverable:
- Agent continues working via manual invocation
- Fix validation errors to enable discovery
- Use error messages to identify issues

---

#### Q: Are validation rules strict or warnings?

**A**:
- **Errors** (blocking): Missing required fields, invalid enum values, wrong types
- **Warnings** (non-blocking): Too many capabilities, generic keywords

Warnings allow flexibility while encouraging best practices.

---

### Migration Questions

#### Q: Do I need to migrate all agents at once?

**A**: No. Migration is incremental and optional:
- Migrate new agents immediately (TASK-HAI-002, 003, 004)
- Migrate existing agents as needed
- Leave unchanged agents that work fine without metadata

---

#### Q: Will migration affect my existing tasks?

**A**: No. Tasks continue working exactly as before:
- Agents WITH metadata → Also available for automatic selection
- Agents WITHOUT metadata → Continue working via manual invocation
- Zero disruption to existing workflows

---

#### Q: Can I remove metadata after adding it?

**A**: Yes. Simply delete the discovery fields from the frontmatter:
- Agent returns to manual-invocation-only
- Zero impact on agent functionality
- Metadata is purely opt-in

---

### Technical Questions

#### Q: How does AI matching work?

**A**: AI uses semantic matching based on:
1. **Stack**: Technology alignment (Python task → Python agent)
2. **Phase**: Workflow phase (Implementation task → Implementation agent)
3. **Capabilities**: Pattern matching (API task → API capabilities)
4. **Keywords**: Semantic similarity (FastAPI → fastapi, async, api)

AI selects best agent based on combined score across all fields.

---

#### Q: What if multiple agents match?

**A**: AI ranks agents by relevance score:
1. Exact stack + phase match (highest priority)
2. Capability overlap with task requirements
3. Keyword semantic similarity

Most relevant agent is selected automatically.

---

#### Q: Can I override automatic selection?

**A**: Yes. Always possible to:
- Manually invoke specific agent
- Disable automatic selection (if feature added)
- Create task-specific agent preferences (future enhancement)

Metadata enables automation but doesn't force it.

---

#### Q: How extensible is the schema?

**A**: Highly extensible:
- ✅ Add new stack enum values (backward compatible)
- ✅ Add new phase enum values (backward compatible)
- ✅ Add optional fields (backward compatible)
- ⚠️ Breaking changes require major version bump (rare)

---

### Support Questions

#### Q: Where can I get help with migration?

**A**:
1. Use `/agent-enhance` command (AI-assisted migration)
2. Review complete examples in this document
3. Check validation pseudo-code for debugging
4. Contact maintainers for schema questions

---

#### Q: How do I report schema issues?

**A**:
- Schema bugs: Open issue with validation error details
- Schema enhancements: Propose new allowed values or fields
- Migration problems: Share agent file and error messages

---

## Version History

### v1.0 (2025-11-25)

**Initial Release**

- 4 discovery fields: `stack`, `phase`, `capabilities`, `keywords`
- Opt-in discovery model (backward compatible)
- Support for Python, React, .NET stacks
- Validation rules and pseudo-code
- Complete documentation with examples
- Migration guide for existing agents

**Related Tasks**:
- TASK-HAI-001-D668: Schema design (this document)
- TASK-HAI-002: Python API Specialist (first implementation)
- TASK-HAI-003: React State Specialist (first implementation)
- TASK-HAI-004: .NET Domain Specialist (first implementation)

---

## Related Documentation

- **Schema YAML**: `docs/schemas/agent-discovery-metadata.yaml`
- **Validation Pseudo-Code**: See [Validation Rules](#validation-rules) section above
- **Agent Enhancement Guide**: `/agent-enhance` command documentation
- **Task Creation**: `TASK-HAI-002/003/004` (first agents using schema)

---

## Feedback and Contributions

This schema is designed to be extensible and community-driven:

- **New Stack Support**: Propose additional stack enum values
- **New Phase Types**: Suggest new workflow phases
- **Schema Enhancements**: Recommend additional optional fields
- **Documentation Improvements**: Submit clarifications or examples

All feedback helps improve agent discoverability for the entire community.
