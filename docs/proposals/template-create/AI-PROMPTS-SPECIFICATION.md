# AI Prompts Specification for Template-Create

**Date**: 2025-11-18
**Status**: SPECIFICATION
**Purpose**: Define complete AI prompts for template-create phases
**Related**: TEMPLATE-CREATE-REDESIGN-PROPOSAL.md, AGENT-STRATEGY-high-level-design.md

---

## Overview

This document specifies the exact prompts, expected outputs, and confidence thresholds for all AI-powered phases in the template-create workflow. These specifications ensure:

1. **Deterministic AI invocation** - No ambiguity in what to ask
2. **Parseable outputs** - Structured JSON responses
3. **Quality gates** - Confidence thresholds for proceed/fallback decisions
4. **AI-First compliance** - AI creates and analyzes, no hard-coded patterns

---

## Phase 1: AI Codebase Analysis

### Agent
`architectural-reviewer`

### Purpose
Analyze codebase samples to extract technology stack, architecture patterns, and project characteristics with high confidence.

### Prompt Template

```markdown
# Codebase Analysis Request

You are analyzing a codebase to generate a project template. Examine the provided file samples and extract comprehensive technical information.

## File Samples

The following files were selected using stratified sampling (30 files across different directories and types):

```json
{file_samples}
```

## Analysis Requirements

Analyze the codebase and provide structured output covering:

### 1. Technology Stack
- **Primary Language**: The main programming language (e.g., "C#", "TypeScript", "Python")
- **Secondary Languages**: Other languages used (e.g., ["XAML", "JSON"])
- **Frameworks**: Main frameworks with versions (e.g., ".NET MAUI 8.0", "React 18.2", "FastAPI 0.100")
- **Build Tools**: Build systems used (e.g., "MSBuild", "Vite", "Poetry")
- **Package Manager**: Dependency management (e.g., "NuGet", "npm", "pip")

### 2. Architecture Analysis
- **Architectural Pattern**: Primary pattern (e.g., "MVVM", "Clean Architecture", "MVC", "Hexagonal")
- **Layers**: Identified layers (e.g., ["Domain", "Application", "Infrastructure", "Presentation"])
- **Module Structure**: How code is organized (e.g., "feature-based", "layer-based", "hybrid")

### 3. Code Patterns
Identify specific patterns used in the codebase:
- Design patterns (Repository, Factory, Mediator, etc.)
- Error handling patterns (ErrorOr<T>, Result<T>, exceptions)
- Dependency injection approach
- State management patterns
- Navigation patterns (for UI apps)

For each pattern, provide:
- Pattern name
- Confidence (how certain you are it's used)
- Example files where you saw it
- Usage frequency estimate

### 4. Testing Analysis
- **Testing Framework**: e.g., "xUnit", "Jest", "pytest"
- **Testing Patterns**: e.g., "Arrange-Act-Assert", "Given-When-Then"
- **Test Organization**: How tests are structured
- **Coverage Indicators**: Estimate of test coverage (Low/Medium/High)

### 5. Quality Indicators
- **SOLID Compliance**: Estimate (1-10 scale)
- **Code Organization**: How well-organized (1-10 scale)
- **Documentation Level**: Amount of docs/comments (Low/Medium/High)
- **Naming Conventions**: Patterns observed (e.g., "PascalCase for classes", "camelCase for variables")

## Output Format

Return a JSON object matching this exact schema:

```json
{
  "technology_stack": {
    "primary_language": "string",
    "secondary_languages": ["string"],
    "frameworks": [
      {
        "name": "string",
        "version": "string",
        "confidence": 0.0-1.0
      }
    ],
    "build_tools": ["string"],
    "package_manager": "string",
    "confidence": 0.0-1.0
  },
  "architecture": {
    "pattern": "string",
    "layers": ["string"],
    "module_structure": "string",
    "key_abstractions": ["string"],
    "confidence": 0.0-1.0
  },
  "patterns": [
    {
      "name": "string",
      "category": "design|error_handling|di|state|navigation|other",
      "confidence": 0.0-1.0,
      "example_files": ["string"],
      "usage_frequency": "rare|occasional|common|pervasive",
      "description": "string"
    }
  ],
  "testing": {
    "framework": "string",
    "patterns": ["string"],
    "organization": "string",
    "coverage_estimate": "low|medium|high",
    "confidence": 0.0-1.0
  },
  "quality_indicators": {
    "solid_compliance": 1-10,
    "code_organization": 1-10,
    "documentation_level": "low|medium|high",
    "naming_conventions": {
      "classes": "string",
      "methods": "string",
      "variables": "string",
      "files": "string"
    }
  },
  "overall_confidence": 0.0-1.0,
  "analysis_notes": "string"
}
```

## Confidence Scoring Guidelines

- **0.95-1.0**: Absolutely certain (explicit evidence in multiple files)
- **0.85-0.94**: Very confident (clear evidence in several files)
- **0.70-0.84**: Reasonably confident (evidence present but limited)
- **0.50-0.69**: Uncertain (some indicators but could be wrong)
- **Below 0.50**: Guessing (insufficient evidence)

## Important Notes

1. **Be conservative with confidence scores** - Only score high if you have clear evidence
2. **List all patterns you detect** - Even if usage is rare
3. **Include example files** - Show where you found each pattern
4. **Note uncertainties** - Use analysis_notes for caveats
5. **Focus on what you SEE** - Don't assume patterns that aren't evident
```

