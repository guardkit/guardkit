---
id: TASK-PD-009
title: Define CORE_SECTIONS and EXTENDED_SECTIONS rules
status: completed
created: 2025-12-03T16:00:00Z
updated: 2025-12-05T15:45:00Z
completed: 2025-12-05T15:45:00Z
priority: high
tags: [progressive-disclosure, phase-3, categorization, rules]
complexity: 5
estimated_hours: 4
actual_hours: 0.5
blocked_by: [TASK-PD-008]
blocks: [TASK-PD-010]
review_task: TASK-REV-426C
completed_location: tasks/completed/TASK-PD-009/
organized_files:
  - TASK-PD-009.md
  - completion-summary.md
test_results:
  status: passed
  coverage: 100
  last_run: 2025-12-05T15:40:00Z
  tests_passed: 21
  tests_failed: 0
code_review:
  status: approved
  score: 9.5
---

# Task: Define CORE_SECTIONS and EXTENDED_SECTIONS rules

## Phase

**Phase 3: Automated Global Agent Migration**

## Description

Define precise rules for categorizing agent content into core (always loaded) and extended (loaded on-demand) sections. These rules drive the automated splitter.

## Categorization Philosophy

### Core Content = Decision-Making

Core content answers: "Should I use this agent? How do I invoke it?"

- Identity (who am I?)
- Quick examples (how do I use this?)
- Boundaries (what should I always/never do?)
- Phase integration (when am I invoked?)
- Capabilities summary (what can I do?)

### Extended Content = Implementation Details

Extended content answers: "How do I implement correctly? What are the edge cases?"

- Detailed examples (full code samples)
- Best practices (in-depth explanations)
- Anti-patterns (what to avoid with examples)
- Technology specifics (per-stack guidance)
- Troubleshooting (edge cases)

## Section Categorization Rules

### CORE Sections (Keep in main file)

```python
CORE_SECTIONS = {
    # Always core - structural
    'frontmatter': True,           # Required for discovery
    'title': True,                 # H1 heading - agent name

    # Always core - essential for invocation
    'quick_start': {
        'patterns': ['Quick Start', 'Getting Started', 'Usage'],
        'max_examples': 10,        # Limit to 10 essential examples
    },

    'boundaries': {
        'patterns': ['Boundaries', 'ALWAYS', 'NEVER', 'ASK'],
        'required': True,          # Must be present (GitHub standards)
    },

    'capabilities': {
        'patterns': ['Capabilities', 'What I Can Do', 'Features'],
        'condensed': True,         # List only, no detailed explanations
    },

    'phase_integration': {
        'patterns': ['Phase', 'When to Use', 'Integration'],
        'include_routing': True,   # Include auto-routing logic
    },

    'mission': {
        'patterns': ['Your Mission', 'Your Critical Mission', 'Role'],
    },

    'model_config': {
        'patterns': ['Model', 'Model Selection', 'Cost'],
    },
}
```

### EXTENDED Sections (Move to -ext.md)

```python
EXTENDED_SECTIONS = {
    # Detailed examples
    'code_examples': {
        'patterns': [
            'Example', 'Code Example', 'Implementation Example',
            'Sample', 'Code Sample', 'Demonstration'
        ],
        'reason': 'Detailed code belongs in reference material',
    },

    # Patterns and practices
    'patterns': {
        'patterns': [
            'Pattern', 'Best Practice', 'Recommended Practice',
            'Design Pattern', 'Architecture Pattern'
        ],
        'reason': 'In-depth explanations loaded when implementing',
    },

    # Anti-patterns
    'anti_patterns': {
        'patterns': [
            'Anti-Pattern', 'What Not to Do', 'Common Mistake',
            'Pitfall', 'Warning'
        ],
        'reason': 'Reference material for avoiding issues',
    },

    # Technology specifics
    'technology': {
        'patterns': [
            'Technology', 'Stack', 'Framework', 'Language-Specific',
            'Python', 'TypeScript', 'React', '.NET', 'FastAPI'
        ],
        'reason': 'Per-stack details loaded when needed',
    },

    # MCP integration
    'mcp': {
        'patterns': [
            'MCP', 'Context7', 'Design Pattern MCP', 'Tool Integration'
        ],
        'reason': 'Advanced integration details',
    },

    # Troubleshooting
    'troubleshooting': {
        'patterns': [
            'Troubleshoot', 'Debug', 'Common Issue', 'FAQ',
            'Edge Case', 'Known Issue'
        ],
        'reason': 'Reference when problems occur',
    },

    # Implementation guides
    'implementation': {
        'patterns': [
            'Implementation Guide', 'Step-by-Step', 'Walkthrough',
            'Tutorial', 'How To'
        ],
        'reason': 'Detailed implementation belongs in reference',
    },

    # Reference material
    'reference': {
        'patterns': [
            'Reference', 'Appendix', 'Additional', 'See Also',
            'Related', 'Further Reading'
        ],
        'reason': 'Reference material loaded on demand',
    },
}
```

