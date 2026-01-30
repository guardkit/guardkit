---
id: TASK-GR-002-G
title: Tests for parsers
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, context-addition, testing, parsers, mvp-phase-2]
task_type: testing
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 9
conductor_workspace: gr-mvp-wave9-tests
complexity: 4
depends_on:
  - TASK-GR-002-F
---

# Task: Tests for parsers

## Description

Create comprehensive tests for all parser implementations (FeatureSpecParser, ADRParser, ProjectOverviewParser).

## Acceptance Criteria

- [ ] Unit tests for each parser
- [ ] Tests for edge cases and malformed input
- [ ] Tests for parser registry
- [ ] Integration tests with real sample files
- [ ] 80%+ coverage for parser code

## Implementation Notes

### Test Structure

```
tests/
├── unit/
│   └── integrations/
│       └── graphiti/
│           └── parsers/
│               ├── test_base.py
│               ├── test_registry.py
│               ├── test_feature_spec.py
│               ├── test_adr.py
│               └── test_project_overview.py
└── fixtures/
    └── parsers/
        ├── sample_feature_spec.md
        ├── sample_adr.md
        ├── sample_claude.md
        └── malformed/
            ├── no_frontmatter.md
            └── invalid_yaml.md
```

### Test Cases per Parser

```python
# FeatureSpecParser tests
class TestFeatureSpecParser:
    def test_parse_valid_spec(self, sample_feature_spec):
        """Test parsing valid feature spec."""
        pass

    def test_extract_tasks(self, sample_feature_spec):
        """Test task extraction from spec."""
        pass

    def test_handle_missing_frontmatter(self, no_frontmatter):
        """Test handling of missing frontmatter."""
        pass

    def test_can_parse_detection(self):
        """Test file type detection."""
        pass

# ADRParser tests
class TestADRParser:
    def test_parse_valid_adr(self, sample_adr):
        """Test parsing valid ADR."""
        pass

    def test_extract_sections(self, sample_adr):
        """Test section extraction."""
        pass

    def test_various_formats(self, adr_variants):
        """Test different ADR formats."""
        pass

# ProjectOverviewParser tests
class TestProjectOverviewParser:
    def test_parse_claude_md(self, sample_claude):
        """Test parsing CLAUDE.md."""
        pass

    def test_parse_readme(self, sample_readme):
        """Test parsing README.md."""
        pass

    def test_missing_sections(self):
        """Test handling of incomplete docs."""
        pass
```

### Files to Create

- Test files as listed above
- Fixture files with sample content

## Test Requirements

- [ ] All tests pass
- [ ] 80%+ coverage for parser code
- [ ] Edge cases covered

## Notes

Final testing task for parsers.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