### Expected Output Schema

See JSON schema in prompt above.

### Confidence Thresholds

| Overall Confidence | Action | Description |
|-------------------|--------|-------------|
| ≥ 0.85 | AUTO_PROCEED | High confidence, continue automatically |
| 0.70 - 0.84 | PROCEED_WITH_WARNING | Acceptable confidence, warn user |
| < 0.70 | FALLBACK_TO_HEURISTICS | Low confidence, use heuristic analysis |

### Fallback Behavior

If confidence < 0.70 or agent invocation fails:
1. Log warning: "AI analysis confidence too low ({confidence}), using heuristics"
2. Fall back to existing `_heuristic_analysis()` method
3. Set manifest confidence to heuristic result
4. Continue workflow

### Error Handling

```python
try:
    response = agent_invoker.invoke(
        agent_name="architectural-reviewer",
        prompt=PHASE_1_ANALYSIS_PROMPT.format(file_samples=json.dumps(samples)),
        timeout_seconds=120
    )
    analysis = json.loads(response)

    if analysis["overall_confidence"] < 0.70:
        logger.warning(f"Low AI confidence: {analysis['overall_confidence']}")
        return self._fallback_to_heuristics(samples)

    return CodebaseAnalysis.from_ai_response(analysis)

except json.JSONDecodeError as e:
    logger.error(f"Failed to parse AI response: {e}")
    return self._fallback_to_heuristics(samples)

except AgentInvocationError as e:
    logger.warning(f"Agent invocation failed: {e}")
    return self._fallback_to_heuristics(samples)
```

---

## Phase 4: AI Agent Creation

### Agent
`architectural-reviewer` (in agent creation mode)

### Purpose
CREATE specialized agents to fill capability gaps based on codebase analysis. This phase follows the AI-First Strategy principle: **AI creates agents, not just discovers them**.

### Important: Creation vs Discovery

Per AGENT-STRATEGY-high-level-design.md:
> "Claude Code should **create appropriate agents** based on codebase analysis, not just discover existing ones."

This phase must:
1. Check existing agents (user custom > template > global)
2. Identify capability gaps
3. CREATE new agents to fill those gaps
4. Output both "use existing" and "create new" lists

### Prompt Template

