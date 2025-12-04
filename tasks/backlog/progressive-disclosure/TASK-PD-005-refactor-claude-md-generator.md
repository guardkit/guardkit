---
id: TASK-PD-005
title: Refactor claude_md_generator.py (generate_core + generate_patterns)
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: high
tags: [progressive-disclosure, phase-2, claude-md, generator]
complexity: 6
blocked_by: [TASK-PD-004]
blocks: [TASK-PD-006]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Refactor claude_md_generator.py (generate_core + generate_patterns)

## Phase

**Phase 2: Template Generation - CLAUDE.md Split** (MEDIUM RISK)

## Description

Refactor `installer/global/lib/template_generator/claude_md_generator.py` to produce split output: a core CLAUDE.md (~8KB) and separate pattern/reference files.

## Current State

- `claude_md_generator.py` (1147 lines) produces single CLAUDE.md file
- All content combined: architecture, patterns, examples, testing, workflow
- Typical output: ~20KB per template

## Target State

- `generate_core()` method produces essential content (~8KB)
- `generate_patterns()` method produces detailed patterns/examples
- `generate_reference()` method produces reference documentation
- Split output structure for progressive disclosure

## Content Split Analysis

Based on react-typescript CLAUDE.md (695 lines, ~20KB):

### Core Content (~40%, lines 1-175, 277-295, 451-477, 529-552)

Keep in CLAUDE.md:
- Project Context (essential)
- Core Principles (essential)
- Architecture Overview (essential)
- Technology Stack (essential)
- Project Structure (essential)
- Naming Conventions (essential)
- Quality Standards summary (essential)
- Specialized Agents list (essential)
- Loading instructions (new)

### Patterns Content (~35%, lines 176-375)

Move to `docs/patterns/`:
- Patterns and Best Practices (detailed)
- Query Options Factory Pattern
- Mutations with Cache Invalidation
- Form Validation with Zod
- Component Variants with CVA
- Authorization Patterns
- API Mocking with MSW

### Reference Content (~25%, lines 377-449, 479-527, 554-662)

Move to `docs/reference/`:
- Code Examples (detailed)
- Creating a New Feature (full walkthrough)
- Testing Strategy (detailed)
- Development Workflow
- Common Tasks
- Environment Variables
- Troubleshooting

## Implementation

### New Method Structure

```python
class ClaudeMdGenerator:

    def generate(self) -> TemplateClaude:
        """Generate complete CLAUDE.md content (legacy single-file)."""
        # Existing implementation

    def generate_split(self) -> TemplateSplitOutput:
        """Generate split output for progressive disclosure.

        Returns:
            TemplateSplitOutput with core, patterns, and reference content
        """
        return TemplateSplitOutput(
            core=self._generate_core(),
            patterns=self._generate_patterns(),
            reference=self._generate_reference()
        )

    def _generate_core(self) -> str:
        """Generate core CLAUDE.md content (~8KB)."""
        sections = [
            self._generate_architecture_overview(),
            self._generate_technology_stack(),
            self._generate_project_structure(),
            self._generate_naming_conventions(),
            self._generate_quality_standards_summary(),  # Condensed
            self._generate_agent_usage_summary(),        # Condensed
            self._generate_loading_instructions(),       # NEW
        ]
        return "\n\n".join(sections)

    def _generate_patterns(self) -> str:
        """Generate patterns documentation."""
        return self._generate_patterns_full()  # Existing detailed patterns

    def _generate_reference(self) -> str:
        """Generate reference documentation."""
        sections = [
            self._generate_examples(),
            self._generate_testing_strategy(),
            self._generate_development_workflow(),
            self._generate_common_tasks(),
            self._generate_troubleshooting(),
        ]
        return "\n\n".join(sections)
```

### New Output Model

```python
@dataclass
class TemplateSplitOutput:
    """Split template output for progressive disclosure."""
    core: str               # CLAUDE.md content
    patterns: str           # docs/patterns/*.md content
    reference: str          # docs/reference/*.md content

    def get_core_size(self) -> int:
        """Get core content size in bytes."""
        return len(self.core.encode('utf-8'))

    def get_total_size(self) -> int:
        """Get total content size in bytes."""
        return sum(len(s.encode('utf-8')) for s in [self.core, self.patterns, self.reference])

    def get_reduction_percent(self) -> float:
        """Calculate size reduction for core vs total."""
        return (1 - self.get_core_size() / self.get_total_size()) * 100
```

### Loading Instructions Section

```python
def _generate_loading_instructions(self) -> str:
    """Generate loading instructions for split content."""
    return '''
## Extended Documentation

For detailed patterns and examples, load the extended documentation:

```bash
# Patterns and best practices
cat docs/patterns/README.md

# Reference documentation
cat docs/reference/README.md
```

**Patterns documentation includes**:
- Query patterns with full code examples
- Form validation with Zod schemas
- Component variant patterns
- Authorization patterns

**Reference documentation includes**:
- Creating new features (step-by-step)
- Testing strategy with examples
- Development workflow
- Common tasks reference
- Troubleshooting guide
'''
```

## Acceptance Criteria

- [ ] `generate_split()` method implemented
- [ ] `_generate_core()` produces ~8KB content
- [ ] `_generate_patterns()` extracts pattern content
- [ ] `_generate_reference()` extracts reference content
- [ ] `TemplateSplitOutput` dataclass implemented
- [ ] Loading instructions section in core
- [ ] Backward compatible `generate()` method preserved
- [ ] Unit tests for split generation
- [ ] Size validation (core ≤10KB)

## Test Strategy

```python
def test_generate_split():
    """Test split output generation."""
    generator = ClaudeMdGenerator(analysis)
    output = generator.generate_split()

    # Verify core size
    assert output.get_core_size() <= 10 * 1024  # 10KB max

    # Verify content distribution
    assert "## Architecture Overview" in output.core
    assert "## Loading Instructions" in output.core
    assert "## Patterns and Best Practices" in output.patterns
    assert "## Troubleshooting" in output.reference

    # Verify reduction
    assert output.get_reduction_percent() >= 50  # At least 50% reduction

def test_backward_compatibility():
    """Test legacy single-file generation still works."""
    generator = ClaudeMdGenerator(analysis)
    claude = generator.generate()

    assert isinstance(claude, TemplateClaude)
    assert len(claude.to_markdown()) > 15000  # Full content
```

## Files to Modify

1. `installer/global/lib/template_generator/claude_md_generator.py` - Main refactor
2. `installer/global/lib/template_generator/models.py` - Add TemplateSplitOutput

## Estimated Effort

**2 days**

## Dependencies

- TASK-PD-004 (Phase 1 complete)
