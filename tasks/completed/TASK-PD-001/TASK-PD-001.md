---
id: TASK-PD-001
title: Refactor applier.py with create_extended_file() method
status: completed
created: 2025-12-03T16:00:00Z
updated: 2025-12-05T08:40:00Z
completed: 2025-12-05T08:40:00Z
priority: high
tags: [progressive-disclosure, phase-1, foundation, applier, high-risk]
complexity: 7
blocked_by: [TASK-PD-000]
blocks: [TASK-PD-002, TASK-PD-003, TASK-PD-004]
review_task: TASK-REV-426C
design:
  status: approved
  approved_at: "2025-12-05T08:30:00Z"
  approved_by: user
  implementation_plan_version: v1
  architectural_review_score: 78
  complexity_score: 7
  design_notes: "Plan approved with architectural recommendations applied"
test_results:
  status: passed
  coverage: 75
  branch_coverage: 92
  tests_passed: 40
  tests_failed: 0
  last_run: 2025-12-05T08:35:00Z
completed_location: tasks/completed/TASK-PD-001/
organized_files:
  - TASK-PD-001.md
  - implementation-complete.md
duration_hours: 0.25
---

# Task: Refactor applier.py with create_extended_file() method

## Phase

**Phase 1: Foundation** (HIGHEST RISK)

## Description

Refactor `installer/core/lib/agent_enhancement/applier.py` to support progressive disclosure by creating separate extended files (`{name}-ext.md`) alongside core agent files.

This is the **highest risk task** in the progressive disclosure initiative as it changes the core behavior of the enhancement pipeline.

## Current State

- `applier.py` (253 lines) merges enhancement content into a single file
- `_merge_content()` appends sections to original file
- Single file output model

## Target State

- New `create_extended_file()` method that writes extended content to `{name}-ext.md`
- Modified `apply()` method that splits content between core and extended files
- Content categorization logic (core vs extended sections)
- Backward compatibility maintained (feature flag if needed)

## Implementation Approach

### Option A: New Method (Recommended)

Add `create_extended_file()` without modifying existing `apply()`:

```python
def create_extended_file(self, agent_path: Path, extended_content: str) -> Path:
    """Create extended content file alongside core agent file.

    Args:
        agent_path: Path to core agent file
        extended_content: Content for extended file

    Returns:
        Path to created extended file
    """
    ext_path = agent_path.with_stem(f"{agent_path.stem}-ext")
    ext_path.write_text(extended_content, encoding='utf-8')
    return ext_path

def apply_with_split(self, agent_path: Path, enhancement: AgentEnhancement) -> Tuple[Path, Path]:
    """Apply enhancement with progressive disclosure split.

    Returns:
        Tuple of (core_path, extended_path)
    """
    core_content, extended_content = self._split_enhancement(enhancement)

    # Apply core content to original file
    self.apply(agent_path, core_content)

    # Create extended file
    ext_path = self.create_extended_file(agent_path, extended_content)

    return agent_path, ext_path
```

### Option B: Feature Flag

Add flag to existing `apply()`:

```python
def apply(self, agent_path: Path, enhancement: AgentEnhancement,
          split_output: bool = False) -> Union[Path, Tuple[Path, Path]]:
    """Apply enhancement to agent file.

    Args:
        split_output: If True, create separate extended file
    """
    if split_output:
        return self._apply_with_split(agent_path, enhancement)
    else:
        return self._apply_single(agent_path, enhancement)
```

## Content Categorization

### Core Sections (Keep in main file)

```python
CORE_SECTIONS = [
    'frontmatter',           # Required for discovery
    'title',                 # Agent name/description
    'quick_start',           # Essential examples (5-10)
    'boundaries',            # ALWAYS/NEVER/ASK
    'capabilities',          # Condensed list
    'phase_integration',     # Which phases
    'loading_instruction',   # Link to extended file
]
```

### Extended Sections (Move to -ext.md)

```python
EXTENDED_SECTIONS = [
    'detailed_examples',     # 20-50 code examples
    'best_practices',        # Full explanations
    'anti_patterns',         # Full code with explanations
    'cross_stack',           # Cross-stack considerations
    'mcp_integration',       # MCP details
    'troubleshooting',       # Edge cases
    'technology_specific',   # Per-technology guidance
]
```

## Acceptance Criteria

- [ ] `create_extended_file()` method implemented
- [ ] `apply_with_split()` or feature flag implemented
- [ ] Content categorization logic works correctly
- [ ] Core file contains loading instruction section
- [ ] Extended file has proper header referencing core file
- [ ] Existing `apply()` behavior unchanged (backward compatible)
- [ ] Unit tests for new methods
- [ ] Integration test: enhance single agent, verify split output

## Test Strategy

```python
def test_create_extended_file():
    """Test extended file creation."""
    applier = EnhancementApplier()
    agent_path = Path("test-agent.md")
    extended_content = "# Extended Content\n\n## Examples\n..."

    ext_path = applier.create_extended_file(agent_path, extended_content)

    assert ext_path == Path("test-agent-ext.md")
    assert ext_path.exists()
    assert ext_path.read_text() == extended_content

def test_apply_with_split():
    """Test enhancement with split output."""
    applier = EnhancementApplier()
    agent_path = create_test_agent()
    enhancement = create_test_enhancement()

    core_path, ext_path = applier.apply_with_split(agent_path, enhancement)

    # Verify core has loading instruction
    core_content = core_path.read_text()
    assert "## Extended Reference" in core_content
    assert f"cat {ext_path.name}" in core_content

    # Verify extended has content
    ext_content = ext_path.read_text()
    assert "## Detailed Examples" in ext_content
```

## Files to Modify

1. `installer/core/lib/agent_enhancement/applier.py` - Main changes
2. `installer/core/lib/agent_enhancement/models.py` - May need new types

## Risk Mitigation

- Create new methods without touching existing code
- Use feature flag for gradual rollout
- Test with single agent before global deployment
- Keep backup of original applier.py

## Validation Checkpoint

After completing this task:
1. Run `/agent-enhance` on a test agent with split enabled
2. Verify core file size reduced by ~50%
3. Verify extended file created with correct content
4. Verify loading instruction present in core
5. Verify no regression in standard enhancement

## Estimated Effort

**2-3 days**

## Dependencies

- None (this is the foundation task)

## Related Documents

- [Review Report](.claude/reviews/TASK-REV-426C-review-report.md)
- [Progressive Disclosure Analysis](docs/research/progressive-disclosure-analysis.md)
- [Current applier.py](installer/core/lib/agent_enhancement/applier.py)