```markdown
# Agent Creation Request

You are creating specialized AI agents for a codebase. Based on the analysis provided, determine which existing agents to use and which NEW agents to create.

## Codebase Analysis

```json
{codebase_analysis}
```

## Existing Agent Inventory

The following agents already exist and should NOT be recreated:

### User Custom Agents (HIGHEST PRIORITY - always use these)
```json
{user_custom_agents}
```

### Template Agents (HIGH PRIORITY)
```json
{template_agents}
```

### Global Built-in Agents (MEDIUM PRIORITY)
```json
{global_agents}
```

## Agent Creation Guidelines

### Priority Rules
1. **Never recreate** user custom agents - always use them
2. **Prefer** template agents over creating duplicates
3. **Use** global agents for general capabilities
4. **Create** new agents only for GAPS in coverage

### Agent Types to Consider

Based on the codebase patterns, consider creating agents for:

**Architecture Patterns:**
- repository-pattern-specialist (if Repository pattern detected)
- service-layer-specialist (if Service layer detected)
- cqrs-specialist (if Command/Query separation detected)
- event-sourcing-specialist (if Event sourcing detected)
- domain-driven-design-specialist (if DDD patterns detected)
- clean-architecture-specialist (if Clean Architecture detected)

**Technology-Specific:**
- database-specialist (if direct database access patterns)
- orm-specialist (if ORM usage detected - EF Core, SQLAlchemy, etc.)
- api-client-specialist (if external API consumption)
- message-queue-specialist (if async messaging)
- caching-specialist (if caching patterns detected)

**UI/Frontend Patterns:**
- mvvm-specialist (if MVVM pattern detected)
- navigation-specialist (if routing/navigation)
- state-management-specialist (if state management patterns)
- form-validation-specialist (if form validation)

**Error Handling:**
- erroror-pattern-specialist (if ErrorOr<T> or Result<T> types)
- exception-handling-specialist (if structured exception handling)

**Testing:**
- testing-specialist (always recommended if test files exist)
- integration-testing-specialist (if integration tests present)
- e2e-testing-specialist (if E2E test framework detected)

### Creation Requirements

For each new agent, you must provide:
1. **name**: Kebab-case identifier (e.g., "repository-pattern-specialist")
2. **priority**: 1-10 (higher = more important for this codebase)
3. **rationale**: Why this agent is needed (reference specific patterns/files)
4. **key_patterns**: List of patterns that triggered this recommendation
5. **capabilities**: What this agent can do
6. **content_outline**: Structure for the agent definition

## Output Format

Return a JSON object matching this exact schema:

```json
{
  "use_existing": [
    {
      "name": "string",
      "source": "custom|template|global",
      "reason": "string"
    }
  ],
  "create_new": [
    {
      "name": "string",
      "priority": 1-10,
      "rationale": "string",
      "key_patterns": ["string"],
      "example_files": ["string"],
      "capabilities": ["string"],
      "content_outline": {
        "purpose": "string",
        "when_to_use": ["string"],
        "key_responsibilities": ["string"],
        "related_patterns": ["string"],
        "tools_needed": ["string"]
      }
    }
  ],
  "agent_count": {
    "existing_used": "integer",
    "newly_created": "integer",
    "total": "integer"
  },
  "coverage_analysis": {
    "patterns_covered": ["string"],
    "patterns_uncovered": ["string"],
    "coverage_percentage": 0-100
  },
  "confidence": 0.0-1.0,
  "notes": "string"
}
```

## Quality Requirements

1. **Target 7-9 total agents** for a typical project
2. **All major patterns should have coverage**
3. **Don't over-specialize** - combine related patterns into single agent
4. **Prioritize** most-used patterns
5. **Include testing-specialist** if tests exist

## Example Output

For a .NET MAUI project with MVVM, ErrorOr, and Repository patterns:

```json
{
  "use_existing": [
    {"name": "architectural-reviewer", "source": "global", "reason": "General architecture review"},
    {"name": "code-reviewer", "source": "global", "reason": "Code quality review"},
    {"name": "test-verifier", "source": "global", "reason": "Test execution"}
  ],
  "create_new": [
    {
      "name": "maui-mvvm-specialist",
      "priority": 9,
      "rationale": "MVVM pattern detected in 15 ViewModels with INotifyPropertyChanged",
      "key_patterns": ["MVVM", "INotifyPropertyChanged", "CommunityToolkit.Mvvm"],
      "example_files": ["ViewModels/ProductListViewModel.cs", "ViewModels/SettingsViewModel.cs"],
      "capabilities": [
        "Create ViewModels following project conventions",
        "Implement INotifyPropertyChanged correctly",
        "Set up command bindings",
        "Manage ViewModel lifecycle"
      ],
      "content_outline": {
        "purpose": "Specialist in .NET MAUI MVVM implementation patterns",
        "when_to_use": ["Creating new ViewModels", "Adding properties", "Setting up commands"],
        "key_responsibilities": ["ViewModel structure", "Data binding", "Command implementation"],
        "related_patterns": ["CommunityToolkit.Mvvm", "ObservableObject"],
        "tools_needed": ["Read", "Write", "Edit", "Grep"]
      }
    },
    {
      "name": "erroror-pattern-specialist",
      "priority": 8,
      "rationale": "ErrorOr<T> pattern used in all domain operations",
      "key_patterns": ["ErrorOr<T>", "Railway-oriented programming", "Result types"],
      "example_files": ["Domain/Products/GetProducts.cs", "Domain/Orders/CreateOrder.cs"],
      "capabilities": [
        "Implement ErrorOr return types",
        "Create custom errors",
        "Chain operations with Then/Map",
        "Handle error cases properly"
      ],
      "content_outline": {
        "purpose": "Expert in ErrorOr<T> railway-oriented error handling",
        "when_to_use": ["Domain operations", "Service methods", "Error propagation"],
        "key_responsibilities": ["Error creation", "Result chaining", "Error handling"],
        "related_patterns": ["Railway-oriented programming", "Result pattern"],
        "tools_needed": ["Read", "Write", "Edit"]
      }
    }
  ],
  "agent_count": {
    "existing_used": 3,
    "newly_created": 6,
    "total": 9
  },
  "coverage_analysis": {
    "patterns_covered": ["MVVM", "ErrorOr", "Repository", "Navigation", "DI", "Testing"],
    "patterns_uncovered": [],
    "coverage_percentage": 100
  },
  "confidence": 0.92,
  "notes": "Good pattern coverage. Created 6 specialized agents for MAUI-specific patterns."
}
```
```

