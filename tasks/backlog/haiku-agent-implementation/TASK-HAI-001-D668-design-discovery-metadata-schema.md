---
id: TASK-HAI-001-D668
title: Design Discovery Metadata Schema
status: backlog
priority: high
tags: [haiku-agents, model-optimization, schema-design]
epic: haiku-agent-implementation
complexity: 3
estimated_hours: 1.5
dependencies: []
blocks: [TASK-HAI-002, TASK-HAI-003, TASK-HAI-004]
created: 2025-11-25T12:00:00Z
updated: 2025-11-25T12:00:00Z
---

# Task: Design Discovery Metadata Schema

## Context

Define the YAML frontmatter schema for agent discovery metadata that enables AI-powered agent selection in Phase 3 implementation. This schema will be used by 3 new stack-specific Haiku agents and can be adopted by existing agents via incremental enhancement.

**Parent Epic**: haiku-agent-implementation
**Related Review**: TASK-895A (defer Opus 4.5, complete Haiku agents)
**Original Vision**: TASK-EE41 (model optimization strategy)

## Objectives

1. Define clear, extensible YAML schema for discovery metadata
2. Support AI-powered agent matching (stack, phase, capabilities, keywords)
3. Enable graceful degradation (agents without metadata still work)
4. Document schema with examples and validation rules
5. Provide migration path for existing agents

## Discovery Metadata Fields

### Required for Discovery

```yaml
stack:
  type: array
  items:
    enum: [python, react, dotnet, typescript, javascript, go, rust, java, ruby, php, cross-stack]
  description: "Technology stacks this agent supports"
  examples:
    - [python]              # Python-specific
    - [react, typescript]   # React + TypeScript
    - [cross-stack]         # Works across all stacks
  
phase:
  type: string
  enum: [implementation, review, testing, orchestration]
  description: "Primary workflow phase where agent operates"
  examples:
    - implementation  # Phase 3 code generation
    - review          # Phase 5 code review
    - testing         # Phase 4 test execution
    - orchestration   # Phase coordination (task-manager)
  
capabilities:
  type: array
  items: string
  description: "Specific capabilities and patterns agent implements"
  examples:
    - ["API design", "FastAPI patterns", "async handlers"]
    - ["React hooks", "state management", "TanStack Query"]
    - ["Domain entities", "value objects", "DDD patterns"]
  
keywords:
  type: array
  items: string
  description: "Keywords for AI-powered agent matching"
  examples:
    - [fastapi, async, endpoints, pydantic]
    - [react, hooks, state, zustand]
    - [entity, domain, repository, ddd]
```

### Existing Fields (Preserved)

```yaml
name: string (required)
description: string (required)
tools: array (optional)
model: string (optional - sonnet, haiku, opus)
model_rationale: string (optional)
orchestration: string (optional)
collaborates_with: array (optional)
```

## Design Principles

1. **Opt-In Discovery**: Only agents WITH metadata are discoverable for phase-specific tasks
2. **Backward Compatible**: Agents WITHOUT metadata continue to work (manual invocation)
3. **Graceful Degradation**: Missing fields don't cause errors
4. **AI-Friendly**: Keywords enable semantic matching beyond exact stack names
5. **Future-Proof**: Extensible to new stacks/phases without breaking changes

## Example: Complete Agent Frontmatter

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
keywords: [fastapi, async, endpoints, router, dependency-injection, pydantic]

# Optional collaboration
collaborates_with:
  - python-testing-specialist
  - database-specialist
---
```

## Validation Rules

### Stack Field
- **Type**: Array of strings
- **Min Items**: 1
- **Valid Values**: python, react, dotnet, typescript, javascript, go, rust, java, ruby, php, cross-stack
- **Cross-Stack**: Use `[cross-stack]` for agents working across all technologies

### Phase Field
- **Type**: String (single value)
- **Valid Values**: implementation, review, testing, orchestration
- **Constraint**: Each agent has ONE primary phase (not an array)

### Capabilities Field
- **Type**: Array of strings
- **Min Items**: 1
- **Max Items**: 10 (keep focused)
- **Format**: Descriptive phrases (not single words)
- **Examples**: "API design", "React hooks", "Domain modeling"

### Keywords Field
- **Type**: Array of strings
- **Min Items**: 3
- **Max Items**: 15
- **Format**: Lowercase, hyphenated for multi-word
- **Purpose**: AI semantic matching
- **Examples**: fastapi, react-hooks, dependency-injection

## Acceptance Criteria

- [ ] Schema defined in YAML format
- [ ] Documentation created: `docs/schemas/agent-discovery-metadata.md`
- [ ] All 4 discovery fields specified (stack, phase, capabilities, keywords)
- [ ] Validation rules documented
- [ ] Examples provided for each field
- [ ] Cross-stack vs stack-specific distinction clear
- [ ] Migration path for existing agents documented
- [ ] Schema validation pseudo-code provided

## Deliverables

### 1. Schema Definition File

**Path**: `docs/schemas/agent-discovery-metadata.yaml`

Complete YAML schema with:
- Field definitions
- Type specifications
- Enum values
- Validation rules
- Default values (if any)

### 2. Documentation

**Path**: `docs/schemas/agent-discovery-metadata.md`

Includes:
- Purpose and overview
- Field-by-field documentation
- Examples for each stack (Python, React, .NET)
- Validation rules and constraints
- FAQ section

### 3. Validation Pseudo-Code

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
        valid_stacks = ['python', 'react', 'dotnet', 'typescript', 'javascript', 'go', 'rust', 'java', 'ruby', 'php', 'cross-stack']
        for stack in metadata['stack']:
            if stack not in valid_stacks:
                errors.append(f"Invalid stack value: {stack}")
    
    # Validate phase
    if 'phase' not in metadata:
        errors.append("Missing required field: phase")
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
        errors.append("Field 'capabilities' should have at most 10 items")
    
    # Validate keywords
    if 'keywords' not in metadata:
        errors.append("Missing required field: keywords")
    elif not isinstance(metadata['keywords'], list):
        errors.append("Field 'keywords' must be an array")
    elif len(metadata['keywords']) < 3:
        errors.append("Field 'keywords' must have at least 3 items")
    elif len(metadata['keywords']) > 15:
        errors.append("Field 'keywords' should have at most 15 items")
    
    return (len(errors) == 0, errors)
```

