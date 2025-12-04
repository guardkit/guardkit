---
id: TASK-PD-007
title: Update TemplateClaude model with split fields
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: high
tags: [progressive-disclosure, phase-2, models, dataclass]
complexity: 4
blocked_by: [TASK-PD-006]
blocks: [TASK-PD-008]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update TemplateClaude model with split fields

## Phase

**Phase 2: Template Generation - CLAUDE.md Split** (Final task)

## Description

Update the `TemplateClaude` dataclass and related models to support progressive disclosure metadata and split output tracking.

## Current State

- `TemplateClaude` in `models.py` represents single-file output
- No awareness of split structure
- No size tracking

## Target State

- `TemplateClaude` extended with optional split metadata
- `TemplateSplitOutput` dataclass for split generation results
- Size tracking and validation methods
- Backward compatible with existing code

## Implementation

### Extended TemplateClaude

```python
@dataclass
class TemplateClaude:
    """CLAUDE.md content structure."""
    schema_version: str
    architecture_overview: str
    technology_stack: str
    project_structure: str
    naming_conventions: str
    patterns: str
    examples: str
    quality_standards: str
    agent_usage: str
    generated_at: str
    confidence_score: float

    # Progressive disclosure fields (optional)
    split_output: bool = False
    loading_instructions: Optional[str] = None
    patterns_path: Optional[str] = None
    reference_path: Optional[str] = None

    def to_markdown(self) -> str:
        """Convert to full markdown (legacy single-file)."""
        # Existing implementation
        pass

    def to_core_markdown(self) -> str:
        """Convert to core markdown for progressive disclosure."""
        if not self.split_output:
            return self.to_markdown()

        sections = [
            f"# {self._get_title()}",
            "",
            self.architecture_overview,
            self.technology_stack,
            self.project_structure,
            self.naming_conventions,
            self._get_quality_summary(),
            self._get_agent_summary(),
            self.loading_instructions or self._generate_loading_instructions(),
        ]
        return "\n\n".join(sections)

    def _generate_loading_instructions(self) -> str:
        """Generate default loading instructions."""
        return f'''
## Extended Documentation

For detailed patterns and examples, load the extended documentation:

```bash
cat {self.patterns_path or 'docs/patterns/README.md'}
cat {self.reference_path or 'docs/reference/README.md'}
```
'''
```

### New TemplateSplitOutput

```python
@dataclass
class TemplateSplitOutput:
    """Split template output for progressive disclosure."""
    core: str
    patterns: str
    reference: str
    metadata: TemplateSplitMetadata

    def get_core_size(self) -> int:
        """Get core content size in bytes."""
        return len(self.core.encode('utf-8'))

    def get_total_size(self) -> int:
        """Get total content size in bytes."""
        return sum(len(s.encode('utf-8')) for s in [self.core, self.patterns, self.reference])

    def get_reduction_percent(self) -> float:
        """Calculate size reduction for core vs total."""
        total = self.get_total_size()
        if total == 0:
            return 0
        return (1 - self.get_core_size() / total) * 100

    def validate(self) -> List[str]:
        """Validate split output meets requirements.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Core size check
        core_size = self.get_core_size()
        if core_size > 10 * 1024:  # 10KB limit
            errors.append(f"Core size {core_size:,} exceeds 10KB limit")

        # Reduction check
        reduction = self.get_reduction_percent()
        if reduction < 40:
            errors.append(f"Reduction {reduction:.1f}% below 40% target")

        # Content presence checks
        if not self.patterns.strip():
            errors.append("Patterns content is empty")
        if not self.reference.strip():
            errors.append("Reference content is empty")

        return errors


@dataclass
class TemplateSplitMetadata:
    """Metadata for split template output."""
    core_size_bytes: int
    patterns_size_bytes: int
    reference_size_bytes: int
    total_size_bytes: int
    reduction_percent: float
    generated_at: str
    validation_passed: bool
    validation_errors: List[str]
```

## Acceptance Criteria

- [ ] `TemplateClaude` extended with split fields
- [ ] `to_core_markdown()` method implemented
- [ ] `TemplateSplitOutput` dataclass implemented
- [ ] `TemplateSplitMetadata` dataclass implemented
- [ ] Size validation methods working
- [ ] Backward compatible (existing code unaffected)
- [ ] Unit tests for new methods

## Test Strategy

```python
def test_template_claude_core_markdown():
    """Test core markdown generation."""
    claude = TemplateClaude(
        # ... fields ...
        split_output=True
    )

    core = claude.to_core_markdown()

    assert len(core.encode('utf-8')) < len(claude.to_markdown().encode('utf-8'))
    assert "## Extended Documentation" in core

def test_template_split_output_validation():
    """Test split output validation."""
    output = TemplateSplitOutput(
        core="# Core\n" * 100,      # Small core
        patterns="# Patterns\n" * 500,
        reference="# Reference\n" * 500,
        metadata=TemplateSplitMetadata(...)
    )

    errors = output.validate()
    assert len(errors) == 0  # Should pass

def test_template_split_output_validation_fails():
    """Test validation catches issues."""
    output = TemplateSplitOutput(
        core="# Core\n" * 5000,    # Too large
        patterns="",               # Empty
        reference="# Reference",
        metadata=TemplateSplitMetadata(...)
    )

    errors = output.validate()
    assert "exceeds 10KB limit" in errors[0]
    assert "Patterns content is empty" in errors[1]
```

## Files to Modify

1. `installer/global/lib/template_generator/models.py` - Main changes

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-006 (orchestrator update)