### Expected Output Schema

See JSON schema in prompt above.

### Confidence Thresholds

| Confidence | Action | Description |
|------------|--------|-------------|
| ≥ 0.85 | AUTO_PROCEED | Create all recommended agents |
| 0.70 - 0.84 | PROCEED_WITH_WARNING | Create agents, warn user to review |
| < 0.70 | FALLBACK_TO_BASIC | Use basic agent set from manifest |

### Fallback Behavior

If confidence < 0.70 or agent invocation fails:
1. Log warning: "AI agent creation confidence too low ({confidence}), using basic set"
2. Fall back to basic agent set: [architectural-reviewer, code-reviewer, test-verifier, testing-specialist]
3. Set agent count to 4 (basic set)
4. Continue workflow with basic agents

### Error Handling

```python
try:
    response = agent_invoker.invoke(
        agent_name="architectural-reviewer",
        prompt=PHASE_4_AGENT_CREATION_PROMPT.format(
            codebase_analysis=json.dumps(analysis),
            user_custom_agents=json.dumps(user_agents),
            template_agents=json.dumps(template_agents),
            global_agents=json.dumps(global_agents)
        ),
        timeout_seconds=180  # Longer timeout for complex analysis
    )
    result = json.loads(response)

    if result["confidence"] < 0.70:
        logger.warning(f"Low AI confidence: {result['confidence']}")
        return self._fallback_to_basic_agents()

    return AgentCreationResult.from_ai_response(result)

except json.JSONDecodeError as e:
    logger.error(f"Failed to parse AI response: {e}")
    return self._fallback_to_basic_agents()

except AgentInvocationError as e:
    logger.warning(f"Agent invocation failed: {e}")
    return self._fallback_to_basic_agents()
```

