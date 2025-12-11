---
id: TASK-FIX-RATIONALE-E7F1
title: Meaningful Agent Rationale
status: completed
task_type: implementation
created: 2025-12-11T10:45:00Z
updated: 2025-12-11T12:30:00Z
completed: 2025-12-11T12:30:00Z
priority: low
tags: [template-create, agent-generation, ux, documentation]
complexity: 2
parent_review: TASK-REV-D4A7
test_results:
  status: passed
  coverage: 100
  last_run: 2025-12-11T12:25:00Z
completed_location: tasks/completed/TASK-FIX-RATIONALE-E7F1/
organized_files:
  - TASK-FIX-RATIONALE-E7F1.md
---

# Task: Meaningful Agent Rationale

## Problem Statement

Generated agents have generic, unhelpful "Why This Agent Exists" text:

```markdown
## Why This Agent Exists

Specialized agent for maui mvvm viewmodel specialist
```

This provides no value to users trying to understand when to use the agent.

## Root Cause

**Generic Fallback** (`template_create_orchestrator.py:1178`):
```python
'reason': getattr(agent, 'reason', f"Specialized agent for {agent_name.replace('-', ' ')}")
```

**Existing Capability (Unused)** - `agent_generator.py:262-276` has meaningful examples:
```python
"reason": "Project uses Repository pattern in Infrastructure layer",
"reason": "Project has domain layer with operations subdirectory",
"reason": "Project uses MVVM architecture with ViewModels",
```

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `installer/core/commands/lib/template_create_orchestrator.py` | 1178 | Replace fallback with intelligent generation |
| `installer/core/lib/agent_generator/markdown_formatter.py` | 67-69 | No change needed (uses passed reason) |

## Implementation Specification

### Step 1: Add Rationale Generation Function (template_create_orchestrator.py)

**Add this function before line 1178:**

```python
def _generate_agent_rationale(
    agent_name: str,
    technologies: list,
    description: str,
    detected_patterns: list = None,
    detected_layers: list = None
) -> str:
    """
    Generate meaningful rationale for why this agent exists in the template.

    Args:
        agent_name: Name of the agent (e.g., "realm-repository-specialist")
        technologies: List of technologies the agent handles
        description: Agent description from frontmatter
        detected_patterns: Patterns detected in codebase (optional)
        detected_layers: Layers detected in codebase (optional)

    Returns:
        Meaningful rationale string

    Examples:
        "Provides specialized guidance for Realm, ErrorOr implementations.
         This project uses the Repository pattern with Realm Mobile Database
         for thread-safe data access."
    """
    rationale_parts = []

    # Part 1: Technology expertise
    if technologies and len(technologies) >= 1:
        tech_str = ", ".join(technologies[:4])  # Limit to 4 for readability
        rationale_parts.append(
            f"Provides specialized guidance for {tech_str} implementations"
        )

    # Part 2: Pattern relevance (if available)
    if detected_patterns:
        # Map agent names to relevant patterns
        pattern_mappings = {
            'repository': ['Repository', 'Data Access'],
            'viewmodel': ['MVVM', 'ViewModel'],
            'service': ['Service Layer', 'Services'],
            'engine': ['Engine', 'Business Logic'],
            'erroror': ['Railway-Oriented Programming', 'ErrorOr'],
            'testing': ['Testing', 'Unit Tests'],
            'api': ['API', 'REST', 'HTTP'],
            'mapper': ['Mapper', 'Mapping'],
        }

        agent_lower = agent_name.lower()
        relevant_patterns = []
        for key, patterns in pattern_mappings.items():
            if key in agent_lower:
                relevant_patterns.extend(
                    p for p in patterns if p in detected_patterns
                )

        if relevant_patterns:
            pattern_str = ", ".join(set(relevant_patterns))
            rationale_parts.append(
                f"This project uses the {pattern_str} pattern"
            )

    # Part 3: Layer relevance (if available)
    if detected_layers:
        layer_mappings = {
            'repository': 'Infrastructure',
            'viewmodel': 'Presentation',
            'service': 'Application',
            'engine': 'Application',
            'domain': 'Domain',
            'api': 'API',
        }

        agent_lower = agent_name.lower()
        for key, layer in layer_mappings.items():
            if key in agent_lower and layer in detected_layers:
                rationale_parts.append(
                    f"in the {layer} layer"
                )
                break

    # Part 4: Extract key insight from description
    if description and not rationale_parts:
        # Fall back to description-based rationale
        # Extract first meaningful phrase (up to 60 chars)
        desc_clean = description.strip()
        if len(desc_clean) > 60:
            # Find a good break point
            truncated = desc_clean[:60]
            last_space = truncated.rfind(' ')
            if last_space > 30:
                desc_clean = truncated[:last_space] + "..."

        rationale_parts.append(
            f"Handles {desc_clean}"
        )

    # Combine parts into coherent rationale
    if rationale_parts:
        # Join with appropriate punctuation
        if len(rationale_parts) == 1:
            return rationale_parts[0] + "."
        elif len(rationale_parts) == 2:
            return f"{rationale_parts[0]}. {rationale_parts[1]}."
        else:
            return ". ".join(rationale_parts) + "."

    # Final fallback (should rarely happen)
    return f"Specialized agent for {agent_name.replace('-', ' ')} patterns."
```

### Step 2: Update Agent Dictionary Creation (template_create_orchestrator.py:1178)

**Before:**
```python
'reason': getattr(agent, 'reason', f"Specialized agent for {agent_name.replace('-', ' ')}")
```