### 4. Migration Guide

**Path**: `docs/schemas/agent-discovery-metadata.md` (section)

Explains how to add metadata to existing agents:
- When to add metadata (optional for existing agents)
- How to use `/agent-enhance` for migration
- How to manually add metadata
- Testing metadata after addition

## Testing

### Unit Tests (Pseudo-Code)

```python
def test_valid_metadata_passes():
    """Valid metadata should pass validation."""
    metadata = {
        'stack': ['python'],
        'phase': 'implementation',
        'capabilities': ['API design', 'FastAPI patterns'],
        'keywords': ['fastapi', 'async', 'api']
    }
    is_valid, errors = validate_discovery_metadata(metadata)
    assert is_valid
    assert len(errors) == 0

def test_missing_required_field_fails():
    """Missing required field should fail validation."""
    metadata = {
        'stack': ['python'],
        'phase': 'implementation'
        # Missing capabilities and keywords
    }
    is_valid, errors = validate_discovery_metadata(metadata)
    assert not is_valid
    assert 'capabilities' in str(errors)

def test_invalid_stack_fails():
    """Invalid stack value should fail validation."""
    metadata = {
        'stack': ['invalid-stack'],
        'phase': 'implementation',
        'capabilities': ['API design'],
        'keywords': ['api']
    }
    is_valid, errors = validate_discovery_metadata(metadata)
    assert not is_valid
    assert 'invalid-stack' in str(errors)

def test_too_many_capabilities_warns():
    """More than 10 capabilities should generate warning."""
    metadata = {
        'stack': ['python'],
        'phase': 'implementation',
        'capabilities': [f'Cap{i}' for i in range(15)],
        'keywords': ['python', 'api', 'test']
    }
    is_valid, errors = validate_discovery_metadata(metadata)
    assert not is_valid
    assert 'at most 10' in str(errors)
```

## Risk Assessment

**Risk Level**: LOW

**Potential Risks**:
1. Schema too restrictive → Mitigation: Extensible enum values
2. Validation too strict → Mitigation: Warnings vs errors
3. Migration confusion → Mitigation: Clear documentation and examples

**Rollback Strategy**: Delete schema files (no impact on system)

## Non-Functional Requirements

### Performance
- Schema validation: <10ms per agent
- No runtime performance impact (validation during creation only)

### Maintainability
- Schema version tracked (v1.0)
- Backward compatible additions (new enum values OK)
- Breaking changes require major version bump

### Documentation Quality
- Examples for all 3 target stacks (Python, React, .NET)
- FAQ addresses common questions
- Migration guide clear and actionable

## Related Tasks

**Blocks**:
- TASK-HAI-002: Create Python API Specialist (needs schema)
- TASK-HAI-003: Create React State Specialist (needs schema)
- TASK-HAI-004: Create .NET Domain Specialist (needs schema)

**Related**:
- TASK-895A: Model selection strategy review (parent decision)
- TASK-EE41: Original model optimization (context)

## Definition of Done

- [ ] Schema YAML file created and validated
- [ ] Documentation markdown file complete with examples
- [ ] Validation pseudo-code provided
- [ ] Migration guide documented
- [ ] Examples for Python, React, .NET stacks
- [ ] Peer reviewed for clarity and completeness
- [ ] No blocking issues from TASK-HAI-002/003/004 reviewers

## Notes

This schema enables AI-powered agent discovery without hardcoded mappings, maintaining Taskwright's AI-first philosophy while providing the structure needed for reliable matching.

**Key Design Decision**: Metadata is OPT-IN, ensuring zero disruption to 15 existing agents enhanced Nov 25 08:05.