---

## Phase 7.5: AI Agent Enhancement

### Agent
`agent-content-enhancer`

### Purpose
Enhance basic agent definitions (30 lines) into comprehensive documentation (150-250 lines) with template-specific examples, code samples, and best practices.

### Prompt Template

```markdown
# Agent Enhancement Request

You are enhancing basic AI agent definitions with comprehensive, template-specific content. Transform each basic agent into a detailed, actionable specialist.

## Basic Agent Definitions

The following agents need enhancement:

```json
{basic_agents}
```

## Template Context

### Available Templates
```json
{template_catalog}
```

### Code Samples from Templates
```json
{template_code_samples}
```

### Project Settings
```json
{project_settings}
```

## Enhancement Requirements

For EACH agent, generate comprehensive documentation (150-250 lines) including:

### 1. Header Section
```markdown
---
name: agent-name
description: One-line description
tools: [Read, Write, Edit, Grep, Glob]
tags: [relevant, tags, here]
---
```

### 2. Purpose Statement (50-100 words)
- What this agent does
- When it's most useful
- What problems it solves

### 3. When to Use (3-4 scenarios)
Specific scenarios with examples:
```markdown
## When to Use

Use this agent when you need to:

1. **Scenario name** - Description of when to use
   - Example: "Creating a new Repository for the Orders domain"

2. **Scenario name** - Description
   - Example: "..."
```

### 4. Capabilities (5-7 items)
What the agent can do:
```markdown
## Capabilities

- Capability 1: Description
- Capability 2: Description
...
```

### 5. Related Templates (2-3 primary)
Link to actual templates with descriptions:
```markdown
## Related Templates

### Primary Templates
1. **template-name** (`path/to/template.py`)
   - What it demonstrates
   - Key patterns to note

2. **template-name** ...
```

### 6. Code Examples (2-3 examples)
Extract ACTUAL code from template_code_samples:
```markdown
## Code Examples

### Example 1: Pattern Name

From `path/to/file.py`:

\`\`\`python
# Actual code from template
class ExampleClass:
    def method(self):
        pass
\`\`\`

**Key Points:**
- Point 1
- Point 2
```

### 7. Best Practices (3-5 practices)
Derived from template patterns:
```markdown
## Best Practices

### DO
- Practice 1
- Practice 2

### DON'T
- Anti-pattern 1
- Anti-pattern 2
```

### 8. Common Patterns (2-3 patterns)
Patterns this agent works with:
```markdown
## Common Patterns

### Pattern Name
Description and when to use.

\`\`\`python
# Pattern example
\`\`\`
```

### 9. Integration Points
How this agent works with others:
```markdown
## Integration Points

- Works with **agent-name** for X
- Coordinates with **agent-name** for Y
```

## Output Format

Return a JSON object matching this schema:

```json
{
  "enhanced_agents": [
    {
      "name": "string",
      "enhanced_content": "string (full markdown, 150-250 lines)",
      "template_references": [
        {
          "template": "string",
          "relevance": "primary|secondary",
          "patterns_shown": ["string"]
        }
      ],
      "code_examples_count": "integer",
      "line_count": "integer",
      "sections_included": ["string"],
      "quality_score": 1-10
    }
  ],
  "enhancement_summary": {
    "total_agents": "integer",
    "average_line_count": "integer",
    "average_quality_score": "number",
    "templates_referenced": ["string"]
  },
  "confidence": 0.0-1.0,
  "notes": "string"
}
```

## Quality Requirements

1. **Minimum 150 lines** per agent
2. **All 9 sections** must be present
3. **At least 2 code examples** with actual template code
4. **At least 2 template references** per agent
5. **Quality score ≥ 8/10** for each agent

