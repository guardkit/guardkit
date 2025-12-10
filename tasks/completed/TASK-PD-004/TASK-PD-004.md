---
id: TASK-PD-004
title: Update agent_scanner.py to exclude -ext.md files
status: completed
created: 2025-12-03T16:00:00Z
updated: 2025-12-05T12:15:00Z
completed: 2025-12-05T12:20:00Z
priority: high
tags: [progressive-disclosure, phase-1, foundation, discovery]
complexity: 3
blocked_by: [TASK-PD-003]
blocks: [TASK-PD-005, TASK-PD-008]
review_task: TASK-REV-426C
completed_location: tasks/completed/TASK-PD-004/
test_results:
  status: passed
  coverage: 44%
  last_run: 2025-12-05T12:00:00Z
  tests_passed: 9
  tests_failed: 0
organized_files:
  - completion-summary.md
  - TASK-PD-004.md
---

# Task: Update agent_scanner.py to exclude -ext.md files

## Phase

**Phase 1: Foundation** (Final task before checkpoint)

## Description

Update the agent discovery system to exclude `-ext.md` files from agent listings. Extended files should not appear as separate agents - they are supplementary content loaded on-demand.

## Current State

- `agent_scanner.py` globs `*.md` files in agent directories
- All markdown files are treated as potential agents
- No filtering based on filename patterns

## Target State

- Files ending in `-ext.md` are excluded from discovery
- Only core agent files appear in agent listings
- Extended files remain accessible for explicit loading

## Implementation

### Simple Exclusion Pattern

```python
def scan_agents(self, agent_dir: Path) -> List[AgentMetadata]:
    """Scan directory for agent files.

    Args:
        agent_dir: Directory to scan

    Returns:
        List of agent metadata (excluding extended files)
    """
    agent_files = []
    for f in agent_dir.glob("*.md"):
        # Exclude extended files from discovery
        if f.stem.endswith('-ext'):
            continue
        agent_files.append(f)

    return [self._parse_agent(f) for f in sorted(agent_files)]
```

### Alternative: Regex Pattern

```python
import re

EXTENDED_FILE_PATTERN = re.compile(r'.*-ext\.md$')

def is_extended_file(path: Path) -> bool:
    """Check if file is an extended content file."""
    return EXTENDED_FILE_PATTERN.match(path.name) is not None

def scan_agents(self, agent_dir: Path) -> List[AgentMetadata]:
    """Scan directory for agent files."""
    return [
        self._parse_agent(f)
        for f in sorted(agent_dir.glob("*.md"))
        if not is_extended_file(f)
    ]
```

## Acceptance Criteria

- [x] `-ext.md` files excluded from `scan_agents()` results
- [x] Core agent files still discovered correctly
- [x] `is_extended_file()` helper function available
- [x] No changes to agent metadata parsing
- [x] Unit tests for exclusion logic
- [x] Integration test: scan directory with split agents

## Test Strategy

```python
def test_extended_files_excluded():
    """Test that -ext.md files are excluded from discovery."""
    scanner = AgentScanner()

    # Create test directory with split agents
    agent_dir = create_test_agent_dir([
        "task-manager.md",      # Should be discovered
        "task-manager-ext.md",  # Should be excluded
        "code-reviewer.md",     # Should be discovered
        "code-reviewer-ext.md", # Should be excluded
    ])

    agents = scanner.scan_agents(agent_dir)

    assert len(agents) == 2
    assert "task-manager" in [a.name for a in agents]
    assert "code-reviewer" in [a.name for a in agents]
    assert not any("-ext" in a.name for a in agents)

def test_is_extended_file():
    """Test extended file detection."""
    assert is_extended_file(Path("task-manager-ext.md")) is True
    assert is_extended_file(Path("task-manager.md")) is False
    assert is_extended_file(Path("my-ext-agent.md")) is False  # Not at end
    assert is_extended_file(Path("agent-ext.md")) is True
```

## Files to Modify

1. `installer/core/lib/agent_scanner/agent_scanner.py` - Add exclusion logic
2. `installer/core/lib/agent_scanner/__init__.py` - Export helper function (optional)

## Validation Checkpoint

**After completing TASK-PD-001 through TASK-PD-004:**

1. Run `/agent-enhance` on a test agent
2. Verify split output (core + ext files)
3. Run agent discovery scan
4. Verify only core agent appears in listing
5. Verify ext file is accessible via explicit `cat`

```bash
# Test sequence
/agent-enhance test-template/test-agent.md
ls -la test-template/agents/
# Should show: test-agent.md, test-agent-ext.md

# Discovery test
python3 -c "from lib.agent_scanner import AgentScanner; print([a.name for a in AgentScanner().scan_agents(Path('test-template/agents'))])"
# Should show: ['test-agent'] (not 'test-agent-ext')
```

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-003 (enhancer update)

## Risk

**Low** - Simple string matching, no complex logic changes.