**After:**
```python
'reason': getattr(agent, 'reason', None) or _generate_agent_rationale(
    agent_name=agent_name,
    technologies=getattr(agent, 'technologies', []),
    description=getattr(agent, 'description', ''),
    detected_patterns=self.analysis.architecture.patterns if self.analysis else None,
    detected_layers=[l.name for l in self.analysis.architecture.layers] if self.analysis else None
)
```

### Step 3: Add Tests

```python
# tests/commands/lib/test_agent_rationale.py

import pytest
from installer.core.commands.lib.template_create_orchestrator import _generate_agent_rationale


class TestAgentRationale:
    """Tests for agent rationale generation."""

    def test_rationale_with_technologies(self):
        """Test rationale generation from technologies."""
        rationale = _generate_agent_rationale(
            agent_name="realm-repository-specialist",
            technologies=["Realm", "ErrorOr", "Riok.Mapperly"],
            description=""
        )

        assert "Realm" in rationale
        assert "ErrorOr" in rationale
        assert "Specialized agent for" not in rationale  # Not generic

    def test_rationale_with_patterns(self):
        """Test rationale includes detected patterns."""
        rationale = _generate_agent_rationale(
            agent_name="repository-specialist",
            technologies=["C#"],
            description="",
            detected_patterns=["Repository", "Service Layer", "MVVM"]
        )

        assert "Repository" in rationale

    def test_rationale_with_layers(self):
        """Test rationale includes layer context."""
        rationale = _generate_agent_rationale(
            agent_name="repository-specialist",
            technologies=["C#"],
            description="",
            detected_patterns=["Repository"],
            detected_layers=["Infrastructure", "Domain"]
        )

        assert "Infrastructure" in rationale

    def test_rationale_fallback_to_description(self):
        """Test rationale uses description when no tech."""
        rationale = _generate_agent_rationale(
            agent_name="custom-specialist",
            technologies=[],
            description="Handles complex business validation rules"
        )

        assert "business validation" in rationale.lower()

    def test_rationale_not_generic(self):
        """Test that output is never the generic fallback."""
        test_cases = [
            {"technologies": ["Python"]},
            {"description": "Handles API calls"},
            {"detected_patterns": ["Repository"]},
        ]

        for case in test_cases:
            rationale = _generate_agent_rationale(
                agent_name="test-specialist",
                technologies=case.get("technologies", []),
                description=case.get("description", ""),
                detected_patterns=case.get("detected_patterns"),
            )

            assert "Specialized agent for test specialist" not in rationale

    def test_rationale_for_maui_agents(self):
        """Test rationale for .NET MAUI specific agents."""
        agents = [
            ("maui-mvvm-viewmodel-specialist", ["C#", "MAUI", "CommunityToolkit.Mvvm"]),
            ("realm-repository-specialist", ["C#", "Realm", "ErrorOr"]),
            ("error-or-railway-specialist", ["C#", "ErrorOr"]),
        ]

        for agent_name, technologies in agents:
            rationale = _generate_agent_rationale(
                agent_name=agent_name,
                technologies=technologies,
                description="",
                detected_patterns=["Repository", "MVVM", "Railway-Oriented Programming"]
            )

            # Should mention at least one technology
            assert any(tech in rationale for tech in technologies[:2])
            # Should not be generic
            assert "Specialized agent for" not in rationale or "patterns" in rationale
```

## Expected Output Examples

**Before (generic):**
```markdown
## Why This Agent Exists

Specialized agent for maui mvvm viewmodel specialist
```

**After (meaningful):**
```markdown
## Why This Agent Exists

Provides specialized guidance for C#, MAUI, CommunityToolkit.Mvvm implementations. This project uses the MVVM pattern in the Presentation layer.
```

**Other examples:**

| Agent | Generated Rationale |
|-------|---------------------|
| realm-repository-specialist | "Provides specialized guidance for Realm, ErrorOr, Riok.Mapperly implementations. This project uses the Repository pattern in the Infrastructure layer." |
| error-or-railway-specialist | "Provides specialized guidance for ErrorOr implementations. This project uses the Railway-Oriented Programming pattern." |
| xunit-nsubstitute-testing-specialist | "Provides specialized guidance for xUnit, NSubstitute, FluentAssertions implementations. This project uses the Testing pattern." |

## Acceptance Criteria

- [ ] Agent rationale derived from technologies list
- [ ] Agent rationale includes detected pattern context
- [ ] Agent rationale includes layer context when relevant
- [ ] No more generic "Specialized agent for {name}" text
- [ ] Rationale is specific and actionable
- [ ] Works for all 7 mydrive agents
- [ ] All tests pass

## Test Requirements

```bash
# Run rationale tests
pytest tests/commands/lib/test_agent_rationale.py -v

# Manual verification
python3 -c "
from installer.core.commands.lib.template_create_orchestrator import _generate_agent_rationale

agents = [
    ('maui-mvvm-viewmodel-specialist', ['C#', 'MAUI', 'CommunityToolkit.Mvvm']),
    ('realm-repository-specialist', ['C#', 'Realm', 'ErrorOr']),
    ('error-or-railway-specialist', ['C#', 'ErrorOr']),
]

for name, tech in agents:
    rationale = _generate_agent_rationale(
        agent_name=name,
        technologies=tech,
        description='',
        detected_patterns=['Repository', 'MVVM', 'Railway-Oriented Programming']
    )
    print(f'{name}:')
    print(f'  {rationale}')
    print()
"
```

## Regression Prevention

**Potential Regressions:**
1. Agents with explicit `reason` attribute might get overwritten
2. Very long technology lists could create unwieldy rationale

**Mitigation:**
- Check for existing `reason` attribute first (existing behavior)
- Limit technology list to 4 items
- Keep rationale under 200 characters when possible

## Notes

- **Low priority** - cosmetic improvement
- Consider adding templates for common agent types
- Future: Allow custom rationale templates in agent config