## Important Notes

1. **Use ACTUAL code from templates** - Don't make up examples
2. **Reference real file paths** - Use paths from template_code_samples
3. **Be specific to this project** - Don't be generic
4. **Include actionable guidance** - Users should know exactly what to do
5. **Cross-reference related agents** - Show how they work together
```

### Expected Output Schema

See JSON schema in prompt above.

### Confidence Thresholds

| Confidence | Action | Description |
|------------|--------|-------------|
| ≥ 0.80 | AUTO_PROCEED | Use all enhanced agents |
| 0.60 - 0.79 | PROCEED_WITH_WARNING | Use enhanced, warn about quality |
| < 0.60 | FALLBACK_TO_BASIC | Keep original basic agents |

### Fallback Behavior

If confidence < 0.60 or agent invocation fails:
1. Log warning: "Agent enhancement failed, using basic agents"
2. Keep original 30-line agent definitions
3. Continue workflow with basic agents
4. Note in validation report

### Error Handling

```python
try:
    response = agent_invoker.invoke(
        agent_name="agent-content-enhancer",
        prompt=PHASE_7_5_ENHANCEMENT_PROMPT.format(
            basic_agents=json.dumps(basic_agents),
            template_catalog=json.dumps(catalog),
            template_code_samples=json.dumps(samples),
            project_settings=json.dumps(settings)
        ),
        timeout_seconds=300  # 5 minutes for batch enhancement
    )
    result = json.loads(response)

    if result["confidence"] < 0.60:
        logger.warning(f"Low enhancement confidence: {result['confidence']}")
        return EnhancementResult(
            agents=basic_agents,
            enhanced=False,
            reason="Low confidence"
        )

    return EnhancementResult.from_ai_response(result)

except json.JSONDecodeError as e:
    logger.error(f"Failed to parse AI response: {e}")
    return EnhancementResult(agents=basic_agents, enhanced=False, reason=str(e))

except AgentInvocationError as e:
    logger.warning(f"Agent invocation failed: {e}")
    return EnhancementResult(agents=basic_agents, enhanced=False, reason=str(e))
```

---

## Summary: Confidence Threshold Reference

| Phase | Agent | Min Confidence | Fallback |
|-------|-------|----------------|----------|
| 1 | architectural-reviewer | 0.70 | Heuristic analysis |
| 4 | architectural-reviewer | 0.70 | Basic agent set (4 agents) |
| 7.5 | agent-content-enhancer | 0.60 | Keep basic 30-line agents |

---

## Usage in Orchestrator

```python
# Phase 1
from prompts import PHASE_1_ANALYSIS_PROMPT, PHASE_1_CONFIDENCE_THRESHOLD

def _phase1_ai_analysis(self, samples: List[FileSample]) -> CodebaseAnalysis:
    prompt = PHASE_1_ANALYSIS_PROMPT.format(file_samples=json.dumps(samples))
    response = self.agent_invoker.invoke("architectural-reviewer", prompt)
    analysis = json.loads(response)

    if analysis["overall_confidence"] < PHASE_1_CONFIDENCE_THRESHOLD:
        return self._fallback_to_heuristics(samples)

    return CodebaseAnalysis.from_dict(analysis)

# Phase 4
from prompts import PHASE_4_AGENT_CREATION_PROMPT, PHASE_4_CONFIDENCE_THRESHOLD

def _phase5_agent_creation(self, analysis: CodebaseAnalysis) -> AgentCreationResult:
    # ... similar pattern

# Phase 7.5
from prompts import PHASE_7_5_ENHANCEMENT_PROMPT, PHASE_7_5_CONFIDENCE_THRESHOLD

def _phase7_5_enhance_agents(self, basic_agents: List[Agent]) -> List[Agent]:
    # ... similar pattern
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-18 | Initial specification |

---

**Created**: 2025-11-18
**Author**: architectural-reviewer, code-reviewer
**Status**: Ready for implementation