## Agent-Specific Overrides

Some agents have unique section names that need special handling:

```python
AGENT_OVERRIDES = {
    'task-manager': {
        'core_additional': [
            'Phase 2.5', 'Phase 2.7', 'Phase 2.8',  # Critical routing
            'State Management', 'Quality Gates'
        ],
        'extended_additional': [
            'Detailed Workflow', 'Complex Scenarios'
        ]
    },

    'architectural-reviewer': {
        'core_additional': [
            'SOLID Principles',  # Keep summary
            'Scoring'
        ],
        'extended_additional': [
            'SOLID Examples',    # Move detailed examples
            'Pattern Analysis'
        ]
    },

    'code-reviewer': {
        'core_additional': [
            'Build Verification', 'Approval Checklist'
        ],
        'extended_additional': [
            'Documentation Level', 'Detailed Checklists'
        ]
    }
}
```

## Validation Rules

```python
VALIDATION_RULES = {
    'core': {
        'max_size_kb': 15,              # Core should be ≤15KB
        'required_sections': [
            'frontmatter',
            'title',
            'boundaries',               # GitHub standards
            'loading_instruction'       # Added by splitter
        ],
        'max_examples': 10,             # Limit examples in core
    },

    'extended': {
        'min_size_kb': 5,               # Should have substantial content
        'required_sections': [
            'header',                   # Reference to core file
        ],
    },

    'overall': {
        'min_reduction_percent': 40,    # At least 40% reduction
        'content_preserved': True,      # No content loss
    }
}
```

## Acceptance Criteria

- [ ] CORE_SECTIONS dictionary defined with patterns
- [ ] EXTENDED_SECTIONS dictionary defined with patterns
- [ ] AGENT_OVERRIDES for agents with unique sections
- [ ] VALIDATION_RULES for split verification
- [ ] Rules documented in split-agent.py
- [ ] Rules tested against sample agents
- [ ] Edge cases handled (ambiguous sections)

## Test Strategy

```python
def test_categorization_task_manager():
    """Test categorization for task-manager.md."""
    splitter = AgentSplitter()
    content = Path('installer/core/agents/task-manager.md').read_text()
    sections = splitter._parse_sections(content)

    core, extended = splitter._categorize_sections(sections)

    # Verify critical sections in core
    core_headings = [s['heading'] for s in core]
    assert 'Quick Start' in core_headings or any('Quick' in h for h in core_headings)
    assert 'Boundaries' in core_headings or any('ALWAYS' in h for h in core_headings)

    # Verify examples moved to extended
    extended_headings = [s['heading'] for s in extended]
    assert any('Example' in h for h in extended_headings)

def test_reduction_target():
    """Test that splits achieve target reduction."""
    splitter = AgentSplitter(dry_run=True)

    for agent_file in Path('installer/core/agents').glob('*.md'):
        if agent_file.stem.endswith('-ext'):
            continue

        result = splitter.split_agent(agent_file)
        assert result.reduction_percent >= 40, f"{agent_file.name}: only {result.reduction_percent:.1f}% reduction"
```

## Files to Modify

1. `scripts/split-agent.py` - Add categorization rules

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-008 (split-agent.py script)

## Notes

- When in doubt, keep section in CORE (safer default)
- Review first 3 splits manually before batch processing
- Document any exceptions in AGENT_OVERRIDES
